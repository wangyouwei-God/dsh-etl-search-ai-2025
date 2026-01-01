#!/usr/bin/env python3
"""
Test script for semantic search functionality.

This script demonstrates semantic search over dataset embeddings
using the HuggingFace embedding service and ChromaDB.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from infrastructure.services.embedding_service import HuggingFaceEmbeddingService
from infrastructure.persistence.vector.chroma_repository import ChromaVectorRepository


def main():
    print("=" * 80)
    print("SEMANTIC SEARCH DEMONSTRATION")
    print("=" * 80)
    print()

    # Initialize services
    print("Initializing embedding service...")
    embedding_service = HuggingFaceEmbeddingService()
    print(f"✓ Model: {embedding_service.get_model_name()}")
    print(f"✓ Dimension: {embedding_service.get_dimension()}")
    print()

    print("Initializing vector repository...")
    vector_repo = ChromaVectorRepository("chroma_db")
    print(f"✓ Total vectors: {vector_repo.count()}")
    print()

    # Test queries
    queries = [
        "land cover mapping",
        "geographic data of Great Britain",
        "environmental datasets",
        "climate change data",
    ]

    for query in queries:
        print("=" * 80)
        print(f"Query: '{query}'")
        print("-" * 80)

        # Generate query embedding
        query_embedding = embedding_service.generate_embedding(query)
        print(f"✓ Generated {len(query_embedding)}-dimensional query embedding")

        # Search for similar vectors
        results = vector_repo.search(query_embedding, limit=3)
        print(f"✓ Found {len(results)} similar datasets:")
        print()

        # Display results
        for i, result in enumerate(results, 1):
            print(f"{i}. Similarity: {result.score:.4f} (distance: {result.distance:.4f})")
            print(f"   ID: {result.id}")
            print(f"   Title: {result.metadata.get('title', 'N/A')}")
            print(f"   Keywords: {result.metadata.get('keywords', 'N/A')}")

            if result.metadata.get('has_geo_extent') == 'True':
                center_lat = result.metadata.get('center_lat', 'N/A')
                center_lon = result.metadata.get('center_lon', 'N/A')
                print(f"   Geographic Center: {center_lat}°N, {center_lon}°E")

            if result.metadata.get('has_temporal_extent') == 'True':
                temporal_start = result.metadata.get('temporal_start', 'N/A')
                temporal_end = result.metadata.get('temporal_end', 'N/A')
                print(f"   Temporal Range: {temporal_start} to {temporal_end}")

            print()

    # Test similarity computation
    print("=" * 80)
    print("SIMILARITY COMPUTATION TEST")
    print("-" * 80)

    text1 = "land cover map"
    text2 = "vegetation mapping"
    text3 = "climate change"

    emb1 = embedding_service.generate_embedding(text1)
    emb2 = embedding_service.generate_embedding(text2)
    emb3 = embedding_service.generate_embedding(text3)

    sim_1_2 = embedding_service.compute_similarity(emb1, emb2)
    sim_1_3 = embedding_service.compute_similarity(emb1, emb3)

    print(f"'{text1}' vs '{text2}': {sim_1_2:.4f}")
    print(f"'{text1}' vs '{text3}': {sim_1_3:.4f}")
    print()

    print("=" * 80)
    print("SEMANTIC SEARCH TEST COMPLETED")
    print("=" * 80)


if __name__ == '__main__':
    main()
