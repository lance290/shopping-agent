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
from routes.contracts import router as contracts_router
from routes.checkout import router as checkout_router
from routes.seller import router as seller_router
from routes.notifications import router as notifications_router
from routes.stripe_connect import router as stripe_connect_router
from routes.signals import router as signals_router
from routes.chat import router as chat_router
from routes.search_enriched import router as search_enriched_router

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
    _is_prod = os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("ENVIRONMENT") == "production"
    if _is_prod:
        raise RuntimeError("CSRF_SECRET_KEY is required in production")

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
app.include_router(contracts_router)
app.include_router(checkout_router)
app.include_router(seller_router)
app.include_router(notifications_router)
app.include_router(stripe_connect_router)
app.include_router(signals_router)
app.include_router(chat_router)
app.include_router(search_enriched_router)

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
    async with engine.begin() as conn:
        # Add chat_history column if it doesn't exist (safe idempotent migration)
        await conn.execute(text("""
            ALTER TABLE row ADD COLUMN IF NOT EXISTS chat_history TEXT;
        """))
        print("Migration check: chat_history column ensured")

    # ── Data integrity check — warn if vendor/user data is missing ──
    async with engine.begin() as conn:
        try:
            seller_count = (await conn.execute(text('SELECT COUNT(*) FROM seller'))).scalar() or 0
            user_count = (await conn.execute(text('SELECT COUNT(*) FROM "user"'))).scalar() or 0
            if seller_count == 0:
                print("⚠️  WARNING: seller table is EMPTY — vendor data may have been wiped!")
                print("   Run: python scripts/seed_vendors.py  to restore early-adopter vendors.")
            else:
                print(f"✓  Data check: {seller_count} sellers, {user_count} users in DB")
        except Exception as e:
            print(f"⚠️  Data integrity check skipped (table may not exist yet): {e}")

    if is_production:
        return


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    print("FastAPI application shutting down...")
