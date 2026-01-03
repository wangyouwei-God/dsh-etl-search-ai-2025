"""
Domain Entity: DataFile

This module defines the DataFile entity representing a data file within a dataset.
Datasets have a one-to-many relationship with data files.

Author: University of Manchester RSE Team
"""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional


@dataclass
class DataFile:
    """
    DataFile entity representing a single data file within a dataset.

    Each dataset can contain multiple data files (one-to-many relationship).
    
    Attributes:
        id: Unique identifier for the data file
        dataset_id: Reference to parent dataset
        filename: Name of the file
        file_path: Local path or URL to the file
        file_size: Size in bytes
        file_format: File format/extension (e.g., 'csv', 'tif', 'nc')
        checksum: Optional MD5/SHA checksum for verification
        description: Optional description of file contents
        downloaded_at: Timestamp of when the file was downloaded
        
    Business Rules:
        - Each file must belong to exactly one dataset
        - Filename is required for identification
    """
    
    id: UUID = field(default_factory=uuid4)
    dataset_id: Optional[UUID] = None
    filename: str = ""
    file_path: str = ""
    file_size: int = 0
    file_format: str = ""
    checksum: Optional[str] = None
    description: Optional[str] = None
    downloaded_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Validate entity invariants."""
        if not isinstance(self.id, UUID):
            raise TypeError(f"DataFile ID must be a UUID, got {type(self.id)}")
    
    def is_downloaded(self) -> bool:
        """Check if the file has been downloaded."""
        return self.downloaded_at is not None and bool(self.file_path)
    
    def get_extension(self) -> str:
        """Extract file extension from filename."""
        if '.' in self.filename:
            return self.filename.rsplit('.', 1)[-1].lower()
        return self.file_format.lower() if self.file_format else ""
    
    def __repr__(self) -> str:
        return f"DataFile(id={self.id}, filename='{self.filename}')"
    
    def __str__(self) -> str:
        return self.filename


@dataclass
class SupportingDocument:
    """
    SupportingDocument entity representing supplementary documentation for a dataset.

    Supporting documents include technical reports, methodologies, data dictionaries,
    and other documentation that helps users understand the dataset.
    
    Attributes:
        id: Unique identifier for the document
        dataset_id: Reference to parent dataset
        title: Document title
        document_type: Type of document (e.g., 'methodology', 'technical_report', 'data_dictionary')
        filename: Name of the document file
        file_path: Local path or URL to the document
        file_size: Size in bytes
        content_text: Optional extracted text content (for RAG)
        is_processed: Whether the document has been processed for RAG
        downloaded_at: Timestamp of when the document was downloaded
        
    Business Rules:
        - Each document must belong to exactly one dataset
        - Title or filename is required for identification
    """
    
    id: UUID = field(default_factory=uuid4)
    dataset_id: Optional[UUID] = None
    title: str = ""
    document_type: str = ""
    filename: str = ""
    file_path: str = ""
    file_size: int = 0
    content_text: Optional[str] = None
    is_processed: bool = False
    downloaded_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Validate entity invariants."""
        if not isinstance(self.id, UUID):
            raise TypeError(f"SupportingDocument ID must be a UUID, got {type(self.id)}")
    
    def is_downloaded(self) -> bool:
        """Check if the document has been downloaded."""
        return self.downloaded_at is not None and bool(self.file_path)
    
    def is_pdf(self) -> bool:
        """Check if the document is a PDF."""
        return self.filename.lower().endswith('.pdf')
    
    def get_display_title(self) -> str:
        """Get a display title, preferring title over filename."""
        return self.title if self.title else self.filename
    
    def __repr__(self) -> str:
        return f"SupportingDocument(id={self.id}, title='{self.title or self.filename}')"
    
    def __str__(self) -> str:
        return self.get_display_title()
