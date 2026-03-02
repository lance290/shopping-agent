"""
SDUI Builder — hydrates LLM-selected UI blueprints with real data.

The LLM selects layout + block types (ui_hint). This builder fills in
every field value from structured Row/Bid data. The LLM NEVER populates
prices, URLs, or images.

See PRD-SDUI-Schema-Spec.md §8.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from services.sdui_schema import (
    BLOCK_TYPES,
    GROCERY_BID_CAP,
    RETAIL_BID_CAP,
    STATE_DRIVEN_BLOCKS,
    ActionObject,
    ActionRowBlock,
    BadgeListBlock,
    ChoiceFactorFormBlock,
    DataGridBlock,
    DataGridItem,
    EscrowStatusBlock,
    FeatureListBlock,
    LayoutToken,
    MarkdownTextBlock,
    MessageListBlock,
    MessageItem,
    PriceBlock,
    ProductImageBlock,
    ReceiptUploaderBlock,
    TimelineBlock,
    TimelineStep,
    UIBlock,
    UIHint,
    UISchema,
    WalletLedgerBlock,
    get_minimum_viable_row,
    validate_ui_hint,
)

if TYPE_CHECKING:
    from models.rows import Row, Project
    from models.bids import Bid

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Deterministic Fallback (when LLM omits or returns invalid ui_hint)
# ---------------------------------------------------------------------------

def derive_layout_fallback(row: "Row", bids: List["Bid"]) -> UIHint:
    """Last resort when LLM ui_hint is missing or invalid."""
    if _is_post_decision_fulfillment(row, bids):
        return UIHint(
            layout=LayoutToken.ROW_TIMELINE,
            blocks=["MarkdownText", "Timeline", "ActionRow"],
        )

    if any(getattr(b, "image_url", None) for b in bids):
        return UIHint(
            layout=LayoutToken.ROW_MEDIA_LEFT,
            blocks=["ProductImage", "PriceBlock", "BadgeList", "ActionRow"],
        )

    return UIHint(
        layout=LayoutToken.ROW_COMPACT,
        blocks=["MarkdownText", "PriceBlock", "ActionRow"],
    )


def _is_post_decision_fulfillment(row: "Row", bids: List["Bid"]) -> bool:
    """Check if the row is in a post-decision state (tracking fulfillment)."""
    status = getattr(row, "status", "sourcing")
    post_decision_statuses = ("closed", "funded", "in_transit", "completed", "delivered")
    if status in post_decision_statuses:
        return True
    # If any bid has a closing_status that indicates active fulfillment
    for bid in bids:
        cs = getattr(bid, "closing_status", None)
        if cs and cs in ("paid", "shipped", "delivered", "contract_signed"):
            return True
    return False


# ---------------------------------------------------------------------------
# Bid Cap (domain-aware)
# ---------------------------------------------------------------------------

def get_bid_cap(row: "Row", bids: List["Bid"]) -> int:
    """Return the max number of bids to hydrate based on domain."""
    # If any bid is a swap, treat as grocery
    if any(getattr(b, "is_swap", None) for b in bids):
        return GROCERY_BID_CAP
    # Check row-level signals
    service_category = getattr(row, "service_category", None)
    is_service = getattr(row, "is_service", False)
    if is_service or service_category:
        return RETAIL_BID_CAP
    # Default to retail cap for general product searches
    return RETAIL_BID_CAP


# ---------------------------------------------------------------------------
# Block Hydrators
# ---------------------------------------------------------------------------

def _hydrate_product_image(row: "Row", bids: List["Bid"]) -> Optional[ProductImageBlock]:
    """Hydrate ProductImage from the top bid's image."""
    for bid in bids:
        img = getattr(bid, "image_url", None)
        if img:
            return ProductImageBlock(url=img, alt=getattr(bid, "item_title", ""))
    return None


def _hydrate_price_block(row: "Row", bids: List["Bid"]) -> Optional[PriceBlock]:
    """Hydrate PriceBlock from the top bid's price."""
    for bid in bids:
        price = getattr(bid, "price", None)
        if price is not None:
            return PriceBlock(
                amount=price,
                currency=getattr(bid, "currency", "USD"),
                label="Best Price",
            )
    # All bids are quote-based
    if bids:
        return PriceBlock(amount=None, currency="USD", label="Request Quote")
    return None


def _hydrate_data_grid(row: "Row", bids: List["Bid"]) -> Optional[DataGridBlock]:
    """Hydrate DataGrid from row constraints."""
    items: List[DataGridItem] = []
    choice_answers = getattr(row, "choice_answers", None)
    if choice_answers and isinstance(choice_answers, dict):
        for key, value in list(choice_answers.items())[:12]:
            items.append(DataGridItem(key=str(key), value=str(value)))
    if not items:
        return None
    return DataGridBlock(items=items)


