"""
LLM service — unified decision engine, choice factor generation, provider query triage.

Ported from apps/bff/src/llm.ts as part of PRD-02 (Kill BFF).
Implementations split across llm_core.py (API calls), llm_models.py (data models),
and llm_pop.py (Pop grocery engine). This file keeps make_unified_decision,
choice factors, provider triage, outreach email, and re-exports everything.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Re-export core LLM functions for backward compatibility
from services.llm_core import (  # noqa: E402, F401
    call_gemini,
    _extract_json,
    _extract_json_array,
    _get_gemini_api_key,
    _get_openrouter_api_key,
    GEMINI_MODEL,
    OPENROUTER_MODEL,
)

# Re-export data models for backward compatibility
from services.llm_models import (  # noqa: E402, F401
    DESIRE_TIERS,
    UserIntent,
    ClarificationAction,
    DisambiguateOption,
    DisambiguateAction,
    SimpleAction,
    UnifiedDecision,
    VendorCoverageAssessment,
    ChatContext,
)

# Re-export Pop decision engine for backward compatibility
from services.llm_pop import make_pop_decision  # noqa: E402, F401


# =============================================================================
# UNIFIED LLM DECISION
# =============================================================================

async def make_unified_decision(ctx: ChatContext) -> UnifiedDecision:
    """
    Single LLM call to decide what action to take based on user message and context.
    Ported from BFF's makeUnifiedDecision() in llm.ts.
    """
    active_row_json = json.dumps({
        "id": ctx.active_row["id"],
        "title": ctx.active_row.get("title", ""),
        "constraints": ctx.active_row.get("constraints", {}),
        "is_service": ctx.active_row.get("is_service", False),
        "service_category": ctx.active_row.get("service_category"),
    }) if ctx.active_row else "none"

    active_project_json = json.dumps({
        "id": ctx.active_project["id"],
        "title": ctx.active_project.get("title", ""),
    }) if ctx.active_project else "none"

    pending_json = json.dumps(ctx.pending_clarification) if ctx.pending_clarification else "none"

    recent = ctx.conversation_history[-6:] if ctx.conversation_history else []
    recent_text = "\n".join(f"  {m['role']}: {m['content']}" for m in recent)

    prompt = f"""You are the decision engine for a shopping/procurement assistant.

INPUTS:
- User message: "{ctx.user_message}"
- Active row: {active_row_json}
- Active project: {active_project_json}
- Pending clarification: {pending_json}
- Recent conversation:
{recent_text}

YOUR JOB: 
1. UNDERSTAND what the user wants (their INTENT)
2. Decide what action to take
3. Return JSON with BOTH intent and action

=== INTENT (REQUIRED - this is the most important part) ===
You MUST always return an "intent" object that captures WHAT THE USER WANTS:

{{
    "intent": {{
    "what": "The core thing they want - e.g., 'private jet charter', 'kids baseball glove', 'custom diamonds'",
    "category": "request",
    "service_type": "optional vendor category hint: private_aviation, roofing, hvac, jewelry, catering, etc. Use when a vendor directory might have relevant providers. null if unsure.",
    "search_query": "The query to find this - derived from WHAT, not conversation snippets",
    "constraints": {{ structured data ONLY: origin, destination, date, size, color, price, recipient, delivery_type, passengers, etc. NEVER include 'what', 'is_service', 'service_category', 'search_query', or 'title' in constraints — those belong in the parent intent fields. }},
    "location_context": {{
      "relevance": "none|endpoint|service_area|vendor_proximity",
      "confidence": 0.0-1.0,
      "targets": {{
        "origin": "optional place string",
        "destination": "optional place string",
        "service_location": "optional place string",
        "search_area": "optional place string",
        "vendor_market": "optional place string"
      }},
      "notes": "optional short explanation"
    }},
    "desire_tier": "one of: commodity, considered, service, bespoke, high_value, advisory",
    "desire_confidence": 0.0-1.0,
    "execution_mode": "one of: affiliate_only, sourcing_only, affiliate_plus_sourcing",
    "search_strategies": ["one or more of: official_first, market_first, specialist_first, prestige_first, local_network_first"],
    "source_archetypes": ["zero or more of: brokerage, association, registry, curated_marketplace, editorial_ranking, local_directory, prior_trusted_source, brand_direct, auction_house, official_body"]
  }}
}}

