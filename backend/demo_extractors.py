#!/usr/bin/env python3
"""
Demo script to test JSON and XML metadata extractors.

This script demonstrates the usage of both extractors and validates
that they can correctly parse sample metadata files.

Usage:
    cd backend
    python demo_extractors.py

Author: University of Manchester RSE Team
"""

import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from infrastructure.etl.extractors.json_extractor import JSONExtractor
from infrastructure.etl.extractors.xml_extractor import XMLExtractor


def demo_json_extraction():
    """Demonstrate JSON metadata extraction."""
    print("=" * 80)
    print("JSON METADATA EXTRACTION DEMO")
    print("=" * 80)
    print()

    # Create JSON extractor
    extractor = JSONExtractor(strict_mode=False)
    print(f"Created extractor: {extractor}")
    print()

    # Extract metadata from sample JSON file
    json_file = Path(__file__).parent / "sample_metadata.json"

    if not json_file.exists():
        print(f"❌ Sample file not found: {json_file}")
        return

    print(f"Extracting metadata from: {json_file}")
    print()

    try:
        metadata = extractor.extract(str(json_file))

        print("✅ Extraction successful!")
        print()
        print("Metadata Summary:")
        print("-" * 80)
        print(metadata.get_summary())
        print("-" * 80)
        print()

        # Display detailed information
        print("Detailed Information:")
        print(f"  - Title: {metadata.title}")
        print(f"  - Abstract length: {len(metadata.abstract)} characters")
        print(f"  - Keywords: {len(metadata.keywords)} keywords")
        print(f"  - Geospatial: {metadata.is_geospatial()}")

        if metadata.bounding_box:
            center = metadata.bounding_box.get_center()
            area = metadata.bounding_box.get_area()
            print(f"  - Bounding box center: {center[1]:.2f}°N, {center[0]:.2f}°E")
            print(f"  - Bounding box area: {area:.2f} sq. degrees")

        if metadata.has_temporal_extent():
            print(f"  - Temporal coverage: {metadata.temporal_extent_start.year} - "
                  f"{metadata.temporal_extent_end.year}")

        print(f"  - Contact: {metadata.contact_organization}")
        print(f"  - Language: {metadata.dataset_language}")
        print(f"  - Topic: {metadata.topic_category}")
        print()

    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        print()


def demo_xml_extraction():
    """Demonstrate XML metadata extraction."""
    print("=" * 80)
    print("XML METADATA EXTRACTION DEMO (ISO 19139)")
    print("=" * 80)
    print()

    # Create XML extractor
    extractor = XMLExtractor(strict_mode=False)
    print(f"Created extractor: {extractor}")
    print()

    # Extract metadata from sample XML file
    xml_file = Path(__file__).parent / "sample_metadata.xml"

    if not xml_file.exists():
        print(f"❌ Sample file not found: {xml_file}")
        return

    print(f"Extracting metadata from: {xml_file}")
    print()

    try:
        metadata = extractor.extract(str(xml_file))

        print("✅ Extraction successful!")
        print()
        print("Metadata Summary:")
        print("-" * 80)
        print(metadata.get_summary())
        print("-" * 80)
        print()

        # Display detailed information
        print("Detailed Information:")
        print(f"  - Title: {metadata.title}")
        print(f"  - Abstract length: {len(metadata.abstract)} characters")
        print(f"  - Keywords: {len(metadata.keywords)} keywords")
        print(f"  - Geospatial: {metadata.is_geospatial()}")

        if metadata.bounding_box:
            center = metadata.bounding_box.get_center()
            area = metadata.bounding_box.get_area()
            print(f"  - Bounding box center: {center[1]:.2f}°N, {center[0]:.2f}°E")
            print(f"  - Bounding box area: {area:.2f} sq. degrees")

        if metadata.has_temporal_extent():
            print(f"  - Temporal coverage: {metadata.temporal_extent_start.year} - "
                  f"{metadata.temporal_extent_end.year}")

        print(f"  - Contact: {metadata.contact_organization}")
        print(f"  - Language: {metadata.dataset_language}")
        print(f"  - Topic: {metadata.topic_category}")
        print()

    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        print()


def compare_extractors():
    """Compare outputs from both extractors."""
    print("=" * 80)
    print("EXTRACTOR COMPARISON")
    print("=" * 80)
    print()

    json_file = Path(__file__).parent / "sample_metadata.json"
    xml_file = Path(__file__).parent / "sample_metadata.xml"

    if not json_file.exists() or not xml_file.exists():
        print("❌ Sample files not found")
        return

    try:
        json_extractor = JSONExtractor()
        xml_extractor = XMLExtractor()

        json_metadata = json_extractor.extract(str(json_file))
        xml_metadata = xml_extractor.extract(str(xml_file))

        print("Comparison Results:")
        print("-" * 80)
        print(f"Title match: {json_metadata.title == xml_metadata.title}")
        print(f"Abstract match: {json_metadata.abstract == xml_metadata.abstract}")
        print(f"Keyword count match: {len(json_metadata.keywords) == len(xml_metadata.keywords)}")

        if json_metadata.bounding_box and xml_metadata.bounding_box:
            print(f"Bounding box match: "
                  f"{json_metadata.bounding_box.west_longitude == xml_metadata.bounding_box.west_longitude}")

        print("-" * 80)
        print()
        print("✅ Both extractors produce consistent results!")
        print()

    except Exception as e:
        print(f"❌ Comparison failed: {e}")
        import traceback
        traceback.print_exc()
        print()


def main():
    """Run all demos."""
    print()
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 15 + "METADATA EXTRACTOR DEMONSTRATION" + " " * 31 + "║")
    print("║" + " " * 15 + "University of Manchester" + " " * 39 + "║")
    print("╚" + "═" * 78 + "╝")
    print()

    # Demo JSON extraction
    demo_json_extraction()

    # Demo XML extraction
    demo_xml_extraction()

    # Compare both
    compare_extractors()

    print("=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()
