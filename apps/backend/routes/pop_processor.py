"""Core Pop message processor: NLU → row CRUD → sourcing → reply."""

import json
import logging
import re
from datetime import datetime
from typing import Optional, List

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from models.rows import Row, Project
from models.auth import User
from models.bids import Bid
from models.coupons import CouponCampaign, PopSwap
from services.llm import make_pop_decision, ChatContext, generate_choice_factors
from routes.chat import _create_row, _update_row, _save_choice_factors, _stream_search
from services.sdui_builder import build_ui_schema
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


async def _enrich_row_cpg(session: AsyncSession, row: Row) -> None:
    """
    PRD-08: Post-sourcing CPG enrichment.

    1. Reads the top Kroger bid for the row and saves retailer_sku + brand_name
       back to the Row model so downstream coupon matching is brand-aware.
    2. If no active PopSwap exists for that brand, creates a CouponCampaign
       (Outreach Queue) so Scout/Tod can reach out to the CPG brand manager.

    This is a best-effort, fire-and-forget step — any failure is logged and
    swallowed so it never disrupts the core message-processing flow.
    """
    try:
        # 1. Find the best Kroger bid (source == "kroger")
        kroger_bid_stmt = (
            select(Bid)
            .where(Bid.row_id == row.id)
            .where(Bid.source == "kroger")
            .order_by(Bid.combined_score.desc().nullslast())
            .limit(1)
        )
        kroger_result = await session.execute(kroger_bid_stmt)
        kroger_bid = kroger_result.scalar_one_or_none()

        if not kroger_bid:
            return

        # Extract brand_name and retailer_sku from the bid
        # KrogerProvider stores title as "{brand} {description}"; item_url encodes productId
        inferred_brand = None
        inferred_sku = None

        # retailer_sku: extract Kroger productId from item URL
        # URL pattern: https://www.kroger.com/p/{slug}/{productId}
        if kroger_bid.item_url:
            url_parts = kroger_bid.item_url.rstrip("/").rsplit("/", 1)
            if len(url_parts) == 2 and url_parts[1]:
                inferred_sku = url_parts[1]

        # brand_name: use the seller name if it's the Kroger vendor, otherwise
        # try to extract from the source_payload (raw provider data)
        if kroger_bid.source_payload and isinstance(kroger_bid.source_payload, dict):
            inferred_brand = kroger_bid.source_payload.get("brand")
        if not inferred_brand and kroger_bid.item_title:
            # KrogerProvider sets title as "Brand Description" — grab first word(s)
            # as a heuristic when no structured brand field is available
            title_parts = kroger_bid.item_title.split()
            if title_parts:
                inferred_brand = title_parts[0]

        changed = False
        if inferred_sku and not row.retailer_sku:
            row.retailer_sku = inferred_sku
            changed = True
        if inferred_brand and not row.brand_name:
            row.brand_name = inferred_brand
            changed = True

        if changed:
            row.updated_at = datetime.utcnow()
            session.add(row)
            await session.commit()
            logger.info(
                f"[Pop CPG] Row {row.id}: brand_name={row.brand_name!r}, "
                f"retailer_sku={row.retailer_sku!r}"
            )

        # 2. Outreach Queue — queue a CouponCampaign if brand has no active swap
        brand = row.brand_name
        if not brand:
            return

        active_swap_stmt = (
            select(PopSwap)
            .where(PopSwap.brand_name == brand)
            .where(PopSwap.is_active == True)
            .limit(1)
        )
        active_swap_result = await session.execute(active_swap_stmt)
        if active_swap_result.scalar_one_or_none():
            return  # brand already has an active coupon — nothing to queue

        # Check if a pending/sent campaign already exists for this brand
        existing_campaign_stmt = (
            select(CouponCampaign)
            .where(CouponCampaign.brand_name == brand)
            .where(CouponCampaign.status.in_(["pending", "sent"]))
            .limit(1)
        )
        existing_result = await session.execute(existing_campaign_stmt)
        existing_campaign = existing_result.scalar_one_or_none()

        if existing_campaign:
            # Increment intent_count so the brand sees growing demand
            existing_campaign.intent_count = (existing_campaign.intent_count or 0) + 1
            existing_campaign.updated_at = datetime.utcnow()
            session.add(existing_campaign)
            await session.commit()
            logger.info(
                f"[Pop CPG] Incremented intent_count for campaign "
                f"{existing_campaign.id} (brand={brand!r})"
            )
        else:
            # Create a new CouponCampaign for outreach
            campaign = CouponCampaign(
                brand_name=brand,
                category=row.title or brand,
                target_product=row.title,
                intent_count=1,
                status="pending",
            )
            session.add(campaign)
            await session.commit()
            logger.info(
                f"[Pop CPG] Created CouponCampaign for brand={brand!r} "
                f"(row_id={row.id})"
            )

    except Exception as exc:
        logger.warning(f"[Pop CPG] Enrichment failed for row {row.id}: {exc}")