=== DESIRE TIER (classify EVERY request) ===
Before deciding the action, classify what KIND of desire this is:

| Tier | When to use | Examples |
| commodity | Simple product or standard ticket/event | "AA batteries", "Roblox gift card", "running shoes", "Taylor Swift concert tickets", "NBA game tickets" |
| considered | Complex product or event needing comparison | "laptop for video editing", "best DSLR camera", "Notre Dame vs Clemson tickets", "Broadway show for anniversary" |
| service | Hire someone / book a service | "private jet charter", "HVAC repair", "catering for 200", "wedding photographer" |
| bespoke | Custom-made / commissioned item | "custom engagement ring", "commission a mural", "bespoke suit" |
| high_value | Major asset purchase (>$100k typically) | "mega-yacht", "aircraft purchase", "commercial real estate" |
| advisory | Needs professional advisory, not a search | "acquire a SaaS company", "set up a family trust", "corporate M&A" |

CRITICAL: The desire_tier drives how the system helps the user:
- commodity/considered → web search (Amazon, eBay, Google Shopping, Ticketmaster for events)
- service/bespoke → vendor directory search (match with specialists) — do NOT search Amazon
- high_value → broker/specialist matching — do NOT search Amazon
- advisory → flag for human review — no search at all

Set desire_confidence to how sure you are (0.0-1.0). If < 0.7, the system will ask a clarifying question.

=== EXECUTION MODE (classify EVERY request) ===
After determining the desire tier, decide the execution mode — this controls which provider families run:

| Mode | When to use | Examples |
| affiliate_only | Simple product purchases where affiliate/marketplace providers suffice | "AA batteries", "running shoes", "Roblox gift card" |
| sourcing_only | Services, specialists, brokers, high-value assets where marketplace providers can't help | "private jet charter", "Nashville realtor", "yacht broker", "custom engagement ring" |
| affiliate_plus_sourcing | Complex requests benefiting from both marketplace results AND specialist discovery | "luxury watch" (marketplace for new + specialist for pre-owned), "concert tickets" (Ticketmaster + broker) |

Rules:
- commodity/considered desire_tier usually → affiliate_only (unless the user explicitly wants specialists)
- service/bespoke/high_value/advisory → sourcing_only (marketplace results are noise for these)
- Only use affiliate_plus_sourcing when BOTH provider families genuinely add value

=== SEARCH STRATEGIES (for sourcing_only and affiliate_plus_sourcing) ===
When execution_mode includes sourcing, pick one or more search strategies that best match the request:

| Strategy | When to use | Examples |
| official_first | Authoritative/official sources matter most | "FAA registered aircraft", "licensed contractor" |
| market_first | Broad market comparison matters | "best price on Rolex Submariner", "compare yacht charters" |
| specialist_first | Need domain specialists, brokers, agents | "Nashville realtor", "M&A advisor", "private aviation broker" |
| prestige_first | Prestige, editorial, or curated sources matter | "top-rated interior designer", "Michelin restaurant for event" |
| local_network_first | Local vendor presence matters most | "HVAC repair near me", "Nashville wedding photographer" |

Most real requests should use 1-3 strategies. For example, "realtors in Nashville for a $3M mansion" → ["specialist_first", "prestige_first", "local_network_first"].
For affiliate_only requests, leave search_strategies as an empty array.

=== SOURCE ARCHETYPES (optional, for sourcing modes) ===
If you can infer what KIND of sources would be ideal, list them. This helps the system know what to look for:
brokerage, association, registry, curated_marketplace, editorial_ranking, local_directory, prior_trusted_source, brand_direct, auction_house, official_body.
Example: "Nashville realtor" → ["brokerage", "local_directory", "association"]. Leave empty if unsure.

CRITICAL INTENT RULES:
- "what" is NEVER a date, number, or clarification answer. It's the THING they want.
- "search_query" is derived from "what" + key constraints. NOT from "Feb 13" or "7 people".
- If user says "private jet from SAN to EWR" then later "Feb 13, 7 people":
  - what: "private jet charter"
  - search_query: "private jet charter SAN to EWR"
  - constraints: {{ origin: "SAN", destination: "EWR", date: "Feb 13", passengers: 7, passenger_names: "John Doe, Jane Doe" }}
- If pending_clarification exists, MERGE its intent with new info. The "what" comes from the ORIGINAL request.

