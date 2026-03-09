#!/usr/bin/env python3
"""
Vendor Enrichment Script

Scrapes vendor websites to extract real business details, then uses an LLM
to produce structured enrichment data. Finally re-embeds all vendors.

Pipeline per vendor:
1. Fetch homepage HTML (+ /about, /services if found)
2. Extract visible text (strip nav/footer boilerplate)
3. Send to LLM: "Given this website text for {vendor_name}, extract structured info"
4. Update DB fields: description, profile_text, specialties, tagline
5. Re-embed profile_text via OpenRouter embeddings API

Usage:
    python scripts/enrich_vendors.py [--limit N] [--dry-run] [--skip-embed] [--names-csv CSV_FILE]
"""

import asyncio
import csv
import json
import logging
import os
import re
import ssl
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin, urlparse
import argparse

import aiohttp
from bs4 import BeautifulSoup
import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env before any imports that use env vars
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from database import get_session, engine
from models import Vendor
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker
import sqlalchemy as sa

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-7s %(message)s',
    handlers=[
        logging.FileHandler('vendor_enrichment.log'),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# --- Config ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
SERPAPI_KEY = os.getenv("SERPAPI_API_KEY", "")
SCALESERP_KEY = os.getenv("SCALESERP_API_KEY", "")
SEARCHAPI_KEY = os.getenv("SEARCHAPI_API_KEY", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))
LLM_MODEL = "google/gemini-3-flash-preview"  # cheap + fast for extraction
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
SCRAPE_TIMEOUT = aiohttp.ClientTimeout(total=20, connect=8)

# SSL context for scraping (skip cert verification)
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

# Rate-limit: max concurrent scrapes & LLM calls
SCRAPE_SEM = asyncio.Semaphore(15)
LLM_SEM = asyncio.Semaphore(10)
EMBED_SEM = asyncio.Semaphore(10)
SEARCH_SEM = asyncio.Semaphore(5)

EMAIL_RE = re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", re.IGNORECASE)
PHONE_RE = re.compile(r"(?:\+?1[\s\-.]?)?(?:\(?\d{3}\)?[\s\-.]?)\d{3}[\s\-.]?\d{4}")
CONTACT_KEYWORDS = ("contact", "about", "service", "team", "staff", "agent", "agents", "bio", "profile", "leadership", "realtor")
GENERIC_EMAIL_PREFIXES = ("info", "contact", "hello", "admin", "office", "support", "team", "sales")
SOCIAL_HOSTS = {
    "linkedin.com": "linkedin",
    "facebook.com": "facebook",
    "instagram.com": "instagram",
    "twitter.com": "twitter",
    "x.com": "twitter",
    "youtube.com": "youtube",
}

# --- Scraping ---

