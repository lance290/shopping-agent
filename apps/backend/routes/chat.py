"""
Chat route — SSE endpoint for the unified chat handler.

Replaces the BFF's POST /api/chat (apps/bff/src/index.ts lines 918-1545).
All backend calls are now direct DB/service calls instead of HTTP round-trips.
Helpers extracted to routes/chat_helpers.py.
"""

import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from dependencies import get_current_session, resolve_user_id
from models.rows import Row, Project
from models.auth import User
from utils.json_utils import safe_json_loads
from services.llm import (
    ChatContext,
    UnifiedDecision,
    generate_choice_factors,
    make_unified_decision,
)

# Helpers extracted to chat_helpers.py — re-exported for backward compatibility
from routes.chat_helpers import (  # noqa: F401
    sse_event,
    sse_ui_schema_event,
    row_to_dict,
    _build_and_persist_ui_schema,
    _build_search_intent_json,
    _create_row,
    _update_row,
    _save_choice_factors,
    _stream_search,
)

router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)


# =============================================================================
# REQUEST / RESPONSE MODELS
# =============================================================================

class ChatRequest(BaseModel):
    messages: List[Dict[str, Any]]
    activeRowId: Optional[int] = None
    projectId: Optional[int] = None
    pendingClarification: Optional[Dict[str, Any]] = None


# =============================================================================
# MAIN CHAT ENDPOINT
# =============================================================================

