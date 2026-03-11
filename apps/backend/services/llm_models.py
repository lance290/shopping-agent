"""
LLM data models — shared between main llm.py and llm_pop.py.
"""
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

# Valid desire tiers — drives downstream routing
DESIRE_TIERS = ("commodity", "considered", "service", "bespoke", "high_value", "advisory")

# Execution modes — maps to triage PRD §7.2
EXECUTION_MODES = ("affiliate_only", "sourcing_only", "affiliate_plus_sourcing")

# Search strategies — maps to sourcing PRD §15
SEARCH_STRATEGIES = (
    "official_first", "market_first", "specialist_first",
    "prestige_first", "local_network_first",
)

# Source archetypes — maps to sourcing PRD §11.3
SOURCE_ARCHETYPES = (
    "brokerage", "association", "registry", "curated_marketplace",
    "editorial_ranking", "local_directory", "prior_trusted_source",
    "brand_direct", "auction_house", "official_body",
)


LocationRelevance = Literal["none", "endpoint", "service_area", "vendor_proximity"]


class LocationTargets(BaseModel):
    origin: Optional[str] = None
    destination: Optional[str] = None
    service_location: Optional[str] = None
    search_area: Optional[str] = None
    vendor_market: Optional[str] = None


class LocationContext(BaseModel):
    relevance: LocationRelevance = "none"
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    targets: LocationTargets = Field(default_factory=LocationTargets)
    notes: Optional[str] = None


class UserIntent(BaseModel):
    what: str
    category: str = "request"
    service_type: Optional[str] = None  # vendor_category hint (e.g. "private_aviation")
    search_query: Optional[str] = None
    constraints: Dict[str, Any] = Field(default_factory=dict)
    location_context: Optional[LocationContext] = None
    desire_tier: str = "commodity"  # one of DESIRE_TIERS
    desire_confidence: float = 0.8  # 0.0-1.0
    execution_mode: Optional[str] = None  # one of EXECUTION_MODES
    search_strategies: List[str] = Field(default_factory=list)  # subset of SEARCH_STRATEGIES
    source_archetypes: List[str] = Field(default_factory=list)  # subset of SOURCE_ARCHETYPES


class ClarificationAction(BaseModel):
    type: str = "ask_clarification"
    missing_fields: List[str] = Field(default_factory=list)


class DisambiguateOption(BaseModel):
    label: str
    search_query: str
    category: str


class DisambiguateAction(BaseModel):
    type: str = "disambiguate"
    options: List[DisambiguateOption] = Field(default_factory=list)


class SimpleAction(BaseModel):
    type: str  # create_row, update_row, context_switch, search, vendor_outreach


class UnifiedDecision(BaseModel):
    message: str
    intent: UserIntent
    action: Dict[str, Any]  # flexible to handle all action types
    items: Optional[List[Dict[str, str]]] = None  # multi-item responses
    project_title: Optional[str] = None  # Name for a group of items
    ui_hint: Optional[Dict[str, Any]] = None  # SDUI layout hint from LLM

    @property
    def desire_tier(self) -> str:
        return self.intent.desire_tier if self.intent.desire_tier in DESIRE_TIERS else "commodity"

    @property
    def skip_web_search(self) -> bool:
        """Service/bespoke/high-value/advisory tiers skip web search — it can't help."""
        return self.desire_tier in ("service", "bespoke", "high_value", "advisory")


class VendorCoverageAssessment(BaseModel):
    should_log_gap: bool = False
    gap_type: str = "sufficient_coverage"
    canonical_need: str
    vendor_query: Optional[str] = None
    geo_hint: Optional[str] = None
    summary: str
    rationale: Optional[str] = None
    suggested_vendor_search_queries: List[str] = []
    confidence: float = 0.0


class ChatContext(BaseModel):
    user_message: str
    conversation_history: List[Dict[str, str]]
    active_row: Optional[Dict[str, Any]] = None
    active_project: Optional[Dict[str, Any]] = None
    pending_clarification: Optional[Dict[str, Any]] = None
    image_urls: Optional[List[str]] = None