def unique_strings(values: List[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for value in values:
        item = (value or "").strip()
        if not item:
            continue
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(item)
    return ordered

def normalize_phone(value: Optional[str]) -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits

def classify_page(url: str, title: str, headings: List[str]) -> str:
    haystack = f"{url} {title} {' '.join(headings)}".lower()
    if "contact" in haystack or "get in touch" in haystack:
        return "contact"
    if any(keyword in haystack for keyword in ("team", "staff", "leadership")):
        return "team"
    if any(keyword in haystack for keyword in ("agent", "agents", "realtor", "bio", "profile")):
        return "agent"
    if any(keyword in haystack for keyword in ("service", "practice area", "what we do")):
        return "services"
    if any(keyword in haystack for keyword in ("about", "our story", "who we are")):
        return "about"
    return "home"

def rank_internal_link(base_domain: str, url: str, anchor_text: str) -> int:
    if extract_domain(url) != base_domain:
        return -1
    haystack = f"{url} {anchor_text}".lower()
    score = 0
    for index, keyword in enumerate(CONTACT_KEYWORDS):
        if keyword in haystack:
            score += 20 - index
    if any(keyword in haystack for keyword in ("contact", "team", "agent", "bio")):
        score += 10
    return score

def rank_email_candidate(vendor: Vendor, email: str, domain: str) -> int:
    local_part, _, email_domain = email.lower().partition("@")
    vendor_tokens = [token for token in re.split(r"[^a-z0-9]+", (vendor.name or "").lower()) if len(token) > 2]
    score = 0
    if domain and (email_domain == domain or email_domain.endswith("." + domain)):
        score += 5
    if local_part and not any(local_part.startswith(prefix) for prefix in GENERIC_EMAIL_PREFIXES):
        score += 4
    if any(token in local_part for token in vendor_tokens):
        score += 4
    if "luxuryhomemagazine.com" not in email_domain:
        score += 1
    return score

def choose_best_email(vendor: Vendor, emails: List[str], domain: str) -> Optional[str]:
    ranked = sorted(unique_strings([email.lower() for email in emails]), key=lambda item: rank_email_candidate(vendor, item, domain), reverse=True)
    return ranked[0] if ranked else None

def extract_supported_emails(text: str) -> List[str]:
    return unique_strings([email.strip().strip(".,;:").lower() for email in EMAIL_RE.findall(text or "") if "@" in email])

def extract_supported_phones(text: str) -> List[str]:
    return unique_strings([match.strip() for match in PHONE_RE.findall(text or "") if normalize_phone(match)])

async def fetch_page_bundle(url: str) -> Optional[Dict[str, Any]]:
    if not url or url == "#":
        return None
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        async with SCRAPE_SEM:
            connector = aiohttp.TCPConnector(ssl=SSL_CTX)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(
                    url, headers={"User-Agent": USER_AGENT}, timeout=SCRAPE_TIMEOUT,
                    allow_redirects=True, max_redirects=5,
                ) as resp:
                    if resp.status != 200:
                        return None
                    final_url = str(resp.url)
                    html = await resp.text()
        soup = BeautifulSoup(html, "html.parser")
        title = (soup.title.string or "").strip() if soup.title and soup.title.string else ""
        meta_description = ""
        for attrs in ({"name": "description"}, {"property": "og:description"}):
            tag = soup.find("meta", attrs=attrs)
            if tag and tag.get("content"):
                meta_description = tag.get("content", "").strip()
                break
        headings = unique_strings([
            heading.get_text(" ", strip=True)
            for heading in soup.find_all(["h1", "h2", "h3"])
            if heading.get_text(" ", strip=True)
        ])[:8]
        explicit_emails = extract_supported_emails(html)
        explicit_phones = extract_supported_phones(html)
        social_links: Dict[str, str] = {}
        internal_links: List[Dict[str, Any]] = []
        base_domain = extract_domain(final_url)
        for anchor in soup.find_all("a", href=True):
            raw_href = (anchor.get("href") or "").strip()
            anchor_text = anchor.get_text(" ", strip=True)
            if raw_href.lower().startswith("mailto:"):
                email = raw_href.split(":", 1)[1].split("?", 1)[0].strip().lower()
                if email:
                    explicit_emails.append(email)
                continue
            if raw_href.lower().startswith("tel:"):
                phone = raw_href.split(":", 1)[1].split("?", 1)[0].strip()
                if phone:
                    explicit_phones.append(phone)
                continue
            absolute_url = urljoin(final_url, raw_href)
            link_domain = extract_domain(absolute_url)
            if not link_domain:
                continue
            for host, label in SOCIAL_HOSTS.items():
                if host in link_domain and label not in social_links:
                    social_links[label] = absolute_url
            score = rank_internal_link(base_domain, absolute_url, anchor_text)
            if score > 0:
                internal_links.append({"url": absolute_url, "anchor": anchor_text[:120], "score": score})
        explicit_emails = unique_strings([email.lower() for email in explicit_emails])
        explicit_phones = unique_strings(explicit_phones)
        for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "iframe", "svg", "form"]):
            tag.decompose()
        text = re.sub(r"\s+", " ", soup.get_text(separator=" ", strip=True)).strip()
        if explicit_emails:
            text = f"{text} Explicit emails: {' ; '.join(explicit_emails[:8])}"
        if explicit_phones:
            text = f"{text} Explicit phones: {' ; '.join(explicit_phones[:6])}"
        internal_links = sorted(internal_links, key=lambda item: item["score"], reverse=True)
        page_type = classify_page(final_url, title, headings)
        return {
            "url": final_url,
            "title": title,
            "meta_description": meta_description,
            "headings": headings,
            "emails": explicit_emails,
            "phones": explicit_phones,
            "text": text[:5000] if text else "",
            "page_type": page_type,
            "internal_links": internal_links[:12],
            "social_links": social_links,
        }
    except Exception:
        return None

async def fetch_text(url: str) -> Optional[str]:
    bundle = await fetch_page_bundle(url)
    return bundle.get("text") if bundle else None

