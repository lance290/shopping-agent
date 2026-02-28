"""
FastAPI Application - Shopping Agent Backend
Production-ready with modular routes
"""
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from security.headers import SecurityHeadersMiddleware
from security.csrf import CSRFProtectionMiddleware, set_csrf_secret
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import os
import traceback
from pathlib import Path
from dotenv import load_dotenv

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy import text

from database import init_db, get_session
from sourcing import SourcingRepository, SearchResult
from audit import audit_log

# Import routers
from routes.auth import router as auth_router
from routes.rows import router as rows_router
from routes.bids import router as bids_router
from routes.projects import router as projects_router
from routes.likes import router as likes_router
from routes.comments import router as comments_router
from routes.bugs import router as bugs_router
from routes.webhooks import router as webhooks_router
from routes.clickout import router as clickout_router
from routes.admin import router as admin_router
from routes.shares import router as shares_router
from routes.outreach import router as outreach_router
from routes.quotes import router as quotes_router
from routes.merchants import router as merchants_router
from routes.checkout import router as checkout_router
from routes.seller import router as seller_router
from routes.notifications import router as notifications_router
from routes.stripe_connect import router as stripe_connect_router
from routes.chat import router as chat_router
from routes.search_enriched import router as search_enriched_router
from routes.outreach_campaigns import router as outreach_campaigns_router
from routes.public_search import router as public_search_router
from routes.public_vendors import router as public_vendors_router
from routes.deals import router as deals_router
from routes.pop import router as pop_router

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env", override=False)

# Create FastAPI app
app = FastAPI(
    title="Shopping Agent Backend",
    description="Agent-facilitated competitive bidding backend",
    version="0.1.0"
)

# Configure CORS
_default_origins = [
    "http://localhost:3003",
    "http://127.0.0.1:3003",
]
_extra = os.getenv("CORS_ORIGINS", "")
if _extra:
    _default_origins.extend([o.strip() for o in _extra.split(",") if o.strip()])
# Always allow the Railway frontend if we're on Railway
_railway_frontend = os.getenv("RAILWAY_FRONTEND_URL", "")
if _railway_frontend and _railway_frontend not in _default_origins:
    _default_origins.append(_railway_frontend)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_default_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add security headers middleware (CSP with nonce-based protection)
app.add_middleware(SecurityHeadersMiddleware)

# Enable CSRF protection in ALL environments
_csrf_secret = os.getenv("CSRF_SECRET_KEY")
if _csrf_secret:
    set_csrf_secret(_csrf_secret)
else:
    import logging
    logging.warning(
        "CSRF_SECRET_KEY not set — CSRF protection will be inactive. "
        "Generate one with: openssl rand -hex 32"
    )
    # Don't crash — the middleware gracefully skips validation when no secret is set.
    # Set CSRF_SECRET_KEY in production for full protection: openssl rand -hex 32

# Always register middleware; it skips validation when no secret is configured
app.add_middleware(CSRFProtectionMiddleware)

# Ensure uploads directory exists
env_upload_dir = os.getenv("UPLOAD_DIR")
candidate_paths = [
    env_upload_dir,
    "/data/uploads/bugs" if os.path.exists("/data") and os.access("/data", os.W_OK) else None,
    "uploads/bugs",
    "/tmp/uploads/bugs",
]

UPLOAD_DIR: Optional[Path] = None
for p in candidate_paths:
    if not p:
        continue
    try:
        candidate = Path(p)
        candidate.mkdir(parents=True, exist_ok=True)
        UPLOAD_DIR = candidate
        break
    except Exception:
        continue

if UPLOAD_DIR is None:
    raise RuntimeError("No writable upload directory found")

UPLOAD_ROOT = UPLOAD_DIR.parent
try:
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
except Exception:
    UPLOAD_DIR = Path("/tmp/uploads/bugs")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_ROOT = UPLOAD_DIR.parent
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_ROOT)), name="uploads")

# Include routers
app.include_router(auth_router)
app.include_router(rows_router)
app.include_router(bids_router)
app.include_router(projects_router)
app.include_router(likes_router)
app.include_router(comments_router)
app.include_router(bugs_router)
app.include_router(webhooks_router)
app.include_router(clickout_router)
app.include_router(admin_router)
app.include_router(shares_router)
app.include_router(outreach_router)
app.include_router(quotes_router)
app.include_router(merchants_router)
app.include_router(checkout_router)
app.include_router(seller_router)
app.include_router(notifications_router)
app.include_router(stripe_connect_router)
app.include_router(chat_router)
app.include_router(search_enriched_router)
app.include_router(outreach_campaigns_router)
app.include_router(public_search_router)
app.include_router(public_vendors_router)
app.include_router(deals_router)
app.include_router(pop_router)

# Lazy init sourcing repository
_sourcing_repo = None

def get_sourcing_repo():
    global _sourcing_repo
    if _sourcing_repo is None:
        _sourcing_repo = SourcingRepository()
    return _sourcing_repo


