# shared_architecture/utils/enhanced_logging.py
import logging
import json
import uuid
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, Union
from functools import wraps
from contextvars import ContextVar
import sys

# Context variables for request correlation
correlation_id_var: ContextVar[str] = ContextVar('correlation_id', default='')
user_id_var: ContextVar[str] = ContextVar('user_id', default='')
organization_id_var: ContextVar[str] = ContextVar('organization_id', default='')

class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured JSON logs with correlation tracking.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        # Base log structure
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'service': 'trade_service',
            'correlation_id': correlation_id_var.get(''),
            'user_id': user_id_var.get(''),
            'organization_id': organization_id_var.get(''),
        }
        
        # Add extra fields if present
        if hasattr(record, 'extra') and record.extra:
            log_entry.update(record.extra)
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add function/file info for debug logs
        if record.levelno <= logging.DEBUG:
            log_entry['source'] = {
                'file': record.pathname,
                'function': record.funcName,
                'line': record.lineno
            }
        
        return json.dumps(log_entry)

class TradeServiceLogger:
    """
    Enhanced logger for trade service with structured logging and context tracking.
    """
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    def _setup_logger(self):
        """Setup logger with structured formatting"""
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(StructuredFormatter())
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def set_correlation_id(self, correlation_id: str):
        """Set correlation ID for request tracking"""
        correlation_id_var.set(correlation_id)
    
    def set_user_context(self, user_id: str = None, organization_id: str = None):
        """Set user context for logging"""
        if user_id:
            user_id_var.set(user_id)
        if organization_id:
            organization_id_var.set(organization_id)
    
    def info(self, message: str, **kwargs):
        """Log info message with extra context"""
        self.logger.info(message, extra=kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message with extra context"""
        self.logger.error(message, extra=kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with extra context"""
        self.logger.warning(message, extra=kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with extra context"""
        self.logger.debug(message, extra=kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message with extra context"""
        self.logger.critical(message, extra=kwargs)
    
    def log_order_event(self, order_id: str, event: str, details: Dict[str, Any] = None):
        """Specialized logging for order events"""
        self.info(
            f"Order event: {event}",
            order_id=order_id,
            event_type=event,
            event_details=details or {},
            category="order_lifecycle"
        )
    
    def log_api_call(self, service: str, method: str, duration_ms: float, success: bool, **kwargs):
        """Specialized logging for external API calls"""
        self.info(
            f"API call to {service}.{method}",
            service=service,
            method=method,
            duration_ms=duration_ms,
            success=success,
            category="api_call",
            **kwargs
        )
    
    def log_business_event(self, event_type: str, details: Dict[str, Any]):
        """Log business-critical events"""
        self.info(
            f"Business event: {event_type}",
            event_type=event_type,
            event_details=details,
            category="business_event"
        )
    
    def log_security_event(self, event_type: str, details: Dict[str, Any]):
        """Log security-related events"""
        self.warning(
            f"Security event: {event_type}",
            event_type=event_type,
            event_details=details,
            category="security_event"
        )
    
    def log_performance_metric(self, metric_name: str, value: Union[int, float], unit: str = None):
        """Log performance metrics"""
        self.info(
            f"Performance metric: {metric_name}",
            metric_name=metric_name,
            metric_value=value,
            metric_unit=unit,
            category="performance"
        )
    
    def log_data_consistency_issue(self, issue_type: str, details: Dict[str, Any]):
        """Log data consistency issues"""
        self.error(
            f"Data consistency issue: {issue_type}",
            issue_type=issue_type,
            issue_details=details,
            category="data_consistency"
        )

def get_logger(name: str) -> TradeServiceLogger:
    """Get or create a structured logger instance"""
    return TradeServiceLogger(name)

def with_logging(logger_name: str = None):
    """Decorator to add automatic logging to functions"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_logger(logger_name or f"{func.__module__}.{func.__name__}")
            start_time = datetime.utcnow()
            
            # Generate correlation ID if not present
            if not correlation_id_var.get():
                correlation_id_var.set(str(uuid.uuid4()))
            
            logger.debug(
                f"Function {func.__name__} started",
                function=func.__name__,
                args_count=len(args),
                kwargs_keys=list(kwargs.keys())
            )
            
            try:
                result = await func(*args, **kwargs)
                duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                logger.debug(
                    f"Function {func.__name__} completed successfully",
                    function=func.__name__,
                    duration_ms=duration_ms,
                    success=True
                )
                return result
                
            except Exception as e:
                duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                logger.error(
                    f"Function {func.__name__} failed",
                    function=func.__name__,
                    duration_ms=duration_ms,
                    success=False,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    exc_info=True
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_logger(logger_name or f"{func.__module__}.{func.__name__}")
            start_time = datetime.utcnow()
            
            # Generate correlation ID if not present
            if not correlation_id_var.get():
                correlation_id_var.set(str(uuid.uuid4()))
            
            logger.debug(
                f"Function {func.__name__} started",
                function=func.__name__,
                args_count=len(args),
                kwargs_keys=list(kwargs.keys())
            )
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                logger.debug(
                    f"Function {func.__name__} completed successfully",
                    function=func.__name__,
                    duration_ms=duration_ms,
                    success=True
                )
                return result
                
            except Exception as e:
                duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                logger.error(
                    f"Function {func.__name__} failed",
                    function=func.__name__,
                    duration_ms=duration_ms,
                    success=False,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    exc_info=True
                )
                raise
        
        # Return appropriate wrapper based on function type
        if hasattr(func, '__call__'):
            import inspect
            if inspect.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper
        return func
    
    return decorator

# Context manager for setting correlation context
class LoggingContext:
    """Context manager for setting logging context"""
    
    def __init__(self, correlation_id: str = None, user_id: str = None, organization_id: str = None):
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.user_id = user_id
        self.organization_id = organization_id
        self.previous_context = {}
    
    def __enter__(self):
        # Store previous context
        self.previous_context = {
            'correlation_id': correlation_id_var.get(''),
            'user_id': user_id_var.get(''),
            'organization_id': organization_id_var.get('')
        }
        
        # Set new context
        correlation_id_var.set(self.correlation_id)
        if self.user_id:
            user_id_var.set(self.user_id)
        if self.organization_id:
            organization_id_var.set(self.organization_id)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore previous context
        correlation_id_var.set(self.previous_context['correlation_id'])
        user_id_var.set(self.previous_context['user_id'])
        organization_id_var.set(self.previous_context['organization_id'])

# Convenience functions for common logging patterns
def log_trade_execution(logger: TradeServiceLogger, order_id: str, symbol: str, quantity: int, price: float, success: bool):
    """Log trade execution events"""
    logger.log_business_event(
        "trade_execution",
        {
            "order_id": order_id,
            "symbol": symbol,
            "quantity": quantity,
            "price": price,
            "success": success
        }
    )

def log_rate_limit_hit(logger: TradeServiceLogger, user_id: str, endpoint: str, limit_type: str):
    """Log rate limit violations"""
    logger.log_security_event(
        "rate_limit_exceeded",
        {
            "user_id": user_id,
            "endpoint": endpoint,
            "limit_type": limit_type
        }
    )

def log_autotrader_call(logger: TradeServiceLogger, method: str, duration_ms: float, success: bool, response_data: Dict = None):
    """Log AutoTrader API calls"""
    logger.log_api_call(
        "autotrader",
        method,
        duration_ms,
        success,
        response_data=response_data
    )