---
allowed-tools: "*"
description: Conversational boot-up workflow to scaffold repo/stack based on user selections
---
allowed-tools: "*"

# Boot-Up Workflow (Full Stack Scaffolding)

> **⚡ TL;DR FOR SENIOR DEVS:**
> Type `/bootup` → Answer questions about:
> 1. **Security first** (compliance, PII, payments)
> 2. **Stack** (frontend, backend, databases, ML/AI)
> 3. **Test harness** (Vitest/Jest/Playwright/pytest/etc.)
> 4. **Auth provider** (Clerk, Auth0, Supabase, etc.)
> → AI scaffolds everything: Docker Compose, migrations, tests, CI/CD, docs
> → Review output → Git init → Done
> 
> **For juniors:** This is an **advanced workflow**. Start with the [Junior Developer Guide](../../docs/GETTING_STARTED_JUNIOR.md) instead. Come back to `/bootup` when you need to create a new project from scratch.

---
allowed-tools: "*"

## What This Workflow Does

Use this workflow to interview the user about their target stack, compliance requirements, and special modules, then automatically scaffold the repo accordingly. The agent carries the knowledge of common CLI generators (Next.js, FastAPI, Go, etc.) so the user never has to type commands manually.

**Best for:** Mid-senior developers setting up new projects  
**Not for:** Day 1 learning - use [GETTING_STARTED_JUNIOR.md](../../docs/GETTING_STARTED_JUNIOR.md) instead


## Step 0: Detect Package Manager & Context
1. List lockfiles in repo root (package-lock.json, pnpm-lock.yaml, yarn.lock, bun.lockb, poetry.lock, requirements.txt, Pipfile, uv.lock, go.mod, Cargo.toml, etc.).
2. If exactly one ecosystem is detected, announce the default selection.
3. If multiples or none detected, ask: "Which package manager should I use for scaffolding?" Provide quick choices (pnpm, npm, yarn, bun, pip/uv/poetry, go, other) plus an "Other" free-form option.
4. Cache selection for later commands.
5. Confirm target directory (default = repo root). If user wants a subdirectory/monorepo layout, capture that now.
6. Ensure bootstrap artifacts can be written even on brand-new repos:
   - If `.cfoi/` is missing, `mkdir -p .cfoi/branches/<branch-name>` before writing any files.
   - If git is not initialized yet, postpone git-only commands until Step 5 (announce that `git init` will happen later).
7. For any running task checklist, create/update `.cfoi/branches/<branch-name>/todo.md` instead of calling external commands.

## Step 1: Security & Compliance First (Critical Questions)
**Ask these BEFORE any stack selection - they influence all technical choices.**

### 1A. Data Sensitivity & Compliance
1. **Will this app handle sensitive user data?**
   - PII (personal identifiable information)
   - Health information (HIPAA)
   - Financial data (PCI DSS)
   - Government data (FedRAMP)
   - Child data (COPPA)

2. **Required certifications?**
   - SOC 2 (Type I or II?)
   - HIPAA (healthcare)
   - PCI DSS (payments)
   - CASA (which tier?)
   - FedRAMP (Low/Moderate/High?)
   - ISO 27001
   - GDPR (EU data)

3. **Data residency requirements?**
   - Must data stay in specific countries?
   - Cross-border data transfer restrictions?

4. **Access control needs?**
   - Role-based access (RBAC)
   - Multi-factor authentication required
   - Audit logging for all access

### 1B. Third-Party Integrations
1. **Payment processing needed?**
   - Stripe (recommended for PCI DSS)
   - Braintree
   - PayPal
   - Square
   - Adyen
   - None

2. **Email access required?**
   - Send-only (transactional)
   - Full mailbox access (OAuth/IMAP)
   - Calendar integration
   - Contact sync
   - None

3. **External API integrations?**
   - Social media OAuth
   - CRM systems
   - Analytics platforms
   - Cloud storage

### 1C. Authentication & User Management

**1. Authentication provider needed?**
- Clerk (recommended - multi-framework, user management UI included)
- Stytch (passwordless-first, magic links, SMS)
- Auth0 (enterprise-grade, SAML/SSO, extensive integrations)
- Supabase Auth (open source, PostgreSQL-backed, row-level security)
- NextAuth/Auth.js (Next.js native, SvelteKit adapter available)
- Lucia Auth (lightweight, SvelteKit-native, full control)
- Custom (roll your own with JWT/sessions)
- None

**2. Authentication methods** (if provider selected):
- Email/password (traditional)
- Magic links (passwordless email)
- OAuth providers (Google, GitHub, Microsoft, etc.)
- SMS/phone authentication
- Passkeys/WebAuthn (biometric)
- SAML/SSO (enterprise single sign-on)

**3. User management features** (if provider selected):
- User profiles and metadata
- Role-based access control (RBAC)
- Multi-factor authentication (MFA)
- Team/organization management
- User invitation flows
- Admin dashboard
- None (basic auth only)

**Anti-recommendations based on frontend choice:**
- **For SvelteKit**: ⚠️ NextAuth requires `@auth/sveltekit` adapter (not as smooth), consider Clerk or Lucia instead
- **For Remix**: ⚠️ NextAuth requires `remix-auth` (different API), consider Clerk or Auth0
- **For Vue**: ❌ NextAuth has no official support, use Clerk, Auth0, or Supabase
- **For compliance (SOC 2/HIPAA)**: ✅ Clerk, Auth0, or Supabase (audit logs built-in)
- **For B2B/multi-tenant**: ✅ Clerk, Stytch, or Auth0 (organization support)

### 1D. Auto-Trigger Security Workflow
If ANY of the following are selected:
- Compliance requirements (SOC 2, HIPAA, PCI DSS, CASA, FedRAMP, etc.)
- Payment processing (Stripe, Braintree, etc.)
- Full email/calendar access (OAuth/IMAP)
- Authentication with MFA or SAML/SSO requirements

Then auto-invoke security workflow:
```
🔒 Security requirements detected. Auto-invoking /security-compliance workflow...
```
Execute `/security-compliance` workflow to capture detailed requirements and generate compliance artifacts.

Store all answers in `.cfoi/branches/<branch>/bootstrap.json` for traceability.

## Step 1B: PRD Analysis & Stack Recommendations (Optional)

**Ask:** "Do you have a PRD, requirements doc, or project description I can analyze to recommend a stack?"

**If yes:**

### 1. Ingest Requirements

**Accept multiple formats:**
- **File path:** User provides path to PRD.md, requirements.txt, project-brief.pdf
- **Paste inline:** User pastes requirements directly
- **URL:** User provides link to requirements doc
- **Verbal description:** User describes project verbally

**Prompt:**
```
Please provide your requirements:
- Paste them here directly
- Provide a file path (e.g., ./docs/PRD.md)
- Provide a URL
- Or describe the project verbally
```

### 2. Analyze Requirements for Stack Signals

**Parse for technical indicators:**

