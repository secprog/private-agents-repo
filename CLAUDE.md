# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A multi-agent AI platform for analyzing architecture diagrams and performing security assessments. Built on Google ADK (Agent Development Kit) with A2A (Agent-to-Agent) protocol.

**Core Purpose**: Orchestrate specialized agents to analyze architecture diagrams using computer vision, extract security threats, and provide actionable recommendations.

## Architecture

### Agent Hierarchy

```
Frontend (Express.js + Vanilla JS)
    ↓ A2A Protocol (HTTP)
Orchestrator Agent (port 8000)
    ↓ A2A Protocol (Internal Docker Network)
    ├── Vision Agent (port 8002)
    ├── CyberSecurity Agent (port 8001)
    └── RAG Agent (port 8003)
```

**Security Model**: Only the Orchestrator is exposed externally. All other agents communicate via Docker internal network.

### Agent Structure

All agents follow the same pattern (see `agents/vision/vision_agent.py` as reference):

```
agents/[agent_name]/
├── [agent_name]_agent.py     # Main entry point with ADK Agent setup
├── [agent_name]_analysis.py  # Core analysis logic
├── models.py                  # Pydantic schemas
├── prompts.py                 # System prompts (if needed)
├── requirements.txt
└── Dockerfile
```

**Key Pattern**: Each agent has a root agent that delegates to specialized sub-agents using ADK's hierarchical agent structure.

### Critical Dependencies

- **Google ADK SDK**: Core agent framework from `git+https://github.com/secprog/adk-python@main`
- **LiteLLM**: ALL LLM calls (including embeddings) go through LiteLLM - never use OpenAI/Anthropic SDKs directly
- **A2A Protocol**: All agent communication uses A2A with JSON-RPC 2.0
- **PostgreSQL + pgvector**: Session storage and vector operations
- **Neo4j**: RAG agent graph database (required for RAG agent)

## Development Commands

### Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f orchestrator
docker-compose logs -f vision-agent

# Rebuild after changes
docker-compose up -d --build

# Stop all services
docker-compose down
```

### Local Development

```bash
# Each agent can run independently
cd agents/orchestrator
python orchestrator.py

cd agents/vision
python vision_agent.py

cd agents/cybersecurity
python cybersecurity_agent.py
```

**Port Assignments**:
- Orchestrator: 8000
- CyberSecurity: 8001
- Vision: 8002
- RAG: 8003
- Frontend: 3000
- PostgreSQL: 5432
- OpenMemory: 8080

## LLM Integration (CRITICAL)

### Always Use LiteLLM

**Never** import or use:
- ❌ `from openai import OpenAI`
- ❌ `from anthropic import Anthropic`
- ❌ `from google.genai import Client`
- ❌ `langchain_openai` or any LangChain LLM wrappers

**Always** use:
- ✅ `from google.adk.models import LiteLlm`
- ✅ `litellm.embedding()` for embeddings

### Example LLM Usage

```python
from google.adk.models import LiteLlm
from google.adk.models.llm_request import LlmRequest
from google.genai import types
import os

# Initialize LLM
llm = LiteLlm(model=os.getenv("LLM_MODEL", "openai/gpt-5-mini"))

# Create request
llm_request = LlmRequest(
    model=llm.model,
    contents=[
        types.Content(
            role="user",
            parts=[types.Part.from_text(text="Your prompt here")]
        )
    ],
    config=types.GenerateContentConfig(
        system_instruction="System instructions",
        max_output_tokens=50000,
        response_mime_type="application/json"
    )
)

# For structured output
llm_request.set_output_schema(YourPydanticModel)

# Call LLM
async for response in llm.generate_content_async(llm_request, stream=False):
    # Process response
```

### Example Embeddings Usage

```python
import litellm

# Generate embeddings
response = litellm.embedding(
    model="text-embedding-3-small",
    input="Your text here"
)
embedding = response.data[0]['embedding']
```

## Environment Configuration

Key environment variables (`.env` file):

```bash
# LLM Configuration
LLM_MODEL=openai/gpt-5.2-reasoning  # Used by orchestrator
EMBEDDING_MODEL=text-embedding-3-small  # Used for embeddings
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AIza...

# Database
DATABASE_URL=postgresql://admin:admin123@postgres:5432/agent_platform
NEO4J_URI=bolt://neo4j:7687  # For RAG agent
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
NEO4J_DATABASE=neo4j

# Artifact Storage
ARTIFACT_SERVICE_TYPE=FILE
ARTIFACT_ROOT_DIR=/artifacts

