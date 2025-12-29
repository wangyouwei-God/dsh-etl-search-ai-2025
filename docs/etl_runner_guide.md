# ETL Runner Guide

## University of Manchester - Dataset Search and Discovery Solution

**ETL Runner**: Complete orchestration script for metadata ingestion from remote catalogues.

---

## Overview

The ETL Runner provides a command-line interface for the complete metadata ingestion pipeline:

1. **Fetch**: Download metadata from remote catalogues (CEH, CEDA)
2. **Extract**: Parse metadata using appropriate extractor (JSON/XML)
3. **Validate**: Ensure metadata conforms to ISO 19115 standards
4. **Display**: Show structured metadata information

---

## Architecture

### Component Stack

```
ETL Runner (scripts/etl_runner.py)
    ↓ orchestrates
┌─────────────────────────────────────────────┐
│ MetadataFetcher (infrastructure/etl/)       │
│   - Tries multiple URL patterns            │
│   - Downloads to temp directory            │
│   - Format detection and fallback          │
└─────────────────────────────────────────────┘
    ↓ downloads file
┌─────────────────────────────────────────────┐
│ ExtractorFactory (infrastructure/etl/)      │
│   - Detects file format                    │
│   - Creates appropriate extractor          │
└─────────────────────────────────────────────┘
    ↓ creates
┌─────────────────────────────────────────────┐
│ JSONExtractor / XMLExtractor               │
│   - Parses file format                     │
│   - Maps to domain entities                │
└─────────────────────────────────────────────┘
    ↓ returns
┌─────────────────────────────────────────────┐
│ Metadata (domain/entities/)                │
│   - Validated domain entity                │
│   - Business rules enforced                │
└─────────────────────────────────────────────┘
```

### Design Patterns Applied

1. **Facade Pattern** (`ETLRunner`): Simplifies complex multi-step process
2. **Factory Pattern** (`ExtractorFactory`): Creates appropriate extractor
3. **Strategy Pattern** (Extractors): Interchangeable parsing strategies
4. **Service Pattern** (`MetadataFetcher`): Encapsulates fetching logic

---

## Usage

### Basic Usage

```bash
cd backend
python src/scripts/etl_runner.py <UUID>
```

**Example**:
```bash
python src/scripts/etl_runner.py 1d33a8a1-4c7e-4d6f-b8c1-c158c1f5a8e2
```

### Command-Line Options

```
usage: etl_runner.py [-h] [--catalogue {ceh,ceda}] [--format {json,xml}]
                     [--strict] [--timeout TIMEOUT] [--retries RETRIES]
                     [--verbose] [--quiet]
                     uuid

ETL Runner for Dataset Metadata Ingestion

positional arguments:
  uuid                  Dataset UUID or identifier

optional arguments:
  -h, --help            show this help message and exit
  --catalogue {ceh,ceda}
                        Catalogue to fetch from (default: ceh)
  --format {json,xml}   Preferred metadata format (default: auto-detect)
  --strict              Enable strict validation (all fields required)
  --timeout TIMEOUT     HTTP timeout in seconds (default: 60)
  --retries RETRIES     Maximum retry attempts (default: 3)
  --verbose             Enable verbose logging
  --quiet               Suppress all output except errors
```

### Examples

#### 1. Basic Fetch (Auto-detect Format)
```bash
python src/scripts/etl_runner.py abc123
```
Tries JSON first, falls back to XML if needed.

#### 2. Force JSON Format
```bash
python src/scripts/etl_runner.py abc123 --format json
```
Only attempts JSON format.

#### 3. Strict Validation Mode
```bash
python src/scripts/etl_runner.py abc123 --strict
```
Requires all mandatory fields (fails if missing).

#### 4. Fetch from Different Catalogue
```bash
python src/scripts/etl_runner.py xyz789 --catalogue ceda
```

#### 5. Verbose Logging
```bash
python src/scripts/etl_runner.py abc123 --verbose
```
Shows detailed debug information.

