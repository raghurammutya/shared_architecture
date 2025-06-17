# shared_architecture/exceptions/trade_exceptions.py
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

class ErrorCategory(Enum):
    """Error categories for better error handling"""
    VALIDATION = "validation"
    BUSINESS_LOGIC = "business_logic"
    EXTERNAL_API = "external_api"
    DATABASE = "database"
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    RATE_LIMITING = "rate_limiting"
    DATA_CONSISTENCY = "data_consistency"
    SYSTEM = "system"

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ErrorContext:
    """Context information for errors"""
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    order_id: Optional[str] = None
    symbol: Optional[str] = None
    endpoint: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None

class BaseTradeException(Exception):
    """Base exception for all trade service errors"""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        error_code: str = None,
        context: ErrorContext = None,
        original_exception: Exception = None,
        http_status_code: int = 500,
        user_message: str = None,
        retry_after: int = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.error_code = error_code or self._generate_error_code()
        self.context = context or ErrorContext()
        self.original_exception = original_exception
        self.http_status_code = http_status_code
        self.user_message = user_message or self._default_user_message()
        self.retry_after = retry_after
    
    def _generate_error_code(self) -> str:
        """Generate error code based on exception class and category"""
        class_name = self.__class__.__name__.replace('Exception', '').upper()
        return f"{self.category.value.upper()}_{class_name}"
    
    def _default_user_message(self) -> str:
        """Generate user-friendly error message"""
        if self.severity == ErrorSeverity.CRITICAL:
            return "A critical system error occurred. Please contact support immediately."
        elif self.severity == ErrorSeverity.HIGH:
            return "An error occurred while processing your request. Please try again or contact support."
        else:
            return "An error occurred. Please try again."
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/API responses"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "user_message": self.user_message,
            "category": self.category.value,
            "severity": self.severity.value,
            "http_status_code": self.http_status_code,
            "retry_after": self.retry_after,
            "context": {
                "correlation_id": self.context.correlation_id,
                "user_id": self.context.user_id,
                "organization_id": self.context.organization_id,
                "order_id": self.context.order_id,
                "symbol": self.context.symbol,
                "endpoint": self.context.endpoint,
                "additional_data": self.context.additional_data
            },
            "original_error": str(self.original_exception) if self.original_exception else None
        }

# Validation Exceptions
class ValidationException(BaseTradeException):
    """Raised when input validation fails"""
    
    def __init__(self, message: str, field_name: str = None, field_value: Any = None, **kwargs):
        context = kwargs.get('context', ErrorContext())
        if not context.additional_data:
            context.additional_data = {}
        context.additional_data.update({
            'field_name': field_name,
            'field_value': str(field_value) if field_value is not None else None
        })
        kwargs['context'] = context
        
        super().__init__(
            message,
            ErrorCategory.VALIDATION,
            ErrorSeverity.LOW,
            http_status_code=400,
            user_message="Invalid input provided. Please check your request and try again.",
            **kwargs
        )

class InsufficientFundsException(BaseTradeException):
    """Raised when user has insufficient funds for trade"""
    
    def __init__(self, required_amount: float, available_amount: float, **kwargs):
        message = f"Insufficient funds: required {required_amount}, available {available_amount}"
        context = kwargs.get('context', ErrorContext())
        if not context.additional_data:
            context.additional_data = {}
        context.additional_data.update({
            'required_amount': required_amount,
            'available_amount': available_amount
        })
        kwargs['context'] = context
        
        super().__init__(
            message,
            ErrorCategory.BUSINESS_LOGIC,
            ErrorSeverity.MEDIUM,
            http_status_code=400,
            user_message=f"Insufficient funds for this trade. Required: {required_amount}, Available: {available_amount}",
            **kwargs
        )

class OrderNotFoundException(BaseTradeException):
    """Raised when order is not found"""
    
    def __init__(self, order_id: str, **kwargs):
        message = f"Order not found: {order_id}"
        context = kwargs.get('context', ErrorContext())
        context.order_id = order_id
        kwargs['context'] = context
        
        super().__init__(
            message,
            ErrorCategory.BUSINESS_LOGIC,
            ErrorSeverity.MEDIUM,
            http_status_code=404,
            user_message="The requested order was not found.",
            **kwargs
        )

# External API Exceptions
class AutoTraderException(BaseTradeException):
    """Raised when AutoTrader API calls fail"""
    
    def __init__(self, message: str, api_method: str = None, api_response: Dict = None, **kwargs):
        context = kwargs.get('context', ErrorContext())
        if not context.additional_data:
            context.additional_data = {}
        context.additional_data.update({
            'api_method': api_method,
            'api_response': api_response
        })
        kwargs['context'] = context
        
        super().__init__(
            message,
            ErrorCategory.EXTERNAL_API,
            ErrorSeverity.HIGH,
            http_status_code=502,
            user_message="Trading platform is temporarily unavailable. Please try again.",
            **kwargs
        )

class AutoTraderRateLimitException(BaseTradeException):
    """Raised when AutoTrader rate limits are exceeded"""
    
    def __init__(self, retry_after: int = 60, **kwargs):
        message = f"AutoTrader rate limit exceeded. Retry after {retry_after} seconds."
        
        super().__init__(
            message,
            ErrorCategory.RATE_LIMITING,
            ErrorSeverity.MEDIUM,
            http_status_code=429,
            user_message="Too many requests. Please wait a moment and try again.",
            retry_after=retry_after,
            **kwargs
        )