@router.post("/api/chat")
async def chat_endpoint(
    body: ChatRequest,
    authorization: Optional[str] = Header(None),
    x_anonymous_session_id: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """
    Unified chat endpoint — SSE stream.
    Replaces BFF's POST /api/chat entirely.
    """
    user_id = await resolve_user_id(authorization, session)

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
                        choice_answers = safe_json_loads(active_row.choice_answers, {})
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
            _META_KEYS = {"what", "is_service", "service_category", "search_query", "title", "category", "desire_tier", "desire_confidence"}
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

            # --- MULTI-ITEM / LIST CREATION ---
            if decision.items and action_type in ("create_row", "context_switch"):
                # If there's no project yet, create one for this list
                if not project_id:
                    proj_title = decision.project_title or "Shopping List"
                    new_proj = Project(title=proj_title, user_id=user_id)
                    session.add(new_proj)
                    await session.commit()
                    await session.refresh(new_proj)
                    project_id = new_proj.id

                created_rows = []
                for item_data in decision.items:
                    item_title = item_data.get("what", "").strip()
                    if not item_title:
                        continue
                    item_title = item_title[0].upper() + item_title[1:]
                    item_query = item_data.get("search_query", item_title)
                    item_tier = item_data.get("desire_tier", "commodity")
                    
                    row = await _create_row(
                        session, user_id, item_title, project_id,
                        False, None, {}, item_query,
                        desire_tier=item_tier,
                        anonymous_session_id=x_anonymous_session_id,
                    )
                    created_rows.append((row, item_query, item_tier))
                    yield sse_event("row_created", {"row": row_to_dict(row)})

                # Search for deals on each created row sequentially
                for row, q, tier in created_rows:
                    yield sse_event("action_started", {"type": "search", "row_id": row.id, "query": q})
                    async for batch in _stream_search(row.id, q, authorization):
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

                    # Build and emit SDUI schema after search completes
                    schema = await _build_and_persist_ui_schema(session, row, decision.ui_hint)
                    if schema:
                        yield sse_ui_schema_event(row.id, schema, row.ui_schema_version, "search_complete")

                yield sse_event("done", {})
                return

            # --- CREATE ROW (also used for context_switch) ---
            if action_type in ("create_row", "context_switch"):
                event_name = "context_switch" if action_type == "context_switch" else "row_created"
                tier = decision.desire_tier

                yield sse_event("action_started", {"type": "create_row", "title": title})
                row = await _create_row(
                    session, user_id, title, project_id,
                    is_service, service_category, constraints, search_query,
                    desire_tier=tier,
                    anonymous_session_id=x_anonymous_session_id,
                )
                yield sse_event(event_name, {"row": row_to_dict(row)})
                yield sse_event("desire_tier_classified", {
                    "row_id": row.id,
                    "desire_tier": tier,
                    "desire_confidence": intent.desire_confidence,
                    "skip_web_search": decision.skip_web_search,
                })

                # Generate choice factors
                factors = await generate_choice_factors(
                    title, constraints, is_service, service_category,
                )
                if factors:
                    row = await _save_choice_factors(session, row, factors)
                yield sse_event("factors_updated", {"row": row_to_dict(row)})

                # Search — tier filtering happens inside the search pipeline
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

                # Build and emit SDUI schema after search completes
                schema = await _build_and_persist_ui_schema(session, row, decision.ui_hint)
                if schema:
                    yield sse_ui_schema_event(row.id, schema, row.ui_schema_version, "search_complete")

                yield sse_event("done", {})
                return

            # --- UPDATE ROW ---
            if action_type == "update_row":
                tier = decision.desire_tier

                if not active_row_id:
                    # No row exists yet (e.g. after ask_clarification).
                    # Promote to create_row — we have everything we need.
                    logger.info("update_row with no active row — promoting to create_row")
                    yield sse_event("action_started", {"type": "create_row", "title": title})
                    row = await _create_row(
                        session, user_id, title, project_id,
                        is_service, service_category, constraints, search_query,
                        desire_tier=tier,
                        anonymous_session_id=x_anonymous_session_id,
                    )
                    yield sse_event("row_created", {"row": row_to_dict(row)})
                    yield sse_event("desire_tier_classified", {
                        "row_id": row.id,
                        "desire_tier": tier,
                        "desire_confidence": intent.desire_confidence,
                        "skip_web_search": decision.skip_web_search,
                    })

                    factors = await generate_choice_factors(
                        title, constraints, is_service, service_category,
                    )
                    if factors:
                        row = await _save_choice_factors(session, row, factors)
                    yield sse_event("factors_updated", {"row": row_to_dict(row)})

                    yield sse_event("action_started", {"type": "search", "row_id": row.id, "query": search_query})
                    async for batch in _stream_search(row.id, search_query, authorization):
                        if batch.get("event") == "complete":
                            if batch.get("user_message"):
                                yield sse_event("search_results", {"row_id": row.id, "results": [], "more_incoming": False, "user_message": batch["user_message"]})
                        else:
                            yield sse_event("search_results", {"row_id": row.id, "results": batch.get("results", []), "provider_statuses": [batch.get("status")] if batch.get("status") else [], "more_incoming": batch.get("more_incoming", False), "provider": batch.get("provider")})

                    # Build and emit SDUI schema
                    schema = await _build_and_persist_ui_schema(session, row, decision.ui_hint)
                    if schema:
                        yield sse_ui_schema_event(row.id, schema, row.ui_schema_version, "search_complete")

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
                    existing_constraints = safe_json_loads(row.choice_answers, {})

                next_constraints = dict(constraints) if title_changed else {**existing_constraints, **constraints}

                # Update desire_tier on the row
                row.desire_tier = tier
                row.structured_constraints = json.dumps(next_constraints) if next_constraints else row.structured_constraints

                yield sse_event("action_started", {"type": "update_row", "row_id": active_row_id})
                row = await _update_row(
                    session, row,
                    title=title if title_changed else None,
                    constraints=next_constraints if constraints else None,
                    reset_bids=title_changed,
                )
                # Refresh search_intent so scorer has current relevance data
                row_service_cat_for_intent = service_category or (active_row_data or {}).get("service_category")
                row.search_intent = _build_search_intent_json(
                    row.title, search_query or row.title, next_constraints, row_service_cat_for_intent,
                )
                session.add(row)
                await session.commit()
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

                # Search — tier filtering happens inside the search pipeline
                if search_query:
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

                    # Build and emit SDUI schema
                    schema = await _build_and_persist_ui_schema(session, row, decision.ui_hint)
                    if schema:
                        yield sse_ui_schema_event(row.id, schema, row.ui_schema_version, "search_complete")

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
                        is_service, service_category, constraints, search_query,
                        desire_tier=decision.desire_tier,
                        anonymous_session_id=x_anonymous_session_id,
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
