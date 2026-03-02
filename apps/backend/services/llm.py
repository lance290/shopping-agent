"""
LLM service — unified decision engine, choice factor generation, provider query triage.

Ported from apps/bff/src/llm.ts as part of PRD-02 (Kill BFF).
Uses httpx to call the Gemini REST API directly.
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")  # Direct Gemini REST API fallback
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-3-flash-preview")  # Primary LLM path


def _get_gemini_api_key() -> str:
    return os.getenv("GOOGLE_GENERATIVE_AI_API_KEY") or os.getenv("GEMINI_API_KEY") or ""


def _get_openrouter_api_key() -> str:
    return os.getenv("OPENROUTER_API_KEY") or ""


async def _call_gemini_direct(prompt: str, timeout: float = 30.0) -> str:
    """Call Gemini REST API directly."""
    api_key = _get_gemini_api_key()
    if not api_key:
        raise ValueError("No Gemini API key")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 4096,
        },
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            params={"key": api_key},
            json=payload,
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()

    candidates = data.get("candidates", [])
    if not candidates:
        raise ValueError("Gemini returned no candidates")
    parts = candidates[0].get("content", {}).get("parts", [])
    if not parts:
        raise ValueError("Gemini returned no content parts")
    return parts[0].get("text", "")


async def _call_openrouter(prompt: str, timeout: float = 30.0) -> str:
    """Call OpenRouter API (OpenAI-compatible)."""
    api_key = _get_openrouter_api_key()
    if not api_key:
        raise ValueError("No OpenRouter API key (OPENROUTER_API_KEY)")

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 4096,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()

    choices = data.get("choices", [])
    if not choices:
        raise ValueError("OpenRouter returned no choices")
    return choices[0].get("message", {}).get("content", "")


async def call_gemini(prompt: str, timeout: float = 30.0) -> str:
    """Call LLM: try OpenRouter first (gemini-3-flash-preview), fall back to Gemini direct."""
    # Primary: OpenRouter (supports gemini-3-flash-preview)
    if _get_openrouter_api_key():
        try:
            return await _call_openrouter(prompt, timeout)
        except Exception as e:
            logger.warning(f"OpenRouter failed, trying Gemini direct: {e}")

    # Fallback: Gemini direct API
    if _get_gemini_api_key():
        try:
            return await _call_gemini_direct(prompt, timeout)
        except Exception as e:
            logger.error(f"Gemini direct also failed: {e}")
            raise

    raise ValueError("No LLM API key configured (OPENROUTER_API_KEY, GEMINI_API_KEY, or GOOGLE_GENERATIVE_AI_API_KEY)")


def _extract_json(text: str) -> dict:
    """Extract JSON object from LLM response, handling markdown fences and prose."""
    cleaned = re.sub(r"```(?:json)?\s*\n?", "", text)
    cleaned = re.sub(r"\n?```", "", cleaned)
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        cleaned = cleaned[first_brace : last_brace + 1]
    return json.loads(cleaned)


def _extract_json_array(text: str) -> list:
    """Extract JSON array from LLM response."""
    cleaned = re.sub(r"```(?:json)?\s*\n?", "", text)
    cleaned = re.sub(r"\n?```", "", cleaned)
    first_bracket = cleaned.find("[")
    last_bracket = cleaned.rfind("]")
    if first_bracket != -1 and last_bracket > first_bracket:
        cleaned = cleaned[first_bracket : last_bracket + 1]
    return json.loads(cleaned)


# =============================================================================
# DATA MODELS
# =============================================================================

# Valid desire tiers — drives downstream routing
DESIRE_TIERS = ("commodity", "considered", "service", "bespoke", "high_value", "advisory")


class UserIntent(BaseModel):
    what: str
    category: str = "request"
    service_type: Optional[str] = None  # vendor_category hint (e.g. "private_aviation")
    search_query: Optional[str] = None
    constraints: Dict[str, Any] = {}
    desire_tier: str = "commodity"  # one of DESIRE_TIERS
    desire_confidence: float = 0.8  # 0.0-1.0


class ClarificationAction(BaseModel):
    type: str = "ask_clarification"
    missing_fields: List[str] = []


class DisambiguateOption(BaseModel):
    label: str
    search_query: str
    category: str


class DisambiguateAction(BaseModel):
    type: str = "disambiguate"
    options: List[DisambiguateOption] = []


class SimpleAction(BaseModel):
    type: str  # create_row, update_row, context_switch, search, vendor_outreach


class UnifiedDecision(BaseModel):
    message: str
    intent: UserIntent
    action: Dict[str, Any]  # flexible to handle all action types
    items: Optional[List[Dict[str, str]]] = None  # multi-item responses
    project_title: Optional[str] = None  # Name for a group of items
    ui_hint: Optional[Dict[str, Any]] = None  # SDUI layout hint from LLM

    @property
    def desire_tier(self) -> str:
        return self.intent.desire_tier if self.intent.desire_tier in DESIRE_TIERS else "commodity"

    @property
    def skip_web_search(self) -> bool:
        """Service/bespoke/high-value/advisory tiers skip web search — it can't help."""
        return self.desire_tier in ("service", "bespoke", "high_value", "advisory")


