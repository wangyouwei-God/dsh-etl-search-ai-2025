"""
Infrastructure: ChromaDB Vector Repository Implementation

This module implements the IVectorRepository interface using ChromaDB,
a local-first vector database optimized for embeddings.

Author: University of Manchester RSE Team
"""

import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))

import chromadb
from chromadb.config import Settings

from domain.repositories.vector_repository import (
    IVectorRepository,
    VectorSearchResult,
    VectorRepositoryError,
    VectorNotFoundError,
    VectorDimensionError
)

# Configure logging
logger = logging.getLogger(__name__)


class ChromaVectorRepository(IVectorRepository):
    """
    ChromaDB implementation of IVectorRepository.

    ChromaDB is a local-first vector database that stores embeddings
    and metadata, enabling fast similarity search. Data is persisted
    to disk in the specified directory.

    Design Pattern: Repository Pattern
    - Abstracts ChromaDB operations
    - Provides clean interface for vector operations
    - Handles error translation and logging

    Attributes:
        client: ChromaDB persistent client
        collection: ChromaDB collection for storing vectors
        collection_name: Name of the collection
        persist_directory: Path to persistence directory
    """

    DEFAULT_COLLECTION_NAME = "dataset_embeddings"

    def __init__(
        self,
        persist_directory: str = "chroma_db",
        collection_name: str = DEFAULT_COLLECTION_NAME
    ):
        """
        Initialize ChromaDB vector repository.

        Args:
            persist_directory: Directory for ChromaDB persistence
            collection_name: Name of the ChromaDB collection

        Example:
            >>> repo = ChromaVectorRepository("chroma_db")
            >>> repo.count()
            0
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name

        # Create persist directory if it doesn't exist
        Path(persist_directory).mkdir(parents=True, exist_ok=True)

        try:
            # Initialize ChromaDB client with persistence
            logger.info(f"Initializing ChromaDB at {persist_directory}")
            self.client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )

            # Get or create collection
            # ChromaDB uses cosine similarity by default
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}  # Cosine similarity
            )

            logger.info(
                f"ChromaDB initialized: collection='{collection_name}', "
                f"vectors={self.count()}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {str(e)}")
            raise VectorRepositoryError(f"ChromaDB initialization failed: {str(e)}")

    def upsert_vector(
        self,
        id: str,
        vector: List[float],
        metadata: Dict[str, Any]
    ) -> None:
        """
        Insert or update a vector with metadata.

        ChromaDB automatically handles upsert - if the ID exists,
        it updates; otherwise, it inserts.

        Args:
            id: Unique identifier for the vector
            vector: Dense embedding vector
            metadata: Associated metadata dictionary

        Raises:
            VectorRepositoryError: If upsert fails
        """
        try:
            # ChromaDB requires metadata values to be strings, ints, or floats
            # Convert complex types to strings
            sanitized_metadata = self._sanitize_metadata(metadata)

            # Upsert to ChromaDB
            self.collection.upsert(
                ids=[id],
                embeddings=[vector],
                metadatas=[sanitized_metadata]
            )

            logger.debug(f"Upserted vector: {id}")

        except Exception as e:
            logger.error(f"Failed to upsert vector {id}: {str(e)}")
            raise VectorRepositoryError(f"Upsert failed: {str(e)}")

    def upsert_vectors_batch(
        self,
        ids: List[str],
        vectors: List[List[float]],
        metadatas: List[Dict[str, Any]]
    ) -> None:
        """
        Insert or update multiple vectors in a batch.

        Args:
            ids: List of unique identifiers
            vectors: List of embedding vectors
            metadatas: List of metadata dictionaries

        Raises:
            VectorRepositoryError: If batch upsert fails
        """
        if not ids or not vectors or not metadatas:
            logger.warning("Empty batch provided for upsert")
            return

        if len(ids) != len(vectors) != len(metadatas):
            raise VectorRepositoryError(
                f"Length mismatch: ids={len(ids)}, vectors={len(vectors)}, "
                f"metadatas={len(metadatas)}"
            )

        try:
            # Sanitize all metadata
            sanitized_metadatas = [
                self._sanitize_metadata(metadata)
                for metadata in metadatas
            ]

            # Batch upsert to ChromaDB
            self.collection.upsert(
                ids=ids,
                embeddings=vectors,
                metadatas=sanitized_metadatas
            )

            logger.info(f"Batch upserted {len(ids)} vectors")

        except Exception as e:
            logger.error(f"Failed to batch upsert: {str(e)}")
            raise VectorRepositoryError(f"Batch upsert failed: {str(e)}")

    def search(
        self,
        query_vector: List[float],
        limit: int = 10
    ) -> List[VectorSearchResult]:
        """
        Search for similar vectors using cosine similarity.

        Args:
            query_vector: Query embedding vector
            limit: Maximum number of results to return

        Returns:
            List[VectorSearchResult]: Sorted by similarity (most similar first)
        """
        try:
            # Query ChromaDB
            results = self.collection.query(
                query_embeddings=[query_vector],
                n_results=limit,
                include=["metadatas", "distances"]
            )

            # Parse results
            search_results = []

            if results['ids'] and results['ids'][0]:
                ids = results['ids'][0]
                distances = results['distances'][0] if results['distances'] else [0.0] * len(ids)
                metadatas = results['metadatas'][0] if results['metadatas'] else [{}] * len(ids)

                for i, (id, distance, metadata) in enumerate(zip(ids, distances, metadatas)):
                    # Convert distance to similarity score
                    # ChromaDB cosine distance: 0 = identical, 2 = opposite
                    # Convert to similarity: 1 = identical, -1 = opposite
                    similarity = 1.0 - (distance / 2.0)

                    search_results.append(
                        VectorSearchResult(
                            id=id,
                            score=similarity,
                            metadata=metadata,
                            distance=distance
                        )
                    )

            logger.debug(f"Search returned {len(search_results)} results")
            return search_results

        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            raise VectorRepositoryError(f"Search failed: {str(e)}")

    def get_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve vector and metadata by ID.

        Args:
            id: Unique identifier

        Returns:
            Dict with 'vector' and 'metadata' keys, or None if not found
        """
        try:
            # Get from ChromaDB
            result = self.collection.get(
                ids=[id],
                include=["embeddings", "metadatas"]
            )

            if not result['ids']:
                return None

            return {
                'vector': result['embeddings'][0] if result['embeddings'] else None,
                'metadata': result['metadatas'][0] if result['metadatas'] else {}
            }

        except Exception as e:
            logger.error(f"Failed to get vector {id}: {str(e)}")
            raise VectorRepositoryError(f"Get failed: {str(e)}")

    def delete(self, id: str) -> bool:
        """
        Delete a vector by ID.

        Args:
            id: Unique identifier to delete

        Returns:
            bool: True if deleted, False if not found
        """
        try:
            # Check if exists
            existing = self.get_by_id(id)
            if not existing:
                return False

            # Delete from ChromaDB
            self.collection.delete(ids=[id])

            logger.info(f"Deleted vector: {id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete vector {id}: {str(e)}")
            raise VectorRepositoryError(f"Delete failed: {str(e)}")

    def count(self) -> int:
        """
        Count total number of vectors in the repository.

        Returns:
            int: Total vector count
        """
        try:
            return self.collection.count()
        except Exception as e:
            logger.error(f"Failed to count vectors: {str(e)}")
            raise VectorRepositoryError(f"Count failed: {str(e)}")

    def clear(self) -> None:
        """
        Clear all vectors from the repository.

        Warning:
            This operation is irreversible!
        """
        try:
            # Delete the collection and recreate it
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )

            logger.warning(f"Cleared all vectors from collection '{self.collection_name}'")

        except Exception as e:
            logger.error(f"Failed to clear collection: {str(e)}")
            raise VectorRepositoryError(f"Clear failed: {str(e)}")

    def _sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize metadata for ChromaDB compatibility.

        ChromaDB requires metadata values to be strings, ints, floats, or bools.
        Complex types (lists, dicts) are converted to strings.

        Args:
            metadata: Raw metadata dictionary

        Returns:
            Dict[str, Any]: Sanitized metadata
        """
        sanitized = {}

        for key, value in metadata.items():
            if value is None:
                continue  # Skip None values

            # Keep primitives as-is
            if isinstance(value, (str, int, float, bool)):
                sanitized[key] = value
            # Convert complex types to strings
            elif isinstance(value, (list, dict)):
                sanitized[key] = str(value)
            else:
                # Convert other types to string
                sanitized[key] = str(value)

        return sanitized

    def __repr__(self):
        """Return string representation."""
        return (
            f"ChromaVectorRepository(collection='{self.collection_name}', "
            f"vectors={self.count()}, path='{self.persist_directory}')"
        )
