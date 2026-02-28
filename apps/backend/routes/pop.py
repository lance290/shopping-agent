from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks
from fastapi.responses import PlainTextResponse
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import Field, SQLModel, select
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import json
import re
import os
import hmac
import hashlib
import logging
import uuid
import base64
from datetime import timedelta

from database import get_session
from models.rows import Row, Project, ProjectMember, ProjectInvite
from models.bids import Bid
from models.auth import User
from models.pop import WalletTransaction, Receipt, Referral, _gen_ref_code
from services.llm import make_unified_decision, make_pop_decision, ChatContext, generate_choice_factors, call_gemini
from dependencies import get_current_session
from services.email import EmailResult, RESEND_API_KEY, FROM_EMAIL, FROM_NAME, _maybe_intercept
from routes.chat import _create_row, _update_row, _save_factors_scoped, _stream_search

try:
    import resend
except ModuleNotFoundError:  # pragma: no cover
    resend = None  # type: ignore

try:
    from twilio.rest import Client as TwilioClient
    from twilio.request_validator import RequestValidator as TwilioValidator
except ModuleNotFoundError:  # pragma: no cover
    TwilioClient = None  # type: ignore
    TwilioValidator = None  # type: ignore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pop", tags=["pop-chatbot"])


async def _get_pop_user(request: Request, session: AsyncSession) -> Optional[User]:
    """Resolve the current user from a Bearer token, or return None."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header:
        return None
    auth_session = await get_current_session(auth_header, session)
    if not auth_session:
        return None
    return await session.get(User, auth_session.user_id)

POP_FROM_EMAIL = os.getenv("POP_FROM_EMAIL", "pop@popsavings.com")
POP_DOMAIN = os.getenv("POP_DOMAIN", "https://popsavings.com")
RESEND_WEBHOOK_SECRET = os.getenv("RESEND_WEBHOOK_SECRET", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")


@router.get("/health")
async def pop_health():
    """Health check for Pop/Bob service."""
    return {"status": "ok", "service": "pop"}


# ---------------------------------------------------------------------------
# Helpers: channel-aware reply (email or SMS)
# ---------------------------------------------------------------------------


async def send_pop_reply(
    to_email: str,
    subject: str,
    body_text: str,
) -> EmailResult:
    """
    Send a reply email from Bob using the existing Resend service.
    """
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="white-space: pre-wrap; line-height: 1.6;">
{body_text.replace(chr(10), '<br>')}
        </div>
        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
        <p style="color: #999; font-size: 12px;">Pop — your AI grocery savings assistant. Powered by BuyAnything.</p>
    </body>
    </html>
    """

    to_email, subject = _maybe_intercept(to_email, subject)
    if RESEND_API_KEY and resend is not None:
        try:
            params: resend.Emails.SendParams = {
                "from": f"Pop <{POP_FROM_EMAIL}>",
                "to": [to_email],
                "subject": subject,
                "html": html_content,
                "text": body_text,
            }
            response = resend.Emails.send(params)
            return EmailResult(success=True, message_id=response.get("id"))
        except Exception as e:
            logger.error(f"[Pop RESEND ERROR] {e}")
            return EmailResult(success=False, error=str(e))

    logger.info(f"[Pop DEMO EMAIL] To: {to_email} | Subject: {subject}")
    return EmailResult(success=True, message_id="demo-pop-reply")


def send_pop_sms(to_phone: str, body_text: str) -> bool:
    """
    Send an outbound SMS from Bob via Twilio.
    Returns True on success.
    """
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_PHONE_NUMBER:
        logger.info(f"[Pop DEMO SMS] To: {to_phone} | Body: {body_text[:120]}")
        return True
    if TwilioClient is None:
        logger.warning("[Pop] twilio package not installed — cannot send SMS")
        return False
    try:
        client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        msg = client.messages.create(
            body=body_text[:1600],  # SMS limit
            from_=TWILIO_PHONE_NUMBER,
            to=to_phone,
        )
        logger.info(f"[Pop] SMS sent to {to_phone} (sid={msg.sid})")
        return True
    except Exception as e:
        logger.error(f"[Pop SMS ERROR] {e}")
        return False