VENDOR CATEGORY HINT:
- Set service_type to a vendor category when the request might benefit from matching against a vendor directory.
- Examples: "private_aviation", "roofing", "hvac", "jewelry", "catering", "photography", "auto_repair", "events", "tickets"
- This is just a hint — the system will ALWAYS search for both vendors and web results regardless.
- Set to null if no obvious vendor category applies (e.g. "Roblox gift card").

LOCATION MODE RULES:
- Use "endpoint" when route endpoints matter more than vendor office location. Example: private aviation, yacht charter.
- Use "service_area" when the vendor must cover a market or region, but physical nearness is secondary. Example: real estate brokers, interior design.
- Use "vendor_proximity" when local vendor presence matters strongly. Example: roofing, HVAC, photography.
- Use "none" when location should not materially affect ranking. Example: jewelry or commodity product search unless the user explicitly asks for local.
- Always fill location_context.targets from any usable location strings you can extract.

=== ACTION TYPES ===
1. "create_row" - Create new request (no active row, or after clarification)
2. "update_row" - Refine active row (same topic: price, color, size)
3. "context_switch" - User switched to completely different topic - create new row, clear chat
4. "ask_clarification" - Need essential info before proceeding (use sparingly)
5. "search" - Refresh search on current row
6. "vendor_outreach" - Reach out to vendors for quotes
7. "disambiguate" - Query is genuinely ambiguous (e.g., "apple" could be fruit or tech). Offer 2-4 options with label, search_query, category. Use SPARINGLY — only when truly ambiguous.

RULES:
- Active row exists AND user asks for UNRELATED thing (completely different product/service) → context_switch
- Active row exists AND user refines/adds to it (same topic) → update_row. THIS INCLUDES: adding round-trip details, changing dates, adding passengers, specifying aircraft, updating any constraint. If in doubt and same topic, ALWAYS use update_row.
- NO active row → create_row
- pending_clarification exists AND active row exists AND user provides info → update_row (merge intent into active row)
- pending_clarification exists AND NO active row AND user provides info → create_row (merge intent)
- pending_clarification exists BUT user asks for something else → context_switch

CRITICAL: If an active row exists and the user's message relates to the SAME category/topic, you MUST use update_row. NEVER create a duplicate row for the same request. "Make it round trip", "add return leg", "change date", "2 passengers" — these are ALL update_row when an active row exists.

=== LISTS & MULTIPLE ITEMS ===
If the user asks for multiple completely separate things in one message (e.g., a grocery list, or "I need a lawnmower and some running shoes"), return them in the `items` array and set `action` to `create_row`.
If the user names the list (e.g., "Camping trip: tent, sleeping bag, stove"), set `project_title` to "Camping Trip".
Otherwise, if it's just a bunch of random items, set `project_title` to a logical group name or null.

For MULTIPLE items, your JSON MUST look like this:
{{
  "message": "I'll start searching for these items right away.",
  "action": {{ "type": "create_row" }},
  "project_title": "Camping Trip",
  "items": [
    {{ "what": "Tent", "search_query": "4 person camping tent" }},
    {{ "what": "Sleeping Bag", "search_query": "cold weather sleeping bag" }},
    {{ "what": "Stove", "search_query": "portable camping stove" }}
  ],
  "intent": {{ "what": "Multiple items", "category": "product", "search_query": "list", "constraints": {{}}, "desire_tier": "commodity", "desire_confidence": 0.9 }}
}}

=== STRUCTURED RFP BUILDER (Phase 4) ===
You are NOT just a chatbot. You are a procurement agent. For every request, follow this pattern:

1. IDENTIFY CHOICE FACTORS for the category. Every product/service category has 3-6 key decision factors:
   - Electronics: brand, specs, budget, warranty, condition
   - Vehicles: make/model, year, mileage, budget, features
   - Events/Tickets: event name, date, venue/city, number of tickets, seating preference, budget
   - Services (aviation): origin, destination, date, passengers, passenger_names, aircraft type
   - Services (catering): date, location, headcount, cuisine, dietary restrictions
   - Services (general): date, location, scope, budget, timeline
   - Apparel: size, color, material, brand, budget
   - Home goods: dimensions, style, material, budget, delivery timeline

2. ASK about missing choice factors using ask_clarification. Be specific:
   - BAD: "Can you tell me more?"
   - GOOD: "To find the best options, I need a few details:\\n• What's your budget range?\\n• Any preferred brands?\\n• New or refurbished OK?"
   - Ask 2-3 questions MAX per turn. Don't overwhelm.

