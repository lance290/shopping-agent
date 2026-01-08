"""
LangChain/LangGraph/CrewAI Agent Service
Production-ready FastAPI server for AI agents
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os

# Import example agents
from examples.langgraph_agent import run_langgraph_agent
from examples.crewai_team import run_crewai_team
from examples.simple_agent import run_simple_agent

app = FastAPI(
    title="AI Agent Service",
    description="Production-ready AI agents with LangChain/LangGraph/CrewAI",
    version="1.0.0"
)

# Request/Response models
class AgentRequest(BaseModel):
    query: str
    agent_type: str = "simple"  # simple, langgraph, crewai
    config: Optional[Dict[str, Any]] = None

class AgentResponse(BaseModel):
    result: str
    agent_type: str
    metadata: Optional[Dict[str, Any]] = None

@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "AI Agent Service",
        "version": "1.0.0",
        "agents": ["simple", "langgraph", "crewai"],
        "endpoints": ["/health", "/agent", "/docs"]
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.post("/agent", response_model=AgentResponse)
async def run_agent(request: AgentRequest):
    """
    Run an AI agent based on the specified type
    
    Agent types:
    - simple: Basic LangChain agent with tools
    - langgraph: Multi-step agent with state management
    - crewai: Team of role-based agents
    """
    try:
        # Validate API key
        if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
            raise HTTPException(
                status_code=500,
                detail="No LLM API key configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY"
            )
        
        # Route to appropriate agent
        if request.agent_type == "simple":
            result = await run_simple_agent(request.query, request.config or {})
        elif request.agent_type == "langgraph":
            result = await run_langgraph_agent(request.query, request.config or {})
        elif request.agent_type == "crewai":
            result = await run_crewai_team(request.query, request.config or {})
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown agent type: {request.agent_type}"
            )
        
        return AgentResponse(
            result=result["output"],
            agent_type=request.agent_type,
            metadata=result.get("metadata", {})
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
