"""
RAG Analysis Module - Document retrieval and knowledge extraction
"""

import os
import logging
import json
from typing import List, Dict
from dotenv import load_dotenv
from neo4j import GraphDatabase
from google.adk.models import LiteLlm
from google.adk.models.llm_request import LlmRequest
from google.genai import types
import litellm
import numpy as np

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LiteLLMEmbeddings:
    """Embeddings using LiteLLM."""

    def __init__(self):
        self.model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        logger.info(f"LiteLLM Embeddings initialized with model: {self.model}")

    def embed_query(self, text: str):
        """Generate embedding for a single query text."""
        try:
            response = litellm.embedding(
                model=self.model,
                input=text
            )
            return response.data[0]['embedding']
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise


class Neo4jConnection:
    """Neo4j database connection for graph and vector operations."""

    def __init__(self):
        self.uri = os.getenv("NEO4J_URI")
        self.user = os.getenv("NEO4J_USERNAME")
        self.password = os.getenv("NEO4J_PASSWORD")
        self.database = os.getenv("NEO4J_DATABASE")

        if not all([self.uri, self.user, self.password, self.database]):
            logger.warning("Neo4j configuration incomplete. Some features may not work.")
            self.driver = None
            return

        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            # Test connection
            with self.driver.session(database=self.database) as session:
                session.run("RETURN 1")
            logger.info(f"Neo4j connection initialized: {self.database}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            self.driver = None

    def query(self, cypher, params=None):
        """Execute a Cypher query and return results."""
        if not self.driver:
            logger.error("Neo4j driver not initialized")
            return []

        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(cypher, params or {})
                return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return []

    def close(self):
        """Close the Neo4j driver connection."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")


class RAGAnalysis:
    """RAG analysis tools for document retrieval and knowledge extraction."""

    def __init__(self):
        self.llm = LiteLlm(model=os.getenv("LLM_MODEL", "openai/gpt-5-mini"))
        self.embeddings = LiteLLMEmbeddings()
        self.neo4j = Neo4jConnection()
        logger.info("RAGAnalysis initialized")

    async def vector_search(self, search_query: str, top_k: int = 10) -> str:
        """
        Search for documents using semantic similarity.

        Args:
            search_query: Query string to search for
            top_k: Number of results to return

        Returns:
            JSON string with search results
        """
        try:
            logger.info(f"Vector search: '{search_query}' (top_k={top_k})")

            if not self.neo4j.driver:
                return json.dumps({"error": "Neo4j not configured"})

            # Generate embedding for query
            embedding = self.embeddings.embed_query(search_query)

            # Search for similar documents
            cypher = """
            CALL db.index.vector.queryNodes('chunk_embedding_index', $k, $embedding)
            YIELD node, score
            RETURN node.id AS id, node.text AS text, score
            ORDER BY score DESC
            """
            results = self.neo4j.query(cypher, {"k": top_k, "embedding": embedding})

            if not results:
                return json.dumps({"results": [], "message": "No results found"})

            return json.dumps({"results": results, "count": len(results)})

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return json.dumps({"error": str(e)})

    async def graph_search(self, search_query: str) -> str:
        """
        Search structured data using natural language converted to Cypher.

        Args:
            search_query: Natural language query

        Returns:
            JSON string with search results
        """
        try:
            logger.info(f"Graph search: '{search_query}'")

            if not self.neo4j.driver:
                return json.dumps({"error": "Neo4j not configured"})

            # Generate Cypher query using LLM
            prompt = f"""Generate a Cypher query for Neo4j to answer this question: {search_query}

Use only standard Neo4j syntax. Return ONLY the Cypher query, no explanations."""

            content = types.Content(role="user", parts=[types.Part(text=prompt)])
            llm_request = LlmRequest(
                model=self.llm.model,
                contents=[content],
                config=types.GenerateContentConfig(temperature=0.1, max_output_tokens=500),
            )

            # Generate Cypher query
            import asyncio
            response_gen = self.llm.generate_content_async(llm_request)
            response_text = ""
            async for resp in response_gen:
                if resp.content and resp.content.parts:
                    for part in resp.content.parts:
                        if hasattr(part, "text") and part.text:
                            response_text += part.text

            if not response_text:
                return json.dumps({"error": "Failed to generate query"})

            # Execute generated query
            results = self.neo4j.query(response_text.strip())

            return json.dumps({
                "query": response_text.strip(),
                "results": results,
                "count": len(results)
            })

        except Exception as e:
            logger.error(f"Graph search failed: {e}")
            return json.dumps({"error": str(e)})

    async def detect_entities(self, text: str) -> str:
        """
        Extract named entities from text using LLM.

        Args:
            text: Text to extract entities from

        Returns:
            JSON string with extracted entities
        """
        try:
            logger.info(f"Detecting entities in text (length: {len(text)})")

            prompt = f"""Extract all named entities from the text below. Include people, organizations, locations, products, technologies, and domain-specific terms.

Text: {text}

Return ONLY a JSON array with entity names, e.g.: ["Entity1", "Entity2"]
Do not include any explanation, just the JSON array."""

            content = types.Content(role="user", parts=[types.Part(text=prompt)])
            llm_request = LlmRequest(
                model=self.llm.model,
                contents=[content],
                config=types.GenerateContentConfig(max_output_tokens=1000),
            )

            # Call LLM
            import asyncio
            response_gen = self.llm.generate_content_async(llm_request)
            response_text = ""
            async for resp in response_gen:
                if resp.content and resp.content.parts:
                    for part in resp.content.parts:
                        if hasattr(part, "text") and part.text:
                            response_text += part.text

            if not response_text:
                return json.dumps({"entities": []})

            # Parse entities from response
            try:
                entities = json.loads(response_text.strip())
                if isinstance(entities, list):
                    return json.dumps({"entities": entities, "count": len(entities)})
            except json.JSONDecodeError:
                pass

            # If JSON parsing fails, extract quoted strings
            import re
            quoted_strings = re.findall(r'"([^"]*)"', response_text)
            return json.dumps({"entities": quoted_strings, "count": len(quoted_strings)})

        except Exception as e:
            logger.error(f"Entity detection failed: {e}")
            return json.dumps({"error": str(e), "entities": []})

    async def hybrid_search(self, search_query: str, top_k: int = 10) -> str:
        """
        Combine vector and lexical search for better results.

        Args:
            search_query: Query string
            top_k: Number of results to return

        Returns:
            JSON string with fused search results
        """
        try:
            logger.info(f"Hybrid search: '{search_query}' (top_k={top_k})")

            if not self.neo4j.driver:
                return json.dumps({"error": "Neo4j not configured"})

            # Vector search
            embedding = self.embeddings.embed_query(search_query)
            vector_cypher = """
            CALL db.index.vector.queryNodes('chunk_embedding_index', $k, $embedding)
            YIELD node, score
            RETURN node.id AS id, node.text AS text, score
            """
            vector_results = self.neo4j.query(vector_cypher, {"k": top_k, "embedding": embedding})

            # Lexical search (full-text)
            lexical_cypher = """
            CALL db.index.fulltext.queryNodes('chunk_text_ft', $query)
            YIELD node, score
            RETURN node.id AS id, node.text AS text, score
            LIMIT $limit
            """
            lexical_results = self.neo4j.query(lexical_cypher, {"query": search_query, "limit": top_k})

            # Combine results using reciprocal rank fusion
            combined_scores = {}
            k = 60  # RRF constant

            for rank, result in enumerate(vector_results, 1):
                doc_id = result["id"]
                combined_scores[doc_id] = combined_scores.get(doc_id, 0) + 1 / (k + rank)

            for rank, result in enumerate(lexical_results, 1):
                doc_id = result["id"]
                combined_scores[doc_id] = combined_scores.get(doc_id, 0) + 1 / (k + rank)

            # Get all unique documents
            all_docs = {doc["id"]: doc for doc in vector_results + lexical_results}

            # Sort by combined score
            sorted_ids = sorted(combined_scores.keys(), key=lambda x: combined_scores[x], reverse=True)[:top_k]
            fused_results = [
                {**all_docs[doc_id], "fused_score": combined_scores[doc_id]}
                for doc_id in sorted_ids if doc_id in all_docs
            ]

            return json.dumps({
                "results": fused_results,
                "count": len(fused_results),
                "method": "hybrid_rrf"
            })

        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return json.dumps({"error": str(e)})

    async def graph_based_retrieval(self, entities: List[str], limit: int = 10) -> str:
        """
        Retrieve documents based on entity relationships in the graph.

        Args:
            entities: List of entity names to search for
            limit: Maximum number of results

        Returns:
            JSON string with retrieved documents
        """
        try:
            logger.info(f"Graph-based retrieval for entities: {entities}")

            if not self.neo4j.driver:
                return json.dumps({"error": "Neo4j not configured"})

            if not entities:
                return json.dumps({"results": [], "message": "No entities provided"})

            cypher = """
            UNWIND $entities AS ent
            MATCH (e:__Entity__ {name:ent})
            OPTIONAL MATCH (e)<-[:MENTIONS]-(c1:__Chunk__)
            OPTIONAL MATCH (e)-[:REL]-()-[:MENTIONS]-(c2:__Chunk__)
            WITH collect(c1) + collect(c2) AS chunks
            UNWIND chunks AS c
            WHERE c IS NOT NULL
            RETURN c.id AS id, c.text AS text, count(*) AS relevance
            ORDER BY relevance DESC
            LIMIT $limit
            """
            results = self.neo4j.query(cypher, {"entities": entities, "limit": limit})

            return json.dumps({"results": results, "count": len(results)})

        except Exception as e:
            logger.error(f"Graph-based retrieval failed: {e}")
            return json.dumps({"error": str(e)})
