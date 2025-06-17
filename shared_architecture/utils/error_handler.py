# shared_architecture/utils/error_handler.py
import traceback
from typing import Dict, Any, Optional, Union, Tuple
from functools import wraps
from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
import asyncio

from shared_architecture.exceptions.trade_exceptions import (
    BaseTradeException, ErrorCategory, ErrorSeverity, ErrorContext,
    DatabaseException, NetworkException, AutoTraderException,
    ValidationException, ConfigurationException
)
from shared_architecture.utils.enhanced_logging import get_logger, LoggingContext

logger = get_logger(__name__)

class ErrorHandler:
    """Centralized error handling for the trade service"""
    
    @staticmethod
    def handle_exception(
        exception: Exception,
        context: ErrorContext = None,
        default_message: str = "An unexpected error occurred"
    ) -> BaseTradeException:
        """
        Convert any exception to a BaseTradeException with proper categorization
        """
        if isinstance(exception, BaseTradeException):
            return exception
        
        # Database exceptions
        if isinstance(exception, SQLAlchemyError):
            return ErrorHandler._handle_database_exception(exception, context)
        
        # HTTP/Network exceptions
        if isinstance(exception, (ConnectionError, TimeoutError, OSError)):
            return ErrorHandler._handle_network_exception(exception, context)
        
        # Validation exceptions
        if isinstance(exception, (ValueError, TypeError)):
            return ErrorHandler._handle_validation_exception(exception, context)
        
        # AsyncIO exceptions
        if isinstance(exception, asyncio.TimeoutError):
            return NetworkException(
                "Operation timed out",
                timeout=True,
                context=context,
                original_exception=exception
            )
        
        # Generic exception - treat as system error
        return BaseTradeException(
            message=str(exception) or default_message,
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.HIGH,
            context=context,
            original_exception=exception
        )
    
    @staticmethod
    def _handle_database_exception(exception: SQLAlchemyError, context: ErrorContext) -> DatabaseException:
        """Handle SQLAlchemy exceptions"""
        operation = "unknown"
        table = "unknown"
        
        # Extract operation details from exception
        if hasattr(exception, 'statement') and exception.statement:
            statement = str(exception.statement).upper()
            if 'INSERT' in statement:
                operation = "insert"
            elif 'UPDATE' in statement:
                operation = "update"
            elif 'DELETE' in statement:
                operation = "delete"
            elif 'SELECT' in statement:
                operation = "select"
        
        # Specific handling for different types
        if isinstance(exception, IntegrityError):
            message = "Data integrity constraint violation"
            severity = ErrorSeverity.HIGH
        elif isinstance(exception, OperationalError):
            message = "Database connection or operation error"
            severity = ErrorSeverity.CRITICAL
        else:
            message = f"Database error: {str(exception)}"
            severity = ErrorSeverity.HIGH
        
        return DatabaseException(
            message=message,
            operation=operation,
            table=table,
            context=context,
            original_exception=exception,
            severity=severity
        )
    
    @staticmethod
    def _handle_network_exception(exception: Exception, context: ErrorContext) -> NetworkException:
        """Handle network-related exceptions"""
        timeout = isinstance(exception, TimeoutError)
        message = f"Network error: {str(exception)}"
        
        return NetworkException(
            message=message,
            timeout=timeout,
            context=context,
            original_exception=exception
        )
    
    @staticmethod
    def _handle_validation_exception(exception: Exception, context: ErrorContext) -> ValidationException:
        """Handle validation exceptions"""
        message = f"Validation error: {str(exception)}"
        
        return ValidationException(
            message=message,
            context=context,
            original_exception=exception
        )
    
    @staticmethod
    async def log_and_handle_exception(
        exception: Exception,
        context: ErrorContext = None,
        correlation_id: str = None
    ) -> BaseTradeException:
        """
        Log exception and convert to BaseTradeException
        """
        # Create logging context
        with LoggingContext(
            correlation_id=correlation_id,
            user_id=context.user_id if context else None,
            organization_id=context.organization_id if context else None
        ):
            # Convert to BaseTradeException
            trade_exception = ErrorHandler.handle_exception(exception, context)
            
            # Log based on severity
            if trade_exception.severity == ErrorSeverity.CRITICAL:
                logger.critical(
                    trade_exception.message,
                    error_code=trade_exception.error_code,
                    category=trade_exception.category.value,
                    exception_details=trade_exception.to_dict(),
                    exc_info=True
                )
            elif trade_exception.severity == ErrorSeverity.HIGH:
                logger.error(
                    trade_exception.message,
                    error_code=trade_exception.error_code,
                    category=trade_exception.category.value,
                    exception_details=trade_exception.to_dict(),
                    exc_info=True
                )
            elif trade_exception.severity == ErrorSeverity.MEDIUM:
                logger.warning(
                    trade_exception.message,
                    error_code=trade_exception.error_code,
                    category=trade_exception.category.value,
                    exception_details=trade_exception.to_dict()
                )
            else:
                logger.info(
                    trade_exception.message,
                    error_code=trade_exception.error_code,
                    category=trade_exception.category.value,
                    exception_details=trade_exception.to_dict()
                )
            
            return trade_exception

