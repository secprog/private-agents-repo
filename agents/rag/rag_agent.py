"""
RAG Agent - Main entry point using ADK SDK
"""

import os
import logging
from google.adk.auth.credential_service.in_memory_credential_service import (
    InMemoryCredentialService,
)
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions.database_session_service import DatabaseSessionService
from google.adk.apps.app import App, ResumabilityConfig
from google.adk.artifacts import InMemoryArtifactService
import uvicorn
from google.adk.planners.built_in_planner import BuiltInPlanner
from fastapi.middleware.cors import CORSMiddleware
from google.adk.tools.long_running_tool import LongRunningFunctionTool
from google.adk.models import LiteLlm
from google.adk.agents import Agent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.genai import types
from rag_analysis import RAGAnalysis

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

agent_name = "rag-agent"
agent_identifier = agent_name.replace("-", "_")

# Thinking configuration for extended reasoning
THINKING_BUDGET = int(os.getenv("THINKING_BUDGET", "1024"))
INCLUDE_THOUGHTS = os.getenv("INCLUDE_THOUGHTS", "true").lower() == "true"

# Create thinking config for planners
thinking_config = types.ThinkingConfig(
    include_thoughts=INCLUDE_THOUGHTS,
    thinking_budget=THINKING_BUDGET
)

# Use postgresql+psycopg:// for async driver (psycopg 3.x)
db_url = os.getenv(
    "DATABASE_URL", "postgresql://admin:admin123@localhost:5432/agent_platform"
)
# Convert postgresql:// to postgresql+psycopg:// for async support
if db_url.startswith("postgresql://") and "+psycopg" not in db_url:
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

session_service = DatabaseSessionService(db_url=db_url)
rag_analysis = RAGAnalysis()

# Create RAG analysis agent
rag_analyzer_agent = Agent(
    name="rag_analyzer",
    description="Specialized agent for retrieval-augmented generation and document search",
    model=LiteLlm(model=os.getenv("LLM_MODEL", "openai/gpt-5-mini")),
    instruction="""You are an advanced RAG (Retrieval-Augmented Generation) agent specialized in document retrieval and knowledge extraction.

You have access to the following tools:

SEARCH TOOLS:
1. vector_search - Search for documents using semantic similarity
2. graph_search - Search structured data using graph queries
3. detect_entities - Extract named entities from text

RETRIEVAL TOOLS:
4. hybrid_search - Combine vector and lexical search for better results
5. graph_based_retrieval - Retrieve documents based on entity relationships

Use these tools to:
- Answer questions based on retrieved documents
- Extract relevant information from knowledge bases
- Find semantically similar content
- Identify entities and relationships

When the user asks a question:
1. First, use detect_entities to extract key entities from the question
2. Use hybrid_search or vector_search to find relevant documents
3. If needed, use graph_based_retrieval to find related information
4. Synthesize the information to provide a comprehensive answer

IMPORTANT:
- Always cite your sources when providing information
- If information is not found, clearly state that
- Prefer hybrid_search over simple vector_search for better results
""",
    tools=[
        LongRunningFunctionTool(func=rag_analysis.vector_search),
        LongRunningFunctionTool(func=rag_analysis.graph_search),
        LongRunningFunctionTool(func=rag_analysis.detect_entities),
        LongRunningFunctionTool(func=rag_analysis.hybrid_search),
        LongRunningFunctionTool(func=rag_analysis.graph_based_retrieval),
    ],
    planner=BuiltInPlanner(thinking_config=thinking_config),
)

# Create A2A server using ADK SDK directly
root_agent = Agent(
    name=agent_identifier,
    description="Specialized agent for retrieval-augmented generation and knowledge extraction from documents.",
    model=LiteLlm(model=os.getenv("LLM_MODEL", "openai/gpt-5-mini")),
    instruction="""You are a RAG agent coordinator. Delegate all retrieval and search tasks to the rag_analyzer sub-agent.

Workflow:
- For document search and retrieval: Delegate to rag_analyzer
- For entity extraction and knowledge graph queries: Delegate to rag_analyzer
- You do not touch the sub-agent's input or output, you only delegate to them

IMPORTANT GUARDRAILS:
- If the user is just saying hello or asking a general question NOT related to searching documents, YOU should respond directly
- ONLY delegate to the analyzer when the user wants to search, retrieve, or extract information from documents
""",
    sub_agents=[rag_analyzer_agent],
    planner=BuiltInPlanner(thinking_config=thinking_config),
)

rag_app = App(
    name=agent_identifier,
    root_agent=root_agent,
    resumability_config=ResumabilityConfig(is_resumable=True),
)

app = to_a2a(
    agent=root_agent,
    port=8003,
    host=agent_name,
    protocol="http",
    runner=Runner(
        app=rag_app,
        artifact_service=InMemoryArtifactService(),
        session_service=session_service,
        memory_service=InMemoryMemoryService(),
        credential_service=InMemoryCredentialService(),
    ),
)

# Add CORS middleware to A2A app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    uvicorn.run(app)
