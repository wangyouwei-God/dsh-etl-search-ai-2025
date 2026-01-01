"""
Domain Repository Interface: IVectorRepository

This module defines the repository interface for vector storage and similarity search.
This is part of the Domain layer and contains only the abstraction (interface).

The actual implementation will be in the Infrastructure layer (ChromaDB, Pinecone, etc.).

Author: University of Manchester RSE Team
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class VectorSearchResult:
    """
    Result from a vector similarity search.

    Attributes:
        id: Unique identifier of the document
        score: Similarity score (higher = more similar)
        metadata: Associated metadata dictionary
        distance: Distance metric (optional, lower = more similar)
    """
    id: str
    score: float
    metadata: Dict[str, Any]
    distance: Optional[float] = None


class IVectorRepository(ABC):
    """
    Repository interface for vector storage and similarity search.

    This interface defines the contract for vector database operations,
    enabling semantic search over dataset embeddings.

    Design Pattern: Repository Pattern
    - Abstracts vector database operations
    - Domain layer defines the interface
    - Infrastructure layer provides implementations (ChromaDB, Pinecone, etc.)

    SOLID Principles:
    - Dependency Inversion: Domain depends on abstraction
    - Interface Segregation: Focused interface for vector operations
    - Single Responsibility: Only handles vector storage and search
    """

    @abstractmethod
    def upsert_vector(
        self,
        id: str,
        vector: List[float],
        metadata: Dict[str, Any]
    ) -> None:
        """
        Insert or update a vector with metadata.

        If a vector with the given ID already exists, it will be updated.
        Otherwise, a new vector is inserted.

        Args:
            id: Unique identifier for the vector (e.g., dataset UUID)
            vector: Dense embedding vector (e.g., 384 dimensions)
            metadata: Associated metadata dictionary (e.g., title, abstract)

        Raises:
            VectorRepositoryError: If upsert operation fails

        Example:
            >>> repo = ChromaVectorRepository()
            >>> vector = [0.1, 0.2, 0.3, ...]  # 384 dimensions
            >>> metadata = {"title": "Land Cover Map", "abstract": "..."}
            >>> repo.upsert_vector("dataset-123", vector, metadata)
        """
        pass

    @abstractmethod
    def upsert_vectors_batch(
        self,
        ids: List[str],
        vectors: List[List[float]],
        metadatas: List[Dict[str, Any]]
    ) -> None:
        """
        Insert or update multiple vectors in a batch.

        Batch operations are more efficient for bulk inserts.

        Args:
            ids: List of unique identifiers
            vectors: List of embedding vectors
            metadatas: List of metadata dictionaries

        Raises:
            VectorRepositoryError: If batch upsert fails

        Example:
            >>> repo = ChromaVectorRepository()
            >>> ids = ["id1", "id2"]
            >>> vectors = [[0.1, 0.2, ...], [0.3, 0.4, ...]]
            >>> metadatas = [{"title": "Dataset 1"}, {"title": "Dataset 2"}]
            >>> repo.upsert_vectors_batch(ids, vectors, metadatas)
        """
        pass

    @abstractmethod
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

        Example:
            >>> repo = ChromaVectorRepository()
            >>> query = [0.1, 0.2, 0.3, ...]  # Query embedding
            >>> results = repo.search(query, limit=5)
            >>> for result in results:
            ...     print(f"{result.metadata['title']}: {result.score}")
        """
        pass

    @abstractmethod
    def get_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve vector and metadata by ID.

        Args:
            id: Unique identifier

        Returns:
            Dict with 'vector' and 'metadata' keys, or None if not found

        Example:
            >>> repo = ChromaVectorRepository()
            >>> result = repo.get_by_id("dataset-123")
            >>> if result:
            ...     print(result['metadata']['title'])
        """
        pass

    @abstractmethod
    def delete(self, id: str) -> bool:
        """
        Delete a vector by ID.

        Args:
            id: Unique identifier to delete

        Returns:
            bool: True if deleted, False if not found

        Example:
            >>> repo = ChromaVectorRepository()
            >>> repo.delete("dataset-123")
            True
        """
        pass

    @abstractmethod
    def count(self) -> int:
        """
        Count total number of vectors in the repository.

        Returns:
            int: Total vector count

        Example:
            >>> repo = ChromaVectorRepository()
            >>> total = repo.count()
            >>> print(f"Total vectors: {total}")
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """
        Clear all vectors from the repository.

        Warning:
            This operation is irreversible!

        Example:
            >>> repo = ChromaVectorRepository()
            >>> repo.clear()  # Deletes all vectors
        """
        pass


class VectorRepositoryError(Exception):
    """Base exception for vector repository operations."""
    pass


class VectorNotFoundError(VectorRepositoryError):
    """Raised when a vector is not found in the repository."""

    def __init__(self, vector_id: str):
        self.vector_id = vector_id
        super().__init__(f"Vector not found: {vector_id}")


class VectorDimensionError(VectorRepositoryError):
    """Raised when vector dimension doesn't match expected dimension."""

    def __init__(self, expected: int, actual: int):
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"Vector dimension mismatch: expected {expected}, got {actual}"
        )