**Scale & Performance Signals:**
- "millions of users", "high traffic", "global scale" → Performance-focused stack
- "real-time", "live updates", "websockets", "chat", "notifications" → WebSocket support
- "low latency", "fast response" → Fastify over NestJS
- "enterprise", "B2B", "large teams" → NestJS for structure

**Data & ML Signals:**
- "analytics", "dashboards", "reports", "BI" → Data-heavy stack
- "recommendations", "predictions", "ML", "AI" → ML capabilities
- "embeddings", "semantic search", "RAG" → Vector database
- "time-series", "metrics", "logs" → Time-series database

**Compliance & Security Signals:**
- "healthcare", "HIPAA", "PHI" → High security, SvelteKit preferred
- "payments", "PCI DSS", "financial" → Stripe integration, security-first
- "government", "FedRAMP", "classified" → Self-hosted, high security
- "GDPR", "EU data", "data residency" → Geographic constraints
- "SOC 2", "audit logs", "compliance" → Audit logging required

**Mobile & Platform Signals:**
- "iOS", "Android", "mobile app" → Mobile frameworks
- "cross-platform", "mobile-first" → React Native, Flutter
- "PWA", "progressive web app" → Next.js or Svelte with PWA

**Architecture Signals:**
- "microservices", "distributed", "event-driven" → Microservices architecture
- "monolith", "simple", "MVP" → Monolithic stack
- "serverless", "lambda", "functions" → Serverless architecture
- "API-only", "headless", "backend-only" → API-only stack

**Mentioned Technologies:**
- Extract explicitly mentioned tech (PostgreSQL, Redis, Next.js, etc.)
- Validate compatibility with other requirements

### 3. Generate Stack Recommendations

**Analyze collected signals and recommend:**

**Example Output:**
```
📋 PRD Analysis Complete

Detected Requirements:
✓ Real-time collaboration features
✓ Healthcare data (HIPAA compliance required)
✓ User authentication with MFA
✓ PostgreSQL database mentioned
✓ REST API with webhooks
✓ Admin dashboard needed
✓ Mobile app planned (phase 2)

🎯 Recommended Stack:

Frontend: svelte ✅ (production template)
├─ Reason: HIPAA compliance easier than Next.js
├─ Security: Server-side rendering, minimal client JS
├─ Performance: Lightweight, fast load times
└─ Alternative: nextjs (if SEO is critical priority)

Backend: nestjs ✅ (production template)
├─ Reason: Structured for healthcare compliance
├─ Features: WebSocket support for real-time
├─ Security: Guards, interceptors for audit logging
└─ Alternative: fastify (if max performance needed)

Databases:
├─ postgres ✅ (explicitly mentioned, HIPAA-compliant)
└─ redis ✅ (recommended: real-time + caching)

Authentication:
└─ Clerk ✅ (MFA built-in, HIPAA BAA available)

Testing:
├─ Vitest (frontend)
└─ Jest (backend) with high coverage for compliance

Observability:
└─ Recommended (audit logging required for HIPAA)

Compliance:
⚠️  HIPAA requirements detected
└─ Will auto-invoke /security-compliance workflow

Mobile (Phase 2):
└─ React Native (recommended for cross-platform)
```

### 4. User Decision Point

**Present recommendations and ask:**
```
Based on your requirements, I recommend:
- Frontend: Svelte (HIPAA-friendly)
- Backend: NestJS (structured, WebSocket support)
- Databases: PostgreSQL + Redis
- Auth: Clerk (MFA + HIPAA BAA)

Options:
1. ✅ Accept recommendations (skip to Step 4: Confirmation)
2. 🔧 Modify recommendations (selective overrides)
3. ❌ Manual selection (continue to Step 2: Stack Interview)

Your choice? [1/2/3]
```

**If Option 1 (Accept):**
- Skip Step 2 & 3 (Stack Interview & Clarifications)
- Pre-populate all selections
- Jump to Step 4 (Final Confirmation)
- User can still review/modify before scaffolding

**If Option 2 (Modify):**
- Show each recommendation with option to change
- "Frontend: Svelte → Change? [y/N]"
- Accept changes, then jump to Step 4

**If Option 3 (Manual):**
- Discard recommendations
- Continue to Step 2 (normal interview flow)
- Recommendations available for reference

### 5. Save Analysis

**Store in `.cfoi/branches/<branch>/bootstrap.json`:**
```json
{
  "prdAnalysis": {
    "source": "file:./docs/PRD.md",
    "analyzedAt": "2025-01-15T10:30:00Z",
    "signals": {
      "scale": ["real-time", "websockets"],
      "compliance": ["HIPAA", "healthcare"],
      "security": ["MFA", "audit-logging"],
      "databases": ["postgres"]
    },
    "recommendations": {
      "frontend": "svelte",
      "backend": "nestjs",
      "databases": ["postgres", "redis"],
      "auth": "clerk"
    },
    "userDecision": "accepted"
  }
}
```

**If no PRD provided:**
- Skip to Step 2 (normal interview flow)
- No analysis saved

## Step 2: Stack Interview (Informed by Security Requirements & PRD)
**Security-aware recommendations based on Step 1 answers.**
**PRD-informed suggestions if analysis was performed.**

### 2A. Frontend (Security-Filtered Options with Production Templates)

**✅ Production-Ready Templates Available (Recommended):**
- **nextjs** - Next.js 15 + App Router + TypeScript (Docker optimized)
- **svelte** - SvelteKit + TypeScript (Docker optimized)

**⚙️ Other Options (Generic Scaffolding):**
- React + Vite
- Vue
- Remix
- Static sites
- Vanilla JS
- React Native, Expo, Flutter

**Security-Aware Recommendations:**
- **High Security (CASA/SOC 2/HIPAA):** ✅ SvelteKit template (recommended), static sites, vanilla JS
- **Standard Security:** ✅ SvelteKit template, ✅ Next.js template, Vue, Remix
- **Lower Security:** ✅ Next.js template (⚠️ warning: "Next.js server components can be challenging for CASA certification due to opaque build process")

**Anti-recommendations based on compliance:**
- For CASA/SOC 2/HIPAA: Strongly recommend SvelteKit template over Next.js
- For FedRAMP: Recommend self-hosted or GCP GovCloud over Vercel/Netlify

**Template Benefits:**
- Multi-stage Dockerfile (optimized for Railway/GCP)
- Health check endpoints built-in
- TypeScript strict mode configured
- Security hardened (non-root user, dumb-init)
- Ready for Pulumi deployment

### 2B. Backend / APIs (Production Templates Available)

**✅ Production-Ready Templates Available (Recommended):**
- **nestjs** - NestJS + validation + TypeScript (Docker optimized)
- **fastify** - Fastify + performance + TypeScript (Docker optimized)
- **nodejs** - Generic Node.js + TypeScript (Docker optimized)

**⚙️ Other Options (Generic Scaffolding):**
- Python (FastAPI/Django/Flask)
- Go (Fiber/Gin)
- Rust (Axum/Actix)
- C++ (CMake-based service)
- Java/Kotlin (Spring)
- .NET
- Serverless functions
- "None", "Other"