async def crawl_vendor_site_evidence(website: str) -> Optional[Dict[str, Any]]:
    homepage = await fetch_page_bundle(website)
    if not homepage:
        return None
    parsed = urlparse(homepage["url"] if homepage["url"].startswith("http") else f"https://{homepage['url']}")
    base = f"{parsed.scheme}://{parsed.netloc}"
    candidate_urls = [link["url"] for link in homepage.get("internal_links", [])]
    candidate_urls.extend(urljoin(base, path) for path in ["/about", "/about-us", "/services", "/contact", "/contact-us", "/team", "/our-team", "/agents", "/leadership"])
    pages = [homepage]
    visited = {homepage["url"]}
    for candidate in unique_strings(candidate_urls):
        if candidate in visited:
            continue
        if len(pages) >= 6:
            break
        bundle = await fetch_page_bundle(candidate)
        if not bundle:
            continue
        visited.add(bundle["url"])
        if bundle.get("text") or bundle.get("emails") or bundle.get("phones"):
            pages.append(bundle)
    all_emails: List[str] = []
    all_phones: List[str] = []
    social_links: Dict[str, str] = {}
    for page in pages:
        all_emails.extend(page.get("emails", []))
        all_phones.extend(page.get("phones", []))
        for label, link in (page.get("social_links") or {}).items():
            if label not in social_links:
                social_links[label] = link
    return {
        "pages": pages,
        "emails": unique_strings(all_emails),
        "phones": unique_strings(all_phones),
        "social_links": social_links,
        "website": homepage["url"],
    }

async def scrape_vendor_site(website: str) -> str:
    crawl_bundle = await crawl_vendor_site_evidence(website)
    if not crawl_bundle:
        return ""
    combined = "\n\n".join(page.get("text", "") for page in crawl_bundle.get("pages", []) if page.get("text"))
    return combined[:10000]

def extract_domain(url: Optional[str]) -> str:
    if not url:
        return ""
    try:
        parsed = urlparse(url if url.startswith(("http://", "https://")) else f"https://{url}")
        return parsed.netloc.lower().lstrip("www.")
    except Exception:
        return ""


def rank_contact_result(vendor: Vendor, item: Dict[str, str], domain: str) -> int:
    url = item.get("url", "")
    title = item.get("title", "")
    snippet = item.get("snippet", "")
    haystack = f"{url} {title} {snippet}".lower()
    vendor_name = (vendor.name or "").lower()
    score = 0
    if domain and extract_domain(url) == domain:
        score += 5
    if vendor_name and vendor_name in haystack:
        score += 4
    if "@" in haystack or "email" in haystack or "mailto" in haystack:
        score += 4
    for keyword in ("contact", "about", "team", "agent", "agents", "bio", "profile", "staff", "realtor"):
        if keyword in haystack:
            score += 2
    return score


