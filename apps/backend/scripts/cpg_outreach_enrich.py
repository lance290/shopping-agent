import asyncio
import argparse
import csv
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from enrich_vendors import (
    build_crawl_context,
    crawl_vendor_site_evidence,
    extract_supported_emails,
    extract_supported_phones,
    fetch_text,
    search_results,
    unique_strings,
)

# Setup logging to be clean and simple
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)
# Suppress noisy HTTP logs from httpx
logging.getLogger("httpx").setLevel(logging.WARNING)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
LLM_MODEL = os.getenv("SALES_RESEARCH_MODEL", "google/gemini-3-flash-preview")

LLM_SEM = asyncio.Semaphore(3)

RESOLVED_FIELDS = [
    "Resolved_Website",
    "Resolved_Contact_Name",
    "Resolved_Contact_Title",
    "Resolved_Contact_Email",
    "Resolved_Contact_Phone",
    "Resolved_Contact_Link",
    "Resolved_Tagline",
    "Resolved_Description",
    "Resolved_SEO_Summary",
    "Resolved_Services",
    "Resolved_Confidence",
    "Resolved_Source_URL",
    "Resolved_Search_Used",
    "Resolved_Last_Run_UTC",
    "Resolved_Notes",
]

EXTRACT_PROMPT = """You are an elite outbound research assistant working on premium luxury sales leads.
Research the lead \"{name}\".

Entity type: {entity_type}

Known row data:
{row_context}

Deterministic crawl evidence:
{crawl_context}

Search evidence:
{search_context}

Return ONLY valid JSON with no markdown fences:
{{
  \"website\": \"https://... or null\",
  \"tagline\": \"Short 1-sentence tagline or null\",
  \"description\": \"2-4 sentence factual description grounded in evidence\",
  \"seo_summary\": \"High-density 2-3 sentence summary of core offering or differentiators\",
  \"services_list\": [\"service 1\", \"service 2\"],
  \"contacts\": [
    {{
      \"name\": \"Best contact name or null\",
      \"title\": \"Role/title or null\",
      \"email\": \"explicit email if found else null\",
      \"phone\": \"best explicit phone if found else null\",
      \"linkedin_or_url\": \"LinkedIn or profile/contact URL if found else null\"
    }}
  ],
  \"confidence\": \"high|medium|low\"
}}

Rules:
- Prefer explicit first-party contact information.
- Do not invent emails or titles.
- If the lead itself is the contact, use that person as the primary contact.
- If only a general reservations/sales/help contact exists, return that.
"""

REPAIR_PROMPT = """The following model output should be valid JSON but is malformed or incomplete.
Repair it into valid JSON matching this schema exactly:
{{
  \"website\": \"string or null\",
  \"tagline\": \"string or null\",
  \"description\": \"string or null\",
  \"seo_summary\": \"string or null\",
  \"services_list\": [\"string\"],
  \"contacts\": [
    {{\"name\": \"string or null\", \"title\": \"string or null\", \"email\": \"string or null\", \"phone\": \"string or null\", \"linkedin_or_url\": \"string or null\"}}
  ],
  \"confidence\": \"high|medium|low\"
}}

Broken output:
{raw_text}

Context:
{context}
"""