class ChatContext(BaseModel):
    user_message: str
    conversation_history: List[Dict[str, str]]
    active_row: Optional[Dict[str, Any]] = None
    active_project: Optional[Dict[str, Any]] = None
    pending_clarification: Optional[Dict[str, Any]] = None


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
    "constraints": {{ structured data ONLY: origin, destination, date, size, color, price, recipient, etc. NEVER include 'what', 'is_service', 'service_category', 'search_query', or 'title' in constraints — those belong in the parent intent fields. }},
    "desire_tier": "one of: commodity, considered, service, bespoke, high_value, advisory",
    "desire_confidence": 0.0-1.0
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
- Use ask_clarification to gather essential details first
- Essential details by type:
  - Private jets: origin, destination, date, passengers, passenger_names
  - Catering: date, location, headcount
  - Photography: date, location, event type
  - Custom jewelry: recipient, budget, carat weight, style preferences
- Then create_row with full intent

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
  "intent": {{ "what": "...", "category": "...", "service_type": "...", "search_query": "...", "constraints": {{...}}, "desire_tier": "commodity|considered|service|bespoke|high_value|advisory", "desire_confidence": 0.9 }},
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


async def make_pop_decision(ctx: ChatContext) -> UnifiedDecision:
    """
    Pop-specific decision engine for grocery list management.
    Much simpler than the main Shopping Agent — focused on quick adds,
    minimal questions, and grocery-aware behavior.
    """
    active_row_json = json.dumps({
        "id": ctx.active_row["id"],
        "title": ctx.active_row.get("title", ""),
        "constraints": ctx.active_row.get("constraints", {}),
    }) if ctx.active_row else "none"

    active_project_json = json.dumps({
        "id": ctx.active_project["id"],
        "title": ctx.active_project.get("title", ""),
    }) if ctx.active_project else "none"

    recent = ctx.conversation_history[-6:] if ctx.conversation_history else []
    recent_text = "\n".join(f"  {m['role']}: {m['content']}" for m in recent)

    prompt = f"""You are Pop, a fast and friendly grocery savings assistant. Your job is to help users build their grocery shopping list and find the best deals.

INPUTS:
- User message: "{ctx.user_message}"
- Active list item (the one the user is currently talking about or just added): {active_row_json}
- Shopping list: {active_project_json}
- Recent conversation:
{recent_text}

YOUR PERSONALITY:
- Friendly, casual, efficient — like a helpful friend at the grocery store
- FAST: add items immediately, don't interrogate the user
- Brief responses: 1-2 sentences max

GOLDEN RULES:
1. **ADD FIRST, ASK LATER.** When a user says "steak" — add "Steak" to the list and search for deals. Do NOT ask what cut, grade, or brand. The user will specify if they care.
2. **NEVER ask more than 1 question per turn.** And only ask if truly ambiguous.
3. **Stay in grocery land.** You help with groceries, household items, and everyday store purchases.
4. **Quantity is implicit.** "eggs" means a carton. Don't ask unless the user specifies a weird amount.
5. **Simple item names.** Use normal grocery names: "Steak", "Eggs", "Milk".
6. **SPLIT MULTIPLE ITEMS.** If user says "milk, eggs, and bread" — return ALL items in the "items" array.
7. **BE SMART ABOUT MODIFICATIONS.** Read the recent conversation. If the user says "no, remove that" or "I meant Roquefort cheese", understand the *spirit* of their request:
   - If they want to CHANGE the active item entirely: use "update_row" with the new name.
   - If they want to DELETE the active item: use "delete_row".
   - If they are clarifying details of the active item (e.g. "organic"): use "update_row" with new constraints.

HANDLING USER MESSAGES:
- "hi" / "hello" / "hey" → GREET BACK. Message: "Hey! What do you need from the store today?" Action: "ask_clarification".
- "thanks" / "ok" → Acknowledge briefly. Action: "ask_clarification".
- "steak" → Add "Steak". Action: "create_row".
- "ice cream, cookies, and wine" → THREE separate items in "items" array. Action: "create_row".
- "prime, fresh" → User is adding details to the active item. Action: "update_row".
- "actually make it ground beef instead" → User is replacing the active item. Action: "update_row" with "what" = "Ground Beef".
- "remove steak" / "delete that" / "nevermind" → Remove the active item. Action: "delete_row".
- "laptop" → Decline politely. Action: "ask_clarification".

ACTION TYPES:
1. "create_row" — Add new item(s) to the grocery list
2. "update_row" — Update the ACTIVE item (change its name, add preferences, etc.)
3. "delete_row" — Remove the ACTIVE item from the list
4. "context_switch" — User mentions a new grocery item while one is active, and they DON'T want to modify the active one.
5. "ask_clarification" — RARELY used. Only for chitchat, non-grocery requests, or true ambiguity.
6. "search" — Re-search for deals on current item

Return ONLY valid JSON. 

For MULTIPLE new items (create_row / context_switch), use the "items" array AND provide a default fallback intent:
{{
  "message": "Brief friendly response",
  "items": [
    {{ "what": "Ice Cream", "search_query": "ice cream grocery deals" }},
    {{ "what": "Cookies", "search_query": "cookies grocery deals" }}
  ],
  "intent": {{
    "what": "Multiple items",
    "category": "product",
    "search_query": "grocery deals",
    "constraints": {{}},
    "desire_tier": "commodity",
    "desire_confidence": 0.95
  }},
  "action": {{ "type": "create_row" }}
}}

For a SINGLE item (create_row, update_row, delete_row, etc.), you MUST provide the "intent" block containing the item details:
{{
  "message": "Brief friendly response",
  "intent": {{
    "what": "Simple grocery item name",
    "category": "product",
    "service_type": null,
    "search_query": "grocery search query for deals",
    "constraints": {{}},
    "desire_tier": "commodity",
    "desire_confidence": 0.95
  }},
  "action": {{ "type": "update_row" }}
}}"""

    try:
        text = await call_gemini(prompt, timeout=20.0)
        parsed = _extract_json(text)

        # Handle multi-item responses: LLM returns "items" array instead of "intent"
        items_list = parsed.pop("items", None)
        if items_list and isinstance(items_list, list) and len(items_list) > 0:
            first = items_list[0]
            if "intent" not in parsed:
                parsed["intent"] = {
                    "what": first.get("what", ""),
                    "category": "product",
                    "search_query": first.get("search_query", f"{first.get('what', '')} grocery deals"),
                    "constraints": {},
                    "desire_tier": "commodity",
                    "desire_confidence": 0.95,
                }
            decision = UnifiedDecision(**parsed)
            decision.items = items_list
            return decision

        return UnifiedDecision(**parsed)
    except Exception as e:
        logger.error(f"[Pop] Failed to parse LLM decision: {e}")
        # Don't blindly add non-grocery messages as items
        return UnifiedDecision(
            message="Hey! What do you need from the store today?",
            intent=UserIntent(
                what="",
                category="product",
                search_query="",
                constraints={},
                desire_tier="commodity",
                desire_confidence=0.0,
            ),
            action={"type": "ask_clarification"},
        )


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
    Returns {"subject": ..., "body": ...}.
    """
    prompt = f"""Write a brief, professional outreach email from {sender_name} to {vendor_company}
about a customer looking for: {row_title}.

Return JSON ONLY: {{"subject": "...", "body": "..."}}"""

    try:
        text = await call_gemini(prompt, timeout=15.0)
        parsed = _extract_json(text)
        return {
            "subject": parsed.get("subject", f"Inquiry about {row_title}"),
            "body": parsed.get("body", f"Hi {vendor_company}, we have a customer interested in {row_title}."),
        }
    except Exception:
        return {
            "subject": f"Inquiry about {row_title}",
            "body": f"Hi {vendor_company},\n\nWe have a customer interested in {row_title}. Would you be able to provide a quote?\n\nBest,\n{sender_name}",
        }


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
