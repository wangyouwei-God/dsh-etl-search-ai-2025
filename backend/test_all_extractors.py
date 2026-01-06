#!/usr/bin/env python3
"""
Test all 4 metadata extractors (XML, JSON, JSON-LD, RDF) to demonstrate
they all work correctly.
"""

import sys
import os
sys.path.insert(0, 'src')

from infrastructure.etl.factory.extractor_factory import ExtractorFactory
from infrastructure.etl.extractors.xml_extractor import XMLExtractor
from infrastructure.etl.extractors.json_extractor import JSONExtractor
from infrastructure.etl.extractors.jsonld_extractor import JSONLDExtractor
from infrastructure.etl.extractors.rdf_extractor import RDFExtractor
import sqlite3
from pathlib import Path
import json

def test_extractor(extractor_name, extractor_class, test_file):
    """Test a single extractor."""
    print(f'\n{"="*60}')
    print(f'Testing {extractor_name}')
    print(f'File: {test_file}')
    print('=' * 60)

    if not Path(test_file).exists():
        print(f'✗ Test file not found: {test_file}')
        return False

    try:
        extractor = extractor_class(strict_mode=False)
        metadata = extractor.extract(test_file)

        print(f'✓ Extraction successful!')
        print(f'\nExtracted Metadata:')
        print(f'  - Title: {metadata.title[:80]}...' if len(metadata.title) > 80 else f'  - Title: {metadata.title}')
        print(f'  - Abstract: {len(metadata.abstract)} characters')
        print(f'  - Keywords: {metadata.keywords}')
        print(f'  - Contact: {metadata.contact_email}')

        if metadata.bounding_box:
            print(f'  - Bounding Box: ({metadata.bounding_box.west_longitude}, {metadata.bounding_box.south_latitude}) to ({metadata.bounding_box.east_longitude}, {metadata.bounding_box.north_latitude})')

        if metadata.temporal_extent_start:
            print(f'  - Temporal Start: {metadata.temporal_extent_start}')

        print(f'\n✅ {extractor_name} WORKING')
        return True

    except Exception as e:
        print(f'✗ Error: {e}')
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run tests for all extractors."""

    print('=' * 60)
    print('EXTRACTOR FUNCTIONALITY TEST')
    print('Testing all 4 metadata extractors')
    print('=' * 60)

    # Prefer local XML sample to avoid relying on DB metadata_url (often JSON)
    xml_file_path = Path(__file__).parent / 'sample_metadata.xml'
    if xml_file_path.exists():
        xml_file = str(xml_file_path)
    else:
        # Fallback: try to get a test XML file from database
        conn = sqlite3.connect('datasets.db')
        cursor = conn.cursor()
        cursor.execute('SELECT dataset_id FROM metadata LIMIT 1')
        result = cursor.fetchone()

        if result:
            dataset_id = result[0]
            cursor.execute('SELECT metadata_url FROM datasets WHERE id = ?', (dataset_id,))
            result2 = cursor.fetchone()
            xml_file = result2[0] if result2 else None
        else:
            xml_file = None

        conn.close()

        if not xml_file:
            print('✗ No test XML file found (sample missing and DB empty)')
            return 1

    # Test results
    results = {}

    # Test 1: XML Extractor
    results['XML'] = test_extractor(
        'XML Extractor',
        XMLExtractor,
        xml_file
    )

    # Test 2: JSON Extractor (we'll create a mock JSON file)
    print(f'\n{"="*60}')
    print('Testing JSON Extractor')
    print('=' * 60)

    # Create a test JSON metadata file
    test_json = {
        "title": "Test JSON Metadata",
        "abstract": "This is a test abstract to demonstrate the JSON extractor works correctly with all required ISO 19115 fields.",
        "keywords": ["Testing", "JSON", "Metadata"],
        "contactEmail": "test@example.com",
        "contactOrganization": "Test Organization",
        "boundingBox": {
            "west": -180.0,
            "east": 180.0,
            "south": -90.0,
            "north": 90.0
        },
        "temporalExtent": {
            "start": "2020-01-01T00:00:00",
            "end": "2023-12-31T23:59:59"
        },
        "language": "eng",
        "topicCategory": "environment"
    }

    test_json_file = Path('test_metadata.json')
    with open(test_json_file, 'w') as f:
        json.dump(test_json, f, indent=2)

    try:
        extractor = JSONExtractor(strict_mode=False)
        metadata = extractor.extract(str(test_json_file))

        print(f'✓ JSON Extraction successful!')
        print(f'\nExtracted Metadata:')
        print(f'  - Title: {metadata.title}')
        print(f'  - Abstract: {len(metadata.abstract)} characters')
        print(f'  - Keywords: {metadata.keywords}')
        print(f'  - Contact: {metadata.contact_email}')

        if metadata.bounding_box:
            print(f'  - Bounding Box: ({metadata.bounding_box.west_longitude}, {metadata.bounding_box.south_latitude}) to ({metadata.bounding_box.east_longitude}, {metadata.bounding_box.north_latitude})')

        print(f'\n✅ JSON Extractor WORKING')
        results['JSON'] = True

    except Exception as e:
        print(f'✗ JSON Extractor Error: {e}')
        import traceback
        traceback.print_exc()
        results['JSON'] = False
    finally:
        if test_json_file.exists():
            test_json_file.unlink()

    # Test 3: JSON-LD Extractor
    print(f'\n{"="*60}')
    print('Testing JSON-LD Extractor')
    print('=' * 60)

    # Create a test JSON-LD file (Schema.org Dataset)
    test_jsonld = {
        "@context": "https://schema.org/",
        "@type": "Dataset",
        "name": "Test JSON-LD Dataset",
        "description": "This demonstrates the JSON-LD extractor working with Schema.org vocabulary for metadata extraction.",
        "keywords": ["JSON-LD", "Schema.org", "Testing"],
        "creator": {
            "@type": "Organization",
            "name": "Test Organization",
            "email": "test@example.com"
        },
        "spatialCoverage": {
            "@type": "Place",
            "geo": {
                "@type": "GeoShape",
                "box": "-90,-180 90,180"
            }
        },
        "temporalCoverage": "2020-01-01/2023-12-31"
    }

    test_jsonld_file = Path('test_metadata.jsonld')
    with open(test_jsonld_file, 'w') as f:
        json.dump(test_jsonld, f, indent=2)

    try:
        extractor = JSONLDExtractor(strict_mode=False)
        metadata = extractor.extract(str(test_jsonld_file))

        print(f'✓ JSON-LD Extraction successful!')
        print(f'\nExtracted Metadata:')
        print(f'  - Title: {metadata.title}')
        print(f'  - Abstract: {len(metadata.abstract)} characters')
        print(f'  - Keywords: {metadata.keywords}')
        print(f'  - Contact: {metadata.contact_email}')

        print(f'\n✅ JSON-LD Extractor WORKING')
        results['JSON-LD'] = True

    except Exception as e:
        print(f'✗ JSON-LD Extractor Error: {e}')
        import traceback
        traceback.print_exc()
        results['JSON-LD'] = False
    finally:
        if test_jsonld_file.exists():
            test_jsonld_file.unlink()

    # Test 4: RDF Extractor
    print(f'\n{"="*60}')
    print('Testing RDF Extractor')
    print('=' * 60)

    # Create a test RDF/Turtle file (DCAT vocabulary)
    test_rdf = """
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix dct: <http://purl.org/dc/terms/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<http://example.org/dataset/1> a dcat:Dataset ;
    dct:title "Test RDF Dataset" ;
    dct:description "This demonstrates the RDF/Turtle extractor working with DCAT vocabulary for semantic metadata." ;
    dcat:keyword "RDF", "DCAT", "Testing" ;
    dct:creator [
        a foaf:Organization ;
        foaf:name "Test Organization" ;
        foaf:mbox <mailto:test@example.com>
    ] ;
    dct:temporal [
        a dct:PeriodOfTime ;
        dcat:startDate "2020-01-01"^^xsd:date ;
        dcat:endDate "2023-12-31"^^xsd:date
    ] .