def sanitize_string(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned or None


def first_present(row: Dict[str, str], keys: List[str]) -> Optional[str]:
    for key in keys:
        value = sanitize_string(row.get(key))
        if value:
            return value
    return None


def row_name(row: Dict[str, str]) -> str:
    return first_present(row, ["Agent_or_Team", "Vendor", "Brand", "Company"]) or "Unknown Lead"


def row_entity_type(row: Dict[str, str]) -> str:
    if row.get("Agent_or_Team"):
        return "luxury real estate agent or team"
    if row.get("Vendor"):
        return "luxury travel or hospitality vendor"
    return "luxury sales lead"


def row_location(row: Dict[str, str]) -> str:
    city = sanitize_string(row.get("City")) or ""
    state = sanitize_string(row.get("State")) or ""
    return ", ".join(part for part in [city, state] if part)


def row_context(row: Dict[str, str]) -> str:
    ordered_keys = [
        "Agent_or_Team",
        "Brokerage",
        "City",
        "State",
        "Vendor",
        "Category",
        "Why_it_fits_$2Mplus",
        "Why it matches",
        "Source",
        "Source_URL",
        "Public_Phone",
        "Primary contact",
        "Phone/WhatsApp",
        "Contact page / URL",
        "Notes",
        "Methodology_Notes",
    ]
    parts: List[str] = []
    for key in ordered_keys:
        value = sanitize_string(row.get(key))
        if value:
            parts.append(f"{key}: {value}")
    return "\n".join(parts)[:3000]


def url_candidates(row: Dict[str, str]) -> List[str]:
    values: List[str] = []
    for key in ["Resolved_Website", "Website", "Contact page / URL", "Source_URL"]:
        raw = row.get(key) or ""
        values.extend(re.findall(r"https?://[^\s|,]+", raw))
    return unique_strings([value.rstrip(").,") for value in values])


def search_queries(row: Dict[str, str]) -> List[str]:
    name = row_name(row)
    location = row_location(row)
    queries: List[str] = []
    if row.get("Agent_or_Team"):
        brokerage = sanitize_string(row.get("Brokerage")) or ""
        queries.extend([
            f'\"{name}\" \"{brokerage}\" {location} real estate email',
            f'\"{name}\" \"{brokerage}\" {location} contact',
            f'\"{name}\" \"{brokerage}\" {location} luxury real estate',
            f'\"{name}\" \"{brokerage}\" site:linkedin.com/in',
        ])
    else:
        category = sanitize_string(row.get("Category")) or "luxury travel"
        queries.extend([
            f'\"{name}\" {category} contact',
            f'\"{name}\" {category} email',
            f'\"{name}\" {category} reservations',
            f'\"{name}\" {location} contact',
        ])
    return unique_strings([query.strip() for query in queries if query.strip()])


async def build_search_context_for_row(row: Dict[str, str], limit_pages: int = 3) -> str:
    snippet_parts: List[str] = []
    page_parts: List[str] = []
    seen_urls = set()
    for query in search_queries(row):
        results = await search_results(query, num=6)
        for item in results:
            url = item.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            snippet_parts.append(f"Title: {item.get('title', '')}\nURL: {url}\nSnippet: {item.get('snippet', '')}")
            if len(page_parts) < limit_pages:
                page_text = await fetch_text(url)
                if page_text and len(page_text) > 120:
                    page_parts.append(f"URL: {url}\nText: {page_text[:2200]}")
            if len(seen_urls) >= 10:
                break
        if len(seen_urls) >= 10:
            break
    parts: List[str] = []
    if snippet_parts:
        parts.append("Search results:\n" + "\n\n".join(snippet_parts[:10]))
    if page_parts:
        parts.append("Search page text:\n" + "\n\n".join(page_parts[:limit_pages]))
    return "\n\n".join(parts)[:7000]


async def repair_json_with_openrouter(raw_text: str, context: str) -> Optional[Dict[str, Any]]:
    prompt = REPAIR_PROMPT.format(raw_text=raw_text, context=context)
    try:
        async with httpx.AsyncClient(timeout=60) as client:
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
                }
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?\n?", "", content)
                content = re.sub(r"\n?```$", "", content)
            return json.loads(content)
    except Exception:
        return None