3. SUMMARIZE before creating/searching. When you have enough info, your message should include a brief summary.

4. Only use ask_clarification when you're missing ESSENTIAL choice factors. For simple product searches with enough context, go straight to create_row.

COMPLEX REQUESTS (services, custom/bespoke items, high-value purchases):
- SEARCH IMMEDIATELY + ASK ALONGSIDE. Never block the search with ask_clarification.
- If the user provides ANY recognizable service request (e.g. "yacht charter San Diego"), use create_row to START THE SEARCH, and include 2-3 clarifying questions IN YOUR MESSAGE TEXT.
- The system searches vendors + products in parallel while the user answers your questions.
- Example message for "yacht charter, San Diego to Acapulco, March 1-31, one passenger":
  "I'll start searching for yacht charter options from San Diego to Acapulco for March. While I search, a few questions to narrow down the best match:
  • Do you prefer a motor yacht or sailing yacht?
  • Any preference on yacht size or number of cabins?
  • Full crew with chef, or bareboat charter?"
- The action should be create_row (or update_row if row exists) — NOT ask_clarification.
- ONLY use ask_clarification when the request is so vague you literally cannot form a search query (e.g. "I need something nice" with zero context).
- "No budget" / "no preference" / "any" counts as a provided detail.
- Essential details to ASK ABOUT (in your message, not as a blocking action):
  - Private jets: aircraft type, one-way vs round-trip
  - Yacht charter: vessel type (motor/sailing), crew preference, yacht size
  - Catering: cuisine type, dietary restrictions
  - Photography: style preference, deliverables
  - Custom jewelry: carat, metal preference, setting style
  - General services: budget range, timeline, special requirements

=== UI HINT (optional but recommended) ===
Select how the results should be displayed. Pick a layout and list which UI blocks to show:

Layouts: ROW_COMPACT (text-only comparison), ROW_MEDIA_LEFT (image + details), ROW_TIMELINE (progress/fulfillment tracking)
Blocks (pick 3-6 from): ProductImage, PriceBlock, DataGrid, FeatureList, BadgeList, MarkdownText, Timeline, MessageList, ChoiceFactorForm, ActionRow

Examples:
- Grocery items: {{"layout": "ROW_MEDIA_LEFT", "blocks": ["ProductImage", "PriceBlock", "BadgeList", "ActionRow"], "value_vector": "unit_price"}}
- Private jet charter: {{"layout": "ROW_TIMELINE", "blocks": ["DataGrid", "BadgeList", "Timeline", "ActionRow"], "value_vector": "safety"}}
- Simple product search: {{"layout": "ROW_COMPACT", "blocks": ["MarkdownText", "PriceBlock", "BadgeList", "ActionRow"]}}
- Custom/bespoke item needing details: {{"layout": "ROW_COMPACT", "blocks": ["MarkdownText", "ChoiceFactorForm", "ActionRow"]}}

