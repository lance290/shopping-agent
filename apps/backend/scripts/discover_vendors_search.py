import aiohttp
from typing import List, Dict, Optional
import os

SERPAPI_KEY = os.getenv("SERPAPI_API_KEY", "")
SCALESERP_KEY = os.getenv("SCALESERP_API_KEY", "")
SEARCHAPI_KEY = os.getenv("SEARCHAPI_API_KEY", "")



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