async def llm_research_row(row: Dict[str, str], crawl_context: str, search_context: str) -> Optional[Dict[str, Any]]:
    prompt = EXTRACT_PROMPT.format(
        name=row_name(row),
        entity_type=row_entity_type(row),
        row_context=row_context(row) or "None",
        crawl_context=crawl_context or "None",
        search_context=search_context or "None",
    )
    raw_content = ""
    try:
        async with LLM_SEM:
            async with httpx.AsyncClient(timeout=120) as client:
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
                        "max_tokens": 1200,
                    }
                )
                resp.raise_for_status()
                raw_content = resp.json()["choices"][0]["message"]["content"]
    except Exception:
        return None

    try:
        cleaned = raw_content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
            cleaned = re.sub(r"\n?```$", "", cleaned)
        parsed = json.loads(cleaned)
        if not parsed.get("website") and not parsed.get("description") and not parsed.get("contacts"):
            return await repair_json_with_openrouter(raw_content, prompt)
        return parsed
    except json.JSONDecodeError:
        return await repair_json_with_openrouter(raw_content, prompt)


def normalize_contact(contact: Dict[str, Any]) -> Dict[str, str]:
    return {
        "name": sanitize_string(contact.get("name")) or "",
        "title": sanitize_string(contact.get("title")) or "",
        "email": sanitize_string(contact.get("email")) or "",
        "phone": sanitize_string(contact.get("phone")) or "",
        "linkedin_or_url": sanitize_string(contact.get("linkedin_or_url")) or "",
    }


def already_resolved(row: Dict[str, str]) -> bool:
    return any(sanitize_string(row.get(field)) for field in RESOLVED_FIELDS[:10])


def seed_emails_and_phones(row: Dict[str, str]) -> Dict[str, List[str]]:
    blob = " ".join([
        row.get("Primary contact") or "",
        row.get("Phone/WhatsApp") or "",
        row.get("Public_Phone") or "",
        row.get("Notes") or "",
    ])
    return {
        "emails": extract_supported_emails(blob),
        "phones": extract_supported_phones(blob),
    }


def infer_best_website(extracted: Dict[str, Any], urls: List[str]) -> Optional[str]:
    website = sanitize_string(extracted.get("website"))
    if website:
        return website
    for url in urls:
        if not url.lower().endswith(".pdf"):
            return url
    return urls[0] if urls else None


async def process_row(row: Dict[str, str]) -> Dict[str, str]:
    urls = url_candidates(row)
    seed_contact = seed_emails_and_phones(row)
    crawl_bundle = None
    for url in urls:
        if url.lower().endswith(".pdf"):
            continue
        crawl_bundle = await crawl_vendor_site_evidence(url)
        if crawl_bundle:
            break

    crawl_context = build_crawl_context(crawl_bundle) if crawl_bundle else ""
    combined_crawl_context = "\n\n".join(part for part in [row_context(row), crawl_context] if part)[:12000]
    search_context = ""
    if not crawl_bundle or not (((crawl_bundle.get("emails") or []) if crawl_bundle else []) or seed_contact["emails"]):
        search_context = await build_search_context_for_row(row)

    extracted = await llm_research_row(row, combined_crawl_context or row_context(row), search_context)
    if not extracted:
        row["Resolved_Notes"] = "LLM extraction failed"
        row["Resolved_Last_Run_UTC"] = datetime.utcnow().isoformat()
        return row

    contacts = [normalize_contact(contact) for contact in extracted.get("contacts", []) if isinstance(contact, dict)]
    explicit_emails = unique_strings(seed_contact["emails"] + (((crawl_bundle or {}).get("emails") or []) if crawl_bundle else []) + extract_supported_emails(search_context))
    explicit_phones = unique_strings(seed_contact["phones"] + (((crawl_bundle or {}).get("phones") or []) if crawl_bundle else []) + extract_supported_phones(search_context))
    if contacts:
        primary = contacts[0]
    else:
        primary = {
            "name": row_name(row) if row.get("Agent_or_Team") else (sanitize_string(row.get("Primary contact")) or ""),
            "title": sanitize_string(row.get("Brokerage")) or "",
            "email": "",
            "phone": "",
            "linkedin_or_url": "",
        }
    if not primary.get("email") and explicit_emails:
        primary["email"] = explicit_emails[0]
    if not primary.get("phone") and explicit_phones:
        primary["phone"] = explicit_phones[0]
    if not primary.get("linkedin_or_url"):
        for url in urls:
            if not url.lower().endswith(".pdf"):
                primary["linkedin_or_url"] = url
                break

    summary = sanitize_string(extracted.get("seo_summary")) or sanitize_string(extracted.get("description")) or ""
    services_list = extracted.get("services_list") if isinstance(extracted.get("services_list"), list) else []
    confidence = sanitize_string(extracted.get("confidence")) or ("high" if primary.get("email") else "medium" if infer_best_website(extracted, urls) else "low")

    row["Resolved_Website"] = infer_best_website(extracted, urls) or ""
    row["Resolved_Contact_Name"] = primary.get("name", "")
    row["Resolved_Contact_Title"] = primary.get("title", "")
    row["Resolved_Contact_Email"] = primary.get("email", "")
    row["Resolved_Contact_Phone"] = primary.get("phone", "")
    row["Resolved_Contact_Link"] = primary.get("linkedin_or_url", "")
    row["Resolved_Tagline"] = sanitize_string(extracted.get("tagline")) or ""
    row["Resolved_Description"] = sanitize_string(extracted.get("description")) or ""
    row["Resolved_SEO_Summary"] = summary
    row["Resolved_Services"] = " | ".join(str(item).strip() for item in services_list if str(item).strip())
    row["Resolved_Confidence"] = confidence
    row["Resolved_Source_URL"] = (crawl_bundle or {}).get("website") or (urls[0] if urls else "")
    row["Resolved_Search_Used"] = "TRUE" if bool(search_context.strip()) else "FALSE"
    row["Resolved_Last_Run_UTC"] = datetime.utcnow().isoformat()
    row["Resolved_Notes"] = sanitize_string(row.get("Resolved_Notes")) or ""
    return row


