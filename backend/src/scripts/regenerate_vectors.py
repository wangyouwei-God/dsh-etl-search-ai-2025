#!/usr/bin/env python3
"""
Regenerate Vector Embeddings from SQLite.

This script reads existing metadata from the SQLite database and populates
the ChromaDB vector store. It does NOT make any network requests.
Use this to restore the vector database after a schema version upgrade.
"""

import logging
import sys
import os
from pathlib import Path

# Add src to path (both base 'backend' and 'backend/src' for legacy import support)
SCRIPT_DIR = Path(__file__).parent
SRC_DIR = SCRIPT_DIR.parent
BACKEND_DIR = SRC_DIR.parent

sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(SRC_DIR))

from src.infrastructure.persistence.sqlite.connection import get_database
from src.infrastructure.persistence.sqlite.models import MetadataModel, DatasetModel
from src.infrastructure.services.embedding_service import HuggingFaceEmbeddingService
from src.infrastructure.persistence.vector.chroma_repository import ChromaVectorRepository

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting vector regeneration from SQLite...")
    
    # Paths
    base_dir = Path(__file__).parent.parent.parent
    db_path = str(base_dir / "datasets.db")
    chroma_path = str(base_dir / "chroma_db")
    
    # Initialize components
    logger.info(f"Connecting to SQLite: {db_path}")
    db = get_database(db_path)
    
    logger.info(f"Initializing Vector DB: {chroma_path}")
    try:
        embedding_service = HuggingFaceEmbeddingService()
        vector_repo = ChromaVectorRepository(chroma_path)
        logger.info(f"Embedding model loaded: {embedding_service.get_model_name()}")
    except Exception as e:
        logger.error(f"Failed to initialize vector components: {e}")
        return

    # Process all datasets
    success_count = 0
    fail_count = 0
    
    with db.session_scope() as session:
        # Fetch all datasets with their metadata
        datasets = session.query(DatasetModel).all()
        total = len(datasets)
        logger.info(f"Found {total} datasets in SQLite.")
        
        for i, dataset in enumerate(datasets, 1):
            try:
                metadata = dataset.dataset_metadata
                if not metadata:
                    logger.warning(f"[{i}/{total}] Skipping {dataset.id}: No metadata")
                    continue
                
                # Prepare text for embedding
                text_to_embed = f"{metadata.title} {metadata.abstract}"
                
                # Generate embedding
                embedding = embedding_service.generate_embedding(text_to_embed)
                
                # Prepare vector metadata
                vector_metadata = {
                    "title": metadata.title,
                    "abstract": metadata.abstract[:500] if metadata.abstract else "",
                    "contact_email": metadata.contact_email or "",
                    "dataset_language": metadata.dataset_language or "eng",
                    # Convert list to string for ChromaDB metadata
                    "keywords": str(metadata.get_keywords()),
                }
                
                # Geo info
                if metadata.bounding_box_json:
                    import json
                    try:
                        bbox = json.loads(metadata.bounding_box_json)
                        # Minimal geo logic reconstruction
                        if isinstance(bbox, dict):
                            # Calculate center roughly
                            west = float(bbox.get('west_longitude', 0))
                            east = float(bbox.get('east_longitude', 0))
                            south = float(bbox.get('south_latitude', 0))
                            north = float(bbox.get('north_latitude', 0))
                            
                            vector_metadata["has_geo_extent"] = True
                            vector_metadata["center_lat"] = str((south + north) / 2)
                            vector_metadata["center_lon"] = str((west + east) / 2)
                    except:
                        vector_metadata["has_geo_extent"] = False
                else:
                    vector_metadata["has_geo_extent"] = False

                # Temporal info
                if metadata.temporal_extent_start and metadata.temporal_extent_end:
                    vector_metadata["has_temporal_extent"] = True
                    vector_metadata["temporal_start"] = str(metadata.temporal_extent_start)
                    vector_metadata["temporal_end"] = str(metadata.temporal_extent_end)
                else:
                    vector_metadata["has_temporal_extent"] = False
                
                # Upsert to Chroma
                vector_repo.upsert_vector(
                    id=dataset.id,
                    vector=embedding,
                    metadata=vector_metadata
                )
                
                success_count += 1
                if i % 10 == 0:
                    logger.info(f"[{i}/{total}] Processed... Success so far: {success_count}")
                    
            except Exception as e:
                logger.error(f"Failed to process {dataset.id}: {e}")
                fail_count += 1

    logger.info("=" * 60)
    logger.info("REGENERATION COMPLETE")
    logger.info(f"Total processed: {total}")
    logger.info(f"Successfully restored: {success_count}")
    logger.info(f"Failed: {fail_count}")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
