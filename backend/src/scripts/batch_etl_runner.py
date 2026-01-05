#!/usr/bin/env python3
"""
Batch ETL Runner Script

Processes multiple datasets from metadata-file-identifiers.txt
Saves to database and vector store with comprehensive reporting.

Usage:
    python batch_etl_runner.py <identifier_file> [--max-datasets N]

Author: University of Manchester RSE Team
"""

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import List, Optional
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from etl_runner import ETLRunner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('batch_etl.log')
    ]
)
logger = logging.getLogger(__name__)


def load_identifiers(file_path: str) -> List[str]:
    """Load dataset identifiers from file."""
    identifiers = []
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                identifiers.append(line)
    logger.info(f"Loaded {len(identifiers)} identifiers from {file_path}")
    return identifiers


def main():
    parser = argparse.ArgumentParser(description='Batch ETL Runner')
    parser.add_argument('identifier_file', help='Path to file with UUIDs')
    parser.add_argument('--max-datasets', type=int, help='Max datasets to process')
    parser.add_argument('--db-path', default='datasets.db', help='Database path')
    parser.add_argument('--vector-db-path', default='chroma_db', help='Vector DB path')
    
    args = parser.parse_args()

    # Load identifiers
    all_ids = load_identifiers(args.identifier_file)
    identifiers = all_ids[:args.max_datasets] if args.max_datasets else all_ids

    logger.info(f"Processing {len(identifiers)} of {len(all_ids)} total datasets")

    # Initialize ETL runner
    runner = ETLRunner(
        db_path=args.db_path,
        vector_db_path=args.vector_db_path,
        save_to_db=True,
        enable_vector_search=True
    )

    # Statistics
    stats = {'total': len(identifiers), 'success': 0, 'failed': 0, 'errors': []}
    start_time = time.time()

    # Process each dataset
    for index, uuid in enumerate(identifiers, 1):
        logger.info(f"\n{'='*80}")
        logger.info(f"[{index}/{len(identifiers)}] Processing: {uuid}")
        logger.info(f"{'='*80}")

        try:
            runner.run(uuid, preferred_format='json')
            stats['success'] += 1
            logger.info(f"✓ [{index}/{len(identifiers)}] Success")

        except Exception as e:
            stats['failed'] += 1
            stats['errors'].append({'uuid': uuid, 'error': str(e)})
            logger.error(f"✗ [{index}/{len(identifiers)}] Failed: {str(e)}")

        # Progress update
        progress = (index / len(identifiers)) * 100
        success_rate = (stats['success'] / index) * 100
        logger.info(f"Progress: {progress:.1f}% | Success rate: {success_rate:.1f}%")

        # Small delay to avoid rate limiting
        if index < len(identifiers):
            time.sleep(0.5)

    # Final report
    duration = time.time() - start_time
    logger.info(f"\n{'='*80}")
    logger.info("BATCH ETL COMPLETED")
    logger.info(f"{'='*80}")
    logger.info(f"Total:      {stats['total']}")
    logger.info(f"Successful: {stats['success']}")
    logger.info(f"Failed:     {stats['failed']}")
    logger.info(f"Duration:   {duration:.1f}s ({duration/60:.1f} min)")
    logger.info(f"Avg/dataset: {duration/stats['total']:.1f}s")
    logger.info(f"{'='*80}\n")

    if stats['errors']:
        logger.info("ERRORS:")
        for err in stats['errors'][:10]:
            logger.info(f"  {err['uuid']}: {err['error'][:100]}")

    runner.close()


if __name__ == '__main__':
    main()
