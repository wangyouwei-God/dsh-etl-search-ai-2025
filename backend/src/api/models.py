"""
API Models (Pydantic Schemas)

This module defines the Pydantic models for API request/response validation.
These are separate from domain entities to maintain Clean Architecture.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class BoundingBoxSchema(BaseModel):
    """Geographic bounding box schema."""
    west_longitude: float
    east_longitude: float
    south_latitude: float
    north_latitude: float


class MetadataSchema(BaseModel):
    """Dataset metadata schema for API responses."""
    title: str
    abstract: str
    keywords: List[str] = []
    contact_organization: Optional[str] = None
    contact_email: Optional[str] = None
    dataset_language: Optional[str] = "eng"
    topic_category: Optional[str] = None
    bounding_box: Optional[BoundingBoxSchema] = None
    temporal_extent_start: Optional[datetime] = None
    temporal_extent_end: Optional[datetime] = None
    metadata_date: Optional[datetime] = None


class DatasetSchema(BaseModel):
    """Dataset schema for API responses."""
    id: str
    title: str
    abstract: str
    metadata_url: str
    created_at: datetime
    last_updated: datetime
    metadata: Optional[MetadataSchema] = None


class SearchResultSchema(BaseModel):
    """Search result schema."""
    id: str
    title: str
    abstract: str
    score: float = Field(..., description="Similarity score (0-1, higher = more similar)")
    keywords: List[str] = []
    has_geo_extent: bool = False
    has_temporal_extent: bool = False
    center_lat: Optional[float] = None
    center_lon: Optional[float] = None


class SearchResponseSchema(BaseModel):
    """Search response schema."""
    query: str
    total_results: int
    results: List[SearchResultSchema]
    processing_time_ms: float


class HealthCheckSchema(BaseModel):
    """Health check response schema."""
    status: str
    database_connected: bool
    vector_db_connected: bool
    total_datasets: int
    total_vectors: int
    embedding_model: str
    embedding_dimension: int


class ErrorSchema(BaseModel):
    """Error response schema."""
    detail: str
    error_type: Optional[str] = None


# ============================================================================
# Chat/RAG Schemas
# ============================================================================

class ChatSourceSchema(BaseModel):
    """Source citation in chat response."""
    id: str
    title: str
    source_type: str = "dataset"  # 'dataset' or 'document'
    relevance_score: float
    content_preview: Optional[str] = None


class ChatRequestSchema(BaseModel):
    """Chat request schema."""
    message: str = Field(..., description="User message", min_length=1, max_length=5000)
    conversation_id: Optional[str] = Field(None, description="ID of existing conversation")
    include_sources: bool = Field(True, description="Include source citations")


class ChatResponseSchema(BaseModel):
    """Chat response schema."""
    answer: str
    conversation_id: str
    sources: List[ChatSourceSchema] = []
    processing_time_ms: float


class ConversationTurnSchema(BaseModel):
    """A single turn in a conversation."""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: datetime


class ConversationSchema(BaseModel):
    """Conversation schema for listing."""
    id: str
    turns_count: int
    created_at: datetime
    updated_at: datetime