def write_rows(csv_path: Path, fieldnames: List[str], rows: List[Dict[str, str]]) -> None:
    with open(csv_path, "w", encoding="utf-8", newline="") as out_f:
        writer = csv.DictWriter(out_f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


async def process_csv(csv_path: Path, limit: Optional[int], force: bool) -> None:
    if not csv_path.exists():
        logger.error(f"Input CSV not found at {csv_path}")
        return

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = [dict(row) for row in reader]
        fieldnames = list(reader.fieldnames or [])
    for field in RESOLVED_FIELDS:
        if field not in fieldnames:
            fieldnames.append(field)

    selected_indices = [
        index for index, row in enumerate(rows)
        if row_name(row) != "Unknown Lead" and (force or not already_resolved(row))
    ]
    if limit:
        selected_indices = selected_indices[:limit]

    total = len(selected_indices)
    print("=====================================================")
    print(f"🚀 Starting luxury lead enrichment on {csv_path.name}")
    print(f"   Rows to process: {total} / {len(rows)}")
    print("=====================================================\n")

    for position, row_index in enumerate(selected_indices, start=1):
        percent = int((position / total) * 100) if total else 100
        logger.info(f"[{position}/{total}] ({percent}%) 🔍 Researching {row_name(rows[row_index])}...")
        rows[row_index] = await process_row(rows[row_index])
        write_rows(csv_path, fieldnames, rows)
        logger.info("")

    print("\n=====================================================")
    print(f"✅ Finished processing {csv_path.name}")
    print(f"📂 Updated in place: {csv_path}")
    print("=====================================================")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generic luxury sales lead enricher")
    parser.add_argument("--input-csv", required=True, help="CSV file to enrich in place")
    parser.add_argument("--limit", type=int, help="Limit the number of unresolved rows to process")
    parser.add_argument("--force", action="store_true", help="Reprocess rows even if resolved fields already exist")
    args = parser.parse_args()

    if not OPENROUTER_API_KEY:
        logger.error("OPENROUTER_API_KEY not set")
        sys.exit(1)

    csv_path = Path(args.input_csv)
    if not csv_path.is_absolute():
        csv_path = (Path.cwd() / csv_path).resolve()
    asyncio.run(process_csv(csv_path, args.limit, args.force))


if __name__ == "__main__":
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    main()
