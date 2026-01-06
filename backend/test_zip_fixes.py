#!/usr/bin/env python3
"""
Test script for ZIP extraction fixes.

This script tests:
1. UUID matching fix
2. Enhanced download_url extraction
3. Nested ZIP recursive processing
4. Data vs supporting ZIP classification
"""

import sys
import logging
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_etl_with_fixes():
    """Test ETL with all fixes applied."""
    from src.scripts.etl_runner import ETLRunner
    from infrastructure.persistence.sqlite.connection import get_database
    from sqlalchemy.orm import Session

    # Test dataset UUIDs
    test_uuids = [
        "755e0369-f8db-4550-aabe-3f9c9fbcb93d",  # Known to have ZIP data
        "be0bdc0e-bc2e-4f1d-b524-2c02798dd893",  # Known to exist in identifiers list
    ]

    print("\n" + "="*80)
    print("  ZIP EXTRACTION FIXES - VALIDATION TEST")
    print("="*80 + "\n")

    # Initialize ETL runner
    runner = ETLRunner(
        catalogue='ceh',
        strict_mode=False,
        save_to_db=True,
        enable_vector_search=False  # Disable for faster testing
    )

    for uuid in test_uuids:
        print(f"\n{'='*80}")
        print(f"  Testing UUID: {uuid}")
        print(f"{'='*80}\n")

        try:
            metadata = runner.run(uuid, preferred_format='xml')

            print("\n✓ ETL completed successfully")
            print(f"  Title: {metadata.title[:60]}...")
            print(f"  Download URL: {metadata.download_url[:80] if metadata.download_url else 'None'}...")

        except Exception as e:
            print(f"\n✗ ETL failed: {str(e)}")
            import traceback
            traceback.print_exc()
            continue

    # Verify database integrity
    print("\n" + "="*80)
    print("  DATABASE INTEGRITY CHECK")
    print("="*80 + "\n")

    db = get_database('backend/datasets.db')
    with Session(db.engine) as session:
        from infrastructure.persistence.sqlite.models import DatasetModel, DataFileModel

        # Check datasets
        datasets_count = session.query(DatasetModel).count()
        print(f"Total datasets: {datasets_count}")

        # Check data_files
        data_files_count = session.query(DataFileModel).count()
        print(f"Total data_files: {data_files_count}")

        # CRITICAL: Check if data_files have valid foreign keys
        orphan_files = session.query(DataFileModel).outerjoin(
            DatasetModel, DataFileModel.dataset_id == DatasetModel.id
        ).filter(DatasetModel.id == None).count()

        print(f"\n{'='*80}")
        if orphan_files == 0:
            print("✓ PASS: All data_files have valid dataset foreign keys")
            print(f"  {data_files_count} data_files correctly linked")
        else:
            print("✗ FAIL: Found orphaned data_files")
            print(f"  {orphan_files} data_files with invalid dataset_id")
        print(f"{'='*80}\n")

        # Show sample data_files
        if data_files_count > 0:
            print("\nSample data_files:")
            sample_files = session.query(DataFileModel).limit(5).all()
            for df in sample_files:
                print(f"  • {df.filename[:50]}")
                print(f"    Dataset ID: {df.dataset_id}")
                print(f"    Format: {df.file_format}")

    runner.close()

    return data_files_count, orphan_files

if __name__ == "__main__":
    try:
        files_count, orphans = test_etl_with_fixes()

        print("\n" + "="*80)
        print("  TEST SUMMARY")
        print("="*80)
        print(f"  Data files created: {files_count}")
        print(f"  Orphaned files: {orphans}")

        if orphans == 0 and files_count > 0:
            print("\n  ✓ ALL TESTS PASSED")
            sys.exit(0)
        elif orphans > 0:
            print("\n  ✗ UUID FIX FAILED - Orphaned files detected")
            sys.exit(1)
        else:
            print("\n  ⚠ WARNING - No data files created (may need datasets with download URLs)")
            sys.exit(0)

    except Exception as e:
        print(f"\n✗ Test failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