def _hydrate_feature_list(row: "Row", bids: List["Bid"]) -> Optional[FeatureListBlock]:
    """Hydrate FeatureList from bid provenance matched_features."""
    features: List[str] = []
    for bid in bids[:3]:
        prov = getattr(bid, "provenance", None)
        if prov and isinstance(prov, dict):
            mf = prov.get("matched_features", [])
            if isinstance(mf, list):
                features.extend(mf)
    if not features:
        return None
    return FeatureListBlock(features=list(dict.fromkeys(features))[:10])


def _hydrate_badge_list(row: "Row", bids: List["Bid"]) -> Optional[BadgeListBlock]:
    """Hydrate BadgeList from row status and bid sources."""
    tags: List[str] = []
    status = getattr(row, "status", "sourcing")
    if status:
        tags.append(status.replace("_", " ").title())
    sources = set()
    for bid in bids[:5]:
        src = getattr(bid, "source", "")
        if src and src != "manual":
            sources.add(src)
    for s in sorted(sources):
        tags.append(s.replace("_", " ").title())
    # Check for swaps
    if any(getattr(b, "is_swap", None) for b in bids):
        tags.append("Pop Swap")
    return BadgeListBlock(tags=tags) if tags else None


def _hydrate_markdown_text(row: "Row", bids: List["Bid"]) -> Optional[MarkdownTextBlock]:
    """Hydrate MarkdownText — row title as bold header."""
    title = getattr(row, "title", "Untitled")
    return MarkdownTextBlock(content=f"**{title}**")


def _hydrate_timeline(row: "Row", bids: List["Bid"]) -> Optional[TimelineBlock]:
    """Hydrate Timeline from row/bid status for fulfillment tracking."""
    steps: List[TimelineStep] = []
    status = getattr(row, "status", "sourcing")

    pipeline = [
        ("Sourcing", "sourcing"),
        ("Comparing", "shortlisting"),
        ("Negotiating", "negotiating"),
        ("Funded", "funded"),
        ("Delivered", "delivered"),
    ]

    found_current = False
    for label, s in pipeline:
        if s == status:
            steps.append(TimelineStep(label=label, status="active"))
            found_current = True
        elif not found_current:
            steps.append(TimelineStep(label=label, status="done"))
        else:
            steps.append(TimelineStep(label=label, status="pending"))

    if not found_current:
        # Status didn't match pipeline — show generic
        steps = [TimelineStep(label=status.replace("_", " ").title(), status="active")]

    return TimelineBlock(steps=steps)


def _hydrate_message_list(row: "Row", bids: List["Bid"]) -> Optional[MessageListBlock]:
    """Hydrate MessageList from row chat_history (last 3 messages)."""
    chat = getattr(row, "chat_history", None)
    if not chat or not isinstance(chat, list):
        return None
    messages = []
    for msg in chat[-3:]:
        if isinstance(msg, dict):
            messages.append(MessageItem(
                sender=msg.get("role", "system"),
                text=str(msg.get("content", ""))[:200],
            ))
    return MessageListBlock(messages=messages) if messages else None


def _hydrate_choice_factor_form(row: "Row", bids: List["Bid"]) -> Optional[ChoiceFactorFormBlock]:
    """Hydrate ChoiceFactorForm from row.choice_factors."""
    factors = getattr(row, "choice_factors", None)
    if not factors or not isinstance(factors, list):
        return None
    return ChoiceFactorFormBlock(factors=factors)


def _hydrate_action_row(row: "Row", bids: List["Bid"], total_bid_count: Optional[int] = None) -> Optional[ActionRowBlock]:
    """Hydrate default ActionRow based on available bids."""
    actions: List[ActionObject] = []

    # If bids have URLs, add affiliate action for top bid
    for bid in bids[:1]:
        url = getattr(bid, "item_url", None)
        bid_id = getattr(bid, "id", None)
        if url and not url.startswith("mailto:"):
            actions.append(ActionObject(
                label="View Deal",
                intent="outbound_affiliate",
                bid_id=str(bid_id) if bid_id else None,
                url=url,
            ))
            break
        elif url and url.startswith("mailto:"):
            actions.append(ActionObject(
                label="Contact Vendor",
                intent="contact_vendor",
                bid_id=str(bid_id) if bid_id else None,
            ))
            break

    # If more bids than cap, add "View All"
    cap = get_bid_cap(row, bids)
    real_total = total_bid_count if total_bid_count is not None else len(bids)
    if real_total > cap:
        actions.append(ActionObject(
            label=f"View All ({real_total})",
            intent="view_all_bids",
            count=real_total,
        ))

    if not actions:
        actions.append(ActionObject(label="Edit Request", intent="edit_request"))

    return ActionRowBlock(actions=actions[:3])


