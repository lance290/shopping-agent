"""Projects routes - CRUD for project groups."""
from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional, List

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from models import Project, ProjectCreate, Row

router = APIRouter(tags=["projects"])


@router.post("/projects", response_model=Project)
async def create_project(
    project: ProjectCreate,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    from routes.auth import get_current_session
    
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    db_project = Project(
        title=project.title,
        user_id=auth_session.user_id
    )
    session.add(db_project)
    await session.commit()
    await session.refresh(db_project)
    return db_project


@router.get("/projects", response_model=List[Project])
async def read_projects(
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    from routes.auth import get_current_session
    
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await session.exec(
        select(Project)
        .where(Project.user_id == auth_session.user_id)
        .order_by(Project.created_at.desc())
    )
    return result.all()


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: int,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    from routes.auth import get_current_session
    
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await session.exec(
        select(Project).where(Project.id == project_id, Project.user_id == auth_session.user_id)
    )
    project = result.first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Unlink child rows (ungroup them)
    rows_result = await session.exec(select(Row).where(Row.project_id == project_id))
    for row in rows_result.all():
        row.project_id = None
        session.add(row)
    
    await session.delete(project)
    await session.commit()
    return {"status": "deleted", "id": project_id}
