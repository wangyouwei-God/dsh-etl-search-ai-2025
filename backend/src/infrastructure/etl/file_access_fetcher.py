"""
Infrastructure: File Access Fetcher

Handles datasets exposed via web-accessible folders (fileAccess).
This component discovers and optionally downloads data files listed in
directory-style HTML pages.

Author: University of Manchester RSE Team
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set
from urllib.parse import urljoin, urlparse

import requests
from lxml import html

logger = logging.getLogger(__name__)


@dataclass
class FileAccessFileInfo:
    """Information about a file exposed via a web folder."""

    url: str
    filename: str
    file_format: str
    file_size: int = 0
    local_path: Optional[str] = None
    downloaded_at: Optional[datetime] = None

    @property
    def is_downloaded(self) -> bool:
        return self.local_path is not None and self.downloaded_at is not None


class FileAccessFetcher:
    """
    Fetcher for datasets exposed via fileAccess (web folder listing).

    Capabilities:
    - Crawl HTML directory listings to discover data files
    - Recursively traverse subfolders (depth-limited)
    - Optionally download files to local storage
    """

    DEFAULT_DOWNLOAD_DIR = "extracted_datasets"
    SKIP_EXTENSIONS = {".html", ".htm", ".php", ".asp", ".aspx"}

    def __init__(
        self,
        download_dir: str = DEFAULT_DOWNLOAD_DIR,
        timeout: int = 60,
        max_size_mb: int = 500
    ):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.max_size_bytes = max_size_mb * 1024 * 1024

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "DatasetSearchBot/1.0 (University of Manchester RSE)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        })

        logger.info(f"FileAccessFetcher initialized: dir={self.download_dir}")

    def list_files(
        self,
        base_url: str,
        max_files: Optional[int] = None,
        max_depth: int = 1
    ) -> List[FileAccessFileInfo]:
        """
        Crawl a web folder to discover files.

        Args:
            base_url: Base folder URL (fileAccess endpoint)
            max_files: Maximum number of files to return
            max_depth: Depth of recursive traversal for subfolders
        """
        if not base_url:
            return []

        normalized = base_url if base_url.endswith("/") else base_url + "/"
        visited: Set[str] = set()
        seen_files: Set[str] = set()
        files: List[FileAccessFileInfo] = []

        self._crawl_folder(
            normalized,
            root_url=normalized,
            max_depth=max_depth,
            visited=visited,
            seen_files=seen_files,
            files=files,
            max_files=max_files
        )

        return files

    def download_files(
        self,
        files: List[FileAccessFileInfo],
        dataset_id: str,
        max_files: Optional[int] = None
    ) -> List[FileAccessFileInfo]:
        """
        Download discovered files to local storage.

        Args:
            files: List of discovered files
            dataset_id: Dataset UUID for local storage organization
            max_files: Optional maximum files to download
        """
        if not files:
            return []

        dataset_dir = self.download_dir / dataset_id
        dataset_dir.mkdir(parents=True, exist_ok=True)

        downloaded: List[FileAccessFileInfo] = []
        for info in files:
            if max_files is not None and len(downloaded) >= max_files:
                break
            try:
                dest_path = dataset_dir / info.filename
                self._download_file(info.url, dest_path)
                info.local_path = str(dest_path)
                info.downloaded_at = datetime.utcnow()
                info.file_size = dest_path.stat().st_size
                downloaded.append(info)
            except Exception as e:
                logger.warning(f"Failed to download {info.url}: {e}")

        return downloaded

    def _crawl_folder(
        self,
        url: str,
        root_url: str,
        max_depth: int,
        visited: Set[str],
        seen_files: Set[str],
        files: List[FileAccessFileInfo],
        max_files: Optional[int]
    ) -> None:
        """Recursive crawler for directory-style HTML pages."""
        if max_files is not None and len(files) >= max_files:
            return

        if url in visited:
            return
        visited.add(url)

        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.warning(f"Failed to fetch folder listing {url}: {e}")
            return

        content_type = (response.headers.get("content-type") or "").lower()
        if "text/html" not in content_type:
            file_info = self._file_from_url(url)
            if file_info and file_info.url not in seen_files:
                files.append(file_info)
                seen_files.add(file_info.url)
            return

        tree = html.fromstring(response.text)
        links = tree.xpath("//a[@href]")
        base_netloc = urlparse(url).netloc

        for link in links:
            href = (link.get("href") or "").strip()
            if not href or href.startswith("#") or href.startswith("?"):
                continue
            if href in ("../", "./", "/"):
                continue

            full_url = urljoin(url, href)
            parsed = urlparse(full_url)
            if parsed.netloc and parsed.netloc != base_netloc:
                continue
            if not full_url.startswith(root_url):
                continue

            is_dir = href.endswith("/") or (link.text_content() or "").strip().endswith("/")
            if is_dir:
                if max_depth > 0:
                    self._crawl_folder(
                        full_url if full_url.endswith("/") else full_url + "/",
                        root_url=root_url,
                        max_depth=max_depth - 1,
                        visited=visited,
                        seen_files=seen_files,
                        files=files,
                        max_files=max_files
                    )
                continue

            file_info = self._file_from_url(full_url)
            if not file_info:
                continue
            if file_info.url in seen_files:
                continue

            files.append(file_info)
            seen_files.add(file_info.url)
            if max_files is not None and len(files) >= max_files:
                return

    def _file_from_url(self, file_url: str) -> Optional[FileAccessFileInfo]:
        """Create FileAccessFileInfo from a URL."""
        filename = Path(urlparse(file_url).path).name
        if not filename:
            return None

        ext = f".{filename.rsplit('.', 1)[-1].lower()}" if "." in filename else ""
        if ext in self.SKIP_EXTENSIONS:
            return None

        file_format = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        return FileAccessFileInfo(
            url=file_url,
            filename=filename,
            file_format=file_format
        )

    def _download_file(self, url: str, destination: Path) -> None:
        """Download a single file with size safeguards."""
        response = self.session.get(url, timeout=self.timeout, stream=True)
        response.raise_for_status()

        content_length = response.headers.get("content-length")
        if content_length and content_length.isdigit():
            if int(content_length) > self.max_size_bytes:
                raise ValueError("File too large to download within size limit")

        destination.parent.mkdir(parents=True, exist_ok=True)
        with open(destination, "wb") as f:
            downloaded = 0
            for chunk in response.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                downloaded += len(chunk)
                if downloaded > self.max_size_bytes:
                    raise ValueError("File exceeds size limit during download")
                f.write(chunk)
