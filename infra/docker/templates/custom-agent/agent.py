"""
Custom Agent Implementation
Simple ReAct (Reasoning + Acting) loop with function calling
"""
from typing import List, Dict, Any
from openai import AsyncOpenAI
import json

from tools import AVAILABLE_TOOLS, execute_tool

class Agent:
    """Lightweight agent with ReAct loop"""
    
    def __init__(self, model: str, temperature: float, api_key: str):
        self.model = model
        self.temperature = temperature
        self.client = AsyncOpenAI(api_key=api_key)
        self.tools = self._format_tools_for_openai()
    
    def _format_tools_for_openai(self) -> List[Dict[str, Any]]:
        """Convert tools to OpenAI function calling format"""
        return [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool["description"],
                    "parameters": tool["parameters"]
                }
            }
            for name, tool in AVAILABLE_TOOLS.items()
        ]
    
    async def run(
        self,
        query: str,
        max_iterations: int = 5,
        conversation_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Run the agent with ReAct loop
        
        Loop:
        1. Thought: Agent reasons about what to do
        2. Action: Agent calls a tool (if needed)
        3. Observation: Tool returns result
        4. Repeat until final answer
        
        Args:
            query: User query
            max_iterations: Max number of reasoning loops
            conversation_history: Previous messages
        
        Returns:
            Dict with response, tool_calls, and iterations
        """
        # Initialize conversation
        messages = conversation_history or []
        messages.append({"role": "user", "content": query})
        
        tool_calls_log = []
        
        for iteration in range(max_iterations):
            # Call LLM
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools,
                temperature=self.temperature
            )
            
            message = response.choices[0].message
            
            # Check if agent wants to use tools
            if message.tool_calls:
                # Agent decided to call tools
                messages.append({
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in message.tool_calls
                    ]
                })
                
                # Execute each tool call
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    # Execute tool
                    result = await execute_tool(function_name, function_args)
                    
                    # Log tool call
                    tool_calls_log.append({
                        "tool": function_name,
                        "arguments": function_args,
                        "result": result
                    })
                    
                    # Add tool result to conversation
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(result)
                    })
                
                # Continue loop to get agent's next response
                continue
            
            # Agent provided final answer (no tool calls)
            if message.content:
                return {
                    "response": message.content,
                    "tool_calls": tool_calls_log,
                    "iterations": iteration + 1
                }
        
        # Max iterations reached
        return {
            "response": "Maximum iterations reached without conclusive answer.",
            "tool_calls": tool_calls_log,
            "iterations": max_iterations
        }
