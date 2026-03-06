"""Pop web chat route."""

import hmac
import hashlib
import json
import logging
import os
from typing import Any, AsyncGenerator, Dict, Optional

from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from models.rows import Row, Project
from models.auth import User
from services.llm import make_pop_decision, ChatContext, generate_choice_factors
from routes.chat import _create_row, _update_row, _save_choice_factors, _stream_search
from routes.chat_helpers import _build_and_persist_ui_schema, sse_event
from routes.pop_helpers import _get_pop_user, _ensure_project_member, _load_chat_history, _append_chat_history, _build_item_with_deals

logger = logging.getLogger(__name__)
chat_router = APIRouter()

GUEST_EMAIL = "guest@buy-anything.com"


_GUEST_SESSION_SECRET = os.getenv("GUEST_SESSION_SECRET", "pop-guest-session-default-key")

def _sign_guest_project(project_id: int) -> str:
    """Create an HMAC token binding a guest session to a specific project."""
    return hmac.new(
        _GUEST_SESSION_SECRET.encode(),
        f"guest-project:{project_id}".encode(),
        hashlib.sha256,
    ).hexdigest()


def _verify_guest_token(project_id: int, token: str) -> bool:
    """Verify that the guest token matches the claimed project."""
    expected = _sign_guest_project(project_id)
    return hmac.compare_digest(expected, token)


async def _load_project_list_items(session: AsyncSession, project_id: int) -> list[dict[str, Any]]:
    list_stmt = (
        select(Row)
        .where(Row.project_id == project_id)
        .where(Row.status.in_(["sourcing", "bids_arriving", "open", "active", "pending"]))
        .order_by(Row.created_at.desc())
        .limit(20)
    )
    list_result = await session.execute(list_stmt)
    list_rows = list_result.scalars().all()
    return [await _build_item_with_deals(session, r) for r in list_rows]


async def _build_list_items_event(
    session: AsyncSession,
    project_id: int,
    *,
    row_id: Optional[int] = None,
    action: Optional[str] = None,
    more_incoming: bool = False,
    provider: Optional[str] = None,
    user_message: Optional[str] = None,
) -> str:
    payload: Dict[str, Any] = {
        "project_id": project_id,
        "list_items": await _load_project_list_items(session, project_id),
        "more_incoming": more_incoming,
    }
    if row_id is not None:
        payload["row_id"] = row_id
    if action is not None:
        payload["action"] = action
    if provider is not None:
        payload["provider"] = provider
    if user_message is not None:
        payload["user_message"] = user_message
    return sse_event("list_items", payload)


class PopChatRequest(BaseModel):
    message: str
    email: Optional[str] = None
    channel: str = "web"
    guest_project_id: Optional[int] = None
    guest_session_token: Optional[str] = None  # HMAC token binding guest to project
    target_project_id: Optional[int] = None
    stream: bool = False


