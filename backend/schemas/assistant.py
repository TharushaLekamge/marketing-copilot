"""Schemas for assistant/RAG endpoints."""

from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AssistantQueryRequest(BaseModel):
    """Request schema for assistant query."""

    project_id: UUID = Field(..., description="ID of the project to search within")
    question: str = Field(..., description="User's question", min_length=1)
    top_k: int = Field(default=5, description="Number of relevant chunks to retrieve", ge=1, le=20)
    include_citations: bool = Field(default=True, description="Whether to include citations in response")


class Citation(BaseModel):
    """Schema for a citation from retrieved chunks."""

    index: int = Field(..., description="Citation index (1-based)")
    text: str = Field(..., description="Text excerpt from the source")
    asset_id: str = Field(..., description="Asset ID of the source document")
    chunk_index: int = Field(..., description="Chunk index within the asset")
    score: float = Field(..., description="Similarity score of the chunk")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata about the source")


class AssistantQueryMetadata(BaseModel):
    """Metadata about the RAG query."""

    model: str = Field(..., description="Model used for generation")
    provider: str = Field(..., description="LLM provider")
    project_id: str = Field(..., description="Project ID")
    chunks_retrieved: int = Field(..., description="Number of chunks retrieved")
    has_context: bool = Field(..., description="Whether context was found")


class AssistantQueryResponse(BaseModel):
    """Response schema for assistant query."""

    answer: str = Field(..., description="Generated answer from the assistant")
    citations: List[Citation] = Field(default_factory=list, description="List of citations from source documents")
    metadata: AssistantQueryMetadata = Field(..., description="RAG query metadata")
