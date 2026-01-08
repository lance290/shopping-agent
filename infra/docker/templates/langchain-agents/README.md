# LangChain/LangGraph/CrewAI Agent Service

Production-ready AI agent service supporting multiple agent frameworks and patterns. Choose the right approach for your use case.

---

## Features

- ✅ **LangChain** - Basic agents with tools and memory
- ✅ **LangGraph** - Multi-agent workflows with state management
- ✅ **CrewAI** - Role-based agent teams
- ✅ **FastAPI** - Production HTTP server
- ✅ **Multi-LLM Support** - OpenAI, Anthropic, Google
- ✅ **Self-hosted** - No external dependencies required
- ✅ **Docker optimized** - Multi-stage build, non-root user

---

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set API key
export OPENAI_API_KEY=sk-...

# Run server
uvicorn main:app --reload

# Test
curl -X POST http://localhost:8080/agent \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the capital of France?", "agent_type": "simple"}'
```

### Docker

```bash
# Build
docker build -t agent-service .

# Run
docker run -p 8080:8080 \
  -e OPENAI_API_KEY=sk-... \
  agent-service

# Test
curl http://localhost:8080/health
```

---

## Agent Types

### 1. Simple Agent (Basic LangChain)

**Use Case:** Basic question-answering with tools

**Example:**
```json
{
  "query": "What is 25 * 4?",
  "agent_type": "simple",
  "config": {
    "model": "gpt-3.5-turbo",
    "temperature": 0.7
  }
}
```

**Features:**
- Function calling
- Tool usage (search, calculator)
- Conversation memory
- Fast and lightweight

**When to Use:**
- Simple Q&A
- Single-step reasoning
- Tool integration
- Low latency requirements

---

### 2. LangGraph Agent (Multi-Step)

**Use Case:** Complex multi-step reasoning with state management

**Example:**
```json
{
  "query": "Analyze the impact of AI on healthcare",
  "agent_type": "langgraph",
  "config": {
    "model": "gpt-4",
    "temperature": 0.3
  }
}
```

**Workflow:**
```
Research → Analyze → Synthesize
```

**Features:**
- State management
- Conditional routing
- Multi-step reasoning
- Cyclic workflows
- Checkpointing

**When to Use:**
- Research tasks
- Multi-step analysis
- Complex reasoning
- Need to inspect intermediate steps

---

### 3. CrewAI Team (Role-Based Collaboration)

**Use Case:** Team of specialized agents working together

**Example:**
```json
{
  "query": "Create a market analysis report for EV industry",
  "agent_type": "crewai",
  "config": {
    "model": "gpt-4",
    "temperature": 0.5
  }
}
```

**Team:**
- **Researcher** - Gathers information
- **Analyst** - Analyzes data and identifies patterns
- **Writer** - Creates comprehensive response

**Features:**
- Role specialization
- Sequential or parallel execution
- Delegation between agents
- Task dependencies

**When to Use:**
- Complex research projects
- Need specialized expertise
- Multi-perspective analysis
- Team-like collaboration

---

## Architecture

### Project Structure

```
langchain-agents/
├── Dockerfile              # Production build
├── requirements.txt        # Dependencies
├── main.py                 # FastAPI server
├── .env.example            # Environment variables
├── examples/
│   ├── simple_agent.py    # Basic LangChain agent
│   ├── langgraph_agent.py # Multi-step workflow
│   └── crewai_team.py     # Role-based team
├── tools/                  # Custom tools (add yours)
└── prompts/                # Prompt templates (add yours)
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Service info |
| `/health` | GET | Health check |
| `/agent` | POST | Run agent |
| `/docs` | GET | Swagger UI |

---

## Configuration

### Environment Variables