async def send_pop_onboarding_email(email: str) -> EmailResult:
    """
    Send onboarding / welcome email to a new user who emailed Bob.
    """
    subject = "Welcome to Pop — your AI grocery savings assistant!"
    body_text = (
        "Hi there!\n\n"
        "I'm Pop, your AI grocery savings assistant.\n\n"
        "It looks like you don't have an account yet. "
        "To get started, visit:\n\n"
        f"  {POP_DOMAIN}/signup\n\n"
        "Once you're signed up, just email me your shopping list "
        "and I'll find the best deals for you!\n\n"
        "— Pop"
    )
    return await send_pop_reply(email, subject, body_text)


def send_pop_onboarding_sms(phone: str) -> bool:
    """
    Send onboarding SMS to an unknown phone number.
    """
    body = (
        f"Hi! I'm Pop, your AI grocery savings assistant. "
        f"To get started, sign up at {POP_DOMAIN} "
        f"and add your phone number to your profile. "
        f"Then text me your shopping list!"
    )
    return send_pop_sms(phone, body)


# ---------------------------------------------------------------------------
# Conversation history helpers
# ---------------------------------------------------------------------------

def _load_chat_history(row: Optional[Row]) -> List[dict]:
    """Load conversation history from the active Row's chat_history JSON field."""
    if not row or not row.chat_history:
        return []
    try:
        history = json.loads(row.chat_history)
        if isinstance(history, list):
            return history
    except (json.JSONDecodeError, TypeError):
        pass
    return []


async def _append_chat_history(
    session: AsyncSession,
    row: Row,
    user_message: str,
    assistant_message: str,
) -> None:
    """Append the latest user + assistant exchange to Row.chat_history."""
    history = _load_chat_history(row)
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": assistant_message})
    # Keep last 50 messages to avoid unbounded growth
    if len(history) > 50:
        history = history[-50:]
    row.chat_history = json.dumps(history)
    row.updated_at = datetime.utcnow()
    session.add(row)
    await session.commit()


# ---------------------------------------------------------------------------
# ProjectMember helpers
# ---------------------------------------------------------------------------

async def _ensure_project_member(
    session: AsyncSession,
    project_id: int,
    user_id: int,
    channel: str = "email",
    role: str = "owner",
) -> ProjectMember:
    """Ensure the user is a member of the project; create if not."""
    stmt = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id,
    )
    result = await session.execute(stmt)
    member = result.scalar_one_or_none()
    if member:
        if member.channel != channel:
            member.channel = channel
            session.add(member)
            await session.commit()
        return member
    member = ProjectMember(
        project_id=project_id,
        user_id=user_id,
        role=role,
        channel=channel,
    )
    session.add(member)
    await session.commit()
    await session.refresh(member)
    return member

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
                "constraints": json.loads(active_row.choice_answers) if active_row.choice_answers else {},
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
        logger.info(f"[Pop] Decision: {len(decision.items)} items extracted.")

        target_row = None

        for item in decision.items:
            action_type = item.action.get("type", "")
            intent = item.intent

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
                    await _save_factors_scoped(row.id, factors)

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