# OpenMemory (Cognitive Memory)
OM_BASE_URL=http://openmemory:8080
OM_API_KEY=...
```

## A2A Protocol Implementation

### File Upload Extension

The orchestrator includes a custom A2A extension for file uploads (`agents/orchestrator/a2aExtensions/A2AUploadMiddleware.py`):

**Methods**:
- `artifactUpload/start` - Begin chunked upload
- `artifactUpload/append` - Upload chunk
- `artifactUpload/finish` - Complete upload
- `artifactUpload/abort` - Cancel upload

**Features**:
- Chunked transfer (max 512KB per chunk)
- SHA256 integrity verification
- Session-scoped and user-scoped artifacts
- Memory cleanup for abandoned uploads

### Agent Discovery

The orchestrator dynamically discovers agents by:
1. Querying `.well-known/agent-card.json` endpoints
2. Building a registry of available agents
3. Creating `RemoteA2aAgent` instances for delegation

See `agents/orchestrator/modules/orchestrator_core.py` for implementation.

## Agent-Specific Notes

### Vision Agent

**Purpose**: Analyze architecture diagrams using computer vision

**Key Tools**:
- `run_core_analysis_parallel` - Parallel analysis of components/connections/zones
- `detect_trust_boundaries` - Security boundary detection
- `export_to_plantuml/mermaid/drawio` - Export to diagram formats

**Models**: Extensive Pydantic schemas in `models.py` (VisualComponent, VisualConnection, etc.)

### CyberSecurity Agent

**Purpose**: Security analysis of architecture diagrams

**Key Function**: `analyze_architecture_security()` - Takes visual analysis JSON and produces security assessment (threats, vulnerabilities, attack paths, recommendations)

**Input**: Receives comprehensive visual data from Vision agent (components, connections, zones, trust boundaries, technologies)

### RAG Agent

**Purpose**: Document retrieval and knowledge extraction from Neo4j

**Key Tools**:
- `vector_search` - Semantic similarity search
- `graph_search` - Natural language to Cypher
- `hybrid_search` - Combined vector + lexical with RRF
- `detect_entities` - LLM-based entity extraction
- `graph_based_retrieval` - Entity relationship retrieval

**Database**: Requires Neo4j with vector indexes

### Orchestrator Agent

**Purpose**: Route tasks to specialized agents

**Key Features**:
- Dynamic agent discovery with retry mechanism
- Session management with PostgreSQL
- Memory integration with OpenMemory
- LLM_MODEL configurable via environment (uses gpt-5.2-reasoning by default)

## Database Sessions

All agents use `DatabaseSessionService` with async PostgreSQL:

```python
# Convert postgresql:// to postgresql+psycopg:// for async support
db_url = os.getenv("DATABASE_URL")
if db_url.startswith("postgresql://") and "+psycopg" not in db_url:
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

session_service = DatabaseSessionService(db_url=db_url)
```

## Artifact Services

**Vision Agent**: Uses `FileArtifactService` for persistent image storage
**CyberSecurity Agent**: Uses `FileArtifactService` for diagram files
**RAG Agent**: Uses `InMemoryArtifactService` (no file storage needed)

## Adding New Agents

Follow this structure:

1. Create directory: `agents/new_agent/`
2. Create main file: `new_agent_agent.py` (follow vision_agent.py pattern)
3. Create analysis file: `new_agent_analysis.py` (core logic)
4. Create models: `models.py` (Pydantic schemas)
5. Add to docker-compose.yml with internal networking
6. Set agent endpoint in `.env`: `NEW_AGENT_ENDPOINT=http://new-agent:PORT`

**Critical**: New agents must:
- Use LiteLLM for all LLM operations
- Implement ADK Agent structure
- Support A2A protocol via `to_a2a()`
- Include `.well-known/agent-card.json` endpoint

## Testing

```bash
# Run agent locally
cd agents/vision
python vision_agent.py

# Test with Docker Compose
docker-compose up -d
docker-compose logs -f vision-agent

# Check agent health
curl http://localhost:8002/.well-known/agent-card.json
```

## Common Pitfalls

1. **Never use OpenAI/Anthropic SDKs directly** - Always use LiteLLM
2. **Never use LangChain** - Use Google ADK and direct database drivers
3. **Agent discovery requires retry logic** - Agents may not start simultaneously
4. **Session URLs need async driver** - Convert `postgresql://` to `postgresql+psycopg://`
5. **Artifact services differ by agent** - Vision/CyberSecurity use File, RAG uses InMemory
6. **Only orchestrator exposed externally** - Internal agents use Docker network

## Key Files

- `agents/orchestrator/modules/orchestrator_core.py` - Agent discovery and routing
- `agents/vision/vision_analysis.py` - Computer vision implementation
- `agents/cybersecurity/modules/architecture_analysis.py` - Security analysis
- `agents/rag/rag_analysis.py` - Document retrieval implementation
- `docker-compose.yml` - Service orchestration and networking
- `.env` - Environment configuration
