"""
Repository Module

This module implements the repository pattern for data access. It provides a
base repository class that abstracts database query operations using SQLAlchemy.
"""

class BaseRepository:
    """
    Base Repository Class

    This class provides a generic interface for interacting with the database.
    It supports basic CRUD operations and filtering using SQLAlchemy sessions.
    """

    def __init__(self, session):
        """
        Initialize the repository with a database session.

        Args:
            session (sqlalchemy.orm.Session): The SQLAlchemy session to use for database operations.
        """
        self.session = session

    def get(self, model, filters):
        """
        Retrieve records from the database.

        Args:
            model: The SQLAlchemy model to query.
            filters: A list of SQLAlchemy filter expressions to apply.

        Returns:
            List: A list of model instances matching the filters.
        """
        return self.session.query(model).filter(*filters).all()

    def add(self, model_instance):
        """
        Add a new record to the database.

        Args:
            model_instance: An instance of the SQLAlchemy model to add.

        Returns:
            None
        """
        self.session.add(model_instance)
        self.session.commit()

# Add a blank line at the end for PEP 8 compliance