Return ONLY valid JSON:
{{
  "message": "Conversational response to user (REQUIRED)",
  "intent": {{ "what": "...", "category": "...", "service_type": "...", "search_query": "...", "constraints": {{...}}, "location_context": {{"relevance": "none|endpoint|service_area|vendor_proximity", "confidence": 0.85, "targets": {{}}, "notes": null}}, "desire_tier": "commodity|considered|service|bespoke|high_value|advisory", "desire_confidence": 0.9, "execution_mode": "affiliate_only|sourcing_only|affiliate_plus_sourcing", "search_strategies": ["specialist_first", "local_network_first"], "source_archetypes": ["brokerage", "local_directory"] }},
  "action": {{ "type": "..." }},
  "ui_hint": {{ "layout": "ROW_COMPACT|ROW_MEDIA_LEFT|ROW_TIMELINE", "blocks": ["..."], "value_vector": "unit_price|safety|speed|reliability|durability" }}
}}"""

    try:
        text = await call_gemini(prompt, timeout=30.0)
        parsed = _extract_json(text)

        # Handle multi-item responses
        items_list = parsed.pop("items", None)
        if items_list and isinstance(items_list, list) and len(items_list) > 0:
            first = items_list[0]
            if "intent" not in parsed:
                parsed["intent"] = {
                    "what": first.get("what", ""),
                    "category": "product",
                    "search_query": first.get("search_query", f"{first.get('what', '')} deals"),
                    "constraints": {},
                    "desire_tier": "commodity",
                    "desire_confidence": 0.95,
                }
            decision = UnifiedDecision(**parsed)
            decision.items = items_list
            return decision

        return UnifiedDecision(**parsed)
    except Exception as e:
        logger.error(f"Failed to parse LLM decision: {e}")
        # Fallback: create a basic row from the user message
        return UnifiedDecision(
            message="I'll help you find that. Let me set up a search for you.",
            intent=UserIntent(
                what=ctx.user_message,
                category="product",
                search_query=ctx.user_message,
                constraints={},
            ),
            action={"type": "create_row"},
        )


# make_pop_decision extracted to services/llm_pop.py (re-exported above)


# =============================================================================
# CHOICE FACTOR GENERATION
# =============================================================================

async def generate_choice_factors(
    item_description: str,
    existing_constraints: Optional[Dict[str, Any]] = None,
    is_service: bool = False,
    service_category: Optional[str] = None,
) -> Optional[List[Dict[str, Any]]]:
    """
    Generate choice factors for an item/service via LLM.
    Returns a list of factor dicts, or None on failure.
    Ported from BFF's generateAndSaveChoiceFactors() in llm.ts.
    """
    constraints_text = f"\nExisting constraints: {json.dumps(existing_constraints)}" if existing_constraints else ""
    service_context = f"\nThis is a SERVICE request (category: {service_category or 'service'}), NOT a product purchase. Generate service-specific fields." if is_service else ""

    prompt = f"""You are determining the key specifications for: "{item_description}"{service_context}{constraints_text}

Return a JSON array of 3-6 key specifications. Each spec should have:
- name: lowercase_snake_case identifier (MUST match keys in existing constraints if present)
- label: Human-readable label (e.g. "Screen Size", "Budget")
- type: "number" | "select" | "text" | "boolean"
- options: array of strings (only for "select" type)
- required: boolean

Example for "laptop":
[
  {{"name": "budget", "label": "Max Budget", "type": "number", "required": true}},
  {{"name": "primary_use", "label": "Primary Use", "type": "select", "options": ["gaming", "work", "school", "general"], "required": true}},
  {{"name": "screen_size", "label": "Screen Size", "type": "select", "options": ["13 inch", "15 inch", "17 inch"], "required": false}}
]

Example for "private jet charter" or any flight/travel service:
[
  {{"name": "from_airport", "label": "Departure Airport", "type": "text", "required": true}},
  {{"name": "to_airport", "label": "Arrival Airport", "type": "text", "required": true}},
  {{"name": "departure_date", "label": "Departure Date", "type": "text", "required": true}},
  {{"name": "wheels_up_time", "label": "Wheels Up Time", "type": "text", "required": true}},
  {{"name": "trip_type", "label": "Trip Type", "type": "select", "options": ["one-way", "round-trip"], "required": true}},
  {{"name": "passengers", "label": "Passengers", "type": "number", "required": true}},
  {{"name": "passenger_names", "label": "Passenger Names", "type": "text", "required": false}}
]

IMPORTANT: If "Existing constraints" are provided, you MUST include a spec definition for each constraint key so the UI can display it.

