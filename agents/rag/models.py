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
