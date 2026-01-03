#!/usr/bin/env python3
"""
Batch ETL Runner Script

This script processes multiple dataset UUIDs from a file, with support for:
- Progress tracking and resumption
- Concurrent processing with rate limiting
- Error recovery and detailed logging

Usage:
    python batch_etl_runner.py --input-file metadata-file-identifiers.txt --verbose

Author: University of Manchester RSE Team
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from infrastructure.etl.fetcher import MetadataFetcher, FetchError
from infrastructure.etl.factory.extractor_factory import ExtractorFactory
from application.interfaces.metadata_extractor import MetadataExtractionError
from domain.entities.metadata import Metadata
from domain.entities.dataset import Dataset
from infrastructure.persistence.sqlite.connection import get_database
from infrastructure.persistence.sqlite.dataset_repository_impl import SQLiteDatasetRepository
from domain.repositories.dataset_repository import RepositoryError
from infrastructure.services.embedding_service import HuggingFaceEmbeddingService
from infrastructure.persistence.vector.chroma_repository import ChromaVectorRepository


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Result of processing a single UUID."""
    uuid: str
    success: bool
    error_message: Optional[str] = None
    title: Optional[str] = None
    processing_time: float = 0.0


@dataclass
class BatchProgress:
    """Tracks batch processing progress for resumption."""
    total: int = 0
    processed: int = 0
    successful: int = 0
    failed: int = 0
    completed_uuids: Set[str] = field(default_factory=set)
    failed_uuids: Dict[str, str] = field(default_factory=dict)
    start_time: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "processed": self.processed,
            "successful": self.successful,
            "failed": self.failed,
            "completed_uuids": list(self.completed_uuids),
            "failed_uuids": self.failed_uuids,
            "start_time": self.start_time.isoformat() if self.start_time else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "BatchProgress":
        progress = cls(
            total=data.get("total", 0),
            processed=data.get("processed", 0),
            successful=data.get("successful", 0),
            failed=data.get("failed", 0),
            completed_uuids=set(data.get("completed_uuids", [])),
            failed_uuids=data.get("failed_uuids", {}),
        )
        if data.get("start_time"):
            progress.start_time = datetime.fromisoformat(data["start_time"])
        return progress


