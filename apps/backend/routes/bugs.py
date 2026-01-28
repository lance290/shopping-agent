"""Bug report routes - submit and track bug reports."""
from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import json
import traceback

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from models import BugReport, User
from github_client import github_client
from diagnostics_utils import generate_diagnostics_summary
from storage import get_storage_provider

router = APIRouter(tags=["bugs"])

# Lazy init to avoid import-time filesystem errors
_storage_provider = None

def get_storage():
    global _storage_provider
    if _storage_provider is None:
        _storage_provider = get_storage_provider()
    return _storage_provider


class BugReportRead(BaseModel):
    id: int
    status: str
    created_at: datetime
    notes: str
    severity: str
    category: str
    attachments: Optional[List[str]] = []


async def create_github_issue_task(bug_id: int):
    """Background task to create GitHub issue for a bug report."""
    from database import get_session
    
    async for session in get_session():
        try:
            bug = await session.get(BugReport, bug_id)
            if not bug or bug.github_issue_url:
                return

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
                        body += f"- {path}\n"
                except:
                    pass
            
            if bug.diagnostics:
                summary = generate_diagnostics_summary(bug.diagnostics)
                body += f"\n### Diagnostics Summary\n{summary}\n"
                body += f"\n<details>\n<summary>Full Diagnostics JSON</summary>\n\n```json\n{bug.diagnostics}\n```\n</details>\n"

            body += "\n\n<!-- CLAUDE-INSTRUCTION: Fix this bug. Use the provided context and diagnostics. -->"

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
    from routes.auth import get_current_session
    from audit import audit_log
    
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = await session.get(User, auth_session.user_id)
    if not user or not user.is_admin:
        await audit_log(
            session=session,
            action="admin.access_denied",
            user_id=auth_session.user_id,
            details={"reason": "Not an admin"},
        )
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return user


@router.post("/api/bugs", response_model=BugReportRead, status_code=201)
async def create_bug_report(
    notes: str = Form(...),
    severity: str = Form("low"),
    category: str = Form("ui"),
    expected: Optional[str] = Form(None),
    actual: Optional[str] = Form(None),
    includeDiagnostics: str = Form("true"),
    diagnostics: Optional[str] = Form(None),
    attachments: List[UploadFile] = File(None),
    authorization: Optional[str] = Header(None),
    background_tasks: BackgroundTasks = None,
    session: AsyncSession = Depends(get_session)
):
    """Submit a bug report with optional file attachments."""
    from routes.auth import get_current_session
    
    user_id = None
    if authorization:
        auth_session = await get_current_session(authorization, session)
        if auth_session:
            user_id = auth_session.user_id

    saved_paths = []
    if attachments:
        for file in attachments:
            if not file.filename:
                continue
            
            try:
                content = await file.read()
                public_url = await get_storage().save_file(content, file.filename, "bugs")
                saved_paths.append(public_url)
            except Exception as e:
                print(f"[BUG] Failed to save attachment {file.filename}: {e}")
            finally:
                await file.close()

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
    
    if background_tasks is not None:
        background_tasks.add_task(create_github_issue_task, bug.id)
    
    return BugReportRead(
        id=bug.id,
        status=bug.status,
        created_at=bug.created_at,
        notes=bug.notes,
        severity=bug.severity,
        category=bug.category,
        attachments=saved_paths
    )


@router.get("/api/bugs/{bug_id}", response_model=BugReportRead)
async def get_bug_report(
    bug_id: int,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    """Get status of a specific bug report."""
    from routes.auth import get_current_session
    
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await session.exec(select(BugReport).where(BugReport.id == bug_id))
    bug = result.first()
    
    if not bug:
        raise HTTPException(status_code=404, detail="Bug report not found")
        
    user = await session.get(User, auth_session.user_id)
    is_admin = user.is_admin if user else False
    
    if bug.user_id != auth_session.user_id and not is_admin:
        raise HTTPException(status_code=404, detail="Bug report not found")
    
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


@router.get("/api/bugs", response_model=List[BugReportRead])
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
