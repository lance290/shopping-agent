"""
FastAPI Application Example
Production-ready template with health checks and CORS
"""
from fastapi import FastAPI, Depends, HTTPException, Header, Request, Query, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Any, Dict
import os
import shutil
import json
import httpx
import traceback
import asyncio
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from sourcing import SourcingRepository, SearchResult, extract_merchant_domain
from database import init_db, get_session
from models import (
    Row, RowBase, RowCreate, RequestSpec,
    AuthLoginCode, AuthSession, Bid, Seller, User, ClickoutEvent,
    BugReport,
    hash_token, generate_verification_code, generate_session_token
)
from affiliate import link_resolver, ClickContext
from audit import audit_log
from clerk_auth import verify_clerk_token, get_clerk_user_id
from github_client import github_client
from diagnostics_utils import validate_and_redact_diagnostics, generate_diagnostics_summary
from notifications import send_internal_notification
import hmac
import hashlib

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env", override=False)

# Create FastAPI app (must be defined before any @app.* decorators)
app = FastAPI(
    title="Shopping Agent Backend",
    description="Agent-facilitated competitive bidding backend",
    version="0.1.0"
)

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "Agent Shopper <shopper@info.xcor-cto.com>")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "dev-webhook-secret")  # Set this in env

def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verify GitHub webhook signature (HMAC SHA-256)."""
    if not signature:
        return False
    # GitHub sends sha256=...
    algo, sig = signature.split('=') if '=' in signature else ('sha256', signature)
    
    mac = hmac.new(WEBHOOK_SECRET.encode(), payload, hashlib.sha256)
    expected_sig = mac.hexdigest()
    return hmac.compare_digest(sig, expected_sig)

class WebhookPayload(BaseModel):
    action: Optional[str] = None
    pull_request: Optional[Dict[str, Any]] = None
    deployment_status: Optional[Dict[str, Any]] = None
    # Add other fields as needed for Railway/GitHub

@app.post("/api/webhooks/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None)
):
    """Handle GitHub webhooks (PR opened, merged)."""
    payload_bytes = await request.body()
    
    # In dev, we might skip signature check if secret is default
    if WEBHOOK_SECRET != "dev-webhook-secret":
        if not verify_webhook_signature(payload_bytes, x_hub_signature_256 or ""):
            raise HTTPException(status_code=401, detail="Invalid signature")
            
    payload = await request.json()
    action = payload.get("action")
    pr = payload.get("pull_request")
    
    print(f"[WEBHOOK] Received GitHub event: {action}")
    
    # Logic for PR opened
    if action == "opened" and pr:
        # Find the bug report this PR links to.
        # We assume the branch name is 'fix/bug-{id}' as per CLAUDE.yml instruction
        branch_name = pr.get("head", {}).get("ref", "")
        if branch_name.startswith("fix/bug-"):
            try:
                bug_id = int(branch_name.split("-")[-1])
                async for session in get_session():
                    bug = await session.get(BugReport, bug_id)
                    if bug:
                        bug.status = "pr_created"
                        bug.github_pr_url = pr.get("html_url")
                        session.add(bug)
                        await session.commit()
                        print(f"[WEBHOOK] Updated bug {bug_id} to pr_created")
            except Exception as e:
                print(f"[WEBHOOK] Failed to link PR to bug: {e}")

    # Logic for PR merged (closed + merged=True)
    if action == "closed" and pr and pr.get("merged"):
        branch_name = pr.get("head", {}).get("ref", "")
        if branch_name.startswith("fix/bug-"):
            try:
                bug_id = int(branch_name.split("-")[-1])
                async for session in get_session():
                    bug = await session.get(BugReport, bug_id)
                    if bug:
                        bug.status = "shipped"
                        session.add(bug)
                        await session.commit()
                        print(f"[WEBHOOK] Updated bug {bug_id} to shipped")
            except Exception as e:
                print(f"[WEBHOOK] Failed to link merged PR to bug: {e}")
    
    return {"status": "received"}

@app.post("/api/webhooks/railway")
async def railway_webhook(
    request: Request,
    # Railway signatures work differently, simplified for MVP (check secret in query or header?)
    # For now, let's use a shared secret header: X-Railway-Secret
    x_railway_secret: Optional[str] = Header(None)
):
    """Handle Railway webhooks (Deployment success)."""
    if WEBHOOK_SECRET != "dev-webhook-secret":
        if x_railway_secret != WEBHOOK_SECRET:
             raise HTTPException(status_code=401, detail="Invalid secret")
             
    payload = await request.json()
    print(f"[WEBHOOK] Received Railway event: {payload.get('type')}")
    
    # Logic for deployment success (preview URL) will go here
    
    return {"status": "received"}



async def create_github_issue_task(bug_id: int):
    """Background task to create GitHub issue for a bug report."""
    # Create a new session for the background task
    async for session in get_session():
        try:
            bug = await session.get(BugReport, bug_id)
            if not bug or bug.github_issue_url:
                return

            # Construct issue body
            body = f"### Description\n{bug.notes}\n\n"
            
            if bug.expected:
                body += f"### Expected Behavior\n{bug.expected}\n\n"
            if bug.actual:
                body += f"### Actual Behavior\n{bug.actual}\n\n"
                
            body += f"### Metadata\n"
            body += f"- **Severity**: {bug.severity}\n"
            body += f"- **Category**: {bug.category}\n"
            body += f"- **Reporter ID**: {bug.user_id}\n"
            body += f"- **Report ID**: {bug.id}\n\n"

            if bug.attachments and bug.attachments != "[]":
                body += f"### Attachments\n"
                try:
                    paths = json.loads(bug.attachments)
                    for path in paths:
                        # In a real app, these would be public URLs or presigned links
                        # For now, we'll list the paths
                        body += f"- {path}\n"
                except:
                    pass
            
            if bug.diagnostics:
                summary = generate_diagnostics_summary(bug.diagnostics)
                body += f"\n### Diagnostics Summary\n{summary}\n"
                body += f"\n<details>\n<summary>Full Diagnostics JSON</summary>\n\n```json\n{bug.diagnostics}\n```\n</details>\n"

            # Add magic instruction block for Claude
            body += "\n\n<!-- CLAUDE-INSTRUCTION: Fix this bug. Use the provided context and diagnostics. -->"

            # Create Issue
            issue = await github_client.create_issue(
                title=f"[Bug] {bug.notes[:50]}...",
                body=body,
                labels=["ai-fix"]
            )

            if issue and issue.get("html_url"):
                bug.github_issue_url = issue["html_url"]
                bug.status = "sent"
                session.add(bug)
                await session.commit()
                print(f"[BUG] Linked report {bug_id} to issue {bug.github_issue_url}")
            
        except Exception as e:
            print(f"[BUG] Failed to create GitHub issue for report {bug_id}: {e}")
            traceback.print_exc()


async def require_admin(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
) -> User:
    """Dependency that requires admin role."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = await session.get(User, auth_session.user_id)
    if not user or not user.is_admin:
        # Log unauthorized admin access attempt
        await audit_log(
            session=session,
            action="admin.access_denied",
            user_id=auth_session.user_id,
            details={"reason": "Not an admin"},
        )
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return user


