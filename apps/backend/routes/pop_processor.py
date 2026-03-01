"""Core Pop message processor: NLU → row CRUD → sourcing → reply."""

import json
import logging
import re
from typing import Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models.rows import Row, Project
from models.auth import User
from services.llm import make_pop_decision, ChatContext, generate_choice_factors
from routes.chat import _create_row, _update_row, _save_choice_factors, _stream_search
from routes.pop_helpers import (
    POP_DOMAIN,
    _ensure_project_member,
    _load_chat_history,
    _append_chat_history,
)
from routes.pop_notify import (
    send_pop_reply,
    send_pop_sms,
    send_pop_onboarding_email,
    send_pop_onboarding_sms,
)

logger = logging.getLogger(__name__)


async def process_pop_message(
    user_email: str,
    message_text: str,
    session: AsyncSession,
    channel: str = "email",
    sender_phone: Optional[str] = None,
):
    """
    Core logic for Pop:
    1. Identify user (or trigger onboarding)
    2. Identify or create their active Family List (Project)
    3. Load conversation history from Row.chat_history
    4. Use Unified NLU Decision Engine
    5. Create/Update Rows and trigger sourcing
    6. Persist conversation history
    7. Reply to user via email or SMS (based on channel)
    """
    try:
        # 1. Find User
        statement = select(User).where(User.email == user_email)
        result = await session.execute(statement)
        user = result.scalar_one_or_none()

        if not user:
            logger.info(f"[Pop] Unknown user {user_email}. Sending onboarding.")
            if channel == "sms" and sender_phone:
                send_pop_onboarding_sms(sender_phone)
            else:
                await send_pop_onboarding_email(user_email)
            return

        # 1b. Extract zip_code from message if user hasn't set one yet
        if not user.zip_code:
            zip_match = re.search(r'\b(\d{5})(?:-\d{4})?\b', message_text)
            if zip_match:
                user.zip_code = zip_match.group(1)
                session.add(user)
                await session.commit()
                await session.refresh(user)
                logger.info(f"[Pop] Saved zip_code {user.zip_code} for user {user.id}")

        # 2. Find active Pop project (Family List)
        proj_stmt = (
            select(Project)
            .where(Project.user_id == user.id)
            .where(Project.title == "Family Shopping List")
            .where(Project.status == "active")
        )
        proj_result = await session.execute(proj_stmt)
        project = proj_result.scalar_one_or_none()

        if not project:
            project = Project(title="Family Shopping List", user_id=user.id)
            session.add(project)
            await session.commit()
            await session.refresh(project)

        # Register user as project member (tracks channel preference)
        await _ensure_project_member(session, project.id, user.id, channel=channel)

        # 3. Find active row and load conversation history
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
            user_message=message_text,
            conversation_history=conversation_history,
            active_row=active_row_data,
            active_project={"id": project.id, "title": project.title},
            pending_clarification=None,
        )

        # 4. NLU Decision
        decision = await make_pop_decision(ctx)
        logger.info(f"[Pop] Decision: action={decision.action}, intent={decision.intent.what}")

        target_row = None
        title = ""

        action_type = decision.action.get("type", "")
        intent = decision.intent

        is_service = intent.category == "service"
        service_category = intent.service_type
        title = intent.what[0].upper() + intent.what[1:] if intent.what else intent.what
        search_query = intent.search_query
        exclude_keywords = intent.exclude_keywords or []
        exclude_merchants = intent.exclude_merchants or []
        _META_KEYS = {
            "what", "is_service", "service_category", "search_query", "title",
            "category", "desire_tier", "desire_confidence",
            "exclude_keywords", "exclude_merchants",
        }
        constraints = {k: v for k, v in (intent.constraints or {}).items() if k not in _META_KEYS}

        # 5. Create or Update Row based on intent
        if action_type in ("create_row", "context_switch") or (action_type == "search" and not active_row):
            row = await _create_row(
                session, user.id, title, project.id,
                is_service, service_category, constraints, search_query,
                desire_tier=intent.desire_tier,
                exclude_keywords=exclude_keywords,
                exclude_merchants=exclude_merchants,
            )
            target_row = row

            factors = await generate_choice_factors(title, constraints, is_service, service_category)
            if factors:
                await _save_choice_factors(session, row, factors)

        elif action_type == "update_row" and active_row:
            row = await _update_row(
                session, active_row,
                title=title if active_row.title != title else None,
                constraints=constraints if constraints else None,
                reset_bids=bool(search_query),
            )
            target_row = row

        # Trigger sourcing
        if search_query and target_row:
            async for _batch in _stream_search(target_row.id, search_query, authorization=None):
                pass

        # If no row was created/updated, use active_row for history persistence
        if target_row is None:
            target_row = active_row

        # 6. Persist conversation history on the row
        if target_row:
            await _append_chat_history(session, target_row, message_text, decision.message or "")

        # 7. Reply to user via the same channel they used
        reply_message = f"{decision.message}\n\nView your list: {POP_DOMAIN}/list/{project.id}"
        reply_subject = f"Re: {title}" if title else "Your shopping list update"

        if channel == "sms" and sender_phone:
            ok = send_pop_sms(sender_phone, reply_message)
            if ok:
                logger.info(f"[Pop] SMS reply sent to {sender_phone}")
            else:
                logger.warning(f"[Pop] SMS reply failed for {sender_phone}")
        else:
            email_result = await send_pop_reply(user_email, reply_subject, reply_message)
            if email_result.success:
                logger.info(f"[Pop] Email reply sent to {user_email} (id={email_result.message_id})")
            else:
                logger.warning(f"[Pop] Email reply failed for {user_email}: {email_result.error}")

    except Exception as e:
        logger.error(f"[Pop] Failed to process message: {e}", exc_info=True)
