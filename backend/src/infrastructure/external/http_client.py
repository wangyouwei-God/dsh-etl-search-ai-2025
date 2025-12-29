"""
Infrastructure: HTTP Client

This module provides a robust HTTP client for downloading remote metadata files
with retry logic to handle flaky remote catalogues and network issues.

Design Pattern: Facade Pattern (simplifies complex HTTP operations)

Author: University of Manchester RSE Team
"""

import os
import logging
from typing import Optional, Dict
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter, Retry
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)


# Configure logging
logger = logging.getLogger(__name__)


class HTTPClientError(Exception):
    """Base exception for HTTP client errors."""
    pass


class DownloadError(HTTPClientError):
    """Raised when file download fails."""

    def __init__(self, url: str, reason: str):
        self.url = url
        self.reason = reason
        super().__init__(f"Failed to download {url}: {reason}")


class HTTPClient:
    """
    Robust HTTP client for downloading files with retry logic.

    This client is designed to handle flaky remote metadata catalogues by:
    - Automatic retries with exponential backoff
    - Connection pooling for efficiency
    - Proper timeout handling
    - User-agent configuration

    Attributes:
        timeout: Request timeout in seconds (default: 30)
        max_retries: Maximum number of retry attempts (default: 3)
        session: Configured requests session with retry logic

    Example:
        >>> client = HTTPClient(timeout=60, max_retries=5)
        >>> local_path = client.download_file(
        ...     "https://catalogue.example.com/metadata.xml",
        ...     "/tmp/metadata.xml"
        ... )
        >>> print(local_path)
        '/tmp/metadata.xml'
    """

    def __init__(
        self,
        timeout: int = 30,
        max_retries: int = 3,
        user_agent: Optional[str] = None
    ):
        """
        Initialize the HTTP client with retry configuration.

        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts for failed requests
            user_agent: Custom User-Agent header (optional)
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.user_agent = user_agent or (
            "UoM-Dataset-Discovery/1.0 "
            "(University of Manchester Research Software Engineering)"
        )

        # Create session with retry logic
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """
        Create a requests session with retry configuration.

        Implements retry logic for:
        - Connection errors
        - Timeout errors
        - HTTP 5xx server errors
        - HTTP 429 (Too Many Requests)

        Returns:
            Configured requests.Session with retry adapter
        """
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,  # Wait 1, 2, 4, 8, ... seconds between retries
            status_forcelist=[429, 500, 502, 503, 504],  # Retry on these HTTP codes
            allowed_methods=["HEAD", "GET", "OPTIONS"],  # Only retry safe methods
            raise_on_status=False  # Don't raise exception, let us handle it
        )

        # Mount adapter with retry strategy for both HTTP and HTTPS
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set default headers
        session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'application/xml, application/json, text/xml, */*',
        })

        return session

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    def download_file(
        self,
        url: str,
        destination: str,
        chunk_size: int = 8192,
        headers: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Download a file from a URL to a local destination with retry logic.

        This method uses tenacity for advanced retry logic on top of the
        requests session retry adapter. It handles:
        - Network failures with exponential backoff
        - Streaming download for large files
        - Automatic directory creation
        - File integrity verification

        Args:
            url: URL of the file to download
            destination: Local file path where the file should be saved
            chunk_size: Size of chunks for streaming download (bytes)
            headers: Optional additional HTTP headers

        Returns:
            str: Absolute path to the downloaded file

        Raises:
            DownloadError: If download fails after all retries
            ValueError: If URL or destination is invalid

        Example:
            >>> client = HTTPClient()
            >>> path = client.download_file(
            ...     "https://catalogue.ceda.ac.uk/uuid/abc123",
            ...     "/tmp/metadata.xml"
            ... )
        """
        # Validate inputs
        if not url or not url.strip():
            raise ValueError("URL cannot be empty")

        if not destination or not destination.strip():
            raise ValueError("Destination path cannot be empty")

        # Ensure destination directory exists
        dest_path = Path(destination)
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Downloading file from {url} to {destination}")

        try:
            # Merge custom headers with session headers
            request_headers = headers or {}

            # Make request with streaming to handle large files
            response = self.session.get(
                url,
                headers=request_headers,
                timeout=self.timeout,
                stream=True,
                allow_redirects=True
            )

            # Check if request was successful
            response.raise_for_status()

            # Get content type for validation
            content_type = response.headers.get('Content-Type', '')
            logger.debug(f"Content-Type: {content_type}")

            # Stream download to file
            total_size = 0
            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:  # Filter out keep-alive chunks
                        f.write(chunk)
                        total_size += len(chunk)

            logger.info(
                f"Successfully downloaded {total_size} bytes from {url} "
                f"to {dest_path.absolute()}"
            )

            # Verify file was created and has content
            if not dest_path.exists():
                raise DownloadError(url, "File was not created on disk")

            if dest_path.stat().st_size == 0:
                raise DownloadError(url, "Downloaded file is empty")

            return str(dest_path.absolute())

        except requests.HTTPError as e:
            # HTTP error (4xx, 5xx)
            status_code = e.response.status_code if e.response else "unknown"
            raise DownloadError(
                url,
                f"HTTP {status_code} error: {str(e)}"
            )

        except requests.ConnectionError as e:
            # Network connection error
            raise DownloadError(url, f"Connection error: {str(e)}")

        except requests.Timeout as e:
            # Timeout error
            raise DownloadError(url, f"Request timeout after {self.timeout}s: {str(e)}")

        except requests.RequestException as e:
            # Other requests errors
            raise DownloadError(url, f"Request failed: {str(e)}")

        except OSError as e:
            # File system errors
            raise DownloadError(url, f"File system error: {str(e)}")

        except Exception as e:
            # Unexpected errors
            raise DownloadError(url, f"Unexpected error: {str(e)}")

    def get_metadata(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """
        Get HTTP headers for a resource without downloading the body.

        Useful for checking content type, size, and last modified date
        before downloading.

        Args:
            url: URL to check
            headers: Optional additional HTTP headers

        Returns:
            Dictionary of response headers

        Raises:
            DownloadError: If HEAD request fails
        """
        try:
            response = self.session.head(
                url,
                headers=headers or {},
                timeout=self.timeout,
                allow_redirects=True
            )
            response.raise_for_status()
            return dict(response.headers)

        except requests.RequestException as e:
            raise DownloadError(url, f"Failed to get metadata: {str(e)}")

    def close(self):
        """Close the HTTP session and release resources."""
        if self.session:
            self.session.close()
            logger.debug("HTTP session closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close session."""
        self.close()

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"HTTPClient(timeout={self.timeout}, "
            f"max_retries={self.max_retries})"
        )


# Convenience function for simple downloads
def download_file(url: str, destination: str, **kwargs) -> str:
    """
    Convenience function to download a file without managing a client instance.

    Args:
        url: URL to download from
        destination: Local path to save to
        **kwargs: Additional arguments passed to HTTPClient constructor

    Returns:
        str: Path to downloaded file

    Example:
        >>> from infrastructure.external.http_client import download_file
        >>> download_file(
        ...     "https://example.com/metadata.xml",
        ...     "/tmp/metadata.xml"
        ... )
    """
    with HTTPClient(**kwargs) as client:
        return client.download_file(url, destination)
