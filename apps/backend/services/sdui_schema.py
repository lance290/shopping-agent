"""
SDUI Schema Validation — Pydantic models mirroring PRD-SDUI-Schema-Spec.md (v0).

This is the single source of truth for SDUI block shapes, layout tokens,
action intents, and validation limits.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_BLOCKS_PER_ROW = 8
MAX_MARKDOWN_LENGTH = 500
MAX_DATAGRID_ITEMS = 12
MAX_ACTION_ROW_ACTIONS = 3
GROCERY_BID_CAP = 5
RETAIL_BID_CAP = 30

LAYOUT_TOKENS = ("ROW_COMPACT", "ROW_MEDIA_LEFT", "ROW_TIMELINE")

VALUE_VECTORS = ("unit_price", "safety", "speed", "reliability", "durability")

BLOCK_TYPES = (
    "ProductImage",
    "PriceBlock",
    "DataGrid",
    "FeatureList",
    "BadgeList",
    "MarkdownText",
    "Timeline",
    "MessageList",
    "ChoiceFactorForm",
    "ActionRow",
    "ReceiptUploader",
    "WalletLedger",
    "EscrowStatus",
)

ACTION_INTENTS = (
    "outbound_affiliate",
    "claim_swap",
    "fund_escrow",
    "send_tip",
    "contact_vendor",
    "view_all_bids",
    "view_raw",
    "edit_request",
)

# Post-purchase block types that require backend state verification
STATE_DRIVEN_BLOCKS = ("ReceiptUploader", "WalletLedger", "EscrowStatus")


# ---------------------------------------------------------------------------
# Layout Token Enum
# ---------------------------------------------------------------------------

class LayoutToken(str, Enum):
    ROW_COMPACT = "ROW_COMPACT"
    ROW_MEDIA_LEFT = "ROW_MEDIA_LEFT"
    ROW_TIMELINE = "ROW_TIMELINE"


# ---------------------------------------------------------------------------
# Block Models
# ---------------------------------------------------------------------------

class ProductImageBlock(BaseModel):
    type: Literal["ProductImage"] = "ProductImage"
    url: str
    alt: str = ""


class PriceBlockItem(BaseModel):
    amount: Optional[float] = None
    currency: str = "USD"
    label: str = "Total"


class PriceBlock(BaseModel):
    type: Literal["PriceBlock"] = "PriceBlock"
    amount: Optional[float] = None
    currency: str = "USD"
    label: str = "Total"


class DataGridItem(BaseModel):
    key: str
    value: str


class DataGridBlock(BaseModel):
    type: Literal["DataGrid"] = "DataGrid"
    items: List[DataGridItem] = Field(default_factory=list)

    @field_validator("items")
    @classmethod
    def limit_items(cls, v: List[DataGridItem]) -> List[DataGridItem]:
        if len(v) > MAX_DATAGRID_ITEMS:
            return v[:MAX_DATAGRID_ITEMS]
        return v


class FeatureListBlock(BaseModel):
    type: Literal["FeatureList"] = "FeatureList"
    features: List[str] = Field(default_factory=list)


class BadgeListBlock(BaseModel):
    type: Literal["BadgeList"] = "BadgeList"
    tags: List[str] = Field(default_factory=list)
    source_refs: Optional[List[str]] = None


class MarkdownTextBlock(BaseModel):
    type: Literal["MarkdownText"] = "MarkdownText"
    content: str = ""

    @field_validator("content")
    @classmethod
    def truncate_content(cls, v: str) -> str:
        if len(v) > MAX_MARKDOWN_LENGTH:
            return v[:MAX_MARKDOWN_LENGTH]
        return v


class TimelineStep(BaseModel):
    label: str
    status: Literal["pending", "active", "done"] = "pending"


class TimelineBlock(BaseModel):
    type: Literal["Timeline"] = "Timeline"
    steps: List[TimelineStep] = Field(default_factory=list)


class MessageItem(BaseModel):
    sender: str
    text: str


class MessageListBlock(BaseModel):
    type: Literal["MessageList"] = "MessageList"
    messages: List[MessageItem] = Field(default_factory=list)


class ChoiceFactorFormBlock(BaseModel):
    type: Literal["ChoiceFactorForm"] = "ChoiceFactorForm"
    factors: List[Dict[str, Any]] = Field(default_factory=list)


class ActionObject(BaseModel):
    label: str
    intent: str
    bid_id: Optional[str] = None
    url: Optional[str] = None
    merchant_id: Optional[str] = None
    product_id: Optional[str] = None
    amount: Optional[float] = None
    count: Optional[int] = None

    @field_validator("intent")
    @classmethod
    def validate_intent(cls, v: str) -> str:
        if v not in ACTION_INTENTS:
            raise ValueError(f"Unknown intent: {v}. Must be one of {ACTION_INTENTS}")
        return v


class ActionRowBlock(BaseModel):
    type: Literal["ActionRow"] = "ActionRow"
    actions: List[ActionObject] = Field(default_factory=list)

    @field_validator("actions")
    @classmethod
    def limit_actions(cls, v: List[ActionObject]) -> List[ActionObject]:
        if len(v) > MAX_ACTION_ROW_ACTIONS:
            return v[:MAX_ACTION_ROW_ACTIONS]
        return v


class ReceiptUploaderBlock(BaseModel):
    type: Literal["ReceiptUploader"] = "ReceiptUploader"
    campaign_id: str = ""


class WalletLedgerBlock(BaseModel):
    type: Literal["WalletLedger"] = "WalletLedger"


class EscrowStatusBlock(BaseModel):
    type: Literal["EscrowStatus"] = "EscrowStatus"
    deal_id: str = ""


# Union of all block types for validation
UIBlock = Union[
    ProductImageBlock,
    PriceBlock,
    DataGridBlock,
    FeatureListBlock,
    BadgeListBlock,
    MarkdownTextBlock,
    TimelineBlock,
    MessageListBlock,
    ChoiceFactorFormBlock,
    ActionRowBlock,
    ReceiptUploaderBlock,
    WalletLedgerBlock,
    EscrowStatusBlock,
]


# ---------------------------------------------------------------------------
# Top-Level Schema
# ---------------------------------------------------------------------------

class UISchema(BaseModel):
    """Top-level ui_schema object stored on Project, Row, or Bid."""
    version: int = 1
    layout: LayoutToken
    value_vector: Optional[str] = None
    value_rationale_refs: Optional[List[str]] = None
    blocks: List[UIBlock] = Field(default_factory=list)

    @field_validator("value_vector")
    @classmethod
    def validate_value_vector(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALUE_VECTORS:
            logger.warning(f"Unknown value_vector: {v}")
            return None
        return v

    @model_validator(mode="after")
    def enforce_block_limit(self) -> "UISchema":
        if len(self.blocks) > MAX_BLOCKS_PER_ROW:
            self.blocks = self.blocks[:MAX_BLOCKS_PER_ROW]
        return self


# ---------------------------------------------------------------------------
# UIHint — lightweight LLM output
# ---------------------------------------------------------------------------

class UIHint(BaseModel):
    """The lightweight blueprint the LLM outputs."""
    layout: LayoutToken
    blocks: List[str] = Field(default_factory=list)
    value_vector: Optional[str] = None

    @field_validator("blocks")
    @classmethod
    def validate_block_types(cls, v: List[str]) -> List[str]:
        valid = [b for b in v if b in BLOCK_TYPES]
        if len(valid) != len(v):
            unknown = [b for b in v if b not in BLOCK_TYPES]
            logger.warning(f"Stripped unknown block types from ui_hint: {unknown}")
        return valid[:MAX_BLOCKS_PER_ROW]


# ---------------------------------------------------------------------------
# ProjectUIHint — list-level hint
# ---------------------------------------------------------------------------

class ProjectUIHint(BaseModel):
    """Project-level UI hint for list headers."""
    blocks: List[str] = Field(default_factory=list)

    @field_validator("blocks")
    @classmethod
    def validate_block_types(cls, v: List[str]) -> List[str]:
        valid = [b for b in v if b in BLOCK_TYPES]
        return valid


# ---------------------------------------------------------------------------
# Validation Helpers
# ---------------------------------------------------------------------------

def validate_ui_schema(data: Dict[str, Any]) -> Optional[UISchema]:
    """Validate a raw dict as a UISchema. Returns None on failure."""
    try:
        return UISchema(**data)
    except Exception as e:
        logger.warning(f"UISchema validation failed: {e}")
        return None


def validate_ui_hint(data: Dict[str, Any]) -> Optional[UIHint]:
    """Validate a raw dict as a UIHint. Returns None on failure."""
    try:
        return UIHint(**data)
    except Exception as e:
        logger.warning(f"UIHint validation failed: {e}")
        return None


def strip_unknown_blocks(schema_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Remove blocks with unknown types from a schema dict."""
    if "blocks" not in schema_dict:
        return schema_dict
    schema_dict["blocks"] = [
        b for b in schema_dict["blocks"]
        if isinstance(b, dict) and b.get("type") in BLOCK_TYPES
    ]
    return schema_dict


MINIMUM_VIABLE_ROW_SCHEMA = {
    "version": 1,
    "layout": "ROW_COMPACT",
    "blocks": [
        {"type": "MarkdownText", "content": "**Loading...**"},
        {"type": "BadgeList", "tags": ["Loading"]},
        {"type": "ActionRow", "actions": [{"label": "View Raw Options", "intent": "view_raw"}]},
    ],
}


def get_minimum_viable_row(title: str = "Untitled", status: str = "sourcing") -> Dict[str, Any]:
    """Return the guaranteed fallback schema for a row."""
    return {
        "version": 1,
        "layout": "ROW_COMPACT",
        "blocks": [
            {"type": "MarkdownText", "content": f"**{title}**"},
            {"type": "BadgeList", "tags": [status]},
            {"type": "ActionRow", "actions": [{"label": "View Raw Options", "intent": "view_raw"}]},
        ],
    }
