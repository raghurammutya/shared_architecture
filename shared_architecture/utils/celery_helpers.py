"""
Celery Helper Utilities

This module provides utilities for Celery tasks that need database access
and other common patterns used across microservices.
"""

import os
import logging
from contextlib import contextmanager
from typing import Generator, Optional, Any, Dict
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine

from shared_architecture.utils.enhanced_logging import get_logger
from shared_architecture.connections.service_discovery import service_discovery, ServiceType

logger = get_logger(__name__)

class CeleryDatabaseHelper:
    """
    Helper class for managing database connections in Celery tasks.
    
    Provides synchronous database sessions specifically designed for Celery tasks,
    which run in separate processes and need their own database connections.
    """
    
    def __init__(self):
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
    
    def _get_database_url(self) -> str:
        """Get database URL with service discovery support."""
        db_user = os.getenv("TIMESCALEDB_USER", "tradmin")
        db_password = os.getenv("TIMESCALEDB_PASSWORD", "tradpass")
        db_host = os.getenv("TIMESCALEDB_HOST", "timescaledb")
        db_port = os.getenv("TIMESCALEDB_PORT", "5432")
        db_name = os.getenv("TIMESCALEDB_DB", "tradingdb")
        
        # Try to resolve host via service discovery
        try:
            resolved_host = service_discovery.resolve_service_host(db_host, ServiceType.TIMESCALEDB)
            db_host = resolved_host
            self.logger.info(f"Database host resolved via service discovery: {db_host}")
        except Exception as e:
            self.logger.warning(f"Service discovery failed for database host, using configured value: {e}")
        
        return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    def _initialize_engine(self):
        """Initialize SQLAlchemy engine if not already done."""
        if self._engine is None:
            database_url = self._get_database_url()
            
            # Configure engine for Celery tasks
            self._engine = create_engine(
                database_url,
                pool_size=int(os.getenv("CELERY_DB_POOL_SIZE", "5")),
                max_overflow=int(os.getenv("CELERY_DB_MAX_OVERFLOW", "10")),
                pool_pre_ping=True,  # Validate connections before use
                pool_recycle=int(os.getenv("CELERY_DB_POOL_RECYCLE", "3600")),  # 1 hour
                echo=os.getenv("CELERY_DB_ECHO", "false").lower() == "true"
            )
            
            self._session_factory = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self._engine
            )
            
            self.logger.info("Celery database engine initialized")
    
    def get_session(self) -> Session:
        """
        Get a synchronous database session for Celery tasks.
        
        Returns:
            SQLAlchemy Session instance
            
        Note:
            This method returns an actual Session instance, not a sessionmaker.
            The caller is responsible for closing the session.
        """
        self._initialize_engine()
        session = self._session_factory()
        return session
    
    @contextmanager
    def get_session_context(self) -> Generator[Session, None, None]:
        """
        Get a database session with automatic cleanup.
        
        Usage:
            with celery_helper.get_session_context() as session:
                # Use session here
                result = session.query(Model).all()
        
        Yields:
            SQLAlchemy Session instance that will be automatically closed
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            self.logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def execute_in_session(self, func, *args, **kwargs) -> Any:
        """
        Execute a function with a database session.
        
        Args:
            func: Function to execute that takes session as first parameter
            *args: Additional positional arguments for the function
            **kwargs: Additional keyword arguments for the function
            
        Returns:
            Result of the function execution
            
        Example:
            def my_query(session, user_id):
                return session.query(User).filter_by(id=user_id).first()
            
            user = celery_helper.execute_in_session(my_query, user_id=123)
        """
        with self.get_session_context() as session:
            return func(session, *args, **kwargs)
    
    def test_connection(self) -> bool:
        """
        Test the database connection.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            with self.get_session_context() as session:
                session.execute("SELECT 1")
            return True
        except Exception as e:
            self.logger.error(f"Database connection test failed: {e}")
            return False
    
    def get_engine_info(self) -> Dict[str, Any]:
        """
        Get information about the database engine.
        
        Returns:
            Dictionary with engine information
        """
        self._initialize_engine()
        
        return {
            "url": str(self._engine.url),
            "pool_size": self._engine.pool.size(),
            "checked_in": self._engine.pool.checkedin(),
            "checked_out": self._engine.pool.checkedout(),
            "overflow": self._engine.pool.overflow(),
            "is_valid": self.test_connection()
        }

