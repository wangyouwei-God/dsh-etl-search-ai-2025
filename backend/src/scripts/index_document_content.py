#!/usr/bin/env python3
"""
Index Document Content Pipeline

This script implements the full RAG content indexing pipeline:
1. Retrieves all supporting documents from database
2. Extracts text content using ContentExtractor
3. Chunks text into semantic units
4. Generates embeddings for each chunk
5. Stores in ChromaDB for semantic search

This enables TRUE RAG capability by indexing actual document content,
not just metadata.

Author: University of Manchester RSE Team
"""

import sys
import os
from pathlib import Path
import logging
from datetime import datetime
import sqlite3

# Add backend/src to path for local imports
SCRIPT_DIR = Path(__file__).resolve().parent
SRC_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SRC_DIR))

from infrastructure.etl.content_extractor import ContentExtractor, DocumentIndexer
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DocumentContentIndexingPipeline:
    """
    Orchestrates the document content indexing process.

    This is a batch processing pipeline that:
    - Reads supporting documents from database
    - Extracts text content
    - Generates semantic embeddings
    - Stores in vector database
    """

    def __init__(self, db_path: str, chroma_path: str):
        """
        Initialize the indexing pipeline.

        Args:
            db_path: Path to SQLite database
            chroma_path: Path to ChromaDB storage
        """
        self.db_path = db_path
        self.chroma_path = chroma_path

        # Initialize components
        logger.info("Initializing embedding model...")
        self.embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

        logger.info("Connecting to ChromaDB...")
        self.chroma_client = chromadb.PersistentClient(
            path=chroma_path,
            settings=Settings(anonymized_telemetry=False)
        )

        # Get or create collection for document content
        self.content_collection = self.chroma_client.get_or_create_collection(
            name="document_content",
            metadata={"description": "Full-text content from supporting documents"}
        )

        logger.info("Initializing content extractor...")
        self.indexer = DocumentIndexer(
            vector_db=self.content_collection,
            embedding_service=self.embedding_model
        )

        self.stats = {
            'total_docs': 0,
            'processed': 0,
            'indexed': 0,
            'failed': 0,
            'total_chunks': 0,
            'skipped_unsupported': 0,
            'skipped_missing': 0
        }

    def get_supporting_documents(self):
        """
        Retrieve all supporting documents from database.

        Returns:
            List of tuples: (id, dataset_id, file_path, file_type)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, dataset_id, file_path, filename
            FROM supporting_documents
            ORDER BY created_at DESC
        ''')

        docs = cursor.fetchall()
        conn.close()

        return docs

    def process_all_documents(self):
        """
        Process all supporting documents in the database.

        Returns:
            dict: Statistics about the indexing process
        """
        logger.info("=" * 60)
        logger.info("DOCUMENT CONTENT INDEXING PIPELINE")
        logger.info("=" * 60)

        # Get all documents
        documents = self.get_supporting_documents()
        self.stats['total_docs'] = len(documents)

        logger.info(f"Found {len(documents)} supporting documents")

        # Process each document
        for idx, (doc_id, dataset_id, file_path, filename) in enumerate(documents, 1):
            display_name = Path(file_path).name if file_path else filename
            logger.info(f"\n[{idx}/{len(documents)}] Processing: {display_name}")

            try:
                # Check if file exists
                if not file_path or not Path(file_path).exists():
                    logger.warning(f"  File not found: {file_path or filename}")
                    self.stats['skipped_missing'] += 1
                    continue

                # Check if format is supported
                file_type = Path(file_path).suffix.lower().lstrip('.')
                if not self.indexer.extractor.can_extract(file_path):
                    logger.info(f"  Skipping unsupported format: {file_type}")
                    self.stats['skipped_unsupported'] += 1
                    continue

                # Index the document
                chunks_indexed = self.indexer.index_document(
                    file_path=file_path,
                    dataset_id=dataset_id,
                    doc_id=doc_id
                )

                if chunks_indexed > 0:
                    self.stats['indexed'] += 1
                    self.stats['total_chunks'] += chunks_indexed
                    logger.info(f"  ✓ Indexed {chunks_indexed} chunks")
                else:
                    logger.warning(f"  No content indexed")
                    self.stats['failed'] += 1

                self.stats['processed'] += 1

            except Exception as e:
                logger.error(f"  ✗ Error processing document: {e}")
                self.stats['failed'] += 1
                continue

        return self.stats

    def print_summary(self):
        """Print indexing statistics."""
        logger.info("\n" + "=" * 60)
        logger.info("INDEXING COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Total Documents: {self.stats['total_docs']}")
        logger.info(f"Processed: {self.stats['processed']}")
        logger.info(f"Successfully Indexed: {self.stats['indexed']}")
        logger.info(f"Failed: {self.stats['failed']}")
        logger.info(f"Skipped (Unsupported): {self.stats['skipped_unsupported']}")
        logger.info(f"Skipped (Missing): {self.stats['skipped_missing']}")
        logger.info(f"Total Chunks Generated: {self.stats['total_chunks']}")

        if self.stats['indexed'] > 0:
            avg_chunks = self.stats['total_chunks'] / self.stats['indexed']
            logger.info(f"Average Chunks per Document: {avg_chunks:.1f}")

        logger.info("=" * 60)

        # ChromaDB stats
        try:
            count = self.content_collection.count()
            logger.info(f"ChromaDB 'document_content' collection: {count} vectors")
        except Exception as e:
            logger.error(f"Error getting ChromaDB count: {e}")


def main():
    """Main entry point."""
    logger.info("Starting Document Content Indexing Pipeline")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")

    # Initialize pipeline
    backend_dir = SCRIPT_DIR.parents[1]
    pipeline = DocumentContentIndexingPipeline(
        db_path=str(backend_dir / "datasets.db"),
        chroma_path=str(backend_dir / "chroma_db")
    )

    # Process all documents
    stats = pipeline.process_all_documents()

    # Print summary
    pipeline.print_summary()

    # Exit code based on results
    if stats['indexed'] > 0:
        logger.info("\nContent indexing completed successfully")
        return 0
    else:
        logger.warning("\nNo documents were indexed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
