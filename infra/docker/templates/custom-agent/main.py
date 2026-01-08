"""
Custom Lightweight Agent Service
No frameworks - direct LLM API calls with function calling
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os

from agent import Agent
from tools import AVAILABLE_TOOLS

app = FastAPI(
    title="Custom Agent Service",
    description="Lightweight AI agent with direct LLM API calls",
    version="1.0.0"
)

# Request/Response models
class Message(BaseModel):
    role: str
    content: str

class AgentRequest(BaseModel):
    query: str
    model: str = "gpt-3.5-turbo"
    temperature: float = 0.7
    max_iterations: int = 5
    conversation_history: Optional[List[Message]] = None

class AgentResponse(BaseModel):
    response: str
    tool_calls: List[Dict[str, Any]]
    iterations: int

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Custom Agent Service",
        "version": "1.0.0",
        "description": "Lightweight agent with no frameworks",
        "tools": list(AVAILABLE_TOOLS.keys())
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.post("/agent", response_model=AgentResponse)
async def run_agent(request: AgentRequest):
    """
    Run the custom agent with ReAct loop
    
    The agent uses function calling to decide which tools to use,
    then iterates until it reaches a final answer.
    """
    try:
        # Validate API key
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="No API key configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY"
            )
        
        # Initialize agent
        agent = Agent(
            model=request.model,
            temperature=request.temperature,
            api_key=api_key
        )
        
        # Convert conversation history if provided
        history = []
        if request.conversation_history:
            history = [
                {"role": msg.role, "content": msg.content}
                for msg in request.conversation_history
            ]
        
        # Run agent
        result = await agent.run(
            query=request.query,
            max_iterations=request.max_iterations,
            conversation_history=history
        )
        
        return AgentResponse(
            response=result["response"],
            tool_calls=result["tool_calls"],
            iterations=result["iterations"]
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