**Template Benefits:**
- Multi-stage Dockerfile optimized for production
- Health check endpoints at `/health`
- CORS configured for frontend integration
- Graceful shutdown hooks
- Database connection wiring ready
- TypeScript strict mode configured

**Capture for each:**
- Language-specific package manager if different
- Architecture quirks (monolith vs microservices, serverless preference, GraphQL, gRPC, websocket)

### 2C. Data Stores (allow multi-select)
- Relational: Postgres (recommended for compliance), MySQL, MSSQL, Cockroach, "None"
- NoSQL / caches: MongoDB (⚠️ compliance warning), DynamoDB, Redis, Neo4j, Cassandra
- Vector / AI: Pinecone, Weaviate, Chroma, ObjectGraph
- Legacy/enterprise: Oracle, DB2
- Other: prompt user to specify
- For each enabled store, capture deployment preference (managed cloud vs self-hosted) and migration tooling.

### 2D. ML/AI Capabilities (Detailed Interview)

**1. What type of ML/AI workload?**
- LLM inference (GPT, Llama, Mistral, Claude, etc.)
- Traditional ML (sklearn, XGBoost, PyTorch, TensorFlow)
- Computer vision (object detection, segmentation, classification)
- Embedding generation & vector search (RAG applications)
- ML training pipeline (model training, hyperparameter tuning)
- None

**2. Model Serving Framework** (conditional based on workload):

**For LLM inference:**
- vLLM (recommended - 24x faster, OpenAI-compatible API)
- TGI / Text Generation Inference (HuggingFace official, production-ready)
- Ray Serve (complex multi-model pipelines)
- Ollama (local development and testing)
- ⚠️ **Not recommended:** FastAPI alone (not optimized for ML workloads)

**For traditional ML:**
- BentoML (recommended - production-ready, multi-framework)
- Triton Inference Server (NVIDIA - maximum performance with TensorRT)
- Ray Serve (multi-model serving with auto-scaling)
- FastAPI + custom (⚠️ warning: requires manual optimization for ML workloads)

**3. Model Storage & Versioning:**
- MLflow (recommended - open source, model registry + experiment tracking)
- Weights & Biases (W&B) (enterprise-grade experiment tracking)
- DVC (Data Version Control) (Git-like versioning for data/models)
- Hugging Face Hub (for transformer models, pre-trained model repository)
- None (local storage only - not recommended for production)

**4. GPU Requirements:**

**Cloud GPU (managed):**
- GCP Vertex AI (managed ML platform, T4/V100/A100 GPUs)
- AWS SageMaker (managed ML platform, P3/P4/G5 instances)
- Modal (serverless GPU, pay-per-second, developer-friendly)
- RunPod (cost-effective spot instances, community cloud)

**Self-hosted:**
- Kubernetes + GPU Operator (full control, multi-tenant)
- Docker + NVIDIA Container Runtime (single-node)

**CPU only:**
- Suitable for smaller models, embeddings, inference on quantized models

**5. Vector Database** (for RAG, embeddings, semantic search):
- pgvector (PostgreSQL extension - simplest, integrates with existing Postgres)
- Pinecone (managed, scalable, serverless)
- Qdrant (open source, high performance, Rust-based)
- Weaviate (knowledge graphs, hybrid search)
- Chroma (lightweight, local-first, Python-native)
- Milvus (cloud-native, highly scalable)
- None

**6. Data Processing & Feature Engineering:**
- Ray Data (distributed data processing, ML-focused)
- Feast (feature store, online/offline features)
- Apache Spark (big data processing)
- Pandas/Polars (single-node processing)
- None (simple data pipelines)

**7. ML Monitoring & Observability:**
- Prometheus + Grafana (metrics, dashboards)
- Weights & Biases (experiment tracking, model monitoring)
- MLflow tracking (experiment logging, model comparison)
- LangSmith (LLM tracing, prompt debugging)
- Arize AI (ML observability, drift detection)
- None (basic logging only)

### 2E. Testing Strategy (Context-Aware Test Harness Selection)

**⚠️ Smart Recommendations Based on Stack Selections from Step 2A & 2B**

#### Frontend Testing (based on Step 2A selection):

**If SvelteKit/Svelte selected:**
- **Vitest** (✅ recommended - SvelteKit-native, fast, Vite ecosystem)
- Playwright (E2E)
- Cypress (E2E)
- Node's built-in test runner
- Jest (⚠️ requires extra config for Svelte)
- None

**If Next.js/React selected:**
- **Vitest** (✅ recommended - faster than Jest, better DX)
- **Jest** (established, React Testing Library ecosystem)
- Playwright (E2E)
- Cypress (E2E)
- Node's built-in test runner
- None

**If Vue/Nuxt selected:**
- **Vitest** (✅ recommended - Vue ecosystem standard)
- Playwright (E2E)
- Cypress (E2E)
- Jest (⚠️ requires extra config)
- None

**If Remix selected:**
- **Vitest** (✅ recommended - Remix team uses it)
- Playwright (E2E for Remix apps)
- Jest
- None

**If vanilla JS/static site selected:**
- **Node's built-in test runner** (✅ recommended - zero dependencies)
- Vitest (fast, modern)
- Mocha (classic)
- AVA (minimal)
- None

#### Backend Testing (based on Step 2B selection):

**If Python (FastAPI/Django/Flask) selected:**
- **pytest** (✅ recommended - Python standard, great fixtures)
- unittest (built-in, basic)
- nose2 (older)

**If Node.js backend selected:**
- **Vitest** (✅ recommended - modern, fast)
- Node's built-in test runner (zero dependencies)
- Jest (established)
- Mocha (classic)
- AVA (minimal)

**If Go selected:**
- **go test** (✅ required - built-in standard, no alternatives needed)

**If Rust selected:**
- **cargo test** (✅ required - built-in standard, no alternatives needed)

**If C++ selected:**
- **GoogleTest** (✅ recommended - industry standard, CMake integration)
- Catch2 (modern, header-only)
- Boost.Test (if already using Boost)

**If Java/Kotlin selected:**
- **JUnit 5** (✅ recommended - Java standard)
- TestNG (alternative)

**If .NET selected:**
- **xUnit** (✅ recommended - modern .NET standard)
- NUnit (alternative)
- MSTest (built-in)

#### Additional Testing Tools (ask after primary runner selected):

**Coverage tools:**
- For Node/Vitest: **c8** (✅ recommended - V8 native, accurate)
- For Node/Jest: **istanbul/nyc** (Jest built-in coverage)
- For Python: **pytest-cov** (✅ recommended - pytest plugin)
- For Go: built-in `go test -cover`
- For Rust: built-in `cargo tarpaulin` or `cargo llvm-cov`
- For C++: **lcov** or **gcov**
- None

**E2E testing (if frontend selected):**
- **Playwright** (✅ recommended - modern, reliable, multi-browser)
- Cypress (developer experience, Chrome-focused)
- Puppeteer (Chrome automation)
- None

**API testing (if backend selected):**
- Supertest (Node.js HTTP assertions)
- Hoppscotch CLI (REST/GraphQL testing)
- Postman/Newman (collections)
- None

