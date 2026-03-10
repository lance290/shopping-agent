"""Heuristic-first classification for live discovery candidates."""

from __future__ import annotations

import logging
import os
import re
from dataclasses import asdict, dataclass, field
from typing import Iterable, Sequence
from urllib.parse import urlparse

import httpx

from models.rows import Row
from sourcing.discovery.adapters.base import DiscoveryCandidate
from sourcing.models import SearchIntent

logger = logging.getLogger(__name__)

DIRECTORY_DOMAINS = {
    "zillow.com",
    "realtor.com",
    "redfin.com",
    "trulia.com",
    "loopnet.com",
    "yelp.com",
    "yellowpages.com",
    "tripadvisor.com",
    "houzz.com",
}
MARKETPLACE_DOMAINS = {
    "ebay.com",
    "stockx.com",
    "goat.com",
    "1stdibs.com",
    "chrono24.com",
    "controller.com",
    "yachtworld.com",
    "avbuyer.com",
}
EDITORIAL_DOMAINS = {
    "forbes.com",
    "robbreport.com",
    "architecturaldigest.com",
    "travelandleisure.com",
}
BROKERAGE_TERMS = (
    "broker",
    "brokerage",
    "agent",
    "team",
    "group",
    "real estate",
    "realtor",
    "charter",
    "aviation",
    "advisors",
    "advisory",
)
LISTING_TERMS = (
    "for sale",
    "listing",
    "listings",
    "property details",
    "view property",
    "inventory",
    "available now",
    "mls",
    "auction lot",
)
MARKETPLACE_TERMS = (
    "marketplace",
    "exchange",
    "auction",
    "dealer network",
    "inventory",
    "brokers",
    "compare offers",
)
EDITORIAL_TERMS = (
    "blog",
    "article",
    "news",
    "guide",
    "review",
    "resources",
    "discover",
    "our regions",
)
PAGE_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
META_DESC_RE = re.compile(
    r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
    re.I | re.S,
)


@dataclass
class DiscoveryClassification:
    candidate_type: str
    confidence: float
    official_site: bool
    first_party_contact: bool
    location_evidence: list[str] = field(default_factory=list)
    service_category_evidence: list[str] = field(default_factory=list)
    trust_signals: dict[str, object] = field(default_factory=dict)
    rejection_reasons: list[str] = field(default_factory=list)

    def model_dump(self) -> dict[str, object]:
        return asdict(self)


def _location_terms(intent: SearchIntent | None) -> list[str]:
    if not intent:
        return []
    targets = intent.location_context.targets.non_empty_items()
    terms: list[str] = []
    for value in targets.values():
        for part in re.split(r"[,/]| - ", value):
            cleaned = part.strip()
            if cleaned:
                terms.append(cleaned)
    dedup: dict[str, str] = {}
    for item in terms:
        key = item.casefold()
        if key not in dedup:
            dedup[key] = item
    return list(dedup.values())


def _service_terms(intent: SearchIntent | None, row: Row | None) -> list[str]:
    tokens: list[str] = []
    if intent:
        tokens.extend(intent.keywords)
        if intent.product_name:
            tokens.extend(intent.product_name.split())
        if intent.product_category:
            tokens.extend(intent.product_category.replace("_", " ").split())
    if row:
        if row.service_category:
            tokens.extend(str(row.service_category).replace("_", " ").split())
        if row.title:
            tokens.extend(str(row.title).split())
    dedup: dict[str, str] = {}
    for token in tokens:
        cleaned = token.strip().lower()
        if len(cleaned) < 3:
            continue
        if cleaned not in dedup:
            dedup[cleaned] = cleaned
    return list(dedup.values())


def _matches_terms(text: str, terms: Sequence[str]) -> list[str]:
    haystack = text.casefold()
    matches: list[str] = []
    for term in terms:
        if term and term.casefold() in haystack:
            matches.append(term)
    return matches


def _domain_title_alignment(candidate: DiscoveryCandidate) -> bool:
    domain = (candidate.canonical_domain or "").replace("-", " ").replace(".", " ")
    title = (candidate.title or "").casefold()
    if not domain or not title:
        return False
    pieces = [part for part in domain.split() if len(part) > 3 and part not in {"www", "com"}]
    return any(piece in title for piece in pieces)


def _contact_domain_match(candidate: DiscoveryCandidate) -> bool:
    if not candidate.email or not candidate.canonical_domain:
        return False
    email_domain = candidate.email.split("@")[-1].lower()
    return email_domain == candidate.canonical_domain.lower()


