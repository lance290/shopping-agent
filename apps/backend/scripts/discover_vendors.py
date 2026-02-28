#!/usr/bin/env python3
"""
Vendor Discovery Pipeline

Searches the web for new vendors by category using SerpAPI/ScaleSerp,
scrapes their sites, uses local Ollama for structured profile extraction,
generates embeddings via OpenRouter, and inserts into the DB.

Pipeline per discovered vendor:
1. Web search via SerpAPI (Google organic) for category+location queries
2. Extract business URLs from results, dedupe against existing DB domains
3. Scrape discovered vendor websites
4. Local Ollama LLM → structured profile JSON + SEO content
5. Embed via OpenRouter (text-embedding-3-small)
6. Insert into vendor table

Usage:
    python scripts/discover_vendors.py [--limit N] [--dry-run] [--categories CAT1,CAT2]
    python scripts/discover_vendors.py --categories "luxury_villas,plastic_surgery" --limit 50
    python scripts/discover_vendors.py --all  # Run all categories
"""

import asyncio
import json
import logging
import os
import re
import ssl
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Set, Tuple
from urllib.parse import urlparse, quote_plus
import argparse

import aiohttp
from bs4 import BeautifulSoup
import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from database import engine
from models import Vendor
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker
import sqlalchemy as sa

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-7s %(message)s',
    handlers=[
        logging.FileHandler('vendor_discovery.log'),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────────────────────────────
SERPAPI_KEY = os.getenv("SERPAPI_API_KEY", "")
SCALESERP_KEY = os.getenv("SCALESERP_API_KEY", "")
SEARCHAPI_KEY = os.getenv("SEARCHAPI_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:120b")

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
SCRAPE_TIMEOUT = aiohttp.ClientTimeout(total=20, connect=8)
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

SCRAPE_SEM = asyncio.Semaphore(10)
LLM_SEM = asyncio.Semaphore(2)
EMBED_SEM = asyncio.Semaphore(5)
SEARCH_SEM = asyncio.Semaphore(3)

# Domains to skip — aggregators, directories, social media
SKIP_DOMAINS = {
    "google.com", "www.google.com", "maps.google.com",
    "yelp.com", "www.yelp.com",
    "facebook.com", "www.facebook.com", "m.facebook.com",
    "linkedin.com", "www.linkedin.com",
    "instagram.com", "www.instagram.com",
    "twitter.com", "www.twitter.com", "x.com",
    "youtube.com", "www.youtube.com",
    "pinterest.com", "www.pinterest.com",
    "tiktok.com", "www.tiktok.com",
    "reddit.com", "www.reddit.com",
    "wikipedia.org", "en.wikipedia.org",
    "amazon.com", "www.amazon.com",
    "ebay.com", "www.ebay.com",
    "etsy.com", "www.etsy.com",
    "walmart.com", "www.walmart.com",
    "target.com", "www.target.com",
    "bbb.org", "www.bbb.org",
    "glassdoor.com", "www.glassdoor.com",
    "indeed.com", "www.indeed.com",
    "crunchbase.com", "www.crunchbase.com",
    "angi.com", "www.angi.com", "angieslist.com",
    "thumbtack.com", "www.thumbtack.com",
    "homeadvisor.com", "www.homeadvisor.com",
    "houzz.com", "www.houzz.com",
    "tripadvisor.com", "www.tripadvisor.com",
    "trustpilot.com", "www.trustpilot.com",
    "buildzoom.com", "www.buildzoom.com",
    "manta.com", "www.manta.com",
    "yellowpages.com", "www.yellowpages.com",
    "mapquest.com", "www.mapquest.com",
    "apple.com", "maps.apple.com",
    "nextdoor.com", "www.nextdoor.com",
}

# ── Search Queries by Category ──────────────────────────────────────────────
# Each category has multiple search queries to cast a wide net
CATEGORY_QUERIES: Dict[str, List[str]] = {
    "luxury_villas": [
        "luxury villa rental company",
        "luxury vacation home rental service",
        "private villa concierge service",
        "high end villa rental caribbean",
        "luxury villa rental europe mediterranean",
        "exclusive vacation rental company",
        "luxury ski chalet rental company",
        "private island rental service",
    ],
    "plastic_surgery": [
        "top plastic surgeon Beverly Hills",
        "best plastic surgeon New York City",
        "elite cosmetic surgeon Miami",
        "top rhinoplasty surgeon USA",
        "best facelift surgeon",
        "top body contouring surgeon",
        "celebrity plastic surgeon",
        "best plastic surgeon Nashville",
        "top plastic surgeon Dallas Houston",
        "best plastic surgeon Chicago",
    ],
    "luxury_cosmetics": [
        "luxury skincare brand",
        "high end cosmetics company",
        "premium anti-aging skincare brand",
        "luxury beauty brand",
        "exclusive skincare line",
        "prestige cosmetics brand",
        "luxury fragrance house",
        "high end makeup brand",
    ],
    "yacht_charter": [
        "luxury yacht charter company",
        "superyacht charter broker",
        "private yacht rental Mediterranean",
        "luxury catamaran charter Caribbean",
        "motor yacht charter company",
        "sailing yacht charter luxury",
        "yacht charter broker Florida",
        "luxury boat charter company",
    ],
    "private_aviation": [
        "private jet charter company",
        "fractional jet ownership",
        "private aviation membership",
        "jet card program",
        "private jet broker",
        "business aviation charter",
        "helicopter charter luxury",
        "private aircraft management company",
    ],
    "fine_jewelry": [
        "luxury jewelry designer",
        "high end custom jeweler",
        "bespoke diamond jeweler",
        "luxury watch dealer authorized",
        "fine jewelry brand",
        "estate jewelry dealer luxury",
        "custom engagement ring designer",
        "luxury jewelry store",
    ],
    "concierge_medicine": [
        "concierge medicine practice",
        "direct primary care luxury",
        "executive health program",
        "private physician practice",
        "VIP medical concierge",
        "longevity medicine clinic",
        "anti-aging medicine doctor",
        "functional medicine luxury practice",
    ],
    "luxury_real_estate": [
        "luxury real estate brokerage",
        "high end real estate agent",
        "luxury property management company",
        "mansion real estate broker",
        "waterfront luxury real estate",
        "luxury condo developer",
        "resort real estate developer",
        "luxury ranch real estate",
    ],
    "fine_art": [
        "fine art gallery contemporary",
        "art advisory firm",
        "luxury art dealer",
        "art collection management",
        "fine art auction house",
        "sculpture gallery luxury",
        "art investment advisory",
        "private art dealer",
    ],
    "luxury_automotive": [
        "exotic car dealer",
        "luxury car dealership",
        "supercar broker",
        "classic car dealer luxury",
        "luxury car rental company",
        "exotic car experience company",
        "armored vehicle luxury",
        "luxury electric vehicle dealer",
    ],
    "executive_protection": [
        "executive protection company",
        "celebrity bodyguard service",
        "VIP security firm",
        "close protection service",
        "luxury security company",
        "residential security company",
        "cybersecurity luxury family office",
        "threat assessment company",
    ],
    "luxury_events": [
        "luxury event planner",
        "high end wedding planner",
        "celebrity event planner",
        "luxury catering company",
        "private chef hire luxury",
        "luxury tent rental company",
        "exclusive venue rental",
        "luxury floral designer",
    ],
    "luxury_travel": [
        "luxury travel advisor",
        "bespoke travel company",
        "luxury safari operator",
        "expedition cruise company luxury",
        "luxury train journey company",
        "luxury wellness retreat",
        "adventure travel luxury",
        "luxury honeymoon planner",
    ],
    "home_services_luxury": [
        "luxury interior designer",
        "high end landscape architect",
        "luxury pool builder",
        "custom home builder luxury",
        "smart home installation company",
        "luxury closet designer",
        "wine cellar builder luxury",
        "luxury home theater installer",
    ],
    "wealth_management": [
        "family office advisory",
        "wealth management firm UHNW",
        "private banking services",
        "luxury financial advisor",
        "art and collectibles insurance",
        "luxury asset management",
        "estate planning attorney luxury",
        "trust and estate advisor",
    ],
}


# ── Web Search ──────────────────────────────────────────────────────────────

async def search_serpapi(query: str, num: int = 30) -> List[Dict[str, str]]:
    """Search Google organic via SerpAPI. Returns list of {title, url, snippet}."""
    if not SERPAPI_KEY:
        return []
    params = {
        "engine": "google",
        "q": query,
        "api_key": SERPAPI_KEY,
        "num": num,
        "gl": "us",
        "hl": "en",
    }
    try:
        async with SEARCH_SEM:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get("https://serpapi.com/search", params=params)
                resp.raise_for_status()
                data = resp.json()
        results = []
        for item in data.get("organic_results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
            })
        return results
    except Exception as e:
        logger.warning(f"SerpAPI search failed for '{query}': {e}")
        return []