```bash
# Required: LLM API Key
OPENAI_API_KEY=sk-...          # OpenAI
ANTHROPIC_API_KEY=sk-ant-...   # Anthropic (alternative)
GOOGLE_API_KEY=...             # Google Gemini (alternative)

# Optional: Observability
LANGCHAIN_TRACING_V2=true      # Enable LangSmith tracing
LANGCHAIN_API_KEY=...          # LangSmith API key
LANGCHAIN_PROJECT=my-project   # Project name

# Optional: Vector Store
QDRANT_URL=http://localhost:6333
CHROMA_HOST=localhost

# Server
PORT=8080
```

### Model Configuration

Supported models:
- **OpenAI**: `gpt-4`, `gpt-3.5-turbo`
- **Anthropic**: `claude-3-opus`, `claude-3-sonnet`
- **Google**: `gemini-pro`

---

## Adding Custom Tools

### Example: Weather Tool

```python
# tools/weather.py
from langchain.tools import Tool
import requests

def get_weather(location: str) -> str:
    """Get current weather for a location"""
    # Call weather API
    response = requests.get(f"https://api.weather.com/{location}")
    return response.json()

weather_tool = Tool(
    name="weather",
    func=get_weather,
    description="Get current weather for a location"
)
```

### Register in Agent

```python
# examples/simple_agent.py
from tools.weather import weather_tool

tools = [
    weather_tool,
    # ... other tools
]
```

---

## Vector Store Integration

### Add RAG Capabilities

```python
# Install vector store
pip install chromadb  # or qdrant-client, pgvector

# Update simple_agent.py
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings

# Create vector store
vectorstore = Chroma(
    embedding_function=OpenAIEmbeddings(),
    persist_directory="./chroma_db"
)

# Add retrieval tool
from langchain.tools import create_retriever_tool

retriever_tool = create_retriever_tool(
    vectorstore.as_retriever(),
    name="knowledge_base",
    description="Search internal knowledge base"
)

tools.append(retriever_tool)
```

---

## Advanced: Human-in-the-Loop (HITL)

### LangGraph with HITL

```python
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import create_react_agent

# Add checkpointing
memory = SqliteSaver.from_conn_string(":memory:")

app = create_react_agent(
    llm,
    tools,
    checkpointer=memory
)

# Run with interrupts
config = {"configurable": {"thread_id": "1"}}
for chunk in app.stream({"messages": [query]}, config, stream_mode="values"):
    # Interrupt for human input
    if chunk.get("needs_human_input"):
        human_response = input("Your input: ")
        app.update_state(config, {"human_input": human_response})
```

---

## Production Deployment

### Railway

```bash
# Add railway.json
{
  "build": {
    "builder": "DOCKERFILE"
  },
  "deploy": {
    "restartPolicyType": "ON_FAILURE"
  }
}

# Deploy
railway up
```

### GCP Cloud Run

```bash
# Build and push
gcloud builds submit --tag gcr.io/PROJECT_ID/agent-service

# Deploy
gcloud run deploy agent-service \
  --image gcr.io/PROJECT_ID/agent-service \
  --platform managed \
  --set-env-vars OPENAI_API_KEY=$OPENAI_API_KEY
```

### Environment Variables in Production

**DO NOT hardcode API keys**. Use:
- Railway: Environment variables in dashboard
- GCP: Secret Manager
- AWS: Parameter Store

---

## Performance & Scaling

### Optimization Tips

1. **Use GPT-3.5 for simple tasks** (10x faster, 10x cheaper than GPT-4)
2. **Cache embeddings** for RAG applications
3. **Batch requests** when possible
4. **Stream responses** for better UX
5. **Use async/await** (already implemented)

### Scaling

- **Horizontal**: Run multiple instances behind load balancer
- **Vertical**: Increase CPU/memory for concurrent requests
- **Caching**: Add Redis for conversation memory
- **Queue**: Add Celery for long-running tasks

---

## Cost Optimization

### Token Usage by Agent Type

| Agent Type | Avg Tokens | Est. Cost (GPT-4) |
|------------|-----------|-------------------|
| Simple | 500-1000 | $0.01-0.03 |
| LangGraph | 2000-5000 | $0.06-0.15 |
| CrewAI | 5000-15000 | $0.15-0.45 |

