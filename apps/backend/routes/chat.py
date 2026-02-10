"""
Chat route — SSE endpoint for the unified chat handler.

Replaces the BFF's POST /api/chat (apps/bff/src/index.ts lines 918-1545).
All backend calls are now direct DB/service calls instead of HTTP round-trips.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from dependencies import get_current_session
from models import Row, RequestSpec, Project
from services.llm import (
    ChatContext,
    UnifiedDecision,
    generate_choice_factors,
    make_unified_decision,
)

router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)

_SELF_BASE_URL = f"http://127.0.0.1:{os.environ.get('PORT', '8000')}"


# =============================================================================
# REQUEST / RESPONSE MODELS
# =============================================================================

class ChatRequest(BaseModel):
    messages: List[Dict[str, Any]]
    activeRowId: Optional[int] = None
    projectId: Optional[int] = None
    pendingClarification: Optional[Dict[str, Any]] = None


# =============================================================================
# SSE HELPERS
# =============================================================================

def sse_event(event: str, data: Any) -> str:
    """Format a single SSE event."""
    return f"event: {event}\ndata: {json.dumps(data if data is not None else None)}\n\n"


def row_to_dict(row: Row) -> dict:
    """Convert a Row model to a JSON-safe dict for SSE events."""
    return {
        "id": row.id,
        "title": row.title,
        "status": row.status,
        "project_id": row.project_id,
        "is_service": row.is_service,
        "service_category": row.service_category,
        "choice_factors": row.choice_factors,
        "choice_answers": row.choice_answers,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


# =============================================================================
# INTERNAL HELPERS (replace BFF HTTP calls with direct DB ops)
# =============================================================================

async def _create_row(
    session: AsyncSession,
    user_id: int,
    title: str,
    project_id: Optional[int],
    is_service: bool,
    service_category: Optional[str],
    constraints: Dict[str, Any],
) -> Row:
    """Create a new Row directly in DB."""
    row = Row(
        title=title,
        status="sourcing",
        user_id=user_id,
        project_id=project_id,
        is_service=is_service,
        service_category=service_category or None,
    )
    session.add(row)
    await session.flush()

    spec = RequestSpec(
        row_id=row.id,
        item_name=title,
        constraints=json.dumps(constraints) if constraints else "{}",
    )
    session.add(spec)

    if constraints:
        row.choice_answers = json.dumps(constraints)

    await session.commit()
    await session.refresh(row)
    return row


async def _update_row(
    session: AsyncSession,
    row: Row,
    title: Optional[str] = None,
    constraints: Optional[Dict[str, Any]] = None,
    reset_bids: bool = False,
) -> Row:
    """Update an existing Row directly in DB."""
    if title:
        row.title = title
    if constraints is not None:
        row.choice_answers = json.dumps(constraints)
    row.updated_at = datetime.utcnow()
    session.add(row)

    # Update request_spec if title or constraints changed
    if title or constraints is not None:
        result = await session.exec(select(RequestSpec).where(RequestSpec.row_id == row.id))
        spec = result.first()
        if spec:
            if title:
                spec.item_name = title
            if constraints is not None:
                spec.constraints = json.dumps(constraints)
            session.add(spec)

    await session.commit()
    await session.refresh(row)
    return row


async def _save_choice_factors(session: AsyncSession, row: Row, factors: list) -> Row:
    """Save generated choice factors to a row."""
    row.choice_factors = json.dumps(factors)
    row.updated_at = datetime.utcnow()
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def _fetch_vendors(
    session: AsyncSession,
    row_id: int,
    service_category: str,
    authorization: Optional[str],
) -> List[Dict[str, Any]]:
    """Fetch vendors for a service category. Uses the outreach route's logic."""
    import httpx

    # Call the backend's own outreach endpoint internally
    # This is simpler than duplicating the vendor logic
    headers: Dict[str, str] = {}
    if authorization:
        headers["Authorization"] = authorization

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{_SELF_BASE_URL}/outreach/vendors/{service_category}",
                headers=headers,
                timeout=15.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                vendors = data.get("vendors", [])
                if vendors:
                    # Persist vendors as bids
                    await client.post(
                        f"{_SELF_BASE_URL}/outreach/rows/{row_id}/vendors",
                        headers={**headers, "Content-Type": "application/json"},
                        json={"category": service_category, "vendors": vendors},
                        timeout=10.0,
                    )
                return vendors
    except Exception as e:
        logger.error(f"Failed to fetch vendors: {e}")

    return []


