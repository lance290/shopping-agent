"""Projects routes - CRUD for project groups."""
from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional, List

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from database import get_session
from models import Project, ProjectCreate, Row
from dependencies import get_current_session, resolve_user_id

router = APIRouter(tags=["projects"])


@router.post("/projects", response_model=Project)
async def create_project(
    project: ProjectCreate,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    
    user_id = await resolve_user_id(authorization, session)

    db_project = Project(
        title=project.title,
        user_id=user_id
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
    
    user_id = await resolve_user_id(authorization, session)

    result = await session.exec(
        select(Project)
        .where(Project.user_id == user_id, Project.status != "archived")
        .order_by(Project.created_at.desc())
    )
    return result.all()


@router.post("/projects/{project_id}/duplicate", response_model=Project)
async def duplicate_project(
    project_id: int,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await session.exec(
        select(Project).where(Project.id == project_id, Project.user_id == auth_session.user_id)
    )
    project = result.first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    new_project = Project(
        title=f"{project.title} (Copy)",
        user_id=auth_session.user_id
    )
    session.add(new_project)
    await session.commit()
    await session.refresh(new_project)

    rows_result = await session.exec(
        select(Row).where(Row.project_id == project_id, Row.status != "archived")
    )
    for row in rows_result.all():
        new_row = Row(
            user_id=auth_session.user_id,
            project_id=new_project.id,
            title=row.title,
            status=row.status,
            is_service=row.is_service,
            service_category=row.service_category,
            choice_answers=row.choice_answers,
            provider_query=row.provider_query,
            desire_tier=row.desire_tier,
            budget_max=row.budget_max,
            currency=row.currency
        )
        session.add(new_row)

    await session.commit()
    return new_project


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: int,
    authorization: Optional[str] = Header(None),
    session: AsyncSession = Depends(get_session)
):
    
    auth_session = await get_current_session(authorization, session)
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await session.exec(
        select(Project).where(Project.id == project_id, Project.user_id == auth_session.user_id)
    )
    project = result.first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.status = "archived"
    session.add(project)

    # Unlink rows from this project so they don't reference an archived project
    rows_result = await session.exec(
        select(Row).where(Row.project_id == project_id)
    )
    for row in rows_result.all():
        row.project_id = None
        session.add(row)

    await session.commit()
    return {"status": "archived", "id": project_id}