**Load testing (for production apps):**
- k6 (recommended - modern, scriptable)
- Artillery (Node-based)
- JMeter (Java-based)
- None

**Capture for each workspace:**
- Primary test runner (context-aware recommendation)
- Coverage tool (if desired)
- E2E tool (if frontend exists)
- Test file patterns (e.g., `*.test.ts`, `*_test.go`)
- Smart defaults based on stack choices

### 2F. Observability Stack (Detailed Interview)

**1. What level of observability do you need?**
- **None** - Skip observability setup (can add later with `/observability`)
- **Basic** - Health checks + structured logging only
- **Standard** - Logging + metrics + error tracking (recommended for most)
- **Full** - Logging + metrics + tracing + error tracking + dashboards

**2. Deployment preference:**

| Approach | Best For | Complexity | Cost |
|---
allowed-tools: "*"-------|----------|------------|------|
| **Managed services** | Small teams, fast setup | Low | Pay per usage |
| **Self-hosted** | Data sovereignty, cost control | High | Infrastructure cost |
| **Hybrid** (recommended) | Balance of control + convenience | Medium | Mixed |

**3. Managed Services (if selected):**

| Service | Category | Best For |
|---
allowed-tools: "*"------|----------|----------|
| **Datadog** | Full-stack APM | Enterprise, all-in-one |
| **New Relic** | APM + browser | Performance monitoring |
| **Sentry** | Error tracking | Error tracking (excellent DX) |
| **Honeycomb** | Observability | High-cardinality debugging |
| **Grafana Cloud** | Metrics + logs | Cost-effective, open ecosystem |
| **Better Uptime** | Uptime monitoring | Status pages + alerts |
| **Checkly** | Synthetic monitoring | API + browser checks |

**4. Self-Hosted Components (if selected):**

| Component | Purpose | Alternatives |
|---
allowed-tools: "*"--------|---------|--------------|
| **OpenTelemetry Collector** | Telemetry routing | Fluent Bit, Vector |
| **Prometheus** | Metrics storage | VictoriaMetrics, Mimir |
| **Grafana** | Dashboards | - |
| **Loki** | Log aggregation | Elasticsearch |
| **Jaeger** | Distributed tracing | Tempo, Zipkin |

**5. Instrumentation SDK:**
- **OpenTelemetry** (✅ recommended - vendor-neutral, auto-instrumentation)
- Datadog SDK (if using Datadog)
- New Relic SDK (if using New Relic)
- Custom (roll your own)

**6. What to instrument:**
- [ ] HTTP requests (latency, status codes, routes)
- [ ] Database queries (query time, connection pool)
- [ ] External API calls (third-party latency)
- [ ] Background jobs (queue depth, processing time)
- [ ] Business metrics (signups, purchases, etc.)
- [ ] Custom events

**Recommended Stack by Project Type:**

| Project Type | Recommended Stack |
|---
allowed-tools: "*"-----------|-------------------|
| **MVP / Side project** | Basic: Pino logging + Sentry |
| **Production SaaS** | Standard: OpenTelemetry + Prometheus + Grafana + Sentry |
| **Enterprise / Compliance** | Full: OpenTelemetry + Datadog (or self-hosted full stack) |
| **High-traffic API** | Full: OpenTelemetry + Prometheus + Jaeger + Grafana |

**Store selection in `.cfoi/branches/<branch>/bootstrap.json`:**
```json
{
  "observability": {
    "level": "standard",
    "approach": "hybrid",
    "logging": "pino",
    "metrics": "prometheus",
    "tracing": "jaeger",
    "errors": "sentry",
    "uptime": "betteruptime",
    "sdk": "opentelemetry"
  }
}
```

### 2G. Additional Capabilities (Non-ML)
- Streaming/queue (Kafka, Pub/Sub, RabbitMQ)
- Analytics/BI (Segment, Amplitude, Mixpanel)
- Quantum toolkit (Qiskit, Cirq)
- Custom integrations

### 2H. Agentic Orchestration & Automation

**1. Do you need an AI agent service or low-code automation?**
- **None** – Skip agent/orchestrator setup for now (you can add later).
- **AI Agent Service** – Self-hosted LLM agents exposed over HTTP.
- **Automation / Workflow Orchestrator** – Low-code workflows that call your APIs and agents.

**2. If AI Agent Service is selected, which template?**
- **LangChain / LangGraph / CrewAI template** (recommended for complex workflows)
  - Location: `infra/docker/templates/langchain-agents/`
  - Includes: simple LangChain agent, LangGraph multi-step workflow, CrewAI team-based agent
- **Custom lightweight agent template** (recommended for simple, fast agents)
  - Location: `infra/docker/templates/custom-agent/`
  - Minimal dependencies, ReAct loop, easy to customize

**3. If Automation / Workflow Orchestrator is selected, which tool?**
- **n8n** – General-purpose workflow automation that can call your APIs/agents via webhooks/HTTP.
- **Existing orchestrator** – e.g., Temporal, Airflow, Dagster, or a hosted vendor.
  - Capture name and how it will talk to your services (HTTP/webhooks/queues).

**4. Deployment & integration details (capture):**
- Where the agent/orchestrator will run (Railway, GCP Cloud Run, Kubernetes, other).
- How it discovers your services (internal network vs public URL).
- Any additional data stores (Redis for queues, Postgres for state, vector DBs for RAG).

**5. Persist selection to `.cfoi/branches/<branch>/bootstrap.json`:**
```json
{
  "agents": {
    "service": "langchain-agents",
    "orchestrator": "n8n",
    "deployment": "railway"
  }
}
```

Store all answers in `.cfoi/branches/<branch>/bootstrap.json` for traceability.

## Step 3: Clarifying Questions
1. Review captured selections, highlight missing info (e.g., "You chose FastAPI but didn’t specify pip vs poetry").
2. **Security-specific follow-ups:** If compliance requirements exist, confirm data handling, encryption, and audit logging needs.
3. Confirm infrastructure platforms (Railway, GCP, AWS, Azure, hybrid) and desired CI (GitHub Actions, Cloud Build, etc.).
4. Confirm env naming (dev/staging/prod) and deployment cadence.

## Step 4: Final Confirmation
1. Display a concise summary table:
   - Security/Compliance requirements
   - Frontend(s) (with security recommendations)
   - Backend(s)
   - Databases/cache/vector
   - **Test harnesses** (runner + coverage tool per workspace)
   - Payment/Email integrations
   - Extra capabilities
   - Package managers per workspace
2. **Security review summary:** "Based on your [CASA/SOC 2] requirements, we recommend SvelteKit over Next.js for easier certification."
3. **Test setup confirmation:** "I'll install [Vitest + c8] for frontend testing and [pytest + coverage] for backend. Sound good?"
4. Ask: "Anything else you want included before I scaffold all of this?" Capture additional requests (e.g., CLI tool, extra docs, quantum example).
5. Obtain explicit go-ahead: "Ready for me to run the installers and create files?"

## Step 4B: Generate Pulumi Tech Stack Configuration

