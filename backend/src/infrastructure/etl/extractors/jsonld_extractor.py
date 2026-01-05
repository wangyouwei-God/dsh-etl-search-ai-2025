"""
Infrastructure: JSON-LD (Schema.org) Extractor

This module implements the metadata extraction strategy for JSON-LD formatted 
metadata files using Schema.org vocabulary.

Design Pattern: Strategy Pattern (Concrete Strategy)

Author: University of Manchester RSE Team
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../../')))

from application.interfaces.metadata_extractor import (
    IMetadataExtractor,
    MetadataExtractionError,
    UnsupportedFormatError
)
from domain.entities.metadata import Metadata, BoundingBox


class JSONLDExtractor(IMetadataExtractor):
    """
    Concrete implementation of IMetadataExtractor for JSON-LD (Schema.org) metadata.

    JSON-LD (JavaScript Object Notation for Linked Data) is a method of encoding
    Linked Data using JSON. Schema.org provides a vocabulary for structured data.

    This extractor handles files containing:
    - @context: Schema.org context URL
    - @type: Dataset or similar type
    - Standard Schema.org properties (name, description, keywords, etc.)

    Strategy Pattern:
        - Implements the IMetadataExtractor interface
        - Provides JSON-LD specific extraction logic
        - Maps Schema.org vocabulary to Metadata domain entity

    Example JSON-LD structure:
        {
            "@context": "https://schema.org/",
            "@type": "Dataset",
            "name": "Land Cover Map 2020",
            "description": "High-resolution land cover classification...",
            "keywords": ["land cover", "remote sensing"],
            "spatialCoverage": {
                "@type": "Place",
                "geo": {
                    "@type": "GeoShape",
                    "box": "49.8 -6.4 60.9 1.8"
                }
            }
        }
    """

    # Schema.org type mappings
    SUPPORTED_TYPES = ['Dataset', 'DataCatalog', 'CreativeWork']

    def __init__(self, strict_mode: bool = False):
        """
        Initialize the JSON-LD extractor.

        Args:
            strict_mode: If True, require Schema.org context and type.
                        If False, attempt extraction on any JSON-LD-like structure.
        """
        self.strict_mode = strict_mode

    def extract(self, source_path: str) -> Metadata:
        """
        Extract metadata from a JSON-LD file.

        Args:
            source_path: Path to the JSON-LD metadata file

        Returns:
            Metadata: Validated metadata entity

        Raises:
            FileNotFoundError: If the source file doesn't exist
            MetadataExtractionError: If parsing or extraction fails
            UnsupportedFormatError: If file is not JSON-LD format
        """
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"Metadata file not found: {source_path}")

        if not self.can_extract(source_path):
            raise UnsupportedFormatError(source_path, ["JSON-LD"])

        try:
            with open(source_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Validate JSON-LD structure
            self._validate_jsonld_structure(data, source_path)

            # Transform to Metadata entity
            metadata = self._transform_to_metadata(data)
            return metadata

        except json.JSONDecodeError as e:
            raise MetadataExtractionError(source_path, f"Invalid JSON format: {str(e)}")
        except ValueError as e:
            raise MetadataExtractionError(source_path, f"Validation failed: {str(e)}")
        except Exception as e:
            raise MetadataExtractionError(source_path, f"Extraction error: {str(e)}")

    def can_extract(self, source_path: str) -> bool:
        """
        Check if this extractor can handle the given file.

        Args:
            source_path: Path to the file to check

        Returns:
            bool: True if file has .jsonld extension
        """
        return source_path.lower().endswith('.jsonld')

    def get_supported_format(self) -> str:
        """Get the format name this extractor supports."""
        return 'JSON-LD'

    def _validate_jsonld_structure(self, data: Dict[str, Any], source_path: str) -> None:
        """
        Validate that the data has proper JSON-LD structure.

        Args:
            data: Parsed JSON data
            source_path: Path for error reporting

        Raises:
            MetadataExtractionError: If structure is invalid in strict mode
        """
        if self.strict_mode:
            # Check for @context
            if '@context' not in data:
                raise MetadataExtractionError(
                    source_path,
                    "Missing @context - not valid JSON-LD"
                )
            
            # Check for @type
            data_type = data.get('@type', '')
            if data_type not in self.SUPPORTED_TYPES:
                raise MetadataExtractionError(
                    source_path,
                    f"Unsupported @type: {data_type}. Expected: {self.SUPPORTED_TYPES}"
                )

    def _transform_to_metadata(self, data: Dict[str, Any]) -> Metadata:
        """
        Transform JSON-LD data to Metadata domain entity.

        Maps Schema.org vocabulary to our domain model:
        - name -> title
        - description -> abstract
        - keywords -> keywords
        - spatialCoverage -> bounding_box
        - temporalCoverage -> temporal_extent
        - creator/publisher -> contact info

        Args:
            data: Dictionary containing parsed JSON-LD data

        Returns:
            Metadata: Validated metadata entity
        """
        # Extract title (Schema.org: name)
        title = data.get('name', data.get('headline', '[Missing title]'))

        # Extract abstract (Schema.org: description)
        abstract = data.get('description', '[Missing description]')

        # Extract keywords
        keywords = self._extract_keywords(data)

        # Extract spatial coverage (bounding box)
        bounding_box = self._extract_bounding_box(data.get('spatialCoverage'))

        # Extract temporal coverage
        temporal_start, temporal_end = self._extract_temporal_coverage(
            data.get('temporalCoverage')
        )

        # Extract contact information
        contact_org, contact_email = self._extract_contact(data)

        # Extract metadata date
        metadata_date = self._parse_datetime(
            data.get('dateModified', data.get('datePublished'))
        )
        if metadata_date is None:
            metadata_date = datetime.utcnow()

        # Extract language
        language = data.get('inLanguage', 'eng')
        if isinstance(language, dict):
            language = language.get('name', 'eng')

        return Metadata(
            title=str(title),
            abstract=str(abstract),
            keywords=keywords,
            bounding_box=bounding_box,
            temporal_extent_start=temporal_start,
            temporal_extent_end=temporal_end,
            contact_organization=contact_org,
            contact_email=contact_email,
            metadata_date=metadata_date,
            dataset_language=language,
            topic_category=data.get('about', ''),
            download_url=data.get('distribution', {}).get('contentUrl', '') if isinstance(data.get('distribution'), dict) else '',
            landing_page_url=data.get('url', '')
        )

    def _extract_keywords(self, data: Dict[str, Any]) -> List[str]:
        """Extract keywords from Schema.org structure."""
        keywords = data.get('keywords', [])
        
        if isinstance(keywords, str):
            # Handle comma-separated string
            return [k.strip() for k in keywords.split(',') if k.strip()]
        elif isinstance(keywords, list):
            return [str(k) for k in keywords]
        return []

    def _extract_bounding_box(self, spatial: Optional[Dict]) -> Optional[BoundingBox]:
        """
        Extract bounding box from Schema.org spatialCoverage.

        Supports formats:
        - GeoShape with box property: "south west north east"
        - GeoCoordinates with latitude/longitude
        """
        if spatial is None:
            return None

        try:
            # Handle Place with geo property
            geo = spatial.get('geo', spatial)
            
            if 'box' in geo:
                # Format: "south west north east" or "south,west north,east"
                box_str = geo['box']
                parts = box_str.replace(',', ' ').split()
                if len(parts) == 4:
                    south, west, north, east = map(float, parts)
                    return BoundingBox(
                        west_longitude=west,
                        east_longitude=east,
                        south_latitude=south,
                        north_latitude=north
                    )
            
            # Handle individual coordinates
            if all(k in geo for k in ['latitude', 'longitude']):
                lat = float(geo['latitude'])
                lon = float(geo['longitude'])
                # Create a point (same coords for all corners)
                return BoundingBox(
                    west_longitude=lon,
                    east_longitude=lon,
                    south_latitude=lat,
                    north_latitude=lat
                )

        except (ValueError, TypeError, KeyError):
            pass
        
        return None

    def _extract_temporal_coverage(self, temporal: Optional[str]) -> tuple:
        """
        Extract temporal coverage from Schema.org temporalCoverage.

        Supports formats:
        - "2020-01-01/2020-12-31" (ISO 8601 interval)
        - "2020" (single year)
        - "2020-01-01" (single date)
        """
        if temporal is None:
            return None, None

        try:
            if '/' in temporal:
                # ISO 8601 interval
                start_str, end_str = temporal.split('/')
                return self._parse_datetime(start_str), self._parse_datetime(end_str)
            else:
                # Single date/year
                dt = self._parse_datetime(temporal)
                return dt, dt
        except Exception:
            return None, None

    def _extract_contact(self, data: Dict[str, Any]) -> tuple:
        """Extract contact information from creator/publisher."""
        contact_org = ''
        contact_email = ''

        # Try creator first, then publisher
        for field in ['creator', 'publisher', 'author']:
            entity = data.get(field)
            if entity:
                if isinstance(entity, dict):
                    contact_org = entity.get('name', '')
                    contact_email = entity.get('email', '')
                elif isinstance(entity, str):
                    contact_org = entity
                if contact_org:
                    break

        return contact_org, contact_email

    def _parse_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO 8601 date string."""
        if date_str is None or not isinstance(date_str, str):
            return None

        try:
            # Clean up timezone suffix
            if date_str.endswith('Z'):
                date_str = date_str[:-1]

            for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d', '%Y']:
                try:
                    return datetime.strptime(date_str.split('+')[0].split('.')[0], fmt)
                except ValueError:
                    continue
            return None
        except Exception:
            return None

    def __repr__(self) -> str:
        mode = "strict" if self.strict_mode else "lenient"
        return f"JSONLDExtractor(mode={mode})"