#### 6. Quiet Mode (Errors Only)
```bash
python src/scripts/etl_runner.py abc123 --quiet
```
Suppresses all output except errors.

#### 7. Custom Timeout and Retries
```bash
python src/scripts/etl_runner.py abc123 --timeout 120 --retries 5
```
2-minute timeout with 5 retry attempts (for slow/flaky catalogues).

---

## Sample Output

### Successful Execution

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                    DATASET METADATA ETL RUNNER                               ║
║                    University of Manchester                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝

UUID: 1d33a8a1-4c7e-4d6f-b8c1-c158c1f5a8e2
Catalogue: ceh
Format: auto-detect
Strict mode: False

2025-12-29 21:35:00 - INFO - ETL Runner initialized (catalogue=ceh, strict=False)
2025-12-29 21:35:00 - INFO - Starting ETL process for UUID: 1d33a8a1...
2025-12-29 21:35:00 - INFO - Step 1: Fetching metadata from catalogue...
2025-12-29 21:35:02 - INFO - ✓ Fetched json metadata to /tmp/metadata_1d33a8a1.json
2025-12-29 21:35:02 - INFO - Step 2: Creating extractor...
2025-12-29 21:35:02 - INFO - ✓ Created JSONExtractor
2025-12-29 21:35:02 - INFO - Step 3: Extracting metadata...
2025-12-29 21:35:02 - INFO - ✓ Successfully extracted metadata
2025-12-29 21:35:02 - INFO - Step 4: Validating metadata...
2025-12-29 21:35:02 - INFO - ✓ Geospatial dataset detected
2025-12-29 21:35:02 - INFO - ✓ Temporal extent: 2010 - 2020
================================================================================
ETL PROCESS COMPLETED SUCCESSFULLY
================================================================================

╔══════════════════════════════════════════════════════════════════════════════╗
║                         EXTRACTED METADATA                                   ║
╚══════════════════════════════════════════════════════════════════════════════╝

================================================================================
SUMMARY
================================================================================
Title: UK Rainfall Dataset 2010-2020
Abstract: Comprehensive rainfall measurements from weather stations across...
Keywords: rainfall, precipitation, United Kingdom, climate, meteorology
Geospatial: Yes
Center: 54.50°N, -2.50°E
Temporal: 2010 - 2020
================================================================================

DETAILED INFORMATION
--------------------------------------------------------------------------------
Title:
  UK Rainfall Dataset 2010-2020

Abstract (255 characters):
  Comprehensive rainfall measurements from weather stations across the
  United Kingdom covering the period 2010-2020. Data includes daily
  precipitation totals, quality flags, and station metadata.

Keywords (5):
  1. rainfall
  2. precipitation
  3. United Kingdom
  4. climate
  5. meteorology

Geographic Extent:
  West:  -8.0°
  East:  2.0°
  South: 50.0°
  North: 59.0°
  Center: 54.5000°N, -3.0000°E
  Area: 90.00 square degrees

Temporal Coverage:
  Start: 2010-01-01 00:00:00
  End:   2020-12-31 00:00:00
  Duration: 4017 days

Contact Information:
  Organization: Centre for Ecology & Hydrology
  Email: enquiries@ceh.ac.uk

Additional Metadata:
  Language: eng
  Topic Category: climatologyMeteorologyAtmosphere
  Metadata Date: 2023-06-15 10:30:00

================================================================================
```

---

## Components Deep Dive

### 1. MetadataFetcher (`infrastructure/etl/fetcher.py`)

**Purpose**: Download metadata from remote catalogues with format detection.

**Features**:
- Multiple URL pattern attempts (JSON, XML, Gemini XML)
- Automatic format detection
- Retry logic for network failures
- Temporary file management

**URL Patterns for CEH**:
```python
'ceh': {
    'json_url': 'https://catalogue.ceh.ac.uk/id/{uuid}.json',
    'xml_url': 'https://catalogue.ceh.ac.uk/id/{uuid}.xml',
    'gemini_xml_url': 'https://catalogue.ceh.ac.uk/id/{uuid}/gemini.xml',
}
```

**Fetch Strategy**:
1. Try JSON URL (if preferred or first attempt)
2. Try standard XML URL
3. Try Gemini XML URL (CEH-specific)
4. Try base URL with content negotiation

**Example**:
```python
from infrastructure.etl.fetcher import MetadataFetcher

