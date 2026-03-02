#!/usr/bin/env python3
"""
SEO Enrichment Script (Programmatic SEO & GEO)

Scrapes vendor websites and uses a local Ollama instance (e.g., gpt-oss:120b)
to produce highly structured, SEO-optimized JSON content.
Updates the `slug` and `seo_content` fields in the database.

Usage:
    python scripts/seo_enrich.py [--limit N] [--dry-run]
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
from urllib.parse import urlparse
import argparse

import aiohttp
from bs4 import BeautifulSoup
import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from database import get_session, engine
from models import Vendor
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-7s %(message)s',
    handlers=[
        logging.FileHandler('seo_enrichment.log'),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# --- Config ---
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

SCRAPE_CONCURRENCY = int(os.getenv("SEO_ENRICH_SCRAPE_CONCURRENCY", "15"))
LLM_CONCURRENCY = int(os.getenv("SEO_ENRICH_LLM_CONCURRENCY", "3"))
SCRAPE_SEM = asyncio.Semaphore(max(1, SCRAPE_CONCURRENCY))
LLM_SEM = asyncio.Semaphore(max(1, LLM_CONCURRENCY))

# --- Scraping ---

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
        for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "iframe", "svg", "form"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text)
        return text[:8000] if text else None
    except Exception:
        return None

async def scrape_vendor_site(website: str) -> str:
    texts = []
    homepage = await fetch_text(website)
    if homepage:
        texts.append(homepage)

    parsed = urlparse(website if website.startswith("http") else f"https://{website}")
    base = f"{parsed.scheme}://{parsed.netloc}"
    for path in ["/about", "/about-us", "/services", "/pricing", "/faq"]:
        sub = await fetch_text(base + path)
        if sub and len(sub) > 200:
            texts.append(sub[:3000])

    combined = "\n\n".join(texts)
    return combined[:12000]


# --- Local LLM Extraction ---

EXTRACT_PROMPT = """You are a data extraction and SEO synthesis assistant. Given scraped website text for a business called "{name}", extract highly structured JSON optimized for Generative Engine Optimization (GEO).

Requirements:
1. Extreme Information Density: Extract exact services, pricing models, pros/cons, and distinct features.
2. No Fluff: Remove marketing prose. Be factual.
3. Formatting: The output must strictly conform to the following JSON structure so it can be mapped directly to HTML tables (<table/>), lists (<ul>), and definition lists (<dl/>).

Required JSON Structure:
{{
  "slug": "url-friendly-slug-for-{name}",
  "seo_content": {{
    "summary": "High-density 2-3 sentence summary of core offerings.",
    "services_list": ["Service 1", "Service 2", "Service 3"],
    "features_matrix": [
      {{"feature": "Feature Name", "details": "Specific detail"}},
      {{"feature": "Another Feature", "details": "Detail"}}
    ],
    "pricing_model": "Fixed, hourly, quote-based, etc. Include numbers if found.",
    "pros": ["Pro 1", "Pro 2"],
    "cons": ["Con 1", "Con 2"]
  }},
  "schema_markup": {{
    "@context": "https://schema.org",
    "@type": "LocalBusiness",
    "name": "{name}",
    "description": "High-density summary"
  }}
}}

Return ONLY valid JSON. No markdown fences, no explanatory text.