async def send_verification_email(to_email: str, code: str) -> bool:
    """Send verification code via Resend API. Returns True on success."""
    if not RESEND_API_KEY:
        print(f"[AUTH] RESEND_API_KEY not set. Code would be sent to {to_email}")
        return True
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": FROM_EMAIL,
                    "to": [to_email],
                    "subject": "Your verification code",
                    "text": f"Your verification code is: {code}",
                },
            )
            if 200 <= response.status_code < 300:
                print(f"[AUTH] Email sent to {to_email}")
                return True
            else:
                print(f"[AUTH] Resend error: {response.status_code}")
                return False
    except httpx.TimeoutException:
        print(f"[AUTH] Resend timeout for {to_email}")
        return False
    except httpx.RequestError as e:
        print(f"[AUTH] Resend request error: {type(e).__name__}")
        return False

# Initialize sourcing repository
sourcing_repo = SourcingRepository()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
 )

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

# Mount static files for serving uploads
# We need to map the /uploads URL to the actual directory
# If using absolute path like /data/uploads/bugs, we mount the parent or the specific dir?
# Mounting /uploads to the parent directory of 'bugs' is safer.
# If UPLOAD_DIR is /data/uploads/bugs, we serve /data/uploads at /uploads
UPLOAD_ROOT = UPLOAD_DIR.parent
try:
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
except Exception:
    UPLOAD_DIR = Path("/tmp/uploads/bugs")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_ROOT = UPLOAD_DIR.parent
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_ROOT)), name="uploads")

# Request/Response models
class HealthResponse(BaseModel):
    status: str
    version: str

# --- Bug Report Models ---
class BugReportRead(BaseModel):
    id: int
    status: str
    created_at: datetime
    notes: str
    severity: str
    category: str
    attachments: Optional[List[str]] = []

# --- Bug Report Endpoints ---

