"""Seller reputation scoring service (PRD 10 R2).

Computes a reputation score (0.0-5.0) for merchants based on:
- Response rate to RFPs
- Average response time
- Quote acceptance rate (buyer selected their bid)
- Transaction completion rate
- Dispute/complaint count
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models import Merchant, OutreachEvent, SellerQuote, Bid, PurchaseEvent

logger = logging.getLogger(__name__)


async def compute_reputation(session: AsyncSession, merchant_id: int) -> float:
    """
    Compute reputation score for a merchant.
    Returns a score between 0.0 and 5.0.
    """
    merchant = await session.get(Merchant, merchant_id)
    if not merchant:
        return 0.0

    scores = []
    weights = []

    # 1. Response rate — how often does the seller respond to outreach?
    response_rate = await _response_rate(session, merchant)
    if response_rate is not None:
        scores.append(response_rate * 5.0)
        weights.append(0.25)

    # 2. Quote acceptance rate — how often are their quotes selected?
    acceptance_rate = await _quote_acceptance_rate(session, merchant)
    if acceptance_rate is not None:
        scores.append(acceptance_rate * 5.0)
        weights.append(0.25)

    # 3. Transaction completion rate
    completion_rate = await _transaction_completion_rate(session, merchant)
    if completion_rate is not None:
        scores.append(completion_rate * 5.0)
        weights.append(0.30)

    # 4. Account maturity bonus (older accounts are more trustworthy)
    maturity_score = _account_maturity_score(merchant)
    scores.append(maturity_score)
    weights.append(0.10)

    # 5. Verification level bonus
    verification_score = _verification_score(merchant)
    scores.append(verification_score)
    weights.append(0.10)

    if not weights:
        return 0.0

    total_weight = sum(weights)
    weighted_sum = sum(s * w for s, w in zip(scores, weights))
    final_score = round(weighted_sum / total_weight, 2) if total_weight > 0 else 0.0

    return max(0.0, min(5.0, final_score))


async def update_merchant_reputation(session: AsyncSession, merchant_id: int) -> float:
    """Compute and persist the reputation score for a merchant."""
    score = await compute_reputation(session, merchant_id)

    merchant = await session.get(Merchant, merchant_id)
    if merchant:
        merchant.reputation_score = score
        merchant.updated_at = datetime.utcnow()
        session.add(merchant)
        await session.flush()
        logger.info(f"[REPUTATION] Merchant {merchant_id} score updated to {score}")

    return score


async def _response_rate(session: AsyncSession, merchant: Merchant) -> Optional[float]:
    """Fraction of outreach events the merchant responded to."""
    if not merchant.email:
        return None

    result = await session.exec(
        select(
            func.count(OutreachEvent.id),
            func.count(OutreachEvent.id).filter(
                OutreachEvent.status == "responded"
            ),
        ).where(OutreachEvent.vendor_email == merchant.email)
    )
    row = result.one()
    total, responded = row

    if total == 0:
        return None

    return responded / total


async def _quote_acceptance_rate(session: AsyncSession, merchant: Merchant) -> Optional[float]:
    """Fraction of submitted quotes that were accepted/selected by buyers."""
    result = await session.exec(
        select(
            func.count(SellerQuote.id),
            func.count(SellerQuote.id).filter(
                SellerQuote.status == "accepted"
            ),
        ).where(SellerQuote.seller_email == merchant.email)
    )
    row = result.one()
    total, accepted = row

    if total == 0:
        return None

    return accepted / total


async def _transaction_completion_rate(session: AsyncSession, merchant: Merchant) -> Optional[float]:
    """Fraction of purchases that completed successfully (not refunded/failed)."""
    if not merchant.seller_id:
        return None

    result = await session.exec(
        select(
            func.count(PurchaseEvent.id),
            func.count(PurchaseEvent.id).filter(
                PurchaseEvent.status == "completed"
            ),
        ).where(
            PurchaseEvent.bid_id.in_(
                select(Bid.id).where(Bid.seller_id == merchant.seller_id)
            )
        )
    )
    row = result.one()
    total, completed = row

    if total == 0:
        return None

    return completed / total


def _account_maturity_score(merchant: Merchant) -> float:
    """Score based on account age. Max 5.0 at 180+ days."""
    age_days = (datetime.utcnow() - merchant.created_at).days
    if age_days >= 180:
        return 5.0
    elif age_days >= 90:
        return 4.0
    elif age_days >= 30:
        return 3.0
    elif age_days >= 7:
        return 2.0
    else:
        return 1.0


def _verification_score(merchant: Merchant) -> float:
    """Score based on verification level."""
    levels = {
        "unverified": 1.0,
        "email_verified": 2.5,
        "identity_verified": 4.0,
        "premium": 5.0,
    }
    return levels.get(merchant.verification_level, 1.0)
