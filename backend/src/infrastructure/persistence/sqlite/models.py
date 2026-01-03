"""
Infrastructure: SQLAlchemy ORM Models

This module defines the database schema using SQLAlchemy ORM models.
These models map domain entities to database tables.

Tables:
    - datasets: Core dataset information
    - metadata: ISO 19115 metadata for each dataset

Author: University of Manchester RSE Team
"""

from sqlalchemy import Column, String, DateTime, Text, Integer, Float, ForeignKey, Index
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
import json

# Create declarative base
Base = declarative_base()


class DatasetModel(Base):
    """
    SQLAlchemy model for datasets table.

    Maps to the Dataset domain entity.
    """

    __tablename__ = 'datasets'

    # Primary key
    id = Column(String(36), primary_key=True, index=True)  # UUID as string

    # Core fields
    title = Column(String(500), nullable=False, index=True)
    abstract = Column(Text, nullable=False)
    metadata_url = Column(String(1000), nullable=False)

    # Timestamps
    last_updated = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationship to metadata (one-to-one)
    # Note: Cannot use 'metadata' as name (reserved by SQLAlchemy)
    dataset_metadata = relationship(
        "MetadataModel",
        back_populates="dataset",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    # Relationship to data files (one-to-many)
    data_files = relationship(
        "DataFileModel",
        back_populates="dataset",
        cascade="all, delete-orphan"
    )
    
    # Relationship to supporting documents (one-to-many)
    supporting_documents = relationship(
        "SupportingDocumentModel",
        back_populates="dataset",
        cascade="all, delete-orphan"
    )

    # Indexes for search performance
    __table_args__ = (
        Index('idx_dataset_title', 'title'),
        Index('idx_dataset_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<DatasetModel(id='{self.id}', title='{self.title[:50]}...')>"


class MetadataModel(Base):
    """
    SQLAlchemy model for metadata table.

    Maps to the Metadata domain entity (ISO 19115).
    Stores complex fields (bounding_box, keywords) as JSON.
    """

    __tablename__ = 'metadata'

    # Primary key and foreign key
    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(String(36), ForeignKey('datasets.id'), nullable=False, unique=True, index=True)

    # Mandatory ISO 19115 fields
    title = Column(String(500), nullable=False, index=True)
    abstract = Column(Text, nullable=False)

    # Keywords (stored as JSON array)
    keywords_json = Column(Text, nullable=True)  # JSON array: ["keyword1", "keyword2"]

    # Geographic extent (stored as JSON object)
    # Format: {"west": -180.0, "east": 180.0, "south": -90.0, "north": 90.0}
    bounding_box_json = Column(Text, nullable=True)

    # Temporal extent
    temporal_extent_start = Column(DateTime, nullable=True)
    temporal_extent_end = Column(DateTime, nullable=True)

    # Contact information
    contact_organization = Column(String(500), nullable=True)
    contact_email = Column(String(255), nullable=True)

    # Additional ISO 19115 fields
    metadata_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    dataset_language = Column(String(10), nullable=True, default='eng')
    topic_category = Column(String(100), nullable=True)

    # Relationship to dataset
    dataset = relationship("DatasetModel", back_populates="dataset_metadata")

    # Indexes for search performance
    __table_args__ = (
        Index('idx_metadata_title', 'title'),
        Index('idx_metadata_dataset_id', 'dataset_id'),
    )

    def __repr__(self):
        return f"<MetadataModel(dataset_id='{self.dataset_id}', title='{self.title[:50]}...')>"

    # Helper methods for JSON serialization/deserialization

    def set_keywords(self, keywords: list):
        """
        Store keywords list as JSON.

        Args:
            keywords: List of keyword strings
        """
        if keywords:
            self.keywords_json = json.dumps(keywords)
        else:
            self.keywords_json = None

    def get_keywords(self) -> list:
        """
        Retrieve keywords from JSON.

        Returns:
            List of keyword strings
        """
        if self.keywords_json:
            try:
                return json.loads(self.keywords_json)
            except json.JSONDecodeError:
                return []
        return []

    def set_bounding_box(self, bounding_box: dict):
        """
        Store bounding box as JSON.

        Args:
            bounding_box: Dict with keys: west, east, south, north
        """
        if bounding_box:
            self.bounding_box_json = json.dumps(bounding_box)
        else:
            self.bounding_box_json = None

    def get_bounding_box(self) -> dict:
        """
        Retrieve bounding box from JSON.

        Returns:
            Dict with west, east, south, north coordinates
        """
        if self.bounding_box_json:
            try:
                return json.loads(self.bounding_box_json)
            except json.JSONDecodeError:
                return None
        return None


class DataFileModel(Base):
    """
    SQLAlchemy model for data files within datasets.
    
    Maps to the DataFile domain entity.
    Represents the one-to-many relationship between datasets and their data files.
    """
    
    __tablename__ = 'data_files'
    
    # Primary key
    id = Column(String(36), primary_key=True, index=True)  # UUID as string
    
    # Foreign key to dataset
    dataset_id = Column(String(36), ForeignKey('datasets.id'), nullable=False, index=True)
    
    # File information
    filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=True)
    file_size = Column(Integer, nullable=True, default=0)
    file_format = Column(String(50), nullable=True)
    checksum = Column(String(64), nullable=True)  # MD5/SHA256
    description = Column(Text, nullable=True)
    
    # Timestamps
    downloaded_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationship
    dataset = relationship("DatasetModel", back_populates="data_files")
    
    __table_args__ = (
        Index('idx_data_file_dataset_id', 'dataset_id'),
        Index('idx_data_file_filename', 'filename'),
    )
    
    def __repr__(self):
        return f"<DataFileModel(id='{self.id}', filename='{self.filename}')>"


class SupportingDocumentModel(Base):
    """
    SQLAlchemy model for supporting documents.
    
    Maps to the SupportingDocument domain entity.
    Stores supplementary documentation with optional extracted text for RAG.
    """
    
    __tablename__ = 'supporting_documents'
    
    # Primary key
    id = Column(String(36), primary_key=True, index=True)  # UUID as string
    
    # Foreign key to dataset
    dataset_id = Column(String(36), ForeignKey('datasets.id'), nullable=False, index=True)
    
    # Document information
    title = Column(String(500), nullable=True)
    document_type = Column(String(100), nullable=True)  # methodology, technical_report, etc.
    filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=True)
    file_size = Column(Integer, nullable=True, default=0)
    
    # RAG support
    content_text = Column(Text, nullable=True)  # Extracted text content
    is_processed = Column(Integer, nullable=False, default=0)  # Boolean as int
    
    # Timestamps
    downloaded_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationship
    dataset = relationship("DatasetModel", back_populates="supporting_documents")
    
    __table_args__ = (
        Index('idx_supporting_doc_dataset_id', 'dataset_id'),
        Index('idx_supporting_doc_type', 'document_type'),
    )
    
    def __repr__(self):
        return f"<SupportingDocumentModel(id='{self.id}', title='{self.title or self.filename}')>"


# Database initialization helper
def create_tables(engine):
    """
    Create all tables in the database.

    Args:
        engine: SQLAlchemy engine instance

    Example:
        >>> from sqlalchemy import create_engine
        >>> engine = create_engine('sqlite:///datasets.db')
        >>> create_tables(engine)
    """
    Base.metadata.create_all(engine)


def drop_tables(engine):
    """
    Drop all tables from the database.

    Args:
        engine: SQLAlchemy engine instance

    Warning:
        This will delete all data! Use with caution.

    Example:
        >>> from sqlalchemy import create_engine
        >>> engine = create_engine('sqlite:///datasets.db')
        >>> drop_tables(engine)
    """
    Base.metadata.drop_all(engine)