fetcher = MetadataFetcher(catalogue='ceh', timeout=60)
file_path, format_type = fetcher.fetch('abc123')
print(f"Downloaded {format_type} to {file_path}")
```

### 2. ExtractorFactory (`infrastructure/etl/factory/extractor_factory.py`)

**Purpose**: Create appropriate metadata extractor based on file format.

**Features**:
- Automatic format detection from file extension
- Explicit format specification
- Extendable registry for new formats
- Strict/lenient mode configuration

**Example**:
```python
from infrastructure.etl.factory.extractor_factory import ExtractorFactory

factory = ExtractorFactory(strict_mode=False)

# Auto-detect from file extension
extractor = factory.create_extractor("metadata.json")

# Or specify format explicitly
extractor = factory.create_extractor_by_format("xml")

# Use the extractor
metadata = extractor.extract("path/to/file.xml")
```

### 3. ETLRunner (`scripts/etl_runner.py`)

**Purpose**: Orchestrate the complete ETL pipeline.

**Process**:
1. Initialize services (Fetcher, Factory)
2. Fetch metadata from catalogue
3. Create appropriate extractor
4. Extract and validate metadata
5. Return domain entity

**Example (Programmatic Use)**:
```python
from scripts.etl_runner import ETLRunner

runner = ETLRunner(catalogue='ceh', strict_mode=False)
metadata = runner.run('abc123', preferred_format='json')

print(f"Title: {metadata.title}")
print(f"Keywords: {len(metadata.keywords)}")
```

---

## Error Handling

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Fetch error (network, catalogue unavailable) |
| 2 | Extraction error (parsing failed) |
| 3 | Validation error (metadata invalid) |
| 4 | Unexpected error |
| 130 | User interrupted (Ctrl+C) |

### Error Examples

#### Fetch Error (Network Issue)
```bash
$ python src/scripts/etl_runner.py abc123
ERROR - Failed to fetch metadata: Connection error: ...
Exit code: 1
```

#### Extraction Error (Invalid JSON)
```bash
$ python src/scripts/etl_runner.py abc123 --format json
ERROR - Failed to extract metadata: Invalid JSON format
Exit code: 2
```

#### Validation Error (Missing Required Fields)
```bash
$ python src/scripts/etl_runner.py abc123 --strict
ERROR - Metadata validation failed: Required field 'title' is missing
Exit code: 3
```

---

## Real-World Examples

### Example 1: CEH Rainfall Dataset
```bash
python src/scripts/etl_runner.py 1d33a8a1-4c7e-4d6f-b8c1-c158c1f5a8e2
```

**Dataset**: UK Rainfall observations
**Catalogue**: CEH (Centre for Ecology & Hydrology)
**Expected**: JSON format available, geospatial dataset

### Example 2: CEH Land Cover Map
```bash
python src/scripts/etl_runner.py a344d217-5320-4dae-8f6f-39a7f975f14a
```

**Dataset**: Land Cover Map 2020
**Catalogue**: CEH
**Expected**: Large bounding box covering UK

### Example 3: CEDA Climate Model Output
```bash
python src/scripts/etl_runner.py abc123 --catalogue ceda
```

**Dataset**: Climate model data
**Catalogue**: CEDA (Centre for Environmental Data Analysis)
**Expected**: XML format with extensive temporal coverage

---

## Testing

### Unit Testing Approach

```python
# Test MetadataFetcher
def test_metadata_fetcher():
    fetcher = MetadataFetcher(catalogue='ceh')
    path, fmt = fetcher.fetch('test-uuid')
    assert os.path.exists(path)
    assert fmt in ['json', 'xml']

