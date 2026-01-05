#!/usr/bin/env python3
"""
ETL Runner Script

This script orchestrates the complete ETL process for ingesting metadata from
remote catalogues. It fetches metadata, extracts it using the appropriate
parser, and displays the results.

Usage:
    python etl_runner.py <uuid> [--catalogue ceh] [--format json|xml] [--strict]

Examples:
    # Fetch from CEH catalogue (auto-detect format)
    python etl_runner.py 1d33a8a1-4c7e-4d6f-b8c1-c158c1f5a8e2

    # Fetch JSON format only
    python etl_runner.py 1d33a8a1-4c7e-4d6f-b8c1-c158c1f5a8e2 --format json

    # Fetch with strict validation
    python etl_runner.py 1d33a8a1-4c7e-4d6f-b8c1-c158c1f5a8e2 --strict

    # Fetch from CEDA catalogue
    python etl_runner.py abc123 --catalogue ceda

Author: University of Manchester RSE Team
"""

import argparse
import logging
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from infrastructure.etl.fetcher import MetadataFetcher, FetchError
from infrastructure.etl.factory.extractor_factory import ExtractorFactory
from application.interfaces.metadata_extractor import MetadataExtractionError
from domain.entities.metadata import Metadata
from domain.entities.dataset import Dataset
from infrastructure.persistence.sqlite.connection import DatabaseConnection, get_database
from infrastructure.persistence.sqlite.dataset_repository_impl import SQLiteDatasetRepository
from domain.repositories.dataset_repository import RepositoryError
from infrastructure.services.embedding_service import HuggingFaceEmbeddingService
from infrastructure.persistence.vector.chroma_repository import ChromaVectorRepository
from application.interfaces.embedding_service import EmbeddingError
from domain.repositories.vector_repository import VectorRepositoryError
from infrastructure.etl.zip_extractor import ZipExtractor, ExtractedFile
from infrastructure.etl.supporting_doc_fetcher import SupportingDocFetcher
from infrastructure.etl.file_access_fetcher import FileAccessFetcher
from application.services.document_processor import DocumentProcessorFactory
from domain.entities.data_file import DataFile, SupportingDocument


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class ETLRunner:
    """
    ETL Runner for metadata ingestion.

    This class orchestrates the complete ETL process:
    1. Fetch metadata from remote catalogue
    2. Select appropriate extractor
    3. Extract and validate metadata
    4. Return structured metadata entity

    Design Pattern: Facade Pattern
    - Provides simple interface for complex ETL process
    - Coordinates multiple services (Fetcher, Factory, Extractors)
    """

    def __init__(
        self,
        catalogue: str = 'ceh',
        strict_mode: bool = False,
        timeout: int = 60,
        max_retries: int = 3,
        db_path: Optional[str] = None,
        save_to_db: bool = True,
        enable_vector_search: bool = True,
        vector_db_path: Optional[str] = None,
        download_fileaccess: bool = False,
        fileaccess_max_files: int = 200,
        fileaccess_max_depth: int = 1,
        fileaccess_max_size_mb: int = 500
    ):
        """
        Initialize the ETL runner.

        Args:
            catalogue: Catalogue identifier ('ceh', 'ceda', etc.)
            strict_mode: If True, enforce all required fields
            timeout: HTTP timeout in seconds
            max_retries: Maximum retry attempts
            db_path: Path to SQLite database (default: datasets.db)
            save_to_db: If True, save extracted data to database
            enable_vector_search: If True, enable semantic search with embeddings
            vector_db_path: Path to ChromaDB directory (default: chroma_db)
        """
        self.catalogue = catalogue
        self.strict_mode = strict_mode
        self.save_to_db = save_to_db
        self.enable_vector_search = enable_vector_search
        self.download_fileaccess = download_fileaccess
        self.fileaccess_max_files = fileaccess_max_files
        self.fileaccess_max_depth = fileaccess_max_depth
        self.fileaccess_max_size_mb = fileaccess_max_size_mb

        # Create services
        self.fetcher = MetadataFetcher(
            catalogue=catalogue,
            timeout=timeout,
            max_retries=max_retries
        )
        self.factory = ExtractorFactory(strict_mode=strict_mode)
        
        # Initialize file processors
        self.zip_extractor = ZipExtractor(overwrite=True)  # Overwrite for idempotency
        self.doc_fetcher = SupportingDocFetcher()
        self.file_access_fetcher = FileAccessFetcher(max_size_mb=fileaccess_max_size_mb)
        self.doc_processor_factory = DocumentProcessorFactory()

        # Initialize database if persistence is enabled
        self.db = None
        self.repository = None
        if save_to_db:
            db_path = db_path or "datasets.db"
            self.db = get_database(db_path)
            logger.info(f"Database initialized: {db_path}")

        # Initialize vector search if enabled
        self.embedding_service = None
        self.vector_repository = None
        if enable_vector_search:
            try:
                logger.info("Initializing semantic search components...")
                self.embedding_service = HuggingFaceEmbeddingService()
                vector_db_path = vector_db_path or "chroma_db"
                self.vector_repository = ChromaVectorRepository(vector_db_path)
                logger.info(
                    f"Semantic search initialized: model={self.embedding_service.get_model_name()}, "
                    f"dimension={self.embedding_service.get_dimension()}"
                )
            except Exception as e:
                logger.warning(f"Failed to initialize semantic search: {str(e)}")
                logger.warning("Continuing without vector search...")
                self.enable_vector_search = False

        logger.info(
            f"ETL Runner initialized (catalogue={catalogue}, "
            f"strict={strict_mode}, save_to_db={save_to_db}, "
            f"vector_search={enable_vector_search})"
        )

    def run(
        self,
        uuid: str,
        preferred_format: Optional[str] = None
    ) -> Metadata:
        """
        Run the complete ETL process for a given UUID.

        Args:
            uuid: Dataset UUID or identifier
            preferred_format: Preferred format ('json' or 'xml'), optional

        Returns:
            Metadata: Extracted and validated metadata entity

        Raises:
            FetchError: If metadata cannot be fetched
            MetadataExtractionError: If extraction fails
            ValueError: If validation fails

        Example:
            >>> runner = ETLRunner()
            >>> metadata = runner.run('abc123')
            >>> print(metadata.title)
        """
        logger.info(f"Starting ETL process for UUID: {uuid}")

        # Step 1: Fetch metadata from catalogue
        logger.info("Step 1: Fetching metadata from catalogue...")
        try:
            file_path, format_type = self.fetcher.fetch(
                uuid,
                preferred_format=preferred_format
            )
            logger.info(f"✓ Fetched {format_type} metadata to {file_path}")
        except FetchError as e:
            logger.error(f"✗ Fetch failed: {e.reason}")
            raise

        # Step 2: Create appropriate extractor
        logger.info("Step 2: Creating extractor...")
        try:
            extractor = self.factory.create_extractor(file_path)
            logger.info(f"✓ Created {extractor.__class__.__name__}")
        except Exception as e:
            logger.error(f"✗ Failed to create extractor: {str(e)}")
            raise

        # Step 3: Extract metadata
        logger.info("Step 3: Extracting metadata...")
        try:
            metadata = extractor.extract(file_path)
            logger.info(f"✓ Successfully extracted metadata")
        except MetadataExtractionError as e:
            logger.error(f"✗ Extraction failed: {e}")
            raise
        except ValueError as e:
            logger.error(f"✗ Validation failed: {str(e)}")
            raise

        # Step 4: Validate metadata
        logger.info("Step 4: Validating metadata...")
        if metadata.is_geospatial():
            logger.info(f"✓ Geospatial dataset detected")
        if metadata.has_temporal_extent():
            logger.info(
                f"✓ Temporal extent: {metadata.temporal_extent_start.year} - "
                f"{metadata.temporal_extent_end.year}"
            )

        # Step 5: Save to database (if enabled)
        dataset_id = None
        if self.save_to_db:
            logger.info("Step 5: Saving to database...")
            try:
                # Create dataset entity
                # BUGFIX: Use CEH's original UUID to ensure data_files foreign key integrity
                from uuid import UUID
                dataset = Dataset(
                    id=UUID(uuid),  # Use the original CEH UUID
                    title=metadata.title,
                    abstract=metadata.abstract,
                    metadata_url=file_path
                )

                # Read raw document content (TASK REQUIREMENT)
                # PDF p.3: "store the entire document in a field in the database"
                raw_document = None
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        raw_document = f.read()
                    logger.debug(f"Read raw document: {len(raw_document)} characters")
                except Exception as e:
                    logger.warning(f"Failed to read raw document: {e}")

                # Process data files (Phase 1.5)
                data_files = []
                if metadata.download_url:
                    logger.info("Step 5.1: Processing data files...")
                    try:
                        data_files = self._process_data_files(metadata, uuid)
                        logger.info(f"✓ Processed {len(data_files)} data files")
                    except Exception as e:
                        logger.error(f"✗ Failed to process data files: {str(e)}")

                # Process supporting documents (Phase 1.5)
                supporting_docs = []
                if metadata.landing_page_url:
                    logger.info("Step 5.2: Processing supporting documents...")
                    try:
                        supporting_docs = self._process_supporting_documents(metadata, uuid)
                        logger.info(f"✓ Processed {len(supporting_docs)} supporting documents")
                    except Exception as e:
                        logger.error(f"✗ Failed to process supporting documents: {str(e)}")

                # Save to database with raw document and files
                with self.db.session_scope() as session:
                    repository = SQLiteDatasetRepository(session)
                    dataset_id = repository.save(
                        dataset,
                        metadata,
                        data_files=data_files,
                        supporting_documents=supporting_docs,
                        raw_document=raw_document,
                        document_format=format_type
                    )
                    logger.info(f"✓ Saved to database with ID: {dataset_id}")
                    if raw_document:
                        logger.info(f"✓ Stored raw {format_type} document ({len(raw_document)} chars)")

            except RepositoryError as e:
                logger.error(f"✗ Failed to save to database: {str(e)}")
                # Don't fail the entire ETL process if database save fails
                logger.warning("Continuing without database persistence...")

        # Step 6: Generate embeddings and save to vector database (if enabled)
        if self.enable_vector_search and self.embedding_service and self.vector_repository:
            logger.info("Step 6: Generating embeddings for semantic search...")
            try:
                # Combine title and abstract for embedding
                text_to_embed = f"{metadata.title} {metadata.abstract}"

                # Generate embedding
                logger.info("Generating text embedding...")
                embedding = self.embedding_service.generate_embedding(text_to_embed)
                logger.info(f"✓ Generated {len(embedding)}-dimensional embedding")

                # Prepare metadata for vector store
                vector_metadata = {
                    "title": metadata.title,
                    "abstract": metadata.abstract[:500],  # Truncate for storage
                    "contact_email": metadata.contact_email or "",
                    "dataset_language": metadata.dataset_language or "eng",
                    "keywords": str(metadata.keywords),
                    "type": "dataset",
                }

                # Add geographic/temporal info if available
                if metadata.bounding_box:
                    vector_metadata["has_geo_extent"] = True
                    vector_metadata["center_lat"] = str(metadata.bounding_box.get_center()[1])
                    vector_metadata["center_lon"] = str(metadata.bounding_box.get_center()[0])
                else:
                    vector_metadata["has_geo_extent"] = False

                if metadata.has_temporal_extent():
                    vector_metadata["has_temporal_extent"] = True
                    vector_metadata["temporal_start"] = str(metadata.temporal_extent_start)
                    vector_metadata["temporal_end"] = str(metadata.temporal_extent_end)
                else:
                    vector_metadata["has_temporal_extent"] = False

                # Use dataset ID or UUID as vector ID
                vector_id = dataset_id or uuid

                # Save to vector database
                self.vector_repository.upsert_vector(
                    id=vector_id,
                    vector=embedding,
                    metadata=vector_metadata
                )
                logger.info(f"✓ Saved embedding to vector database with ID: {vector_id}")

            except EmbeddingError as e:
                logger.error(f"✗ Failed to generate embedding: {str(e)}")
                logger.warning("Continuing without vector search...")
            except VectorRepositoryError as e:
                logger.error(f"✗ Failed to save to vector database: {str(e)}")
                logger.warning("Continuing without vector search...")

        logger.info("=" * 80)
        logger.info("ETL PROCESS COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)

        return metadata

    def _process_data_files(self, metadata: Metadata, dataset_id: str) -> list[DataFile]:
        """Download and process data files."""
        if metadata.access_type == "fileAccess":
            folder_url = metadata.download_url or metadata.landing_page_url
            if not folder_url:
                logger.info("fileAccess dataset detected but no folder URL available")
                return []

            logger.info("fileAccess dataset detected; crawling folder listing for data files")
            file_infos = self.file_access_fetcher.list_files(
                folder_url,
                max_files=self.fileaccess_max_files,
                max_depth=self.fileaccess_max_depth
            )
            logger.info(f"Discovered {len(file_infos)} fileAccess data files")

            if self.download_fileaccess and file_infos:
                logger.info("Downloading fileAccess data files")
                file_infos = self.file_access_fetcher.download_files(
                    file_infos,
                    dataset_id=dataset_id,
                    max_files=self.fileaccess_max_files
                )

            data_files = []
            for info in file_infos:
                df = DataFile(
                    dataset_id=dataset_id,
                    filename=info.filename,
                    file_path=info.local_path or info.url,
                    file_size=info.file_size,
                    file_format=info.file_format,
                    downloaded_at=info.downloaded_at
                )
                data_files.append(df)

            return data_files

        # Determine best URL for data files
        # Priority: landing_page_url if it's a ZIP file, otherwise download_url
        zip_url = None
        if metadata.landing_page_url and metadata.landing_page_url.endswith('.zip'):
            zip_url = metadata.landing_page_url
        elif metadata.download_url:
            zip_url = metadata.download_url

        if not zip_url:
            return []

        # Download and extract ZIP
        zip_info = self.zip_extractor.extract_from_url(
            zip_url,
            dataset_id=dataset_id
        )

        # Convert to domain entities
        data_files = []
        for extracted in zip_info.extracted_files:
            df = DataFile(
                dataset_id=dataset_id,
                filename=extracted.filename,
                file_path=extracted.file_path,
                file_size=extracted.file_size,
                file_format=extracted.file_format,
                downloaded_at=extracted.extracted_at
            )
            data_files.append(df)
        
        return data_files

    def _process_supporting_documents(self, metadata: Metadata, dataset_id: str) -> list[SupportingDocument]:
        """Download and process supporting documents."""
        if not metadata.landing_page_url:
            return []

        # Fetch documents
        downloaded_docs = self.doc_fetcher.fetch_all_documents(
            dataset_id=dataset_id,
            max_docs=5  # Reasonable limit to avoid overloading
        )

        # Convert to domain entities and process with RAG processor
        supporting_docs = []
        for doc_info in downloaded_docs:
            # Create entity
            doc = SupportingDocument(
                dataset_id=dataset_id,
                title=doc_info.title or doc_info.filename, # Use title if available
                document_type=doc_info.document_type,
                filename=doc_info.filename,
                file_path=str(doc_info.file_path),
                file_size=doc_info.file_size,
                downloaded_at=datetime.utcnow()
            )
            
            # Phase 2.2: Process for RAG (Extract Text)
            # Only process if it's a PDF or text file
            if self.doc_processor_factory.can_process(doc.file_path):
                try:
                    logger.info(f"Processing document for RAG: {doc.filename}")
                    processed = self.doc_processor_factory.process(doc.file_path, title=doc.title)
                    if processed and processed.chunks:
                        # Concatenate chunk content for storage in SQL (simplified RAG)
                        # Ideally we store chunks in Vector DB, but storing full text in SQL is a good backup
                        full_text = "\n\n".join([c.content for c in processed.chunks])
                        doc.content_text = full_text
                        doc.is_processed = True
                        logger.info(f"✓ Extracted {len(full_text)} chars from {doc.filename}")
                        
                        # Store chunks in Vector DB if enabled
                        if self.enable_vector_search and self.vector_repository and self.embedding_service:
                            try:
                                logger.info(f"Generating embeddings for {len(processed.chunks)} chunks...")
                                ids = []
                                vectors = []
                                metadatas = []
                                
                                for chunk in processed.chunks:
                                    # Generate embedding
                                    vector = self.embedding_service.generate_embedding(chunk.content)
                                    
                                    ids.append(chunk.id)
                                    vectors.append(vector)
                                    # ChromaDB metadata must be flat
                                    metadatas.append({
                                        "type": "document",
                                        "parent_id": dataset_id,
                                        "filename": doc.filename,
                                        "title": doc.title,
                                        "chunk_index": chunk.chunk_index,
                                        "content": chunk.content[:1000],  # Truncate content in metadata if too long
                                        "abstract": chunk.content[:1000]  # Map to abstract for search compatibility
                                    })
                                
                                # Batch upsert
                                self.vector_repository.upsert_vectors_batch(ids, vectors, metadatas)
                                logger.info(f"✓ Stored {len(ids)} chunks in vector database")
                                
                            except Exception as ve:
                                logger.error(f"Failed to store chunks in vector DB: {ve}")

                except Exception as e:
                    logger.warning(f"Failed to process document {doc.filename}: {e}")

            supporting_docs.append(doc)
            
        return supporting_docs

    def close(self):
        """Close resources."""
        if self.fetcher:
            self.fetcher.close()
        if self.zip_extractor:
            self.zip_extractor.close()


def print_metadata_summary(metadata: Metadata):
    """
    Print a formatted summary of extracted metadata.

    Args:
        metadata: Metadata entity to display
    """
    print()
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 25 + "EXTRACTED METADATA" + " " * 35 + "║")
    print("╚" + "═" * 78 + "╝")
    print()

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(metadata.get_summary())
    print("=" * 80)
    print()

    print("DETAILED INFORMATION")
    print("-" * 80)
    print(f"Title:")
    print(f"  {metadata.title}")
    print()

    print(f"Abstract ({len(metadata.abstract)} characters):")
    # Wrap abstract at 76 characters
    abstract_lines = [
        metadata.abstract[i:i+76]
        for i in range(0, len(metadata.abstract), 76)
    ]
    for line in abstract_lines[:5]:  # Show first 5 lines
        print(f"  {line}")
    if len(abstract_lines) > 5:
        print(f"  ... ({len(abstract_lines) - 5} more lines)")
    print()

    if metadata.keywords:
        print(f"Keywords ({len(metadata.keywords)}):")
        for i, keyword in enumerate(metadata.keywords, 1):
            print(f"  {i}. {keyword}")
        print()

    if metadata.bounding_box:
        print("Geographic Extent:")
        bbox = metadata.bounding_box
        print(f"  West:  {bbox.west_longitude}°")
        print(f"  East:  {bbox.east_longitude}°")
        print(f"  South: {bbox.south_latitude}°")
        print(f"  North: {bbox.north_latitude}°")
        center = bbox.get_center()
        print(f"  Center: {center[1]:.4f}°N, {center[0]:.4f}°E")
        print(f"  Area: {bbox.get_area():.2f} square degrees")
        print()

    if metadata.has_temporal_extent():
        print("Temporal Coverage:")
        print(f"  Start: {metadata.temporal_extent_start}")
        print(f"  End:   {metadata.temporal_extent_end}")
        duration = metadata.temporal_extent_end - metadata.temporal_extent_start
        print(f"  Duration: {duration.days} days")
        print()

    print("Contact Information:")
    if metadata.contact_organization:
        print(f"  Organization: {metadata.contact_organization}")
    if metadata.contact_email:
        print(f"  Email: {metadata.contact_email}")
    print()

    print("Additional Metadata:")
    print(f"  Language: {metadata.dataset_language}")
    if metadata.topic_category:
        print(f"  Topic Category: {metadata.topic_category}")
    print(f"  Metadata Date: {metadata.metadata_date}")
    print()

    print("=" * 80)