@app.post("/api/bugs", response_model=BugReportRead, status_code=201)
async def create_bug_report(
    notes: str = Form(...),
    severity: str = Form("low"),
    category: str = Form("ui"),
    expected: Optional[str] = Form(None),
    actual: Optional[str] = Form(None),
    includeDiagnostics: str = Form("true"), # Received as string from FormData
    diagnostics: Optional[str] = Form(None),
    attachments: List[UploadFile] = File(None),
    authorization: Optional[str] = Header(None),
    background_tasks: BackgroundTasks = None,
    session: AsyncSession = Depends(get_session)
):
    """
    Submit a bug report with optional file attachments.
    """
    # Authenticate (Optional - allow anon?)
    # For now, let's make it optional but link if auth present
    user_id = None
    if authorization:
        auth_session = await get_current_session(authorization, session)
        if auth_session:
            user_id = auth_session.user_id

    # 1. Save attachments
    saved_paths = []
    if attachments:
        for file in attachments:
            if not file.filename:
                continue
            
            # Sanitize filename (basic)
            safe_name = os.path.basename(file.filename).replace(" ", "_")
            # Create unique name
            timestamp = int(datetime.utcnow().timestamp())
            unique_name = f"{timestamp}_{secrets.token_hex(4)}_{safe_name}"
            file_path = UPLOAD_DIR / unique_name
            
            try:
                with file_path.open("wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                # Store relative path for URL generation
                saved_paths.append(f"/uploads/bugs/{unique_name}")
            except Exception as e:
                print(f"[BUG] Failed to save attachment {file.filename}: {e}")
            finally:
                file.file.close()

    # 2. Persist to DB
    bug = BugReport(
        user_id=user_id,
        notes=notes,
        severity=severity,
        category=category,
        expected=expected,
        actual=actual,
        status="captured",
        attachments=json.dumps(saved_paths) if saved_paths else "[]",
        diagnostics=diagnostics
    )
    
    session.add(bug)
    await session.commit()
    await session.refresh(bug)
    
    # Trigger GitHub Issue Creation
    if background_tasks is not None:
        background_tasks.add_task(create_github_issue_task, bug.id)
    
    # Return formatted response
    return BugReportRead(
        id=bug.id,
        status=bug.status,
        created_at=bug.created_at,
        notes=bug.notes,
        severity=bug.severity,
        category=bug.category,
        attachments=saved_paths
    )

@app.get("/api/bugs/{bug_id}", response_model=BugReportRead)
async def get_bug_report(
    bug_id: int,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    """Get status of a specific bug report."""
    # Authenticate
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Fetch bug
    result = await session.exec(select(BugReport).where(BugReport.id == bug_id))
    bug = result.first()
    
    if not bug:
        raise HTTPException(status_code=404, detail="Bug report not found")
        
    # Check ownership (or admin)
    user = await session.get(User, auth_session.user_id)
    is_admin = user.is_admin if user else False
    
    if bug.user_id != auth_session.user_id and not is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to view this report")
    
    # Parse attachments
    attachments_list = []
    if bug.attachments:
        try:
            attachments_list = json.loads(bug.attachments)
        except:
            attachments_list = []

    return BugReportRead(
        id=bug.id,
        status=bug.status,
        created_at=bug.created_at,
        notes=bug.notes,
        severity=bug.severity,
        category=bug.category,
        attachments=attachments_list
    )

@app.get("/api/bugs", response_model=List[BugReportRead])
async def list_bug_reports(
    authorization: Optional[str] = Header(None),
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session)
):
    """List all bug reports (Admin only)."""
    result = await session.exec(select(BugReport).order_by(BugReport.created_at.desc()))
    bugs = result.all()
    
    response = []
    for bug in bugs:
        attachments_list = []
        if bug.attachments:
            try:
                attachments_list = json.loads(bug.attachments)
            except:
                attachments_list = []
                
        response.append(BugReportRead(
            id=bug.id,
            status=bug.status,
            created_at=bug.created_at,
            notes=bug.notes,
            severity=bug.severity,
            category=bug.category,
            attachments=attachments_list
        ))
        
    return response

# --- Response Models for Read with Relationships ---
class SellerRead(BaseModel):
    id: int
    name: str
    domain: Optional[str] = None

class BidRead(BaseModel):
    id: int
    price: float
    currency: str
    item_title: str
    item_url: Optional[str] = None
    image_url: Optional[str] = None
    source: str
    is_selected: bool = False
    seller: Optional[SellerRead] = None

class RowReadWithBids(RowBase):
    id: int
    user_id: int
    bids: List[BidRead] = []

class SearchRequest(BaseModel):
    query: str
    gl: Optional[str] = "us"
    hl: Optional[str] = "en"
    providers: Optional[List[str]] = None

class SearchResponse(BaseModel):
    results: List[SearchResult]

# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    return {
        "status": "healthy",
        "version": "0.1.0"
    }

