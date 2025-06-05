"""
Database Package Initialization

This module initializes the shared_architecture.db package. It exposes utilities for
database session management and repository patterns for data access.

Exports:
    - get_db: A generator that provides a SQLAlchemy database session.
    - BaseRepository: A base class for implementing repository patterns.
"""
from .repository import BaseRepository
from .session import get_db  # Adjust the module name if necessary

__all__ = ["BaseRepository", "get_db"]

