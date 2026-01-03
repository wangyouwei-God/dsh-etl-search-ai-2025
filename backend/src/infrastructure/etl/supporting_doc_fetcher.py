"""
Infrastructure: Supporting Document Fetcher

This module provides functionality for downloading supporting documents
(PDFs, technical reports, methodologies) associated with datasets.

Author: University of Manchester RSE Team
"""

import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse
from uuid import uuid4

import requests
from lxml import html

logger = logging.getLogger(__name__)


class DocumentFetchError(Exception):
    """Raised when document fetch fails."""
    pass


@dataclass
class SupportingDocumentInfo:
    """Information about a supporting document."""
    id: str
    dataset_id: str
    title: str
    document_type: str  # 'methodology', 'technical_report', 'data_dictionary', 'other'
    url: str
    filename: str
    file_path: Optional[str]
    file_size: int
    downloaded_at: Optional[datetime]
    
    @property
    def is_downloaded(self) -> bool:
        return self.downloaded_at is not None and self.file_path is not None


class SupportingDocFetcher:
    """
    Fetcher for supporting documents associated with datasets.
    
    This class provides the capability to:
    - Discover supporting documents from dataset landing pages
    - Download PDFs and other documents
    - Extract document metadata
    - Store documents locally with proper organization
    
    CEH Catalogue URL patterns:
    - Landing page: https://catalogue.ceh.ac.uk/documents/{uuid}
    - Supporting docs: linked from the landing page
    """
    
    # Document type patterns for classification
    DOC_TYPE_PATTERNS = {
        'methodology': r'methodolog|method|how.?to',
        'technical_report': r'technical.?report|tech.?report|report',
        'data_dictionary': r'data.?dictionary|dictionary|codebook|schema',
        'user_guide': r'user.?guide|guide|manual|tutorial',
        'readme': r'readme|read.?me',
    }
    
    # Supported file extensions
    SUPPORTED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.txt', '.csv', '.xlsx'}
    
    # CEH catalogue base URL
    CEH_BASE_URL = "https://catalogue.ceh.ac.uk"
    
    def __init__(
        self,
        download_dir: str = "supporting_docs",
        timeout: int = 60,
        max_size_mb: int = 50
    ):
        """
        Initialize supporting document fetcher.
        
        Args:
            download_dir: Directory for downloaded documents
            timeout: Download timeout in seconds
            max_size_mb: Maximum document size to download (MB)
        """
        self.download_dir = Path(download_dir)
        self.timeout = timeout
        self.max_size_bytes = max_size_mb * 1024 * 1024
        
        # Create download directory
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        # Session for HTTP requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'DatasetSearchBot/1.0 (University of Manchester RSE)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        })
        
        logger.info(f"SupportingDocFetcher initialized: dir={self.download_dir}")
    
    def _get_download_path(self, dataset_id: str) -> Path:
        """Get the download path for a dataset's documents."""
        return self.download_dir / dataset_id
    
    def _classify_document_type(self, title: str, filename: str) -> str:
        """Classify document type based on title/filename."""
        text = f"{title} {filename}".lower()
        
        for doc_type, pattern in self.DOC_TYPE_PATTERNS.items():
            if re.search(pattern, text, re.IGNORECASE):
                return doc_type
        
        return 'other'
    
    def _extract_filename_from_url(self, url: str) -> str:
        """Extract filename from URL."""
        parsed = urlparse(url)
        path = parsed.path
        filename = path.split('/')[-1] if '/' in path else path
        
        # Clean up filename
        if not filename or filename == '':
            filename = f"document_{uuid4().hex[:8]}.pdf"
        
        return filename
    
    def discover_documents(self, dataset_id: str) -> List[SupportingDocumentInfo]:
        """
        Discover supporting documents from a dataset's landing page.
        
        Args:
            dataset_id: Dataset UUID
            
        Returns:
            List of SupportingDocumentInfo (not yet downloaded)
        """
        landing_url = f"{self.CEH_BASE_URL}/documents/{dataset_id}"
        
        try:
            logger.info(f"Discovering supporting docs for: {dataset_id}")
            
            response = self.session.get(landing_url, timeout=self.timeout)
            response.raise_for_status()
            
            # Parse HTML
            tree = html.fromstring(response.content)
            
            # Find document links
            # CEH typically has supporting documents in specific sections
            documents = []
            
            # Look for links in "Supporting Documents" or similar sections
            doc_links = tree.xpath('//a[contains(@href, ".pdf") or contains(@href, "download")]')
            
            seen_urls = set()
            for link in doc_links:
                href = link.get('href', '')
                
                # Skip if no href or already seen
                if not href or href in seen_urls:
                    continue
                
                # Make absolute URL
                if not href.startswith('http'):
                    href = urljoin(landing_url, href)
                
                # Check if it's a document link
                ext = Path(urlparse(href).path).suffix.lower()
                if ext not in self.SUPPORTED_EXTENSIONS and 'download' not in href.lower():
                    continue
                
                seen_urls.add(href)
                
                # Get title from link text or title attribute
                title = link.text_content().strip() if link.text_content() else ''
                if not title:
                    title = link.get('title', '')
                if not title:
                    title = self._extract_filename_from_url(href)
                
                filename = self._extract_filename_from_url(href)
                doc_type = self._classify_document_type(title, filename)
                
                documents.append(SupportingDocumentInfo(
                    id=str(uuid4()),
                    dataset_id=dataset_id,
                    title=title,
                    document_type=doc_type,
                    url=href,
                    filename=filename,
                    file_path=None,
                    file_size=0,
                    downloaded_at=None
                ))
            
            logger.info(f"Discovered {len(documents)} supporting documents")
            return documents
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to discover documents for {dataset_id}: {e}")
            return []
    
    def download_document(
        self,
        doc_info: SupportingDocumentInfo
    ) -> SupportingDocumentInfo:
        """
        Download a supporting document.
        
        Args:
            doc_info: Document information (with URL)
            
        Returns:
            Updated SupportingDocumentInfo with file_path and downloaded_at
        """
        try:
            logger.info(f"Downloading: {doc_info.title} ({doc_info.url})")
            
            # Create dataset directory
            dataset_dir = self._get_download_path(doc_info.dataset_id)
            dataset_dir.mkdir(parents=True, exist_ok=True)
            
            # Download file
            response = self.session.get(doc_info.url, timeout=self.timeout, stream=True)
            response.raise_for_status()
            
            # Check size
            content_length = int(response.headers.get('content-length', 0))
            if content_length > self.max_size_bytes:
                raise DocumentFetchError(
                    f"Document too large: {content_length / 1024 / 1024:.1f}MB"
                )
            
            # Determine filename
            filename = doc_info.filename
            
            # Check for filename in Content-Disposition header
            content_disp = response.headers.get('content-disposition', '')
            if 'filename=' in content_disp:
                match = re.search(r'filename[^;=\n]*=([\"\']?)([^;\"\'\n]+)\1', content_disp)
                if match:
                    filename = match.group(2)
            
            # Save file
            file_path = dataset_dir / filename
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            file_size = file_path.stat().st_size
            
            logger.info(f"Downloaded: {filename} ({file_size / 1024:.1f}KB)")
            
            # Return updated info
            return SupportingDocumentInfo(
                id=doc_info.id,
                dataset_id=doc_info.dataset_id,
                title=doc_info.title,
                document_type=doc_info.document_type,
                url=doc_info.url,
                filename=filename,
                file_path=str(file_path),
                file_size=file_size,
                downloaded_at=datetime.utcnow()
            )
            
        except requests.exceptions.RequestException as e:
            raise DocumentFetchError(f"Download failed: {str(e)}")
    
    def fetch_all_documents(
        self,
        dataset_id: str,
        max_docs: int = 5
    ) -> List[SupportingDocumentInfo]:
        """
        Discover and download all supporting documents for a dataset.
        
        Args:
            dataset_id: Dataset UUID
            max_docs: Maximum number of documents to download
            
        Returns:
            List of downloaded SupportingDocumentInfo
        """
        # Discover documents
        discovered = self.discover_documents(dataset_id)
        
        if not discovered:
            logger.info(f"No supporting documents found for {dataset_id}")
            return []
        
        # Download up to max_docs
        downloaded = []
        for doc_info in discovered[:max_docs]:
            try:
                result = self.download_document(doc_info)
                downloaded.append(result)
            except DocumentFetchError as e:
                logger.warning(f"Failed to download {doc_info.title}: {e}")
        
        logger.info(f"Downloaded {len(downloaded)}/{len(discovered)} documents")
        return downloaded
    
    def close(self):
        """Close HTTP session."""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
