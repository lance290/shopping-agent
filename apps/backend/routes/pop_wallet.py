"""Pop wallet and receipt scanning routes."""

import json
import re
import hashlib
import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from models.rows import Row, Project
from models.pop import WalletTransaction, Receipt
from services.llm import call_gemini
from routes.pop_helpers import _get_pop_user

logger = logging.getLogger(__name__)
wallet_router = APIRouter()


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


@wallet_router.post("/receipt/scan")
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

        result = await call_gemini(prompt, timeout=30.0, image_base64=image_base64)
        match = re.search(r'\[.*\]', result, re.DOTALL)
        if match:
            items = json.loads(match.group())
            if isinstance(items, list):
                return items
        return []
    except Exception as e:
        logger.error(f"[Pop Receipt] Failed to extract items: {e}")
        return []
