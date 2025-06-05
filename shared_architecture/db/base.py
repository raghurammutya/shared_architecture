"""
Base Module for SQLAlchemy Declarative Models

Defines the Base class for declarative SQLAlchemy models.
Dynamically sets __tablename__ based on class name.
"""

from sqlalchemy.ext.declarative import as_declarative, declared_attr

@as_declarative()
class Base:
    """
    Declarative base class for all SQLAlchemy ORM models.

    Automatically generates __tablename__ based on class name.
    """

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()  # type: ignore[attr-defined]
