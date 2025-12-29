"""
Domain Entity: Dataset

This module defines the core Dataset entity representing a discoverable dataset
in the system. This is part of the Domain layer and has no external dependencies.

Author: University of Manchester RSE Team
"""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional


@dataclass
class Dataset:
    """
    Dataset entity representing a discoverable dataset in the system.

    This is a core domain entity that encapsulates the business concept of a dataset.
    It contains essential information needed for dataset discovery and management.

    Attributes:
        id: Unique identifier for the dataset (UUID)
        title: Human-readable title of the dataset
        abstract: Detailed description of the dataset contents and purpose
        metadata_url: URL or path to the source metadata file
        last_updated: Timestamp of when the dataset metadata was last updated
        created_at: Timestamp of when the dataset was first ingested

    Business Rules:
        - ID must be unique across the system
        - Title and abstract are mandatory for discoverability
        - Timestamps are immutable after creation
    """

    id: UUID = field(default_factory=uuid4)
    title: str = field(default="")
    abstract: str = field(default="")
    metadata_url: str = field(default="")
    last_updated: datetime = field(default_factory=datetime.utcnow)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Validate entity invariants after initialization."""
        if not isinstance(self.id, UUID):
            raise TypeError(f"Dataset ID must be a UUID, got {type(self.id)}")

        if not isinstance(self.last_updated, datetime):
            raise TypeError(f"last_updated must be datetime, got {type(self.last_updated)}")

        if not isinstance(self.created_at, datetime):
            raise TypeError(f"created_at must be datetime, got {type(self.created_at)}")

    def is_complete(self) -> bool:
        """
        Check if the dataset has all required fields populated.

        Returns:
            True if title, abstract, and metadata_url are all non-empty, False otherwise
        """
        return bool(self.title and self.abstract and self.metadata_url)

    def update_metadata(self, title: Optional[str] = None,
                       abstract: Optional[str] = None,
                       metadata_url: Optional[str] = None) -> None:
        """
        Update dataset metadata fields and refresh the last_updated timestamp.

        Args:
            title: New title (optional)
            abstract: New abstract (optional)
            metadata_url: New metadata URL (optional)
        """
        if title is not None:
            self.title = title
        if abstract is not None:
            self.abstract = abstract
        if metadata_url is not None:
            self.metadata_url = metadata_url

        # Update timestamp whenever metadata changes
        self.last_updated = datetime.utcnow()

    def __repr__(self) -> str:
        """Return a detailed string representation of the dataset."""
        return (
            f"Dataset(id={self.id}, title='{self.title[:50]}...', "
            f"last_updated={self.last_updated.isoformat()})"
        )

    def __str__(self) -> str:
        """Return a user-friendly string representation."""
        return f"{self.title} ({self.id})"
