"""
RAG Analysis Module - Document retrieval and knowledge extraction
"""

import os
import logging
import json
from typing import List, Dict
from dotenv import load_dotenv
from neo4j import AsyncGraphDatabase
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
            response = litellm.embedding(model=self.model, input=text)
            return response.data[0]["embedding"]
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
            logger.warning(
                "Neo4j configuration incomplete. Some features may not work."
            )
            self.driver = None
            return

        try:
            # Type assertion: we've already verified these are not None above
            assert self.uri is not None and self.user is not None and self.password is not None
            self.driver = AsyncGraphDatabase.driver(
                self.uri, auth=(self.user, self.password)
            )
            logger.info(f"Neo4j connection initialized: {self.database}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            self.driver = None

    async def query(self, cypher, params=None):
        """Execute a Cypher query and return results without blocking the event loop."""
        if not self.driver:
            logger.error("Neo4j driver not initialized")
            return []

        try:
            async with self.driver.session(database=self.database) as session:
                result = await session.run(cypher, params or {})
                return [dict(record) async for record in result]
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return []

    async def close(self):
        """Close the Neo4j driver connection."""
        if self.driver:
            await self.driver.close()
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
            results = await self.neo4j.query(
                cypher, {"k": top_k, "embedding": embedding}
            )

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
                config=types.GenerateContentConfig(
                    temperature=0.1, max_output_tokens=500
                ),
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
            results = await self.neo4j.query(response_text.strip())

            return json.dumps(
                {
                    "query": response_text.strip(),
                    "results": results,
                    "count": len(results),
                }
            )

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
            return json.dumps(
                {"entities": quoted_strings, "count": len(quoted_strings)}
            )

        except Exception as e:
            logger.error(f"Entity detection failed: {e}")
            return json.dumps({"error": str(e), "entities": []})

    async def lexical_search(self, search_query: str, top_k: int = 10) -> str:
        """
        Search for documents using full-text lexical matching.

        Args:
            search_query: Query string (supports Lucene query syntax)
            top_k: Number of results to return

        Returns:
            JSON string with search results ranked by text relevance
        """
        try:
            logger.info(f"Lexical search: '{search_query}' (top_k={top_k})")

            if not self.neo4j.driver:
                return json.dumps({"error": "Neo4j not configured"})

            cypher = """
            CALL db.index.fulltext.queryNodes('chunk_text_ft', $query)
            YIELD node, score
            RETURN node.id AS id, node.text AS text, score
            LIMIT $limit
            """
            results = await self.neo4j.query(
                cypher, {"query": search_query, "limit": top_k}
            )

            if not results:
                return json.dumps({"results": [], "message": "No results found"})

            return json.dumps({"results": results, "count": len(results)})

        except Exception as e:
            logger.error(f"Lexical search failed: {e}")
            return json.dumps({"error": str(e)})

    async def reciprocal_rank_fusion(
        self,
        ranked_lists_json: str,
        k: int = 60,
        top_k: int = 10,
        weights_json: str = "null",
    ) -> str:
        """
        Fuse multiple ranked result lists using Reciprocal Rank Fusion (RRF).

        RRF combines multiple ranking lists by summing reciprocal ranks:
        score(doc) = Σ weight_i / (k + rank_i(doc))

        Args:
            ranked_lists_json: JSON object with named ranked lists. Each list contains objects with "id" field.
                Example: {"vector": [{"id": "doc1", "text": "..."}, ...], "lexical": [{"id": "doc2", ...}]}
            k: RRF constant (default 60). Higher values reduce impact of high ranks.
            top_k: Number of results to return after fusion.
            weights_json: Optional JSON object with weights per source. Default is equal weight (1.0).
                Example: {"vector": 1.5, "lexical": 1.0, "graph": 0.8}

        Returns:
            JSON string with fused results including source contributions.
        """
        try:
            logger.info(f"Reciprocal Rank Fusion (k={k}, top_k={top_k})")

            # Parse ranked lists
            try:
                ranked_lists = json.loads(ranked_lists_json)
            except json.JSONDecodeError as e:
                return json.dumps({"error": f"Invalid ranked_lists_json: {e}"})

            if not isinstance(ranked_lists, dict):
                return json.dumps(
                    {
                        "error": "ranked_lists_json must be a JSON object with named lists"
                    }
                )

            if not ranked_lists:
                return json.dumps(
                    {"results": [], "message": "No ranked lists provided"}
                )

            # Parse weights (optional)
            weights = {}
            if weights_json and weights_json != "null":
                try:
                    weights = json.loads(weights_json)
                except json.JSONDecodeError:
                    pass

            # Default weight is 1.0 for all sources
            for source in ranked_lists.keys():
                if source not in weights:
                    weights[source] = 1.0

            # Calculate RRF scores
            rrf_scores: Dict[str, float] = {}
            source_contributions: Dict[str, Dict[str, float]] = (
                {}
            )  # doc_id -> {source: contribution}
            all_docs: Dict[str, dict] = {}

            for source_name, results in ranked_lists.items():
                if not isinstance(results, list):
                    logger.warning(f"Skipping source '{source_name}': not a list")
                    continue

                weight = weights.get(source_name, 1.0)

                for rank, doc in enumerate(results, start=1):
                    if not isinstance(doc, dict) or "id" not in doc:
                        continue

                    doc_id = doc["id"]
                    contribution = weight / (k + rank)

                    # Accumulate RRF score
                    rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + contribution

                    # Track source contributions
                    if doc_id not in source_contributions:
                        source_contributions[doc_id] = {}
                    source_contributions[doc_id][source_name] = contribution

                    # Store document data (prefer earlier occurrence)
                    if doc_id not in all_docs:
                        all_docs[doc_id] = doc

            if not rrf_scores:
                return json.dumps(
                    {
                        "results": [],
                        "message": "No valid documents found in ranked lists",
                    }
                )

            # Sort by RRF score and take top_k
            sorted_doc_ids = sorted(
                rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True
            )[:top_k]

            # Build fused results
            fused_results = []
            for doc_id in sorted_doc_ids:
                doc = all_docs[doc_id].copy()
                doc["rrf_score"] = round(rrf_scores[doc_id], 6)
                doc["source_contributions"] = {
                    src: round(score, 6)
                    for src, score in source_contributions[doc_id].items()
                }
                fused_results.append(doc)

            return json.dumps(
                {
                    "results": fused_results,
                    "count": len(fused_results),
                    "sources": list(ranked_lists.keys()),
                    "weights": weights,
                    "k": k,
                }
            )

        except Exception as e:
            logger.error(f"Reciprocal Rank Fusion failed: {e}")
            return json.dumps({"error": str(e)})

    async def bm25_rerank(
        self,
        query: str,
        documents_json: str,
        k1: float = 1.5,
        b: float = 0.75,
        top_k: int = 10,
    ) -> str:
        """
        Re-rank documents using BM25 scoring algorithm.

        BM25 is a bag-of-words ranking function that scores documents based on
        term frequency, inverse document frequency, and document length normalization.

        Args:
            query: Search query string
            documents_json: JSON array of documents with "id" and "text" fields.
                Example: [{"id": "doc1", "text": "document content..."}, ...]
            k1: Term frequency saturation parameter (default 1.5). Higher values
                increase the impact of term frequency. Typical range: 1.2-2.0
            b: Document length normalization (default 0.75). 0 = no normalization,
                1 = full normalization. Typical range: 0.5-0.8
            top_k: Number of top results to return after re-ranking.

        Returns:
            JSON string with re-ranked documents including BM25 scores.
        """
        import math
        from collections import Counter

        try:
            logger.info(
                f"BM25 rerank: query='{query[:50]}...' k1={k1}, b={b}, top_k={top_k}"
            )

            # Parse documents
            try:
                documents = json.loads(documents_json)
            except json.JSONDecodeError as e:
                return json.dumps({"error": f"Invalid documents_json: {e}"})

            if not isinstance(documents, list):
                return json.dumps({"error": "documents_json must be a JSON array"})

            if not documents:
                return json.dumps({"results": [], "message": "No documents provided"})

            # Tokenize (simple whitespace + lowercase)
            def tokenize(text: str) -> List[str]:
                return text.lower().split()

            # Tokenize query
            query_terms = tokenize(query)
            if not query_terms:
                return json.dumps(
                    {"results": documents[:top_k], "message": "Empty query"}
                )

            # Tokenize all documents and compute stats
            doc_tokens: List[List[str]] = []
            doc_lengths: List[int] = []
            for doc in documents:
                text = doc.get("text", "")
                tokens = tokenize(text)
                doc_tokens.append(tokens)
                doc_lengths.append(len(tokens))

            N = len(documents)  # Total number of documents
            avgdl = sum(doc_lengths) / N if N > 0 else 1  # Average document length

            # Compute document frequency for each query term
            df: Dict[str, int] = {}  # term -> number of docs containing it
            for term in set(query_terms):
                df[term] = sum(1 for tokens in doc_tokens if term in tokens)

            # Compute IDF for each query term
            # Using BM25 IDF formula: log((N - df + 0.5) / (df + 0.5) + 1)
            idf: Dict[str, float] = {}
            for term in set(query_terms):
                n = df.get(term, 0)
                idf[term] = math.log((N - n + 0.5) / (n + 0.5) + 1)

            # Score each document
            scores: List[tuple] = []
            for i, doc in enumerate(documents):
                tokens = doc_tokens[i]
                doc_len = doc_lengths[i]

                # Term frequencies in this document
                tf = Counter(tokens)

                # BM25 score
                score = 0.0
                term_scores: Dict[str, float] = {}
                for term in query_terms:
                    if term not in tf:
                        continue

                    freq = tf[term]
                    term_idf = idf.get(term, 0)

                    # BM25 term score
                    numerator = freq * (k1 + 1)
                    denominator = freq + k1 * (1 - b + b * (doc_len / avgdl))
                    term_score = term_idf * (numerator / denominator)

                    score += term_score
                    term_scores[term] = round(term_score, 4)

                scores.append((i, score, term_scores))

            # Sort by score descending and take top_k
            scores.sort(key=lambda x: x[1], reverse=True)
            top_results = scores[:top_k]

            # Build result
            reranked = []
            for idx, score, term_scores in top_results:
                doc = documents[idx].copy()
                doc["bm25_score"] = round(score, 6)
                doc["term_contributions"] = term_scores
                reranked.append(doc)

            return json.dumps(
                {
                    "results": reranked,
                    "count": len(reranked),
                    "params": {"k1": k1, "b": b, "avgdl": round(avgdl, 2)},
                    "query_terms": query_terms,
                }
            )

        except Exception as e:
            logger.error(f"BM25 rerank failed: {e}")
            return json.dumps({"error": str(e)})

    async def cross_encoder_rerank(
        self, query: str, documents_json: str, top_k: int = 10
    ) -> str:
        """
        Re-rank documents using LLM-based cross-encoder scoring.

        Cross-encoders jointly encode the query and document together, allowing
        for deeper semantic understanding than bi-encoder (embedding) approaches.
        This uses the LLM to score query-document relevance.

        Args:
            query: Search query string
            documents_json: JSON array of documents with "id" and "text" fields.
                Example: [{"id": "doc1", "text": "document content..."}, ...]
            top_k: Number of top results to return after re-ranking.

        Returns:
            JSON string with re-ranked documents including relevance scores.
        """
        try:
            logger.info(f"Cross-encoder rerank: query='{query[:50]}...' top_k={top_k}")

            # Parse documents
            try:
                documents = json.loads(documents_json)
            except json.JSONDecodeError as e:
                return json.dumps({"error": f"Invalid documents_json: {e}"})

            if not isinstance(documents, list):
                return json.dumps({"error": "documents_json must be a JSON array"})

            if not documents:
                return json.dumps({"results": [], "message": "No documents provided"})

            # Score each document using LLM
            scored_docs = []
            for doc in documents:
                doc_text = doc.get("text", "")[:2000]  # Limit text length

                prompt = f"""Rate the relevance of this document to the query on a scale of 0-100.

Query: {query}

Document: {doc_text}

Return ONLY a number between 0 and 100, nothing else."""

                content = types.Content(role="user", parts=[types.Part(text=prompt)])
                llm_request = LlmRequest(
                    model=self.llm.model,
                    contents=[content],
                    config=types.GenerateContentConfig(
                        temperature=0.0, max_output_tokens=10
                    ),
                )

                response_text = ""
                async for resp in self.llm.generate_content_async(llm_request):
                    if resp.content and resp.content.parts:
                        for part in resp.content.parts:
                            if hasattr(part, "text") and part.text:
                                response_text += part.text

                # Parse score
                try:
                    score = float(response_text.strip())
                    score = max(0, min(100, score))  # Clamp to 0-100
                except ValueError:
                    score = 0.0

                scored_docs.append((doc, score))

            # Sort by score descending and take top_k
            scored_docs.sort(key=lambda x: x[1], reverse=True)
            top_results = scored_docs[:top_k]

            # Build result
            reranked = []
            for doc, score in top_results:
                doc_copy = doc.copy()
                doc_copy["cross_encoder_score"] = round(score, 2)
                reranked.append(doc_copy)

            return json.dumps(
                {
                    "results": reranked,
                    "count": len(reranked),
                    "method": "llm_cross_encoder",
                }
            )

        except Exception as e:
            logger.error(f"Cross-encoder rerank failed: {e}")
            return json.dumps({"error": str(e)})

    async def query_expand(
        self, query: str, expansion_type: str = "all", max_terms: int = 10
    ) -> str:
        """
        Expand a search query with synonyms, related terms, and alternate phrasings.

        Query expansion improves recall by adding terms that users might not have
        included but are semantically related to the original query.

        Args:
            query: Original search query
            expansion_type: Type of expansion - "synonyms", "related", "rephrase", or "all" (default)
            max_terms: Maximum number of expansion terms to generate (default 10)

        Returns:
            JSON string with original query, expanded terms, and suggested expanded queries.
        """
        try:
            logger.info(f"Query expansion: '{query}' type={expansion_type}")

            prompt = f"""Expand this search query to improve search recall.

Original query: {query}

Generate expansions based on type "{expansion_type}":
- synonyms: Alternative words with same meaning
- related: Related concepts and terms
- rephrase: Alternative phrasings of the query
- all: All of the above

Return a JSON object with this exact structure:
{{
    "synonyms": ["term1", "term2"],
    "related_terms": ["term1", "term2"],
    "rephrased_queries": ["query1", "query2"],
    "expanded_query": "original query with key expansion terms added"
}}

Generate up to {max_terms} terms total across all categories.
Return ONLY valid JSON, no explanation."""

            content = types.Content(role="user", parts=[types.Part(text=prompt)])
            llm_request = LlmRequest(
                model=self.llm.model,
                contents=[content],
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=500,
                    response_mime_type="application/json",
                ),
            )

            response_text = ""
            async for resp in self.llm.generate_content_async(llm_request):
                if resp.content and resp.content.parts:
                    for part in resp.content.parts:
                        if hasattr(part, "text") and part.text:
                            response_text += part.text

            if not response_text:
                return json.dumps(
                    {
                        "original_query": query,
                        "synonyms": [],
                        "related_terms": [],
                        "rephrased_queries": [],
                        "expanded_query": query,
                        "error": "Failed to generate expansions",
                    }
                )

            # Parse response
            try:
                expansion = json.loads(response_text.strip())
                expansion["original_query"] = query
                return json.dumps(expansion)
            except json.JSONDecodeError:
                return json.dumps(
                    {
                        "original_query": query,
                        "synonyms": [],
                        "related_terms": [],
                        "rephrased_queries": [],
                        "expanded_query": query,
                        "error": "Failed to parse expansion response",
                    }
                )

        except Exception as e:
            logger.error(f"Query expansion failed: {e}")
            return json.dumps({"error": str(e), "original_query": query})

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
            MATCH (e:__Entity__ {name: ent})
            OPTIONAL MATCH (e)<-[:MENTIONS]-(c_direct:__Chunk__)
            OPTIONAL MATCH (e)-[:REL]-(:__Entity__)-[:MENTIONS]->(c_rel:__Chunk__)
            WITH collect(DISTINCT {chunk: c_direct, weight: 2.0}) +
                 collect(DISTINCT {chunk: c_rel, weight: 1.0}) AS chunk_entries
            UNWIND chunk_entries AS entry
            WITH entry.chunk AS c, sum(entry.weight) AS score
            WHERE c IS NOT NULL
            RETURN c.id AS id, c.text AS text, score
            ORDER BY score DESC
            LIMIT $limit
            """
            results = await self.neo4j.query(
                cypher, {"entities": entities, "limit": limit}
            )

            return json.dumps({"results": results, "count": len(results)})

        except Exception as e:
            logger.error(f"Graph-based retrieval failed: {e}")
            return json.dumps({"error": str(e)})