Return ONLY the JSON array, no explanation."""

    try:
        text = await call_gemini(prompt, timeout=20.0)
        factors = _extract_json_array(text)

        if not isinstance(factors, list):
            return None

        # Clean up factors: fix empty select options
        cleaned = []
        for f in factors:
            if not isinstance(f, dict):
                continue
            if f.get("type") == "select":
                options = f.get("options", [])
                if not isinstance(options, list) or len(options) == 0:
                    f["type"] = "text"
                    f.pop("options", None)
                else:
                    f["options"] = [o for o in options if isinstance(o, str) and o.strip()]
                    if not f["options"]:
                        f["type"] = "text"
                        f.pop("options", None)
            cleaned.append(f)

        # Ensure every constraint key has a matching factor
        if existing_constraints:
            factor_names = {f.get("name") for f in cleaned}
            for key in existing_constraints:
                if key not in factor_names:
                    label = " ".join(w.capitalize() for w in key.split("_"))
                    cleaned.append({"name": key, "label": label, "type": "text", "required": False})

        return cleaned

    except Exception as e:
        logger.error(f"Error generating choice factors: {e}")

        # Fallback for aviation
        if service_category == "private_aviation":
            logger.warning("Using hardcoded aviation factors as fallback")
            fallback = [
                {"name": "from_airport", "label": "Departure Airport", "type": "text", "required": True},
                {"name": "to_airport", "label": "Arrival Airport", "type": "text", "required": True},
                {"name": "departure_date", "label": "Departure Date", "type": "text", "required": True},
                {"name": "wheels_up_time", "label": "Wheels Up Time", "type": "text", "required": True},
                {"name": "trip_type", "label": "Trip Type", "type": "select", "options": ["one-way", "round-trip"], "required": True},
                {"name": "passengers", "label": "Passengers", "type": "number", "required": True},
                {"name": "passenger_names", "label": "Passenger Names", "type": "text", "required": False},
                {"name": "aircraft_class", "label": "Aircraft Class", "type": "select", "options": ["light jet", "midsize jet", "super-midsize jet", "heavy jet", "ultra-long-range"], "required": False},
                {"name": "wifi", "label": "Wi-Fi Required", "type": "select", "options": ["yes", "no", "preferred"], "required": False},
            ]
            if existing_constraints:
                factor_names = {f["name"] for f in fallback}
                for key in existing_constraints:
                    if key not in factor_names:
                        label = " ".join(w.capitalize() for w in key.split("_"))
                        fallback.append({"name": key, "label": label, "type": "text", "required": False})
            return fallback

        return None


# =============================================================================
# PROVIDER QUERY TRIAGE
# =============================================================================

def _heuristic_provider_query(display_query: str) -> str:
    """Heuristic fallback for provider query: strip price patterns."""
    q = display_query
    q = re.sub(r"\$\s*\d+(?:\.\d+)?", "", q)
    q = re.sub(r"\b(over|under|below|above)\s*\$?\s*\d+(?:\.\d+)?\b", "", q, flags=re.IGNORECASE)
    q = re.sub(r"\b\d+\s*\+\b", "", q)
    q = re.sub(r"\$\s*\d+(?:\.\d+)?\s*(and\s*up|\+|or\s*more|and\s*above)\b", "", q, flags=re.IGNORECASE)
    q = re.sub(r"\b(and\s*up|or\s*more|and\s*above)\b", "", q, flags=re.IGNORECASE)
    q = re.sub(r"[()]", " ", q)
    q = " ".join(q.split()).strip()
    return q


async def generate_outreach_email(
    row_title: str,
    vendor_company: str,
    sender_name: str,
    **kwargs,
) -> Dict[str, str]:
    """
    Generate a personalized outreach email to a vendor using LLM.
    Includes ALL request details so the vendor can quote without a form.
    Returns {"subject": ..., "body": ...}.
    """
    safe_sender = sender_name or "BuyAnything Concierge"
    chat_history = kwargs.get("chat_history") or ""
    choice_answers = kwargs.get("choice_answers") or ""
    search_intent = kwargs.get("search_intent") or ""
    structured_constraints = kwargs.get("structured_constraints") or ""
    sender_company = kwargs.get("sender_company") or ""

    parsed_intent = search_intent
    if isinstance(search_intent, str):
        try:
            parsed_intent = json.loads(search_intent)
        except Exception:
            parsed_intent = {}
    if not isinstance(parsed_intent, dict):
        parsed_intent = {}

    def _sig_tokens(value: object) -> set[str]:
        text = str(value or "").lower()
        return {
            token for token in re.findall(r"[a-z0-9]+", text)
            if len(token) > 2 and token not in {"the", "and", "for", "with", "from", "your", "that"}
        }

    product_name = str(parsed_intent.get("product_name") or "").strip()
    raw_input = str(parsed_intent.get("raw_input") or "").strip()
    location_context = parsed_intent.get("location_context") if isinstance(parsed_intent.get("location_context"), dict) else {}
    location_mode = str(location_context.get("relevance") or "none")
    request_summary = row_title.strip() or product_name or raw_input or "your request"
    if raw_input:
        if not product_name:
            request_summary = raw_input
        elif location_mode in {"service_area", "vendor_proximity"} and len(_sig_tokens(raw_input) - _sig_tokens(product_name)) >= 2:
            request_summary = raw_input
        elif len(_sig_tokens(raw_input) - _sig_tokens(request_summary)) >= 3:
            request_summary = raw_input

    prompt = f"""You are writing a professional outreach email from a buyer directly to a vendor.

