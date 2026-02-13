"""
Pydantic models for RAG Agent data structures
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class SearchResult(BaseModel):
    """A single search result from document retrieval"""
    id: str = Field(description="Document/chunk identifier")
    text: str = Field(description="Content of the document/chunk")
    score: float = Field(description="Relevance score")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class VectorSearchResponse(BaseModel):
    """Response from vector search"""
    results: List[SearchResult] = Field(description="List of search results")
    count: int = Field(description="Number of results returned")
    query: str = Field(description="Original search query")


class EntityExtractionResponse(BaseModel):
    """Response from entity extraction"""
    entities: List[str] = Field(description="Extracted entity names")
    count: int = Field(description="Number of entities extracted")
    text_preview: Optional[str] = Field(default=None, description="Preview of analyzed text")


class GraphSearchResponse(BaseModel):
    """Response from graph-based search"""
    results: List[Dict[str, Any]] = Field(description="Query results")
    count: int = Field(description="Number of results")
    query: str = Field(description="Generated Cypher query")


class HybridSearchResponse(BaseModel):
    """Response from hybrid search combining vector and lexical"""
    results: List[SearchResult] = Field(description="Fused search results")
    count: int = Field(description="Number of results")
    method: str = Field(default="hybrid_rrf", description="Search method used")
    retrieval_debug: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "Optional retrieval diagnostics. Expected keys: "
            "source_hits, weights, confidence, score_gap_top1_top5, "
            "cross_encoder_used, context_tokens, citation_audit"
        ),
    )


class GraphRelationship(BaseModel):
    """A relationship between entities in the graph"""
    source: str = Field(description="Source entity name")
    target: str = Field(description="Target entity name")
    relationship_type: str = Field(description="Type of relationship")
    properties: Optional[Dict[str, Any]] = Field(default=None, description="Relationship properties")


class GraphBasedRetrievalResponse(BaseModel):
    """Response from graph-based retrieval"""
    results: List[SearchResult] = Field(description="Retrieved documents")
    count: int = Field(description="Number of results")
    entities: List[str] = Field(description="Entities used for retrieval")


class HydeSearchResponse(BaseModel):
    """Response from HyDE (Hypothetical Document Embeddings) search"""
    results: List[SearchResult] = Field(description="Search results")
    count: int = Field(description="Number of results")
    method: str = Field(default="hyde", description="Search method used")
    hypothetical_document: str = Field(description="Generated hypothetical document used for embedding")


class BM25RerankResponse(BaseModel):
    """Response from BM25 reranking"""
    results: List[Dict[str, Any]] = Field(description="Re-ranked documents with BM25 scores")
    count: int = Field(description="Number of results")
    params: Dict[str, float] = Field(description="BM25 parameters used (k1, b, avgdl)")
    query_terms: List[str] = Field(description="Tokenized query terms")


class CrossEncoderRerankResponse(BaseModel):
    """Response from cross-encoder reranking"""
    results: List[Dict[str, Any]] = Field(description="Re-ranked documents with cross-encoder scores")
    count: int = Field(description="Number of results")
    method: str = Field(default="llm_cross_encoder", description="Reranking method used")


class RRFResponse(BaseModel):
    """Response from Reciprocal Rank Fusion"""
    results: List[Dict[str, Any]] = Field(description="Fused results with RRF scores and source contributions")
    count: int = Field(description="Number of results")
    sources: List[str] = Field(description="Source ranked lists used")
    weights: Dict[str, float] = Field(description="Weights applied per source")
    k: int = Field(description="RRF constant used")


class QueryExpansionResponse(BaseModel):
    """Response from query expansion"""
    original_query: str = Field(description="Original search query")
    synonyms: List[str] = Field(default_factory=list, description="Synonym terms")
    related_terms: List[str] = Field(default_factory=list, description="Related concept terms")
    rephrased_queries: List[str] = Field(default_factory=list, description="Alternative query phrasings")
    expanded_query: str = Field(description="Original query enriched with expansion terms")


class ChunkContextResponse(BaseModel):
    """Response from contextual chunk expansion"""
    chunk_id: str = Field(description="Requested chunk ID")
    chunks: List[Dict[str, Any]] = Field(description="Chunk with surrounding context chunks")
    count: int = Field(description="Number of chunks returned")


class ErrorResponse(BaseModel):
    """Standardized error response for all RAG tools"""
    error: str = Field(description="Error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error context")


class CommunityRetrievalResponse(BaseModel):
    """Response from community-based retrieval"""
    results: List[Dict[str, Any]] = Field(description="Retrieved chunks with community context")
    count: int = Field(description="Number of results")


class PayloadSearchResponse(BaseModel):
    """Response from payload search"""
    results: List[Dict[str, Any]] = Field(description="Payload search results")
    count: int = Field(description="Number of results")
    modalities_searched: List[str] = Field(
        default_factory=list,
        description="Payload retrieval channels queried (text/image/audio/video)"
    )


class LexicalSearchResponse(BaseModel):
    """Response from lexical (full-text) search"""
    results: List[SearchResult] = Field(description="List of search results")
    count: int = Field(description="Number of results returned")
    query: str = Field(description="Original search query")


class GraphRagAnswerResponse(BaseModel):
    """Response from the end-to-end GraphRAG answer pipeline"""
    answer: str = Field(description="Synthesized answer grounded in retrieved context")
    citations: List[str] = Field(default_factory=list, description="Chunk IDs cited in the answer")
    retrieved_chunks: List[str] = Field(default_factory=list, description="All chunk IDs used for context")
    retrieval: Dict[str, Any] = Field(default_factory=dict, description="Retrieval statistics per source")
    retrieval_debug: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "Optional retrieval diagnostics. Expected keys: "
            "source_hits, weights, confidence, score_gap_top1_top5, "
            "cross_encoder_used, context_tokens, citation_audit"
        ),
    )
