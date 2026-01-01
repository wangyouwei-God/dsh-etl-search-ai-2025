"""
Infrastructure: HuggingFace Embedding Service Implementation

This module implements the IEmbeddingService interface using sentence-transformers
from HuggingFace. It provides local, CPU-based text embedding generation.

Author: University of Manchester RSE Team
"""

import logging
from typing import List
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from sentence_transformers import SentenceTransformer
import numpy as np

from application.interfaces.embedding_service import (
    IEmbeddingService,
    EmbeddingError,
    ModelLoadError,
    TextEmbeddingError
)

# Configure logging
logger = logging.getLogger(__name__)


class HuggingFaceEmbeddingService(IEmbeddingService):
    """
    HuggingFace sentence-transformers implementation of IEmbeddingService.

    This service uses the 'all-MiniLM-L6-v2' model, which provides:
    - 384-dimensional embeddings
    - Fast inference (suitable for CPU)
    - Good quality for semantic search
    - Small model size (~80MB)

    Design Pattern: Strategy Pattern
    - Concrete strategy for text embedding
    - Can be replaced with other embedding services (OpenAI, Cohere, etc.)

    Attributes:
        model: SentenceTransformer model instance
        model_name: Name of the HuggingFace model
        dimension: Embedding dimensionality
    """

    DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

    def __init__(self, model_name: str = DEFAULT_MODEL, device: str = "cpu"):
        """
        Initialize the HuggingFace embedding service.

        Args:
            model_name: HuggingFace model identifier (default: all-MiniLM-L6-v2)
            device: Device to run model on ('cpu' or 'cuda')

        Raises:
            ModelLoadError: If model fails to load

        Example:
            >>> service = HuggingFaceEmbeddingService()
            >>> service.get_dimension()
            384
        """
        self.model_name = model_name
        self.device = device

        try:
            logger.info(f"Loading embedding model: {model_name} on {device}")
            self.model = SentenceTransformer(model_name, device=device)
            self.dimension = self.model.get_sentence_embedding_dimension()
            logger.info(f"Model loaded successfully (dimension={self.dimension})")

        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {str(e)}")
            raise ModelLoadError(model_name, str(e))

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate a dense vector embedding from text.

        The model encodes text into a 384-dimensional vector using
        sentence-transformers. The embedding captures semantic meaning
        and can be used for similarity search.

        Args:
            text: Input text to embed

        Returns:
            List[float]: 384-dimensional embedding vector

        Raises:
            TextEmbeddingError: If embedding generation fails

        Example:
            >>> service = HuggingFaceEmbeddingService()
            >>> text = "Land cover map of Great Britain"
            >>> embedding = service.generate_embedding(text)
            >>> len(embedding)
            384
            >>> all(isinstance(x, float) for x in embedding)
            True
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            raise TextEmbeddingError(text, "Text is empty or whitespace-only")

        try:
            # Generate embedding
            logger.debug(f"Generating embedding for text: {text[:100]}...")
            embedding = self.model.encode(text, convert_to_numpy=True)

            # Convert numpy array to Python list
            embedding_list = embedding.tolist()

            logger.debug(f"Generated embedding with {len(embedding_list)} dimensions")
            return embedding_list

        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            raise TextEmbeddingError(text, str(e))

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in a batch.

        Batch processing is more efficient than individual calls
        for large datasets.

        Args:
            texts: List of texts to embed

        Returns:
            List[List[float]]: List of embedding vectors

        Raises:
            TextEmbeddingError: If batch embedding fails

        Example:
            >>> service = HuggingFaceEmbeddingService()
            >>> texts = ["Climate data", "Land cover map"]
            >>> embeddings = service.generate_embeddings_batch(texts)
            >>> len(embeddings)
            2
            >>> len(embeddings[0])
            384
        """
        if not texts:
            logger.warning("Empty text list provided for batch embedding")
            return []

        try:
            logger.info(f"Generating batch embeddings for {len(texts)} texts")
            embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)

            # Convert numpy arrays to Python lists
            embeddings_list = [emb.tolist() for emb in embeddings]

            logger.info(f"Generated {len(embeddings_list)} embeddings")
            return embeddings_list

        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {str(e)}")
            raise TextEmbeddingError(f"Batch of {len(texts)} texts", str(e))

    def get_dimension(self) -> int:
        """
        Get the dimensionality of embeddings.

        Returns:
            int: Embedding dimension (384 for all-MiniLM-L6-v2)
        """
        return self.dimension

    def get_model_name(self) -> str:
        """
        Get the name of the embedding model.

        Returns:
            str: Model name identifier
        """
        return self.model_name

    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Compute cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            float: Cosine similarity score (-1 to 1, higher = more similar)

        Example:
            >>> service = HuggingFaceEmbeddingService()
            >>> emb1 = service.generate_embedding("climate change")
            >>> emb2 = service.generate_embedding("global warming")
            >>> similarity = service.compute_similarity(emb1, emb2)
            >>> 0.5 < similarity < 1.0  # Should be highly similar
            True
        """
        # Convert to numpy arrays
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        # Compute cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)
        return float(similarity)

    def __repr__(self):
        """Return string representation."""
        return f"HuggingFaceEmbeddingService(model='{self.model_name}', dimension={self.dimension})"