class BatchETLRunner:
    """
    Batch ETL Runner for processing multiple dataset UUIDs.
    
    Features:
    - Progress tracking and resumption from checkpoint
    - Concurrent processing with configurable parallelism
    - Rate limiting to avoid overwhelming remote servers
    - Detailed error reporting and recovery
    
    Design Pattern: Template Method + Strategy
    - Uses existing ETL components (Fetcher, Factory, Extractors)
    - Adds batch processing coordination
    """
    
    PROGRESS_FILE = "batch_progress.json"
    
    def __init__(
        self,
        catalogue: str = 'ceh',
        db_path: str = "datasets.db",
        vector_db_path: str = "chroma_db",
        max_workers: int = 3,
        rate_limit_delay: float = 1.0,
        enable_vector_search: bool = True,
        resume: bool = True
    ):
        """
        Initialize the batch ETL runner.
        
        Args:
            catalogue: Catalogue identifier ('ceh', 'ceda')
            db_path: Path to SQLite database
            vector_db_path: Path to ChromaDB directory
            max_workers: Maximum concurrent workers (default: 3 to be respectful)
            rate_limit_delay: Delay between requests in seconds
            enable_vector_search: Enable semantic search embeddings
            resume: Resume from previous checkpoint if available
        """
        self.catalogue = catalogue
        self.db_path = db_path
        self.vector_db_path = vector_db_path
        self.max_workers = max_workers
        self.rate_limit_delay = rate_limit_delay
        self.enable_vector_search = enable_vector_search
        self.resume = resume
        
        # Initialize shared services
        self.factory = ExtractorFactory(strict_mode=False)
        self.db = get_database(db_path)
        
        # Initialize embedding service (shared across workers)
        self.embedding_service = None
        self.vector_repository = None
        if enable_vector_search:
            try:
                logger.info("Initializing semantic search components...")
                self.embedding_service = HuggingFaceEmbeddingService()
                self.vector_repository = ChromaVectorRepository(vector_db_path)
                logger.info(f"Semantic search initialized: {self.embedding_service.get_model_name()}")
            except Exception as e:
                logger.warning(f"Failed to initialize semantic search: {e}")
                self.enable_vector_search = False
        
        logger.info(
            f"BatchETLRunner initialized: workers={max_workers}, "
            f"rate_limit={rate_limit_delay}s, vector_search={enable_vector_search}"
        )
    
    def load_uuids(self, input_file: str) -> List[str]:
        """
        Load UUIDs from input file.
        
        Args:
            input_file: Path to file containing UUIDs (one per line)
            
        Returns:
            List of valid UUIDs
        """
        uuids = []
        path = Path(input_file)
        
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                uuid = line.strip()
                if uuid and not uuid.startswith('#'):  # Skip empty lines and comments
                    uuids.append(uuid)
        
        logger.info(f"Loaded {len(uuids)} UUIDs from {input_file}")
        return uuids
    
    def load_progress(self, progress_file: str) -> BatchProgress:
        """Load progress from checkpoint file."""
        path = Path(progress_file)
        if path.exists():
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                progress = BatchProgress.from_dict(data)
                logger.info(
                    f"Resuming from checkpoint: {progress.processed}/{progress.total} "
                    f"({progress.successful} successful, {progress.failed} failed)"
                )
                return progress
            except Exception as e:
                logger.warning(f"Failed to load progress file: {e}")
        
        return BatchProgress(start_time=datetime.now())
    
    def save_progress(self, progress: BatchProgress, progress_file: str):
        """Save progress to checkpoint file."""
        with open(progress_file, 'w') as f:
            json.dump(progress.to_dict(), f, indent=2)
    
    def process_single_uuid(self, uuid: str) -> ProcessingResult:
        """
        Process a single UUID.
        
        This method is designed to be called by worker threads.
        
        Args:
            uuid: Dataset UUID to process
            
        Returns:
            ProcessingResult with success/failure status
        """
        start_time = time.time()
        
        try:
            # Create fetcher for this thread
            fetcher = MetadataFetcher(
                catalogue=self.catalogue,
                timeout=60,
                max_retries=3
            )
            
            try:
                # Step 1: Fetch metadata
                file_path, format_type = fetcher.fetch(uuid)
                
                # Step 2: Extract metadata
                extractor = self.factory.create_extractor(file_path)
                metadata = extractor.extract(file_path)
                
                # Step 3: Save to database
                dataset = Dataset(
                    title=metadata.title,
                    abstract=metadata.abstract,
                    metadata_url=file_path
                )
                
                dataset_id = None
                with self.db.session_scope() as session:
                    repository = SQLiteDatasetRepository(session)
                    dataset_id = repository.save(dataset, metadata)
                
                # Step 4: Generate embeddings
                if self.enable_vector_search and self.embedding_service:
                    text_to_embed = f"{metadata.title} {metadata.abstract}"
                    embedding = self.embedding_service.generate_embedding(text_to_embed)
                    
                    vector_metadata = {
                        "title": metadata.title,
                        "abstract": metadata.abstract[:500],
                        "keywords": str(metadata.keywords),
                    }
                    
                    vector_id = dataset_id or uuid
                    self.vector_repository.upsert_vector(
                        id=vector_id,
                        vector=embedding,
                        metadata=vector_metadata
                    )
                
                processing_time = time.time() - start_time
                return ProcessingResult(
                    uuid=uuid,
                    success=True,
                    title=metadata.title,
                    processing_time=processing_time
                )
                
            finally:
                fetcher.close()
                
        except FetchError as e:
            return ProcessingResult(
                uuid=uuid,
                success=False,
                error_message=f"Fetch error: {e.reason}",
                processing_time=time.time() - start_time
            )
        except MetadataExtractionError as e:
            return ProcessingResult(
                uuid=uuid,
                success=False,
                error_message=f"Extraction error: {str(e)}",
                processing_time=time.time() - start_time
            )
        except RepositoryError as e:
            return ProcessingResult(
                uuid=uuid,
                success=False,
                error_message=f"Database error: {str(e)}",
                processing_time=time.time() - start_time
            )
        except Exception as e:
            return ProcessingResult(
                uuid=uuid,
                success=False,
                error_message=f"Unexpected error: {str(e)}",
                processing_time=time.time() - start_time
            )
    
    def run(
        self,
        input_file: str,
        progress_file: Optional[str] = None
    ) -> BatchProgress:
        """
        Run batch processing on all UUIDs from input file.
        
        Args:
            input_file: Path to file containing UUIDs
            progress_file: Path to progress checkpoint file
            
        Returns:
            BatchProgress with final statistics
        """
        progress_file = progress_file or self.PROGRESS_FILE
        
        # Load UUIDs
        all_uuids = self.load_uuids(input_file)
        
        # Load or initialize progress
        if self.resume:
            progress = self.load_progress(progress_file)
            progress.total = len(all_uuids)
        else:
            progress = BatchProgress(total=len(all_uuids), start_time=datetime.now())
        
        # Filter out already processed UUIDs
        uuids_to_process = [
            uuid for uuid in all_uuids 
            if uuid not in progress.completed_uuids
        ]
        
        logger.info(f"Processing {len(uuids_to_process)} remaining UUIDs...")
        
        # Process with thread pool
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_uuid = {}
            for i, uuid in enumerate(uuids_to_process):
                # Rate limiting - stagger submission
                if i > 0 and i % self.max_workers == 0:
                    time.sleep(self.rate_limit_delay)
                
                future = executor.submit(self.process_single_uuid, uuid)
                future_to_uuid[future] = uuid
            
            # Process results as they complete
            for future in as_completed(future_to_uuid):
                uuid = future_to_uuid[future]
                
                try:
                    result = future.result()
                    progress.processed += 1
                    
                    if result.success:
                        progress.successful += 1
                        progress.completed_uuids.add(uuid)
                        logger.info(
                            f"[{progress.processed}/{progress.total}] ✓ {uuid[:8]}... "
                            f"- {result.title[:50] if result.title else 'N/A'}... "
                            f"({result.processing_time:.1f}s)"
                        )
                    else:
                        progress.failed += 1
                        progress.failed_uuids[uuid] = result.error_message or "Unknown error"
                        logger.warning(
                            f"[{progress.processed}/{progress.total}] ✗ {uuid[:8]}... "
                            f"- {result.error_message}"
                        )
                    
                    # Save progress periodically
                    if progress.processed % 10 == 0:
                        self.save_progress(progress, progress_file)
                        
                except Exception as e:
                    progress.processed += 1
                    progress.failed += 1
                    progress.failed_uuids[uuid] = str(e)
                    logger.error(f"Worker exception for {uuid}: {e}")
        
        # Save final progress
        self.save_progress(progress, progress_file)
        
        # Print summary
        elapsed = (datetime.now() - progress.start_time).total_seconds() if progress.start_time else 0
        logger.info("=" * 80)
        logger.info("BATCH PROCESSING COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Total:      {progress.total}")
        logger.info(f"Processed:  {progress.processed}")
        logger.info(f"Successful: {progress.successful}")
        logger.info(f"Failed:     {progress.failed}")
        logger.info(f"Time:       {elapsed:.1f} seconds")
        logger.info(f"Rate:       {progress.processed / elapsed:.2f} UUIDs/sec" if elapsed > 0 else "N/A")
        
        if progress.failed_uuids:
            logger.info("-" * 80)
            logger.info("Failed UUIDs:")
            for uuid, error in list(progress.failed_uuids.items())[:10]:
                logger.info(f"  {uuid}: {error}")
            if len(progress.failed_uuids) > 10:
                logger.info(f"  ... and {len(progress.failed_uuids) - 10} more")
        
        return progress