**If user selected any of our production templates (nextjs, svelte, nestjs, fastify):**

1. **Determine stack name** from current environment (dev, staging, production)
2. **Check for preset match:**
   ```bash
   # Check if their selections match a preset
   node infra/pulumi/config-tech-stack.js list-presets
   ```

3. **Generate Pulumi config:**

   **If preset match found:**
   ```bash
   node infra/pulumi/config-tech-stack.js generate <preset-name> <stack>
   ```

   **If custom combination:**
   ```bash
   node infra/pulumi/config-tech-stack.js custom <stack> \
     --frontend=<tech> \
     --backend=<tech> \
     [--postgres] \
     [--redis] \
     [--mongodb] \
     [--neo4j]
   ```

4. **Review generated config:**
   ```bash
   node infra/pulumi/config-tech-stack.js get-config <stack>
   ```

5. **Show user the deployment plan:**
   - Display: "✅ Pulumi config generated at `infra/pulumi/Pulumi.<stack>.yaml`"
   - Summary: "This will deploy: [frontend tech] + [backend tech] + [databases]"
   - Note: "You can deploy with `cd infra/pulumi && pulumi up` after scaffolding"

6. **Save config reference** to `.cfoi/branches/<branch>/bootstrap.json`:
   ```json
   {
     "pulumiConfig": {
       "stack": "dev",
       "frontend": "nextjs",
       "backend": "nestjs",
       "databases": ["postgres", "redis"],
       "configFile": "infra/pulumi/Pulumi.dev.yaml"
     }
   }
   ```

## Step 5: Execute Scaffolding
For each selected stack element, run the appropriate generator or template.

**⚠️ CRITICAL: When generating any scripts (dev.sh, seed scripts, etc.), follow patterns in `docs/SCRIPT_GENERATION_GUIDE.md`**

Key patterns to apply:
- Create `logs/`, `data/` directories before redirecting output
- Kill existing processes on ports before starting services
- Include authentication in all database connection commands
- Use dynamic imports for optional third-party services (Clerk, Auth0, etc.)
- Remove `version:` field from docker-compose.yml files
- Validate npm package existence before installation
- Generate companion scripts: `stop.sh`, `status.sh`, `ports.sh`

**CLI safety tips (share with juniors):**
- Run commands directly (never wrap them in `eval` or other shells that can mangle flags/line breaks).
- Always run scaffold commands as a single line (avoid wrapped `--flags` that split across lines).
- Confirm the destination directory exists (use `mkdir -p apps/web` etc.) and is empty before scaffolding.
- If a command prompts for confirmation, surface the exact question and recommended answer.
- If a CLI cannot write to the path, double-check for typos or line breaks before assuming permissions issues.

1. **Directory Layout**
   - Create `apps/`, `packages/`, `infra/`, etc. when a monorepo is requested.
   - Ensure no duplicate directories; confirm before overwriting existing files.

2. **Frontend**
   
   **If user selected production template (nextjs, svelte):**
   ```bash
   # Copy template files
   cp -r infra/docker/templates/<tech>/* apps/frontend/
   
   # Rename package.json.template if it exists
   if [ -f apps/frontend/package.json.template ]; then
     mv apps/frontend/package.json.template apps/frontend/package.json
   fi
   
   # Install dependencies
   cd apps/frontend && npm install
   ```
   
   **Template includes:**
   - ✅ Complete app structure (app/ or src/routes/)
   - ✅ Health check endpoint configured
   - ✅ Dockerfile optimized for production
   - ✅ TypeScript configured
   - ✅ Next.js config with standalone output (if nextjs)
   - ✅ Svelte config with node adapter (if svelte)
   
   **If user selected other frontend (React, Vue, etc.):**
   - Run CLI: e.g., `pnpm create next-app@latest apps/frontend --ts --eslint`.
   - Configure package manager (install deps, set scripts, add `.nvmrc`/`.tool-versions` if needed).
   - Generate Dockerfile & docker-compose service (use generic Node.js template).
   
   **For all frontends:**
   - When adding third-party auth (Clerk, Auth0), use dynamic import pattern from Section 4 of `docs/SCRIPT_GENERATION_GUIDE.md`.
   - Validate package names before installation (Section 7 of guide).

3. **Backend**

   **If user selected production template (nestjs, fastify, nodejs):**
   ```bash
   # Copy template files
   cp -r infra/docker/templates/<tech>/* apps/backend/
   
   # Rename package.json.template if it exists
   if [ -f apps/backend/package.json.template ]; then
     mv apps/backend/package.json.template apps/backend/package.json
   fi
   
   # Install dependencies
   cd apps/backend && npm install
   ```
   
   **Template includes:**
   - ✅ Complete app structure (src/ with main.ts/index.ts)
   - ✅ Health check endpoint at `/health` or `/api/health`
   - ✅ Dockerfile optimized for production
   - ✅ TypeScript strict mode configured
   - ✅ CORS configured for frontend integration
   - ✅ Validation pipes (if NestJS)
   - ✅ Graceful shutdown hooks
   
   **Wire environment variables:**
   - Add database connection strings to `.env.example`
   - Update service to read from environment
   - Follow Section 2 of `docs/SCRIPT_GENERATION_GUIDE.md` for database authentication
   
   **If user selected other backend (Python, Go, Rust, C++):**
   - Run stack-specific scaffolding command (FastAPI template, `django-admin startproject`, `go mod init`, CMake-based skeleton for C++ services, etc.).
   - Wire environment variables, `infra/docker` templates, and service entrypoints.
   - Generate startup scripts following Section 1 of `docs/SCRIPT_GENERATION_GUIDE.md` (directory creation, process cleanup, health checks).
   - Add health check endpoints for CI smoke tests.
   - **For C++/CMake backends specifically:**
     - Ensure a root `CMakeLists.txt` is present (create if missing).
     - Inject `enable_testing()` once (idempotent) if not already present.
     - Create a `tests/` directory with a minimal sample test (e.g., using GoogleTest or Catch2) and corresponding `add_executable(...)`/`add_test(...)` entries.
     - Document in the TECHNICAL README how to run C++ tests locally (e.g., `cmake -S . -B build` then `cd build && ctest`).

4. **Data Stores**
   - Update `docker-compose.dev.yml` & `.prod.yml` with services (follow `docs/SCRIPT_GENERATION_GUIDE.md` for modern compose format).
   - Generate seed scripts with proper authentication (see Section 2 of guide).
   - Generate migration folders (Prisma/Alembic/Flyway/etc.).
   - Append env vars to `.env.example` using `tools/setup-env.sh` schema conventions.

