"""
CrewAI Team Example
Role-based agents collaborating as a team
"""
from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
from typing import Dict, Any
import os

async def run_crewai_team(query: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run a CrewAI team of role-based agents
    
    Team: Researcher → Analyst → Writer
    
    Args:
        query: User query
        config: Optional configuration
    
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
    
    # Define agents
    researcher = Agent(
        role="Research Analyst",
        goal="Gather comprehensive information about the topic",
        backstory="""You are an expert researcher with a keen eye for detail. 
        You excel at finding relevant information and identifying key facts.""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
    
    analyst = Agent(
        role="Data Analyst",
        goal="Analyze information and identify patterns and insights",
        backstory="""You are a skilled data analyst who can identify trends, 
        patterns, and draw meaningful conclusions from research data.""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
    
    writer = Agent(
        role="Content Writer",
        goal="Create clear, comprehensive responses based on analysis",
        backstory="""You are a talented writer who excels at synthesizing 
        complex information into clear, engaging content.""",
        llm=llm,
        verbose=True,
        allow_delegation=False
    )
    
    # Define tasks
    research_task = Task(
        description=f"Research the following topic thoroughly: {query}",
        agent=researcher,
        expected_output="Comprehensive research findings with key facts and sources"
    )
    
    analysis_task = Task(
        description="Analyze the research findings and identify key insights and patterns",
        agent=analyst,
        expected_output="Detailed analysis with insights and conclusions"
    )
    
    writing_task = Task(
        description="Create a comprehensive, well-written response based on the research and analysis",
        agent=writer,
        expected_output="Clear, comprehensive final answer"
    )
    
    # Create crew
    crew = Crew(
        agents=[researcher, analyst, writer],
        tasks=[research_task, analysis_task, writing_task],
        process=Process.sequential,  # Tasks run in sequence
        verbose=True
    )
    
    # Execute crew workflow
    result = crew.kickoff()
    
    return {
        "output": str(result),
        "metadata": {
            "team": ["researcher", "analyst", "writer"],
            "process": "sequential",
            "agent_type": "crewai"
        }
    }