async def _classify_swaps_llm(row_title: str, bids: list) -> set:
    """
    Ask Gemini to classify which bids are swap alternatives for a list item.
    Returns a set of bid IDs classified as swaps.
    Bids not in the returned set are direct matches.
    """
    try:
        lines = "\n".join(
            f'{i + 1}. [id={b.id}] "{b.item_title}"'
            for i, b in enumerate(bids)
        )
        prompt = (
            f'A shopper wants: "{row_title}"\n\n'
            f"The following products were found:\n{lines}\n\n"
            f"For each product, decide: is it a DIRECT match (same product, possibly different brand/size) "
            f"or a SWAP (a meaningfully different product that could substitute)?\n\n"
            f'Return ONLY a JSON array of objects: [{{"id": <bid_id>, "is_swap": true|false}}, ...]\n'
            f"No explanation, no markdown, just the JSON array."
        )
        raw = await call_gemini(prompt, timeout=15.0)
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if not match:
            return set()
        classifications = json.loads(match.group())
        return {item["id"] for item in classifications if item.get("is_swap")}
    except Exception as e:
        logger.warning(f"[Pop] LLM swap classification failed: {e}")
        return set()


@router.get("/list/{project_id}")
async def get_pop_list(
    project_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    Fetch the family shopping list for the Pop list view.
    Returns project info + rows with their bids.
    """
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="List not found")

    rows_stmt = (
        select(Row)
        .where(Row.project_id == project_id)
        .where(Row.status.in_(["sourcing", "active", "pending"]))
        .order_by(Row.created_at.desc())
        .limit(50)
    )
    rows_result = await session.execute(rows_stmt)
    rows = rows_result.scalars().all()

    items = []
    for row in rows:
        bids_stmt = (
            select(Bid)
            .where(Bid.row_id == row.id)
            .order_by(Bid.combined_score.desc().nullslast())
            .limit(5)
        )
        bids_result = await session.execute(bids_stmt)
        bids = bids_result.scalars().all()

        deals = []
        swaps = []
        lowest_price = None

        priced_bids = [b for b in bids if b.price is not None]

        # LLM swap classification: classify any unclassified bids in one Gemini call
        unclassified = [b for b in priced_bids if b.is_swap is None]
        if unclassified and row.title:
            swap_ids = await _classify_swaps_llm(row.title, unclassified)
            for b in unclassified:
                b.is_swap = b.id in swap_ids
                session.add(b)
            await session.commit()

        for b in priced_bids:
            deal = {
                "id": b.id,
                "title": b.item_title,
                "price": b.price,
                "source": b.source,
                "url": b.canonical_url,
                "image_url": b.image_url,
            }
            deals.append(deal)
            if lowest_price is None or b.price < lowest_price:
                lowest_price = b.price
            if b.is_swap:
                swaps.append({
                    "id": b.id,
                    "title": b.item_title,
                    "price": b.price,
                    "source": b.source,
                    "url": b.canonical_url,
                    "image_url": b.image_url,
                    "savings_vs_first": round(deals[0]["price"] - b.price, 2) if deals and b.price < deals[0]["price"] else None,
                })

        items.append({
            "id": row.id,
            "title": row.title,
            "status": row.status,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "deals": deals,
            "swaps": swaps[:3],
            "lowest_price": lowest_price,
            "deal_count": len(deals),
        })

    return {
        "project_id": project_id,
        "title": project.title,
        "items": items,
    }


@router.get("/my-list")
async def get_my_pop_list(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    Return the current user's active Family Shopping List project + items.
    Used on page load to restore list state without knowing the project_id upfront.
    """
    user = await _get_pop_user(request, session)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    proj_stmt = (
        select(Project)
        .where(Project.user_id == user.id)
        .where(Project.title == "Family Shopping List")
        .where(Project.status == "active")
    )
    proj_result = await session.execute(proj_stmt)
    project = proj_result.scalar_one_or_none()

    if not project:
        return {"project_id": None, "title": "Family Shopping List", "items": []}

    rows_stmt = (
        select(Row)
        .where(Row.project_id == project.id)
        .where(Row.status.in_(["sourcing", "active", "pending"]))
        .order_by(Row.created_at.asc())
        .limit(50)
    )
    rows_result = await session.execute(rows_stmt)
    rows = rows_result.scalars().all()

    items = [{"id": r.id, "title": r.title, "status": r.status} for r in rows]
    return {"project_id": project.id, "title": project.title, "items": items}


@router.post("/list/{project_id}/invite")
async def create_pop_invite(
    project_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    Create an opaque invite token for sharing a Pop list.
    Returns a shareable invite URL.
    """
    user = await _get_pop_user(request, session)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="List not found")

    token = str(uuid.uuid4())
    invite = ProjectInvite(
        id=token,
        project_id=project_id,
        invited_by=user.id,
        expires_at=datetime.utcnow() + timedelta(days=30),
    )
    session.add(invite)
    await session.commit()

    invite_url = f"{POP_DOMAIN}/pop-site/invite/{token}"
    return {"token": token, "invite_url": invite_url, "expires_days": 30}


@router.get("/invite/{token}")
async def resolve_pop_invite(
    token: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Public endpoint: resolve an invite token to project info (title, item count).
    Does NOT require authentication — used to preview the list before login.
    """
    invite = await session.get(ProjectInvite, token)
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found or expired")
    if invite.expires_at and invite.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Invite link has expired")

    project = await session.get(Project, invite.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="List not found")

    rows_stmt = (
        select(Row)
        .where(Row.project_id == project.id)
        .where(Row.status.in_(["sourcing", "active", "pending"]))
    )
    rows_result = await session.execute(rows_stmt)
    items = rows_result.scalars().all()

    return {
        "project_id": project.id,
        "title": project.title,
        "item_count": len(items),
        "token": token,
    }


@router.post("/join-list/{project_id}")
async def join_pop_list(
    project_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    Add the authenticated user as a member of the given shared Pop list.
    Used when a family member accepts a shared list invite.
    """
    user = await _get_pop_user(request, session)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="List not found")

    await _ensure_project_member(session, project.id, user.id, channel="web", role="member")
    return {"joined": True, "project_id": project.id, "title": project.title}


class PatchItemRequest(BaseModel):
    title: str


@router.patch("/item/{row_id}")
async def patch_pop_item(
    row_id: int,
    body: PatchItemRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Rename a list item."""
    user = await _get_pop_user(request, session)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    row = await session.get(Row, row_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Item not found")

    row.title = body.title.strip()
    row.updated_at = datetime.utcnow()
    session.add(row)
    await session.commit()
    return {"id": row.id, "title": row.title, "status": row.status}


@router.delete("/item/{row_id}")
async def delete_pop_item(
    row_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Remove a list item (soft-delete to avoid FK constraint on bids)."""
    user = await _get_pop_user(request, session)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    row = await session.get(Row, row_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Item not found")

    row.status = "canceled"
    row.updated_at = datetime.utcnow()
    session.add(row)
    await session.commit()
    return {"deleted": True}


@router.post("/offer/{bid_id}/claim")
async def claim_pop_offer(
    bid_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    Claim a swap offer (mark bid as selected for this household).
    Only the row owner can claim. One active claim per row.
    """
    user = await _get_pop_user(request, session)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    bid = await session.get(Bid, bid_id)
    if not bid:
        raise HTTPException(status_code=404, detail="Offer not found")

    row = await session.get(Row, bid.row_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Offer not found")

    if row.status == "canceled":
        raise HTTPException(status_code=409, detail="Cannot claim offer on a canceled item")

    # Clear any prior selection on this row (one active claim per item)
    prior_stmt = select(Bid).where(Bid.row_id == bid.row_id, Bid.is_selected == True)
    prior_result = await session.execute(prior_stmt)
    for prior in prior_result.scalars().all():
        prior.is_selected = False
        prior.liked_at = None
        session.add(prior)

    bid.is_selected = True
    bid.liked_at = datetime.utcnow()
    session.add(bid)
    await session.commit()
    return {"claimed": True, "bid_id": bid_id, "title": bid.item_title, "price": bid.price}


@router.delete("/offer/{bid_id}/claim")
async def unclaim_pop_offer(
    bid_id: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Cancel (unclaim) a previously claimed swap offer."""
    user = await _get_pop_user(request, session)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    bid = await session.get(Bid, bid_id)
    if not bid:
        raise HTTPException(status_code=404, detail="Offer not found")

    row = await session.get(Row, bid.row_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Offer not found")

    bid.is_selected = False
    bid.liked_at = None
    session.add(bid)
    await session.commit()
    return {"claimed": False, "bid_id": bid_id}


@router.get("/wallet")
async def get_pop_wallet(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    Fetch the user's Pop wallet balance and transaction history.
    """
    user = await _get_pop_user(request, session)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    txn_stmt = (
        select(WalletTransaction)
        .where(WalletTransaction.user_id == user.id)
        .order_by(WalletTransaction.created_at.desc())
        .limit(50)
    )
    txn_result = await session.execute(txn_stmt)
    transactions = txn_result.scalars().all()

    return {
        "balance_cents": user.wallet_balance_cents,
        "transactions": [
            {
                "id": t.id,
                "amount_cents": t.amount_cents,
                "description": t.description,
                "source": t.source,
                "created_at": t.created_at.isoformat(),
            }
            for t in transactions
        ],
    }


# ---------------------------------------------------------------------------
# Receipt scanning — "Shop & earn" (step 4 of How Pop Works)
# ---------------------------------------------------------------------------

class ReceiptScanRequest(BaseModel):
    image_base64: str
    project_id: Optional[int] = None


@router.post("/receipt/scan")
async def scan_receipt(
    request: Request,
    body: ReceiptScanRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Scan a grocery receipt image. Uses Gemini vision to extract line items,
    then matches them against the user's Pop list to verify swap purchases
    and calculate wallet credits.
    """
    user = await _get_pop_user(request, session)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Find the user's active project
    project_id = body.project_id
    if not project_id:
        proj_stmt = (
            select(Project)
            .where(Project.user_id == user.id)
            .where(Project.title == "Family Shopping List")
            .where(Project.status == "active")
        )
        proj_result = await session.execute(proj_stmt)
        project = proj_result.scalar_one_or_none()
        if project:
            project_id = project.id

    # Dedup: reject if this exact receipt image was already submitted
    image_hash = hashlib.sha256(body.image_base64.encode()).hexdigest()
    dup_stmt = (
        select(Receipt)
        .where(Receipt.user_id == user.id)
        .where(Receipt.image_hash == image_hash)
    )
    dup_result = await session.execute(dup_stmt)
    if dup_result.scalar_one_or_none():
        return {
            "status": "duplicate",
            "message": "Looks like you already submitted this receipt! Credits were applied the first time.",
            "items": [],
            "credits_earned_cents": 0,
        }

    # Use Gemini to extract receipt items
    receipt_items = await _extract_receipt_items(body.image_base64)

    if not receipt_items:
        return {
            "status": "no_items",
            "message": "Couldn't read any items from this receipt. Try taking a clearer photo!",
            "items": [],
            "credits_earned_cents": 0,
        }

    # Match receipt items against list items (if we have a project)
    matched = []
    credits_cents = 0
    if project_id:
        rows_stmt = (
            select(Row)
            .where(Row.project_id == project_id)
            .where(Row.status.in_(["sourcing", "active", "pending"]))
        )
        rows_result = await session.execute(rows_stmt)
        list_rows = rows_result.scalars().all()

        list_titles = {r.id: (r.title or "").lower() for r in list_rows}

        for receipt_item in receipt_items:
            receipt_lower = receipt_item.get("name", "").lower()
            best_match_id = None
            best_overlap = 0

            for row_id, row_title in list_titles.items():
                row_words = set(row_title.split())
                receipt_words = set(receipt_lower.split())
                overlap = len(row_words & receipt_words)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_match_id = row_id

            matched.append({
                "receipt_item": receipt_item.get("name", ""),
                "receipt_price": receipt_item.get("price"),
                "matched_list_item_id": best_match_id if best_overlap > 0 else None,
                "matched_list_item_title": list_titles.get(best_match_id, "") if best_match_id else None,
                "is_swap": receipt_item.get("is_swap", False),
            })

            # MVP credit: $0.25 per matched item, $0.50 for a swap
            if best_match_id:
                if receipt_item.get("is_swap", False):
                    credits_cents += 50
                else:
                    credits_cents += 25
    else:
        matched = [
            {"receipt_item": item.get("name", ""), "receipt_price": item.get("price"), "matched_list_item_id": None}
            for item in receipt_items
        ]

    # Persist receipt record (for dedup and audit)
    receipt_record = Receipt(
        user_id=user.id,
        project_id=project_id,
        image_hash=image_hash,
        status="processed",
        credits_earned_cents=credits_cents,
        items_matched=sum(1 for m in matched if m.get("matched_list_item_id")),
        raw_items_json=json.dumps(receipt_items),
    )
    session.add(receipt_record)
    await session.flush()  # get receipt_record.id

    # Post credits to wallet if any earned
    if credits_cents > 0:
        user.wallet_balance_cents = (user.wallet_balance_cents or 0) + credits_cents
        session.add(user)
        txn = WalletTransaction(
            user_id=user.id,
            amount_cents=credits_cents,
            description=f"Receipt scan — {len(receipt_items)} item(s) matched",
            source="receipt_scan",
            receipt_id=receipt_record.id,
        )
        session.add(txn)

    await session.commit()

    return {
        "status": "scanned",
        "message": f"Found {len(receipt_items)} items on your receipt!" + (
            f" You earned ${credits_cents / 100:.2f} in Pop credits!" if credits_cents > 0 else ""
        ),
        "items": matched,
        "credits_earned_cents": credits_cents,
        "total_items": len(receipt_items),
        "new_balance_cents": user.wallet_balance_cents,
    }


async def _extract_receipt_items(image_base64: str) -> List[dict]:
    """
    Use Gemini vision to extract line items from a receipt image.
    Returns list of {"name": str, "price": float|None, "is_swap": bool}.
    """
    try:
        prompt = """Analyze this grocery receipt image. Extract each line item with its name and price.

Return ONLY a JSON array of objects, each with:
- "name": the product name (string)
- "price": the price in dollars (number or null if unclear)
- "is_swap": false (we'll determine swaps separately)

Example:
[
  {"name": "Great Value Whole Milk 1 Gal", "price": 3.28, "is_swap": false},
  {"name": "Kroger Large Eggs 12ct", "price": 2.99, "is_swap": false}
]

Return ONLY the JSON array, no other text."""

        # Call Gemini with the image
        result = await call_gemini(
            prompt,
            timeout=30.0,
            image_base64=image_base64,
        )

        # Parse the JSON response
        import re as _re
        # Extract JSON array from response
        match = _re.search(r'\[.*\]', result, _re.DOTALL)
        if match:
            items = json.loads(match.group())
            if isinstance(items, list):
                return items
        return []
    except Exception as e:
        logger.error(f"[Pop Receipt] Failed to extract items: {e}")
        return []


GUEST_EMAIL = "guest@buy-anything.com"


class PopChatRequest(BaseModel):
    message: str
    email: Optional[str] = None
    channel: str = "web"
    guest_project_id: Optional[int] = None  # Guest lists get a real DB project ID


@router.post("/chat")
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
    # Resolve user from auth token or provided email
    user = await _get_pop_user(request, session)

    if not user and body.email:
        stmt = select(User).where(User.email == body.email)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

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
            # Guest sessions each get their own project — resume via guest_project_id
            if body.guest_project_id:
                project = await session.get(Project, body.guest_project_id)
                # Safety: only use it if it actually belongs to the guest user
                if project and project.user_id != user.id:
                    project = None
            if not project:
                project = Project(title="My Shopping List", user_id=user.id)
                session.add(project)
                await session.commit()
                await session.refresh(project)
        else:
            # Authenticated users — find or create their personal "Family Shopping List"
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
                "constraints": json.loads(active_row.choice_answers) if active_row.choice_answers else {},
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
        logger.info(f"[Pop Web] Decision: {len(decision.items)} items extracted.")

        target_row = None

        for item in decision.items:
            action_type = item.action.get("type", "")
            intent = item.intent

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
                    await _save_factors_scoped(row.id, factors)

            elif action_type == "update_row" and active_row:
                row = await _update_row(
                    session, active_row,
                    title=title if active_row.title != title else None,
                    constraints=constraints if constraints else None,
                    reset_bids=bool(search_query),
                )
                target_row = row

            # Trigger sourcing (non-streaming for web response)
            if search_query and target_row:
                async for _batch in _stream_search(target_row.id, search_query, authorization=None):
                    pass

        if target_row is None:
            target_row = active_row

        # Persist conversation history
        if target_row:
            await _append_chat_history(session, target_row, body.message, decision.message or "")

        # Load list items for the project
        list_stmt = (
            select(Row)
            .where(Row.project_id == project.id)
            .where(Row.status.in_(["sourcing", "active", "pending"]))
            .order_by(Row.created_at.desc())
            .limit(20)
        )
        list_result = await session.execute(list_stmt)
        list_rows = list_result.scalars().all()

        list_items = [
            {"id": r.id, "title": r.title, "status": r.status}
            for r in list_rows
        ]

        return {
            "reply": decision.message or "Got it!",
            "list_items": list_items,
            "project_id": project.id,
            "row_id": target_row.id if target_row else None,
            "action": action_type,
        }

    except Exception as e:
        logger.error(f"[Pop Web] Failed to process chat: {e}", exc_info=True)
        return {"reply": "Oops, something went wrong. Try again!", "list_items": [], "project_id": None}


def _verify_resend_signature(payload: bytes, signature: str) -> bool:
    """Verify Resend webhook signature using HMAC-SHA256."""
    if not RESEND_WEBHOOK_SECRET:
        logger.warning("[Pop] RESEND_WEBHOOK_SECRET not set — skipping verification")
        return True
    expected = hmac.new(
        RESEND_WEBHOOK_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/webhooks/resend")
async def resend_inbound(
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session)
):
    """
    Receives incoming emails to bob@buyanything.ai via Resend Inbound Webhooks.
    Resend posts JSON with the parsed email fields.
    Docs: https://resend.com/docs/dashboard/webhooks/introduction
    """
    raw_body = await request.body()
    signature = request.headers.get("resend-signature", "")

    if not _verify_resend_signature(raw_body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()

    # Resend inbound webhook payload structure
    sender = payload.get("from", "")
    # "from" may be a full address like "John <john@example.com>" — extract email
    if "<" in sender and ">" in sender:
        sender = sender.split("<")[1].split(">")[0]

    body = payload.get("text", "") or payload.get("html", "")
    subject = payload.get("subject", "")

    if not sender or not body:
        raise HTTPException(status_code=400, detail="Missing sender or body")

    logger.info(f"[Pop] Resend inbound from {sender}: {subject}")

    background_tasks.add_task(process_pop_message, sender, body, session, "email", None)

    return {"status": "accepted"}

def _verify_twilio_signature(request: Request, form_data: dict) -> bool:
    """Verify Twilio request signature."""
    if not TWILIO_AUTH_TOKEN or TwilioValidator is None:
        logger.warning("[Pop] Twilio auth token or SDK not available — skipping verification")
        return True
    validator = TwilioValidator(TWILIO_AUTH_TOKEN)
    signature = request.headers.get("X-Twilio-Signature", "")
    url = str(request.url)
    return validator.validate(url, form_data, signature)


@router.post("/webhooks/twilio")
async def twilio_inbound(
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session)
):
    """
    Receives incoming SMS to Bob's phone number via Twilio.
    Twilio posts form-encoded data with From, Body, etc.
    Returns TwiML (empty <Response/>) to acknowledge receipt.
    """
    form_data = await request.form()
    params = {k: v for k, v in form_data.items()}

    if not _verify_twilio_signature(request, params):
        raise HTTPException(status_code=401, detail="Invalid Twilio signature")

    sender_phone = params.get("From", "")
    body = params.get("Body", "")

    if not sender_phone or not body:
        raise HTTPException(status_code=400, detail="Missing From or Body")

    logger.info(f"[Pop] Twilio SMS from {sender_phone}: {body[:80]}")

    # Look up user by phone number
    statement = select(User).where(User.phone_number == sender_phone)
    result = await session.execute(statement)
    user = result.scalar_one_or_none()

    if user and user.email:
        background_tasks.add_task(
            process_pop_message, user.email, body, session, "sms", sender_phone,
        )
    else:
        logger.info(f"[Pop] Unknown phone {sender_phone}. Sending onboarding SMS.")
        send_pop_onboarding_sms(sender_phone)

    # Return empty TwiML so Twilio doesn't retry
    return PlainTextResponse(
        content='<?xml version="1.0" encoding="UTF-8"?><Response/>',
        media_type="application/xml",
    )


# ---------------------------------------------------------------------------
# Referral system
# ---------------------------------------------------------------------------

POP_DOMAIN = os.getenv("POP_DOMAIN", "https://popsavings.com")


@router.get("/referral")
async def get_pop_referral(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    Return the authenticated user's referral code and shareable link.
    Auto-generates a ref_code on first call if one doesn't exist yet.
    """
    user = await _get_pop_user(request, session)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if not user.ref_code:
        user.ref_code = _gen_ref_code()
        session.add(user)
        await session.commit()

    referral_link = f"{POP_DOMAIN}/?ref={user.ref_code}"

    # Count attributed signups
    ref_stmt = select(Referral).where(Referral.referrer_user_id == user.id)
    ref_result = await session.execute(ref_stmt)
    referrals = ref_result.scalars().all()

    return {
        "ref_code": user.ref_code,
        "referral_link": referral_link,
        "total_referrals": len(referrals),
        "activated_referrals": sum(1 for r in referrals if r.status == "activated"),
    }


@router.post("/referral/signup")
async def record_referral_signup(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    Record that a newly-signed-up user came through a referral link.
    Called during onboarding when ?ref=CODE is present.
    Body: { "ref_code": "ABCD1234" }
    """
    new_user = await _get_pop_user(request, session)
    if not new_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    body = await request.json()
    ref_code = (body.get("ref_code") or "").strip().upper()
    if not ref_code:
        raise HTTPException(status_code=400, detail="ref_code required")

    # Find referrer
    referrer_stmt = select(User).where(User.ref_code == ref_code)
    referrer_result = await session.execute(referrer_stmt)
    referrer = referrer_result.scalar_one_or_none()

    if not referrer or referrer.id == new_user.id:
        raise HTTPException(status_code=404, detail="Invalid referral code")

    # Idempotent — ignore duplicate signup attributions
    existing_stmt = select(Referral).where(Referral.referred_user_id == new_user.id)
    existing_result = await session.execute(existing_stmt)
    if existing_result.scalar_one_or_none():
        return {"status": "already_attributed"}

    referral = Referral(
        referrer_user_id=referrer.id,
        referred_user_id=new_user.id,
        ref_code=ref_code,
        status="activated",
        activated_at=datetime.utcnow(),
    )
    session.add(referral)

    # Referral bonus for referrer: $1.00
    referrer.wallet_balance_cents = (referrer.wallet_balance_cents or 0) + 100
    session.add(referrer)
    txn = WalletTransaction(
        user_id=referrer.id,
        amount_cents=100,
        description=f"Referral bonus — friend joined via your link",
        source="referral_bonus",
    )
    session.add(txn)
    await session.commit()

    return {"status": "attributed", "referrer_id": referrer.id}