# Test ExtractorFactory
def test_extractor_factory():
    factory = ExtractorFactory()
    json_extractor = factory.create_extractor("test.json")
    assert isinstance(json_extractor, JSONExtractor)

    xml_extractor = factory.create_extractor("test.xml")
    assert isinstance(xml_extractor, XMLExtractor)

# Test ETLRunner
def test_etl_runner():
    runner = ETLRunner(catalogue='ceh')
    metadata = runner.run('test-uuid')
    assert metadata.title
    assert metadata.abstract
```

### Integration Testing

```bash
# Test with real CEH UUID
python src/scripts/etl_runner.py 1d33a8a1-4c7e-4d6f-b8c1-c158c1f5a8e2 --verbose

# Test JSON format preference
python src/scripts/etl_runner.py 1d33a8a1-4c7e-4d6f-b8c1-c158c1f5a8e2 --format json

# Test XML fallback
python src/scripts/etl_runner.py 1d33a8a1-4c7e-4d6f-b8c1-c158c1f5a8e2 --format xml

# Test strict mode
python src/scripts/etl_runner.py 1d33a8a1-4c7e-4d6f-b8c1-c158c1f5a8e2 --strict
```

---

## Extension Points

### Adding New Catalogues

Edit `fetcher.py` to add new catalogue patterns:

```python
CATALOGUE_PATTERNS = {
    'ceh': { ... },
    'ceda': { ... },
    'new_catalogue': {
        'base_url': 'https://catalogue.example.com/{uuid}',
        'json_url': 'https://catalogue.example.com/{uuid}.json',
        'xml_url': 'https://catalogue.example.com/{uuid}.xml',
    }
}
```

### Adding New Extractors

1. Create extractor class implementing `IMetadataExtractor`
2. Register with factory:

```python
from infrastructure.etl.extractors.csv_extractor import CSVExtractor

factory = ExtractorFactory()
factory.register_extractor('csv', CSVExtractor, ['.csv', '.tsv'])
```

---

## Troubleshooting

### Issue: "UnsupportedFormatError"
**Cause**: File format not recognized
**Solution**: Check file extension, verify it's `.json` or `.xml`

### Issue: "Connection timeout"
**Cause**: Slow network or catalogue down
**Solution**: Increase timeout: `--timeout 120`

### Issue: "Failed to fetch metadata"
**Cause**: UUID not found in catalogue
**Solution**: Verify UUID is correct, try different catalogue

### Issue: "Metadata validation failed"
**Cause**: Missing required fields
**Solution**: Use lenient mode (remove `--strict` flag)

---

## Best Practices

1. **Start with auto-detect**: Let the system try JSON first (faster)
2. **Use verbose mode for debugging**: `--verbose` shows all steps
3. **Increase retries for flaky catalogues**: `--retries 5`
4. **Use strict mode for production**: Ensures data quality
5. **Log outputs for auditing**: Redirect stdout to log files

---

## Performance Considerations

- **JSON is faster than XML**: Prefer JSON when available
- **Network latency**: Typical fetch takes 1-5 seconds
- **Parsing time**: JSON ~0.1s, XML ~0.5s
- **Retry overhead**: 3 retries can add 10-30 seconds

---

## Future Enhancements

1. **Batch processing**: Process multiple UUIDs from CSV file
2. **Caching**: Store downloaded metadata to avoid re-fetching
3. **Database integration**: Save extracted metadata to SQLite
4. **Async support**: Concurrent downloads for multiple datasets
5. **Validation reports**: Generate detailed validation reports
6. **Web UI**: Browser-based interface for ETL operations

---

## Conclusion

The ETL Runner provides a production-ready solution for metadata ingestion with:
- ✅ Robust error handling and retry logic
- ✅ Multiple catalogue support
- ✅ Format auto-detection and fallback
- ✅ Clean Architecture compliance
- ✅ Comprehensive logging and reporting

Ready for integration with:
- Use cases (Application layer)
- Repository implementations (Persistence)
- REST API endpoints (Presentation layer)

---

**Document Version**: 1.0
**Author**: University of Manchester RSE Team
**Last Updated**: 2025-12-29