async def _stream_search(
    row_id: int,
    query: str,
    authorization: Optional[str],
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Stream search results from the backend's own search/stream endpoint.
    Yields dicts with provider, results, status, more_incoming.
    """
    import httpx

    headers: Dict[str, str] = {"Content-Type": "application/json"}
    if authorization:
        headers["Authorization"] = authorization

    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            f"{_SELF_BASE_URL}/rows/{row_id}/search/stream",
            headers=headers,
            json={"query": query},
            timeout=60.0,
        ) as resp:
            buffer = ""
            async for chunk in resp.aiter_text():
                buffer += chunk
                lines = buffer.split("\n")
                buffer = lines.pop()  # keep incomplete line

                for line in lines:
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            yield data
                        except json.JSONDecodeError:
                            pass


# =============================================================================
# MAIN CHAT ENDPOINT
# =============================================================================

@router.post("/api/chat")
async def chat_endpoint(
    body: ChatRequest,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """
    Unified chat endpoint — SSE stream.
    Replaces BFF's POST /api/chat entirely.
    """
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = auth_session.user_id

    async def generate_events() -> AsyncGenerator[str, None]:
        try:
            messages = body.messages or []
            active_row_id = body.activeRowId
            project_id = body.projectId
            pending_clarification = body.pendingClarification

            # Extract last user message
            last_user_msg = None
            for m in reversed(messages):
                if m.get("role") == "user":
                    last_user_msg = m
                    break

            user_message = ""
            if last_user_msg:
                content = last_user_msg.get("content", "")
                if isinstance(content, str):
                    user_message = content
                elif isinstance(content, dict):
                    user_message = content.get("text", "")

            # Build conversation history
            conversation_history = [
                {
                    "role": m["role"],
                    "content": m["content"] if isinstance(m["content"], str) else m.get("content", {}).get("text", ""),
                }
                for m in messages
                if m.get("role") in ("user", "assistant")
            ]

            # Fetch active row if present
            active_row_data = None
            if active_row_id:
                result = await session.exec(
                    select(Row).where(Row.id == active_row_id, Row.user_id == user_id)
                )
                active_row = result.first()
                if active_row:
                    choice_answers = {}
                    if active_row.choice_answers:
                        try:
                            choice_answers = json.loads(active_row.choice_answers)
                        except Exception:
                            pass
                    active_row_data = {
                        "id": active_row_id,
                        "title": active_row.title or "",
                        "constraints": choice_answers,
                        "is_service": active_row.is_service or False,
                        "service_category": active_row.service_category,
                    }

            # Fetch project if present
            active_project_data = None
            if project_id:
                proj = await session.get(Project, project_id)
                if proj:
                    active_project_data = {"id": project_id, "title": proj.title or ""}

            # === SINGLE LLM DECISION ===
            ctx = ChatContext(
                user_message=user_message,
                conversation_history=conversation_history,
                active_row=active_row_data,
                active_project=active_project_data,
                pending_clarification=pending_clarification,
            )

            logger.info(f"Making unified decision: msg={user_message!r}, activeRow={active_row_id}, pending={bool(pending_clarification)}")
            decision = await make_unified_decision(ctx)

            intent = decision.intent
            action = decision.action
            action_type = action.get("type", "")

            logger.info(f"Decision: action={action_type}, intent.what={intent.what}, intent.category={intent.category}")

            # Send assistant message
            yield sse_event("assistant_message", {"text": decision.message})

            # === INTENT-DRIVEN HELPERS ===
            is_service = intent.category == "service"
            service_category = intent.service_type
            title = intent.what[0].upper() + intent.what[1:] if intent.what else intent.what
            search_query = intent.search_query
            # Strip meta-fields that LLM may accidentally put in constraints
            _META_KEYS = {"what", "is_service", "service_category", "search_query", "title", "category"}
            constraints = {k: v for k, v in (intent.constraints or {}).items() if k not in _META_KEYS}

            # === HANDLE EACH ACTION TYPE ===

            if action_type == "ask_clarification":
                yield sse_event("needs_clarification", {
                    "type": "clarification",
                    "service_type": service_category,
                    "title": title,
                    "partial_constraints": constraints,
                    "missing_fields": action.get("missing_fields", []),
                })
                yield sse_event("done", {})
                return

            if action_type == "disambiguate":
                yield sse_event("disambiguate", {
                    "options": action.get("options", []),
                    "title": title,
                })
                yield sse_event("done", {})
                return

            # --- CREATE ROW (also used for context_switch) ---
            if action_type in ("create_row", "context_switch"):
                event_name = "context_switch" if action_type == "context_switch" else "row_created"

                yield sse_event("action_started", {"type": "create_row", "title": title})
                row = await _create_row(
                    session, user_id, title, project_id,
                    is_service, service_category, constraints,
                )
                yield sse_event(event_name, {"row": row_to_dict(row)})

                # Generate choice factors
                factors = await generate_choice_factors(
                    title, constraints, is_service, service_category,
                )
                if factors:
                    row = await _save_choice_factors(session, row, factors)
                yield sse_event("factors_updated", {"row": row_to_dict(row)})

                # For services, fetch vendors. For products, search.
                if is_service and service_category:
                    yield sse_event("action_started", {"type": "fetch_vendors", "row_id": row.id, "category": service_category})
                    vendors = await _fetch_vendors(session, row.id, service_category, authorization)
                    yield sse_event("vendors_loaded", {
                        "row_id": row.id,
                        "category": service_category,
                        "vendors": vendors,
                    })
                else:
                    # Product search
                    yield sse_event("action_started", {"type": "search", "row_id": row.id, "query": search_query})
                    async for batch in _stream_search(row.id, search_query, authorization):
                        if batch.get("event") == "complete":
                            if batch.get("user_message"):
                                yield sse_event("search_results", {
                                    "row_id": row.id,
                                    "results": [],
                                    "more_incoming": False,
                                    "user_message": batch["user_message"],
                                })
                        else:
                            yield sse_event("search_results", {
                                "row_id": row.id,
                                "results": batch.get("results", []),
                                "provider_statuses": [batch.get("status")] if batch.get("status") else [],
                                "more_incoming": batch.get("more_incoming", False),
                                "provider": batch.get("provider"),
                            })

                yield sse_event("done", {})
                return

            # --- UPDATE ROW ---
            if action_type == "update_row":
                if not active_row_id:
                    # No row exists yet (e.g. after ask_clarification).
                    # Promote to create_row — we have everything we need.
                    logger.info("update_row with no active row — promoting to create_row")
                    yield sse_event("action_started", {"type": "create_row", "title": title})
                    row = await _create_row(
                        session, user_id, title, project_id,
                        is_service, service_category, constraints,
                    )
                    yield sse_event("row_created", {"row": row_to_dict(row)})

                    factors = await generate_choice_factors(
                        title, constraints, is_service, service_category,
                    )
                    if factors:
                        row = await _save_choice_factors(session, row, factors)
                    yield sse_event("factors_updated", {"row": row_to_dict(row)})

                    if is_service and service_category:
                        yield sse_event("action_started", {"type": "fetch_vendors", "row_id": row.id, "category": service_category})
                        vendors = await _fetch_vendors(session, row.id, service_category, authorization)
                        yield sse_event("vendors_loaded", {"row_id": row.id, "category": service_category, "vendors": vendors})
                    else:
                        yield sse_event("action_started", {"type": "search", "row_id": row.id, "query": search_query})
                        async for batch in _stream_search(row.id, search_query, authorization):
                            if batch.get("event") == "complete":
                                if batch.get("user_message"):
                                    yield sse_event("search_results", {"row_id": row.id, "results": [], "more_incoming": False, "user_message": batch["user_message"]})
                            else:
                                yield sse_event("search_results", {"row_id": row.id, "results": batch.get("results", []), "provider_statuses": [batch.get("status")] if batch.get("status") else [], "more_incoming": batch.get("more_incoming", False), "provider": batch.get("provider")})

                    yield sse_event("done", {})
                    return

                result = await session.exec(
                    select(Row).where(Row.id == active_row_id, Row.user_id == user_id)
                )
                row = result.first()
                if not row:
                    yield sse_event("error", {"message": "Row not found"})
                    yield sse_event("done", {})
                    return

                title_changed = (row.title or "").strip().lower() != title.strip().lower()
                existing_constraints = {}
                if row.choice_answers:
                    try:
                        existing_constraints = json.loads(row.choice_answers)
                    except Exception:
                        pass

                next_constraints = dict(constraints) if title_changed else {**existing_constraints, **constraints}

                yield sse_event("action_started", {"type": "update_row", "row_id": active_row_id})
                row = await _update_row(
                    session, row,
                    title=title if title_changed else None,
                    constraints=next_constraints if constraints else None,
                    reset_bids=title_changed,
                )
                yield sse_event("row_updated", {"row": row_to_dict(row)})

                # Regenerate factors if needed
                if title_changed or constraints:
                    row_is_service = is_service or (active_row_data or {}).get("is_service", False)
                    row_service_cat = service_category or (active_row_data or {}).get("service_category")
                    factors = await generate_choice_factors(
                        title, next_constraints, row_is_service, row_service_cat,
                    )
                    if factors:
                        row = await _save_choice_factors(session, row, factors)
                    yield sse_event("factors_updated", {"row": row_to_dict(row)})

                # Search or vendor fetch
                row_is_service = is_service or (active_row_data or {}).get("is_service", False)
                row_service_cat = service_category or (active_row_data or {}).get("service_category")

                if row_is_service and row_service_cat:
                    yield sse_event("action_started", {"type": "fetch_vendors", "row_id": active_row_id, "category": row_service_cat})
                    vendors = await _fetch_vendors(session, active_row_id, row_service_cat, authorization)
                    yield sse_event("vendors_loaded", {
                        "row_id": active_row_id,
                        "category": row_service_cat,
                        "vendors": vendors,
                    })
                elif search_query:
                    yield sse_event("action_started", {"type": "search", "row_id": active_row_id, "query": search_query})
                    async for batch in _stream_search(active_row_id, search_query, authorization):
                        if batch.get("event") == "complete":
                            if batch.get("user_message"):
                                yield sse_event("search_results", {
                                    "row_id": active_row_id,
                                    "results": [],
                                    "more_incoming": False,
                                    "user_message": batch["user_message"],
                                })
                        else:
                            yield sse_event("search_results", {
                                "row_id": active_row_id,
                                "results": batch.get("results", []),
                                "provider_statuses": [batch.get("status")] if batch.get("status") else [],
                                "more_incoming": batch.get("more_incoming", False),
                                "provider": batch.get("provider"),
                            })

                yield sse_event("done", {})
                return

            # --- SEARCH (on existing row) ---
            if action_type == "search":
                if not active_row_id:
                    # No row exists — create one first, then search
                    logger.info("search with no active row — creating row first")
                    yield sse_event("action_started", {"type": "create_row", "title": title})
                    row = await _create_row(
                        session, user_id, title, project_id,
                        is_service, service_category, constraints,
                    )
                    yield sse_event("row_created", {"row": row_to_dict(row)})
                    active_row_id = row.id

                    factors = await generate_choice_factors(
                        title, constraints, is_service, service_category,
                    )
                    if factors:
                        row = await _save_choice_factors(session, row, factors)
                    yield sse_event("factors_updated", {"row": row_to_dict(row)})

                yield sse_event("action_started", {"type": "search", "row_id": active_row_id, "query": search_query})
                async for batch in _stream_search(active_row_id, search_query, authorization):
                    if batch.get("event") == "complete":
                        if batch.get("user_message"):
                            yield sse_event("search_results", {
                                "row_id": active_row_id,
                                "results": [],
                                "more_incoming": False,
                                "user_message": batch["user_message"],
                            })
                    else:
                        yield sse_event("search_results", {
                            "row_id": active_row_id,
                            "results": batch.get("results", []),
                            "provider_statuses": [batch.get("status")] if batch.get("status") else [],
                            "more_incoming": batch.get("more_incoming", False),
                            "provider": batch.get("provider"),
                        })

                yield sse_event("done", {})
                return

            # --- VENDOR OUTREACH ---
            if action_type == "vendor_outreach":
                if not active_row_id:
                    yield sse_event("error", {"message": "No active row for vendor outreach"})
                    yield sse_event("done", {})
                    return

                category = service_category or (active_row_data or {}).get("service_category") or "service"
                yield sse_event("action_started", {"type": "vendor_outreach", "row_id": active_row_id, "category": category})
                yield sse_event("vendor_outreach", {"row_id": active_row_id, "category": category})
                yield sse_event("done", {})
                return

            # Fallback
            yield sse_event("done", {})

        except Exception as e:
            logger.error(f"Chat error: {e}", exc_info=True)
            yield sse_event("error", {"message": str(e) or "Chat processing failed"})
            yield sse_event("done", {})

    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
