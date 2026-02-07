"""Clickout routes - affiliate link redirection and logging."""
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from fastapi.responses import RedirectResponse
from typing import Optional
import asyncio

from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from models import ClickoutEvent
from dependencies import get_current_session
from sourcing import extract_merchant_domain
from affiliate import link_resolver, ClickContext
from audit import audit_log
from routes.rate_limit import check_rate_limit

router = APIRouter(tags=["clickout"])


@router.get("/api/out")
async def clickout_redirect(
    url: str,
    request: Request,
    row_id: Optional[int] = None,
    idx: int = 0,
    source: str = "unknown",
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    """
    Log a clickout event and redirect to the merchant.
    
    Query params:
        url: The canonical merchant URL
        row_id: The procurement row this offer belongs to
        idx: The offer's position in search results
        source: The sourcing provider (e.g., serpapi_google_shopping)
    """
    if not url or not url.startswith(('http://', 'https://')):
        raise HTTPException(status_code=400, detail="Invalid URL")
    
    user_id = None
    session_id = None
    if authorization:
        auth_session = await get_current_session(authorization, session)
        if auth_session:
            user_id = auth_session.user_id
            session_id = auth_session.id

    rate_key = f"clickout:{user_id or request.client.host}"
    if not check_rate_limit(rate_key, "clickout"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    merchant_domain = extract_merchant_domain(url)
    
    context = ClickContext(
        user_id=user_id,
        row_id=row_id,
        offer_index=idx,
        source=source,
        merchant_domain=merchant_domain,
    )
    
    resolved = link_resolver.resolve(url, context)
    
    # Anti-Fraud assessment (PRD 10)
    client_ip = request.client.host if request.client else None
    client_ua = request.headers.get("user-agent")
    from services.fraud import assess_clickout
    is_suspicious = assess_clickout(client_ip, client_ua, user_id)

    async def log_clickout():
        try:
            from database import engine
            from sqlalchemy.orm import sessionmaker
            from sqlmodel.ext.asyncio.session import AsyncSession as AS
            async_session = sessionmaker(engine, class_=AS, expire_on_commit=False)
            async with async_session() as log_session:
                event = ClickoutEvent(
                    user_id=user_id,
                    session_id=session_id,
                    row_id=row_id,
                    offer_index=idx,
                    canonical_url=url,
                    final_url=resolved.final_url,
                    merchant_domain=merchant_domain,
                    handler_name=resolved.handler_name,
                    affiliate_tag=resolved.affiliate_tag,
                    source=source,
                    is_suspicious=is_suspicious,
                    ip_address=client_ip,
                    user_agent=client_ua[:500] if client_ua else None,
                )
                log_session.add(event)
                await log_session.commit()
                await log_session.refresh(event)
                
                await audit_log(
                    session=log_session,
                    action="clickout.redirect",
                    user_id=user_id,
                    resource_type="clickout",
                    resource_id=str(event.id),
                    details={
                        "canonical_url": url,
                        "merchant_domain": merchant_domain,
                        "handler_name": resolved.handler_name,
                    },
                    request=request,
                )
        except Exception as e:
            print(f"[CLICKOUT] Failed to log: {e}")
    
    asyncio.create_task(log_clickout())
    
    return RedirectResponse(url=resolved.final_url, status_code=302)
