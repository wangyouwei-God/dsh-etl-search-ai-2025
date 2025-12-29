"""
Domain Repository Interface: IDatasetRepository

This module defines the repository interface for dataset persistence.
This is part of the Domain layer and contains only the abstraction (interface).

The actual implementation will be in the Infrastructure layer.

Author: University of Manchester RSE Team
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from domain.entities.dataset import Dataset
from domain.entities.metadata import Metadata


class IDatasetRepository(ABC):
    """
    Repository interface for Dataset persistence.

    This interface defines the contract for dataset storage and retrieval
    operations. It follows the Repository Pattern, which provides an
    abstraction layer between the domain and data mapping layers.

    Design Pattern: Repository Pattern
    - Abstracts data access logic
    - Domain layer defines the interface
    - Infrastructure layer provides implementations (SQLite, PostgreSQL, etc.)

    SOLID Principles:
    - Dependency Inversion: Domain depends on abstraction, not concrete implementation
    - Interface Segregation: Focused interface with only necessary methods
    - Single Responsibility: Only handles dataset persistence operations
    """

    @abstractmethod
    def save(self, dataset: Dataset, metadata: Metadata) -> str:
        """
        Save a dataset and its metadata to the repository.

        This method persists both the dataset entity and its associated
        metadata. If the dataset already exists (based on ID), it will
        be updated; otherwise, a new record is created.

        Args:
            dataset: Dataset entity to persist
            metadata: Metadata entity associated with the dataset

        Returns:
            str: The UUID of the saved dataset

        Raises:
            RepositoryError: If save operation fails

        Example:
            >>> repo = SQLiteDatasetRepository(session)
            >>> dataset = Dataset(title="My Dataset", ...)
            >>> metadata = Metadata(title="My Dataset", ...)
            >>> dataset_id = repo.save(dataset, metadata)
        """
        pass

    @abstractmethod
    def get_by_id(self, dataset_id: str) -> Optional[tuple[Dataset, Metadata]]:
        """
        Retrieve a dataset and its metadata by ID.

        Args:
            dataset_id: UUID string of the dataset to retrieve

        Returns:
            Tuple of (Dataset, Metadata) if found, None otherwise

        Example:
            >>> repo = SQLiteDatasetRepository(session)
            >>> result = repo.get_by_id("abc-123")
            >>> if result:
            ...     dataset, metadata = result
            ...     print(dataset.title)
        """
        pass

    @abstractmethod
    def exists(self, dataset_id: str) -> bool:
        """
        Check if a dataset exists in the repository.

        Args:
            dataset_id: UUID string of the dataset to check

        Returns:
            bool: True if dataset exists, False otherwise

        Example:
            >>> repo = SQLiteDatasetRepository(session)
            >>> if repo.exists("abc-123"):
            ...     print("Dataset already exists")
        """
        pass

    @abstractmethod
    def get_all(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[tuple[Dataset, Metadata]]:
        """
        Retrieve all datasets with optional pagination.

        Args:
            limit: Maximum number of datasets to return
            offset: Number of datasets to skip (for pagination)

        Returns:
            List of (Dataset, Metadata) tuples

        Example:
            >>> repo = SQLiteDatasetRepository(session)
            >>> # Get first 10 datasets
            >>> datasets = repo.get_all(limit=10, offset=0)
            >>> for dataset, metadata in datasets:
            ...     print(dataset.title)
        """
        pass

    @abstractmethod
    def search_by_title(self, title_query: str) -> List[tuple[Dataset, Metadata]]:
        """
        Search datasets by title (partial match).

        Args:
            title_query: Search string to match against titles

        Returns:
            List of (Dataset, Metadata) tuples matching the query

        Example:
            >>> repo = SQLiteDatasetRepository(session)
            >>> results = repo.search_by_title("climate")
            >>> for dataset, metadata in results:
            ...     print(f"Found: {dataset.title}")
        """
        pass

    @abstractmethod
    def delete(self, dataset_id: str) -> bool:
        """
        Delete a dataset and its metadata from the repository.

        Args:
            dataset_id: UUID string of the dataset to delete

        Returns:
            bool: True if deleted, False if not found

        Example:
            >>> repo = SQLiteDatasetRepository(session)
            >>> if repo.delete("abc-123"):
            ...     print("Dataset deleted successfully")
        """
        pass

    @abstractmethod
    def count(self) -> int:
        """
        Count total number of datasets in the repository.

        Returns:
            int: Total count of datasets

        Example:
            >>> repo = SQLiteDatasetRepository(session)
            >>> total = repo.count()
            >>> print(f"Total datasets: {total}")
        """
        pass


class RepositoryError(Exception):
    """Base exception for repository operations."""
    pass


class DatasetNotFoundError(RepositoryError):
    """Raised when a dataset is not found in the repository."""

    def __init__(self, dataset_id: str):
        self.dataset_id = dataset_id
        super().__init__(f"Dataset not found: {dataset_id}")


class DatasetAlreadyExistsError(RepositoryError):
    """Raised when attempting to create a dataset that already exists."""

    def __init__(self, dataset_id: str):
        self.dataset_id = dataset_id
        super().__init__(f"Dataset already exists: {dataset_id}")
