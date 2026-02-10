"""
Enriched search route — replaces the BFF's POST /api/search.

The BFF used to:
1. Fetch the row from backend
2. Call triageProviderQuery() to optimize the search query
3. Call extractSearchIntent() to build structured intent
4. Patch the row with provider_query
5. Call POST /rows/{rowId}/search with enriched data

Now this happens in-process, eliminating the HTTP round-trips.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from dependencies import get_current_session
from models import Row, RequestSpec, Project
from services.intent import extract_search_intent
from services.llm import triage_provider_query

router = APIRouter(tags=["search"])
logger = logging.getLogger(__name__)


class EnrichedSearchRequest(BaseModel):
    rowId: Optional[int] = None
    query: Optional[str] = None
    providers: Optional[List[str]] = None
    choice_answers: Optional[str] = None
    request_spec: Optional[Dict[str, Any]] = None


@router.post("/api/search")
async def enriched_search(
    body: EnrichedSearchRequest,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """
    Enriched search endpoint — adds intent extraction and provider query triage
    before delegating to the existing /rows/{rowId}/search.
    """
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    row_id = body.rowId
    if not row_id:
        raise HTTPException(status_code=400, detail="rowId is required")

    # Fetch the row
    result = await session.exec(
        select(Row).where(Row.id == row_id, Row.user_id == auth_session.user_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")

    # Fetch project title if available
    project_title: Optional[str] = None
    if row.project_id:
        proj = await session.get(Project, row.project_id)
        if proj:
            project_title = proj.title

    # Determine display query
    client_provided_query = isinstance(body.query, str) and body.query.strip()
    display_query = body.query if client_provided_query else (row.title or "")

    # Fetch request spec for constraints
    spec_result = await session.exec(select(RequestSpec).where(RequestSpec.row_id == row_id))
    spec = spec_result.first()
    constraints_json = spec.constraints if spec else None

    # Enrich: triage provider query
    provider_query = await triage_provider_query(
        display_query=display_query,
        row_title=row.title,
        project_title=project_title,
        choice_answers_json=row.choice_answers,
        request_spec_constraints_json=constraints_json,
    )
    safe_provider_query = provider_query or display_query

    # Enrich: extract search intent
    intent_result = await extract_search_intent(
        display_query=display_query,
        row_title=row.title,
        project_title=project_title,
        choice_answers_json=row.choice_answers,
        request_spec_constraints_json=constraints_json,
    )

    # Patch row with provider_query
    row.provider_query = safe_provider_query
    session.add(row)
    await session.commit()

    # Now delegate to the existing search logic via internal import
    from routes.rows_search import (
        RowSearchRequest,
        search_row_listings,
    )

    search_body = RowSearchRequest(
        query=safe_provider_query if client_provided_query else None,
        providers=body.providers,
        search_intent=intent_result.to_dict(),
    )

    # Call the existing search endpoint logic directly
    search_response = await search_row_listings(
        row_id=row_id,
        body=search_body,
        authorization=authorization,
        session=session,
    )

    # Add search_intent to response
    response_data = {
        "results": [r.model_dump() for r in search_response.results] if hasattr(search_response, "results") else [],
        "provider_statuses": [s.model_dump() for s in search_response.provider_statuses] if hasattr(search_response, "provider_statuses") else [],
        "user_message": getattr(search_response, "user_message", None),
        "search_intent": intent_result.to_dict(),
    }

    return response_data