async def search_scaleserp(query: str, num: int = 30) -> List[Dict[str, str]]:
    """Search Google organic via ScaleSerp. Returns list of {title, url, snippet}."""
    if not SCALESERP_KEY:
        return []
    params = {
        "q": query,
        "api_key": SCALESERP_KEY,
        "num": num,
        "gl": "us",
        "hl": "en",
    }
    try:
        async with SEARCH_SEM:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get("https://api.scaleserp.com/search", params=params)
                resp.raise_for_status()
                data = resp.json()
        results = []
        for item in data.get("organic_results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
            })
        return results
    except Exception as e:
        logger.warning(f"ScaleSerp search failed for '{query}': {e}")
        return []


async def search_searchapi(query: str, num: int = 30) -> List[Dict[str, str]]:
    """Search Google organic via SearchAPI.io. Returns list of {title, url, snippet}."""
    if not SEARCHAPI_KEY:
        return []
    params = {
        "engine": "google",
        "q": query,
        "api_key": SEARCHAPI_KEY,
        "num": num,
        "gl": "us",
        "hl": "en",
    }
    try:
        async with SEARCH_SEM:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get("https://www.searchapi.io/api/v1/search", params=params)
                resp.raise_for_status()
                data = resp.json()
        results = []
        for item in data.get("organic_results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
            })
        return results
    except Exception as e:
        logger.warning(f"SearchAPI search failed for '{query}': {e}")
        return []


