
"""
Base Module for SQLAlchemy Declarative Models

Defines the Base class for declarative SQLAlchemy models.
"""

from sqlalchemy.ext.declarative import declarative_base

# Simple declarative base that allows normal table naming
Base = declarative_base()