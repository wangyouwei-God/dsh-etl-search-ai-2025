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