# Database Exceptions
class DatabaseException(BaseTradeException):
    """Raised when database operations fail"""
    
    def __init__(self, message: str, operation: str = None, table: str = None, **kwargs):
        context = kwargs.get('context', ErrorContext())
        if not context.additional_data:
            context.additional_data = {}
        context.additional_data.update({
            'operation': operation,
            'table': table
        })
        kwargs['context'] = context
        
        super().__init__(
            message,
            ErrorCategory.DATABASE,
            ErrorSeverity.HIGH,
            http_status_code=500,
            user_message="A database error occurred. Please try again.",
            **kwargs
        )

class DataConsistencyException(BaseTradeException):
    """Raised when data consistency checks fail"""
    
    def __init__(self, message: str, inconsistency_type: str = None, affected_records: int = None, **kwargs):
        context = kwargs.get('context', ErrorContext())
        if not context.additional_data:
            context.additional_data = {}
        context.additional_data.update({
            'inconsistency_type': inconsistency_type,
            'affected_records': affected_records
        })
        kwargs['context'] = context
        
        super().__init__(
            message,
            ErrorCategory.DATA_CONSISTENCY,
            ErrorSeverity.CRITICAL,
            http_status_code=500,
            user_message="A data consistency issue was detected. Support has been notified.",
            **kwargs
        )

# Authentication/Authorization Exceptions
class AuthenticationException(BaseTradeException):
    """Raised when authentication fails"""
    
    def __init__(self, message: str = "Authentication failed", **kwargs):
        super().__init__(
            message,
            ErrorCategory.AUTHENTICATION,
            ErrorSeverity.MEDIUM,
            http_status_code=401,
            user_message="Authentication required. Please log in.",
            **kwargs
        )

class AuthorizationException(BaseTradeException):
    """Raised when authorization fails"""
    
    def __init__(self, message: str = "Access denied", resource: str = None, **kwargs):
        context = kwargs.get('context', ErrorContext())
        if not context.additional_data:
            context.additional_data = {}
        context.additional_data.update({
            'resource': resource
        })
        kwargs['context'] = context
        
        super().__init__(
            message,
            ErrorCategory.AUTHORIZATION,
            ErrorSeverity.MEDIUM,
            http_status_code=403,
            user_message="You don't have permission to perform this action.",
            **kwargs
        )

# Network/System Exceptions
class NetworkException(BaseTradeException):
    """Raised when network operations fail"""
    
    def __init__(self, message: str, endpoint: str = None, timeout: bool = False, **kwargs):
        context = kwargs.get('context', ErrorContext())
        context.endpoint = endpoint
        if not context.additional_data:
            context.additional_data = {}
        context.additional_data.update({
            'timeout': timeout
        })
        kwargs['context'] = context
        
        retry_after = 30 if timeout else None
        user_message = "Network timeout. Please try again." if timeout else "Network error. Please try again."
        
        super().__init__(
            message,
            ErrorCategory.NETWORK,
            ErrorSeverity.MEDIUM,
            http_status_code=503,
            user_message=user_message,
            retry_after=retry_after,
            **kwargs
        )

class ConfigurationException(BaseTradeException):
    """Raised when configuration errors occur"""
    
    def __init__(self, message: str, config_key: str = None, **kwargs):
        context = kwargs.get('context', ErrorContext())
        if not context.additional_data:
            context.additional_data = {}
        context.additional_data.update({
            'config_key': config_key
        })
        kwargs['context'] = context
        
        super().__init__(
            message,
            ErrorCategory.SYSTEM,
            ErrorSeverity.HIGH,
            http_status_code=500,
            user_message="A system configuration error occurred. Support has been notified.",
            **kwargs
        )

# Rate Limiting Exceptions
class RateLimitException(BaseTradeException):
    """Raised when rate limits are exceeded"""
    
    def __init__(self, message: str, limit_type: str = None, retry_after: int = 60, **kwargs):
        context = kwargs.get('context', ErrorContext())
        if not context.additional_data:
            context.additional_data = {}
        context.additional_data.update({
            'limit_type': limit_type
        })
        kwargs['context'] = context
        
        super().__init__(
            message,
            ErrorCategory.RATE_LIMITING,
            ErrorSeverity.MEDIUM,
            http_status_code=429,
            user_message="Too many requests. Please wait and try again.",
            retry_after=retry_after,
            **kwargs
        )

# Symbol/Instrument Exceptions
class SymbolNotFoundException(BaseTradeException):
    """Raised when symbol/instrument is not found"""
    
    def __init__(self, symbol: str, exchange: str = None, **kwargs):
        message = f"Symbol not found: {symbol}"
        if exchange:
            message += f" on {exchange}"
        
        context = kwargs.get('context', ErrorContext())
        context.symbol = symbol
        if not context.additional_data:
            context.additional_data = {}
        context.additional_data.update({
            'exchange': exchange
        })
        kwargs['context'] = context
        
        super().__init__(
            message,
            ErrorCategory.VALIDATION,
            ErrorSeverity.MEDIUM,
            http_status_code=400,
            user_message=f"The symbol '{symbol}' was not found.",
            **kwargs
        )

class InvalidSymbolFormatException(BaseTradeException):
    """Raised when symbol format is invalid"""
    
    def __init__(self, symbol: str, expected_format: str = None, **kwargs):
        message = f"Invalid symbol format: {symbol}"
        if expected_format:
            message += f". Expected format: {expected_format}"
        
        context = kwargs.get('context', ErrorContext())
        context.symbol = symbol
        if not context.additional_data:
            context.additional_data = {}
        context.additional_data.update({
            'expected_format': expected_format
        })
        kwargs['context'] = context
        
        super().__init__(
            message,
            ErrorCategory.VALIDATION,
            ErrorSeverity.LOW,
            http_status_code=400,
            user_message=f"Invalid symbol format: {symbol}",
            **kwargs
        )