def extract_domain(url: str) -> str:
    """Extract clean domain from URL."""
    try:
        parsed = urlparse(url if url.startswith("http") else f"https://{url}")
        return parsed.netloc.lower().lstrip("www.")
    except Exception:
        return ""


async def discover_urls_for_category(
    category: str, queries: List[str], existing_domains: Set[str]
) -> List[Dict[str, str]]:
    """Run search queries for a category and return deduplicated new vendor URLs."""
    all_results = []
    seen_domains: Set[str] = set()

    for query in queries:
        # Try SerpAPI first, fall back to ScaleSerp, then SearchAPI
        results = await search_serpapi(query)
        if not results:
            results = await search_scaleserp(query)
        if not results:
            results = await search_searchapi(query)

        for r in results:
            url = r.get("url", "")
            domain = extract_domain(url)
            if not domain:
                continue
            # Skip aggregators, social media, already-known vendors
            if domain in SKIP_DOMAINS:
                continue
            if domain in existing_domains:
                continue
            if domain in seen_domains:
                continue
            seen_domains.add(domain)
            all_results.append({
                "title": r.get("title", ""),
                "url": url,
                "domain": domain,
                "snippet": r.get("snippet", ""),
                "category": category,
            })

        # Brief pause between queries to avoid rate limiting
        await asyncio.sleep(1.0)

    logger.info(f"  [{category}] Discovered {len(all_results)} new URLs from {len(queries)} queries")
    return all_results


# ── Scraping ────────────────────────────────────────────────────────────────

async def fetch_text(url: str) -> Optional[str]:
    """Fetch a URL and return visible text content."""
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
                    html = await resp.text()
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "nav", "footer",
                         "header", "iframe", "svg", "form"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text)
        return text[:8000] if text else None
    except Exception:
        return None


async def scrape_vendor_site(website: str) -> str:
    """Scrape homepage + subpages. Return combined text."""
    texts = []
    homepage = await fetch_text(website)
    if homepage:
        texts.append(homepage)

    parsed = urlparse(website if website.startswith("http") else f"https://{website}")
    base = f"{parsed.scheme}://{parsed.netloc}"
    for path in ["/about", "/about-us", "/services", "/contact"]:
        sub = await fetch_text(base + path)
        if sub and len(sub) > 200:
            texts.append(sub[:3000])

    combined = "\n\n".join(texts)
    return combined[:12000]


# ── Local LLM Extraction ───────────────────────────────────────────────────

