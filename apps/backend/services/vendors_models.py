"""
Vendor data models — Vendor and ChecklistItem dataclasses.
Extracted from services/vendors.py.
"""
from typing import Optional, Dict, Any
from dataclasses import dataclass, field, asdict


@dataclass
class Vendor:
    name: str
    company: str
    email: str
    phone: Optional[str] = None
    category: str = "private_aviation"
    source: str = "wattdata"
    image_url: Optional[str] = None
    # Rich fields from provider research
    website: Optional[str] = None
    provider_type: Optional[str] = None  # Operator / Broker / Platform / Services
    fleet: Optional[str] = None  # Published fleet / aircraft
    jet_sizes: Optional[str] = None  # Light / Midsize / Heavy etc.
    wifi: Optional[str] = None  # Connectivity details
    starlink: Optional[str] = None  # Starlink availability
    pricing_info: Optional[str] = None  # Pricing model
    availability: Optional[str] = None  # Lead time / availability info
    safety_certs: Optional[str] = None  # ARGUS / Wyvern / IS-BAO / Part 135
    notes: Optional[str] = None  # Caveats and notes
    source_urls: Optional[str] = None  # Public reference URLs
    last_verified: Optional[str] = None  # Date of last verification
    # Searchable text blob (auto-built)
    _search_text: Optional[str] = field(default=None, repr=False)

    def get_search_text(self) -> str:
        """Build a single searchable text blob from all fields."""
        if self._search_text:
            return self._search_text
        parts = [
            self.company, self.name, self.email,
            self.provider_type or "", self.fleet or "",
            self.jet_sizes or "", self.wifi or "",
            self.starlink or "", self.pricing_info or "",
            self.availability or "", self.safety_certs or "",
            self.notes or "", self.website or "",
        ]
        self._search_text = " ".join(p for p in parts if p).lower()
        return self._search_text

    def to_rich_dict(self) -> Dict[str, Any]:
        """Return all fields as a dict for API responses."""
        d = asdict(self)
        d.pop("_search_text", None)
        return d


@dataclass
class ChecklistItem:
    category: str  # e.g. "Fleet & connectivity"
    item: str  # What to check
    why_it_matters: str
    how_to_verify: str
    must_have: bool  # Y/N from spreadsheet