== CONTEXT (raw structured data — do NOT copy these fields verbatim) ==
Title: {row_title}
Request summary: {request_summary}
Vendor: {vendor_company}
Sender: {safe_sender}{(' at ' + sender_company) if sender_company else ''}
Search intent JSON: {search_intent}
Buyer preferences JSON: {choice_answers}
Structured constraints JSON: {structured_constraints}
Chat history: {chat_history[:1500] if chat_history else 'N/A'}

== YOUR TASK ==
Write a natural, professional email where {safe_sender} reaches out DIRECTLY to {vendor_company} as a potential customer{(' representing ' + sender_company) if sender_company else ''}:
1. Greets {vendor_company} warmly.
2. Explains what {safe_sender} is looking for IN NATURAL PROSE — weave the details into sentences.
   - For SERVICES (charters, contractors, etc.): mention dates, locations, number of people, budget range, specific requirements.
   - For PRODUCTS (snow blowers, electronics, etc.): mention the product, any specs or preferences, quantity, and ask for pricing/availability.
3. Asks the vendor to reply with their quote, availability, and any questions.
4. Signs off as {safe_sender}{(' — ' + sender_company) if sender_company else ''}.
5. Keeps it under 200 words, warm but professional.

== CRITICAL RULES FOR CONSTRAINT USAGE ==
You MUST extract and use ALL relevant details from these structured fields:
1. Search intent JSON → location_context (origin, destination, service_location, vendor_market, search_area)
2. Buyer preferences JSON → delivery_type, passengers, trip_type, date, wheels_up_time, aircraft_class, etc.
3. Structured constraints JSON → ALL fields the buyer specified
4. Location resolution → resolved city/state/coordinates if present

DO NOT write generic "I'm looking for X" or "I need to book a jet" without specifics. ALWAYS include:
- LOCATION DETAILS: If origin/destination/service_location exists in search_intent JSON, mention them explicitly
  - Example: "I need a private jet from San Diego (SAN) to Newark (EWR)" NOT "I need to book a jet"
  - Example: "Looking for luxury real estate brokers serving the Nashville, TN market" NOT "Looking for brokers"
- DATE/TIME: If date, departure_date, or wheels_up_time exists, mention it
  - Example: "on February 13, 2026, wheels up at 9:00 AM" NOT "soon"
- PASSENGER/GROUP SIZE: If passengers, headcount, or number_of_tickets exists, mention it
  - Example: "for 7 passengers: John Doe, Jane Doe, Bob Smith, etc." NOT "for a group"
- PRODUCT SPECIFICITY: If delivery_type, size, color, or other product constraints exist, mention them
  - Example: "physical Roblox gift cards (not digital)" NOT "Roblox gift cards"
  - Example: "in-store pickup preferred" NOT "delivery options"
- BUDGET/PRICE: If budget, max_budget, or price range exists, mention it
  - Example: "Budget range: $15,000-$25,000" NOT "competitive pricing"

If a constraint exists in ANY of the JSON fields, you MUST weave it into natural prose in the email body.
If location_context.targets has vendor_market or service_location, mention the location even if it's not in constraints.

== CRITICAL RULES (EXISTING) ==
- The sender is the BUYER, NOT a concierge or third party. Write in first person ("I'm looking for..." or "We're looking for...").
- NEVER mention "BuyAnything", "concierge", "on behalf of", "my client", or any platform name.
- NEVER dump raw field names like "Product Category:", "Keywords:", "Product Name:", "origin:", "destination:".
- NEVER mention forms, links, or buttons.
- NEVER invent details not present in the context above.
- If details are sparse, keep the email short and simple — don't pad it.
- Write like a real person, not a template.

Return JSON ONLY: {{"subject": "...", "body": "..."}}"""

    fallback_body = f"Hi {vendor_company},\n\nI'm looking for: {request_summary}.\n\nCould you reply with your pricing and availability?\n\nBest regards,\n{safe_sender}"

    try:
        text = await call_gemini(prompt, timeout=15.0)
        parsed = _extract_json(text)
        return {
            "subject": parsed.get("subject", f"Quote Request: {request_summary}"),
            "body": parsed.get("body", fallback_body),
        }
    except Exception:
        return {
            "subject": f"Quote Request: {request_summary}",
            "body": fallback_body,
        }


async def assess_vendor_coverage(
    row_title: str,
    search_query: str,
    desire_tier: Optional[str],
    service_type: Optional[str],
    search_intent: Optional[Any],
    choice_answers: Optional[Any],
    provider_statuses: List[Dict[str, Any]],
    results: List[Dict[str, Any]],
) -> Optional[VendorCoverageAssessment]:
    """Use the LLM to decide whether a real search exposed a vendor coverage gap."""
    prompt = f"""You are evaluating whether BuyAnything has adequate vendor coverage for a real user request.

