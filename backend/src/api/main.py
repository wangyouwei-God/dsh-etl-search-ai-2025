"""
FastAPI REST API for Dataset Search and Discovery

This module implements the REST API layer using FastAPI, exposing
the ETL, persistence, and semantic search capabilities.

Author: University of Manchester RSE Team
"""

import sys
import os
import logging
import time
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from api.models import (
    DatasetSchema,
    SearchResultSchema,
    SearchResponseSchema,
    HealthCheckSchema,
    ErrorSchema,
    MetadataSchema,
    BoundingBoxSchema
)

from infrastructure.persistence.sqlite.connection import get_database
from infrastructure.persistence.sqlite.dataset_repository_impl import SQLiteDatasetRepository
from infrastructure.persistence.vector.chroma_repository import ChromaVectorRepository
from infrastructure.services.embedding_service import HuggingFaceEmbeddingService
from domain.repositories.dataset_repository import DatasetNotFoundError
from domain.repositories.vector_repository import VectorRepositoryError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Global services (initialized at startup)
db = None
embedding_service = None
vector_repository = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI.
    
    Initializes services on startup and cleans up on shutdown.
    """
    global db, embedding_service, vector_repository
    
    logger.info("Initializing API services...")
    
    try:
        # Initialize database (use parent directory)
        backend_dir = Path(__file__).parent.parent.parent
        db_path = str(backend_dir / "datasets.db")
        db = get_database(db_path)
        logger.info(f"✓ Database initialized: {db_path}")

        # Initialize embedding service
        embedding_service = HuggingFaceEmbeddingService()
        logger.info(f"✓ Embedding service initialized: {embedding_service.get_model_name()}")

        # Initialize vector repository (use parent directory)
        chroma_path = str(backend_dir / "chroma_db")
        vector_repository = ChromaVectorRepository(chroma_path)
        logger.info(f"✓ Vector repository initialized: {chroma_path}, {vector_repository.count()} vectors")
        
        logger.info("API services ready!")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {str(e)}")
        raise
    
    yield
    
    # Cleanup on shutdown
    logger.info("Shutting down API services...")


# Create FastAPI application
app = FastAPI(
    title="Dataset Search and Discovery API",
    description="REST API for searching and discovering environmental datasets",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Dataset Search and Discovery API",
        "version": "1.0.0",
        "description": "REST API for semantic search over environmental datasets",
        "endpoints": {
            "health": "/health",
            "search": "/api/search?q={query}",
            "dataset": "/api/datasets/{id}",
            "all_datasets": "/api/datasets"
        }
    }


@app.get("/health", response_model=HealthCheckSchema, tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns the status of all services and database connections.
    """
    try:
        # Check database connection
        with db.session_scope() as session:
            repository = SQLiteDatasetRepository(session)
            dataset_count = repository.count()
        
        # Check vector database connection
        vector_count = vector_repository.count()
        
        return HealthCheckSchema(
            status="healthy",
            database_connected=True,
            vector_db_connected=True,
            total_datasets=dataset_count,
            total_vectors=vector_count,
            embedding_model=embedding_service.get_model_name(),
            embedding_dimension=embedding_service.get_dimension()
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


@app.get("/api/search", response_model=SearchResponseSchema, tags=["Search"])
async def search_datasets(
    q: str = Query(..., description="Search query text"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of results")
):
    """
    Semantic search endpoint.
    
    Performs semantic search over dataset embeddings using the query text.
    Returns datasets ranked by similarity score.
    
    Args:
        q: Search query (e.g., "land cover mapping")
        limit: Maximum number of results (1-100, default: 10)
    
    Returns:
        SearchResponseSchema with ranked results
    """
    start_time = time.time()
    
    try:
        logger.info(f"Search request: query='{q}', limit={limit}")
        
        # Generate query embedding
        query_embedding = embedding_service.generate_embedding(q)
        logger.debug(f"Generated {len(query_embedding)}-dimensional query embedding")
        
        # Search vector database
        vector_results = vector_repository.search(query_embedding, limit=limit)
        logger.info(f"Found {len(vector_results)} results")
        
        # Convert to API schema
        search_results = []
        for result in vector_results:
            metadata = result.metadata
            
            # Parse keywords (stored as string)
            keywords = []
            if 'keywords' in metadata:
                try:
                    keywords_str = metadata['keywords']
                    # Handle string representation of list
                    if keywords_str.startswith('[') and keywords_str.endswith(']'):
                        keywords = eval(keywords_str)  # Safe here as we control the data
                    else:
                        keywords = [keywords_str]
                except:
                    keywords = []
            
            # Parse geo extent
            has_geo_extent = metadata.get('has_geo_extent') == 'True'
            center_lat = None
            center_lon = None
            if has_geo_extent:
                try:
                    center_lat = float(metadata.get('center_lat', 0))
                    center_lon = float(metadata.get('center_lon', 0))
                except:
                    pass
            
            # Parse temporal extent
            has_temporal_extent = metadata.get('has_temporal_extent') == 'True'
            
            search_results.append(
                SearchResultSchema(
                    id=result.id,
                    title=metadata.get('title', 'Unknown'),
                    abstract=metadata.get('abstract', '')[:500],  # Truncated
                    score=result.score,
                    keywords=keywords,
                    has_geo_extent=has_geo_extent,
                    has_temporal_extent=has_temporal_extent,
                    center_lat=center_lat,
                    center_lon=center_lon
                )
            )
        
        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000  # Convert to ms
        
        return SearchResponseSchema(
            query=q,
            total_results=len(search_results),
            results=search_results,
            processing_time_ms=round(processing_time, 2)
        )
        
    except VectorRepositoryError as e:
        logger.error(f"Vector search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get("/api/datasets/{dataset_id}", response_model=DatasetSchema, tags=["Datasets"])
async def get_dataset(dataset_id: str):
    """
    Get dataset by ID.
    
    Returns complete dataset information including metadata.
    
    Args:
        dataset_id: Dataset UUID
    
    Returns:
        DatasetSchema with full metadata
    """
    try:
        logger.info(f"Get dataset request: id={dataset_id}")
        
        # Query database
        with db.session_scope() as session:
            repository = SQLiteDatasetRepository(session)
            result = repository.get_by_id(dataset_id)
        
        if not result:
            raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_id}")
        
        dataset, metadata = result
        
        # Convert to API schema
        metadata_schema = None
        if metadata:
            bounding_box_schema = None
            if metadata.bounding_box:
                bounding_box_schema = BoundingBoxSchema(
                    west_longitude=metadata.bounding_box.west_longitude,
                    east_longitude=metadata.bounding_box.east_longitude,
                    south_latitude=metadata.bounding_box.south_latitude,
                    north_latitude=metadata.bounding_box.north_latitude
                )
            
            metadata_schema = MetadataSchema(
                title=metadata.title,
                abstract=metadata.abstract,
                keywords=metadata.keywords,
                contact_organization=metadata.contact_organization,
                contact_email=metadata.contact_email,
                dataset_language=metadata.dataset_language,
                topic_category=metadata.topic_category,
                bounding_box=bounding_box_schema,
                temporal_extent_start=metadata.temporal_extent_start,
                temporal_extent_end=metadata.temporal_extent_end,
                metadata_date=metadata.metadata_date
            )
        
        return DatasetSchema(
            id=str(dataset.id),
            title=dataset.title,
            abstract=dataset.abstract,
            metadata_url=dataset.metadata_url,
            created_at=dataset.created_at,
            last_updated=dataset.last_updated,
            metadata=metadata_schema
        )
        
    except DatasetNotFoundError:
        raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_id}")
    except Exception as e:
        logger.error(f"Error retrieving dataset: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@app.get("/api/datasets", response_model=list[DatasetSchema], tags=["Datasets"])
async def list_datasets(
    limit: int = Query(10, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
):
    """
    List all datasets with pagination.
    
    Args:
        limit: Maximum number of results (1-100, default: 10)
        offset: Offset for pagination (default: 0)
    
    Returns:
        List of DatasetSchema
    """
    try:
        logger.info(f"List datasets request: limit={limit}, offset={offset}")
        
        # Query database
        with db.session_scope() as session:
            repository = SQLiteDatasetRepository(session)
            results = repository.get_all(limit=limit, offset=offset)
        
        # Convert to API schema
        datasets = []
        for dataset, metadata in results:
            metadata_schema = None
            if metadata:
                bounding_box_schema = None
                if metadata.bounding_box:
                    bounding_box_schema = BoundingBoxSchema(
                        west_longitude=metadata.bounding_box.west_longitude,
                        east_longitude=metadata.bounding_box.east_longitude,
                        south_latitude=metadata.bounding_box.south_latitude,
                        north_latitude=metadata.bounding_box.north_latitude
                    )
                
                metadata_schema = MetadataSchema(
                    title=metadata.title,
                    abstract=metadata.abstract,
                    keywords=metadata.keywords,
                    contact_organization=metadata.contact_organization,
                    contact_email=metadata.contact_email,
                    dataset_language=metadata.dataset_language,
                    topic_category=metadata.topic_category,
                    bounding_box=bounding_box_schema,
                    temporal_extent_start=metadata.temporal_extent_start,
                    temporal_extent_end=metadata.temporal_extent_end,
                    metadata_date=metadata.metadata_date
                )
            
            datasets.append(
                DatasetSchema(
                    id=str(dataset.id),
                    title=dataset.title,
                    abstract=dataset.abstract,
                    metadata_url=dataset.metadata_url,
                    created_at=dataset.created_at,
                    last_updated=dataset.last_updated,
                    metadata=metadata_schema
                )
            )
        
        return datasets
        
    except Exception as e:
        logger.error(f"Error listing datasets: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 80)
    print("Starting Dataset Search and Discovery API")
    print("=" * 80)
    print()
    print("API Documentation: http://localhost:8000/docs")
    print("Alternative Docs:  http://localhost:8000/redoc")
    print()
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