def main():
    """Main entry point for batch ETL runner."""
    parser = argparse.ArgumentParser(
        description='Batch ETL Runner for Dataset Metadata Ingestion',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--input-file',
        required=True,
        help='Path to file containing UUIDs (one per line)'
    )
    
    parser.add_argument(
        '--catalogue',
        choices=['ceh', 'ceda'],
        default='ceh',
        help='Catalogue to fetch from (default: ceh)'
    )
    
    parser.add_argument(
        '--workers',
        type=int,
        default=3,
        help='Maximum concurrent workers (default: 3)'
    )
    
    parser.add_argument(
        '--rate-limit',
        type=float,
        default=1.0,
        help='Delay between batches in seconds (default: 1.0)'
    )
    
    parser.add_argument(
        '--db-path',
        default='datasets.db',
        help='Path to SQLite database'
    )
    
    parser.add_argument(
        '--vector-db-path',
        default='chroma_db',
        help='Path to ChromaDB directory'
    )
    
    parser.add_argument(
        '--no-resume',
        action='store_true',
        help='Start fresh, ignore previous progress'
    )
    
    parser.add_argument(
        '--no-vector-search',
        action='store_true',
        help='Disable semantic search / vector embeddings'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Print header
    print()
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "BATCH ETL RUNNER" + " " * 42 + "║")
    print("║" + " " * 20 + "University of Manchester" + " " * 34 + "║")
    print("╚" + "═" * 78 + "╝")
    print()
    
    # Create and run batch processor
    runner = BatchETLRunner(
        catalogue=args.catalogue,
        db_path=args.db_path,
        vector_db_path=args.vector_db_path,
        max_workers=args.workers,
        rate_limit_delay=args.rate_limit,
        enable_vector_search=not args.no_vector_search,
        resume=not args.no_resume
    )
    
    try:
        progress = runner.run(args.input_file)
        
        # Exit with appropriate code
        if progress.failed == 0:
            sys.exit(0)
        elif progress.successful > 0:
            sys.exit(0)  # Partial success is still OK
        else:
            sys.exit(1)
            
    except FileNotFoundError as e:
        logger.error(str(e))
        sys.exit(1)
    except KeyboardInterrupt:
        logger.warning("Process interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