PROFILE_PROMPT = """You are a data extraction assistant. Given scraped website text for a business found via a web search, extract a structured vendor profile as JSON.

The search found this site under the category "{category}".

Requirements:
1. Be factual. Only include info clearly stated or strongly implied.
2. If something is not available, use null.
3. Generate a URL-friendly slug from the business name.

Required JSON:
{{
  "name": "Business Name",
  "slug": "business-name-slug",
  "description": "2-3 sentence factual description of what this business does.",
  "tagline": "Their tagline/slogan if visible, else null",
  "category": "{category}",
  "specialties": "comma-separated list of specific services or specialties",
  "service_areas": "comma-separated list of locations/regions they serve",
  "phone": "primary phone if found, else null",
  "email": "primary email if found, else null",
  "contact_name": "owner/principal name if found, else null",
  "seo_content": {{
    "summary": "High-density 2-3 sentence summary of core offerings.",
    "services_list": ["Service 1", "Service 2"],
    "features_matrix": [
      {{"feature": "Feature", "details": "Detail"}}
    ],
    "pricing_model": "Fixed, hourly, quote-based, etc.",
    "pros": ["Pro 1"],
    "cons": ["Con 1"]
  }},
  "schema_markup": {{
    "@context": "https://schema.org",
    "@type": "LocalBusiness",
    "name": "Business Name",
    "description": "Summary"
  }}
}}

Return ONLY valid JSON. No markdown fences.

Website text:
{text}"""


async def llm_extract_profile(category: str, text: str) -> Optional[Dict[str, Any]]:
    """Call local Ollama to extract structured vendor profile."""
    if not text or len(text) < 80:
        return None
    prompt = PROFILE_PROMPT.format(category=category, text=text[:10000])
    try:
        async with LLM_SEM:
            async with httpx.AsyncClient(timeout=180) as client:
                resp = await client.post(
                    OLLAMA_URL,
                    json={
                        "model": OLLAMA_MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "format": "json",
                        "stream": False,
                        "options": {"temperature": 0.1, "num_predict": 1500},
                    },
                )
                resp.raise_for_status()
                content = resp.json().get("message", {}).get("content", "")
                content = content.strip()
                if content.startswith("```"):
                    content = re.sub(r"^```(?:json)?\n?", "", content)
                    content = re.sub(r"\n?```$", "", content)
                return json.loads(content)
    except Exception as e:
        logger.warning(f"Ollama extract failed: {e}")
        return None


# ── Embedding ───────────────────────────────────────────────────────────────

async def embed_text(text: str) -> Optional[List[float]]:
    """Embed text via OpenRouter."""
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


def build_profile_text(profile: Dict[str, Any]) -> str:
    """Build rich profile text from extracted profile for embedding."""
    parts = []
    if profile.get("name"):
        parts.append(profile["name"] + ".")
    if profile.get("description"):
        parts.append(profile["description"])
    if profile.get("category"):
        parts.append(f"Category: {profile['category']}.")
    if profile.get("specialties"):
        parts.append(f"Specialties: {profile['specialties']}.")
    if profile.get("service_areas"):
        parts.append(f"Service areas: {profile['service_areas']}.")
    if profile.get("tagline"):
        parts.append(f'Tagline: "{profile["tagline"]}".')
    seo = profile.get("seo_content") or {}
    if seo.get("summary"):
        parts.append(seo["summary"])
    return " ".join(parts)


# ── Main Pipeline ───────────────────────────────────────────────────────────

