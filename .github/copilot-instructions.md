<!-- Copilot instructions for contributors and AI assistants -->
# Agent Platform — Copilot Instructions

**Purpose:** Multi-agent AI platform (built on Google ADK) where a central Orchestrator routes analysis tasks to specialized agents (Vision, CyberSecurity, RAG) via A2A protocol for architecture diagram analysis and threat assessment.

## Big Picture Architecture

**External Interface → Internal Agents Flow:**
- Frontend (`frontend/app.js`) sends JSON-RPC A2A messages to Orchestrator (port 8000, externally exposed)
- Orchestrator discovers and delegates to specialized agents over Docker internal network:
  - Vision Agent (port 8002): analyzes images, extracts components/connections
  - CyberSecurity Agent (port 8001): performs threat analysis using vision output
  - RAG Agent (port 8003): vector/graph search for knowledge retrieval
- All agents built with `google.adk.agents.Agent` + `google.adk.models.LiteLlm`

**Key Pattern:** Each agent has a root agent + sub-agents (e.g., vision_agent.py defines root_agent with visual_analyzer sub-agent). See `agents/orchestrator/modules/orchestrator_core.py` for discovery logic.

## Developer Workflows

**Docker Compose (recommended for integration testing):**
```powershell
docker-compose up -d          # Start all containers
docker-compose logs -f orchestrator   # Watch startup
```

**Local dev (shared venv at repo root):**
```powershell
# Windows: activate.bat or .\venv\Scripts\Activate.ps1
# Run agents in separate terminals
python -m agents.orchestrator.orchestrator   # Port 8000
python agents/vision/vision_agent.py          # Port 8002
python agents/cybersecurity/cybersecurity_agent.py  # Port 8001
```

**Frontend:**
```powershell
cd frontend && npm install && npm start  # http://localhost:3000
```

## Critical Conventions & Patterns

**1. LiteLLM Usage (non-negotiable):**
- ✅ Always: `from google.adk.models import LiteLlm` + `llm = LiteLlm(model=os.getenv("LLM_MODEL", "openai/gpt-5-mini"))`
- ✅ Embeddings: `litellm.embedding(model="text-embedding-3-small", input="text")`
- ✅ Planner: `from google.adk.planners.built_in_planner import BuiltInPlanner` for native model reasoning
- ❌ Never: `from openai import OpenAI`, `from anthropic import Anthropic`, direct SDK imports

**1a. Extended Thinking with BuiltInPlanner:**
- All agents use `BuiltInPlanner` with `ThinkingConfig` to leverage model's built-in reasoning
- Configuration via environment: `THINKING_BUDGET=1024`, `INCLUDE_THOUGHTS=true`
- Example:
  ```python
  from google.genai import types
  thinking_config = types.ThinkingConfig(
      include_thoughts=True,  # Show reasoning steps
      thinking_budget=1024    # Token budget for thinking
  )
  planner = BuiltInPlanner(thinking_config=thinking_config)
  ```

**2. Agent Discovery & Routing:**
- Orchestrator discovers agents via environment variables (e.g., `VISION_AGENT_ENDPOINT=http://vision-agent:8002`)
- Agent discovery happens in `OrchestratorCore.__init__()` with retry logic (max 5 attempts, 5s delays)
- Sub-agents are added via `workflow_agent.sub_agents = [discovered_agents]` after discovery
- Tools attached to agents are callable via LLM instructions (see cybersecurity_agent.py line 40)

**3. Database & Async Patterns:**
- PostgreSQL async URL must be `postgresql+psycopg://` (not plain `postgresql://`)
- DatabaseSessionService handles session persistence (imported from `google.adk.sessions`)
- Artifact service defaults to file-based (`FileArtifactService(root_dir=./my_artifacts)`)

**4. A2A File Upload (custom extension in orchestrator):**
- Frontend chunks files (1MB max) and calls `artifactUpload/{start|append|finish}` methods
- See `agents/orchestrator/a2aExtensions/A2AUploadMiddleware.py` for implementation
- Uploads scoped to session or user; memory cleanup on timeout

**5. Data Flow Pattern:**
- Vision agent outputs structured JSON (components, connections, zones, inferred tech)
- CyberSecurity agent receives this JSON and calls `architecture_analysis.analyze_architecture_security(data)`
- Sub-agents inherit parent agent's tools; delegate via `planner=BuiltInPlanner(thinking_config=thinking_config)`

## Integration Points

**Environment Variables (required for local testing):**
```
# LLM
OPENAI_API_KEY=sk-... or GOOGLE_API_KEY=AIza...
LLM_MODEL=openai/gpt-5.2-reasoning  # Orchestrator uses this
EMBEDDING_MODEL=text-embedding-3-small

# Extended Thinking (BuiltInPlanner)
THINKING_BUDGET=1024  # Token budget for model reasoning
INCLUDE_THOUGHTS=true  # Show reasoning steps in responses

# Database
DATABASE_URL=postgresql+psycopg://admin:admin123@localhost:5432/agent_platform
NEO4J_URI=bolt://neo4j:7687 (RAG only)
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password

# Memory
OM_BASE_URL=http://openmemory:8080
OM_API_KEY=...

# Artifacts
ARTIFACT_ROOT_DIR=/artifacts
```

**Agent Endpoints (set in environment for discovery):**
- `VISION_AGENT_ENDPOINT=http://vision-agent:8002`
- `CYBERSECURITY_AGENT_ENDPOINT=http://cybersecurity-agent:8001`
- `RAG_AGENT_ENDPOINT=http://rag-agent:8003`

## Common Pitfalls & Debugging

- **Agents don't connect:** Check Docker network and endpoint env vars. Verify with `docker-compose logs -f orchestrator`.
- **LLM errors:** Verify `LLM_MODEL` format matches LiteLLM syntax (e.g., `openai/gpt-5.2-reasoning`), API keys set, rate limits.
- **Database URL conversion:** Always convert `postgresql://` to `postgresql+psycopg://` for async support (see orchestrator.py line 32).
- **Tool not called:** Ensure tool is in agent's `tools=[]` list and instruction explicitly references it.

## Key Files Reference

- `agents/orchestrator/orchestrator.py` — A2A routing setup, session/artifact services, agent discovery
- `agents/orchestrator/modules/orchestrator_core.py` — Agent registry with retry logic, sub-agent assignment
- `agents/*_agent.py` — Root agent definition with `Agent()` + ADK-specific instructions and tools
- `agents/*/modules/*.py` — Analysis logic (e.g., `vision_analysis.py`, `architecture_analysis.py`)
- `frontend/app.js` — A2A message construction, JSON-RPC calls, file chunking (A2AUploadService)
- `docker-compose.yml` — Container networking, environment variable injection, port mappings

