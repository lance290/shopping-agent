# Architecture Discovery - 2026-03-12

## Tech Stack
- **Frontend:** Next.js (App Router), pnpm, TypeScript, Tailwind CSS, Zustand
- **Backend:** Python 3.11+, FastAPI, SQLModel, SQLAlchemy (async), Alembic
- **Database:** PostgreSQL with pgvector (ankane/pgvector:v0.5.1), port 5437
- **Auth:** Phone-based OTP via Twilio, session tokens, AuditLog
- **Search:** LLM tool-calling agent (Gemini), hybrid vector+FTS vendor search
- **External APIs:** Apify, SerpAPI/SearchAPI, Google CSE, Amazon (Rainforest), eBay, Stripe

## Key Existing Models
- `Vendor` — has: name, email, phone, website, contact_name, category, store_geo_location, lat/lng, specialties, description, embedding, is_verified, status, verification_level, reputation_score, tier_affinity, price_range_min/max
- `Bid` — has: combined_score, relevance_score, quality_score, source_tier, is_service_provider, contact_name/email/phone
- `User` — has: is_admin, trust_level, no team_id/org_id
- `AuditLog` — has: user_id, action, resource_type, resource_id, details (JSON)

## Alembic Head
- `s12_vendor_search_vector` (merge head)
- Last sequential: `s18_project_anonymous_session`

## Key Patterns
- Agent search: `sourcing/agent.py` → `sourcing/tool_executor.py` → providers
- 5 tools: search_vendors, search_marketplace, search_web, run_apify_actor, search_apify_store
- SSE streaming: backend yields events → frontend SearchProgressBar + store actions
- Feature flag: `USE_TOOL_CALLING_AGENT=true`

## Constraints
- No Team/Organization model yet
- Vendor DB: ~3,698 vendors, many NULL categories, 0 verified
- Anonymous sessions supported for search; auth required for curation
