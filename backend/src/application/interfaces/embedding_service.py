"""
Application Interface: IEmbeddingService

This module defines the interface for text embedding services.
Embedding services convert text into dense vector representations
for semantic search and similarity matching.

Author: University of Manchester RSE Team
"""

from abc import ABC, abstractmethod
from typing import List


class IEmbeddingService(ABC):
    """
    Interface for text embedding services.

    This interface defines the contract for services that generate
    dense vector embeddings from text. Embeddings enable semantic
    search by representing text meaning in vector space.

    Design Pattern: Strategy Pattern
    - Different embedding models can be used (HuggingFace, OpenAI, etc.)
    - Application layer defines the interface
    - Infrastructure layer provides implementations

    SOLID Principles:
    - Dependency Inversion: Application depends on abstraction
    - Interface Segregation: Focused interface for embedding generation
    - Single Responsibility: Only handles text-to-vector conversion
    """

    @abstractmethod
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate a dense vector embedding from text.

        This method converts input text into a fixed-length vector
        representation that captures semantic meaning. Similar texts
        will have similar vectors (measured by cosine similarity).

        Args:
            text: Input text to embed (e.g., title + abstract)

        Returns:
            List[float]: Dense vector embedding (typically 384-768 dimensions)

        Raises:
            EmbeddingError: If embedding generation fails

        Example:
            >>> service = HuggingFaceEmbeddingService()
            >>> embedding = service.generate_embedding("Land cover map")
            >>> len(embedding)  # Model-dependent dimension
            384
            >>> isinstance(embedding[0], float)
            True
        """
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        """
        Get the dimensionality of embeddings produced by this service.

        Returns:
            int: Number of dimensions in the embedding vector

        Example:
            >>> service = HuggingFaceEmbeddingService()
            >>> service.get_dimension()
            384
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """
        Get the name/identifier of the underlying embedding model.

        Returns:
            str: Model name or identifier

        Example:
            >>> service = HuggingFaceEmbeddingService()
            >>> service.get_model_name()
            'sentence-transformers/all-MiniLM-L6-v2'
        """
        pass


class EmbeddingError(Exception):
    """Base exception for embedding service operations."""
    pass


class ModelLoadError(EmbeddingError):
    """Raised when the embedding model fails to load."""

    def __init__(self, model_name: str, reason: str):
        self.model_name = model_name
        self.reason = reason
        super().__init__(f"Failed to load model '{model_name}': {reason}")


class TextEmbeddingError(EmbeddingError):
    """Raised when text embedding generation fails."""

    def __init__(self, text_preview: str, reason: str):
        self.text_preview = text_preview[:100] + "..." if len(text_preview) > 100 else text_preview
        self.reason = reason
        super().__init__(f"Failed to embed text '{self.text_preview}': {reason}")