async def search_serpapi(query: str, num: int = 5) -> List[Dict[str, str]]:
    if not SERPAPI_KEY:
        return []
    try:
        async with SEARCH_SEM:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    "https://serpapi.com/search",
                    params={
                        "engine": "google",
                        "q": query,
                        "api_key": SERPAPI_KEY,
                        "num": num,
                        "gl": "us",
                        "hl": "en",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
        return [
            {
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
            }
            for item in data.get("organic_results", [])
        ]
    except Exception:
        return []


async def search_scaleserp(query: str, num: int = 5) -> List[Dict[str, str]]:
    if not SCALESERP_KEY:
        return []
    try:
        async with SEARCH_SEM:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    "https://api.scaleserp.com/search",
                    params={
                        "q": query,
                        "api_key": SCALESERP_KEY,
                        "num": num,
                        "gl": "us",
                        "hl": "en",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
        return [
            {
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
            }
            for item in data.get("organic_results", [])
        ]
    except Exception:
        return []


async def search_searchapi(query: str, num: int = 5) -> List[Dict[str, str]]:
    if not SEARCHAPI_KEY:
        return []
    try:
        async with SEARCH_SEM:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    "https://www.searchapi.io/api/v1/search",
                    params={
                        "engine": "google",
                        "q": query,
                        "api_key": SEARCHAPI_KEY,
                        "num": num,
                        "gl": "us",
                        "hl": "en",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
        return [
            {
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
            }
            for item in data.get("organic_results", [])
        ]
    except Exception:
        return []


async def search_results(query: str, num: int = 5) -> List[Dict[str, str]]:
    for fn in (search_serpapi, search_scaleserp, search_searchapi):
        results = await fn(query, num=num)
        if results:
            return results
    return []


async def build_search_context(vendor: Vendor) -> str:
    domain = extract_domain(vendor.website)
    category = (vendor.category or "").replace("_", " ")
    location = vendor.store_geo_location or ""
    queries: List[str] = []
    if domain:
        queries.append(f'site:{domain} "{vendor.name}"')
        queries.append(f'site:{domain} "{vendor.name}" email')
        queries.append(f'site:{domain} "{vendor.name}" contact')
        queries.append(f'site:{domain} "{vendor.name}" team')
        queries.append(f'site:{domain} "{vendor.name}" agent')
    queries.append(f'"{vendor.name}" {location} {category} email')
    queries.append(f'"{vendor.name}" {location} realtor email')
    queries.append(f'"{vendor.name}" {location} contact')
    queries.append(f'"{vendor.name}" {location} team')

    seen_urls = set()
    snippet_parts: List[str] = []
    page_parts: List[str] = []

    for query in queries:
        results = await search_results(query, num=8)
        results = sorted(results, key=lambda item: rank_contact_result(vendor, item, domain), reverse=True)
        for item in results:
            url = item.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            snippet_parts.append(f"Title: {title}\nURL: {url}\nSnippet: {snippet}")
            if len(page_parts) < 5:
                page_text = await fetch_text(url)
                if page_text and len(page_text) > 120:
                    page_parts.append(f"URL: {url}\nText: {page_text[:2500]}")
            if len(seen_urls) >= 12:
                break
        if len(seen_urls) >= 12:
            break

    parts: List[str] = []
    if snippet_parts:
        parts.append("Search results:\n" + "\n\n".join(snippet_parts[:12]))
    if page_parts:
        parts.append("Search page text:\n" + "\n\n".join(page_parts[:5]))
    return "\n\n".join(parts)[:7000]


def build_crawl_context(crawl_bundle: Optional[Dict[str, Any]]) -> str:
    if not crawl_bundle:
        return ""
    parts: List[str] = []
    if crawl_bundle.get("emails"):
        parts.append("Explicit emails found during crawl: " + " ; ".join(crawl_bundle["emails"][:8]))
    if crawl_bundle.get("phones"):
        parts.append("Explicit phones found during crawl: " + " ; ".join(crawl_bundle["phones"][:6]))
    if crawl_bundle.get("social_links"):
        parts.append("Social profiles: " + " ; ".join(f"{label}: {url}" for label, url in crawl_bundle["social_links"].items()))
    for page in crawl_bundle.get("pages", [])[:5]:
        page_parts = [
            f"Page type: {page.get('page_type', 'unknown')}",
            f"URL: {page.get('url', '')}",
            f"Title: {page.get('title', '')}",
        ]
        if page.get("meta_description"):
            page_parts.append(f"Meta description: {page['meta_description']}")
        if page.get("headings"):
            page_parts.append("Headings: " + " | ".join(page["headings"][:6]))
        if page.get("emails"):
            page_parts.append("Explicit emails on page: " + " ; ".join(page["emails"][:6]))
        if page.get("phones"):
            page_parts.append("Explicit phones on page: " + " ; ".join(page["phones"][:4]))
        if page.get("text"):
            page_parts.append(f"Visible text: {page['text'][:2200]}")
        parts.append("\n".join(page_parts))
    return "\n\n".join(parts)[:12000]


def needs_search_fallback(vendor: Vendor, crawl_bundle: Optional[Dict[str, Any]], needs_contact_backfill: bool) -> bool:
    if not needs_contact_backfill:
        return False
    if not crawl_bundle:
        return True
    if not vendor.email and not crawl_bundle.get("emails"):
        return True
    contact_pages = [
        page for page in crawl_bundle.get("pages", [])
        if page.get("page_type") in {"contact", "team", "agent"}
    ]
    if not vendor.contact_name and not contact_pages:
        return True
    return False


def sanitize_string(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned or None


def ensure_string_list(value: Any) -> List[str]:
    if isinstance(value, str):
        raw_items = re.split(r"[,;\n|•]+", value)
    elif isinstance(value, (list, tuple)):
        raw_items = [str(item) for item in value if item is not None]
    else:
        raw_items = []
    return unique_strings([item for item in (sanitize_string(raw) for raw in raw_items) if item])


def ensure_feature_matrix(value: Any) -> List[Dict[str, str]]:
    if not isinstance(value, list):
        return []
    normalized: List[Dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        feature = sanitize_string(item.get("feature"))
        details = sanitize_string(item.get("details"))
        if feature and details:
            normalized.append({"feature": feature, "details": details})
    return normalized[:8]


def contact_name_supported(name: Optional[str], support_text: str) -> bool:
    if not name:
        return False
    tokens = [token for token in re.split(r"[^a-zA-Z]+", name.lower()) if len(token) > 2]
    if not tokens:
        return False
    matches = sum(token in support_text for token in tokens)
    return matches >= min(2, len(tokens))


def _fallback_slug(name: str, vendor_id: int) -> str:
    base = (name or "vendor").lower().strip()
    base = re.sub(r"[^a-z0-9\s-]", "", base)
    base = re.sub(r"[\s_-]+", "-", base).strip("-")
    return f"{base or 'vendor'}-{vendor_id}"


async def ensure_unique_slug(session: AsyncSession, vendor_id: int, slug: Optional[str], vendor_name: str) -> str:
    proposed = sanitize_string(slug)
    if not proposed:
        proposed = _fallback_slug(vendor_name, vendor_id)
    result = await session.exec(select(Vendor).where(Vendor.slug == proposed, Vendor.id != vendor_id))
    existing = result.first()
    if existing:
        return _fallback_slug(vendor_name, vendor_id)
    return proposed


def normalize_extracted_payload(vendor: Vendor, extracted: Optional[Dict[str, Any]], crawl_bundle: Optional[Dict[str, Any]], search_context: str) -> Optional[Dict[str, Any]]:
    extracted = extracted or {}
    if not extracted and not crawl_bundle:
        return None
    crawl_pages = (crawl_bundle or {}).get("pages", [])
    domain = extract_domain(vendor.website)
    support_text = " ".join(
        [search_context.lower()] +
        [
            f"{page.get('title', '')} {' '.join(page.get('headings', []))} {page.get('text', '')}".lower()
            for page in crawl_pages
        ]
    )
    email_candidates = unique_strings(((crawl_bundle or {}).get("emails") or []) + extract_supported_emails(search_context))
    phone_candidates = unique_strings(((crawl_bundle or {}).get("phones") or []) + extract_supported_phones(search_context))
    email = sanitize_string(extracted.get("email"))
    if not email and email_candidates:
        email = choose_best_email(vendor, email_candidates, domain)
    elif email and email.lower() not in {item.lower() for item in email_candidates} and email_candidates:
        email = choose_best_email(vendor, email_candidates, domain)
    phone = sanitize_string(extracted.get("phone"))
    normalized_candidates = {normalize_phone(candidate): candidate for candidate in phone_candidates}
    if not phone and phone_candidates:
        phone = phone_candidates[0]
    elif phone and normalize_phone(phone) not in normalized_candidates and phone_candidates:
        phone = phone_candidates[0]
    contact_name = sanitize_string(extracted.get("contact_name"))
    if contact_name and contact_name.lower() != (vendor.name or "").strip().lower() and not contact_name_supported(contact_name, support_text):
        contact_name = None
    description = sanitize_string(extracted.get("description"))
    tagline = sanitize_string(extracted.get("tagline"))
    specialties = sanitize_string(extracted.get("specialties"))
    location_hq = sanitize_string(extracted.get("location_hq")) or sanitize_string(vendor.store_geo_location)
    seo_content_raw = extracted.get("seo_content") if isinstance(extracted.get("seo_content"), dict) else {}
    summary = sanitize_string(seo_content_raw.get("summary")) or description
    services_list = ensure_string_list(seo_content_raw.get("services_list"))
    features_matrix = ensure_feature_matrix(seo_content_raw.get("features_matrix"))
    pricing_model = sanitize_string(seo_content_raw.get("pricing_model"))
    pros = ensure_string_list(seo_content_raw.get("pros"))
    cons = ensure_string_list(seo_content_raw.get("cons"))
    validation_raw = extracted.get("validation") if isinstance(extracted.get("validation"), dict) else {}
    explicit_crawl_emails = {item.lower() for item in ((crawl_bundle or {}).get("emails") or [])}
    search_emails = {item.lower() for item in extract_supported_emails(search_context)}
    if email and email.lower() in explicit_crawl_emails:
        contact_confidence = "high"
    elif email and email.lower() in search_emails:
        contact_confidence = "medium"
    else:
        contact_confidence = sanitize_string(validation_raw.get("contact_confidence")) or ("medium" if email else "low")
    description_confidence = sanitize_string(validation_raw.get("description_confidence")) or ("high" if description and len(crawl_pages) >= 2 else "medium" if description else "low")
    seo_confidence = sanitize_string(validation_raw.get("seo_confidence")) or ("high" if summary and services_list else "medium" if summary else "low")
    crawl_metadata = {
        "source_urls": [page.get("url") for page in crawl_pages if page.get("url")][:8],
        "contact_source_urls": [
            page.get("url") for page in crawl_pages
            if page.get("url") and (page.get("emails") or page.get("phones") or page.get("page_type") in {"contact", "team", "agent"})
        ][:6],
        "page_types": [page.get("page_type") for page in crawl_pages if page.get("page_type")],
        "explicit_emails": email_candidates[:8],
        "explicit_phones": phone_candidates[:6],
        "search_used": bool(search_context.strip()),
        "social_links": (crawl_bundle or {}).get("social_links") or {},
    }
    seo_content = {
        "summary": summary,
        "services_list": services_list,
        "features_matrix": features_matrix,
        "pricing_model": pricing_model,
        "pros": pros,
        "cons": cons,
        "validation": {
            "contact_confidence": contact_confidence,
            "description_confidence": description_confidence,
            "seo_confidence": seo_confidence,
        },
        "crawl_metadata": crawl_metadata,
    }
    schema_markup = extracted.get("schema_markup") if isinstance(extracted.get("schema_markup"), dict) else {}
    if not schema_markup.get("@context"):
        schema_markup["@context"] = "https://schema.org"
    if not schema_markup.get("@type"):
        schema_markup["@type"] = "LocalBusiness"
    schema_markup["name"] = vendor.name
    if vendor.website:
        schema_markup["url"] = vendor.website
    if summary or description:
        schema_markup["description"] = summary or description
    if phone:
        schema_markup["telephone"] = phone
    if email:
        schema_markup["email"] = email
    if location_hq:
        schema_markup.setdefault("areaServed", location_hq)
    same_as = ensure_string_list(schema_markup.get("sameAs")) + list(((crawl_bundle or {}).get("social_links") or {}).values())
    if same_as:
        schema_markup["sameAs"] = unique_strings(same_as)
    return {
        "slug": sanitize_string(extracted.get("slug")) or _fallback_slug(vendor.name, vendor.id or 0),
        "description": description,
        "tagline": tagline,
        "specialties": specialties,
        "location_hq": location_hq,
        "phone": phone,
        "email": email,
        "contact_name": contact_name,
        "seo_content": seo_content,
        "schema_markup": schema_markup,
    }


EXTRACT_PROMPT = """You are a vendor research, validation, and SEO synthesis assistant. Given deterministic crawl evidence and optional external search evidence for a business called "{name}" (current category: {category}), extract grounded structured JSON.
Only include claims supported by the evidence. Prefer explicit first-party emails and phone numbers. Use a direct person email when explicitly supported; otherwise use the best explicit office or team email. Do not invent contact data or unsupported specialties.

Return ONLY valid JSON, no markdown fences:
{{
  "slug": "url-friendly-slug-for-{name}",
  "description": "2-3 sentence factual description of what this business does, their specialty, and value proposition",
  "tagline": "their tagline/slogan if visible, else null",
  "specialties": "comma-separated list of specific services or product specialties",
  "location_hq": "city, state/country of headquarters or primary office",
  "phone": "primary phone number if found, else null",
  "email": "primary contact email if found, else null",
  "contact_name": "name of owner/principal/contact person if found, else null",
  "seo_content": {{
    "summary": "high-density 2-3 sentence summary of core offerings",
    "services_list": ["Service 1", "Service 2"],
    "features_matrix": [{{"feature": "Feature", "details": "Specific detail"}}],
    "pricing_model": "Fixed, hourly, quote-based, etc. Include numbers if found.",
    "pros": ["Pro 1"],
    "cons": ["Con 1"]
  }},
  "schema_markup": {{
    "@context": "https://schema.org",
    "@type": "LocalBusiness",
    "name": "{name}",
    "description": "summary"
  }},
  "validation": {{
    "contact_confidence": "high|medium|low",
    "description_confidence": "high|medium|low",
    "seo_confidence": "high|medium|low"
  }}
}}

Deterministic crawl evidence:
{crawl_context}

Optional external search evidence:
{search_context}"""


async def llm_extract(name: str, category: str, crawl_context: str, search_context: str = "") -> Optional[Dict[str, Any]]:
    if not crawl_context or len(crawl_context) < 50:
        return None
    prompt = EXTRACT_PROMPT.format(
        name=name,
        category=category or "Unknown",
        crawl_context=crawl_context[:12000],
        search_context=search_context[:6000],
    )
    try:
        async with LLM_SEM:
            async with httpx.AsyncClient(timeout=45) as client:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": LLM_MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1,
                        "max_tokens": 1400,
                    },
                )
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
                content = content.strip()
                if content.startswith("```"):
                    content = re.sub(r"^```\w*\n?", "", content)
                    content = re.sub(r"\n?```$", "", content)
                return json.loads(content)
    except Exception as e:
        logger.warning(f"LLM extract failed for {name}: {e}")
        return None


async def embed_text(text: str) -> Optional[List[float]]:
    if not OPENROUTER_API_KEY or not text:
        return None
    try:
        async with EMBED_SEM:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    "https://openrouter.ai/api/v1/embeddings",
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": EMBEDDING_MODEL,
                        "input": [text[:8000]],
                        "dimensions": EMBEDDING_DIM,
                    },
                )
                resp.raise_for_status()
                return resp.json()["data"][0]["embedding"]
    except Exception as e:
        logger.warning(f"Embedding failed: {e}")
        return None


def build_profile_text(vendor: Vendor, extracted: Optional[Dict[str, Any]]) -> str:
    parts = [vendor.name + "."]
    desc = (extracted or {}).get("description") or vendor.description or ""
    if desc and "Real-world professional provider" not in desc:
        parts.append(desc)
    seo_summary = ((extracted or {}).get("seo_content") or {}).get("summary") or ""
    if seo_summary and seo_summary != desc:
        parts.append(seo_summary)
    if vendor.category:
        parts.append(f"Category: {vendor.category}.")
    specs = (extracted or {}).get("specialties") or vendor.specialties
    if specs:
        parts.append(f"Specialties: {specs}.")
    hq = (extracted or {}).get("location_hq") or vendor.store_geo_location
    if hq:
        parts.append(f"Headquarters: {hq}.")
    tagline = (extracted or {}).get("tagline") or vendor.tagline
    if tagline:
        parts.append(f'Tagline: "{tagline}".')
    return " ".join(parts)


async def enrich_vendors(limit: Optional[int], dry_run: bool, skip_embed: bool, category: Optional[str], contact_research: bool, names_csv: Optional[str], missing_email_only: bool):
    async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    vendor_names = load_vendor_names(names_csv)

    async with async_session_factory() as session:
        stmt = select(Vendor).where(Vendor.website.isnot(None))
        if category:
            stmt = stmt.where(Vendor.category == category)
        if vendor_names:
            stmt = stmt.where(Vendor.name.in_(vendor_names))
        if missing_email_only:
            stmt = stmt.where(sa.or_(Vendor.email.is_(None), sa.func.btrim(Vendor.email) == ""))
        if limit:
            stmt = stmt.limit(limit)
        result = await session.exec(stmt)
        vendors = result.all()

    logger.info(f"Enriching {len(vendors)} vendors (dry_run={dry_run}, skip_embed={skip_embed}, category={category or 'all'}, contact_research={contact_research}, names_csv={names_csv or 'none'}, missing_email_only={missing_email_only})")

    enriched = 0
    embedded = 0
    errors = 0
    skipped = 0

    for i, vendor in enumerate(vendors, 1):
        try:
            existing_contact = (vendor.contact_name or "").strip().lower()
            vendor_name = (vendor.name or "").strip().lower()
            generic_contact_placeholder = bool(existing_contact) and existing_contact == vendor_name
            needs_contact_backfill = contact_research and (
                not vendor.email or
                not vendor.contact_name or
                not vendor.phone or
                generic_contact_placeholder
            )
            if vendor.profile_text and len(vendor.profile_text) > 200 and vendor.embedding is not None and not skip_embed and not needs_contact_backfill:
                skipped += 1
                if i % 100 == 0:
                    logger.info(f"[{i}/{len(vendors)}] skipped={skipped} enriched={enriched} embedded={embedded} errors={errors}")
                continue

            logger.info(f"[{i}/{len(vendors)}] {vendor.name} — {vendor.website}")

            crawl_bundle = await crawl_vendor_site_evidence(vendor.website)
            crawl_context = build_crawl_context(crawl_bundle)
            if not crawl_context or len(crawl_context) < 100:
                logger.info(f"  Scrape returned insufficient text ({len(crawl_context) if crawl_context else 0} chars)")
                errors += 1
                continue

            search_context = ""
            if needs_search_fallback(vendor, crawl_bundle, needs_contact_backfill):
                search_context = await build_search_context(vendor)
            extracted = await llm_extract(vendor.name, vendor.category, crawl_context, search_context=search_context)
            extracted = normalize_extracted_payload(vendor, extracted, crawl_bundle, search_context)
            profile = build_profile_text(vendor, extracted)

            if dry_run:
                validation = ((extracted or {}).get("seo_content") or {}).get("validation") or {}
                logger.info(f"  [DRY RUN] email={((extracted or {}).get('email') or '-')}, contact_confidence={validation.get('contact_confidence', '-')}, profile_text ({len(profile)} chars): {profile[:150]}...")
                enriched += 1
                continue

            async with async_session_factory() as session:
                db_vendor = (await session.exec(select(Vendor).where(Vendor.id == vendor.id))).one()
                db_vendor.profile_text = profile

                if extracted:
                    if extracted.get("description") and "Real-world professional" not in (db_vendor.description or ""):
                        if not db_vendor.description or len(db_vendor.description) < 60 or "Real-world professional" in (db_vendor.description or ""):
                            db_vendor.description = extracted["description"]
                    if extracted.get("tagline"):
                        db_vendor.tagline = extracted["tagline"]
                    if extracted.get("specialties"):
                        db_vendor.specialties = extracted["specialties"]
                    if extracted.get("phone") and not db_vendor.phone:
                        db_vendor.phone = extracted["phone"]
                    if extracted.get("email") and not db_vendor.email:
                        db_vendor.email = extracted["email"]
                    if extracted.get("contact_name"):
                        existing_contact = (db_vendor.contact_name or "").strip().lower()
                        vendor_name = (db_vendor.name or "").strip().lower()
                        if not existing_contact or existing_contact == vendor_name:
                            db_vendor.contact_name = extracted["contact_name"]
                    if extracted.get("slug"):
                        db_vendor.slug = await ensure_unique_slug(session, vendor.id or 0, extracted.get("slug"), vendor.name)
                    if extracted.get("seo_content"):
                        db_vendor.seo_content = extracted["seo_content"]
                    if extracted.get("schema_markup"):
                        db_vendor.schema_markup = extracted["schema_markup"]

                db_vendor.updated_at = datetime.utcnow()

                if not skip_embed:
                    emb = await embed_text(profile)
                    if emb:
                        vec_str = "[" + ",".join(str(f) for f in emb) + "]"
                        await session.execute(
                            sa.text("UPDATE vendor SET embedding = CAST(:vec AS vector), embedding_model = :model, embedded_at = NOW() WHERE id = :vid"),
                            {"vec": vec_str, "model": EMBEDDING_MODEL, "vid": vendor.id},
                        )
                        embedded += 1

                session.add(db_vendor)
                await session.commit()
                enriched += 1

            if i % 50 == 0:
                logger.info(f"  Progress: {i}/{len(vendors)} | enriched={enriched} embedded={embedded} skipped={skipped} errors={errors}")

        except Exception as e:
            logger.error(f"  Error processing {vendor.name}: {e}")
            errors += 1

    logger.info(f"DONE. enriched={enriched} embedded={embedded} skipped={skipped} errors={errors}")


def load_vendor_names(csv_path: Optional[str]) -> List[str]:
    if not csv_path:
        return []
    path = Path(csv_path)
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    names: List[str] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2 and row[1].strip():
                names.append(row[1].strip())
    return names


def main():
    parser = argparse.ArgumentParser(description="Enrich vendor records from website scraping + LLM")
    parser.add_argument("--limit", type=int, help="Limit vendors to process")
    parser.add_argument("--dry-run", action="store_true", help="Don't write to DB")
    parser.add_argument("--skip-embed", action="store_true", help="Skip re-embedding step")
    parser.add_argument("--category", type=str, help="Only enrich vendors in the given category")
    parser.add_argument("--contact-research", action="store_true", help="Use search APIs to improve direct contact discovery before extraction")
    parser.add_argument("--names-csv", type=str, help="CSV file whose second column contains vendor names to enrich")
    parser.add_argument("--missing-email-only", action="store_true", help="Only enrich vendors whose email is currently missing")
    args = parser.parse_args()

    if not OPENROUTER_API_KEY:
        logger.error("OPENROUTER_API_KEY not set — cannot run LLM extraction or embedding")
        sys.exit(1)

    asyncio.run(enrich_vendors(args.limit, args.dry_run, args.skip_embed, args.category, args.contact_research, args.names_csv, args.missing_email_only))


if __name__ == "__main__":
    main()
