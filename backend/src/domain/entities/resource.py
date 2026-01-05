"""
Domain Entity: Resource

This module defines the Resource entity for representing metadata resources
such as downloadable files, API endpoints, or database records.

This is part of the Domain layer and represents the abstraction mentioned in PDF:
"Your extraction class hierarchy should demonstrate capability to abstract the
resources you extract (ie: remote files, API results, database records)"

Author: University of Manchester RSE Team
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class Resource:
    """
    Domain entity representing a resource that can be extracted from metadata.

    Resources can be:
    - Remote files (ZIP archives, data files)
    - API endpoints
    - Database records
    - Web accessible folders

    This abstraction allows the ETL system to handle different resource types
    uniformly.
    """

    resource_id: str  # Unique identifier for the resource
    resource_type: str  # Type: 'file', 'api', 'database', 'folder'
    url: Optional[str] = None  # URL for remote resources
    file_path: Optional[str] = None  # Local file path
    format: Optional[str] = None  # Format: 'zip', 'csv', 'json', etc.
    size_bytes: Optional[int] = None  # Size in bytes
    checksum: Optional[str] = None  # MD5/SHA256 checksum
    description: Optional[str] = None  # Human-readable description
    discovered_at: datetime = None  # When this resource was discovered

    def __post_init__(self):
        """Set default discovered_at timestamp."""
        if self.discovered_at is None:
            self.discovered_at = datetime.utcnow()

    def is_remote(self) -> bool:
        """Check if this is a remote resource."""
        return self.url is not None

    def is_local(self) -> bool:
        """Check if this is a local resource."""
        return self.file_path is not None

    def __repr__(self) -> str:
        """Return a detailed string representation."""
        return (
            f"Resource(id='{self.resource_id}', "
            f"type='{self.resource_type}', "
            f"url='{self.url}' if self.url else 'local')"
        )

    def __str__(self) -> str:
        """Return a user-friendly string representation."""
        return f"Resource: {self.resource_id} ({self.resource_type})"


@dataclass
class RemoteFileResource(Resource):
    """Resource representing a remote file (e.g., ZIP archive, data file)."""

    def __init__(self, url: str, title: str = "", description: str = ""):
        """Initialize a remote file resource."""
        super().__init__(
            resource_id=url,
            resource_type='file',
            url=url,
            format=url.split('.')[-1] if '.' in url else None,
            description=description or title
        )


@dataclass
class WebFolderResource(Resource):
    """Resource representing a web-accessible folder or datastore."""

    def __init__(self, url: str, title: str = "", description: str = ""):
        """Initialize a web folder resource."""
        super().__init__(
            resource_id=url,
            resource_type='folder',
            url=url,
            description=description or title
        )


@dataclass
class APIDataResource(Resource):
    """Resource representing an API endpoint."""

    def __init__(self, url: str, title: str = "", description: str = ""):
        """Initialize an API data resource."""
        super().__init__(
            resource_id=url,
            resource_type='api',
            url=url,
            description=description or title
        )
