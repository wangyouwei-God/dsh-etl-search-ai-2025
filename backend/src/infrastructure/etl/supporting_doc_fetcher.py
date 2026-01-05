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
    - Download supporting documents ZIP directly from CEH data-package URL
    - Extract and process PDFs, DOCX, and other documents
    - Fall back to HTML page crawling if ZIP not available
    - Store documents locally with proper organization
    
    CEH Catalogue URL patterns:
    - Landing page: https://catalogue.ceh.ac.uk/documents/{uuid}
    - Supporting docs ZIP: https://data-package.ceh.ac.uk/sd/{uuid}.zip
      (Contains: readme.html, ro-crate-metadata.json, supporting-documents/*.docx)
    """
    
    # Document type patterns for classification
    DOC_TYPE_PATTERNS = {
        'methodology': r'methodolog|method|how.?to',
        'technical_report': r'technical.?report|tech.?report|report',
        'data_dictionary': r'data.?dictionary|dictionary|codebook|schema',
        'user_guide': r'user.?guide|guide|manual|tutorial',
        'readme': r'readme|read.?me',
    }
    
    # Supported file extensions for document processing
    SUPPORTED_EXTENSIONS = {'.pdf', '.doc', '.docx', '.txt', '.csv', '.xlsx'}
    
    # CEH catalogue base URL
    CEH_BASE_URL = "https://catalogue.ceh.ac.uk"
    
    # CEH supporting documents ZIP URL pattern (PRIMARY SOURCE)
    CEH_SUPPORTING_DOCS_URL = "https://data-package.ceh.ac.uk/sd/{uuid}.zip"
    
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
    
    def download_supporting_zip(self, dataset_id: str) -> List[SupportingDocumentInfo]:
        """
        Download supporting documents ZIP directly from CEH data-package URL.
        
        This is the PRIMARY method for getting supporting documents.
        CEH provides them as a ZIP at: https://data-package.ceh.ac.uk/sd/{uuid}.zip
        
        The ZIP typically contains:
        - readme.html
        - ro-crate-metadata.json
        - supporting-documents/*.docx (or .pdf, etc.)
        
        Args:
            dataset_id: Dataset UUID
            
        Returns:
            List of SupportingDocumentInfo for extracted documents
        """
        import zipfile
        import io
        
        zip_url = self.CEH_SUPPORTING_DOCS_URL.format(uuid=dataset_id)
        logger.info(f"Downloading supporting docs ZIP: {zip_url}")
        
        try:
            # Download ZIP file
            response = self.session.get(zip_url, timeout=self.timeout, stream=True)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '')
            if 'html' in content_type.lower():
                logger.warning(f"Got HTML instead of ZIP for {dataset_id}, falling back to HTML crawling")
                return []
            
            # Read ZIP content
            zip_content = response.content
            if len(zip_content) == 0:
                logger.warning(f"Empty ZIP file for {dataset_id}")
                return []
            
            logger.info(f"Downloaded ZIP: {len(zip_content) / 1024:.1f}KB")
            
            # Create dataset directory
            dataset_dir = self._get_download_path(dataset_id)
            dataset_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract ZIP
            documents = []
            with zipfile.ZipFile(io.BytesIO(zip_content)) as zf:
                for file_info in zf.infolist():
                    filename = file_info.filename
                    
                    # Skip directories
                    if filename.endswith('/'):
                        continue
                    
                    # Get file extension
                    ext = Path(filename).suffix.lower()
                    
                    # Focus on actual documents (PDFs, DOCX, etc.)
                    # Skip readme.html and ro-crate-metadata.json for RAG
                    is_document = ext in self.SUPPORTED_EXTENSIONS
                    is_in_supporting_dir = 'supporting-documents/' in filename or 'supporting_documents/' in filename
                    
                    # Extract the file
                    safe_filename = Path(filename).name  # Get just the filename
                    if is_in_supporting_dir:
                        # Create supporting-documents subdirectory
                        (dataset_dir / 'supporting-documents').mkdir(exist_ok=True)
                        file_path = dataset_dir / 'supporting-documents' / safe_filename
                    else:
                        file_path = dataset_dir / safe_filename
                    
                    # Extract file
                    with zf.open(file_info) as src, open(file_path, 'wb') as dst:
                        dst.write(src.read())
                    
                    file_size = file_path.stat().st_size
                    logger.debug(f"Extracted: {safe_filename} ({file_size / 1024:.1f}KB)")
                    
                    # Only include actual documents (not HTML/JSON metadata)
                    if is_document or is_in_supporting_dir:
                        doc_type = self._classify_document_type(safe_filename, safe_filename)
                        
                        documents.append(SupportingDocumentInfo(
                            id=str(uuid4()),
                            dataset_id=dataset_id,
                            title=Path(safe_filename).stem.replace('_', ' ').replace('-', ' ').title(),
                            document_type=doc_type,
                            url=zip_url,
                            filename=safe_filename,
                            file_path=str(file_path),
                            file_size=file_size,
                            downloaded_at=datetime.utcnow()
                        ))
            
            logger.info(f"Extracted {len(documents)} supporting documents from ZIP")
            return documents
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.info(f"No supporting docs ZIP available for {dataset_id} (404)")
            else:
                logger.warning(f"HTTP error downloading supporting docs ZIP: {e}")
            return []
        except zipfile.BadZipFile as e:
            logger.warning(f"Invalid ZIP file for {dataset_id}: {e}")
            return []
        except Exception as e:
            logger.warning(f"Failed to download supporting docs ZIP for {dataset_id}: {e}")
            return []
    
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

                # ENHANCEMENT: Skip data ZIPs (these should be handled by ZipExtractor)
                # Data ZIPs typically have specific patterns
                if ext == '.zip':
                    # Skip if it's a CEH datastore link (data archive)
                    if 'datastore/eidchub' in href or 'eidc/download' in href:
                        logger.debug(f"Skipping data ZIP (datastore): {href}")
                        continue
                    # Skip if the title/text suggests it's raw data
                    link_text = link.text_content().strip().lower() if link.text_content() else ''
                    if any(keyword in link_text for keyword in ['download data', 'get data', 'dataset', 'raw data']):
                        logger.debug(f"Skipping data ZIP (content match): {href}")
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
        Fetch all supporting documents for a dataset.
        
        Strategy (in order of priority):
        1. Download ZIP directly from data-package.ceh.ac.uk/sd/{uuid}.zip (PRIMARY)
        2. Fall back to HTML page crawling if ZIP not available
        
        Args:
            dataset_id: Dataset UUID
            max_docs: Maximum number of documents to download
            
        Returns:
            List of downloaded SupportingDocumentInfo
        """
        # PRIMARY: Try to download supporting docs ZIP directly
        logger.info(f"Attempting to fetch supporting documents for: {dataset_id}")
        
        documents = self.download_supporting_zip(dataset_id)
        
        if documents:
            logger.info(f"Successfully downloaded {len(documents)} documents from ZIP")
            return documents[:max_docs]
        
        # FALLBACK: Try HTML page crawling
        logger.info(f"ZIP not available, falling back to HTML crawling for {dataset_id}")
        
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
        
        logger.info(f"Downloaded {len(downloaded)}/{len(discovered)} documents via HTML crawling")
        return downloaded
    
    def close(self):
        """Close HTTP session."""
        self.session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
