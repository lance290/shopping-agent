"""
FastAPI Application Example
Production-ready template with health checks and CORS
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from datetime import datetime
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from sourcing import SourcingRepository, SearchResult
from database import init_db, get_session
from models import Row, RowBase, RowCreate, RequestSpec

# Create FastAPI app
app = FastAPI(
    title="Shopping Agent Backend",
    description="Agent-facilitated competitive bidding backend",
    version="0.1.0"
)

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

# Request/Response models
class HealthResponse(BaseModel):
    status: str
    version: str

class SearchRequest(BaseModel):
    query: str
    gl: Optional[str] = "us"
    hl: Optional[str] = "en"

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
async def create_row(row: RowCreate, session: AsyncSession = Depends(get_session)):
    # Extract request_spec data
    request_spec_data = row.request_spec
    
    # Create Row
    db_row = Row(
        title=row.title,
        status=row.status,
        budget_max=row.budget_max,
        currency=row.currency
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

@app.get("/rows", response_model=List[Row])
async def read_rows(session: AsyncSession = Depends(get_session)):
    result = await session.exec(select(Row))
    return result.all()

@app.get("/rows/{row_id}", response_model=Row)
async def read_row(row_id: int, session: AsyncSession = Depends(get_session)):
    row = await session.get(Row, row_id)
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")
    return row

@app.delete("/rows/{row_id}")
async def delete_row(row_id: int, session: AsyncSession = Depends(get_session)):
    row = await session.get(Row, row_id)
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")
    
    # Delete related RequestSpec first (foreign key constraint)
    result = await session.exec(select(RequestSpec).where(RequestSpec.row_id == row_id))
    for spec in result.all():
        await session.delete(spec)
    
    # Delete related Bids
    from models import Bid
    result = await session.exec(select(Bid).where(Bid.row_id == row_id))
    for bid in result.all():
        await session.delete(bid)
    
    await session.delete(row)
    await session.commit()
    return {"status": "deleted", "id": row_id}

class RowUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    budget_max: Optional[float] = None

@app.patch("/rows/{row_id}")
async def update_row(row_id: int, row_update: RowUpdate, session: AsyncSession = Depends(get_session)):
    print(f"Received PATCH request for row {row_id} with data: {row_update}")
    row = await session.get(Row, row_id)
    if not row:
        print(f"Row {row_id} not found")
        raise HTTPException(status_code=404, detail="Row not found")
    
    row_data = row_update.dict(exclude_unset=True)
    for key, value in row_data.items():
        setattr(row, key, value)
        
    row.updated_at = datetime.utcnow()
    session.add(row)
    await session.commit()
    await session.refresh(row)
    print(f"Row {row_id} updated successfully: {row}")
    return row

# Search endpoint
@app.post("/v1/sourcing/search", response_model=SearchResponse)
async def search_listings(request: SearchRequest):
    results = await sourcing_repo.search_all(request.query, gl=request.gl, hl=request.hl)
    return {"results": results}

# Startup event
@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    print("FastAPI application starting...")
    print(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    await init_db()


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    print("FastAPI application shutting down...")