5. **Capabilities**
   - For agents/chatbots (if AI Agent Service selected in Step 2H):
     - Create `apps/agent/` (or `services/agent/`) and copy one of:
       - `infra/docker/templates/langchain-agents/` → full LangChain/LangGraph/CrewAI service.
       - `infra/docker/templates/custom-agent/` → lightweight ReAct-style agent service.
     - Rename `.env.example` to `.env.example.agent` or merge into root `.env.example` using `tools/setup-env.sh` conventions.
     - Add an `agent` service to `infra/docker-compose.dev.yml` and `.prod.yml` with port mapping (e.g., `8081:8080`) and health check.
     - Document how frontend/backend call the agent (HTTP endpoint, auth, timeouts) in `docs/TECHNICAL_README.md`.
   - For automation/workflow orchestrators (if selected in Step 2H):
     - If **n8n** is chosen, add an `n8n` service to `infra/docker-compose.dev.yml` and `.prod.yml` with:
       - Persistent volume for its database (e.g., `n8n_data:/home/node/.n8n`).
       - Environment variables for base URL, auth, and encryption key.
       - Network access to backend and agent services via internal service names.
     - If an existing orchestrator (Temporal, Airflow, Dagster, hosted) is chosen, capture:
       - How it will invoke your APIs/agents (HTTP/webhooks/queues).
       - Any additional infra needed (queues, cron, workers) and reference it in infra docs instead of scaffolding it directly.
   - For ML/quantum: add notebooks/scripts, dependency files, and GPU/quantum provider configs.

6. **Observability Setup** (if selected in Step 2F)

   **Based on observability level selected:**

   **Basic (health + logging):**
   - Add health check endpoints to all services (`/health`, `/health/ready`)
   - Install structured logging library (Pino for Node.js, structlog for Python)
   - Create `src/lib/logger.ts` or equivalent with trace context

   **Standard (+ metrics + errors):**
   - All of Basic, plus:
   - Install OpenTelemetry SDK with auto-instrumentation
   - Install Sentry SDK for error tracking
   - Create `src/instrumentation.ts` for OTel setup
   - Create `src/lib/metrics.ts` with standard counters/histograms
   - Add `/metrics` endpoint for Prometheus scraping
   - Add `.env.example` entries for `SENTRY_DSN`, `OTEL_*`

   **Full (+ tracing + dashboards):**
   - All of Standard, plus:
   - Copy `infra/observability/` templates:
     - `docker-compose.observability.yml`
     - `otel-collector-config.yaml`
     - `prometheus.yml`
     - `grafana/provisioning/` dashboards
   - Create service overview dashboard
   - Configure trace sampling

   **For each service created, add:**
   ```typescript
   // At top of entry point (MUST be first import)
   import './instrumentation';
   ```

   **Install commands by stack:**
   ```bash
   # Node.js
   npm install @opentelemetry/api @opentelemetry/sdk-node \
     @opentelemetry/auto-instrumentations-node \
     @opentelemetry/exporter-prometheus \
     @sentry/node pino

   # Python
   pip install opentelemetry-api opentelemetry-sdk \
     opentelemetry-instrumentation sentry-sdk structlog
   ```

   **Save observability config to:** `.cfoi/branches/<branch>/observability-config.json`

7. **Security/Compliance**
   - Create `docs/compliance/<framework>.md` with checklists and logging requirements.
   - Add secrets placeholders, encryption helpers, audit log middleware stubs.
   - Configure CI steps (SAST, secret scanning) in `.github/workflows/` when required.

8. **Environment & Secrets**
   - Run `tools/setup-env.sh init` (or update) to merge new variables.
   - If user chose cloud secret manager, offer to sync via `tools/setup-env.sh sync-*`.

9. **Infrastructure & CI**
   - Copy/update Pulumi/Railway templates, Cloud Build configs, GitHub Actions PR env.
   - Register new services in `infra/railway/templates` or `infra/pulumi` config.

### 10. Docker Compose Integration (Dev & Prod)
   - **IMPORTANT:** Follow Section 3 of `docs/SCRIPT_GENERATION_GUIDE.md` for modern Docker Compose format (no `version:` field).
   - For each app/service created above, add a service block to both `docker-compose.dev.yml` and `docker-compose.prod.yml` under `infra/`.
   - Mount source directories for dev (`volumes: - ./apps/<service>:/app`) and copy built artifacts or images for prod.
   - Wire environment variables via `${VAR}` references so Compose picks up the `.env` values generated earlier.
   - Declare dependencies between services using `depends_on` (e.g., frontend depends on backend and backend depends on Postgres).
   - Use port override pattern: `"${MONGO_PORT:-27017}:27017"` to allow flexibility.
   - Include authentication in database connection URLs: `mongodb://user:pass@mongo:27017/db?authSource=admin`
   - Expose the appropriate ports (3000 for Next.js, 8080 for APIs, 5432 for Postgres, etc.) and document them in the TECHNICAL README.
   - After updating both files, run `docker compose -f infra/docker-compose.dev.yml up --build` as a smoke test to ensure everything starts locally.

### 11. Versioning Automation (semver)
   - Ensure the repo has a root `package.json` (or workspace package) that can host shared scripts. Create one if the project is purely services without a root manifest.
   - Install the official `semver` package for version bumping: `npm install --save-dev semver` (or `pnpm add -D semver`, `yarn add -D semver`).
   - Add npm scripts that call `semver` to bump versions, e.g.:
     ```json
     {
       "scripts": {
         "version:bump:patch": "node scripts/version-bump.js patch",
         "version:bump:minor": "node scripts/version-bump.js minor",
         "version:bump:major": "node scripts/version-bump.js major"
       }
     }
     ```
   - Create `scripts/version-bump.js` that loads the current version from `package.json`, uses `semver.inc` to bump according to the argument, updates the manifest, and logs the new version. (Keep the script in the repo so CI/CD can reuse it.)
   - Document the release command sequence in the TECHNICAL README (e.g., "Run `npm run version:bump:patch` before tagging").

## Step 5: Git Initialization & Hygiene
1. If repo not initialized, run `git init`, set default branch, add remote if provided.
2. Update `.gitignore` for each language (Python `__pycache__`, Go `bin/`, Rust `target/`, etc.).
3. Stage generated files and create an initial commit message like `chore: bootstrap stack via /bootup` (only after verification/testing).

## Step 6: TECHNICAL README
1. Create `docs/TECHNICAL_README.md` summarizing:
   - Stack selections & rationale
   - Commands to run each service (dev & prod)
   - Environment variable overview
   - Deployment workflow (CI/CD, infra targets)
   - Compliance obligations / security setup
2. Link to any generated docs (compliance checklists, agent configs, etc.).
3. If existing technical doc exists, append new sections instead of overwriting.

## Step 7: Test Harness Installation & Configuration

### 7A. Install Test Runners (Based on Step 2E Selections)

**For each workspace with a test runner selected:**

#### Frontend (Node.js/TypeScript)

**If Vitest:**
```bash
npm install -D vitest @vitest/ui c8
```
Create `vitest.config.ts`:
```typescript
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    coverage: {
      provider: 'c8',
      reporter: ['text', 'json', 'html']
    }
  }
})
```

**If Playwright:**
```bash
npm install -D @playwright/test
npx playwright install
```
Create `playwright.config.ts` with browser matrix.

**If Jest:**
```bash
npm install -D jest @types/jest ts-jest
```
Create `jest.config.js` with TypeScript support.

**If Node built-in:**
No installation needed! Just configure test scripts.

#### Backend Testing

