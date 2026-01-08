"""
Simple LangChain Agent Example
Basic agent with tools and memory
"""
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import Tool
from typing import Dict, Any
import os

# Example tools
def search_tool(query: str) -> str:
    """Search for information (mock implementation)"""
    return f"Search results for: {query}"

def calculator_tool(expression: str) -> str:
    """Calculate mathematical expressions"""
    try:
        result = eval(expression)  # In production, use a safe eval library
        return f"Result: {result}"
    except Exception as e:
        return f"Error: {str(e)}"

# Define tools
tools = [
    Tool(
        name="search",
        func=search_tool,
        description="Search for information on the internet"
    ),
    Tool(
        name="calculator",
        func=calculator_tool,
        description="Calculate mathematical expressions. Input should be a valid Python expression."
    )
]

async def run_simple_agent(query: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run a simple LangChain agent with tools
    
    Args:
        query: User query
        config: Optional configuration (temperature, model, etc.)
    
    Returns:
        Dict with output and metadata
    """
    # Initialize LLM
    model = config.get("model", "gpt-3.5-turbo")
    temperature = config.get("temperature", 0.7)
    
    llm = ChatOpenAI(
        model=model,
        temperature=temperature,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Create prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful AI assistant with access to tools."),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    # Create agent
    agent = create_openai_functions_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    
    # Run agent
    result = await agent_executor.ainvoke({"input": query})
    
    return {
        "output": result["output"],
        "metadata": {
            "model": model,
            "temperature": temperature,
            "agent_type": "simple"
        }
    }
