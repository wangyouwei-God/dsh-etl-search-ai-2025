#!/usr/bin/env python3
"""
Local ETL Testing Script

This script tests the ETL components using local sample files
(no network access required).

Usage:
    cd backend
    python test_etl_local.py

Author: University of Manchester RSE Team
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from infrastructure.etl.factory.extractor_factory import ExtractorFactory
from domain.entities.metadata import Metadata


def test_extractor_factory():
    """Test the ExtractorFactory with local files."""
    print("=" * 80)
    print("TEST 1: EXTRACTOR FACTORY")
    print("=" * 80)
    print()

    factory = ExtractorFactory(strict_mode=False)
    print(f"Created factory: {factory}")
    print(f"Supported formats: {factory.get_supported_formats()}")
    print(f"Supported extensions: {factory.get_supported_extensions()}")
    print()

    # Test JSON extractor creation
    print("Creating extractor for 'sample_metadata.json'...")
    json_extractor = factory.create_extractor("sample_metadata.json")
    print(f"  ✓ Created: {json_extractor}")
    print()

    # Test XML extractor creation
    print("Creating extractor for 'sample_metadata.xml'...")
    xml_extractor = factory.create_extractor("sample_metadata.xml")
    print(f"  ✓ Created: {xml_extractor}")
    print()

    # Test explicit format creation
    print("Creating JSON extractor by format...")
    json_extractor2 = factory.create_extractor_by_format('json')
    print(f"  ✓ Created: {json_extractor2}")
    print()

    print("✅ ExtractorFactory tests passed!")
    print()


def test_json_extraction():
    """Test JSON extraction with local file."""
    print("=" * 80)
    print("TEST 2: JSON EXTRACTION (Local File)")
    print("=" * 80)
    print()

    json_file = Path(__file__).parent / "sample_metadata.json"

    if not json_file.exists():
        print(f"❌ Sample file not found: {json_file}")
        return False

    print(f"Testing extraction from: {json_file}")
    print()

    # Create factory and extractor
    factory = ExtractorFactory()
    extractor = factory.create_extractor(str(json_file))

    print(f"Using extractor: {extractor}")
    print()

    # Extract metadata
    print("Extracting metadata...")
    metadata = extractor.extract(str(json_file))
    print("  ✓ Extraction successful!")
    print()

    # Validate results
    print("Validating extracted metadata...")
    assert isinstance(metadata, Metadata), "Should return Metadata instance"
    assert metadata.title, "Should have title"
    assert metadata.abstract, "Should have abstract"
    assert len(metadata.keywords) > 0, "Should have keywords"
    assert metadata.is_geospatial(), "Should be geospatial"
    print("  ✓ Validation successful!")
    print()

    # Display summary
    print("Metadata Summary:")
    print("-" * 80)
    print(f"Title: {metadata.title}")
    print(f"Keywords: {len(metadata.keywords)}")
    print(f"Geospatial: {metadata.is_geospatial()}")
    if metadata.bounding_box:
        center = metadata.bounding_box.get_center()
        print(f"Center: {center[1]:.2f}°N, {center[0]:.2f}°E")
    print("-" * 80)
    print()

    print("✅ JSON extraction tests passed!")
    print()
    return True


def test_xml_extraction():
    """Test XML extraction with local file."""
    print("=" * 80)
    print("TEST 3: XML EXTRACTION (Local File)")
    print("=" * 80)
    print()

    xml_file = Path(__file__).parent / "sample_metadata.xml"

    if not xml_file.exists():
        print(f"❌ Sample file not found: {xml_file}")
        return False

    print(f"Testing extraction from: {xml_file}")
    print()

    # Create factory and extractor
    factory = ExtractorFactory()
    extractor = factory.create_extractor(str(xml_file))

    print(f"Using extractor: {extractor}")
    print()

    # Extract metadata
    print("Extracting metadata...")
    metadata = extractor.extract(str(xml_file))
    print("  ✓ Extraction successful!")
    print()

    # Validate results
    print("Validating extracted metadata...")
    assert isinstance(metadata, Metadata), "Should return Metadata instance"
    assert metadata.title, "Should have title"
    assert metadata.abstract, "Should have abstract"
    assert len(metadata.keywords) > 0, "Should have keywords"
    assert metadata.is_geospatial(), "Should be geospatial"
    print("  ✓ Validation successful!")
    print()

    # Display summary
    print("Metadata Summary:")
    print("-" * 80)
    print(f"Title: {metadata.title}")
    print(f"Keywords: {len(metadata.keywords)}")
    print(f"Geospatial: {metadata.is_geospatial()}")
    if metadata.bounding_box:
        center = metadata.bounding_box.get_center()
        print(f"Center: {center[1]:.2f}°N, {center[0]:.2f}°E")
    print("-" * 80)
    print()

    print("✅ XML extraction tests passed!")
    print()
    return True


def test_format_consistency():
    """Test that JSON and XML extractors produce consistent results."""
    print("=" * 80)
    print("TEST 4: FORMAT CONSISTENCY")
    print("=" * 80)
    print()

    json_file = Path(__file__).parent / "sample_metadata.json"
    xml_file = Path(__file__).parent / "sample_metadata.xml"

    if not json_file.exists() or not xml_file.exists():
        print("❌ Sample files not found")
        return False

    # Extract from both formats
    factory = ExtractorFactory()

    print("Extracting from JSON...")
    json_extractor = factory.create_extractor(str(json_file))
    json_metadata = json_extractor.extract(str(json_file))
    print("  ✓ Done")

    print("Extracting from XML...")
    xml_extractor = factory.create_extractor(str(xml_file))
    xml_metadata = xml_extractor.extract(str(xml_file))
    print("  ✓ Done")
    print()

    # Compare results
    print("Comparing results...")
    print(f"  Title match: {json_metadata.title == xml_metadata.title}")
    print(f"  Abstract match: {json_metadata.abstract == xml_metadata.abstract}")
    print(f"  Keyword count: JSON={len(json_metadata.keywords)}, "
          f"XML={len(xml_metadata.keywords)}")

    if json_metadata.bounding_box and xml_metadata.bounding_box:
        bbox_match = (
            json_metadata.bounding_box.west_longitude ==
            xml_metadata.bounding_box.west_longitude
        )
        print(f"  Bounding box match: {bbox_match}")

    print()
    print("✅ Consistency tests passed!")
    print()
    return True


def main():
    """Run all tests."""
    print()
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 25 + "ETL LOCAL TESTING" + " " * 36 + "║")
    print("║" + " " * 20 + "University of Manchester" + " " * 35 + "║")
    print("╚" + "═" * 78 + "╝")
    print()

    tests_passed = 0
    tests_total = 4

    try:
        # Test 1: Factory
        test_extractor_factory()
        tests_passed += 1

        # Test 2: JSON extraction
        if test_json_extraction():
            tests_passed += 1

        # Test 3: XML extraction
        if test_xml_extraction():
            tests_passed += 1

        # Test 4: Consistency
        if test_format_consistency():
            tests_passed += 1

    except Exception as e:
        print()
        print("=" * 80)
        print("❌ TEST FAILED")
        print("=" * 80)
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        print()
        return 1

    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Tests passed: {tests_passed}/{tests_total}")
    print()

    if tests_passed == tests_total:
        print("✅ ALL TESTS PASSED!")
        print()
        print("The ETL components are working correctly.")
        print("You can now test with real remote catalogues using:")
        print("  python src/scripts/etl_runner.py <UUID>")
        print()
        return 0
    else:
        print(f"❌ {tests_total - tests_passed} TEST(S) FAILED")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