Inputs:
- Row title: {json.dumps(row_title or '')}
- Search query: {json.dumps(search_query or '')}
- Desire tier: {json.dumps(desire_tier or '')}
- Service type hint: {json.dumps(service_type or '')}
- Search intent JSON: {json.dumps(search_intent or {})}
- Choice answers JSON: {json.dumps(choice_answers or {})}
- Provider statuses JSON: {json.dumps(provider_statuses[:12])}
- Search results JSON: {json.dumps(results[:12])}

Your task:
1. Decide whether the main issue is a true vendor supply gap.
2. Only mark should_log_gap=true when the evidence suggests we need more or better vendors in our vendor database.
3. If the problem looks like search quality, query generation, filtering, or irrelevant marketplace noise rather than missing vendors, set should_log_gap=false.
4. Prefer conservative judgment. Do not create sourcing work unless the gap is real and actionable.

Guidance:
- Commodity product requests often do NOT need vendor database expansion unless the request clearly needs specialized suppliers.
- Service, bespoke, and high_value requests are the strongest candidates for vendor coverage gaps.
- If vendor results exist and look meaningfully relevant, that is usually sufficient coverage.

Return JSON ONLY:
{{
  "should_log_gap": true,
  "gap_type": "missing_vendors|weak_vendor_match|sufficient_coverage|search_quality_issue|needs_review",
  "canonical_need": "short canonical description of the unmet vendor need",
  "vendor_query": "best query for discovering vendors",
  "geo_hint": "location if materially relevant, else null",
  "summary": "1-2 sentence explanation of the opportunity",
  "rationale": "brief explanation of why this is or is not a real vendor coverage gap",
  "suggested_vendor_search_queries": ["query 1", "query 2", "query 3"],
  "confidence": 0.0
}}"""

    try:
        text = await call_gemini(prompt, timeout=20.0)
        parsed = _extract_json(text)
        if isinstance(parsed.get("suggested_vendor_search_queries"), list):
            parsed["suggested_vendor_search_queries"] = [
                str(q).strip() for q in parsed["suggested_vendor_search_queries"] if str(q).strip()
            ][:5]
        return VendorCoverageAssessment(**parsed)
    except Exception as e:
        logger.warning(f"[VendorCoverage] Assessment failed: {e}")
        return None


async def triage_provider_query(
    display_query: str,
    row_title: Optional[str] = None,
    project_title: Optional[str] = None,
    choice_answers_json: Optional[str] = None,
    request_spec_constraints_json: Optional[str] = None,
) -> str:
    """
    Generate an optimized search query for shopping providers.
    Ported from BFF's triageProviderQuery() in llm.ts.
    """
    if not _get_gemini_api_key():
        return _heuristic_provider_query(display_query or row_title or "")

    prompt = f"""You are generating a concise search query to send to shopping providers (Amazon/Google Shopping/eBay).

Input:
- Display query (what user sees): {json.dumps(display_query or '')}
- Row title: {json.dumps(row_title or '')}
- Project title: {json.dumps(project_title or '')}
- choice_answers JSON (may include min_price/max_price): {json.dumps(choice_answers_json or '')}
- request_spec.constraints JSON: {json.dumps(request_spec_constraints_json or '')}

Goal:
- Output a provider_query that maximizes product relevance.
- Do NOT include price phrases like "$50 and up", "over $50", "under $50", "50+", "or more" in provider_query.
- Keep it short (2-6 words), only the core product/category.
- If the project title helps disambiguate meaning, use it ONLY as context to choose the right meaning; do not include project title in provider_query.

Return JSON ONLY:
{{"provider_query":"..."}}"""

    try:
        text = await call_gemini(prompt, timeout=15.0)
        parsed = _extract_json(text)
        q = parsed.get("provider_query", "").strip()
        return q or _heuristic_provider_query(display_query or row_title or "")
    except Exception:
        return _heuristic_provider_query(display_query or row_title or "")