**Tips:**
- Use GPT-3.5 for research/analysis steps
- Only use GPT-4 for final synthesis
- Set token limits: `max_tokens=500`
- Cache repeated queries

---

## Observability

### Option 1: LangSmith (Official, Paid)

```bash
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_API_KEY=...
export LANGCHAIN_PROJECT=my-project
```

### Option 2: Self-Hosted (Free)

**Phoenix by Arize AI** (Open Source):
```bash
# Run Phoenix locally
docker run -p 6006:6006 arizephoenix/phoenix:latest

# Configure in code
from phoenix.trace.langchain import LangChainInstrumentor
LangChainInstrumentor().instrument()
```

---

## Testing

### Unit Tests

```bash
# Install pytest
pip install pytest pytest-asyncio

# Run tests
pytest tests/
```

### Example Test

```python
# tests/test_simple_agent.py
import pytest
from examples.simple_agent import run_simple_agent

@pytest.mark.asyncio
async def test_simple_agent():
    result = await run_simple_agent(
        "What is 2+2?",
        {"model": "gpt-3.5-turbo"}
    )
    assert "4" in result["output"]
```

---

## Troubleshooting

### Issue: "No API key configured"

**Fix:** Set environment variable:
```bash
export OPENAI_API_KEY=sk-...
```

### Issue: "Rate limit exceeded"

**Fix:** Add retry logic or upgrade API plan

### Issue: "Agent takes too long"

**Fixes:**
- Use faster model (GPT-3.5 instead of GPT-4)
- Reduce max_tokens
- Simplify agent workflow
- Use caching

### Issue: "Out of memory"

**Fix:** Reduce number of concurrent requests or increase container memory

---

## Security Best Practices

1. **Never commit API keys** - Use `.env` file (in `.gitignore`)
2. **Validate user input** - Prevent prompt injection
3. **Rate limiting** - Add rate limits per user/IP
4. **Timeout requests** - Set max execution time
5. **Sandbox execution** - Don't allow arbitrary code execution
6. **Audit logs** - Log all agent actions

### Input Validation Example

```python
from fastapi import HTTPException

@app.post("/agent")
async def run_agent(request: AgentRequest):
    # Validate query length
    if len(request.query) > 5000:
        raise HTTPException(400, "Query too long")
    
    # Sanitize input
    query = request.query.strip()
    
    # ... rest of code
```

---

## Comparison: When to Use What

| Use Case | Simple | LangGraph | CrewAI |
|----------|--------|-----------|--------|
| Basic Q&A | ✅ Best | ❌ Overkill | ❌ Overkill |
| Tool usage | ✅ Best | ✅ Good | ⚠️ Limited |
| Multi-step reasoning | ⚠️ Limited | ✅ Best | ✅ Good |
| Research tasks | ❌ | ✅ Good | ✅ Best |
| Role specialization | ❌ | ⚠️ Manual | ✅ Best |
| Latency | 🚀 Fast | 🐢 Slow | 🐢 Very Slow |
| Cost | 💵 Low | 💵💵 Medium | 💵💵💵 High |

---

## Next Steps

1. **Add more tools** - Create custom tools in `tools/`
2. **Add RAG** - Integrate vector database
3. **Add memory** - Persist conversation history
4. **Add streaming** - Stream responses for better UX
5. **Add authentication** - Protect endpoints
6. **Add monitoring** - Use LangSmith or Phoenix

---

## Resources

- **LangChain Docs**: https://python.langchain.com/docs/
- **LangGraph Docs**: https://langchain-ai.github.io/langgraph/
- **CrewAI Docs**: https://docs.crewai.com/
- **LangSmith**: https://smith.langchain.com/
- **Phoenix (OSS)**: https://phoenix.arize.com/

---

## License

Part of the framework, inherits framework license.