# DB endpoints
@app.post("/rows", response_model=Row)
async def create_row(
    row: RowCreate,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    # Authenticate
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Extract request_spec data
    request_spec_data = row.request_spec
    
    # Create Row
    db_row = Row(
        title=row.title,
        status=row.status,
        budget_max=row.budget_max,
        currency=row.currency,
        user_id=auth_session.user_id,
        choice_factors=row.choice_factors,
        choice_answers=row.choice_answers
    )
    session.add(db_row)
    await session.commit()
    await session.refresh(db_row)
    
    # Create RequestSpec linked to Row
    db_spec = RequestSpec(
        row_id=db_row.id,
        item_name=request_spec_data.item_name,
        constraints=request_spec_data.constraints,
        preferences=request_spec_data.preferences
    )
    session.add(db_spec)
    await session.commit()
    
    # Refresh row to ensure relationships are loaded (though we might need to eager load)
    await session.refresh(db_row)
    return db_row

@app.get("/rows", response_model=List[RowReadWithBids])
async def read_rows(
    authorization: Optional[str] = Header(None),
    include_archived: bool = Query(False),
    session: AsyncSession = Depends(get_session)
):
    # Authenticate
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Fetch rows with bids and sellers eagerly loaded
    result = await session.exec(
        select(Row)
        .where(
            Row.user_id == auth_session.user_id,
            True if include_archived else (Row.status != "archived"),
        )
        .options(selectinload(Row.bids).joinedload(Bid.seller))
        .order_by(Row.updated_at.desc())
    )
    return result.all()

@app.get("/rows/{row_id}", response_model=RowReadWithBids)
async def read_row(
    row_id: int,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    # Authenticate
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Fetch row scoped to user
    result = await session.exec(
        select(Row)
        .where(Row.id == row_id, Row.user_id == auth_session.user_id)
        .options(selectinload(Row.bids).joinedload(Bid.seller))
    )
    row = result.first()
    
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")
    return row

@app.delete("/rows/{row_id}")
async def delete_row(
    row_id: int,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    # Authenticate
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Fetch row scoped to user
    result = await session.exec(
        select(Row).where(Row.id == row_id, Row.user_id == auth_session.user_id)
    )
    row = result.first()

    if not row:
        raise HTTPException(status_code=404, detail="Row not found")
    
    # Soft-delete (archive) row for auditability.
    row.status = "archived"
    row.updated_at = datetime.utcnow()
    session.add(row)
    await session.commit()
    return {"status": "archived", "id": row_id}

class RequestSpecUpdate(BaseModel):
    item_name: Optional[str] = None
    constraints: Optional[str] = None
    preferences: Optional[str] = None

class RowUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    budget_max: Optional[float] = None
    request_spec: Optional[RequestSpecUpdate] = None
    choice_factors: Optional[str] = None
    choice_answers: Optional[str] = None
    selected_bid_id: Optional[int] = None

@app.patch("/rows/{row_id}")
async def update_row(
    row_id: int,
    row_update: RowUpdate,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    print(f"Received PATCH request for row {row_id} with data: {row_update}")
    
    # Authenticate
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Fetch row scoped to user
    result = await session.exec(
        select(Row).where(Row.id == row_id, Row.user_id == auth_session.user_id)
    )
    row = result.first()

    if not row:
        print(f"Row {row_id} not found")
        raise HTTPException(status_code=404, detail="Row not found")
    
    row_data = row_update.dict(exclude_unset=True)
    selected_bid_id = row_data.pop("selected_bid_id", None)

    # Separate row fields and request_spec updates
    request_spec_updates = row_data.pop("request_spec", None)

    if selected_bid_id is not None:
        bids_result = await session.exec(select(Bid).where(Bid.row_id == row_id))
        bids = bids_result.all()
        found = False
        for row_bid in bids:
            if row_bid.id == selected_bid_id:
                found = True
            row_bid.is_selected = row_bid.id == selected_bid_id
            session.add(row_bid)

        if not found:
            raise HTTPException(status_code=404, detail="Option not found")

        row.status = "closed"

    for key, value in row_data.items():
        setattr(row, key, value)
        
    # Update request_spec if provided
    if request_spec_updates:
        result = await session.exec(select(RequestSpec).where(RequestSpec.row_id == row_id))
        spec = result.first()
        if spec:
            spec_data = request_spec_updates
            for key, value in spec_data.items():
                setattr(spec, key, value)
            session.add(spec)

    row.updated_at = datetime.utcnow()
    session.add(row)
    await session.commit()
    await session.refresh(row)
    print(f"Row {row_id} updated successfully: {row}")
    return row


@app.post("/rows/{row_id}/options/{option_id}/select")
async def select_row_option(
    row_id: int,
    option_id: int,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    # Authenticate
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Fetch row scoped to user
    result = await session.exec(
        select(Row).where(Row.id == row_id, Row.user_id == auth_session.user_id)
    )
    row = result.first()

    if not row:
        raise HTTPException(status_code=404, detail="Row not found")

    bid_result = await session.exec(
        select(Bid).where(Bid.id == option_id, Bid.row_id == row_id)
    )
    bid = bid_result.first()
    if not bid:
        raise HTTPException(status_code=404, detail="Option not found")

    all_bids_result = await session.exec(select(Bid).where(Bid.row_id == row_id))
    for row_bid in all_bids_result.all():
        row_bid.is_selected = row_bid.id == option_id
        session.add(row_bid)

    row.status = "closed"
    row.updated_at = datetime.utcnow()
    session.add(row)

    await session.commit()

    return {
        "status": "selected",
        "row_id": row_id,
        "option_id": option_id,
        "row_status": row.status,
    }


class RowSearchRequest(BaseModel):
    query: Optional[str] = None
    providers: Optional[List[str]] = None

from collections import defaultdict

# Simple in-memory rate limiter (use Redis in production)
rate_limit_store: dict[str, List[datetime]] = defaultdict(list)
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = {
    "search": 30,      # 30 searches per minute
    "clickout": 60,    # 60 clicks per minute
    "auth_start": 5,   # 5 login attempts per minute
}

def check_rate_limit(key: str, limit_type: str) -> bool:
    """Returns True if request is allowed, False if rate limited."""
    now = datetime.utcnow()
    window_start = now - timedelta(seconds=RATE_LIMIT_WINDOW)
    
    # Clean old entries
    rate_limit_store[key] = [
        t for t in rate_limit_store[key] if t > window_start
    ]
    
    max_requests = RATE_LIMIT_MAX.get(limit_type, 100)
    if len(rate_limit_store[key]) >= max_requests:
        return False
    
    rate_limit_store[key].append(now)
    return True


@app.post("/rows/{row_id}/search", response_model=SearchResponse)
async def search_row_listings(
    row_id: int,
    body: RowSearchRequest,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    # Authenticate
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Rate limiting
    rate_key = f"search:{auth_session.user_id}"
    if not check_rate_limit(rate_key, "search"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    # Fetch row scoped to user
    result = await session.exec(
        select(Row).where(Row.id == row_id, Row.user_id == auth_session.user_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")

    # Load request spec
    spec_result = await session.exec(select(RequestSpec).where(RequestSpec.row_id == row_id))
    spec = spec_result.first()

    # Build query from stored state unless overridden
    base_query = body.query or row.title or (spec.item_name if spec else "")

    # Combine constraints (stored as JSON string) into the query for now
    if spec and spec.constraints:
        try:
            import json
            constraints_obj = json.loads(spec.constraints)
            constraint_parts = []
            for k, v in constraints_obj.items():
                constraint_parts.append(f"{k}: {v}")
            if constraint_parts:
                base_query = base_query + " " + " ".join(constraint_parts)
        except Exception:
            pass

    # Combine choice answers (user-defined specifications) into the query
    if row.choice_answers:
        try:
            import json
            answers_obj = json.loads(row.choice_answers)
            answer_parts = []

            def _to_num(v):
                if v is None or v == "":
                    return None
                try:
                    return float(v)
                except Exception:
                    return None

            min_price = _to_num(answers_obj.get('min_price'))
            max_price = _to_num(answers_obj.get('max_price'))
            if min_price is not None or max_price is not None:
                if min_price is not None and max_price is not None:
                    answer_parts.append(f"price between {min_price} and {max_price}")
                elif max_price is not None:
                    answer_parts.append(f"price under {max_price}")
                else:
                    answer_parts.append(f"price over {min_price}")

            for k, v in answers_obj.items():
                if k in ('min_price', 'max_price'):
                    continue
                # specific logic to handle boolean/select/text differently if needed
                # for now, simply append "key: value" or just "value" might be better for search?
                # "color: blue" is good. "primary_use: gaming" is good.
                if v and str(v).lower() != "not answered":
                     answer_parts.append(f"{k} {v}")
            if answer_parts:
                base_query = base_query + " " + " ".join(answer_parts)
        except Exception:
            pass

    # Execute Search
    results = await sourcing_repo.search_all(base_query, providers=body.providers)

    # Ensure click_url includes row_id for attribution in clickout logging
    for r in results:
        try:
            # If backend already provided click_url, augment with row_id when missing.
            # We intentionally keep idx/source/url as-is.
            if getattr(r, "click_url", "") and "row_id=" not in str(r.click_url):
                joiner = "&" if "?" in str(r.click_url) else "?"
                r.click_url = f"{r.click_url}{joiner}row_id={row_id}"
        except Exception:
            pass
    
    # --- Persistence Logic ---
    
    # 1. Clear old bids for this row (fresh start)
    # Note: In a real prod app, you might want to archive them or do a diff update.
    # For MVP, clearing is safest to avoid duplicates.
    existing_bids = await session.exec(select(Bid).where(Bid.row_id == row_id))
    for bid in existing_bids.all():
        await session.delete(bid)
    
    # 2. Save new results
    for res in results:
        # Find or Create Seller
        merchant_name = res.merchant or "Unknown"
        seller_res = await session.exec(select(Seller).where(Seller.name == merchant_name))
        seller = seller_res.first()
        
        if not seller:
            seller = Seller(name=merchant_name, domain=res.merchant_domain)
            session.add(seller)
            await session.commit()
            await session.refresh(seller)
            
        # Create Bid
        bid = Bid(
            row_id=row_id,
            seller_id=seller.id,
            price=res.price,
            total_cost=res.price, # Shipping logic later
            currency=res.currency,
            item_title=res.title,
            item_url=res.url,
            image_url=res.image_url,
            source=res.source,
            is_selected=False
        )
        session.add(bid)
        await session.flush()
        res.bid_id = bid.id
        res.is_selected = bid.is_selected
    
    # Update row status if needed
    row.status = "bids_arriving"
    row.updated_at = datetime.utcnow()
    session.add(row)
    
    await session.commit()
    
    return {"results": results}


@app.get("/api/out")
async def clickout_redirect(
    url: str,
    request: Request,
    row_id: Optional[int] = None,
    idx: int = 0,
    source: str = "unknown",
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    """
    Log a clickout event and redirect to the merchant.
    
    Query params:
        url: The canonical merchant URL
        row_id: The procurement row this offer belongs to
        idx: The offer's position in search results
        source: The sourcing provider (e.g., serpapi_google_shopping)
    """
    # Validate URL
    if not url or not url.startswith(('http://', 'https://')):
        raise HTTPException(status_code=400, detail="Invalid URL")
    
    # Extract user if authenticated
    user_id = None
    session_id = None
    if authorization:
        auth_session = await get_current_session(authorization, session)
        if auth_session:
            user_id = auth_session.user_id
            session_id = auth_session.id

    # Rate limiting (per user or IP)
    rate_key = f"clickout:{user_id or request.client.host}"
    if not check_rate_limit(rate_key, "clickout"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Extract merchant domain
    merchant_domain = extract_merchant_domain(url)
    
    # Build context for resolver
    context = ClickContext(
        user_id=user_id,
        row_id=row_id,
        offer_index=idx,
        source=source,
        merchant_domain=merchant_domain,
    )
    
    # Resolve affiliate link
    resolved = link_resolver.resolve(url, context)
    
    # Fire-and-forget logging (don't block the redirect)
    async def log_clickout():
        try:
            from database import engine
            from sqlalchemy.orm import sessionmaker
            from sqlmodel.ext.asyncio.session import AsyncSession as AS
            async_session = sessionmaker(engine, class_=AS, expire_on_commit=False)
            async with async_session() as log_session:
                event = ClickoutEvent(
                    user_id=user_id,
                    session_id=session_id,
                    row_id=row_id,
                    offer_index=idx,
                    canonical_url=url,
                    final_url=resolved.final_url,
                    merchant_domain=merchant_domain,
                    handler_name=resolved.handler_name,
                    affiliate_tag=resolved.affiliate_tag,
                    source=source,
                )
                log_session.add(event)
                await log_session.commit()
                await log_session.refresh(event)
                
                # Audit log
                await audit_log(
                    session=log_session,
                    action="clickout.redirect",
                    user_id=user_id,
                    resource_type="clickout",
                    resource_id=str(event.id),
                    details={
                        "canonical_url": url,
                        "merchant_domain": merchant_domain,
                        "handler_name": resolved.handler_name,
                    },
                    request=request,
                )
        except Exception as e:
            print(f"[CLICKOUT] Failed to log: {e}")
    
    # Start logging in background, redirect immediately
    asyncio.create_task(log_clickout())
    
    # Redirect to transformed URL immediately
    return RedirectResponse(url=resolved.final_url, status_code=302)


# Search endpoint
@app.post("/v1/sourcing/search", response_model=SearchResponse)
async def search_listings(request: SearchRequest):
    results = await sourcing_repo.search_all(
        request.query,
        gl=request.gl,
        hl=request.hl,
        providers=request.providers,
    )
    return {"results": results}


# ============ AUTH ENDPOINTS ============

LOCKOUT_MINUTES = 45
MAX_ATTEMPTS = 5


class AuthStartRequest(BaseModel):
    email: EmailStr


class AuthStartResponse(BaseModel):
    status: str
    locked_until: Optional[datetime] = None


class MintSessionRequest(BaseModel):
    email: EmailStr


class MintSessionResponse(BaseModel):
    session_token: str


@app.post("/test/mint-session", response_model=MintSessionResponse)
async def mint_session(request: MintSessionRequest, session: AsyncSession = Depends(get_session)):
    """
    Test-only endpoint to mint a session without email interaction.
    Only enabled when E2E_TEST_MODE=1 env var is set.
    """
    if os.getenv("E2E_TEST_MODE") != "1":
        raise HTTPException(status_code=404, detail="Not Found")
    
    # Rate limiting (strict for minting)
    if not check_rate_limit(f"mint:{request.email}", "auth_start"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    email = request.email.lower()
    
    # Create user if not exists
    result = await session.exec(select(User).where(User.email == email))
    user = result.first()
    if not user:
        user = User(email=email)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    
    # Create session
    token = generate_session_token()
    new_session = AuthSession(
        email=email,
        user_id=user.id,
        session_token_hash=hash_token(token),
    )
    session.add(new_session)
    await session.commit()
    
    return {"session_token": token}


@app.post("/auth/start", response_model=AuthStartResponse)
async def auth_start(
    auth_request: AuthStartRequest,
    req: Request,
    session: AsyncSession = Depends(get_session)
):
    """Send a verification code to the user's email."""
    email = auth_request.email.lower()
    
    # Audit log start
    await audit_log(
        session=session,
        action="auth.login_start",
        details={"email": email},
        request=req,
    )
    
    now = datetime.utcnow()
    
    # Check for existing active codes and lockout, then invalidate them
    result = await session.exec(
        select(AuthLoginCode)
        .where(AuthLoginCode.email == email, AuthLoginCode.is_active == True)
    )
    existing_codes = result.all()
    
    for existing_code in existing_codes:
        if existing_code.locked_until and existing_code.locked_until > now:
            raise HTTPException(
                status_code=429,
                detail={"status": "locked", "locked_until": existing_code.locked_until.isoformat()}
            )
        existing_code.is_active = False
        session.add(existing_code)
    
    # Generate new code
    code = generate_verification_code()
    new_login_code = AuthLoginCode(
        email=email,
        code_hash=hash_token(code),
        is_active=True,
        attempt_count=0,
        locked_until=None,
    )
    session.add(new_login_code)
    await session.commit()
    
    # Send email
    await send_verification_email(email, code)
    
    return {"status": "sent"}


class AuthVerifyRequest(BaseModel):
    email: EmailStr
    code: str


class AuthVerifyResponse(BaseModel):
    status: str
    session_token: Optional[str] = None


@app.post("/auth/verify", response_model=AuthVerifyResponse)
async def auth_verify(request: AuthVerifyRequest, session: AsyncSession = Depends(get_session)):
    """Verify the code and create a session."""
    email = request.email.lower()
    now = datetime.utcnow()
    
    # Find active code for this email
    result = await session.exec(
        select(AuthLoginCode)
        .where(AuthLoginCode.email == email, AuthLoginCode.is_active == True)
    )
    login_code = result.first()
    
    if not login_code:
        raise HTTPException(status_code=400, detail="No active code found. Request a new one.")
    
    # Check lockout
    if login_code.locked_until and login_code.locked_until > now:
        raise HTTPException(
            status_code=429,
            detail={"status": "locked", "locked_until": login_code.locked_until.isoformat()}
        )
    
    # Verify code
    if hash_token(request.code) != login_code.code_hash:
        login_code.attempt_count += 1
        if login_code.attempt_count >= MAX_ATTEMPTS:
            login_code.locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
            login_code.is_active = False
        session.add(login_code)
        await session.commit()
        
        remaining = MAX_ATTEMPTS - login_code.attempt_count
        if remaining <= 0:
            raise HTTPException(
                status_code=429,
                detail={"status": "locked", "locked_until": login_code.locked_until.isoformat()}
            )
        raise HTTPException(status_code=400, detail=f"Invalid code. {remaining} attempts remaining.")
    
    # Code is valid - deactivate it
    login_code.is_active = False
    session.add(login_code)
    
    # Create user if not exists (registration on first login)
    result = await session.exec(select(User).where(User.email == email))
    user = result.first()
    if not user:
        user = User(email=email)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    
    # Create session
    token = generate_session_token()
    new_session = AuthSession(
        email=email,
        user_id=user.id,
        session_token_hash=hash_token(token),
    )
    session.add(new_session)
    await session.commit()
    
    return {"status": "ok", "session_token": token}


class AuthMeResponse(BaseModel):
    authenticated: bool
    email: Optional[str] = None


async def get_current_session(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
) -> Optional[AuthSession]:
    """Extract and validate session from Authorization header.
    
    Supports both legacy session tokens and Clerk JWTs.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    
    token = authorization[7:]
    
    # First, try Clerk JWT verification
    clerk_user_id = get_clerk_user_id(token)
    if clerk_user_id:
        # Find or create user by Clerk ID
        result = await session.exec(
            select(User).where(User.clerk_user_id == clerk_user_id)
        )
        user = result.first()
        
        if not user:
            # Create new user for this Clerk ID
            user = User(clerk_user_id=clerk_user_id, email=None)
            session.add(user)
            await session.commit()
            await session.refresh(user)
            print(f"[CLERK] Created new user {user.id} for Clerk ID {clerk_user_id}")
        
        # Return a synthetic AuthSession for compatibility
        # We create a fake AuthSession object that has the user_id
        fake_session = AuthSession(
            user_id=user.id,
            session_token_hash="clerk_jwt",
            email=user.email,
        )
        fake_session.id = -1  # Marker for Clerk session
        return fake_session
    
    # Fallback: try legacy session token lookup
    token_hash = hash_token(token)
    
    result = await session.exec(
        select(AuthSession)
        .where(AuthSession.session_token_hash == token_hash, AuthSession.revoked_at == None)
    )
    return result.first()


@app.get("/auth/me", response_model=AuthMeResponse)
async def auth_me(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    """Check if user is authenticated."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"authenticated": True, "email": auth_session.email}


@app.post("/auth/logout")
async def auth_logout(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    """Revoke the current session."""
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    auth_session.revoked_at = datetime.utcnow()
    session.add(auth_session)
    await session.commit()
    
    return {"status": "ok"}


@app.get("/admin/audit")
async def list_audit_logs(
    limit: int = 100,
    action: Optional[str] = None,
    user_id: Optional[int] = None,
    since: Optional[datetime] = None,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """List audit logs (admin only)."""
    # Verify admin access log (already logged in require_admin)
    
    query = select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit)
    
    if action:
        query = query.where(AuditLog.action == action)
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if since:
        query = query.where(AuditLog.timestamp >= since)
    
    result = await session.exec(query)
    return result.all()


@app.get("/health/ready")
async def readiness_check(session: AsyncSession = Depends(get_session)):
    """
    Readiness check - verifies all dependencies are available.
    
    Returns 503 if any dependency is unavailable.
    """
    checks = {}
    
    # Database check
    try:
        await session.exec(select(1))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)[:100]}"
    
    # Check if any critical dependency failed
    all_ok = all(v == "ok" for v in checks.values())
    
    return JSONResponse(
        status_code=200 if all_ok else 503,
        content={
            "status": "ready" if all_ok else "degraded",
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled errors.
    
    - Logs full traceback
    - Returns safe error message to client
    - Creates audit log entry
    """
    error_id = f"ERR-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{id(exc)}"
    
    # Log full error (server-side)
    print(f"[ERROR {error_id}] Unhandled exception:")
    traceback.print_exc()
    
    # Audit log (best effort)
    try:
        # We need a new session here because the request session might be rolled back
        async with get_session() as session:
            # Note: auth info might be missing if auth failed
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
    except:
        pass  # Don't let audit logging fail the error handler
    
    # Safe response to client
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "error_id": error_id,
            "message": "An unexpected error occurred. Please try again.",
        }
    )


# Startup event
@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    print("FastAPI application starting...")
    print(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    print(f"E2E_TEST_MODE: {os.getenv('E2E_TEST_MODE')}")
    # In production, schema management is handled by Alembic migrations (run via start command).
    # We do NOT run init_db() here to avoid conflicts and ensure version control.
    # await init_db()


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    print("FastAPI application shutting down...")