def _hydrate_receipt_uploader(row: "Row", bids: List["Bid"]) -> Optional[ReceiptUploaderBlock]:
    """Hydrate ReceiptUploader — only if row state permits."""
    # State machine check: only render if a swap has been claimed
    for bid in bids:
        cs = getattr(bid, "closing_status", None)
        if cs == "pending" and getattr(bid, "is_swap", False):
            return ReceiptUploaderBlock(campaign_id=str(getattr(bid, "id", "")))
    return None


def _hydrate_wallet_ledger(row: "Row", bids: List["Bid"]) -> Optional[WalletLedgerBlock]:
    """Hydrate WalletLedger — stub for now."""
    return WalletLedgerBlock()


def _hydrate_escrow_status(row: "Row", bids: List["Bid"]) -> Optional[EscrowStatusBlock]:
    """Hydrate EscrowStatus — only if escrow is active."""
    for bid in bids:
        cs = getattr(bid, "closing_status", None)
        if cs in ("payment_initiated", "paid"):
            return EscrowStatusBlock(deal_id=str(getattr(bid, "id", "")))
    return None


# Block type → hydrator mapping
BLOCK_HYDRATORS = {
    "ProductImage": _hydrate_product_image,
    "PriceBlock": _hydrate_price_block,
    "DataGrid": _hydrate_data_grid,
    "FeatureList": _hydrate_feature_list,
    "BadgeList": _hydrate_badge_list,
    "MarkdownText": _hydrate_markdown_text,
    "Timeline": _hydrate_timeline,
    "MessageList": _hydrate_message_list,
    "ChoiceFactorForm": _hydrate_choice_factor_form,
    "ActionRow": _hydrate_action_row,
    "ReceiptUploader": _hydrate_receipt_uploader,
    "WalletLedger": _hydrate_wallet_ledger,
    "EscrowStatus": _hydrate_escrow_status,
}


# ---------------------------------------------------------------------------
# Main Builder
# ---------------------------------------------------------------------------

def hydrate_ui_schema(
    ui_hint: UIHint,
    row: "Row",
    bids: List["Bid"],
) -> UISchema:
    """
    Hydrate a UISchema from an LLM-selected UIHint + real data.

    The LLM picks the layout and block types; this function fills in
    all field values from structured Row/Bid data.
    """
    schema = UISchema(
        version=1,
        layout=ui_hint.layout,
        value_vector=ui_hint.value_vector,
        blocks=[],
    )

    # Apply bid cap
    cap = get_bid_cap(row, bids)
    total_bid_count = len(bids)
    capped_bids = bids[:cap]

    for block_type in ui_hint.blocks:
        hydrator = BLOCK_HYDRATORS.get(block_type)
        if not hydrator:
            continue

        # ActionRow needs the total count (before capping) for "View All"
        if block_type == "ActionRow":
            block = hydrator(row, capped_bids, total_bid_count=total_bid_count)
        else:
            block = hydrator(row, capped_bids)

        if block:
            schema.blocks.append(block)

    return schema


def build_ui_schema(
    ui_hint_data: Optional[Dict[str, Any]],
    row: "Row",
    bids: List["Bid"],
) -> Dict[str, Any]:
    """
    Top-level entry point. Validates ui_hint, hydrates, falls back if needed.
    Returns a plain dict ready for JSON persistence.
    """
    hint: Optional[UIHint] = None

    if ui_hint_data:
        hint = validate_ui_hint(ui_hint_data)

    if not hint:
        hint = derive_layout_fallback(row, bids)

    try:
        schema = hydrate_ui_schema(hint, row, bids)
        return schema.model_dump()
    except Exception as e:
        logger.error(f"hydrate_ui_schema failed: {e}")
        title = getattr(row, "title", "Untitled")
        status = getattr(row, "status", "sourcing")
        return get_minimum_viable_row(title=title, status=status)


def build_project_ui_schema(project: "Project") -> Dict[str, Any]:
    """Build a Project-level ui_schema (list header)."""
    blocks: List[Dict[str, Any]] = []

    title = getattr(project, "title", "Shopping List")
    blocks.append({"type": "MarkdownText", "content": f"**{title}**"})

    # Default share action
    blocks.append({
        "type": "ActionRow",
        "actions": [{"label": "Share List", "intent": "edit_request"}],
    })

    return {
        "version": 1,
        "layout": "ROW_COMPACT",
        "blocks": blocks,
    }


def build_zero_results_schema(row: "Row") -> Dict[str, Any]:
    """Schema for when sourcing completes with 0 bids."""
    title = getattr(row, "title", "Untitled")
    return {
        "version": 1,
        "layout": "ROW_COMPACT",
        "blocks": [
            {"type": "MarkdownText", "content": f"No options found for **{title}**"},
            {"type": "ActionRow", "actions": [{"label": "Edit Request", "intent": "edit_request"}]},
        ],
    }
