import os
import json
import time
import collections
import numpy as np
from typing import Dict, List
# Google ADK imports
from google.genai import types
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse


class RAGTools:

    def vector_search(self, search_query: str, top_k: int) -> str:
        """
        Search unstructured data aka retrieve sources from the vector store.
        Input Description: Query string to retrieve documents from azure search eg: 'PII rules', number of results to retrieve
        Output Description: { response: A long string of text with the output of the model"}
        """
        try:
            # Using vector_search_semantic to get documents
            docs = self.vector_search_semantic(search_query, top_k)
            if not docs:
                return "No results found."

            # Format the results as a text response
            response_parts = []
            for i, doc in enumerate(docs, 1):
                text = doc.get("text", "").strip()
                if text:
                    response_parts.append(f"Result {i}:\n{text}\n")

            return (
                "\n".join(response_parts)
                if response_parts
                else "No relevant content found."
            )
        except Exception as e:
            self.log.error(f"Vector search failed: {e}")
            return f"Search failed: {str(e)}"

    def cosine_similarity(a, b):
        """Enhanced fallback for cosine similarity."""
        a = np.array(a, dtype=np.float64).flatten()
        b = np.array(b, dtype=np.float64).flatten()

        # Handle zero vectors
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        # Compute cosine similarity
        dot_product = np.dot(a, b)
        return dot_product / (norm_a * norm_b)

    def detect_entities(self, text: str) -> List[str]:
        """
        Extract entities from text using both spaCy and LLM for robust entity extraction.
        Only uses spaCy if appropriate language models are available.

        Input Description: Text to extract entities from
        Output Description: List of entities extracted from the text, combining both approaches
        """
        # Set to store unique entities from all methods
        all_entities = set()

        # Get timeout settings from environment or use defaults
        max_retries = int(
            os.getenv("ENTITY_LLM_MAX_RETRIES", "2")
        )  # Number of retries for LLM

        # 2. Always also use LLM-based extraction (not just as fallback)
        retries = 0

        while retries <= max_retries:
            try:
                self.log.info(
                    f"Using LLM for entity extraction (attempt {retries+1}/{max_retries+1})"
                )

                # Create prompt using Google ADK format
                prompt_text = f"""Extract all named entities from the text below. Include people, organizations, locations, products, technologies, and domain-specific terms.
                    
                    Text: {text}
                    
                    Return ONLY a JSON array with entity names, e.g.: ["Entity1", "Entity2"]
                    Do not include any explanation, just the JSON array."""

                # Create LLM request using Google ADK
                content = types.Content(
                    role="user", parts=[types.Part(text=prompt_text)]
                )

                llm_request = LlmRequest(
                    model=self.model_name,
                    contents=[content],
                    config=types.GenerateContentConfig(
                        temperature=0.1, max_output_tokens=1000
                    ),
                )

                # Make async call to LLM
                import asyncio

                response = asyncio.run(self.llm.generate_content_async(llm_request))

                # Extract content from response
                response_content = ""
                for resp in response:
                    if resp.content and resp.content.parts:
                        for part in resp.content.parts:
                            if part.text:
                                response_content += part.text

                # Use our robust extraction helper
                llm_entities = self._extract_entities_from_llm_response(
                    response_content
                )

                if llm_entities:
                    self.log.info(f"Detected {len(llm_entities)} entities using LLM")
                    # Add non-empty entities to our set
                    all_entities.update([e for e in llm_entities if e])
                else:
                    self.log.warning(
                        f"No entities extracted from LLM response on attempt {retries+1}"
                    )
                    retries += 1

            except Exception as e:
                self.log.error(
                    f"Error in LLM entity detection (attempt {retries+1}): {str(e)}"
                )
                retries += 1
                # Brief delay before retry
                if retries <= max_retries:
                    time.sleep(1)

        # 3. Return combined unique entities from both methods
        if all_entities:
            # Clean up entities - remove any that are just numbers or single characters
            cleaned_entities = {
                e for e in all_entities if e and not e.isdigit() and len(e) > 1
            }
            self.log.info(f"Total unique entities detected: {len(cleaned_entities)}")

            # Sort by length (descending) to prioritize more specific entities
            return sorted(list(cleaned_entities), key=len, reverse=True)
        else:
            self.log.warning("No entities detected")
            return []

    def vector_search_semantic(self, query: str, top_k: int) -> List[Dict]:
        """
        Search for documents using vector embedding similarity.

        Input Description: Query text to search for, number of results to retrieve
        Output Description: List of semantically similar documents
        """
        try:
            embedding = vector_store._embedding.embed_query(query)

            cypher = """
            CALL db.index.vector.queryNodes('chunk_embedding_index', $k, $embedding) 
        """
            params = {"k": top_k, "embedding": embedding}
            results = vector_store.query(cypher, params=params)

            # Convert to standardized format
            documents = []
            for result in results:
                doc = {
                    "id": result.get("id"),
                    "text": result.get("text", ""),
                    "score": result.get("score", 0.0),
                    "metadata": result,
                }
                documents.append(doc)

            return documents

        except Exception as e:
            self.log.error(f"Vector semantic search failed: {e}")
            return []

    def lexical_search(self, query: str, top_k: int) -> List[Dict]:
        """
        Search for documents using full-text search.

        Input Description: Query text to search for, number of results to retrieve
        Output Description: List of documents matching keywords
        """
        cypher = """
        CALL db.index.fulltext.queryNodes('chunk_text_ft', $query) YIELD node, score
        RETURN node.id AS id, node.text AS text, score
        LIMIT $limit
        """
        sanitized = self._sanitize_lucene_query(query)
        results = graph_store.query(cypher, {"query": sanitized, "limit": top_k})
        return [
            {"id": r["id"], "text": r["text"], "score": r["score"]} for r in results
        ]

    def graph_based_retrieval(self, entities: List[str], limit: int) -> List[Dict]:
        """
        Retrieve documents based on entity mentions in the graph.

        Input Description: List of entities to search for in the graph, number of results to retrieve
        Output Description: List of documents related to those entities
        """
        if not entities:
            return []

        cypher = """
        UNWIND $entities AS ent
        // A) exact graph hits
        MATCH (e:__Entity__ {name:ent})
        OPTIONAL MATCH (e)<-[:MENTIONS]-(c1:__Chunk__)
        OPTIONAL MATCH (e)-[:REL]-()-[:MENTIONS]-(c2:__Chunk__)
        // collect all graph hits into one list
        WITH collect(c1) + collect(c2) AS graphHits, $entities AS ents

        // B) brute‐force text hits for multi‐word entities
        MATCH (c3:__Chunk__)
        WHERE all(term IN ents 
                WHERE toLower(c3.text) CONTAINS toLower(term))
        // collect those too
        WITH graphHits, collect(c3) AS textHits

        // now union them
        WITH graphHits + textHits AS both

        UNWIND both AS c
        RETURN c.id AS id, c.text AS text, count(*) AS score
        ORDER BY score DESC
        LIMIT $limit
        """
        results = graph_store.query(cypher, {"entities": entities, "limit": limit})
        return [
            {"id": r["id"], "text": r["text"], "score": r["score"]} for r in results
        ]

    def get_entities_for_chunk(self, chunk_id: str) -> List[Dict]:
        """
        Get entities mentioned in a specific chunk.

        Input Description: ID of the chunk to analyze
        Output Description: List of entities and their details from the chunk
        """
        cypher = """
        MATCH (c:__Chunk__ {id:$chunk_id})-[:MENTIONS]->(e:__Entity__)
        RETURN e.name AS name, e.type AS type, e.summary AS summary
        """
        return graph_store.query(cypher, {"chunk_id": chunk_id})

    def get_entity_neighbors(self, entity_name: str, limit: int) -> List[Dict]:
        """
        Get neighboring entities in the graph for a specific entity.

        Input Description: Name of the entity to find neighbors for, max number of results to retrieve
        Output Description: List of neighboring entities and relationship details
        """
        cypher = """
        MATCH (e:__Entity__ {name:$name})-[r]-(n:__Entity__)
        RETURN n.name AS name, n.type AS type, n.summary AS summary, 
               type(r) AS relationship_type, r.description AS relationship_description
        LIMIT $limit
        """
        return graph_store.query(cypher, {"name": entity_name, "limit": limit})

    def get_entity_communities(self, entity_name: str) -> List[Dict]:
        """
        Get communities that an entity belongs to.

        Input Description: Name of the entity to find communities for
        Output Description: List of communities and their details
        """
        cypher = """
        MATCH (e:__Entity__ {name:$name})-[:IN_COMMUNITY*1..]->(c:__Community__)
        RETURN DISTINCT c.level AS level, c.title AS title, c.summary AS summary, c.rating AS rating
        ORDER BY level ASC
        """
        return graph_store.query(cypher, {"name": entity_name})

    def generate_subqueries(self, question: str) -> List[str]:
        """
        Break down a complex question into simpler sub-questions.

        Input Description: Complex question to break down
        Output Description: List of simpler sub-questions
        """
        template = f"""Break the user question into 2–4 more specific sub-questions that, 
        if answered separately, would together fully answer the original.

        Question: {question}

        Sub-questions:
        1."""

        # Create LLM request using Google ADK
        content = types.Content(role="user", parts=[types.Part(text=template)])

        llm_request = LlmRequest(
            model=self.model_name,
            contents=[content],
            config=LlmConfig(temperature=0.3, max_output_tokens=500),
        )

        # Make async call to LLM
        import asyncio

        response = asyncio.run(self.llm.generate_content_async(llm_request))

        # Extract content from response
        text = ""
        for resp in response:
            if resp.content and resp.content.parts:
                for part in resp.content.parts:
                    if part.text:
                        text += part.text

        # Parse lines that start "1.", "2.", etc.
        subqs = []
        for line in text.splitlines():
            line = line.strip()
            if line and line[0] in {"1", "2", "3", "4"} and line[1] == ".":
                subqs.append(line.split(".", 1)[1].strip())
        return subqs

    def _sanitize_lucene_query(self, query: str) -> str:
        """
        Helper method that Escapes special characters for safe Lucene/Neo4j fulltext queries.
        """
        # List of Lucene special characters to escape
        special_chars = r'+-&|!(){}[]^"~*?:\\/'
        for char in special_chars:
            query = query.replace(char, f"\\{char}")
        # Remove unbalanced quotes (optional enhancement)
        if query.count('"') % 2 != 0:
            query = query.replace('"', "")  # Remove all if unbalanced
        # Remove leading/trailing whitespace
        return query.strip()

    def fuse_search_results(
        self,
        vector_results: List[Dict],
        lexical_results: List[Dict],
        graph_results: List[Dict],
        vector_weight: float,
        lexical_weight: float,
        graph_weight: float,
        rrf_k: int,
    ) -> List[Dict]:
        """
        Fuse multiple search result sets using Reciprocal Rank Fusion.

        Input Description: Multiple search result sets to combine, each weight and reciprocal Rank Fusion parameter
        Output Description: Single fused and ranked list of results
        """
        fused = collections.defaultdict(float)

        # Helper function to calculate RRF score
        def rrf(rank):
            return 1.0 / (rrf_k + rank)

        # Add vector search results
        for i, h in enumerate(sorted(vector_results, key=lambda x: -x["score"])):
            fused[h["id"]] += vector_weight * rrf(i + 1)

        # Add lexical search results
        for j, h in enumerate(sorted(lexical_results, key=lambda x: -x["score"])):
            fused[h["id"]] += lexical_weight * rrf(j + 1)

        # Add graph search results if available
        if graph_results:
            for k, h in enumerate(sorted(graph_results, key=lambda x: -x["score"])):
                fused[h["id"]] += graph_weight * rrf(k + 1)

        # Build candidates map
        candidates = {}
        for c in vector_results + lexical_results + (graph_results or []):
            candidates[c["id"]] = c

        # Sort by fused score
        sorted_ids = sorted(fused, key=fused.get, reverse=True)
        results = []
        for i in sorted_ids:
            if i in candidates:
                # Each result should already have id, text, and score fields
                # We only need to update the score to the fused value
                result = candidates[i].copy()  # Copy to avoid modifying the original
                result["score"] = fused[i]  # Update with fused score
                results.append(result)

        return results

    def enrich_chunk_context(
        self,
        chunk_id: str,
        chunk_text: str,
        query_entities: List[str] = None,
        limit_entity_neighbors: int = 5,
    ) -> str:
        """
        Enrich a chunk with entity and graph context.

        Input Description: Chunk ID and text to enrich
        Output Description: Enriched context with entities, relationships, and payload info
        """
        lines = [f"<chunk>{chunk_text}</chunk>"]

        # Get entities and their neighbors
        entities = self.get_entities_for_chunk(chunk_id)
        for entity in entities[:5]:  # Limit to top 5 entities
            lines.append(
                f"<entity>{entity['name']} ({entity.get('type','')}): {entity.get('summary','')}</entity>"
            )

            # Get neighbors for each entity
            neighbors = self.get_entity_neighbors(
                entity["name"], limit_entity_neighbors
            )
            for neighbor in neighbors[:3]:  # Limit to top 3 neighbors per entity
                lines.append(
                    f"<nei>{neighbor['name']} - {neighbor['relationship_type']}</nei>"
                )

            # Get communities
            communities = self.get_entity_communities(entity["name"])
            for community in communities[:2]:  # Limit to top 2 communities
                lines.append(
                    f"<comm l={community['level']}>{community['title']} (Impact:{community.get('rating', 'N/A')}): {community.get('summary', '')}</comm>"
                )

        # If we have query entities, check for semantic neighbors
        if query_entities:
            chunk_entity_names = {e["name"] for e in entities}
            for qe in query_entities:
                if qe in chunk_entity_names:
                    # Get node2vec neighbors for this query entity
                    cypher = """
                    MATCH (e1:__Entity__ {name:$name}) WHERE e1.embedding IS NOT NULL
                    MATCH (e2:__Entity__) WHERE e2.embedding IS NOT NULL AND e2.name<>$name
                      AND size(e2.embedding)=size(e1.embedding)
                    WITH e2,gds.similarity.cosine(e1.embedding,e2.embedding) AS score
                    ORDER BY score DESC LIMIT 5
                    RETURN e2.name AS name, e2.type AS type, e2.summary AS summary, score
                    """
                    n2v_neighbors = graph_store.query(cypher, {"name": qe})
                    for nb in n2v_neighbors:
                        lines.append(
                            f"<n2v>{nb['name']} ({nb.get('type', '')}): {nb.get('summary', '')}</n2v>"
                        )

        # Get payloads for this chunk
        payloads = self.get_payloads_for_chunk(chunk_id)
        for payload in payloads:
            tag = "image" if payload.get("type") == "image" else "table"
            lines.append(f"<{tag}>{payload.get('text', '')}</{tag}>")

        return "\n".join([l for l in lines if l])

    def graph_search(self, search_query: str) -> str:
        """
        Search structured data from graph store.
        Input Description: Query string to retrieve documents from graph store eg: 'PII rules'
        Output Description: { response: A long string of text with the output of the model"}
        """
        # Note: This method would need graph_store to be properly initialized
        # For now, we'll create a simplified version that generates Cypher queries

        template = f"""
        Task: Generate a Cypher statement to query the graph database.

        Instructions:
        Use only relationship types and properties provided in schema.
        Do not use other relationship types or properties that are not provided.
        The user does not know the schema, so you need to use the schema to generate the Cypher statement, 
        and can be a partial match of the schema,a partial match counts too since you have the schema you can create multiple chained cypher statements
        to respond to user query. 

        Note: Do not include explanations or apologies in your answers.
        Do not answer questions that ask anything other than creating Cypher statements.
        Do not include any text other than generated Cypher statements.

        Question: {search_query}"""

        # Create LLM request using Google ADK
        content = types.Content(role="user", parts=[types.Part(text=template)])

        llm_request = LlmRequest(
            model=self.model_name,
            contents=[content],
            config=LlmConfig(temperature=0.1, max_output_tokens=1000),
        )

        # Make async call to LLM
        import asyncio

        response = asyncio.run(self.llm.generate_content_async(llm_request))

        # Extract content from response
        result = ""
        for resp in response:
            if resp.content and resp.content.parts:
                for part in resp.content.parts:
                    if part.text:
                        result += part.text

        return result

    def mmr_rerank(
        self,
        candidate_ids: List[str],
        embeddings: Dict[str, List[float]],
        lambda_param: float,
        k: int,
    ) -> List[str]:
        """
        Re-ranks candidates using Maximum Marginal Relevance for diversity.

        Input Description: List of candidate IDs and their embeddings, lambda_param and k
        Output Description: Re-ranked list of IDs optimizing for relevance and diversity
        """
        # Use the cosine_similarity function defined at the top (sklearn or fallback)
        import numpy as np

        if not candidate_ids:
            return []

        selected = [candidate_ids[0]]
        unselected = candidate_ids[1:]

        while len(selected) < k and unselected:
            scores = []
            for uid in unselected:
                # relevance = score already implied by initial ranking
                rel = 1.0 - float(selected.index(selected[0])) / len(
                    candidate_ids
                )  # Proxy for relevance

                # diversity = max similarity to any selected
                selected_embeddings = [
                    embeddings[s] for s in selected if s in embeddings
                ]
                if not selected_embeddings or uid not in embeddings:
                    div = 0
                else:
                    div = (
                        max(
                            self.cosine_similarity(
                                [embeddings[uid]], selected_embeddings
                            )[0]
                        )
                        if selected_embeddings
                        else 0
                    )

                scores.append((lambda_param * rel - (1 - lambda_param) * div, uid))

            # pick the chunk with highest MMR score
            if not scores:
                break

            next_id = max(scores, key=lambda x: x[0])[1]
            selected.append(next_id)
            unselected.remove(next_id)

        return selected

    def get_dynamic_chunk_count(self, scores: List[float], min_chunks: int) -> int:
        """
        Dynamically determine how many chunks to use based on score distribution.

        Input Description: List of chunk scores in descending order, minimum of chunks
        Output Description: Recommended number of chunks to use
        """
        if not scores:
            return min_chunks

        # Calculate metrics from top scores
        top_n = min(5, len(scores))
        top_scores = scores[:top_n]
        avg_top = sum(top_scores) / len(top_scores)
        score_slope = top_scores[0] - top_scores[-1] if len(top_scores) > 1 else 0

        # Dynamic multiplier logic
        if avg_top < 0.015 or score_slope < 0.002:
            # Low confidence: flat or weak scores → try harder
            chunk_multiplier = 6
        elif avg_top < 0.020:
            chunk_multiplier = 4
        else:
            chunk_multiplier = 3

        return min_chunks * chunk_multiplier

    def _extract_entities_from_llm_response(self, response_text: str) -> List[str]:
        """
        Helper method to extract entities from LLM response with robust JSON parsing.

        Args:
            response_text: Raw text response from LLM

        Returns:
            List of extracted entities
        """
        if not response_text:
            return []

        entities = []

        # Try multiple approaches to extract entities
        try:
            # Approach 1: Direct JSON parsing if the response is a clean JSON array
            try:
                parsed = json.loads(response_text.strip())
                if isinstance(parsed, list):
                    entities = parsed
                    self.log.info(f"Extracted entities using direct JSON parsing")
                    return [
                        e.strip() for e in entities if isinstance(e, str) and e.strip()
                    ]
            except json.JSONDecodeError:
                pass

            # Approach 2: Extract JSON array using regex
            import re

            json_match = re.search(r"\[(.*?)\]", response_text, re.DOTALL)
            if json_match:
                try:
                    extracted_json = json_match.group(0)
                    parsed = json.loads(extracted_json)
                    if isinstance(parsed, list):
                        entities = parsed
                        self.log.info(f"Extracted entities using regex JSON extraction")
                        return [
                            e.strip()
                            for e in entities
                            if isinstance(e, str) and e.strip()
                        ]
                except json.JSONDecodeError:
                    pass

            # Approach 3: Look for entities in a comma-separated list
            comma_match = re.search(r'"(.*?)"', response_text)
            if comma_match:
                # Extract quoted strings
                quoted_strings = re.findall(r'"([^"]*)"', response_text)
                if quoted_strings:
                    self.log.info(f"Extracted entities from quoted strings")
                    return [e.strip() for e in quoted_strings if e.strip()]

            # Approach 4: Fall back to splitting by commas or newlines
            if "," in response_text:
                parts = [p.strip() for p in response_text.split(",")]
                # Remove any obvious non-entities like "entities:" prefixes
                parts = [
                    p
                    for p in parts
                    if not p.lower().startswith(("entities", "entity", "include"))
                ]
                # Remove quotes and brackets
                parts = [p.strip('"[]() ') for p in parts]
                if parts:
                    self.log.info(f"Extracted entities by splitting on commas")
                    return [p for p in parts if p]

            # Approach 5: Split by newlines
            parts = [p.strip() for p in response_text.split("\n")]
            # Look for lines that might be entities (not too long, not starting with explanatory text)
            parts = [
                p
                for p in parts
                if p
                and len(p) < 50
                and not p.lower().startswith(("i found", "here are", "entities"))
            ]
            # Remove bullets, quotes, etc.
            parts = [p.lstrip('-•*"[]() ').rstrip(',.;:")]') for p in parts]
            if parts:
                self.log.info(f"Extracted entities by splitting on newlines")
                return [p for p in parts if p]

        except Exception as e:
            self.log.error(f"Error extracting entities from LLM response: {str(e)}")

        return entities

    def get_payloads_for_chunk(self, chunk_id: str) -> List[Dict]:
        """
        Get associated payloads (images, tables) for a chunk.

        Input Description: ID of the chunk to get payloads for
        Output Description: List of payload data with metadata
        """
        cypher = """
        MATCH (c:__Chunk__ {id:$chunk_id})-[:HAS_PAYLOAD]->(p:__Payload__)
        RETURN p.assetId AS id, p.alt_text AS text, p.type AS type, p.data AS data
        """
        return graph_store.query(cypher, {"chunk_id": chunk_id})
