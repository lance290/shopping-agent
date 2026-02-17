#!/usr/bin/env python3
"""
Vendor Enrichment Script

Scrapes vendor websites to extract real business details, then uses an LLM
to produce structured enrichment data. Finally re-embeds all vendors.

Pipeline per vendor:
1. Fetch homepage HTML (+ /about, /services if found)
2. Extract visible text (strip nav/footer boilerplate)
3. Send to LLM: "Given this website text for {vendor_name}, extract structured info"
4. Update DB fields: description, profile_text, service_areas, specialties, tagline
5. Re-embed profile_text via OpenRouter embeddings API

Usage:
    python scripts/enrich_vendors.py [--limit N] [--dry-run] [--skip-embed]
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
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "openai/text-embedding-3-small")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIMENSIONS", "1536"))
LLM_MODEL = "google/gemini-2.0-flash-001"  # cheap + fast for extraction
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

# --- Scraping ---

async def fetch_text(url: str) -> Optional[str]:
    """Fetch a URL and return visible text content (max ~6000 chars)."""
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
        # Remove script/style/nav/footer noise
        for tag in soup(["script", "style", "noscript", "nav", "footer", "header",
                         "iframe", "svg", "form"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text)
        # Truncate to ~6000 chars to keep LLM context manageable
        return text[:6000] if text else None
    except Exception:
        return None


async def scrape_vendor_site(website: str) -> str:
    """Scrape homepage + try /about and /services pages. Return combined text."""
    texts = []
    homepage = await fetch_text(website)
    if homepage:
        texts.append(homepage)

    # Try common subpages
    parsed = urlparse(website if website.startswith("http") else f"https://{website}")
    base = f"{parsed.scheme}://{parsed.netloc}"
    for path in ["/about", "/about-us", "/services", "/contact"]:
        sub = await fetch_text(base + path)
        if sub and len(sub) > 200:
            texts.append(sub[:3000])

    combined = "\n\n".join(texts)
    # Cap total at 10000 chars
    return combined[:10000]


# --- LLM Extraction ---

EXTRACT_PROMPT = """You are a data extraction assistant. Given scraped website text for a business called "{name}" (current category: {category}), extract the following structured JSON. Be factual — only include information clearly stated or strongly implied by the text. If something is not available, use null.

Return ONLY valid JSON, no markdown fences:
{{
  "description": "2-3 sentence description of what this business does, their specialty, and value proposition",
  "tagline": "their tagline/slogan if visible, else null",
  "specialties": "comma-separated list of specific services or product specialties",
  "service_areas": "comma-separated list of cities, states, regions, or countries they serve. Include headquarters location if mentioned.",
  "location_hq": "city, state/country of headquarters or primary office",
  "phone": "primary phone number if found, else null",
  "email": "primary contact email if found, else null",
  "contact_name": "name of owner/principal/contact person if found, else null"
}}

