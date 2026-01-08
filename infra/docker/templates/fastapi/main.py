"""
FastAPI Application Example
Production-ready template with health checks and CORS
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os

# Create FastAPI app
app = FastAPI(
    title="FastAPI Application",
    description="Production-ready FastAPI template",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class HealthResponse(BaseModel):
    status: str
    version: str

class MessageRequest(BaseModel):
    message: str

class MessageResponse(BaseModel):
    echo: str
    length: int

# Health check endpoint (required for Railway/Cloud Run)
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "version": "1.0.0"
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "FastAPI Application",
        "docs": "/docs",
        "health": "/health"
    }

# Example POST endpoint
@app.post("/echo", response_model=MessageResponse)
async def echo_message(request: MessageRequest):
    """Echo back the message with its length"""
    return {
        "echo": request.message,
        "length": len(request.message)
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    print("FastAPI application starting...")
    print(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    print("FastAPI application shutting down...")