class HealthResponse(BaseModel):
    status: str
    version: str


class SearchRequest(BaseModel):
    query: str
    gl: Optional[str] = "us"
    hl: Optional[str] = "en"
    providers: Optional[List[str]] = None


class SearchResponse(BaseModel):
    results: List[SearchResult]


@app.get("/health", response_model=HealthResponse)
async def health_check():
    return {
        "status": "healthy",
        "version": "0.1.0"
    }


@app.get("/health/ready")
async def readiness_check(session: AsyncSession = Depends(get_session)):
    """
    Readiness check - verifies all dependencies are available.
    """
    checks = {}
    
    try:
        await session.exec(select(1))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)[:100]}"
    
    all_ok = all(v == "ok" for v in checks.values())
    
    return JSONResponse(
        status_code=200 if all_ok else 503,
        content={
            "status": "ready" if all_ok else "degraded",
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


@app.post("/v1/sourcing/search", response_model=SearchResponse)
async def search_listings(request: SearchRequest):
    results = await get_sourcing_repo().search_all(
        request.query,
        gl=request.gl,
        hl=request.hl,
        providers=request.providers,
    )
    return {"results": results}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled errors.
    """
    error_id = f"ERR-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{id(exc)}"
    
    print(f"[ERROR {error_id}] Unhandled exception:")
    traceback.print_exc()
    
    try:
        async with get_session() as session:
            await audit_log(
                session=session,
                action="error.unhandled",
                details={
                    "error_id": error_id,
                    "error_type": type(exc).__name__,
                    "path": str(request.url.path),
                    "method": request.method,
                },
                success=False,
                error_message=str(exc)[:500],
                request=request,
            )
    except Exception as audit_err:
        print(f"[AUDIT] Failed to log error: {audit_err}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "error_id": error_id,
            "message": "An unexpected error occurred. Please try again.",
        }
    )


@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    print("FastAPI application starting...")
    print(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    print(f"E2E_TEST_MODE: {os.getenv('E2E_TEST_MODE')}")
    
    is_production = os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("ENVIRONMENT") == "production"
    if not is_production:
        await init_db()

    # Always run lightweight migrations for new columns
    from database import engine
    try:
        async with engine.begin() as conn:
            # Add chat_history column if it doesn't exist (safe idempotent migration)
            await conn.execute(text("""
                ALTER TABLE row ADD COLUMN IF NOT EXISTS chat_history TEXT;
            """))
            await conn.execute(text("""
                ALTER TABLE row ADD COLUMN IF NOT EXISTS selected_providers TEXT;
            """))
            await conn.execute(text("""
                ALTER TABLE "user" ADD COLUMN IF NOT EXISTS name TEXT;
            """))
            await conn.execute(text("""
                ALTER TABLE "user" ADD COLUMN IF NOT EXISTS company TEXT;
            """))
            # DealHandoff Phase 1+3 columns
            for col, dtype in [
                ("bid_id", "INTEGER"),
                ("vendor_id", "INTEGER"),
                ("vendor_email", "VARCHAR"),
                ("vendor_name", "VARCHAR"),
                ("acceptance_token", "VARCHAR"),
                ("buyer_accepted_at", "TIMESTAMP"),
                ("buyer_accepted_ip", "VARCHAR"),
                ("vendor_accepted_at", "TIMESTAMP"),
                ("vendor_accepted_ip", "VARCHAR"),
            ]:
                await conn.execute(text(f"""
                    ALTER TABLE deal_handoff ADD COLUMN IF NOT EXISTS {col} {dtype};
                """))
            # Vendor description and pg_trgm indices
            await conn.execute(text("""
                ALTER TABLE bid ADD COLUMN IF NOT EXISTS provenance TEXT;
            """))
            # Vendor SEO / Programmatic SEO columns
            await conn.execute(text("""
                ALTER TABLE vendor ADD COLUMN IF NOT EXISTS slug VARCHAR;
            """))
            await conn.execute(text("""
                ALTER TABLE vendor ADD COLUMN IF NOT EXISTS seo_content JSONB;
            """))
            await conn.execute(text("""
                ALTER TABLE vendor ADD COLUMN IF NOT EXISTS schema_markup JSONB;
            """))
            await conn.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS vendor_slug_idx ON vendor (slug);
            """))
            # pg_trgm for fuzzy text search
            await conn.execute(text("""
                CREATE EXTENSION IF NOT EXISTS pg_trgm;
            """))
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS vendor_name_trgm_idx ON vendor USING gin (name gin_trgm_ops);
            """))
            # Deal Pipeline tables (proxy messaging + escrow)
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS deal (
                    id SERIAL PRIMARY KEY,
                    row_id INTEGER NOT NULL REFERENCES row(id),
                    bid_id INTEGER REFERENCES bid(id),
                    vendor_id INTEGER REFERENCES vendor(id),
                    buyer_user_id INTEGER NOT NULL REFERENCES "user"(id),
                    status VARCHAR NOT NULL DEFAULT 'negotiating',
                    proxy_email_alias VARCHAR UNIQUE NOT NULL,
                    vendor_quoted_price FLOAT,
                    platform_fee_pct FLOAT NOT NULL DEFAULT 0.01,
                    platform_fee_amount FLOAT,
                    buyer_total FLOAT,
                    currency VARCHAR NOT NULL DEFAULT 'USD',
                    stripe_payment_intent_id VARCHAR,
                    stripe_transfer_id VARCHAR,
                    stripe_connect_account_id VARCHAR,
                    agreed_terms_summary TEXT,
                    fulfillment_notes TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP,
                    terms_agreed_at TIMESTAMP,
                    funded_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    canceled_at TIMESTAMP
                );
            """))
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS deal_row_id_idx ON deal (row_id);
            """))
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS deal_status_idx ON deal (status);
            """))
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS deal_proxy_alias_idx ON deal (proxy_email_alias);
            """))
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS deal_message (
                    id SERIAL PRIMARY KEY,
                    deal_id INTEGER NOT NULL REFERENCES deal(id),
                    sender_type VARCHAR NOT NULL,
                    sender_email VARCHAR,
                    subject VARCHAR,
                    content_text TEXT NOT NULL,
                    content_html TEXT,
                    attachments JSONB,
                    resend_message_id VARCHAR,
                    ai_classification VARCHAR,
                    ai_confidence FLOAT,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW()
                );
            """))
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS deal_message_deal_id_idx ON deal_message (deal_id);
            """))
            # Seed test vendor for deal pipeline smoke test (idempotent)
            await conn.execute(text("""
                INSERT INTO vendor (name, email, domain, website, category, description, specialties, status, is_verified, tier_affinity, created_at)
                SELECT 'Peak Aviation Solutions', 'lance@xcor-cto.com', 'flypeak.com', 'https://flypeak.com',
                       'Private Aviation', 'Private jet charter and aviation solutions provider',
                       'jet charter, private aviation, on-demand flights, aircraft management',
                       'unverified', false, 'ultra_high_end', NOW()
                WHERE NOT EXISTS (SELECT 1 FROM vendor WHERE domain = 'flypeak.com')
            """))
            # Pop family sharing tables
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS project_member (
                    id SERIAL PRIMARY KEY,
                    project_id INTEGER NOT NULL REFERENCES project(id),
                    user_id INTEGER NOT NULL REFERENCES "user"(id),
                    role VARCHAR NOT NULL DEFAULT 'member',
                    channel VARCHAR NOT NULL DEFAULT 'email',
                    invited_by INTEGER REFERENCES "user"(id),
                    joined_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    UNIQUE (project_id, user_id)
                );
            """))
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS project_invite (
                    id VARCHAR PRIMARY KEY,
                    project_id INTEGER NOT NULL REFERENCES project(id),
                    invited_by INTEGER NOT NULL REFERENCES "user"(id),
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    expires_at TIMESTAMP
                );
            """))
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS project_invite_project_id_idx ON project_invite (project_id);
            """))
            print("Migration check: row + user + deal_handoff + vendor SEO + deal pipeline + pop sharing tables ensured")
    except Exception as e:
        print(f"Migration check skipped (table may not exist yet, Alembic will create it): {e}")

    # ── Data integrity check — warn if vendor/user data is missing ──
    async with engine.begin() as conn:
        try:
            vendor_exists = (
                await conn.execute(
                    text(
                        "SELECT EXISTS ("
                        "SELECT 1 FROM information_schema.tables "
                        "WHERE table_schema = 'public' AND table_name = 'vendor'"
                        ")"
                    )
                )
            ).scalar()
            user_exists = (
                await conn.execute(
                    text(
                        "SELECT EXISTS ("
                        "SELECT 1 FROM information_schema.tables "
                        "WHERE table_schema = 'public' AND table_name = 'user'"
                        ")"
                    )
                )
            ).scalar()

            vendor_count = (
                (await conn.execute(text('SELECT COUNT(*) FROM vendor'))).scalar() or 0
            ) if vendor_exists else 0
            user_count = (
                (await conn.execute(text('SELECT COUNT(*) FROM "user"'))).scalar() or 0
            ) if user_exists else 0

            if not vendor_exists:
                print("⚠️  WARNING: vendor table does not exist yet.")
            elif vendor_count == 0:
                print("⚠️  WARNING: vendor table is EMPTY — vendor data may be missing.")
                print("   Run: python scripts/seed_vendors.py to restore vendor records.")
            else:
                print(f"✓  Data check: {vendor_count} vendors, {user_count} users in DB")
        except Exception as e:
            print(f"⚠️  Data integrity check skipped (table may not exist yet): {e}")

    if is_production:
        return


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    print("FastAPI application shutting down...")
