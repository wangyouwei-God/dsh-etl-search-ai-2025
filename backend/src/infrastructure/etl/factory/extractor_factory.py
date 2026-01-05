"""
Infrastructure: Extractor Factory

This module implements the Factory Pattern for creating metadata extractors
based on file format detection.

Design Pattern: Factory Pattern

Author: University of Manchester RSE Team
"""

import os
from typing import Optional
import sys

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../../')))

from application.interfaces.metadata_extractor import (
    IMetadataExtractor,
    UnsupportedFormatError
)
from infrastructure.etl.extractors.json_extractor import JSONExtractor
from infrastructure.etl.extractors.xml_extractor import XMLExtractor
from infrastructure.etl.extractors.jsonld_extractor import JSONLDExtractor
from infrastructure.etl.extractors.rdf_extractor import RDFExtractor


class ExtractorFactory:
    """
    Factory for creating appropriate metadata extractors based on file format.

    This factory implements the Factory Pattern to encapsulate the logic of
    selecting and instantiating the correct extractor for a given file format.

    Design Pattern: Factory Pattern
    - Centralizes object creation logic
    - Allows adding new extractors without modifying client code
    - Supports both explicit format specification and auto-detection

    Supported Formats:
        - JSON (.json)
        - XML (.xml)

    Example:
        >>> factory = ExtractorFactory()
        >>> extractor = factory.create_extractor("metadata.json")
        >>> metadata = extractor.extract("metadata.json")

        >>> # Or specify format explicitly
        >>> extractor = factory.create_extractor_by_format("json")
        >>> metadata = extractor.extract("path/to/file")
    """

    def __init__(self, strict_mode: bool = False):
        """
        Initialize the factory.

        Args:
            strict_mode: If True, extractors will enforce all fields.
                        If False, extractors use defaults for missing fields.
        """
        self.strict_mode = strict_mode

        # Registry of available extractors
        self._extractors = {
            'json': JSONExtractor,
            'xml': XMLExtractor,
            'jsonld': JSONLDExtractor,
            'rdf': RDFExtractor
        }

        # File extension to format mapping
        self._extension_map = {
            '.json': 'json',
            '.xml': 'xml',
            '.jsonld': 'jsonld',
            '.ttl': 'rdf',
            '.turtle': 'rdf'
        }

    def create_extractor(self, file_path: str) -> IMetadataExtractor:
        """
        Create an appropriate extractor based on file extension.

        Args:
            file_path: Path to the file to be extracted

        Returns:
            IMetadataExtractor: Appropriate extractor instance

        Raises:
            UnsupportedFormatError: If file format is not supported

        Example:
            >>> factory = ExtractorFactory()
            >>> extractor = factory.create_extractor("metadata.json")
            >>> print(type(extractor).__name__)
            'JSONExtractor'
        """
        # Get file extension
        _, ext = os.path.splitext(file_path.lower())

        # Look up format
        format_type = self._extension_map.get(ext)

        if not format_type:
            supported_formats = list(self._extension_map.keys())
            raise UnsupportedFormatError(
                file_path,
                supported_formats
            )

        # Create and return extractor
        return self.create_extractor_by_format(format_type)

    def create_extractor_by_format(self, format_type: str) -> IMetadataExtractor:
        """
        Create an extractor for a specific format.

        Args:
            format_type: Format identifier ('json', 'xml', etc.)

        Returns:
            IMetadataExtractor: Extractor instance for the specified format

        Raises:
            UnsupportedFormatError: If format is not supported

        Example:
            >>> factory = ExtractorFactory()
            >>> json_extractor = factory.create_extractor_by_format('json')
            >>> xml_extractor = factory.create_extractor_by_format('xml')
        """
        format_type = format_type.lower()

        extractor_class = self._extractors.get(format_type)

        if not extractor_class:
            supported_formats = list(self._extractors.keys())
            raise UnsupportedFormatError(
                f"format:{format_type}",
                supported_formats
            )

        # Instantiate and return extractor
        return extractor_class(strict_mode=self.strict_mode)

    def get_extractor_for_file(self, file_path: str) -> Optional[IMetadataExtractor]:
        """
        Get an extractor that can handle the given file.

        This method tries all available extractors until one accepts the file.

        Args:
            file_path: Path to the file

        Returns:
            IMetadataExtractor or None if no extractor can handle the file

        Example:
            >>> factory = ExtractorFactory()
            >>> extractor = factory.get_extractor_for_file("unknown.dat")
            >>> if extractor:
            ...     metadata = extractor.extract("unknown.dat")
        """
        # Try each extractor to see if it can handle the file
        for format_type, extractor_class in self._extractors.items():
            extractor = extractor_class(strict_mode=self.strict_mode)
            if extractor.can_extract(file_path):
                return extractor

        return None

    def register_extractor(
        self,
        format_type: str,
        extractor_class: type,
        extensions: Optional[list] = None
    ):
        """
        Register a new extractor type.

        This allows extending the factory with new extractors at runtime.

        Args:
            format_type: Format identifier (e.g., 'csv', 'rdf')
            extractor_class: Extractor class (must implement IMetadataExtractor)
            extensions: List of file extensions (e.g., ['.csv', '.tsv'])

        Example:
            >>> factory = ExtractorFactory()
            >>> factory.register_extractor('csv', CSVExtractor, ['.csv', '.tsv'])
        """
        self._extractors[format_type.lower()] = extractor_class

        if extensions:
            for ext in extensions:
                if not ext.startswith('.'):
                    ext = '.' + ext
                self._extension_map[ext.lower()] = format_type.lower()

    def get_supported_formats(self) -> list:
        """
        Get list of supported format types.

        Returns:
            List of supported format identifiers

        Example:
            >>> factory = ExtractorFactory()
            >>> factory.get_supported_formats()
            ['json', 'xml']
        """
        return list(self._extractors.keys())

    def get_supported_extensions(self) -> list:
        """
        Get list of supported file extensions.

        Returns:
            List of supported file extensions

        Example:
            >>> factory = ExtractorFactory()
            >>> factory.get_supported_extensions()
            ['.json', '.xml']
        """
        return list(self._extension_map.keys())

    def __repr__(self) -> str:
        """Return string representation."""
        formats = ', '.join(self.get_supported_formats())
        return f"ExtractorFactory(formats=[{formats}], strict_mode={self.strict_mode})"


# Convenience function for quick extractor creation
def get_extractor(file_path: str, strict_mode: bool = False) -> IMetadataExtractor:
    """
    Convenience function to get an extractor for a file.

    Args:
        file_path: Path to the file
        strict_mode: Whether to enforce strict validation

    Returns:
        IMetadataExtractor: Appropriate extractor

    Raises:
        UnsupportedFormatError: If format is not supported

    Example:
        >>> from infrastructure.etl.factory.extractor_factory import get_extractor
        >>> extractor = get_extractor("metadata.json")
        >>> metadata = extractor.extract("metadata.json")
    """
    factory = ExtractorFactory(strict_mode=strict_mode)
    return factory.create_extractor(file_path)
