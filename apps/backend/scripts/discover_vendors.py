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
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

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

# Static config extracted to discover_vendors_config.py
from scripts.discover_vendors_config import SKIP_DOMAINS, CATEGORY_QUERIES


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