**Python (pytest):**
```bash
pip install pytest pytest-cov pytest-asyncio
# or: uv add --dev pytest pytest-cov
```
Create `pytest.ini`:
```ini
[pytest]
testpaths = tests
python_files = test_*.py *_test.py
addopts = --cov=src --cov-report=html --cov-report=term
```

**Go:**
No installation - uses built-in `go test`.
Create `_test.go` files alongside source.

**Rust:**
No installation - uses built-in `cargo test`.
Create `#[cfg(test)]` modules.

**C++ (GoogleTest):**
```cmake
# In CMakeLists.txt
include(FetchContent)
FetchContent_Declare(
  googletest
  URL https://github.com/google/googletest/archive/release-1.12.1.zip
)
FetchContent_MakeAvailable(googletest)
enable_testing()
```

### 7B. Configure Test Scripts

**Add to package.json** (or workspace manifests):
```json
{
  "scripts": {
    "test": "[test-runner] run",
    "test:watch": "[test-runner] --watch",
    "test:coverage": "[test-runner] run --coverage",
    "test:all": "npm run test:coverage"
  }
}
```

**Examples by runner:**
- Vitest: `"test": "vitest run"`
- Jest: `"test": "jest"`
- Playwright: `"test": "playwright test"`
- Node: `"test": "node --test"`

**Python (pyproject.toml or setup.cfg):**
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--cov --cov-report=html"
```

### 7C. Generate Sample Tests

**For each service created, generate a sample test:**

**Frontend (Vitest example):**
```typescript
// src/components/HelloWorld.test.ts
import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import HelloWorld from './HelloWorld'

describe('HelloWorld', () => {
  it('renders hello message', () => {
    const { getByText } = render(<HelloWorld />)
    expect(getByText('Hello World')).toBeInTheDocument()
  })
})
```

**Backend health endpoint test:**
```python
# tests/test_health.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

**Database connection test:**
```python
# tests/test_db_connection.py
def test_database_connection(db_session):
    """Verify database connection works"""
    result = db_session.execute("SELECT 1")
    assert result.scalar() == 1
```

### 7D. Generate `init.sh` (Session Startup Script) - OPTIONAL

**Ask:** "Do you want an `init.sh` script for automated environment startup?"

**When to use:**
- Fully autonomous agent workflows (no human present)
- Complex multi-service setups that are tedious to start manually
- CI/CD environments that need repeatable startup

**Skip if:**
- Human is present and can run `npm run dev` manually
- Simple single-service projects
- Using Docker Compose directly

**If user wants it**, create `init.sh` at project root:
```bash
#!/bin/bash
# init.sh - Start development environment
# Run this at the start of each coding session

set -e

echo "🚀 Starting development environment..."

# Create required directories
mkdir -p logs data

# Kill any existing processes on our ports
echo "🔪 Cleaning up existing processes..."
lsof -ti:3000 | xargs kill -9 2>/dev/null || true  # Frontend
lsof -ti:8080 | xargs kill -9 2>/dev/null || true  # Backend
lsof -ti:5432 | xargs kill -9 2>/dev/null || true  # Postgres (if local)

# Start infrastructure (databases, etc.)
if [ -f "infra/docker-compose.dev.yml" ]; then
    echo "🐳 Starting Docker services..."
    docker compose -f infra/docker-compose.dev.yml up -d
    sleep 3
fi

# Install dependencies if needed
if [ -f "package.json" ] && [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Start development servers
echo "🖥️  Starting dev servers..."
if [ -f "apps/frontend/package.json" ]; then
    (cd apps/frontend && npm run dev &)
fi
if [ -f "apps/backend/package.json" ]; then
    (cd apps/backend && npm run dev &)
fi
# Fallback for single-app projects
if [ -f "package.json" ] && [ ! -d "apps" ]; then
    npm run dev &
fi

# Wait for services to be ready
echo "⏳ Waiting for services..."
sleep 5

# Basic smoke test
echo "🧪 Running smoke test..."
HEALTH_CHECK=$(curl -s http://localhost:3000/health 2>/dev/null || echo "failed")
if [ "$HEALTH_CHECK" != "failed" ]; then
    echo "✅ Frontend health check passed"
else
    echo "⚠️  Frontend not responding (may still be starting)"
fi

BACKEND_CHECK=$(curl -s http://localhost:8080/health 2>/dev/null || echo "failed")
if [ "$BACKEND_CHECK" != "failed" ]; then
    echo "✅ Backend health check passed"
else
    echo "⚠️  Backend not responding (may still be starting)"
fi

echo ""
echo "🎉 Development environment ready!"
echo ""
echo "Services:"
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:8080"
echo ""
echo "To stop: ./scripts/stop.sh"
```

Make executable: `chmod +x init.sh`

### 7E. Generate Process Management Scripts

**Following Section 5 of `docs/SCRIPT_GENERATION_GUIDE.md`:**

1. `scripts/stop.sh` - Kill all service processes
2. `scripts/status.sh` - Show what's running  
3. `scripts/ports.sh` - List port usage
4. Make all scripts executable: `chmod +x scripts/*.sh`

### 7F. Run Initial Test Suite

**For C++ services specifically:**
```bash
cmake -S . -B build
cd build && ctest --output-on-failure
```
This ensures `CTestTestfile.cmake` exists for pre-push hooks.

**For all other services:**
```bash
# Run tests for each workspace
npm run test:all          # Node.js
pytest                    # Python
go test ./...             # Go
cargo test                # Rust
```

**Then run framework verification:**
```bash
./tools/verify-implementation.sh
```

### 7G. Document Test Commands

**Add to `docs/TECHNICAL_README.md`:**

```markdown
## Testing

### Run All Tests
\`\`\`bash
# Frontend
npm run test:all

# Backend
pytest

# Go services  
go test ./...

# C++ services
cd build && ctest
\`\`\`

### Run Tests with Coverage
\`\`\`bash
npm run test:coverage  # Frontend
pytest --cov           # Backend
\`\`\`

### Run E2E Tests
\`\`\`bash
npm run test:e2e      # Playwright/Cypress
\`\`\`
```

### 7H. Capture Test Results

Store test output in `.cfoi/branches/<branch>/proof/bootstrap/`:
- `tests.md` - Test execution summary
- `coverage-summary.json` - Coverage data
- `test-results/` - Detailed reports

## Step 8: Wrap-Up
1. Present summary of created services, tests, docs, and next steps (e.g., "Run docker-compose up -d").

2. **If production templates were used, provide deployment instructions:**
   ```
   📦 Your stack is ready for deployment!
   
   **Local Development:**
   docker-compose -f infra/docker-compose.dev.yml up --build
   
   **Deploy to Cloud (GCP/Railway):**
   cd infra/pulumi
   pulumi stack select <stack>
   pulumi up
   
   **Your Pulumi config includes:**
   - Frontend: [tech]
   - Backend: [tech]
   - Databases: [list]
   
   **See full deployment guide:**
   - infra/TECH_STACK_SYSTEM.md
   - docs/TECHNICAL_README.md
   ```

