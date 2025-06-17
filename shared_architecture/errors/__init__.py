"""
Database Package Initialization

This module initializes the shared_architecture.db package. It exposes utilities for
database session management and repository patterns for data access.

Exports:
    - get_db: A generator that provides a SQLAlchemy database session.
    - BaseRepository: A base class for implementing repository patterns.
"""
from .custom_exceptions import ServiceUnavailableError
from .ledger_exceptions import LedgerEntryValidationError,LedgerFileParsingError,LedgerProcessingError  # Adjust the module name if necessary

__all__ = ["ServiceUnavailableError",
           "LedgerEntryValidationError",
           "LedgerFileParsingError",
           "LedgerProcessingError",
           ]

