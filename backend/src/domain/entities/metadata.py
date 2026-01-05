"""
Domain Entity: Metadata

This module defines the Metadata entity representing ISO 19115 geospatial metadata.
This is part of the Domain layer and contains the business structure for metadata.

ISO 19115 is an international standard for describing geographic information and services.

Author: University of Manchester RSE Team
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from datetime import datetime


@dataclass
class BoundingBox:
    """
    Geographic bounding box representing the spatial extent of a dataset.

    This follows the ISO 19115 geographic extent specification.

    Attributes:
        west_longitude: Western-most longitude (-180 to 180)
        east_longitude: Eastern-most longitude (-180 to 180)
        south_latitude: Southern-most latitude (-90 to 90)
        north_latitude: Northern-most latitude (-90 to 90)

    Business Rules:
        - Longitudes must be in range [-180, 180]
        - Latitudes must be in range [-90, 90]
        - West must be less than or equal to East
        - South must be less than or equal to North
    """

    west_longitude: float
    east_longitude: float
    south_latitude: float
    north_latitude: float

    def __post_init__(self):
        """Validate bounding box coordinates."""
        # Validate longitude range
        if not (-180 <= self.west_longitude <= 180):
            raise ValueError(
                f"West longitude must be in range [-180, 180], got {self.west_longitude}"
            )
        if not (-180 <= self.east_longitude <= 180):
            raise ValueError(
                f"East longitude must be in range [-180, 180], got {self.east_longitude}"
            )

        # Validate latitude range
        if not (-90 <= self.south_latitude <= 90):
            raise ValueError(
                f"South latitude must be in range [-90, 90], got {self.south_latitude}"
            )
        if not (-90 <= self.north_latitude <= 90):
            raise ValueError(
                f"North latitude must be in range [-90, 90], got {self.north_latitude}"
            )

        # Validate logical consistency
        if self.west_longitude > self.east_longitude:
            raise ValueError(
                f"West longitude ({self.west_longitude}) must be <= "
                f"East longitude ({self.east_longitude})"
            )
        if self.south_latitude > self.north_latitude:
            raise ValueError(
                f"South latitude ({self.south_latitude}) must be <= "
                f"North latitude ({self.north_latitude})"
            )

    def get_center(self) -> Tuple[float, float]:
        """
        Calculate the center point of the bounding box.

        Returns:
            Tuple of (longitude, latitude) representing the center point
        """
        center_lon = (self.west_longitude + self.east_longitude) / 2
        center_lat = (self.south_latitude + self.north_latitude) / 2
        return (center_lon, center_lat)

    def get_area(self) -> float:
        """
        Calculate the approximate area covered by the bounding box in square degrees.

        Returns:
            Area in square degrees (rough approximation)
        """
        width = self.east_longitude - self.west_longitude
        height = self.north_latitude - self.south_latitude
        return width * height

    def __repr__(self) -> str:
        """Return a detailed string representation."""
        return (
            f"BoundingBox(west={self.west_longitude}, east={self.east_longitude}, "
            f"south={self.south_latitude}, north={self.north_latitude})"
        )


@dataclass
class MetadataRelationship:
    """
    Relationship between metadata documents.

    Attributes:
        relation: Relationship predicate/URI
        target: Target identifier or URL
        target_id: Parsed UUID if available
        target_url: Parsed URL if available
    """

    relation: str
    target: str
    target_id: str = ""
    target_url: str = ""


@dataclass
class Metadata:
    """
    ISO 19115 Metadata entity representing geospatial dataset metadata.

    This entity captures the essential elements of ISO 19115 metadata standard
    needed for dataset discovery and understanding. The full ISO 19115 standard
    contains many more fields, but this implementation focuses on core discovery
    metadata.

    Attributes:
        title: Dataset title (mandatory in ISO 19115)
        abstract: Dataset abstract/description (mandatory in ISO 19115)
        keywords: List of descriptive keywords for discovery
        bounding_box: Geographic extent of the dataset
        temporal_extent_start: Start date/time of temporal coverage
        temporal_extent_end: End date/time of temporal coverage
        contact_organization: Organization responsible for the dataset
        contact_email: Contact email for inquiries
        metadata_date: Date when metadata was created/updated
        dataset_language: Language of the dataset (ISO 639-2 code)
        topic_category: ISO 19115 topic category (e.g., 'environment', 'climatology')
        relationships: Related metadata targets derived from JSON relationships

    Business Rules:
        - Title and abstract are mandatory for ISO 19115 compliance
        - Keywords should be non-empty for discoverability
        - Bounding box is required for geospatial datasets
        - Contact information should be provided
    """

    title: str
    abstract: str
    keywords: List[str] = field(default_factory=list)
    bounding_box: Optional[BoundingBox] = None
    temporal_extent_start: Optional[datetime] = None
    temporal_extent_end: Optional[datetime] = None
    contact_organization: str = ""
    contact_email: str = ""
    metadata_date: datetime = field(default_factory=datetime.utcnow)
    dataset_language: str = "eng"  # Default to English (ISO 639-2 code)
    topic_category: str = ""
    download_url: str = ""  # Direct download link for the dataset
    landing_page_url: str = ""  # URL of the dataset landing page (for supporting docs)
    # Access type: "download" (ZIP file) or "fileAccess" (web-accessible folder)
    # PDF requirement: "Datasets can be accessed using the download option... Other datasets 
    # can be accessed using the fileAccess option. These datasets are typically available 
    # through a web-accessible folder and require different handling."
    access_type: str = "download"
    relationships: List[MetadataRelationship] = field(default_factory=list)

    def __post_init__(self):
        """Validate metadata invariants after initialization."""
        if not self.title or not self.title.strip():
            raise ValueError("Metadata title is mandatory and cannot be empty")

        if not self.abstract or not self.abstract.strip():
            raise ValueError("Metadata abstract is mandatory and cannot be empty")

        # Validate temporal extent if provided
        if (self.temporal_extent_start and self.temporal_extent_end and
            self.temporal_extent_start > self.temporal_extent_end):
            raise ValueError(
                f"Temporal extent start ({self.temporal_extent_start}) must be "
                f"before end ({self.temporal_extent_end})"
            )

    def is_geospatial(self) -> bool:
        """
        Check if this metadata represents a geospatial dataset.

        Returns:
            True if bounding box is defined, False otherwise
        """
        return self.bounding_box is not None

    def has_temporal_extent(self) -> bool:
        """
        Check if temporal extent information is available.

        Returns:
            True if both start and end dates are defined, False otherwise
        """
        return (self.temporal_extent_start is not None and
                self.temporal_extent_end is not None)

    def add_keywords(self, *keywords: str) -> None:
        """
        Add keywords to the metadata.

        Args:
            *keywords: Variable number of keyword strings to add
        """
        for keyword in keywords:
            if keyword and keyword.strip() and keyword not in self.keywords:
                self.keywords.append(keyword.strip())

    def get_summary(self) -> str:
        """
        Get a human-readable summary of the metadata.

        Returns:
            Multi-line string summary of key metadata fields
        """
        summary_lines = [
            f"Title: {self.title}",
            f"Abstract: {self.abstract[:100]}..." if len(self.abstract) > 100 else f"Abstract: {self.abstract}",
            f"Keywords: {', '.join(self.keywords) if self.keywords else 'None'}",
            f"Geospatial: {'Yes' if self.is_geospatial() else 'No'}",
        ]

        if self.bounding_box:
            center = self.bounding_box.get_center()
            summary_lines.append(f"Center: {center[1]:.2f}°N, {center[0]:.2f}°E")

        if self.has_temporal_extent():
            summary_lines.append(
                f"Temporal: {self.temporal_extent_start.year} - {self.temporal_extent_end.year}"
            )

        return "\n".join(summary_lines)

    def __repr__(self) -> str:
        """Return a detailed string representation."""
        return (
            f"Metadata(title='{self.title[:50]}...', "
            f"keywords={len(self.keywords)}, "
            f"geospatial={self.is_geospatial()})"
        )

    def __str__(self) -> str:
        """Return a user-friendly string representation."""
        return f"Metadata: {self.title}"