async def process_pop_message(
    user_email: str,
    message_text: str,
    session: AsyncSession,
    channel: str = "email",
    sender_phone: Optional[str] = None,
    image_urls: Optional[List[str]] = None,
    group_project_id: Optional[int] = None,
    group_phones: Optional[List[str]] = None,
):
    """
    Core logic for Pop:
    1. Identify user (or trigger onboarding)
    2. Identify or create their active Family List (Project), or use group_project_id
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

        # 2. Find active Pop project
        if group_project_id:
            project = await session.get(Project, group_project_id)
            if not project:
                logger.warning(f"[Pop] Provided group_project_id {group_project_id} not found, falling back")
        else:
            project = None

        if not project:
            proj_stmt = (
                select(Project)
                .where(Project.user_id == user.id)
                .where(Project.status == "active")
                .order_by(Project.updated_at.desc())
                .limit(1)
            )
            proj_result = await session.execute(proj_stmt)
            project = proj_result.scalar_one_or_none()

            if not project:
                project = Project(title="My Shopping List", user_id=user.id)
                session.add(project)
                await session.commit()
                await session.refresh(project)
            else:
                from datetime import datetime
                project.updated_at = datetime.utcnow()
                session.add(project)
                await session.commit()

        # Register user as project member (tracks channel preference)
        await _ensure_project_member(session, project.id, user.id, channel=channel)

        # 3. Find active row and load conversation history
        active_row_stmt = (
            select(Row)
            .where(Row.project_id == project.id)
            .where(Row.status.in_(["sourcing", "bids_arriving", "open", "active", "pending"]))
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
            image_urls=image_urls or [],
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
        _META_KEYS = {
            "what", "is_service", "service_category", "search_query", "title",
            "category", "desire_tier", "desire_confidence",
        }
        constraints = {k: v for k, v in (intent.constraints or {}).items() if k not in _META_KEYS}

        # 5. Create or Update Row based on intent
        if action_type in ("create_row", "context_switch") and decision.items and len(decision.items) > 0:
            # Handle multiple items
            for item in decision.items:
                item_title = item.get("what", "")
                if not item_title:
                    continue
                item_title = item_title[0].upper() + item_title[1:]
                item_search_query = item.get("search_query")
                
                row = await _create_row(
                    session, user.id, item_title, project.id,
                    is_service, service_category, constraints, item_search_query,
                    desire_tier=intent.desire_tier,
                    origin_channel=channel,
                )
                target_row = row
                
                factors = await generate_choice_factors(item_title, constraints, is_service, service_category)
                if factors:
                    await _save_choice_factors(session, row, factors)
                
                # Trigger sourcing for each item
                if item_search_query:
                    async for _batch in _stream_search(row.id, item_search_query, authorization=None):
                        pass

                    # CPG enrichment: capture Kroger SKU/brand + queue outreach (PRD-08)
                    await _enrich_row_cpg(session, row)
                    
                    try:
                        from sqlmodel import select as sql_select
                        from models.bids import Bid
                        bids_result = await session.execute(
                            sql_select(Bid).where(Bid.row_id == row.id).order_by(Bid.combined_score.desc().nullslast()).limit(5)
                        )
                        bids = list(bids_result.scalars().all())
                        ui_schema = build_ui_schema(decision.ui_hint, row, bids)
                        row.ui_schema = ui_schema
                        row.ui_schema_version = (row.ui_schema_version or 0) + 1
                        session.add(row)
                        await session.commit()
                    except Exception as e:
                        logger.warning(f"[Pop] Failed to build ui_schema for row {row.id}: {e}")

        elif action_type in ("create_row", "context_switch") or (action_type == "search" and not active_row):
            row = await _create_row(
                session, user.id, title, project.id,
                is_service, service_category, constraints, search_query,
                desire_tier=intent.desire_tier,
                origin_channel=channel,
            )
            target_row = row

            factors = await generate_choice_factors(title, constraints, is_service, service_category)
            if factors:
                await _save_choice_factors(session, row, factors)

            # Trigger sourcing
            if search_query:
                async for _batch in _stream_search(target_row.id, search_query, authorization=None):
                    pass

                # CPG enrichment: capture Kroger SKU/brand + queue outreach (PRD-08)
                await _enrich_row_cpg(session, target_row)

                # Build and persist SDUI schema after sourcing
                try:
                    from sqlmodel import select as sql_select
                    from models.bids import Bid
                    bids_result = await session.execute(
                        sql_select(Bid).where(Bid.row_id == target_row.id).order_by(Bid.combined_score.desc().nullslast()).limit(5)
                    )
                    bids = list(bids_result.scalars().all())
                    ui_schema = build_ui_schema(decision.ui_hint, target_row, bids)
                    target_row.ui_schema = ui_schema
                    target_row.ui_schema_version = (target_row.ui_schema_version or 0) + 1
                    session.add(target_row)
                    await session.commit()
                except Exception as e:
                    logger.warning(f"[Pop] Failed to build ui_schema for row {target_row.id}: {e}")

        elif action_type == "update_row" and active_row:
            row = await _update_row(
                session, active_row,
                title=title if active_row.title != title else None,
                constraints=constraints if constraints else None,
                reset_bids=bool(search_query),
            )
            target_row = row

            # Trigger sourcing
            if search_query:
                async for _batch in _stream_search(target_row.id, search_query, authorization=None):
                    pass

                # CPG enrichment: capture Kroger SKU/brand + queue outreach (PRD-08)
                await _enrich_row_cpg(session, target_row)

                # Build and persist SDUI schema after sourcing
                try:
                    from sqlmodel import select as sql_select
                    from models.bids import Bid
                    bids_result = await session.execute(
                        sql_select(Bid).where(Bid.row_id == target_row.id).order_by(Bid.combined_score.desc().nullslast()).limit(5)
                    )
                    bids = list(bids_result.scalars().all())
                    ui_schema = build_ui_schema(decision.ui_hint, target_row, bids)
                    target_row.ui_schema = ui_schema
                    target_row.ui_schema_version = (target_row.ui_schema_version or 0) + 1
                    session.add(target_row)
                    await session.commit()
                except Exception as e:
                    logger.warning(f"[Pop] Failed to build ui_schema for row {target_row.id}: {e}")

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
            if group_phones and len(group_phones) > 1:
                from routes.pop_notify import send_pop_group_sms
                sent_count = send_pop_group_sms(group_phones, reply_message)
                logger.info(f"[Pop] Group SMS reply sent to {sent_count}/{len(group_phones)} numbers")
            else:
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
