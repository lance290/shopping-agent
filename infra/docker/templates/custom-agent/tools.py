"""
Tool Definitions
Add your custom tools here
"""
from typing import Dict, Any
import httpx
import json

# Define available tools
AVAILABLE_TOOLS = {
    "search": {
        "description": "Search for information on the internet",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query"
                }
            },
            "required": ["query"]
        }
    },
    "calculator": {
        "description": "Calculate mathematical expressions. Use Python syntax.",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate (e.g., '2 + 2', '10 * 5')"
                }
            },
            "required": ["expression"]
        }
    },
    "weather": {
        "description": "Get current weather for a location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name or location"
                }
            },
            "required": ["location"]
        }
    }
}

# Tool implementations
async def search(query: str) -> str:
    """
    Search tool (mock implementation)
    In production, integrate with a real search API
    """
    # Mock search results
    return f"Search results for '{query}': [Mock result 1], [Mock result 2], [Mock result 3]"

async def calculator(expression: str) -> str:
    """
    Calculator tool
    WARNING: In production, use a safe expression evaluator
    """
    try:
        # Evaluate mathematical expression
        # In production: use safer alternatives like py_expression_eval or numexpr
        result = eval(expression, {"__builtins__": {}}, {})
        return f"Result: {result}"
    except Exception as e:
        return f"Error: {str(e)}"

async def weather(location: str) -> str:
    """
    Weather tool (mock implementation)
    In production, integrate with OpenWeatherMap or similar API
    """
    # Mock weather data
    return f"Weather in {location}: Sunny, 72°F (22°C), Humidity: 65%"

# Tool execution dispatcher
async def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> str:
    """
    Execute a tool by name with given arguments
    
    Args:
        tool_name: Name of the tool to execute
        arguments: Tool arguments
    
    Returns:
        Tool execution result as string
    """
    if tool_name == "search":
        return await search(arguments["query"])
    elif tool_name == "calculator":
        return await calculator(arguments["expression"])
    elif tool_name == "weather":
        return await weather(arguments["location"])
    else:
        return f"Unknown tool: {tool_name}"

# Example: Add your own custom tool
"""
To add a new tool:

1. Add to AVAILABLE_TOOLS dict:
AVAILABLE_TOOLS["my_tool"] = {
    "description": "What it does",
    "parameters": {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "..."}
        },
        "required": ["param1"]
    }
}

2. Implement the function:
async def my_tool(param1: str) -> str:
    # Your implementation
    return result

3. Add to execute_tool dispatcher:
elif tool_name == "my_tool":
    return await my_tool(arguments["param1"])
"""
