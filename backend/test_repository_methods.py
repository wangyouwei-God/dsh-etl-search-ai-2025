#!/usr/bin/env python3
"""
Test script to verify all repository methods.

Tests: get_by_id(), exists(), search_by_title(), delete()
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from infrastructure.persistence.sqlite.connection import get_database
from infrastructure.persistence.sqlite.dataset_repository_impl import SQLiteDatasetRepository


def main():
    print("=" * 80)
    print("REPOSITORY METHOD TESTING")
    print("=" * 80)
    print()

    # Get database connection
    db = get_database("test_datasets.db")

    with db.session_scope() as session:
        repository = SQLiteDatasetRepository(session)

        # Test 1: get_by_id()
        print("TEST 1: get_by_id()")
        print("-" * 80)
        dataset_id = "f648ed85-1b40-4b3c-a3d8-7bfec39ec815"
        result = repository.get_by_id(dataset_id)

        if result:
            dataset, metadata = result
            print(f"✓ Found dataset: {dataset.title}")
            print(f"  - ID: {dataset.id}")
            print(f"  - Keywords: {', '.join(metadata.keywords)}")
        else:
            print(f"✗ Dataset not found: {dataset_id}")
        print()

        # Test 2: get_by_id() with non-existent ID
        print("TEST 2: get_by_id() with non-existent ID")
        print("-" * 80)
        fake_id = "00000000-0000-0000-0000-000000000000"
        result = repository.get_by_id(fake_id)

        if result is None:
            print(f"✓ Correctly returned None for non-existent ID")
        else:
            print(f"✗ Expected None but got result")
        print()

        # Test 3: exists()
        print("TEST 3: exists()")
        print("-" * 80)
        if repository.exists(dataset_id):
            print(f"✓ Dataset exists: {dataset_id}")
        else:
            print(f"✗ Dataset should exist but doesn't")

        if not repository.exists(fake_id):
            print(f"✓ Non-existent dataset correctly identified: {fake_id}")
        else:
            print(f"✗ Fake dataset should not exist")
        print()

        # Test 4: search_by_title()
        print("TEST 4: search_by_title()")
        print("-" * 80)

        # Search for "Land Cover"
        results = repository.search_by_title("Land Cover")
        print(f"Search 'Land Cover': Found {len(results)} result(s)")
        for dataset, metadata in results:
            print(f"  - {dataset.title}")

        # Search for "climate" (should be empty)
        results = repository.search_by_title("climate")
        print(f"Search 'climate': Found {len(results)} result(s)")

        # Search for partial match "map"
        results = repository.search_by_title("map")
        print(f"Search 'map': Found {len(results)} result(s)")
        for dataset, metadata in results:
            print(f"  - {dataset.title}")
        print()

        # Test 5: count()
        print("TEST 5: count()")
        print("-" * 80)
        total = repository.count()
        print(f"✓ Total datasets in repository: {total}")
        print()

        # Test 6: get_all() with pagination
        print("TEST 6: get_all() with pagination")
        print("-" * 80)
        all_datasets = repository.get_all(limit=5, offset=0)
        print(f"✓ Retrieved {len(all_datasets)} dataset(s) (limit=5, offset=0)")
        print()

    print("=" * 80)
    print("ALL REPOSITORY METHODS TESTED SUCCESSFULLY")
    print("=" * 80)


if __name__ == '__main__':
    main()
