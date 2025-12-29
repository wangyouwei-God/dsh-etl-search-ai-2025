"""
Infrastructure: JSONExtractor

This module implements the metadata extraction strategy for JSON-formatted metadata files.
This is part of the Infrastructure layer and handles the technical details of
parsing JSON files and mapping them to domain entities.

Design Pattern: Strategy Pattern (Concrete Strategy)

Author: University of Manchester RSE Team
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
import sys

# Add the parent directory to the path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../../')))

from application.interfaces.metadata_extractor import (
    IMetadataExtractor,
    MetadataExtractionError,
    UnsupportedFormatError
)
from domain.entities.metadata import Metadata, BoundingBox


class JSONExtractor(IMetadataExtractor):
    """
    Concrete implementation of IMetadataExtractor for JSON-formatted metadata.

    This extractor handles JSON files that contain ISO 19115 metadata in a
    structured format. It parses the JSON, validates the structure, and
    transforms it into a Metadata domain entity.

    Strategy Pattern:
        - Implements the IMetadataExtractor interface
        - Provides JSON-specific extraction logic
        - Can be swapped with other extractors (XML, CSV, etc.)

    Attributes:
        strict_mode: If True, raises errors for missing fields.
                    If False, uses default values for missing fields.

    Example JSON structure expected:
        {
            "title": "Climate Dataset 2023",
            "abstract": "Temperature measurements...",
            "keywords": ["climate", "temperature"],
            "bounding_box": {
                "west": -180.0,
                "east": 180.0,
                "south": -90.0,
                "north": 90.0
            },
            "contact": {
                "organization": "University of Manchester",
                "email": "data@manchester.ac.uk"
            }
        }
    """

    def __init__(self, strict_mode: bool = False):
        """
        Initialize the JSON extractor.

        Args:
            strict_mode: If True, require all fields to be present.
                        If False, use defaults for missing optional fields.
        """
        self.strict_mode = strict_mode

    def extract(self, source_path: str) -> Metadata:
        """
        Extract metadata from a JSON file.

        Args:
            source_path: Path to the JSON metadata file

        Returns:
            Metadata: Validated metadata entity

        Raises:
            FileNotFoundError: If the source file doesn't exist
            MetadataExtractionError: If parsing or extraction fails
            ValueError: If metadata validation fails
        """
        # Validate file exists
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"Metadata file not found: {source_path}")

        # Check if we can handle this file
        if not self.can_extract(source_path):
            raise UnsupportedFormatError(source_path, ["JSON"])

        try:
            # Read and parse JSON file
            with open(source_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Transform JSON data to Metadata entity
            metadata = self._transform_to_metadata(data)

            return metadata

        except json.JSONDecodeError as e:
            raise MetadataExtractionError(
                source_path,
                f"Invalid JSON format: {str(e)}"
            )
        except ValueError as e:
            # Re-raise validation errors from Metadata entity
            raise MetadataExtractionError(
                source_path,
                f"Metadata validation failed: {str(e)}"
            )
        except Exception as e:
            raise MetadataExtractionError(
                source_path,
                f"Unexpected error during extraction: {str(e)}"
            )

    def can_extract(self, source_path: str) -> bool:
        """
        Check if this extractor can handle the given file.

        Args:
            source_path: Path to the file to check

        Returns:
            bool: True if file has .json extension, False otherwise
        """
        return source_path.lower().endswith('.json')

    def get_supported_format(self) -> str:
        """
        Get the format name this extractor supports.

        Returns:
            str: 'JSON'
        """
        return 'JSON'

    def _transform_to_metadata(self, data: Dict[str, Any]) -> Metadata:
        """
        Transform raw JSON data into a Metadata domain entity.

        This is the core transformation logic that maps JSON structure to
        the domain model. It handles nested objects and optional fields.

        Args:
            data: Dictionary containing parsed JSON data

        Returns:
            Metadata: Validated metadata entity

        Raises:
            ValueError: If required fields are missing in strict mode
        """
        # Extract mandatory fields
        title = self._get_required_field(data, 'title')
        abstract = self._get_required_field(data, 'abstract')

        # Extract optional fields with defaults
        keywords = data.get('keywords', [])
        if not isinstance(keywords, list):
            keywords = []

        # Extract bounding box if present
        bounding_box = self._extract_bounding_box(data.get('bounding_box'))

        # Extract temporal extent
        temporal_start = self._parse_datetime(data.get('temporal_extent', {}).get('start'))
        temporal_end = self._parse_datetime(data.get('temporal_extent', {}).get('end'))

        # Extract contact information
        contact = data.get('contact', {})
        contact_organization = contact.get('organization', '')
        contact_email = contact.get('email', '')

        # Extract metadata date
        metadata_date = self._parse_datetime(data.get('metadata_date'))
        if metadata_date is None:
            metadata_date = datetime.utcnow()

        # Extract language (ISO 639-2 code)
        dataset_language = data.get('language', 'eng')

        # Extract topic category
        topic_category = data.get('topic_category', '')

        # Create and return Metadata entity
        # The Metadata constructor will validate invariants
        return Metadata(
            title=title,
            abstract=abstract,
            keywords=keywords,
            bounding_box=bounding_box,
            temporal_extent_start=temporal_start,
            temporal_extent_end=temporal_end,
            contact_organization=contact_organization,
            contact_email=contact_email,
            metadata_date=metadata_date,
            dataset_language=dataset_language,
            topic_category=topic_category
        )

    def _get_required_field(self, data: Dict[str, Any], field_name: str) -> str:
        """
        Extract a required field from the data dictionary.

        Args:
            data: Source dictionary
            field_name: Name of the required field

        Returns:
            str: Field value

        Raises:
            ValueError: If field is missing and strict_mode is True
        """
        value = data.get(field_name)

        if value is None or (isinstance(value, str) and not value.strip()):
            if self.strict_mode:
                raise ValueError(f"Required field '{field_name}' is missing or empty")
            else:
                # Return a placeholder value in non-strict mode
                return f"[Missing {field_name}]"

        return str(value)

    def _extract_bounding_box(self, bbox_data: Optional[Dict[str, Any]]) -> Optional[BoundingBox]:
        """
        Extract and validate a bounding box from JSON data.

        Args:
            bbox_data: Dictionary containing bounding box coordinates

        Returns:
            BoundingBox or None if data is not provided

        Raises:
            ValueError: If bounding box data is invalid
        """
        if bbox_data is None:
            return None

        try:
            # Support both verbose and short field names
            west = bbox_data.get('west', bbox_data.get('west_longitude'))
            east = bbox_data.get('east', bbox_data.get('east_longitude'))
            south = bbox_data.get('south', bbox_data.get('south_latitude'))
            north = bbox_data.get('north', bbox_data.get('north_latitude'))

            if any(coord is None for coord in [west, east, south, north]):
                if self.strict_mode:
                    raise ValueError("Incomplete bounding box coordinates")
                return None

            # BoundingBox constructor will validate the coordinates
            return BoundingBox(
                west_longitude=float(west),
                east_longitude=float(east),
                south_latitude=float(south),
                north_latitude=float(north)
            )

        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid bounding box data: {str(e)}")

    def _parse_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        """
        Parse a datetime string into a datetime object.

        Supports common ISO 8601 formats:
        - YYYY-MM-DD
        - YYYY-MM-DDTHH:MM:SS
        - YYYY-MM-DDTHH:MM:SSZ

        Args:
            date_str: ISO 8601 formatted date string

        Returns:
            datetime object or None if parsing fails or input is None
        """
        if date_str is None or not isinstance(date_str, str):
            return None

        try:
            # Try parsing with timezone info
            if date_str.endswith('Z'):
                date_str = date_str[:-1] + '+00:00'

            # Handle different datetime formats
            for fmt in [
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%S.%f',
                '%Y-%m-%d',
            ]:
                try:
                    return datetime.strptime(date_str.split('+')[0].split('.')[0], fmt)
                except ValueError:
                    continue

            # If no format matched, return None
            return None

        except Exception:
            return None

    def __repr__(self) -> str:
        """Return string representation of the extractor."""
        mode = "strict" if self.strict_mode else "lenient"
        return f"JSONExtractor(mode={mode})"