"""

    test_rdf_file = Path('test_metadata.ttl')
    with open(test_rdf_file, 'w') as f:
        f.write(test_rdf)

    try:
        extractor = RDFExtractor(strict_mode=False)
        metadata = extractor.extract(str(test_rdf_file))

        print(f'✓ RDF Extraction successful!')
        print(f'\nExtracted Metadata:')
        print(f'  - Title: {metadata.title}')
        print(f'  - Abstract: {len(metadata.abstract)} characters')
        print(f'  - Keywords: {metadata.keywords}')
        print(f'  - Contact: {metadata.contact_email}')

        print(f'\n✅ RDF Extractor WORKING')
        results['RDF'] = True

    except Exception as e:
        print(f'✗ RDF Extractor Error: {e}')
        import traceback
        traceback.print_exc()
        results['RDF'] = False
    finally:
        if test_rdf_file.exists():
            test_rdf_file.unlink()

    # Summary
    print('\n' + '=' * 60)
    print('TEST SUMMARY')
    print('=' * 60)

    for format_name, success in results.items():
        status = '✅ PASS' if success else '❌ FAIL'
        print(f'{format_name:10} {status}')

    total = len(results)
    passed = sum(1 for r in results.values() if r)

    print('=' * 60)
    print(f'Results: {passed}/{total} extractors working')
    print(f'Success Rate: {passed/total*100:.0f}%')
    print('=' * 60)

    if passed == total:
        print('\n🎉 ALL EXTRACTORS WORKING PERFECTLY!')
        return 0
    else:
        print(f'\n⚠️  {total-passed} extractor(s) failed')
        return 1

if __name__ == '__main__':
    sys.exit(main())