@chat_router.post("/chat")
async def pop_web_chat(
    request: Request,
    body: PopChatRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Web-based chat endpoint for Pop (popsavings.com).
    Returns the assistant reply synchronously instead of sending email/SMS.
    Reuses the same NLU + sourcing pipeline as the webhook flow.
    """
    # Resolve user from auth token ONLY — never trust client-supplied email
    user = await _get_pop_user(request, session)

    if not user:
        # Guest mode — persist to DB under the guest user so the list has a real ID
        guest_stmt = select(User).where(User.email == GUEST_EMAIL)
        guest_result = await session.execute(guest_stmt)
        guest_user = guest_result.scalar_one_or_none()
        if guest_user:
            user = guest_user
        else:
            return {"reply": "Hey! I'm Pop, your grocery savings assistant. Sign up at popsavings.com to save your list!", "list_items": [], "project_id": None}

    is_guest = (user.email == GUEST_EMAIL)

    try:
        project = None

        if is_guest:
            # Guest sessions are cryptographically bound to a project via HMAC token
            if body.guest_project_id and body.guest_session_token:
                if _verify_guest_token(body.guest_project_id, body.guest_session_token):
                    project = await session.get(Project, body.guest_project_id)
                    if project and project.user_id != user.id:
                        project = None  # token valid but project reassigned — start fresh
                else:
                    logger.warning(f"[Pop Web] Invalid guest session token for project {body.guest_project_id}")
                    # Invalid token — don't resume, create new project below
            if not project:
                project = Project(title="My Shopping List", user_id=user.id)
                session.add(project)
                await session.commit()
                await session.refresh(project)
        else:
            # Authenticated users
            if body.target_project_id:
                project = await session.get(Project, body.target_project_id)
                if project and project.user_id != user.id:
                    project = None
            if not project:
                proj_stmt = (
                    select(Project)
                    .where(Project.user_id == user.id)
                    .where(Project.status == "active")
                    .order_by(Project.updated_at.desc())
                    .limit(1)
                )
                proj_result = await session.execute(proj_stmt)
                project = proj_result.scalar_one_or_none()

            if not project:
                project = Project(title="My Shopping List", user_id=user.id)
                session.add(project)
                await session.commit()
                await session.refresh(project)
            else:
                from datetime import datetime
                project.updated_at = datetime.utcnow()
                session.add(project)
                await session.commit()

        await _ensure_project_member(session, project.id, user.id, channel="web")

        # Find active row and load conversation history
        active_row_stmt = (
            select(Row)
            .where(Row.project_id == project.id)
            .where(Row.status == "sourcing")
            .order_by(Row.updated_at.desc())
            .limit(1)
        )
        active_row_result = await session.execute(active_row_stmt)
        active_row = active_row_result.scalar_one_or_none()

        active_row_data = None
        conversation_history = []
        if active_row:
            active_row_data = {
                "id": active_row.id,
                "title": active_row.title or "",
                "constraints": (json.loads(active_row.choice_answers) if isinstance(active_row.choice_answers, str) else active_row.choice_answers) if active_row.choice_answers else {},
                "is_service": active_row.is_service or False,
                "service_category": active_row.service_category,
            }
            conversation_history = _load_chat_history(active_row)

        ctx = ChatContext(
            user_message=body.message,
            conversation_history=conversation_history,
            active_row=active_row_data,
            active_project={"id": project.id, "title": project.title},
            pending_clarification=None,
        )

        # NLU Decision
        decision = await make_pop_decision(ctx)
        logger.info(f"[Pop Web] Decision: action={decision.action}, intent={decision.intent.what}")

        target_row = None
        created_rows = []

        action_type = decision.action.get("type", "")
        intent = decision.intent

        is_service = intent.category == "service"
        service_category = intent.service_type
        title = intent.what[0].upper() + intent.what[1:] if intent.what else intent.what
        search_query = intent.search_query
        _META_KEYS = {
            "what", "is_service", "service_category", "search_query", "title",
            "category", "desire_tier", "desire_confidence",
        }
        constraints = {k: v for k, v in (intent.constraints or {}).items() if k not in _META_KEYS}

        # Multi-item creation: LLM returned an items array
        if decision.items and action_type in ("create_row", "context_switch"):
            for item_data in decision.items:
                item_title = item_data.get("what", "").strip()
                if not item_title:
                    continue
                item_title = item_title[0].upper() + item_title[1:]
                item_query = item_data.get("search_query", f"{item_title} grocery deals")
                row = await _create_row(
                    session, user.id, item_title, project.id,
                    False, None, {}, item_query,
                    desire_tier="commodity",
                    origin_channel="web",
                )
                created_rows.append((row, item_query))
            # Search for deals on each created row
            auth_header = request.headers.get("Authorization")
            for row, q in created_rows:
                try:
                    async for _batch in _stream_search(row.id, q, authorization=auth_header):
                        pass
                    # Build SDUI schema after sourcing
                    await _build_and_persist_ui_schema(session, row, decision.ui_hint)
                except Exception as e:
                    logger.warning(f"[Pop Web] Search failed for row {row.id}: {e}")
            if created_rows:
                target_row = created_rows[-1][0]

        elif action_type in ("create_row", "context_switch") or (action_type == "search" and not active_row):
            row = await _create_row(
                session, user.id, title, project.id,
                is_service, service_category, constraints, search_query,
                desire_tier=intent.desire_tier,
                origin_channel="web",
            )
            target_row = row

            factors = await generate_choice_factors(title, constraints, is_service, service_category)
            if factors:
                await _save_choice_factors(session, row, factors)

            # Trigger sourcing (non-streaming for web response)
            if search_query:
                auth_header = request.headers.get("Authorization")
                try:
                    async for _batch in _stream_search(target_row.id, search_query, authorization=auth_header):
                        pass
                    # Build SDUI schema after sourcing
                    await _build_and_persist_ui_schema(session, target_row, decision.ui_hint)
                except Exception as e:
                    logger.warning(f"[Pop Web] Search failed for row {target_row.id}: {e}")

        elif action_type == "update_row" and active_row:
            row = await _update_row(
                session, active_row,
                title=title if active_row.title != title else None,
                constraints=constraints if constraints else None,
                reset_bids=bool(search_query),
            )
            target_row = row

            if search_query:
                auth_header = request.headers.get("Authorization")
                try:
                    async for _batch in _stream_search(target_row.id, search_query, authorization=auth_header):
                        pass
                    # Build SDUI schema after sourcing
                    await _build_and_persist_ui_schema(session, target_row, decision.ui_hint)
                except Exception as e:
                    logger.warning(f"[Pop Web] Search failed for row {target_row.id}: {e}")

        elif action_type == "delete_row" and active_row:
            active_row.status = "archived"
            session.add(active_row)
            await session.commit()
            target_row = None  # Clear the active row since it's deleted

        if target_row is None and action_type != "delete_row":
            target_row = active_row

        # Persist conversation history
        if target_row:
            await _append_chat_history(session, target_row, body.message, decision.message or "")

        list_items = await _load_project_list_items(session, project.id)

        response_data = {
            "reply": decision.message or "Got it!",
            "list_items": list_items,
            "project_id": project.id,
            "row_id": target_row.id if target_row else None,
            "action": action_type,
        }
        # Include guest session token so the client can resume this project
        if is_guest:
            response_data["guest_session_token"] = _sign_guest_project(project.id)
        return response_data

    except Exception as e:
        logger.error(f"[Pop Web] Failed to process chat: {e}", exc_info=True)
        return {"reply": "Oops, something went wrong. Try again!", "list_items": [], "project_id": None}


@chat_router.post("/chat/stream")
async def pop_web_chat_stream(
    request: Request,
    body: PopChatRequest,
    session: AsyncSession = Depends(get_session),
):
    user = await _get_pop_user(request, session)

    if not user:
        guest_stmt = select(User).where(User.email == GUEST_EMAIL)
        guest_result = await session.execute(guest_stmt)
        guest_user = guest_result.scalar_one_or_none()
        if guest_user:
            user = guest_user

    async def generate_events() -> AsyncGenerator[str, None]:
        if not user:
            yield sse_event("assistant_message", {"text": "Hey! I'm Pop, your grocery savings assistant. Sign up at popsavings.com to save your list!"})
            yield sse_event("done", {"project_id": None, "row_id": None})
            return

        is_guest = (user.email == GUEST_EMAIL)

        try:
            project = None
            if is_guest:
                if body.guest_project_id and body.guest_session_token:
                    if _verify_guest_token(body.guest_project_id, body.guest_session_token):
                        project = await session.get(Project, body.guest_project_id)
                        if project and project.user_id != user.id:
                            project = None
                    else:
                        logger.warning(f"[Pop Web] Invalid guest session token for project {body.guest_project_id}")
                if not project:
                    project = Project(title="My Shopping List", user_id=user.id)
                    session.add(project)
                    await session.commit()
                    await session.refresh(project)
            else:
                if body.target_project_id:
                    project = await session.get(Project, body.target_project_id)
                    if project and project.user_id != user.id:
                        project = None
                if not project:
                    proj_stmt = (
                        select(Project)
                        .where(Project.user_id == user.id)
                        .where(Project.status == "active")
                        .order_by(Project.updated_at.desc())
                        .limit(1)
                    )
                    proj_result = await session.execute(proj_stmt)
                    project = proj_result.scalar_one_or_none()
                if not project:
                    project = Project(title="My Shopping List", user_id=user.id)
                    session.add(project)
                    await session.commit()
                    await session.refresh(project)
                else:
                    from datetime import datetime
                    project.updated_at = datetime.utcnow()
                    session.add(project)
                    await session.commit()

            await _ensure_project_member(session, project.id, user.id, channel="web")

            active_row_stmt = (
                select(Row)
                .where(Row.project_id == project.id)
                .where(Row.status == "sourcing")
                .order_by(Row.updated_at.desc())
                .limit(1)
            )
            active_row_result = await session.execute(active_row_stmt)
            active_row = active_row_result.scalar_one_or_none()

            active_row_data = None
            conversation_history = []
            if active_row:
                active_row_data = {
                    "id": active_row.id,
                    "title": active_row.title or "",
                    "constraints": (json.loads(active_row.choice_answers) if isinstance(active_row.choice_answers, str) else active_row.choice_answers) if active_row.choice_answers else {},
                    "is_service": active_row.is_service or False,
                    "service_category": active_row.service_category,
                }
                conversation_history = _load_chat_history(active_row)

            ctx = ChatContext(
                user_message=body.message,
                conversation_history=conversation_history,
                active_row=active_row_data,
                active_project={"id": project.id, "title": project.title},
                pending_clarification=None,
            )

            decision = await make_pop_decision(ctx)
            logger.info(f"[Pop Web Stream] Decision: action={decision.action}, intent={decision.intent.what}")

            guest_session_token = _sign_guest_project(project.id) if is_guest else None
            yield sse_event("project_ready", {
                "project_id": project.id,
                "guest_session_token": guest_session_token,
            })
            yield sse_event("assistant_message", {"text": decision.message or "Got it!"})

            target_row = None
            created_rows = []
            action_type = decision.action.get("type", "")
            intent = decision.intent
            is_service = intent.category == "service"
            service_category = intent.service_type
            title = intent.what[0].upper() + intent.what[1:] if intent.what else intent.what
            search_query = intent.search_query
            _META_KEYS = {
                "what", "is_service", "service_category", "search_query", "title",
                "category", "desire_tier", "desire_confidence",
            }
            constraints = {k: v for k, v in (intent.constraints or {}).items() if k not in _META_KEYS}
            auth_header = request.headers.get("Authorization")

            async def stream_row_search(row: Row, query: str) -> AsyncGenerator[str, None]:
                async for batch in _stream_search(row.id, query, authorization=auth_header):
                    yield await _build_list_items_event(
                        session,
                        project.id,
                        row_id=row.id,
                        action="search",
                        more_incoming=batch.get("more_incoming", False),
                        provider=batch.get("provider"),
                        user_message=batch.get("user_message") if batch.get("event") == "complete" else None,
                    )
                await _build_and_persist_ui_schema(session, row, decision.ui_hint)
                yield await _build_list_items_event(session, project.id, row_id=row.id, action="search", more_incoming=False)

            if decision.items and action_type in ("create_row", "context_switch"):
                for item_data in decision.items:
                    item_title = item_data.get("what", "").strip()
                    if not item_title:
                        continue
                    item_title = item_title[0].upper() + item_title[1:]
                    item_query = item_data.get("search_query", f"{item_title} grocery deals")
                    row = await _create_row(
                        session, user.id, item_title, project.id,
                        False, None, {}, item_query,
                        desire_tier="commodity",
                        origin_channel="web",
                    )
                    created_rows.append((row, item_query))
                if created_rows:
                    yield await _build_list_items_event(session, project.id, action=action_type, more_incoming=True)
                    for row, query in created_rows:
                        async for event in stream_row_search(row, query):
                            yield event
                    target_row = created_rows[-1][0]

            elif action_type in ("create_row", "context_switch") or (action_type == "search" and not active_row):
                row = await _create_row(
                    session, user.id, title, project.id,
                    is_service, service_category, constraints, search_query,
                    desire_tier=intent.desire_tier,
                    origin_channel="web",
                )
                target_row = row

                factors = await generate_choice_factors(title, constraints, is_service, service_category)
                if factors:
                    await _save_choice_factors(session, row, factors)

                yield await _build_list_items_event(session, project.id, row_id=row.id, action=action_type, more_incoming=bool(search_query))
                if search_query:
                    async for event in stream_row_search(row, search_query):
                        yield event

            elif action_type == "update_row" and active_row:
                row = await _update_row(
                    session, active_row,
                    title=title if active_row.title != title else None,
                    constraints=constraints if constraints else None,
                    reset_bids=bool(search_query),
                )
                target_row = row
                yield await _build_list_items_event(session, project.id, row_id=row.id, action=action_type, more_incoming=bool(search_query))
                if search_query:
                    async for event in stream_row_search(row, search_query):
                        yield event

            elif action_type == "search" and active_row:
                target_row = active_row
                yield await _build_list_items_event(session, project.id, row_id=active_row.id, action=action_type, more_incoming=bool(search_query))
                if search_query:
                    async for event in stream_row_search(active_row, search_query):
                        yield event

            elif action_type == "delete_row" and active_row:
                active_row.status = "archived"
                session.add(active_row)
                await session.commit()
                yield await _build_list_items_event(session, project.id, row_id=active_row.id, action=action_type, more_incoming=False)

            if target_row is None and action_type != "delete_row":
                target_row = active_row

            if target_row:
                await _append_chat_history(session, target_row, body.message, decision.message or "")

            yield await _build_list_items_event(
                session,
                project.id,
                row_id=target_row.id if target_row else None,
                action=action_type,
                more_incoming=False,
            )
            yield sse_event("done", {
                "project_id": project.id,
                "row_id": target_row.id if target_row else None,
                "action": action_type,
                "guest_session_token": guest_session_token,
            })
        except Exception as e:
            logger.error(f"[Pop Web Stream] Failed to process chat: {e}", exc_info=True)
            yield sse_event("error", {"message": "Oops, something went wrong. Try again!"})
            yield sse_event("done", {"project_id": None, "row_id": None})

    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
