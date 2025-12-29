"""
Application Interface: IMetadataExtractor

This module defines the interface for metadata extraction strategies.
This is part of the Application layer and provides the abstraction that
Infrastructure layer implementations must follow.

This interface enables the Strategy Pattern for handling different metadata formats.

Author: University of Manchester RSE Team
"""

from abc import ABC, abstractmethod
from typing import Optional
import sys
import os

# Add the parent directory to the path to allow imports from domain layer
# This is a workaround for the current project structure
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from domain.entities.metadata import Metadata


class IMetadataExtractor(ABC):
    """
    Interface for metadata extraction strategies.

    This interface defines the contract that all metadata extractors must follow,
    regardless of the source format (JSON, XML, etc.). This abstraction allows
    the application layer to work with different extraction strategies without
    knowing the implementation details.

    Design Pattern: Strategy Pattern
    - Each concrete extractor implements this interface with format-specific logic
    - The client (use cases) can switch between extractors without code changes
    - New formats can be added by creating new implementations

    SOLID Principles Applied:
    - Single Responsibility: Each extractor handles one format only
    - Open/Closed: Open for extension (new formats), closed for modification
    - Liskov Substitution: All extractors can be used interchangeably
    - Dependency Inversion: High-level code depends on this abstraction
    """

    @abstractmethod
    def extract(self, source_path: str) -> Metadata:
        """
        Extract metadata from a source file.

        This method reads a metadata file from the given path and converts it
        into a standardized Metadata domain entity. The implementation details
        (parsing, validation, transformation) are format-specific and handled
        by concrete classes.

        Args:
            source_path: Path to the metadata file to extract.
                        Can be a local file path or potentially a URL.

        Returns:
            Metadata: A validated Metadata domain entity containing the extracted
                     information conforming to ISO 19115 structure.

        Raises:
            FileNotFoundError: If the source file does not exist
            ValueError: If the metadata format is invalid or cannot be parsed
            MetadataValidationError: If extracted data fails ISO 19115 validation

        Example:
            >>> extractor = JSONExtractor()
            >>> metadata = extractor.extract('/path/to/metadata.json')
            >>> print(metadata.title)
            'Climate Dataset 2023'

        Note:
            Implementations should delegate validation to domain services
            (e.g., ISO19115Validator) to maintain separation of concerns.
        """
        pass

    @abstractmethod
    def can_extract(self, source_path: str) -> bool:
        """
        Check if this extractor can handle the given source file.

        This method allows the extractor to determine if it's the appropriate
        handler for a given file, typically by checking the file extension,
        MIME type, or file content.

        Args:
            source_path: Path to the metadata file to check

        Returns:
            bool: True if this extractor can handle the file, False otherwise

        Example:
            >>> json_extractor = JSONExtractor()
            >>> json_extractor.can_extract('metadata.json')
            True
            >>> json_extractor.can_extract('metadata.xml')
            False
        """
        pass

    def get_supported_format(self) -> str:
        """
        Get a human-readable name of the format this extractor supports.

        Returns:
            str: Format name (e.g., 'JSON', 'XML', 'CSV')

        Note:
            This is a concrete method with a default implementation.
            Subclasses can override if needed.
        """
        return self.__class__.__name__.replace('Extractor', '')


class ExtractorError(Exception):
    """Base exception for extractor-related errors."""
    pass


class UnsupportedFormatError(ExtractorError):
    """Raised when a file format is not supported by any extractor."""

    def __init__(self, file_path: str, supported_formats: Optional[list] = None):
        self.file_path = file_path
        self.supported_formats = supported_formats or []

        if supported_formats:
            message = (
                f"Unsupported format for file: {file_path}. "
                f"Supported formats: {', '.join(supported_formats)}"
            )
        else:
            message = f"Unsupported format for file: {file_path}"

        super().__init__(message)


class MetadataExtractionError(ExtractorError):
    """Raised when metadata extraction fails."""

    def __init__(self, file_path: str, reason: str):
        self.file_path = file_path
        self.reason = reason
        message = f"Failed to extract metadata from {file_path}: {reason}"
        super().__init__(message)
