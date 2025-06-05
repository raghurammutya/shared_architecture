"""
Base Module for SQLAlchemy Declarative Models

This file defines the `Base` class to be used as the declarative base for all ORM models.
It dynamically generates the `__tablename__` attribute for models based on their class names.
"""

from sqlalchemy.ext.declarative import as_declarative, declared_attr

@as_declarative()
class Base:
    """
    Declarative base class for SQLAlchemy models.

    This class dynamically generates the `__tablename__` attribute for
    derived models based on their class names.
    """
    if False:  # For type checking and Pylint
        __name__: str

    @declared_attr  # pylint: disable=no-self-argument,no-member
    def __tablename__(cls):
        return cls.__name__.lower()