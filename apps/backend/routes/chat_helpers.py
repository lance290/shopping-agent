"""
Chat helpers — SSE formatting, row CRUD, search streaming, SDUI schema.
Shared by routes/chat.py and routes/pop_chat.py / pop_processor.py.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models.rows import Row, Project
from models.bids import Bid
from models import RequestSpec
from sourcing.location import resolve_location_context
from utils.json_utils import safe_json_loads
from services.sdui_builder import build_ui_schema

logger = logging.getLogger(__name__)


def _get_self_base_url() -> str:
    # First respect an explicit self call URL (useful for production/railway)
    explicit_url = os.environ.get("SELF_BASE_URL")
    if explicit_url:
        return explicit_url.rstrip("/")
        
    port = os.environ.get("PORT")
    if not port:
        import sys
        args = sys.argv
        for i, arg in enumerate(args):
            if arg == "--port" and i + 1 < len(args):
                port = args[i + 1]
                break
            if arg.startswith("--port="):
                port = arg.split("=", 1)[1]
                break
    return f"http://127.0.0.1:{port or '8000'}"

_SELF_BASE_URL = _get_self_base_url()


# =============================================================================
# SSE HELPERS
# =============================================================================

def sse_event(event: str, data: Any) -> str:
    """Format a single SSE event."""
    return f"event: {event}\ndata: {json.dumps(data if data is not None else None)}\n\n"


async def _build_and_persist_ui_schema(
    session: AsyncSession, row: Row, ui_hint_data=None
) -> Optional[dict]:
    """Build SDUI schema from bids and persist on the Row. Returns schema dict or None."""
    try:
        result = await session.exec(
            select(Bid).where(Bid.row_id == row.id).order_by(Bid.combined_score.desc().nullslast()).limit(30)
        )
        bids = list(result.all())
        schema = build_ui_schema(ui_hint_data, row, bids)
        row.ui_schema = schema
        row.ui_schema_version = (getattr(row, "ui_schema_version", 0) or 0) + 1
        session.add(row)
        await session.commit()
        return schema
    except Exception as e:
        logger.warning(f"[Chat] Failed to build ui_schema for row {row.id}: {e}")
        return None


def sse_ui_schema_event(row_id: int, schema: dict, version: int, trigger: str) -> str:
    """Emit a ui_schema_updated SSE event per Schema Spec §9."""
    return sse_event("ui_schema_updated", {
        "entity_type": "row",
        "entity_id": row_id,
        "schema": schema,
        "version": version,
        "trigger": trigger,
    })


def row_to_dict(row: Row) -> dict:
    """Convert a Row model to a JSON-safe dict for SSE events."""
    return {
        "id": row.id,
        "title": row.title,
        "status": row.status,
        "project_id": row.project_id,
        "is_service": row.is_service,
        "service_category": row.service_category,
        "desire_tier": row.desire_tier,
        "choice_factors": row.choice_factors,
        "choice_answers": row.choice_answers,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


# =============================================================================
# INTERNAL HELPERS (replace BFF HTTP calls with direct DB ops)
# =============================================================================

def _build_search_intent_json(title: str, search_query: str, constraints: Dict[str, Any], service_category: Optional[str]) -> dict:
    """Build a SearchIntent JSON from LLM intent fields so the scorer can rank by relevance."""
    # Extract keywords from the title (the core "what")
    stop_words = {"a", "an", "the", "for", "my", "i", "me", "to", "and", "or", "of", "in", "on", "with"}
    keywords = [w for w in title.lower().split() if w not in stop_words and len(w) > 1]

    location_context = resolve_location_context(
        service_category=service_category,
        desire_tier=None,
        constraints=constraints,
        features=constraints,
    )
    intent_data = {
        "product_category": service_category or title.lower().replace(" ", "_"),
        "product_name": title,
        "brand": constraints.get("brand") or constraints.get("preferred_brand"),
        "keywords": keywords,
        "min_price": constraints.get("min_price"),
        "max_price": constraints.get("max_price") or constraints.get("budget") or constraints.get("max_budget"),
        "raw_input": search_query or title,
        "features": {k: v for k, v in constraints.items()
                     if k not in ("brand", "preferred_brand", "min_price", "max_price", "budget", "max_budget")
                     and v is not None and str(v).lower() != "not answered"},
        "location_context": location_context.model_dump(),
        "location_resolution": {},
    }
    # Remove None values
    intent_data = {k: v for k, v in intent_data.items() if v is not None}
    return intent_data


async def _create_row(
    session: AsyncSession,
    user_id: int,
    title: str,
    project_id: Optional[int],
    is_service: bool,
    service_category: Optional[str],
    constraints: Dict[str, Any],
    search_query: Optional[str] = None,
    desire_tier: Optional[str] = None,
    anonymous_session_id: Optional[str] = None,
    origin_channel: Optional[str] = None,
) -> Row:
    """Create a new Row directly in DB."""
    row = Row(
        title=title,
        status="sourcing",
        user_id=user_id,
        project_id=project_id,
        is_service=is_service,
        service_category=service_category or None,
        desire_tier=desire_tier,
        structured_constraints=json.dumps(constraints) if constraints else None,
        search_intent=_build_search_intent_json(title, search_query or title, constraints, service_category),
        anonymous_session_id=anonymous_session_id,
        origin_channel=origin_channel,
        origin_user_id=user_id,
    )
    session.add(row)
    await session.flush()

    spec = RequestSpec(
        row_id=row.id,
        item_name=title,
        constraints=json.dumps(constraints) if constraints else "{}",
    )
    session.add(spec)

    row.choice_answers = constraints if constraints else {}

    await session.commit()
    await session.refresh(row)
    return row


async def _update_row(
    session: AsyncSession,
    row: Row,
    title: Optional[str] = None,
    constraints: Optional[Dict[str, Any]] = None,
    search_query: Optional[str] = None,
    is_service: Optional[bool] = None,
    service_category: Optional[str] = None,
    desire_tier: Optional[str] = None,
    reset_bids: bool = False,
) -> Row:
    """Update an existing Row directly in DB."""
    if reset_bids:
        from sqlalchemy import update as sql_update
        await session.exec(
            sql_update(Bid).where(
                Bid.row_id == row.id,
                Bid.is_liked == False,
                Bid.is_selected == False,
                Bid.is_superseded == False,
            ).values(is_superseded=True, superseded_at=datetime.utcnow())
        )
    if title:
        row.title = title
    if constraints is not None:
        row.choice_answers = constraints
        row.structured_constraints = json.dumps(constraints) if constraints else None
    if is_service is not None:
        row.is_service = is_service
    if service_category is not None:
        row.service_category = service_category
    if desire_tier is not None:
        row.desire_tier = desire_tier
    if title or constraints is not None or service_category is not None:
        effective_title = row.title or title or "Shopping Request"
        effective_query = search_query or effective_title
        effective_constraints = constraints if constraints is not None else safe_json_loads(row.choice_answers, {}) if row.choice_answers else {}
        effective_service_category = row.service_category
        row.search_intent = _build_search_intent_json(
            effective_title,
            effective_query,
            effective_constraints if isinstance(effective_constraints, dict) else {},
            effective_service_category,
        )
    if reset_bids:
        row.ui_schema = None  # Invalidate SDUI schema — rebuilt after next search
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
    row.choice_factors = factors
    row.updated_at = datetime.utcnow()
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


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