3. Remind user where bootstrap artifacts live (`.cfoi/.../bootstrap.json`, TECHNICAL README, compliance docs).

4. **Template-specific next steps:**
   - Templates include health check endpoints at `/health`
   - Dockerfiles are production-optimized (multi-stage builds)
   - TypeScript is configured with strict mode
   - All services wire to databases via environment variables

5. **Architecture Best Practices Recommendations (Stack-Specific)**

   **Generate and display recommendations based on selected stack:**

   **If NestJS backend selected:**
   ```
   🏗️ Recommended Architecture Patterns for NestJS:
   
   1. **Layered Architecture:**
      - Controllers: Handle HTTP requests/responses (routes)
      - Services: Business logic
      - Repositories: Database access layer
      - DTOs: Data validation with class-validator
      - Entities: Database models with TypeORM/Prisma
   
   2. **Example Module Structure:**
      src/modules/users/
      ├── users.module.ts
      ├── users.controller.ts      # Routes & HTTP handling
      ├── users.service.ts         # Business logic
      ├── users.repository.ts      # Database queries
      ├── dto/
      │   ├── create-user.dto.ts   # Input validation
      │   └── update-user.dto.ts
      └── entities/
          └── user.entity.ts       # Database schema
   
   3. **Database Integration (if Postgres selected):**
      - Use TypeORM (NestJS standard) or Prisma (type-safe)
      - Repository pattern for clean data access
      - Migrations for schema versioning
      - Connection pooling for performance
   
   4. **Common Patterns:**
      - Dependency injection via constructor
      - Guards for authentication/authorization
      - Interceptors for logging/transformation
      - Pipes for validation
      - Exception filters for error handling
   
   **Want me to implement any of these?**
   - Add TypeORM module with repository pattern
   - Create example CRUD module (users)
   - Set up authentication guards
   - Add input validation with DTOs
   ```

   **If Fastify backend selected:**
   ```
   🏗️ Recommended Architecture Patterns for Fastify:
   
   1. **Plugin-Based Architecture:**
      - Routes as plugins (auto-loaded)
      - Controllers for request handling
      - Services for business logic
      - Repositories for database access
      - Schemas for request/response validation
   
   2. **Recommended Folder Structure:**
      src/
      ├── index.ts
      ├── routes/
      │   ├── users.routes.ts      # Route definitions
      │   └── posts.routes.ts
      ├── controllers/
      │   ├── users.controller.ts  # Request handlers
      │   └── posts.controller.ts
      ├── services/
      │   ├── users.service.ts     # Business logic
      │   └── posts.service.ts
      ├── repositories/
      │   ├── users.repository.ts  # Database queries
      │   └── posts.repository.ts
      └── schemas/
          ├── users.schema.ts      # JSON Schema validation
          └── posts.schema.ts
   
   3. **Database Integration:**
      - Use Drizzle ORM (lightweight, type-safe) or raw pg client
      - Repository pattern with dependency injection
      - Connection pooling with @fastify/postgres
      - Type-safe queries
   
   4. **Performance Patterns:**
      - Use fastify-plugin for encapsulation
      - @fastify/rate-limit for API protection
      - @fastify/compress for response compression
      - @fastify/caching for performance
   
   **Want me to implement any of these?**
   - Set up route plugins with auto-loading
   - Add database connection pool
   - Create example CRUD endpoints with validation
   - Add authentication with @fastify/jwt
   ```

   **If Next.js frontend selected:**
   ```
   🏗️ Recommended Patterns for Next.js 15:
   
   1. **App Router Best Practices:**
      - Server Components by default (better performance)
      - Client Components only when needed ('use client')
      - Server Actions for mutations (no API routes needed)
      - Route handlers for external API endpoints only
      - Streaming with Suspense boundaries
   
   2. **Recommended Folder Structure:**
      app/
      ├── (auth)/              # Route groups (layout)
      │   ├── login/
      │   └── register/
      ├── (dashboard)/
      │   ├── users/
      │   └── settings/
      ├── api/                 # API routes (if needed)
      │   └── webhooks/
      ├── _components/         # Shared components
      │   ├── ui/              # UI primitives
      │   └── forms/           # Form components
      └── _lib/                # Utilities
          ├── actions/         # Server Actions
          ├── api/             # API client
          └── utils/
   
   3. **State Management Strategy:**
      - Server state: React Query / SWR (recommended)
      - URL state: useSearchParams hook
      - Client state: Zustand (lightweight) or React Context
      - Form state: React Hook Form + Zod validation
   
   4. **Data Fetching Patterns:**
      - Server Components: Direct database queries (if backend)
      - Client Components: React Query hooks
      - Mutations: Server Actions (no API needed)
      - Parallel fetching: Promise.all in Server Components
   
   5. **Performance Optimization:**
      - Use next/image for optimized images
      - Dynamic imports for code splitting
      - Streaming with loading.tsx files
      - Partial Pre-rendering (PPR) for static + dynamic
   
   **Want me to implement any of these?**
   - Set up React Query with API client
   - Add authentication with Clerk
   - Create reusable form components with validation
   - Set up Zustand store for client state
   ```

   **If Svelte frontend selected:**
   ```
   🏗️ Recommended Patterns for SvelteKit:
   
   1. **File-Based Routing:**
      - +page.svelte: Page components
      - +page.server.ts: Server-side logic (SSR)
      - +page.ts: Client-side logic
      - +layout.svelte: Shared layouts
      - +server.ts: API endpoints
   
   2. **Recommended Folder Structure:**
      src/
      ├── routes/
      │   ├── (auth)/
      │   │   ├── login/
      │   │   └── register/
      │   ├── (app)/
      │   │   ├── users/
      │   │   └── settings/
      │   └── api/
      ├── lib/
      │   ├── components/      # Reusable components
      │   ├── stores/          # Svelte stores
      │   ├── actions/         # Form actions
      │   └── utils/
      └── hooks.server.ts      # Request hooks
   
   3. **State Management:**
      - Svelte stores (built-in, reactive)
      - Context API for component trees
      - Form actions for mutations
      - Progressive enhancement by default
   
   4. **Data Loading:**
      - load functions in +page.server.ts (SSR)
      - Form actions for mutations
      - Streaming with await blocks
      - Optimistic UI updates
   
   **Want me to implement any of these?**
   - Set up authentication flow
   - Create reusable form components with validation
   - Add API client with typed endpoints
   - Set up global stores
   ```

   **Save recommendations to:** `docs/ARCHITECTURE_GUIDE.md`

6. **Interactive Offer:**
   ```
   Your [stack name] project is scaffolded with production-ready templates.
   
   The templates are intentionally minimal to give you control.
   I've provided architecture recommendations above.
   
   **Want me to implement any architectural patterns now?**
   Just ask, and I can add:
   - Repository pattern with database integration
   - Authentication setup
   - Example CRUD module
   - State management
   - API client
   - Or anything else from the recommendations
   ```

7. Suggest running `/implement` for the next task, or `/notes` to capture follow-ups.

8. Close with: "Anything else you need before we conclude boot-up?"