def handle_errors(
    default_message: str = "An error occurred",
    context_fields: list = None
):
    """
    Decorator for automatic error handling in functions
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Extract context from kwargs
            context = ErrorContext()
            if context_fields:
                for field in context_fields:
                    if field in kwargs:
                        setattr(context, field, kwargs[field])
            
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                trade_exception = await ErrorHandler.log_and_handle_exception(
                    e, context, default_message
                )
                raise trade_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Extract context from kwargs
            context = ErrorContext()
            if context_fields:
                for field in context_fields:
                    if field in kwargs:
                        setattr(context, field, kwargs[field])
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # For sync functions, we can't use async log_and_handle_exception
                trade_exception = ErrorHandler.handle_exception(e, context, default_message)
                
                # Log synchronously
                logger.error(
                    trade_exception.message,
                    error_code=trade_exception.error_code,
                    category=trade_exception.category.value,
                    exception_details=trade_exception.to_dict(),
                    exc_info=True
                )
                
                raise trade_exception
        
        # Return appropriate wrapper
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

# FastAPI Exception Handlers
async def trade_exception_handler(request: Request, exc: BaseTradeException) -> JSONResponse:
    """FastAPI exception handler for BaseTradeException"""
    
    # Log the exception
    logger.error(
        f"Handled trade exception: {exc.message}",
        error_code=exc.error_code,
        category=exc.category.value,
        severity=exc.severity.value,
        path=str(request.url),
        method=request.method,
        exception_details=exc.to_dict()
    )
    
    # Return structured error response
    response_data = {
        "error": {
            "code": exc.error_code,
            "message": exc.user_message,
            "category": exc.category.value,
            "severity": exc.severity.value,
            "correlation_id": exc.context.correlation_id
        }
    }
    
    # Add retry information if applicable
    if exc.retry_after:
        response_data["retry_after"] = exc.retry_after
    
    return JSONResponse(
        status_code=exc.http_status_code,
        content=response_data,
        headers={"Retry-After": str(exc.retry_after)} if exc.retry_after else {}
    )

async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """FastAPI exception handler for generic exceptions"""
    
    # Convert to trade exception
    context = ErrorContext(
        endpoint=str(request.url.path),
        additional_data={
            "method": request.method,
            "query_params": dict(request.query_params)
        }
    )
    
    trade_exception = await ErrorHandler.log_and_handle_exception(exc, context)
    
    # Use the trade exception handler
    return await trade_exception_handler(request, trade_exception)

async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """FastAPI exception handler for HTTPException"""
    
    # Convert HTTPException to BaseTradeException
    if exc.status_code == 400:
        category = ErrorCategory.VALIDATION
        severity = ErrorSeverity.LOW
    elif exc.status_code == 401:
        category = ErrorCategory.AUTHENTICATION
        severity = ErrorSeverity.MEDIUM
    elif exc.status_code == 403:
        category = ErrorCategory.AUTHORIZATION
        severity = ErrorSeverity.MEDIUM
    elif exc.status_code == 404:
        category = ErrorCategory.VALIDATION
        severity = ErrorSeverity.LOW
    elif exc.status_code == 429:
        category = ErrorCategory.RATE_LIMITING
        severity = ErrorSeverity.MEDIUM
    else:
        category = ErrorCategory.SYSTEM
        severity = ErrorSeverity.HIGH
    
    context = ErrorContext(
        endpoint=str(request.url.path),
        additional_data={
            "method": request.method,
            "status_code": exc.status_code
        }
    )
    
    trade_exception = BaseTradeException(
        message=str(exc.detail) if exc.detail else "HTTP error",
        category=category,
        severity=severity,
        http_status_code=exc.status_code,
        context=context,
        original_exception=exc
    )
    
    return await trade_exception_handler(request, trade_exception)

# Context managers for error handling
class ErrorContext:
    """Context manager for setting error context"""
    
    def __init__(self, **context_data):
        self.context_data = context_data
        self.context = ErrorContext(**context_data)
    
    def __enter__(self):
        return self.context
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type and not isinstance(exc_val, BaseTradeException):
            # Convert exception to BaseTradeException
            trade_exception = ErrorHandler.handle_exception(exc_val, self.context)
            
            # Log the exception
            logger.error(
                trade_exception.message,
                error_code=trade_exception.error_code,
                category=trade_exception.category.value,
                exception_details=trade_exception.to_dict(),
                exc_info=True
            )
            
            # Replace the original exception
            raise trade_exception from exc_val
        
        return False  # Don't suppress exceptions

# Utility functions for common error scenarios
def validate_required_fields(data: Dict[str, Any], required_fields: list) -> None:
    """Validate that required fields are present and not None"""
    missing_fields = []
    for field in required_fields:
        if field not in data or data[field] is None:
            missing_fields.append(field)
    
    if missing_fields:
        raise ValidationException(
            f"Missing required fields: {', '.join(missing_fields)}",
            field_name=missing_fields[0] if len(missing_fields) == 1 else None
        )

def validate_field_types(data: Dict[str, Any], field_types: Dict[str, type]) -> None:
    """Validate that fields have correct types"""
    for field, expected_type in field_types.items():
        if field in data and data[field] is not None:
            if not isinstance(data[field], expected_type):
                raise ValidationException(
                    f"Field '{field}' must be of type {expected_type.__name__}, got {type(data[field]).__name__}",
                    field_name=field,
                    field_value=data[field]
                )

def create_error_context(
    correlation_id: str = None,
    user_id: str = None,
    organization_id: str = None,
    order_id: str = None,
    symbol: str = None,
    endpoint: str = None,
    **additional_data
) -> ErrorContext:
    """Create an error context with common fields"""
    return ErrorContext(
        correlation_id=correlation_id,
        user_id=user_id,
        organization_id=organization_id,
        order_id=order_id,
        symbol=symbol,
        endpoint=endpoint,
        additional_data=additional_data if additional_data else None
    )