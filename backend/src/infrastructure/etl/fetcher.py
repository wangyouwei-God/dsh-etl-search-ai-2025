"""
Infrastructure: Metadata Fetcher

This module provides a service for fetching metadata from remote catalogues
with intelligent format detection and fallback strategies.

Design Pattern: Service Pattern

Author: University of Manchester RSE Team
"""

import os
import tempfile
import logging
from pathlib import Path
from typing import Optional, Tuple, List
import sys

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))

from infrastructure.external.http_client import HTTPClient, DownloadError

# Configure logging
logger = logging.getLogger(__name__)


class FetchError(Exception):
    """Raised when metadata fetching fails."""

    def __init__(self, uuid: str, reason: str):
        self.uuid = uuid
        self.reason = reason
        super().__init__(f"Failed to fetch metadata for UUID {uuid}: {reason}")


class MetadataFetcher:
    """
    Service for fetching metadata from remote catalogues.

    This service handles the complexity of:
    - Trying multiple URL patterns for different formats
    - Detecting available formats (JSON, XML)
    - Downloading files to temporary storage
    - Cleaning up temporary files

    Supported Catalogues:
        - CEH (Centre for Ecology & Hydrology) - catalogue.ceh.ac.uk

    Design Pattern: Service Pattern
    - Encapsulates complex fetching logic
    - Provides simple interface for clients
    - Handles errors and retries internally

    Example:
        >>> fetcher = MetadataFetcher(catalogue='ceh')
        >>> file_path, format_type = fetcher.fetch('abc123')
        >>> print(f"Downloaded {format_type} to {file_path}")
    """

    # Catalogue URL patterns
    CATALOGUE_PATTERNS = {
        'ceh': {
            'base_url': 'https://catalogue.ceh.ac.uk/id/{uuid}',
            # Direct JSON/XML endpoints are deprecated/redirected on CEH
            # We rely on Content Negotiation on the base_url
            'gemini_xml_url': 'https://catalogue.ceh.ac.uk/documents/gemini/waf/{uuid}.xml',
        },
        # Can add more catalogues here
        'ceda': {
            'base_url': 'https://catalogue.ceda.ac.uk/uuid/{uuid}',
            'json_url': 'https://catalogue.ceda.ac.uk/uuid/{uuid}?format=json',
            'xml_url': 'https://catalogue.ceda.ac.uk/uuid/{uuid}?format=xml',
        }
    }

    def __init__(
        self,
        catalogue: str = 'ceh',
        timeout: int = 60,
        max_retries: int = 3,
        temp_dir: Optional[str] = None
    ):
        """
        Initialize the metadata fetcher.

        Args:
            catalogue: Catalogue identifier ('ceh', 'ceda', etc.)
            timeout: HTTP request timeout in seconds
            max_retries: Maximum number of retry attempts
            temp_dir: Directory for temporary files (default: system temp)

        Raises:
            ValueError: If catalogue is not supported
        """
        if catalogue not in self.CATALOGUE_PATTERNS:
            supported = ', '.join(self.CATALOGUE_PATTERNS.keys())
            raise ValueError(
                f"Unsupported catalogue: {catalogue}. "
                f"Supported catalogues: {supported}"
            )

        self.catalogue = catalogue
        self.timeout = timeout
        self.max_retries = max_retries
        self.temp_dir = temp_dir or tempfile.gettempdir()

        # Create HTTP client
        self.client = HTTPClient(
            timeout=timeout,
            max_retries=max_retries
        )

        logger.info(
            f"Initialized MetadataFetcher for catalogue '{catalogue}' "
            f"(timeout={timeout}s, retries={max_retries})"
        )

    def fetch(
        self,
        uuid: str,
        preferred_format: Optional[str] = None,
        cleanup: bool = False
    ) -> Tuple[str, str]:
        """
        Fetch metadata for a given UUID.

        This method tries multiple strategies to fetch metadata:
        1. If preferred_format specified, try that first
        2. Try JSON format (fast to parse)
        3. Try XML format (fallback)
        4. Try additional catalogue-specific URLs

        Args:
            uuid: Dataset UUID or identifier
            preferred_format: Preferred format ('json' or 'xml'), optional
            cleanup: If True, caller must manually delete the file

        Returns:
            Tuple of (file_path, format_type)
                file_path: Path to downloaded file
                format_type: 'json' or 'xml'

        Raises:
            FetchError: If all fetch attempts fail

        Example:
            >>> fetcher = MetadataFetcher()
            >>> path, fmt = fetcher.fetch('1d33a8a1-4c7e-4d6f-b8c1-c158c1f5a8e2')
            >>> print(f"Downloaded {fmt} to {path}")
        """
        logger.info(f"Fetching metadata for UUID: {uuid}")

        # Build list of URLs to try
        urls_to_try = self._build_url_list(uuid, preferred_format)

        # Try each URL
        last_error = None
        for url, format_type in urls_to_try:
            try:
                logger.debug(f"Trying {format_type} URL: {url}")

                # Create temporary file
                temp_file = self._create_temp_file(uuid, format_type)

                # Prepare headers for Content Negotiation
                headers = {}
                if 'catalogue.ceh.ac.uk/id/' in url:
                    if format_type == 'json':
                        headers['Accept'] = 'application/json'
                    elif format_type == 'xml':
                        headers['Accept'] = 'application/xml'

                # Download file
                downloaded_path = self.client.download_file(url, temp_file, headers=headers)

                # Verify file has content
                if not self._verify_file(downloaded_path):
                    logger.warning(f"Downloaded file is empty or invalid: {url}")
                    continue

                logger.info(
                    f"Successfully fetched {format_type} metadata from {url}"
                )
                return downloaded_path, format_type

            except DownloadError as e:
                logger.warning(f"Failed to download from {url}: {e.reason}")
                last_error = e
                continue

            except Exception as e:
                logger.warning(f"Unexpected error downloading from {url}: {str(e)}")
                last_error = e
                continue

        # If we get here, all attempts failed
        error_msg = str(last_error) if last_error else "All download attempts failed"
        raise FetchError(uuid, error_msg)

    def fetch_json(self, uuid: str) -> str:
        """
        Fetch JSON format metadata.

        Args:
            uuid: Dataset UUID

        Returns:
            Path to downloaded JSON file

        Raises:
            FetchError: If JSON fetch fails
        """
        file_path, format_type = self.fetch(uuid, preferred_format='json')
        if format_type != 'json':
            raise FetchError(uuid, "JSON format not available")
        return file_path

    def fetch_xml(self, uuid: str) -> str:
        """
        Fetch XML format metadata.

        Args:
            uuid: Dataset UUID

        Returns:
            Path to downloaded XML file

        Raises:
            FetchError: If XML fetch fails
        """
        file_path, format_type = self.fetch(uuid, preferred_format='xml')
        if format_type != 'xml':
            raise FetchError(uuid, "XML format not available")
        return file_path

    def _build_url_list(
        self,
        uuid: str,
        preferred_format: Optional[str] = None
    ) -> List[Tuple[str, str]]:
        """
        Build list of URLs to try in order.

        Args:
            uuid: Dataset UUID
            preferred_format: Preferred format to try first

        Returns:
            List of (url, format_type) tuples
        """
        patterns = self.CATALOGUE_PATTERNS[self.catalogue]
        urls = []

        # Strategy 1: Content Negotiation via Base URL (Modern Way)
        if 'base_url' in patterns:
            base_url = patterns['base_url'].format(uuid=uuid)
            
            # If preferred format specified, try that first
            if preferred_format == 'json':
                urls.append((base_url, 'json'))
            elif preferred_format == 'xml':
                urls.append((base_url, 'xml'))
            else:
                # Default order: JSON first (lighter), then XML
                urls.append((base_url, 'json'))
                urls.append((base_url, 'xml'))

        # Strategy 2: WAF (Web Accessible Folder) - specific to CEH Gemini XML
        if 'gemini_xml_url' in patterns:
            # WAF usually holds the definitive XML record
            urls.append((patterns['gemini_xml_url'].format(uuid=uuid), 'xml'))

        # Legacy fallback (only if patterns explicitly define them)
        if 'json_url' in patterns and preferred_format != 'xml':
             urls.append((patterns['json_url'].format(uuid=uuid), 'json'))
        if 'xml_url' in patterns and preferred_format != 'json':
             urls.append((patterns['xml_url'].format(uuid=uuid), 'xml'))

        return urls

    def _create_temp_file(self, uuid: str, format_type: str) -> str:
        """
        Create a temporary file for download.

        Args:
            uuid: Dataset UUID
            format_type: File format ('json' or 'xml')

        Returns:
            Path to temporary file
        """
        # Create temp directory if it doesn't exist
        temp_path = Path(self.temp_dir)
        temp_path.mkdir(parents=True, exist_ok=True)

        # Create filename
        extension = f'.{format_type}'
        safe_uuid = uuid.replace('/', '_').replace('\\', '_')
        filename = f"metadata_{safe_uuid}{extension}"

        return str(temp_path / filename)

    def _verify_file(self, file_path: str) -> bool:
        """
        Verify that downloaded file is valid.

        Args:
            file_path: Path to file

        Returns:
            True if file is valid, False otherwise
        """
        try:
            path = Path(file_path)

            # Check file exists
            if not path.exists():
                return False

            # Check file has content
            if path.stat().st_size == 0:
                return False

            # Basic content check (should start with { or <)
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                first_char = f.read(1)
                if not first_char:
                    return False

                # JSON should start with { or [
                # XML should start with <
                if first_char not in ['{', '[', '<']:
                    logger.warning(
                        f"File doesn't look like JSON or XML: starts with '{first_char}'"
                    )
                    # Don't reject - could be whitespace before actual content
                    pass

            return True

        except Exception as e:
            logger.warning(f"Error verifying file {file_path}: {str(e)}")
            return False

    def close(self):
        """Close the HTTP client and release resources."""
        if self.client:
            self.client.close()
            logger.debug("MetadataFetcher closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close client."""
        self.close()

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"MetadataFetcher(catalogue='{self.catalogue}', "
            f"timeout={self.timeout}, retries={self.max_retries})"
        )


# Convenience function
def fetch_metadata(
    uuid: str,
    catalogue: str = 'ceh',
    **kwargs
) -> Tuple[str, str]:
    """
    Convenience function to fetch metadata.

    Args:
        uuid: Dataset UUID
        catalogue: Catalogue identifier
        **kwargs: Additional arguments for MetadataFetcher

    Returns:
        Tuple of (file_path, format_type)

    Example:
        >>> from infrastructure.etl.fetcher import fetch_metadata
        >>> path, fmt = fetch_metadata('abc123', catalogue='ceh')
    """
    with MetadataFetcher(catalogue=catalogue, **kwargs) as fetcher:
        return fetcher.fetch(uuid)
