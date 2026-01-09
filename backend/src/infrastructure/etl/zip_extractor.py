"""
Infrastructure: ZIP File Extractor

This module provides functionality for downloading and extracting ZIP files
from dataset archives. Implements the capability to handle ZIP datasets
as specified in the RSE Coding Task requirements.

Author: University of Manchester RSE Team
"""

import io
import logging
import os
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple
from uuid import uuid4

import requests

logger = logging.getLogger(__name__)


class ZipExtractionError(Exception):
    """Raised when ZIP extraction fails."""
    pass


class ZipDownloadError(Exception):
    """Raised when ZIP download fails."""
    pass


@dataclass
class ExtractedFile:
    """Information about an extracted file."""
    filename: str
    file_path: str
    file_size: int
    file_format: str
    extracted_at: datetime


@dataclass
class ZipArchiveInfo:
    """Information about a ZIP archive."""
    source_url: str
    total_files: int
    total_size: int
    extracted_files: List[ExtractedFile]
    extraction_path: str
    downloaded_at: datetime


class ZipExtractor:
    """
    ZIP file extractor for dataset archives.
    
    This class provides the capability to:
    - Download ZIP files from remote URLs
    - Extract contents to local storage
    - Generate file manifests
    - Track extraction metadata
    
    Design Pattern: Strategy Pattern
    - Can be extended with different extraction strategies
    """
    
    # Supported archive formats
    SUPPORTED_EXTENSIONS = {'.zip'}
    
    # Default extraction directory
    DEFAULT_EXTRACT_DIR = "extracted_archives"
    
    def __init__(
        self,
        extract_dir: str = None,
        timeout: int = 300,
        max_size_mb: int = 500,
        overwrite: bool = False,
        max_nested_depth: int = 3
    ):
        """
        Initialize ZIP extractor.

        Args:
            extract_dir: Directory for extracted files
            timeout: Download timeout in seconds
            max_size_mb: Maximum archive size to download (MB)
            overwrite: Whether to overwrite existing extractions
            max_nested_depth: Maximum depth for recursive nested ZIP extraction
        """
        self.extract_dir = Path(extract_dir or self.DEFAULT_EXTRACT_DIR)
        self.timeout = timeout
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.overwrite = overwrite
        self.max_nested_depth = max_nested_depth

        # Create extraction directory
        self.extract_dir.mkdir(parents=True, exist_ok=True)

        # Session for HTTP requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'DatasetSearchBot/1.0 (University of Manchester RSE)'
        })

        logger.info(f"ZipExtractor initialized: dir={self.extract_dir}, max_size={max_size_mb}MB, max_nested_depth={max_nested_depth}")
    
    def _get_extraction_path(self, dataset_id: str) -> Path:
        """Get the extraction path for a dataset."""
        return self.extract_dir / dataset_id
    
    def _check_file_exists(self, dataset_id: str) -> bool:
        """Check if dataset has already been extracted."""
        path = self._get_extraction_path(dataset_id)
        return path.exists() and any(path.iterdir())
    
    def download_zip(self, url: str, dataset_id: str = None) -> Tuple[bytes, int]:
        """
        Download a ZIP file from URL.
        
        Args:
            url: URL of the ZIP file
            dataset_id: Optional dataset ID for logging
            
        Returns:
            Tuple of (file_content, file_size)
            
        Raises:
            ZipDownloadError: If download fails
        """
        try:
            logger.info(f"Downloading ZIP: {url}")
            
            # First, check file size with HEAD request (allow redirects to check final destination)
            head_response = self.session.head(url, timeout=30, allow_redirects=True)
            
            # Check if redirected to login/SSO page (authentication required)
            final_url = head_response.url
            if any(auth_indicator in final_url.lower() for auth_indicator in ['/sso/', '/login', '/signin', '/auth']):
                raise ZipDownloadError(
                    f"Authentication required: The data provider requires login to access this resource. "
                    f"Please download manually from: {url}"
                )
            
            content_length = int(head_response.headers.get('content-length', 0))
            
            if content_length > self.max_size_bytes:
                raise ZipDownloadError(
                    f"File too large: {content_length / 1024 / 1024:.1f}MB "
                    f"(max: {self.max_size_bytes / 1024 / 1024:.1f}MB)"
                )
            
            # Download the file (allow redirects)
            response = self.session.get(url, timeout=self.timeout, stream=True, allow_redirects=True)
            response.raise_for_status()
            
            # Check Content-Type to ensure it's actually a ZIP file
            content_type = response.headers.get('content-type', '').lower()
            valid_zip_types = ['application/zip', 'application/x-zip-compressed', 'application/octet-stream']
            
            # If we got HTML, it's likely a login page or error page
            if 'text/html' in content_type:
                # Check response content for login indicators
                content_preview = response.content[:1000].decode('utf-8', errors='ignore').lower()
                if any(indicator in content_preview for indicator in ['login', 'sign in', 'sso', 'authenticate']):
                    raise ZipDownloadError(
                        f"Authentication required: The data provider requires login to access this resource. "
                        f"Please download manually from: {url}"
                    )
                else:
                    raise ZipDownloadError(
                        f"Invalid response: Expected ZIP file but received HTML. "
                        f"The server may require authentication or the resource may not exist."
                    )
            
            content = response.content
            actual_size = len(content)
            
            # Verify it's actually a ZIP file by checking magic bytes
            if len(content) < 4 or content[:4] not in [b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08']:
                raise ZipDownloadError(
                    f"Invalid file format: The downloaded content is not a valid ZIP file. "
                    f"Content-Type: {content_type}, Size: {actual_size} bytes"
                )
            
            logger.info(f"Downloaded: {actual_size / 1024 / 1024:.2f}MB")
            return content, actual_size
            
        except requests.exceptions.Timeout:
            raise ZipDownloadError(f"Download timed out after {self.timeout}s")
        except requests.exceptions.RequestException as e:
            raise ZipDownloadError(f"Download failed: {str(e)}")
    
    def extract_from_bytes(
        self,
        content: bytes,
        dataset_id: str,
        file_filter: Optional[callable] = None,
        current_depth: int = 0
    ) -> List[ExtractedFile]:
        """
        Extract ZIP content from bytes with recursive nested ZIP support.

        Args:
            content: ZIP file content as bytes
            dataset_id: Dataset ID for directory naming
            file_filter: Optional function to filter files (returns True to include)
            current_depth: Current recursion depth (internal use)

        Returns:
            List of ExtractedFile objects

        Raises:
            ZipExtractionError: If extraction fails
        """
        extraction_path = self._get_extraction_path(dataset_id)

        # Check if already extracted
        if not self.overwrite and self._check_file_exists(dataset_id):
            logger.info(f"Already extracted, skipping: {dataset_id}")
            return self._get_existing_files(extraction_path)

        # Create extraction directory
        extraction_path.mkdir(parents=True, exist_ok=True)

        try:
            extracted_files = []

            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                for info in zf.infolist():
                    # Skip directories
                    if info.is_dir():
                        continue

                    # Apply file filter if provided
                    if file_filter and not file_filter(info.filename):
                        continue

                    # Extract file
                    output_path = extraction_path / info.filename
                    output_path.parent.mkdir(parents=True, exist_ok=True)

                    with zf.open(info) as source:
                        file_content = source.read()
                        with open(output_path, 'wb') as target:
                            target.write(file_content)

                    # Get file extension
                    ext = Path(info.filename).suffix.lower().lstrip('.')

                    extracted_files.append(ExtractedFile(
                        filename=info.filename,
                        file_path=str(output_path),
                        file_size=info.file_size,
                        file_format=ext,
                        extracted_at=datetime.utcnow()
                    ))

                    logger.debug(f"Extracted: {info.filename} ({info.file_size} bytes)")

                    # ENHANCEMENT: Recursively extract nested ZIP files
                    if ext == 'zip' and current_depth < self.max_nested_depth:
                        logger.info(f"Found nested ZIP at depth {current_depth}: {info.filename}")
                        try:
                            # Create nested dataset ID
                            nested_id = f"{dataset_id}_nested_{Path(info.filename).stem}"

                            # Recursively extract
                            nested_files = self.extract_from_bytes(
                                content=file_content,
                                dataset_id=nested_id,
                                file_filter=file_filter,
                                current_depth=current_depth + 1
                            )

                            # Add nested files to result
                            extracted_files.extend(nested_files)
                            logger.info(f"Extracted {len(nested_files)} files from nested ZIP: {info.filename}")

                        except Exception as e:
                            logger.warning(f"Failed to extract nested ZIP {info.filename}: {str(e)}")
                            # Continue with other files

            logger.info(f"Extracted {len(extracted_files)} files total to {extraction_path}")
            return extracted_files

        except zipfile.BadZipFile:
            raise ZipExtractionError("Invalid ZIP file format")
        except Exception as e:
            raise ZipExtractionError(f"Extraction failed: {str(e)}")
    
    def _get_existing_files(self, extraction_path: Path) -> List[ExtractedFile]:
        """Get list of already extracted files."""
        extracted_files = []
        
        for file_path in extraction_path.rglob('*'):
            if file_path.is_file():
                ext = file_path.suffix.lower().lstrip('.')
                extracted_files.append(ExtractedFile(
                    filename=file_path.name,
                    file_path=str(file_path),
                    file_size=file_path.stat().st_size,
                    file_format=ext,
                    extracted_at=datetime.fromtimestamp(file_path.stat().st_mtime)
                ))
        
        return extracted_files
    
    def extract_from_url(
        self,
        url: str,
        dataset_id: str = None,
        file_filter: Optional[callable] = None
    ) -> ZipArchiveInfo:
        """
        Download and extract a ZIP file from URL.
        
        Args:
            url: URL of the ZIP file
            dataset_id: Dataset ID (auto-generated if not provided)
            file_filter: Optional function to filter files
            
        Returns:
            ZipArchiveInfo with extraction details
        """
        dataset_id = dataset_id or str(uuid4())
        
        # Download
        content, size = self.download_zip(url, dataset_id)
        downloaded_at = datetime.utcnow()
        
        # Extract
        extracted_files = self.extract_from_bytes(content, dataset_id, file_filter)
        
        return ZipArchiveInfo(
            source_url=url,
            total_files=len(extracted_files),
            total_size=size,
            extracted_files=extracted_files,
            extraction_path=str(self._get_extraction_path(dataset_id)),
            downloaded_at=downloaded_at
        )
    
    def list_archive_contents(self, url: str) -> List[str]:
        """
        List contents of a ZIP archive without extracting.
        
        Args:
            url: URL of the ZIP file
            
        Returns:
            List of filenames in the archive
        """
        content, _ = self.download_zip(url)
        
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            return [info.filename for info in zf.infolist() if not info.is_dir()]
    
    def get_manifest(self, dataset_id: str) -> Optional[List[ExtractedFile]]:
        """
        Get manifest of extracted files for a dataset.
        
        Args:
            dataset_id: Dataset ID
            
        Returns:
            List of ExtractedFile or None if not extracted
        """
        extraction_path = self._get_extraction_path(dataset_id)
        
        if not extraction_path.exists():
            return None
        
        return self._get_existing_files(extraction_path)
    
    def close(self):
        """Close HTTP session."""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
