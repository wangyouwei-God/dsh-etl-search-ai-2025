#!/usr/bin/env python3
"""
Test script to verify database persistence.

This script queries the database to confirm data was correctly saved.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from infrastructure.persistence.sqlite.connection import get_database
from infrastructure.persistence.sqlite.dataset_repository_impl import SQLiteDatasetRepository


def main():
    print("=" * 80)
    print("DATABASE VERIFICATION")
    print("=" * 80)
    print()

    # Get database connection
    db = get_database("test_datasets.db")

    # Query all datasets
    with db.session_scope() as session:
        repository = SQLiteDatasetRepository(session)

        # Get count
        total_count = repository.count()
        print(f"Total datasets in database: {total_count}")
        print()

        # Get all datasets
        all_datasets = repository.get_all()

        print("STORED DATASETS:")
        print("-" * 80)
        for i, (dataset, metadata) in enumerate(all_datasets, 1):
            print(f"{i}. Dataset ID: {dataset.id}")
            print(f"   Title: {dataset.title}")
            print(f"   Abstract: {dataset.abstract[:100]}...")
            print(f"   Created: {dataset.created_at}")
            print(f"   Last Updated: {dataset.last_updated}")
            print()

            print(f"   Metadata:")
            print(f"   - Title: {metadata.title}")
            print(f"   - Keywords: {', '.join(metadata.keywords)}")
            print(f"   - Contact: {metadata.contact_email}")
            print(f"   - Language: {metadata.dataset_language}")

            if metadata.bounding_box:
                bbox = metadata.bounding_box
                print(f"   - Geographic Extent:")
                print(f"     West: {bbox.west_longitude}°, East: {bbox.east_longitude}°")
                print(f"     South: {bbox.south_latitude}°, North: {bbox.north_latitude}°")

            if metadata.has_temporal_extent():
                print(f"   - Temporal Extent:")
                print(f"     Start: {metadata.temporal_extent_start}")
                print(f"     End: {metadata.temporal_extent_end}")

            print()
            print("-" * 80)

    print()
    print("=" * 80)
    print("DATABASE VERIFICATION COMPLETED")
    print("=" * 80)


if __name__ == '__main__':
    main()
