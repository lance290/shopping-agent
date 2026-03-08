"""Pop wallet and receipt scanning routes."""

import json
import hashlib
import logging
from typing import Optional
from datetime import datetime, timedelta

import sqlalchemy as sa
from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from models.rows import Row, Project
from models.pop import WalletTransaction, Receipt
from services.veryfi import process_receipt_base64, VeryfiError
from routes.pop_helpers import _get_pop_user

logger = logging.getLogger(__name__)
wallet_router = APIRouter()

# Velocity limits (PRD fraud Layer 3)
MAX_RECEIPTS_PER_DAY = 5
MAX_RECEIPTS_PER_WEEK = 20

# Receipt date freshness window (days)
RECEIPT_MAX_AGE_DAYS = 7


@wallet_router.get("/wallet")
async def get_pop_wallet(
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Fetch the user's Pop wallet balance and transaction history."""
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


class ReceiptScanRequest(BaseModel):
    image_base64: str
    project_id: Optional[int] = None
    source: Optional[str] = "camera"  # "camera" | "camera_roll" | "file_upload"


@wallet_router.post("/receipt/scan")
async def scan_receipt(
    request: Request,
    body: ReceiptScanRequest,
    session: AsyncSession = Depends(get_session),
):
    """
    Scan a grocery receipt image via Veryfi OCR + fraud detection.
    Matches line items against the user's Pop list, checks for active
    campaign rebates, and credits the wallet.

    NO fallback to Gemini — if Veryfi fails, return a friendly error.
    """
    user = await _get_pop_user(request, session)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # ---- Velocity limits (PRD fraud Layer 3) ----
    now = datetime.utcnow()
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(weeks=1)

    day_count_result = await session.execute(
        sa.text(
            "SELECT COUNT(*) FROM receipt WHERE user_id = :uid AND created_at > :since"
        ),
        {"uid": user.id, "since": day_ago},
    )
    day_count = day_count_result.scalar() or 0
    if day_count >= MAX_RECEIPTS_PER_DAY:
        return {
            "status": "rate_limited",
            "message": "You've reached the daily receipt limit. Try again tomorrow!",
            "items": [],
            "credits_earned_cents": 0,
        }

    week_count_result = await session.execute(
        sa.text(
            "SELECT COUNT(*) FROM receipt WHERE user_id = :uid AND created_at > :since"
        ),
        {"uid": user.id, "since": week_ago},
    )
    week_count = week_count_result.scalar() or 0
    if week_count >= MAX_RECEIPTS_PER_WEEK:
        return {
            "status": "rate_limited",
            "message": "You've reached the weekly receipt limit. Try again next week!",
            "items": [],
            "credits_earned_cents": 0,
        }

    # ---- Image-based dedup ----
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

    # ---- Call Veryfi (NO fallback) ----
    try:
        veryfi_result = await process_receipt_base64(body.image_base64)
    except VeryfiError as e:
        logger.error(f"[Pop Receipt] Veryfi failed: {e}")
        return {
            "status": "error",
            "message": "We couldn't verify this receipt right now. Sorry about that — please try again later.",
            "items": [],
            "credits_earned_cents": 0,
        }

    # ---- Fraud check (PRD Layer 2: Image Forensics) ----
    if veryfi_result.is_fraudulent:
        logger.warning(
            f"[Pop Receipt] Fraud detected for user {user.id}: "
            f"flags={veryfi_result.fraud_flags}, score={veryfi_result.fraud_score}"
        )
        receipt_record = Receipt(
            user_id=user.id,
            image_hash=image_hash,
            status="rejected",
            fraud_score=veryfi_result.fraud_score,
            fraud_flags=veryfi_result.fraud_flags,
            veryfi_document_id=veryfi_result.document_id,
            raw_veryfi_json=json.dumps(veryfi_result.raw),
        )
        session.add(receipt_record)
        await session.commit()
        return {
            "status": "rejected",
            "message": "This receipt could not be verified. If you believe this is an error, please contact support.",
            "items": [],
            "credits_earned_cents": 0,
        }

    # ---- Receipt date freshness check ----
    if veryfi_result.date:
        try:
            from datetime import date as date_type
            receipt_date = veryfi_result.date if isinstance(veryfi_result.date, date_type) else datetime.strptime(str(veryfi_result.date)[:10], "%Y-%m-%d").date()
            age_days = (now.date() - receipt_date).days
            if age_days > RECEIPT_MAX_AGE_DAYS:
                logger.info(f"[Pop Receipt] Stale receipt rejected: user={user.id}, age={age_days}d, limit={RECEIPT_MAX_AGE_DAYS}d")
                return {
                    "status": "rejected",
                    "message": f"This receipt is more than {RECEIPT_MAX_AGE_DAYS} days old. Please submit receipts within a week of purchase.",
                    "items": [],
                    "credits_earned_cents": 0,
                }
        except (ValueError, TypeError) as e:
            logger.warning(f"[Pop Receipt] Could not parse receipt date: {veryfi_result.date} — {e}")

    # ---- Content-based dedup (store + date + total) ----
    content_hash = hashlib.sha256(
        f"{veryfi_result.vendor_name}|{veryfi_result.date}|{veryfi_result.total}".encode()
    ).hexdigest()
    content_dup_stmt = (
        select(Receipt)
        .where(Receipt.receipt_content_hash == content_hash)
    )
    content_dup_result = await session.execute(content_dup_stmt)
    if content_dup_result.scalar_one_or_none():
        return {
            "status": "duplicate",
            "message": "This receipt has already been submitted (possibly from a different photo). Credits were applied the first time.",
            "items": [],
            "credits_earned_cents": 0,
        }

    # ---- Find the user's active project ----
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

    # ---- Match receipt items against list items ----
    receipt_items = veryfi_result.line_items
    matched = []
    credits_cents = 0

    if project_id and receipt_items:
        rows_stmt = (
            select(Row)
            .where(Row.project_id == project_id)
            .where(Row.status.in_(["sourcing", "active", "pending"]))
        )
        rows_result = await session.execute(rows_stmt)
        list_rows = rows_result.scalars().all()
        list_titles = {r.id: (r.title or "").lower() for r in list_rows}

        for item in receipt_items:
            item_lower = item.description.lower()
            best_match_id = None
            best_overlap = 0

            for row_id, row_title in list_titles.items():
                row_words = set(row_title.split())
                receipt_words = set(item_lower.split())
                overlap = len(row_words & receipt_words)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_match_id = row_id

            matched.append({
                "receipt_item": item.description,
                "receipt_price": item.total,
                "matched_list_item_id": best_match_id if best_overlap > 0 else None,
                "matched_list_item_title": list_titles.get(best_match_id, "") if best_match_id else None,
            })

            # MVP credit: $0.25 per matched item, $0.50 for a swap
            if best_match_id:
                credits_cents += 25
    else:
        matched = [
            {"receipt_item": item.description, "receipt_price": item.total, "matched_list_item_id": None}
            for item in receipt_items
        ]

    # ---- Campaign rebate matching (PRD: PopSwaps Rebate Flow) ----
    campaign_credits_cents = 0
    campaign_matches = []
    try:
        from models.coupons import Campaign
        now_ts = datetime.utcnow()
        camp_stmt = (
            select(Campaign)
            .where(Campaign.status == "active")
            .where(Campaign.budget_remaining_cents > 0)
            .where(
                (Campaign.start_date == None) | (Campaign.start_date <= now_ts)
            )
            .where(
                (Campaign.end_date == None) | (Campaign.end_date > now_ts)
            )
        )
        camp_result = await session.execute(camp_stmt)
        active_campaigns = camp_result.scalars().all()

        for item in receipt_items:
            item_lower = item.description.lower()
            for camp in active_campaigns:
                if camp.budget_remaining_cents <= 0:
                    continue
                # Check if receipt item matches the actual swap product or category.
                cats = (camp.target_categories or "").lower()
                swap_name_lower = (camp.swap_product_name or "").lower()
                cat_match = any(
                    c.strip() and (c.strip() in item_lower or item_lower in c.strip())
                    for c in cats.split(",")
                )
                swap_name_match = any(
                    w in item_lower
                    for w in swap_name_lower.split() if len(w) > 3
                )
                if cat_match or swap_name_match:
                    payout = min(camp.payout_per_swap_cents, camp.budget_remaining_cents)
                    camp.budget_remaining_cents -= payout
                    if camp.budget_remaining_cents <= 0:
                        camp.status = "depleted"
                    camp.updated_at = now_ts
                    session.add(camp)
                    campaign_credits_cents += payout
                    campaign_matches.append({
                        "campaign_id": camp.id,
                        "campaign_name": camp.name,
                        "payout_cents": payout,
                        "receipt_item": item.description,
                    })
                    break  # One campaign match per item
    except Exception as e:
        logger.warning(f"[Pop Receipt] Campaign matching failed (non-fatal): {e}")

    credits_cents += campaign_credits_cents

    # ---- Persist receipt record ----
    receipt_record = Receipt(
        user_id=user.id,
        project_id=project_id,
        image_hash=image_hash,
        status="verified",
        credits_earned_cents=credits_cents,
        items_matched=sum(1 for m in matched if m.get("matched_list_item_id")),
        raw_items_json=json.dumps([i.to_dict() for i in receipt_items]),
        veryfi_document_id=veryfi_result.document_id,
        store_name=veryfi_result.vendor_name,
        total_amount=veryfi_result.total,
        fraud_score=veryfi_result.fraud_score,
        fraud_flags=veryfi_result.fraud_flags,
        raw_veryfi_json=json.dumps(veryfi_result.raw),
        receipt_content_hash=content_hash,
        upload_source=body.source,
    )
    # Parse transaction_date if available
    if veryfi_result.date:
        try:
            receipt_record.transaction_date = datetime.fromisoformat(veryfi_result.date)
        except (ValueError, TypeError):
            pass
    session.add(receipt_record)
    await session.flush()

    # ---- Post credits to wallet ----
    if credits_cents > 0:
        user.wallet_balance_cents = (user.wallet_balance_cents or 0) + credits_cents
        session.add(user)

        # Regular receipt-match credits
        base_credits = credits_cents - campaign_credits_cents
        if base_credits > 0:
            txn = WalletTransaction(
                user_id=user.id,
                amount_cents=base_credits,
                description=f"Receipt scan — {len(receipt_items)} item(s) matched",
                source="receipt_scan",
                receipt_id=receipt_record.id,
            )
            session.add(txn)

        # Campaign rebate credits (one per campaign match)
        for cm in campaign_matches:
            camp_txn = WalletTransaction(
                user_id=user.id,
                amount_cents=cm["payout_cents"],
                description=f"PopSwap rebate — {cm['campaign_name']}",
                source="campaign_rebate",
                receipt_id=receipt_record.id,
                campaign_id=cm["campaign_id"],
            )
            session.add(camp_txn)

        # PRD 6.2: 30% of swap payouts to the referrer
        from models.pop import Referral
        ref_stmt = select(Referral).where(Referral.referred_user_id == user.id, Referral.status == "activated")
        ref_result = await session.execute(ref_stmt)
        referral = ref_result.scalar_one_or_none()

        if referral:
            referrer_amount = int(credits_cents * 0.30)
            if referrer_amount > 0:
                from models.auth import User as AuthUser
                referrer = await session.get(AuthUser, referral.referrer_user_id)
                if referrer:
                    referrer.wallet_balance_cents = (referrer.wallet_balance_cents or 0) + referrer_amount
                    session.add(referrer)
                    ref_txn = WalletTransaction(
                        user_id=referrer.id,
                        amount_cents=referrer_amount,
                        description="Referral share — 30% from a friend's savings",
                        source="referral_share",
                    )
                    session.add(ref_txn)

    await session.commit()

    return {
        "status": "verified",
        "message": f"Found {len(receipt_items)} items on your receipt!" + (
            f" You earned ${credits_cents / 100:.2f} in Pop credits!" if credits_cents > 0 else ""
        ),
        "items": matched,
        "credits_earned_cents": credits_cents,
        "total_items": len(receipt_items),
        "new_balance_cents": user.wallet_balance_cents,
        "store_name": veryfi_result.vendor_name,
        "receipt_total": veryfi_result.total,
        "receipt_date": veryfi_result.date,
    }