# Global instance
celery_db_helper = CeleryDatabaseHelper()

# Convenience functions
def get_celery_db_session() -> Session:
    """
    Get a synchronous database session for Celery tasks.
    
    Returns:
        SQLAlchemy Session instance
        
    Note:
        This is a convenience function that delegates to the global helper instance.
        The caller is responsible for closing the session.
    """
    return celery_db_helper.get_session()

@contextmanager
def celery_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions in Celery tasks.
    
    Usage:
        with celery_db_session() as session:
            # Use session here
            result = session.query(Model).all()
    
    Yields:
        SQLAlchemy Session instance that will be automatically closed
    """
    with celery_db_helper.get_session_context() as session:
        yield session

def execute_with_db(func, *args, **kwargs) -> Any:
    """
    Execute a function with a database session.
    
    Args:
        func: Function to execute that takes session as first parameter
        *args: Additional positional arguments for the function
        **kwargs: Additional keyword arguments for the function
        
    Returns:
        Result of the function execution
    """
    return celery_db_helper.execute_in_session(func, *args, **kwargs)

class CeleryTaskMixin:
    """
    Mixin class for Celery tasks that need database access.
    
    Usage:
        from celery import Task
        
        class MyTask(CeleryTaskMixin, Task):
            def run(self, *args, **kwargs):
                with self.db_session() as session:
                    # Use session here
                    pass
    """
    
    @property
    def db_helper(self) -> CeleryDatabaseHelper:
        """Get the database helper instance."""
        return celery_db_helper
    
    def db_session(self):
        """Get a database session context manager."""
        return self.db_helper.get_session_context()
    
    def execute_with_db(self, func, *args, **kwargs) -> Any:
        """Execute a function with a database session."""
        return self.db_helper.execute_in_session(func, *args, **kwargs)

# Decorators for Celery tasks
def with_db_session(func):
    """
    Decorator that provides a database session to Celery tasks.
    
    The decorated function will receive 'session' as the first parameter.
    
    Usage:
        @celery_app.task
        @with_db_session
        def my_task(session, user_id):
            user = session.query(User).get(user_id)
            # ... process user
    """
    def wrapper(*args, **kwargs):
        with celery_db_session() as session:
            return func(session, *args, **kwargs)
    
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper

def with_error_handling(func):
    """
    Decorator that adds error handling and logging to Celery tasks.
    
    Usage:
        @celery_app.task
        @with_error_handling
        def my_task(*args, **kwargs):
            # Task implementation
            pass
    """
    def wrapper(*args, **kwargs):
        task_name = func.__name__
        logger.info(f"Starting Celery task: {task_name}")
        
        try:
            result = func(*args, **kwargs)
            logger.info(f"Celery task completed successfully: {task_name}")
            return result
        except Exception as e:
            logger.error(f"Celery task failed: {task_name} - {e}", exc_info=True)
            raise
    
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper

def with_retry(max_retries=3, countdown=60):
    """
    Decorator that adds retry logic to Celery tasks.
    
    Args:
        max_retries: Maximum number of retry attempts
        countdown: Delay between retries in seconds
    
    Usage:
        @celery_app.task
        @with_retry(max_retries=5, countdown=30)
        def my_task(*args, **kwargs):
            # Task implementation that might fail
            pass
    """
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                logger.warning(f"Task {func.__name__} failed (attempt {self.request.retries + 1}): {e}")
                
                if self.request.retries < max_retries:
                    raise self.retry(countdown=countdown, exc=e, max_retries=max_retries)
                else:
                    logger.error(f"Task {func.__name__} failed permanently after {max_retries} retries")
                    raise
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    
    return decorator