# PRD: Programmatic SEO & GEO Vendor Directory

## 1. Overview and Objectives
**Goal:** Leverage our existing database of 3,000+ vendors to capture traditional SEO traffic and Generative Engine Optimization (GEO) traffic (ChatGPT, Perplexity, Claude, etc.).
**Constraint:** Keep LLM costs at absolute zero by utilizing a local Ollama instance (`gpt-oss:120b` with web search capabilities) for automated content enrichment and generation. 
**Outcome:** A fully automated pipeline where onboarding a new vendor triggers a crawl, local LLM synthesis, and automatic generation of a highly structured, SEO-optimized public Next.js page.

## 2. Core Architecture Updates

### 2.1 Local LLM Enrichment Pipeline (Zero-Cost)
- **Current State:** Vendor enrichment (`reseed_and_enrich.py`) uses paid external APIs (Gemini/OpenRouter).
- **New State:** Update the python pipeline to call a local Ollama API (`http://localhost:11434/api/generate` or `/api/chat`).
- **Web Search Integration:** Leverage the Ollama web-search tool to pull recent data, reviews, and missing specs for vendors if the initial scrape is sparse.
- **Prompt Engineering for GEO:** The Ollama prompt must explicitly demand:
  - **Extreme Information Density:** Output structured JSON that maps to HTML lists (`<ul>`), tables (`<table>`), and definition lists (`<dl>`).
  - **No Fluff:** Remove marketing prose. Focus on exact services, pricing models, pros/cons, and distinct features.
  - **Category Mapping:** Dynamically assign the vendor to existing embedding-based categories rather than a hardcoded taxonomy list.

### 2.2 Database Changes (Postgres / SQLModel)
- Ensure the `Vendor` (or `Seller`) model has the following fields to support the pages:
  - `slug`: Unique, URL-friendly identifier (e.g., `netjets-private-aviation`).
  - `seo_content`: JSONB field storing the structured output from Ollama (specs, feature lists, pricing data, FAQs).
  - `schema_markup`: JSONB field containing pre-computed `Organization`, `LocalBusiness`, or `Service` JSON-LD schema.

### 2.3 Frontend Directory (Next.js App Router)
- **`/vendors/[slug]` (Vendor Profile Page):**
  - **Server-Side Rendered (ISR):** Fast loading, cacheable.
  - **UI/UX:** High-density layout. Renders the `seo_content` JSON into data tables, feature bullet points, and comparative matrices.
  - **GEO Meta:** Injects the `schema_markup` into the `<head>` to ensure deterministic scraping by Google and AI bots.
- **`/directory/[category]` (Dynamic Category Pages):**
  - Uses the pgvector cosine similarity groupings to dynamically build category hubs without hardcoding taxonomy.
  - Displays comparison tables comparing the top vendors in that cluster.
- **Sitemap Generation:**
  - Automated `sitemap.xml` generation that paginates through all 3,000+ vendors and dynamic category routes.

## 3. Automation Workflow (The "Crawler Update")
When a new vendor is added to the system (via UI, webhook, or CSV):
1. **Scrape:** Base URL is crawled.
2. **Local AI Analysis:** Text is passed to local Ollama (`gpt-oss:120b`). 
3. **Synthesis & Structuring:** Ollama formats the data into the dense GEO-optimized JSON schema.
4. **Persistence:** Saved to the `Vendor` table.
5. **Publish:** The frontend `/vendors/[slug]` route instantly becomes available. ISR cache is invalidated if the page was previously rendered.

## 4. Requirements & Acceptance Criteria
- [ ] **Zero API Cost:** Enrichment pipeline successfully authenticates and processes via local Ollama without falling back to paid APIs (unless explicitly configured).
- [ ] **GEO-Optimized Output:** The LLM output consistently produces structured data (tables, lists) rather than paragraphs of text.
- [ ] **Idempotent Crawler:** Running the crawler on an existing vendor updates their `seo_content` without destroying existing manual overrides or core data.
- [ ] **SEO Basics:** Every generated page has `<title>`, `<meta name="description">`, canonical tags, and structured JSON-LD schema.
- [ ] **Performance:** Vendor pages score > 90 on Lighthouse for SEO and Performance.

## 5. Implementation Phases
**Phase 1: Pipeline & Ollama Integration**
- Update `reseed_and_enrich.py` (or create a dedicated `seo_enrich.py`).
- Implement the local Ollama HTTP client.
- Tune the prompt for `gpt-oss:120b` to output strict JSON.

**Phase 2: Database Migration**
- Add `slug`, `seo_content`, and `schema_markup` to the database via Alembic (safe `ADD COLUMN IF NOT EXISTS` as per Railway migration rules).

**Phase 3: Frontend Views**
- Build the `app/vendors/[slug]/page.tsx` and `app/directory/[category]/page.tsx` views in Next.js.
- Ensure proper mapping of LLM JSON to React Table/List components.

**Phase 4: Sitemaps & Indexing**
- Create `app/sitemap.ts` to output all vendor URLs.
- Submit to Google Search Console.