Website text:
{text}"""


async def llm_extract(name: str, category: str, text: str) -> Optional[Dict[str, Any]]:
    """Call LLM to extract structured vendor info from scraped text."""
    if not text or len(text) < 50:
        return None
    prompt = EXTRACT_PROMPT.format(
        name=name, category=category or "Unknown", text=text[:8000]
    )
    try:
        async with LLM_SEM:
            async with httpx.AsyncClient(timeout=30) as client:
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
                        "max_tokens": 600,
                    },
                )
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
                # Strip markdown fences if present
                content = content.strip()
                if content.startswith("```"):
                    content = re.sub(r"^```\w*\n?", "", content)
                    content = re.sub(r"\n?```$", "", content)
                return json.loads(content)
    except Exception as e:
        logger.warning(f"LLM extract failed for {name}: {e}")
        return None


# --- Embedding ---

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


def build_profile_text(vendor: Vendor, extracted: Optional[Dict]) -> str:
    """Build rich profile text from all available data."""
    parts = []
    name = vendor.name
    parts.append(name + ".")

    desc = (extracted or {}).get("description") or vendor.description or ""
    if desc and "Real-world professional provider" not in desc:
        parts.append(desc)

    cat = vendor.category
    if cat:
        parts.append(f"Category: {cat}.")

    specs = (extracted or {}).get("specialties") or vendor.specialties
    if specs:
        parts.append(f"Specialties: {specs}.")

    areas = (extracted or {}).get("service_areas")
    if areas:
        parts.append(f"Service areas: {areas}.")

    hq = (extracted or {}).get("location_hq")
    if hq:
        parts.append(f"Headquarters: {hq}.")

    tagline = (extracted or {}).get("tagline") or vendor.tagline
    if tagline:
        parts.append(f'Tagline: "{tagline}".')

    return " ".join(parts)


# --- Main pipeline ---

async def enrich_vendors(limit: Optional[int], dry_run: bool, skip_embed: bool):
    """Main enrichment loop."""
    async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_factory() as session:
        stmt = select(Vendor).where(Vendor.website.isnot(None))
        if limit:
            stmt = stmt.limit(limit)
        result = await session.exec(stmt)
        vendors = result.all()

    logger.info(f"Enriching {len(vendors)} vendors (dry_run={dry_run}, skip_embed={skip_embed})")

    enriched = 0
    embedded = 0
    errors = 0
    skipped = 0

    for i, vendor in enumerate(vendors, 1):
        try:
            # Skip if already has rich profile_text (> 200 chars) and embedding
            if vendor.profile_text and len(vendor.profile_text) > 200 and vendor.embedding is not None and not skip_embed:
                skipped += 1
                if i % 100 == 0:
                    logger.info(f"[{i}/{len(vendors)}] skipped={skipped} enriched={enriched} embedded={embedded} errors={errors}")
                continue

            logger.info(f"[{i}/{len(vendors)}] {vendor.name} — {vendor.website}")

            # 1. Scrape
            text = await scrape_vendor_site(vendor.website)
            if not text or len(text) < 100:
                logger.info(f"  Scrape returned insufficient text ({len(text) if text else 0} chars)")
                errors += 1
                continue

            # 2. LLM extraction
            extracted = await llm_extract(vendor.name, vendor.category, text)

            # 3. Build profile text
            profile = build_profile_text(vendor, extracted)

            if dry_run:
                logger.info(f"  [DRY RUN] profile_text ({len(profile)} chars): {profile[:150]}...")
                enriched += 1
                continue

            # 4. Update DB
            async with async_session_factory() as session:
                db_vendor = (await session.exec(select(Vendor).where(Vendor.id == vendor.id))).one()

                db_vendor.profile_text = profile

                if extracted:
                    if extracted.get("description") and "Real-world professional" not in (db_vendor.description or ""):
                        # Only overwrite generic descriptions
                        if not db_vendor.description or len(db_vendor.description) < 60 or "Real-world professional" in db_vendor.description:
                            db_vendor.description = extracted["description"]
                    if extracted.get("tagline"):
                        db_vendor.tagline = extracted["tagline"]
                    if extracted.get("specialties"):
                        db_vendor.specialties = extracted["specialties"]
                    if extracted.get("service_areas"):
                        db_vendor.service_areas = extracted["service_areas"]
                    if extracted.get("phone") and not db_vendor.phone:
                        db_vendor.phone = extracted["phone"]
                    if extracted.get("email") and not db_vendor.email:
                        db_vendor.email = extracted["email"]
                    if extracted.get("contact_name") and not db_vendor.contact_name:
                        db_vendor.contact_name = extracted["contact_name"]

                db_vendor.updated_at = datetime.utcnow()

                # 5. Re-embed
                if not skip_embed:
                    emb = await embed_text(profile)
                    if emb:
                        vec_str = "[" + ",".join(str(f) for f in emb) + "]"
                        await session.execute(
                            sa.text("UPDATE vendor SET embedding = CAST(:vec AS vector), "
                                    "embedding_model = :model, embedded_at = NOW() "
                                    "WHERE id = :vid"),
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


def main():
    parser = argparse.ArgumentParser(description="Enrich vendor records from website scraping + LLM")
    parser.add_argument("--limit", type=int, help="Limit vendors to process")
    parser.add_argument("--dry-run", action="store_true", help="Don't write to DB")
    parser.add_argument("--skip-embed", action="store_true", help="Skip re-embedding step")
    args = parser.parse_args()

    if not OPENROUTER_API_KEY:
        logger.error("OPENROUTER_API_KEY not set — cannot run LLM extraction or embedding")
        sys.exit(1)

    asyncio.run(enrich_vendors(args.limit, args.dry_run, args.skip_embed))


if __name__ == "__main__":
    main()