def main():
    """Main entry point for the ETL runner."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='ETL Runner for Dataset Metadata Ingestion',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s abc123
  %(prog)s abc123 --format json
  %(prog)s abc123 --catalogue ceda --strict
  %(prog)s abc123 --format xml --verbose

Supported Catalogues:
  - ceh  : Centre for Ecology & Hydrology
  - ceda : Centre for Environmental Data Analysis
        """
    )

    parser.add_argument(
        'uuid',
        help='Dataset UUID or identifier'
    )

    parser.add_argument(
        '--catalogue',
        choices=['ceh', 'ceda'],
        default='ceh',
        help='Catalogue to fetch from (default: ceh)'
    )

    parser.add_argument(
        '--format',
        choices=['json', 'xml'],
        help='Preferred metadata format (default: auto-detect)'
    )

    parser.add_argument(
        '--strict',
        action='store_true',
        help='Enable strict validation (all fields required)'
    )

    parser.add_argument(
        '--timeout',
        type=int,
        default=60,
        help='HTTP timeout in seconds (default: 60)'
    )

    parser.add_argument(
        '--retries',
        type=int,
        default=3,
        help='Maximum retry attempts (default: 3)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Suppress all output except errors'
    )

    parser.add_argument(
        '--db-path',
        type=str,
        default='datasets.db',
        help='Path to SQLite database file (default: datasets.db)'
    )

    parser.add_argument(
        '--no-db',
        action='store_true',
        help='Disable database persistence (extract only)'
    )

    parser.add_argument(
        '--no-vector-search',
        action='store_true',
        help='Disable semantic search / vector embeddings'
    )

    parser.add_argument(
        '--vector-db-path',
        type=str,
        default='chroma_db',
        help='Path to ChromaDB directory (default: chroma_db)'
    )

    parser.add_argument(
        '--download-fileaccess',
        action='store_true',
        help='Download files for fileAccess datasets (default: list only)'
    )

    parser.add_argument(
        '--fileaccess-max-files',
        type=int,
        default=200,
        help='Maximum files to list/download from fileAccess folders (default: 200)'
    )

    parser.add_argument(
        '--fileaccess-max-depth',
        type=int,
        default=1,
        help='Recursion depth for fileAccess folder crawling (default: 1)'
    )

    parser.add_argument(
        '--fileaccess-max-size-mb',
        type=int,
        default=500,
        help='Max file size for fileAccess downloads (default: 500MB)'
    )

    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    elif args.quiet:
        logging.getLogger().setLevel(logging.ERROR)

    # Print header
    if not args.quiet:
        print()
        print("╔" + "═" * 78 + "╗")
        print("║" + " " * 20 + "DATASET METADATA ETL RUNNER" + " " * 31 + "║")
        print("║" + " " * 20 + "University of Manchester" + " " * 34 + "║")
        print("╚" + "═" * 78 + "╝")
        print()
        print(f"UUID: {args.uuid}")
        print(f"Catalogue: {args.catalogue}")
        print(f"Format: {args.format or 'auto-detect'}")
        print(f"Strict mode: {args.strict}")
        print()

    # Run ETL process
    runner = ETLRunner(
        catalogue=args.catalogue,
        strict_mode=args.strict,
        timeout=args.timeout,
        max_retries=args.retries,
        db_path=args.db_path,
        save_to_db=not args.no_db,
        enable_vector_search=not args.no_vector_search,
        vector_db_path=args.vector_db_path,
        download_fileaccess=args.download_fileaccess,
        fileaccess_max_files=args.fileaccess_max_files,
        fileaccess_max_depth=args.fileaccess_max_depth,
        fileaccess_max_size_mb=args.fileaccess_max_size_mb
    )

    try:
        # Execute ETL
        metadata = runner.run(args.uuid, preferred_format=args.format)

        # Display results
        if not args.quiet:
            print_metadata_summary(metadata)

        # Success exit code
        sys.exit(0)

    except FetchError as e:
        logger.error(f"Failed to fetch metadata: {e.reason}")
        sys.exit(1)

    except MetadataExtractionError as e:
        logger.error(f"Failed to extract metadata: {str(e)}")
        sys.exit(2)

    except ValueError as e:
        logger.error(f"Metadata validation failed: {str(e)}")
        sys.exit(3)

    except KeyboardInterrupt:
        logger.warning("Process interrupted by user")
        sys.exit(130)

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        sys.exit(4)

    finally:
        runner.close()


if __name__ == '__main__':
    main()