async def enrich_candidates_for_classification(
    candidates: Sequence[DiscoveryCandidate],
    *,
    top_n: int = 3,
    timeout_seconds: float = 1.5,
) -> None:
    if not _shallow_fetch_enabled():
        return
    for candidate in list(candidates)[:top_n]:
        if candidate.extraction_payload.get("page_title") or not candidate.url.startswith("http"):
            continue
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=timeout_seconds) as client:
                response = await client.get(candidate.url)
                response.raise_for_status()
                html = response.text[:15000]
        except Exception as exc:
            logger.debug("[VendorDiscovery] shallow fetch failed for %s: %s", candidate.url, exc)
            continue

        title_match = PAGE_TITLE_RE.search(html)
        meta_match = META_DESC_RE.search(html)
        if title_match:
            candidate.extraction_payload["page_title"] = " ".join(title_match.group(1).split())
        if meta_match:
            candidate.extraction_payload["meta_description"] = " ".join(meta_match.group(1).split())


def _shallow_fetch_enabled() -> bool:
    value = os.getenv("DISCOVERY_SHALLOW_FETCH_ENABLED", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def classify_candidate(
    candidate: DiscoveryCandidate,
    *,
    discovery_mode: str,
    intent: SearchIntent | None,
    row: Row | None,
) -> DiscoveryClassification:
    parsed = urlparse(candidate.url)
    path = parsed.path.lower()
    domain = (candidate.canonical_domain or "").lower()
    fetched_title = str(candidate.extraction_payload.get("page_title") or "")
    fetched_desc = str(candidate.extraction_payload.get("meta_description") or "")
    text = " ".join(
        part
        for part in [
            candidate.title,
            candidate.snippet,
            fetched_title,
            fetched_desc,
            candidate.location_hint or "",
            domain.replace(".", " "),
            path.replace("/", " "),
        ]
        if part
    ).lower()

    location_evidence = _matches_terms(text, _location_terms(intent))
    service_evidence = _matches_terms(text, _service_terms(intent, row))
    first_party_contact = bool(candidate.first_party_contact or _contact_domain_match(candidate))
    aligned = _domain_title_alignment(candidate)

    candidate_type = "editorial_or_irrelevant"
    confidence = 0.55

    if domain in DIRECTORY_DOMAINS or any(term in text for term in ("directory", "find an agent", "compare agents")):
        candidate_type = "directory_or_aggregator"
        confidence = 0.85
    elif domain in EDITORIAL_DOMAINS or any(term in text for term in EDITORIAL_TERMS):
        candidate_type = "editorial_or_irrelevant"
        confidence = 0.82
    elif any(term in text or term in path for term in LISTING_TERMS) and not any(term in text for term in BROKERAGE_TERMS):
        candidate_type = "listing_or_inventory_page"
        confidence = 0.82
    elif domain in MARKETPLACE_DOMAINS or any(term in text for term in MARKETPLACE_TERMS):
        candidate_type = "marketplace_or_exchange"
        confidence = 0.8
    elif any(term in text or term in path for term in BROKERAGE_TERMS):
        candidate_type = "brokerage_or_agent_site"
        confidence = 0.84 if (aligned or first_party_contact) else 0.72
    elif any(term in text for term in ("official", "contact us", "services", "about us")) or aligned:
        candidate_type = "official_vendor_site"
        confidence = 0.72
    elif discovery_mode in {"uhnw_goods_discovery"} and any(term in text for term in ("brand", "manufacturer", "collection", "heritage")):
        candidate_type = "brand_site"
        confidence = 0.68

    if candidate_type == "listing_or_inventory_page" and discovery_mode == "asset_market_discovery":
        candidate_type = "marketplace_or_exchange"
        confidence = max(confidence, 0.66)

    official_site = candidate_type in {"official_vendor_site", "brand_site", "brokerage_or_agent_site"}
    trust_signals = dict(candidate.trust_signals or {})
    trust_signals.update(
        {
            "domain_title_alignment": aligned,
            "location_matches": location_evidence,
            "service_matches": service_evidence,
            "known_directory_domain": domain in DIRECTORY_DOMAINS,
            "known_marketplace_domain": domain in MARKETPLACE_DOMAINS,
            "known_editorial_domain": domain in EDITORIAL_DOMAINS,
        }
    )

    classification = DiscoveryClassification(
        candidate_type=candidate_type,
        confidence=round(confidence, 4),
        official_site=official_site,
        first_party_contact=first_party_contact,
        location_evidence=location_evidence,
        service_category_evidence=service_evidence,
        trust_signals=trust_signals,
    )
    candidate.classification = classification.model_dump()
    candidate.official_site = official_site
    candidate.first_party_contact = first_party_contact
    candidate.trust_signals = trust_signals
    return classification


def classify_candidates(
    candidates: Iterable[DiscoveryCandidate],
    *,
    discovery_mode: str,
    intent: SearchIntent | None,
    row: Row | None,
) -> list[DiscoveryCandidate]:
    classified: list[DiscoveryCandidate] = []
    for candidate in candidates:
        classify_candidate(candidate, discovery_mode=discovery_mode, intent=intent, row=row)
        classified.append(candidate)
    return classified
