#!/usr/bin/env python3
"""
Demo Script: Supporting Document RAG

This script demonstrates:
1. Fetching supporting documents for a sample dataset
2. Extracting text from PDF documents
3. Creating embeddings and storing in vector database
4. Testing RAG search with the new documents

Usage:
    cd backend
    PYTHONPATH=src python3 -m src.scripts.demo_supporting_doc_rag
    
Author: University of Manchester RSE Team
"""

import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Run the supporting document RAG demo."""
    
    print("\n" + "=" * 60)
    print("  Supporting Document RAG Demo")
    print("  Dataset Search and Discovery Solution")
    print("=" * 60 + "\n")
    
    # Import services
    try:
        from infrastructure.etl.supporting_doc_fetcher import SupportingDocFetcher
        from infrastructure.persistence.vector.chroma_repository import ChromaVectorRepository
        from infrastructure.services.embedding_service import HuggingFaceEmbeddingService
        from application.services.document_embedding_service import DocumentEmbeddingService
        logger.info("Services imported successfully")
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error("Please ensure you are running from the backend directory with PYTHONPATH=src")
        return 1
    
    # Initialize services
    print("\n[1/5] Initializing services...")
    try:
        embedding_service = HuggingFaceEmbeddingService()
        vector_repository = ChromaVectorRepository(
            collection_name="supporting_docs",
            persist_directory="chroma_db"
        )
        doc_embedding_service = DocumentEmbeddingService(
            embedding_service=embedding_service,
            vector_repository=vector_repository
        )
        doc_fetcher = SupportingDocFetcher(download_dir="supporting_docs")
        print("   ✓ All services initialized")
    except Exception as e:
        logger.error(f"Service initialization failed: {e}")
        return 1
    
    # Sample dataset IDs (from our 200 datasets)
    sample_dataset_ids = [
        "be0bdc0e-bc2e-4f1d-b524-2c02798dd893",  # Land Cover Map 2020
        "3aaa52d3-d0e1-4c10-b37e-c3d52d9c6968",  # Another sample
    ]
    
    print(f"\n[2/5] Discovering supporting documents for {len(sample_dataset_ids)} sample datasets...")
    all_docs = []
    
    for dataset_id in sample_dataset_ids:
        print(f"\n   Dataset: {dataset_id[:8]}...")
        try:
            docs = doc_fetcher.discover_documents(dataset_id)
            print(f"   ✓ Found {len(docs)} documents")
            all_docs.extend(docs)
        except Exception as e:
            logger.warning(f"   ✗ Discovery failed: {e}")
    
    if not all_docs:
        print("\n   No supporting documents found. Creating sample document for demo...")
        # Create a sample document for demo purposes
        sample_doc_path = Path("supporting_docs/sample_methodology.txt")
        sample_doc_path.parent.mkdir(parents=True, exist_ok=True)
        sample_doc_path.write_text("""
UK Land Cover Map Methodology

1. Introduction
The UK Land Cover Map provides detailed information about land cover 
and land use across the United Kingdom. This document describes the 
methodology used for data collection and classification.

2. Data Sources
- Satellite imagery: Sentinel-2 and Landsat 8
- Aerial photography: UKCEH ortho imagery
- Ground truth data: Field surveys

3. Classification System
The classification follows the UKCEH Land Cover Classes:
- Broadleaved Woodland
- Coniferous Woodland
- Arable and Horticulture
- Improved Grassland
- Neutral Grassland
- Calcareous Grassland
- Acid Grassland
- Fen, Marsh and Swamp
- Heather
- Heather Grassland
- Bog
- Montane Habitats
- Inland Rock
- Freshwater
- Coastal
- Urban and Suburban
        """)
        print(f"   ✓ Created sample document: {sample_doc_path}")
    
    print(f"\n[3/5] Processing documents for embedding...")
    total_chunks = 0
    processed_files = []
    
    # Process downloaded documents or sample document
    doc_directory = Path("supporting_docs")
    if doc_directory.exists():
        for file_path in list(doc_directory.rglob("*.txt"))[:3] + list(doc_directory.rglob("*.pdf"))[:2]:
            print(f"\n   Processing: {file_path.name}")
            try:
                # Determine dataset ID from path or use first sample
                dataset_id = sample_dataset_ids[0]
                if file_path.parent.name and len(file_path.parent.name) > 30:
                    dataset_id = file_path.parent.name
                
                chunks = doc_embedding_service.process_document(
                    str(file_path),
                    dataset_id,
                    "supporting_doc"
                )
                total_chunks += len(chunks)
                processed_files.append(file_path.name)
                print(f"   ✓ Created {len(chunks)} chunks")
            except Exception as e:
                logger.warning(f"   ✗ Processing failed: {e}")
    
    print(f"\n   Total: {total_chunks} chunks from {len(processed_files)} files")
    
    print(f"\n[4/5] Testing vector search...")
    test_queries = [
        "land cover classification methodology",
        "satellite imagery data sources",
        "woodland habitats UK"
    ]
    
    for query in test_queries:
        print(f"\n   Query: '{query}'")
        try:
            results = vector_repository.search(
                query_vector=embedding_service.generate_embedding(query),
                limit=3
            )
            if results:
                for i, result in enumerate(results, 1):
                    title = result.metadata.get('title', result.id)[:40]
                    print(f"   {i}. {title}... (score: {result.score:.3f})")
            else:
                print("   No results found")
        except Exception as e:
            logger.warning(f"   Search failed: {e}")
    
    print(f"\n[5/5] Summary")
    print("=" * 60)
    print(f"   Datasets processed: {len(sample_dataset_ids)}")
    print(f"   Documents found: {len(all_docs)}")
    print(f"   Files processed: {len(processed_files)}")
    print(f"   Chunks embedded: {total_chunks}")
    print(f"   Vector collection: supporting_docs")
    print("=" * 60)
    
    print("\n✓ Supporting Document RAG demo completed successfully!\n")
    
    # Cleanup
    doc_fetcher.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
