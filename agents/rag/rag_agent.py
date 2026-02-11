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


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} env-var missing")
    return value


def _require_positive_int_env(name: str) -> int:
    value = _require_env(name)
    try:
        parsed = int(value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer, got: {value}") from exc
    if parsed <= 0:
        raise RuntimeError(f"{name} must be > 0, got: {parsed}")
    return parsed


def _require_bool_env(name: str) -> bool:
    value = _require_env(name).strip().lower()
    if value in {"1", "true", "yes"}:
        return True
    if value in {"0", "false", "no"}:
        return False
    raise RuntimeError(
        f"{name} must be a boolean string: one of true/false/1/0/yes/no (got: {value})"
    )


# Thinking configuration for extended reasoning
THINKING_BUDGET = _require_positive_int_env("THINKING_BUDGET")
INCLUDE_THOUGHTS = _require_bool_env("INCLUDE_THOUGHTS")
LLM_MODEL = _require_env("LLM_MODEL")

# Create thinking config for planners
thinking_config = types.ThinkingConfig(
    include_thoughts=INCLUDE_THOUGHTS,
    thinking_budget=THINKING_BUDGET
)

# Use postgresql+psycopg:// for async driver (psycopg 3.x)
db_url = _require_env("DATABASE_URL")
# Convert postgresql:// to postgresql+psycopg:// for async support
if db_url.startswith("postgresql://") and "+psycopg" not in db_url:
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

session_service = DatabaseSessionService(db_url=db_url)
rag_analysis = RAGAnalysis()

# Create RAG analysis agent
rag_analyzer_agent = Agent(
    name="rag_analyzer",
    description="Specialized agent for retrieval-augmented generation and document search",
    model=LiteLlm(LLM_MODEL),
    instruction="""You are an advanced RAG (Retrieval-Augmented Generation) agent specialized in document retrieval and knowledge extraction.

You have access to the following tools:

SEARCH TOOLS:
1. vector_search - Semantic similarity search using embeddings
2. hyde_search - HyDE: generates a hypothetical answer then searches by its embedding (better for complex/conceptual queries)
3. lexical_search - Full-text keyword search (supports Lucene syntax)
4. hybrid_search - Unified search: runs vector + lexical + graph in parallel, fuses with RRF, reranks with BM25
5. graph_search - Convert natural language to Cypher and query the graph
6. detect_entities - Extract named entities from text

RETRIEVAL TOOLS:
7. graph_based_retrieval - Retrieve documents based on entity relationships in the graph
8. community_based_retrieval - Retrieve chunks through detected graph communities
9. payload_search - Retrieve visual/table payloads linked to chunks
10. get_chunk_context - Expand a chunk with its neighboring chunks from the same document for fuller context

QUERY TOOLS:
11. query_expand - Expand query with synonyms, related terms, and alternate phrasings

RERANKING TOOLS:
12. bm25_rerank - Re-rank using BM25 (fast, keyword-based)
13. cross_encoder_rerank - Re-rank using LLM scoring (slower, more accurate)

FUSION TOOLS:
14. reciprocal_rank_fusion - Fuse multiple ranked lists with configurable weights

END-TO-END TOOL:
15. graphrag_answer - Full GraphRAG pipeline (entity extraction + hybrid retrieval + fusion + reranking + chunk expansion + grounded answer)

Use these tools to:
- Answer questions based on retrieved documents
- Extract relevant information from knowledge bases
- Find semantically similar content
- Identify entities and relationships

WORKFLOW for answering questions:
0. Prefer graphrag_answer for a full pipeline response unless the user explicitly asks for individual tool steps
1. For quick single-tool retrieval, use hybrid_search (it handles multi-source fusion and reranking internally)
2. For manual multi-step workflow:
   a. Use query_expand to generate synonyms and related terms (recommended for ambiguous queries)
   b. Use detect_entities to extract key entities from the question
   c. Run multiple searches in parallel for best coverage:
      - vector_search for semantic similarity (use expanded query if available)
      - hyde_search for complex or conceptual queries (use INSTEAD of vector_search, not both)
      - lexical_search for exact keyword matches
      - graph_based_retrieval if entities were found
      - community_based_retrieval if entities were found
      - payload_search for image/table context
   d. Use reciprocal_rank_fusion to combine results:
      Example: {"vector": [...], "lexical": [...], "entity": [...]}
      With weights: {"vector": 1.2, "lexical": 1.0, "entity": 0.8}
   e. ALWAYS rerank after fusion — use bm25_rerank on top ~30 results
   f. For highest quality, follow with cross_encoder_rerank on top ~15 results
   g. Use get_chunk_context on top results if chunks seem truncated or the answer may span chunk boundaries
   h. Synthesize the reranked results to provide a comprehensive answer

MANDATORY RERANKING RULES:
- ALWAYS apply at least one reranking pass (bm25_rerank) before synthesizing answers
- For the highest quality, use bm25_rerank on top ~30 results, then cross_encoder_rerank on top ~15
- NEVER return raw search results without reranking when building a final answer
- graphrag_answer and hybrid_search already include built-in reranking — no extra step needed for those

IMPORTANT:
- Always cite your sources when providing information
- If information is not found, clearly state that
- Use query_expand for complex or ambiguous queries to improve recall
- Use vector_search for simple, direct semantic queries
- Use hyde_search for complex, abstract, or conceptual queries where vector_search may miss results
- Use lexical_search alone when exact keywords matter
- Use hybrid_search when you need a fast, high-quality single-tool retrieval path
- Use get_chunk_context when answers may span chunk boundaries or chunks seem truncated
- Use graphrag_answer when the user asks for a complete answer grounded in the graph and chunks
""",
    tools=[
        LongRunningFunctionTool(func=rag_analysis.vector_search),
        LongRunningFunctionTool(func=rag_analysis.hyde_search),
        LongRunningFunctionTool(func=rag_analysis.lexical_search),
        LongRunningFunctionTool(func=rag_analysis.hybrid_search),
        LongRunningFunctionTool(func=rag_analysis.graph_search),
        LongRunningFunctionTool(func=rag_analysis.detect_entities),
        LongRunningFunctionTool(func=rag_analysis.graph_based_retrieval),
        LongRunningFunctionTool(func=rag_analysis.community_based_retrieval),
        LongRunningFunctionTool(func=rag_analysis.payload_search),
        LongRunningFunctionTool(func=rag_analysis.query_expand),
        LongRunningFunctionTool(func=rag_analysis.bm25_rerank),
        LongRunningFunctionTool(func=rag_analysis.cross_encoder_rerank),
        LongRunningFunctionTool(func=rag_analysis.reciprocal_rank_fusion),
        LongRunningFunctionTool(func=rag_analysis.get_chunk_context),
        LongRunningFunctionTool(func=rag_analysis.graphrag_answer),
    ],
    planner=BuiltInPlanner(thinking_config=thinking_config),
)

# Create A2A server using ADK SDK directly
root_agent = Agent(
    name=agent_identifier,
    description="Specialized agent for retrieval-augmented generation and knowledge extraction from documents.",
    model=LiteLlm(LLM_MODEL),
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


@app.on_event("shutdown")
async def shutdown_event():
    """Close Neo4j connection on shutdown."""
    logger.info("Shutting down RAG agent, closing Neo4j connection...")
    await rag_analysis.neo4j.close()


@app.on_event("startup")
async def startup_event():
    """Fail fast if runtime retrieval/embedding compatibility checks fail."""
    logger.info("Running RAG startup runtime checks...")
    await rag_analysis.verify_runtime()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