async def run_discovery(
    categories: Optional[List[str]],
    limit: Optional[int],
    dry_run: bool,
):
    async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # 1. Load existing vendor domains to avoid duplicates
    async with async_session_factory() as session:
        result = await session.exec(select(Vendor.website, Vendor.domain, Vendor.email))
        existing = result.all()

    existing_domains: Set[str] = set()
    for row in existing:
        if row.website:
            existing_domains.add(extract_domain(row.website))
        if row.domain:
            existing_domains.add(row.domain.lower().lstrip("www."))

    logger.info(f"Loaded {len(existing_domains)} existing vendor domains to deduplicate against")

    # 2. Determine which categories to search
    if categories:
        cats = {c: CATEGORY_QUERIES[c] for c in categories if c in CATEGORY_QUERIES}
    else:
        cats = CATEGORY_QUERIES

    if not cats:
        logger.error(f"No valid categories. Available: {list(CATEGORY_QUERIES.keys())}")
        return

    # 3. Discover new vendor URLs
    all_discovered: List[Dict[str, str]] = []
    for cat, queries in cats.items():
        logger.info(f"Searching category: {cat} ({len(queries)} queries)")
        discovered = await discover_urls_for_category(cat, queries, existing_domains)
        all_discovered.extend(discovered)
        # Also add discovered domains to the set so we don't double-discover across categories
        for d in discovered:
            existing_domains.add(d["domain"])

    logger.info(f"Total new vendors discovered: {len(all_discovered)}")

    if limit:
        all_discovered = all_discovered[:limit]
        logger.info(f"Limited to {limit} vendors")

    if not all_discovered:
        logger.info("No new vendors discovered. Done.")
        return

    # 4. Process each discovered vendor: scrape → LLM → embed → insert
    created = 0
    errors = 0

    for i, disc in enumerate(all_discovered, 1):
        url = disc["url"]
        category = disc["category"]
        try:
            logger.info(f"[{i}/{len(all_discovered)}] {disc['title'][:60]} — {disc['domain']}")

            # Scrape
            text = await scrape_vendor_site(url)
            if not text or len(text) < 100:
                logger.info(f"  Scrape insufficient ({len(text) if text else 0} chars)")
                errors += 1
                continue

            # LLM extract
            profile = await llm_extract_profile(category, text)
            if not profile or not profile.get("name"):
                logger.info(f"  LLM extraction failed or no name")
                errors += 1
                continue

            if dry_run:
                logger.info(f"  [DRY RUN] {profile.get('name')} | {profile.get('slug')}")
                created += 1
                continue

            # Build embedding text
            profile_text = build_profile_text(profile)

            # Embed
            emb = await embed_text(profile_text)

            # Insert into DB
            async with async_session_factory() as session:
                vendor = Vendor(
                    name=profile.get("name", disc["title"][:100]),
                    email=profile.get("email"),
                    domain=disc["domain"],
                    phone=profile.get("phone"),
                    website=url,
                    category=profile.get("category", category),
                    service_areas=profile.get("service_areas"),
                    specialties=profile.get("specialties"),
                    description=profile.get("description"),
                    tagline=profile.get("tagline"),
                    profile_text=profile_text,
                    contact_name=profile.get("contact_name"),
                    slug=profile.get("slug"),
                    seo_content=profile.get("seo_content"),
                    schema_markup=profile.get("schema_markup"),
                    embedding_model=EMBEDDING_MODEL if emb else None,
                    embedded_at=datetime.utcnow() if emb else None,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                session.add(vendor)
                await session.commit()
                await session.refresh(vendor)

                # Write embedding via raw SQL (pgvector cast)
                if emb:
                    vec_str = "[" + ",".join(str(f) for f in emb) + "]"
                    await session.execute(
                        sa.text(
                            "UPDATE vendor SET embedding = CAST(:vec AS vector), "
                            "embedding_model = :model, embedded_at = NOW() "
                            "WHERE id = :vid"
                        ),
                        {"vec": vec_str, "model": EMBEDDING_MODEL, "vid": vendor.id},
                    )
                    await session.commit()

                created += 1
                logger.info(f"  ✓ Created vendor #{vendor.id}: {vendor.name} (embedded={'yes' if emb else 'no'})")

        except Exception as e:
            logger.error(f"  Error processing {disc['domain']}: {e}")
            errors += 1

        # Brief pause to be nice to LLM + search APIs
        if i % 10 == 0:
            logger.info(f"  Progress: {i}/{len(all_discovered)} | created={created} errors={errors}")

    logger.info(f"DONE. created={created} errors={errors} total_discovered={len(all_discovered)}")


def main():
    parser = argparse.ArgumentParser(description="Discover new vendors via web search + local Ollama enrichment")
    parser.add_argument("--limit", type=int, help="Max vendors to process")
    parser.add_argument("--dry-run", action="store_true", help="Don't write to DB")
    parser.add_argument("--categories", type=str, help="Comma-separated category names to search")
    parser.add_argument("--all", action="store_true", help="Search all categories")
    parser.add_argument("--list-categories", action="store_true", help="List available categories")
    args = parser.parse_args()

    if args.list_categories:
        for cat, queries in CATEGORY_QUERIES.items():
            print(f"  {cat:30s} ({len(queries)} queries)")
        return

    # Check we have at least one search API
    if not SERPAPI_KEY and not SCALESERP_KEY and not SEARCHAPI_KEY:
        logger.error("No search API keys set (SERPAPI_API_KEY, SCALESERP_API_KEY, or SEARCHAPI_API_KEY)")
        sys.exit(1)

    categories = None
    if args.categories:
        categories = [c.strip() for c in args.categories.split(",")]
    elif not args.all:
        logger.error("Specify --categories or --all")
        sys.exit(1)

    asyncio.run(run_discovery(categories, args.limit, args.dry_run))


if __name__ == "__main__":
    main()
