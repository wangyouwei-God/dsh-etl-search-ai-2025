"""
Infrastructure: Database Connection Management

This module handles SQLite database connections and sessions using SQLAlchemy.
It provides connection pooling, session management, and database initialization.

Author: University of Manchester RSE Team
"""

import os
import logging
from pathlib import Path
from typing import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from .models import Base, create_tables

# Configure logging
logger = logging.getLogger(__name__)


class DatabaseConnection:
    """
    Database connection manager for SQLite.

    This class manages the SQLAlchemy engine and session factory,
    providing connection pooling and session lifecycle management.

    Design Pattern: Singleton (single engine per database path)

    Attributes:
        db_path: Path to the SQLite database file
        engine: SQLAlchemy engine instance
        SessionLocal: Session factory for creating database sessions
    """

    def __init__(
        self,
        db_path: str = "datasets.db",
        echo: bool = False,
        create_db: bool = True
    ):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file (default: datasets.db)
            echo: If True, log all SQL statements (for debugging)
            create_db: If True, create tables if they don't exist

        Example:
            >>> db = DatabaseConnection("datasets.db")
            >>> session = db.get_session()
        """
        self.db_path = db_path
        self.echo = echo

        # Create database directory if it doesn't exist
        db_file = Path(db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

        # Create SQLAlchemy engine
        # Use check_same_thread=False for SQLite to allow multi-threading
        # Use StaticPool for better connection management
        self.engine = create_engine(
            f'sqlite:///{db_path}',
            echo=echo,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,  # Use single connection pool for SQLite
        )

        # Enable foreign key support for SQLite
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

        # Create tables if requested
        if create_db:
            self.create_tables()

        logger.info(f"Database connection initialized: {db_path}")

    def create_tables(self):
        """
        Create all tables defined in models.

        This method is idempotent - it will not recreate existing tables.
        """
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {str(e)}")
            raise

    def drop_tables(self):
        """
        Drop all tables from the database.

        Warning:
            This will delete all data! Use with caution.
        """
        Base.metadata.drop_all(bind=self.engine)
        logger.warning("All database tables dropped")

    def get_session(self) -> Session:
        """
        Get a new database session.

        Returns:
            Session: SQLAlchemy session instance

        Note:
            The caller is responsible for closing the session.

        Example:
            >>> db = DatabaseConnection()
            >>> session = db.get_session()
            >>> try:
            ...     # Use session
            ...     session.query(DatasetModel).all()
            ... finally:
            ...     session.close()
        """
        return self.SessionLocal()

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        Provide a transactional scope around a series of operations.

        This is a context manager that automatically commits or rolls back
        transactions and closes the session.

        Yields:
            Session: SQLAlchemy session instance

        Example:
            >>> db = DatabaseConnection()
            >>> with db.session_scope() as session:
            ...     dataset = session.query(DatasetModel).first()
            ...     # Session automatically committed and closed
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database transaction failed: {str(e)}")
            raise
        finally:
            session.close()

    def close(self):
        """
        Close the database connection and dispose of the engine.

        This should be called when the application shuts down.
        """
        if self.engine:
            self.engine.dispose()
            logger.info("Database connection closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close connection."""
        self.close()

    def __repr__(self):
        """Return string representation."""
        return f"DatabaseConnection(db_path='{self.db_path}')"


# Global database instance (singleton pattern)
_db_instance = None


def get_database(
    db_path: str = "datasets.db",
    echo: bool = False,
    create_db: bool = True
) -> DatabaseConnection:
    """
    Get or create a singleton database connection instance.

    Args:
        db_path: Path to SQLite database file
        echo: If True, log all SQL statements
        create_db: If True, create tables if they don't exist

    Returns:
        DatabaseConnection: Singleton database connection instance

    Example:
        >>> db = get_database()
        >>> with db.session_scope() as session:
        ...     # Use session
        ...     pass
    """
    global _db_instance

    if _db_instance is None:
        _db_instance = DatabaseConnection(
            db_path=db_path,
            echo=echo,
            create_db=create_db
        )

    return _db_instance


def reset_database(db_path: str = "datasets.db"):
    """
    Reset the database by dropping and recreating all tables.

    Warning:
        This will delete all data! Use with caution.

    Args:
        db_path: Path to SQLite database file

    Example:
        >>> reset_database("test_datasets.db")
    """
    db = DatabaseConnection(db_path, create_db=False)
    db.drop_tables()
    db.create_tables()
    db.close()
    logger.info(f"Database reset completed: {db_path}")


# Convenience function for getting a session
def get_session(db_path: str = "datasets.db") -> Session:
    """
    Convenience function to get a database session.

    Args:
        db_path: Path to SQLite database file

    Returns:
        Session: SQLAlchemy session instance

    Note:
        Caller must close the session when done.

    Example:
        >>> session = get_session()
        >>> try:
        ...     datasets = session.query(DatasetModel).all()
        ... finally:
        ...     session.close()
    """
    db = get_database(db_path)
    return db.get_session()