Website text:
{text}"""

async def llm_extract_seo(name: str, text: str) -> Optional[Dict[str, Any]]:
    """Call local Ollama to extract SEO-optimized structured JSON."""
    if not text or len(text) < 50:
        return None
    prompt = EXTRACT_PROMPT.format(name=name, text=text[:10000])
    try:
        async with LLM_SEM:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    OLLAMA_URL,
                    json={
                        "model": OLLAMA_MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "format": "json",
                        "stream": False,
                        "options": {
                            "temperature": 0.1,
                            "num_predict": 1500
                        }
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
        logger.warning(f"Ollama LLM extract failed for {name}: {e}")
        return None


def _fallback_slug(name: str, vendor_id: int) -> str:
    base = (name or "vendor").lower().strip()
    base = re.sub(r"[^a-z0-9\s-]", "", base)
    base = re.sub(r"[\s_-]+", "-", base).strip("-")
    return f"{base or 'vendor'}-{vendor_id}"


# --- Main pipeline ---

async def enrich_seo_vendors(limit: Optional[int], dry_run: bool):
    async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_factory() as session:
        # Query SEO fields via SQL because these columns may exist in DB before ORM model is updated.
        query = """
            SELECT id, name, website
            FROM vendor
            WHERE website IS NOT NULL
              AND COALESCE(TRIM(website), '') <> ''
              AND seo_content IS NULL
            ORDER BY id
        """
        if limit:
            query += " LIMIT :limit"
            result = await session.execute(text(query), {"limit": limit})
        else:
            result = await session.execute(text(query))
        vendors = result.mappings().all()

    logger.info(f"Enriching {len(vendors)} vendors for SEO (dry_run={dry_run})")

    enriched = 0
    errors = 0

    for i, vendor in enumerate(vendors, 1):
        try:
            vendor_id = int(vendor["id"])
            vendor_name = vendor["name"]
            vendor_website = vendor["website"]
            logger.info(f"[{i}/{len(vendors)}] {vendor_name} — {vendor_website}")

            scraped_text = await scrape_vendor_site(vendor_website)
            if not scraped_text or len(scraped_text) < 100:
                logger.info(f"  Scrape returned insufficient text ({len(scraped_text) if scraped_text else 0} chars)")
                errors += 1
                continue

            extracted = await llm_extract_seo(vendor_name, scraped_text)
            
            if not extracted:
                logger.info(f"  Failed to extract JSON from LLM")
                errors += 1
                continue

            if dry_run:
                logger.info(f"  [DRY RUN] Extracted: {json.dumps(extracted)[:200]}...")
                enriched += 1
                continue

            async with async_session_factory() as session:
                slug = extracted.get("slug") or _fallback_slug(vendor_name, vendor_id)
                seo_content = extracted.get("seo_content") or {}
                schema_markup = extracted.get("schema_markup") or {
                    "@context": "https://schema.org",
                    "@type": "LocalBusiness",
                    "name": vendor_name,
                    "description": seo_content.get("summary", ""),
                }

                # Ensure slug uniqueness if generated slug is already taken by another vendor.
                existing = await session.execute(
                    text("SELECT id FROM vendor WHERE slug = :slug AND id != :id LIMIT 1"),
                    {"slug": slug, "id": vendor_id},
                )
                if existing.first():
                    slug = _fallback_slug(vendor_name, vendor_id)

                await session.execute(
                    text(
                        """
                        UPDATE vendor
                        SET slug = :slug,
                            seo_content = CAST(:seo_content AS jsonb),
                            schema_markup = CAST(:schema_markup AS jsonb),
                            updated_at = :updated_at
                        WHERE id = :id
                        """
                    ),
                    {
                        "id": vendor_id,
                        "slug": slug,
                        "seo_content": json.dumps(seo_content),
                        "schema_markup": json.dumps(schema_markup),
                        "updated_at": datetime.utcnow(),
                    },
                )
                await session.commit()
                enriched += 1

        except Exception as e:
            logger.error(f"  Error processing {vendor.get('name')}: {e}")
            errors += 1

    logger.info(f"DONE. enriched={enriched} errors={errors}")


def main():
    parser = argparse.ArgumentParser(description="Programmatic SEO Enrichment via Local Ollama")
    parser.add_argument("--limit", type=int, help="Limit vendors to process")
    parser.add_argument("--dry-run", action="store_true", help="Don't write to DB")
    args = parser.parse_args()

    asyncio.run(enrich_seo_vendors(args.limit, args.dry_run))


if __name__ == "__main__":
    main()
