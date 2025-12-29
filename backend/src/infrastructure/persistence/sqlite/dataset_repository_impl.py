"""
Infrastructure: SQLite Dataset Repository Implementation

This module implements the IDatasetRepository interface using SQLAlchemy and SQLite.
It handles all CRUD operations for datasets and metadata.

Author: University of Manchester RSE Team
"""

import logging
from typing import Optional, List
from datetime import datetime
from uuid import UUID
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../../')))

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from domain.repositories.dataset_repository import (
    IDatasetRepository,
    RepositoryError,
    DatasetNotFoundError,
    DatasetAlreadyExistsError
)
from domain.entities.dataset import Dataset
from domain.entities.metadata import Metadata, BoundingBox

from .models import DatasetModel, MetadataModel

# Configure logging
logger = logging.getLogger(__name__)


class SQLiteDatasetRepository(IDatasetRepository):
    """
    SQLite implementation of IDatasetRepository.

    This class implements all repository operations using SQLAlchemy ORM
    with a SQLite backend. It handles the mapping between domain entities
    and database models.

    Design Pattern: Repository Pattern
    - Abstracts data access details
    - Maps between domain entities and ORM models
    - Handles transactions and error handling

    Attributes:
        session: SQLAlchemy session for database operations
    """

    def __init__(self, session: Session):
        """
        Initialize the repository with a database session.

        Args:
            session: SQLAlchemy session instance

        Example:
            >>> from infrastructure.persistence.sqlite.connection import get_session
            >>> session = get_session()
            >>> repo = SQLiteDatasetRepository(session)
        """
        self.session = session
        logger.debug("SQLiteDatasetRepository initialized")

    def save(self, dataset: Dataset, metadata: Metadata) -> str:
        """
        Save a dataset and its metadata to the database.

        If the dataset already exists (based on ID), it will be updated.
        Otherwise, a new record is created.

        Args:
            dataset: Dataset entity to persist
            metadata: Metadata entity associated with the dataset

        Returns:
            str: The UUID of the saved dataset

        Raises:
            RepositoryError: If save operation fails

        Example:
            >>> repo = SQLiteDatasetRepository(session)
            >>> dataset = Dataset(title="My Dataset")
            >>> metadata = Metadata(title="My Dataset", abstract="...")
            >>> dataset_id = repo.save(dataset, metadata)
        """
        try:
            dataset_id = str(dataset.id)

            # Check if dataset already exists
            existing = self.session.query(DatasetModel).filter_by(id=dataset_id).first()

            if existing:
                # Update existing dataset
                logger.info(f"Updating existing dataset: {dataset_id}")
                self._update_dataset_model(existing, dataset)

                # Update metadata
                if existing.dataset_metadata:
                    self._update_metadata_model(existing.dataset_metadata, metadata)
                else:
                    metadata_model = self._create_metadata_model(metadata, dataset_id)
                    self.session.add(metadata_model)

            else:
                # Create new dataset
                logger.info(f"Creating new dataset: {dataset_id}")
                dataset_model = self._create_dataset_model(dataset)
                metadata_model = self._create_metadata_model(metadata, dataset_id)

                self.session.add(dataset_model)
                self.session.add(metadata_model)

            # Commit transaction
            self.session.commit()
            logger.info(f"Successfully saved dataset: {dataset_id}")

            return dataset_id

        except IntegrityError as e:
            self.session.rollback()
            logger.error(f"Integrity error saving dataset: {str(e)}")
            raise RepositoryError(f"Database integrity error: {str(e)}")

        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Database error saving dataset: {str(e)}")
            raise RepositoryError(f"Database error: {str(e)}")

        except Exception as e:
            self.session.rollback()
            logger.error(f"Unexpected error saving dataset: {str(e)}")
            raise RepositoryError(f"Unexpected error: {str(e)}")

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
        """
        try:
            dataset_model = self.session.query(DatasetModel).filter_by(id=dataset_id).first()

            if not dataset_model or not dataset_model.dataset_metadata:
                return None

            dataset = self._to_dataset_entity(dataset_model)
            metadata = self._to_metadata_entity(dataset_model.dataset_metadata)

            logger.debug(f"Retrieved dataset: {dataset_id}")
            return (dataset, metadata)

        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving dataset {dataset_id}: {str(e)}")
            raise RepositoryError(f"Database error: {str(e)}")

    def exists(self, dataset_id: str) -> bool:
        """
        Check if a dataset exists in the database.

        Args:
            dataset_id: UUID string of the dataset to check

        Returns:
            bool: True if dataset exists, False otherwise
        """
        try:
            count = self.session.query(DatasetModel).filter_by(id=dataset_id).count()
            return count > 0
        except SQLAlchemyError as e:
            logger.error(f"Database error checking existence of {dataset_id}: {str(e)}")
            raise RepositoryError(f"Database error: {str(e)}")

    def get_all(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[tuple[Dataset, Metadata]]:
        """
        Retrieve all datasets with optional pagination.

        Args:
            limit: Maximum number of datasets to return
            offset: Number of datasets to skip

        Returns:
            List of (Dataset, Metadata) tuples
        """
        try:
            query = self.session.query(DatasetModel).order_by(DatasetModel.created_at.desc())

            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)

            dataset_models = query.all()

            results = []
            for dataset_model in dataset_models:
                if dataset_model.dataset_metadata:
                    dataset = self._to_dataset_entity(dataset_model)
                    metadata = self._to_metadata_entity(dataset_model.dataset_metadata)
                    results.append((dataset, metadata))

            logger.debug(f"Retrieved {len(results)} datasets")
            return results

        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving datasets: {str(e)}")
            raise RepositoryError(f"Database error: {str(e)}")

    def search_by_title(self, title_query: str) -> List[tuple[Dataset, Metadata]]:
        """
        Search datasets by title (case-insensitive partial match).

        Args:
            title_query: Search string to match against titles

        Returns:
            List of (Dataset, Metadata) tuples matching the query
        """
        try:
            dataset_models = self.session.query(DatasetModel).filter(
                DatasetModel.title.ilike(f'%{title_query}%')
            ).all()

            results = []
            for dataset_model in dataset_models:
                if dataset_model.dataset_metadata:
                    dataset = self._to_dataset_entity(dataset_model)
                    metadata = self._to_metadata_entity(dataset_model.dataset_metadata)
                    results.append((dataset, metadata))

            logger.debug(f"Found {len(results)} datasets matching '{title_query}'")
            return results

        except SQLAlchemyError as e:
            logger.error(f"Database error searching datasets: {str(e)}")
            raise RepositoryError(f"Database error: {str(e)}")

    def delete(self, dataset_id: str) -> bool:
        """
        Delete a dataset and its metadata from the database.

        Args:
            dataset_id: UUID string of the dataset to delete

        Returns:
            bool: True if deleted, False if not found
        """
        try:
            dataset_model = self.session.query(DatasetModel).filter_by(id=dataset_id).first()

            if not dataset_model:
                return False

            self.session.delete(dataset_model)
            self.session.commit()

            logger.info(f"Deleted dataset: {dataset_id}")
            return True

        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Database error deleting dataset {dataset_id}: {str(e)}")
            raise RepositoryError(f"Database error: {str(e)}")

    def count(self) -> int:
        """
        Count total number of datasets in the database.

        Returns:
            int: Total count of datasets
        """
        try:
            return self.session.query(DatasetModel).count()
        except SQLAlchemyError as e:
            logger.error(f"Database error counting datasets: {str(e)}")
            raise RepositoryError(f"Database error: {str(e)}")

    # Private helper methods for entity/model conversion

    def _create_dataset_model(self, dataset: Dataset) -> DatasetModel:
        """Create a DatasetModel from a Dataset entity."""
        return DatasetModel(
            id=str(dataset.id),
            title=dataset.title,
            abstract=dataset.abstract,
            metadata_url=dataset.metadata_url,
            last_updated=dataset.last_updated,
            created_at=dataset.created_at
        )

    def _update_dataset_model(self, model: DatasetModel, dataset: Dataset):
        """Update a DatasetModel with data from a Dataset entity."""
        model.title = dataset.title
        model.abstract = dataset.abstract
        model.metadata_url = dataset.metadata_url
        model.last_updated = dataset.last_updated

    def _create_metadata_model(self, metadata: Metadata, dataset_id: str) -> MetadataModel:
        """Create a MetadataModel from a Metadata entity."""
        model = MetadataModel(
            dataset_id=dataset_id,
            title=metadata.title,
            abstract=metadata.abstract,
            contact_organization=metadata.contact_organization,
            contact_email=metadata.contact_email,
            metadata_date=metadata.metadata_date,
            dataset_language=metadata.dataset_language,
            topic_category=metadata.topic_category,
            temporal_extent_start=metadata.temporal_extent_start,
            temporal_extent_end=metadata.temporal_extent_end
        )

        # Set keywords using helper method
        model.set_keywords(metadata.keywords)

        # Set bounding box if present
        if metadata.bounding_box:
            bbox_dict = {
                'west': metadata.bounding_box.west_longitude,
                'east': metadata.bounding_box.east_longitude,
                'south': metadata.bounding_box.south_latitude,
                'north': metadata.bounding_box.north_latitude
            }
            model.set_bounding_box(bbox_dict)

        return model

    def _update_metadata_model(self, model: MetadataModel, metadata: Metadata):
        """Update a MetadataModel with data from a Metadata entity."""
        model.title = metadata.title
        model.abstract = metadata.abstract
        model.contact_organization = metadata.contact_organization
        model.contact_email = metadata.contact_email
        model.metadata_date = metadata.metadata_date
        model.dataset_language = metadata.dataset_language
        model.topic_category = metadata.topic_category
        model.temporal_extent_start = metadata.temporal_extent_start
        model.temporal_extent_end = metadata.temporal_extent_end

        # Update keywords
        model.set_keywords(metadata.keywords)

        # Update bounding box
        if metadata.bounding_box:
            bbox_dict = {
                'west': metadata.bounding_box.west_longitude,
                'east': metadata.bounding_box.east_longitude,
                'south': metadata.bounding_box.south_latitude,
                'north': metadata.bounding_box.north_latitude
            }
            model.set_bounding_box(bbox_dict)
        else:
            model.set_bounding_box(None)

    def _to_dataset_entity(self, model: DatasetModel) -> Dataset:
        """Convert a DatasetModel to a Dataset entity."""
        return Dataset(
            id=UUID(model.id),
            title=model.title,
            abstract=model.abstract,
            metadata_url=model.metadata_url,
            last_updated=model.last_updated,
            created_at=model.created_at
        )

    def _to_metadata_entity(self, model: MetadataModel) -> Metadata:
        """Convert a MetadataModel to a Metadata entity."""
        # Get bounding box
        bounding_box = None
        bbox_dict = model.get_bounding_box()
        if bbox_dict:
            try:
                bounding_box = BoundingBox(
                    west_longitude=bbox_dict['west'],
                    east_longitude=bbox_dict['east'],
                    south_latitude=bbox_dict['south'],
                    north_latitude=bbox_dict['north']
                )
            except (KeyError, ValueError) as e:
                logger.warning(f"Invalid bounding box data: {str(e)}")

        # Create metadata entity
        return Metadata(
            title=model.title,
            abstract=model.abstract,
            keywords=model.get_keywords(),
            bounding_box=bounding_box,
            temporal_extent_start=model.temporal_extent_start,
            temporal_extent_end=model.temporal_extent_end,
            contact_organization=model.contact_organization or "",
            contact_email=model.contact_email or "",
            metadata_date=model.metadata_date,
            dataset_language=model.dataset_language or "eng",
            topic_category=model.topic_category or ""
        )

    def __repr__(self):
        """Return string representation."""
        return f"SQLiteDatasetRepository(session={self.session})"
