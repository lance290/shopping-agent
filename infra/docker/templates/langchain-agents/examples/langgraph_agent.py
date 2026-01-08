"""
LangGraph Multi-Agent Example
Complex workflow with state management and conditional routing
"""
from typing import TypedDict, Annotated, Sequence, Dict, Any
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage
import operator
import os

# Define agent state
class AgentState(TypedDict):
    messages: Annotated[Sequence[HumanMessage | AIMessage], operator.add]
    next: str
    research_done: bool
    analysis_done: bool
    final_answer: str

# Initialize LLM
def get_llm(config: Dict[str, Any]):
    model = config.get("model", "gpt-3.5-turbo")
    temperature = config.get("temperature", 0.7)
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        api_key=os.getenv("OPENAI_API_KEY")
    )

# Node: Research
async def research_node(state: AgentState, config: Dict[str, Any]) -> AgentState:
    """Research information related to the query"""
    llm = get_llm(config)
    
    messages = state["messages"]
    query = messages[-1].content if messages else ""
    
    prompt = f"Research and gather information about: {query}"
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    
    return {
        **state,
        "messages": [AIMessage(content=f"Research: {response.content}")],
        "research_done": True,
        "next": "analyze"
    }

# Node: Analysis
async def analyze_node(state: AgentState, config: Dict[str, Any]) -> AgentState:
    """Analyze the researched information"""
    llm = get_llm(config)
    
    research_content = state["messages"][-1].content
    prompt = f"Analyze this information and provide insights:\n{research_content}"
    
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    
    return {
        **state,
        "messages": [AIMessage(content=f"Analysis: {response.content}")],
        "analysis_done": True,
        "next": "synthesize"
    }

# Node: Synthesis
async def synthesize_node(state: AgentState, config: Dict[str, Any]) -> AgentState:
    """Synthesize research and analysis into final answer"""
    llm = get_llm(config)
    
    # Get research and analysis
    messages = state["messages"]
    research = messages[-2].content if len(messages) >= 2 else ""
    analysis = messages[-1].content if len(messages) >= 1 else ""
    
    prompt = f"""Based on the following research and analysis, provide a comprehensive answer:
    
Research: {research}
Analysis: {analysis}

Provide a clear, concise final answer."""
    
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    
    return {
        **state,
        "messages": [AIMessage(content=response.content)],
        "final_answer": response.content,
        "next": "end"
    }

# Routing logic
def route_after_research(state: AgentState) -> str:
    """Determine next step after research"""
    return state.get("next", "analyze")

def route_after_analysis(state: AgentState) -> str:
    """Determine next step after analysis"""
    return state.get("next", "synthesize")

def route_after_synthesis(state: AgentState) -> str:
    """Determine if we're done"""
    return END

async def run_langgraph_agent(query: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run a LangGraph multi-agent workflow
    
    Workflow: Research → Analyze → Synthesize
    
    Args:
        query: User query
        config: Optional configuration
    
    Returns:
        Dict with output and metadata
    """
    # Create graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("research", lambda state: research_node(state, config))
    workflow.add_node("analyze", lambda state: analyze_node(state, config))
    workflow.add_node("synthesize", lambda state: synthesize_node(state, config))
    
    # Set entry point
    workflow.set_entry_point("research")
    
    # Add edges
    workflow.add_conditional_edges("research", route_after_research)
    workflow.add_conditional_edges("analyze", route_after_analysis)
    workflow.add_conditional_edges("synthesize", route_after_synthesis)
    
    # Compile graph
    app = workflow.compile()
    
    # Run workflow
    initial_state = {
        "messages": [HumanMessage(content=query)],
        "next": "research",
        "research_done": False,
        "analysis_done": False,
        "final_answer": ""
    }
    
    final_state = await app.ainvoke(initial_state)
    
    return {
        "output": final_state.get("final_answer", ""),
        "metadata": {
            "workflow": "research -> analyze -> synthesize",
            "steps_completed": sum([
                final_state.get("research_done", False),
                final_state.get("analysis_done", False)
            ]),
            "agent_type": "langgraph"
        }
    }
