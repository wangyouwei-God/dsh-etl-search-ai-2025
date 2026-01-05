"""
Infrastructure: RDF (Turtle) Extractor

This module implements the metadata extraction strategy for RDF Turtle (.ttl) 
formatted metadata files.

Design Pattern: Strategy Pattern (Concrete Strategy)

Author: University of Manchester RSE Team
"""

import os
import re
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../../')))

from application.interfaces.metadata_extractor import (
    IMetadataExtractor,
    MetadataExtractionError,
    UnsupportedFormatError
)
from domain.entities.metadata import Metadata, BoundingBox


class RDFExtractor(IMetadataExtractor):
    """
    Concrete implementation of IMetadataExtractor for RDF Turtle format.

    RDF (Resource Description Framework) Turtle is a textual syntax for RDF
    that allows representing triples in a compact and natural form.

    This extractor parses Turtle files using regex patterns without external
    dependencies, extracting Dublin Core and DCAT vocabulary properties.

    Strategy Pattern:
        - Implements the IMetadataExtractor interface
        - Provides RDF/Turtle specific extraction logic
        - Maps RDF vocabularies (DC, DCAT) to Metadata domain entity

    Supported vocabularies:
        - Dublin Core (dc:, dct:, dcterms:)
        - DCAT (dcat:)
        - Schema.org (schema:)
        - FOAF (foaf:)

    Example Turtle structure:
        @prefix dct: <http://purl.org/dc/terms/> .
        @prefix dcat: <http://www.w3.org/ns/dcat#> .

        <http://example.org/dataset/1> a dcat:Dataset ;
            dct:title "Land Cover Map 2020" ;
            dct:description "High-resolution land cover..." ;
            dcat:keyword "land cover", "remote sensing" .
    """

    # Common RDF namespace prefixes
    NAMESPACE_PATTERNS = {
        'dc': r'http://purl\.org/dc/elements/1\.1/',
        'dct': r'http://purl\.org/dc/terms/',
        'dcterms': r'http://purl\.org/dc/terms/',
        'dcat': r'http://www\.w3\.org/ns/dcat#',
        'schema': r'https?://schema\.org/',
        'foaf': r'http://xmlns\.com/foaf/0\.1/',
        'geo': r'http://www\.w3\.org/2003/01/geo/wgs84_pos#',
    }

    def __init__(self, strict_mode: bool = False):
        """
        Initialize the RDF Turtle extractor.

        Args:
            strict_mode: If True, require proper RDF structure.
                        If False, attempt best-effort extraction.
        """
        self.strict_mode = strict_mode

    def extract(self, source_path: str) -> Metadata:
        """
        Extract metadata from an RDF Turtle file.

        Args:
            source_path: Path to the .ttl metadata file

        Returns:
            Metadata: Validated metadata entity

        Raises:
            FileNotFoundError: If the source file doesn't exist
            MetadataExtractionError: If parsing fails
            UnsupportedFormatError: If file is not Turtle format
        """
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"Metadata file not found: {source_path}")

        if not self.can_extract(source_path):
            raise UnsupportedFormatError(source_path, ["RDF/Turtle"])

        try:
            with open(source_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse prefixes
            prefixes = self._parse_prefixes(content)

            # Extract triples
            triples = self._parse_triples(content, prefixes)

            # Transform to Metadata entity
            metadata = self._transform_to_metadata(triples)
            return metadata

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
            bool: True if file has .ttl or .turtle extension
        """
        lower_path = source_path.lower()
        return lower_path.endswith('.ttl') or lower_path.endswith('.turtle')

    def get_supported_format(self) -> str:
        """Get the format name this extractor supports."""
        return 'RDF/Turtle'

    def _parse_prefixes(self, content: str) -> Dict[str, str]:
        """
        Parse @prefix declarations from Turtle content.

        Args:
            content: Raw Turtle file content

        Returns:
            Dict mapping prefix names to namespace URIs
        """
        prefixes = {}
        prefix_pattern = r'@prefix\s+(\w+):\s*<([^>]+)>\s*\.'
        
        for match in re.finditer(prefix_pattern, content, re.IGNORECASE):
            prefix_name = match.group(1)
            namespace_uri = match.group(2)
            prefixes[prefix_name] = namespace_uri

        return prefixes

    def _parse_triples(self, content: str, prefixes: Dict[str, str]) -> Dict[str, List[str]]:
        """
        Parse subject-predicate-object triples from Turtle content.

        This is a simplified parser that extracts property values
        without building a full RDF graph.

        Args:
            content: Raw Turtle file content
            prefixes: Prefix to namespace mappings

        Returns:
            Dict mapping property names to lists of values
        """
        triples = {}

        # Pattern for property-value pairs
        # Matches: prefix:property "value" or prefix:property <uri>
        property_pattern = r'(\w+):(\w+)\s+(?:"([^"]+)"|<([^>]+)>|(\w+:\w+))'

        for match in re.finditer(property_pattern, content):
            prefix = match.group(1)
            prop_name = match.group(2)
            value = match.group(3) or match.group(4) or match.group(5)

            if value:
                key = f"{prefix}:{prop_name}"
                if key not in triples:
                    triples[key] = []
                triples[key].append(value)

        return triples

    def _transform_to_metadata(self, triples: Dict[str, List[str]]) -> Metadata:
        """
        Transform parsed RDF triples to Metadata domain entity.

        Property mappings:
        - dct:title, dc:title -> title
        - dct:description, dc:description -> abstract
        - dcat:keyword, dc:subject -> keywords
        - dct:spatial -> bounding_box
        - dct:temporal -> temporal_extent
        - dct:publisher, dc:publisher -> contact_organization

        Args:
            triples: Dictionary of property-value pairs

        Returns:
            Metadata: Validated metadata entity
        """
        # Extract title
        title = self._get_first_value(triples, [
            'dct:title', 'dc:title', 'dcterms:title', 'schema:name'
        ], '[Missing title]')

        # Extract abstract/description
        abstract = self._get_first_value(triples, [
            'dct:description', 'dc:description', 'dcterms:description', 'schema:description'
        ], '[Missing description]')

        # Extract keywords
        keywords = self._get_all_values(triples, [
            'dcat:keyword', 'dc:subject', 'dct:subject', 'schema:keywords'
        ])

        # Extract contact information
        contact_org = self._get_first_value(triples, [
            'dct:publisher', 'dc:publisher', 'dct:creator', 'dc:creator', 'foaf:name'
        ], '')

        # Extract temporal coverage
        temporal_str = self._get_first_value(triples, [
            'dct:temporal', 'dc:date', 'dct:date', 'schema:temporalCoverage'
        ], None)
        temporal_start, temporal_end = self._parse_temporal(temporal_str)

        # Extract metadata date
        date_str = self._get_first_value(triples, [
            'dct:modified', 'dct:created', 'dc:date', 'schema:dateModified'
        ], None)
        metadata_date = self._parse_datetime(date_str)
        if metadata_date is None:
            metadata_date = datetime.utcnow()

        # Extract language
        language = self._get_first_value(triples, [
            'dct:language', 'dc:language'
        ], 'eng')

        # Extract topic category
        topic = self._get_first_value(triples, [
            'dcat:theme', 'dc:type', 'dct:type'
        ], '')

        return Metadata(
            title=title,
            abstract=abstract,
            keywords=keywords,
            bounding_box=None,  # Complex to parse from RDF
            temporal_extent_start=temporal_start,
            temporal_extent_end=temporal_end,
            contact_organization=contact_org,
            contact_email='',
            metadata_date=metadata_date,
            dataset_language=language,
            topic_category=topic,
            download_url=self._get_first_value(triples, ['dcat:downloadURL', 'dcat:accessURL'], ''),
            landing_page_url=self._get_first_value(triples, ['dcat:landingPage', 'foaf:homepage'], '')
        )

    def _get_first_value(
        self, 
        triples: Dict[str, List[str]], 
        property_names: List[str],
        default: Optional[str] = None
    ) -> Optional[str]:
        """Get the first matching value from a list of property names."""
        for prop in property_names:
            if prop in triples and triples[prop]:
                return triples[prop][0]
        return default

    def _get_all_values(
        self, 
        triples: Dict[str, List[str]], 
        property_names: List[str]
    ) -> List[str]:
        """Get all values from a list of property names."""
        values = []
        for prop in property_names:
            if prop in triples:
                values.extend(triples[prop])
        return list(set(values))  # Remove duplicates

    def _parse_temporal(self, temporal_str: Optional[str]) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Parse temporal coverage string."""
        if temporal_str is None:
            return None, None

        try:
            # Handle ISO 8601 interval: "2020-01-01/2020-12-31"
            if '/' in temporal_str:
                parts = temporal_str.split('/')
                return self._parse_datetime(parts[0]), self._parse_datetime(parts[1])
            else:
                dt = self._parse_datetime(temporal_str)
                return dt, dt
        except Exception:
            return None, None

    def _parse_datetime(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO 8601 date string."""
        if date_str is None or not isinstance(date_str, str):
            return None

        try:
            # Clean string
            date_str = date_str.strip().strip('"').strip("'")
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
        return f"RDFExtractor(mode={mode})"
