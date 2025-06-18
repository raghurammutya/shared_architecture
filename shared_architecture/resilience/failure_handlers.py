# shared_architecture/resilience/failure_handlers.py

import asyncio
import json
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from functools import wraps

from ..utils.enhanced_logging import get_logger
from ..clients.service_client import ServiceUnavailableError
from ..events.alert_system import get_alert_manager, AlertSeverity

logger = get_logger(__name__)

class FailureMode(Enum):
    """Types of service failures"""
    SERVICE_UNAVAILABLE = "service_unavailable"
    TIMEOUT = "timeout"
    AUTHENTICATION_FAILED = "authentication_failed"
    RATE_LIMITED = "rate_limited"
    DATA_CORRUPTION = "data_corruption"
    PARTIAL_FAILURE = "partial_failure"

class FallbackStrategy(Enum):
    """Fallback strategies when services fail"""
    CACHED_DATA = "cached_data"
    EMERGENCY_LIMITS = "emergency_limits"
    QUEUE_FOR_RETRY = "queue_for_retry"
    FAIL_FAST = "fail_fast"
    DEGRADED_SERVICE = "degraded_service"

@dataclass
class FailureContext:
    """Context information about a failure"""
    service_name: str
    failure_mode: FailureMode
    error_message: str
    timestamp: datetime
    user_id: Optional[int] = None
    trading_account_id: Optional[int] = None
    request_data: Dict[str, Any] = None
    retry_count: int = 0

class CacheManager:
    """Manage cached data for fallback scenarios"""
    
    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.cache_ttl: Dict[str, datetime] = {}
        self.default_ttl = timedelta(minutes=5)
    
    def set(self, key: str, value: Any, ttl: timedelta = None):
        """Set cached value with TTL"""
        self.cache[key] = {
            "value": value,
            "cached_at": datetime.utcnow()
        }
        self.cache_ttl[key] = datetime.utcnow() + (ttl or self.default_ttl)
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired"""
        if key not in self.cache:
            return None
        
        if datetime.utcnow() > self.cache_ttl.get(key, datetime.min):
            # Cache expired
            del self.cache[key]
            del self.cache_ttl[key]
            return None
        
        return self.cache[key]
    
    def is_stale(self, key: str, max_age: timedelta = None) -> bool:
        """Check if cached data is stale"""
        if key not in self.cache:
            return True
        
        max_age = max_age or timedelta(minutes=1)
        cached_at = self.cache[key]["cached_at"]
        return datetime.utcnow() - cached_at > max_age

class EmergencyLimitsProvider:
    """Provide emergency trading limits when user service is down"""
    
    def __init__(self):
        self.emergency_limits = {
            "daily_trading_limit": 10000.00,
            "single_trade_limit": 2000.00,
            "daily_order_count": 5,
            "allowed_instruments": ["NIFTY50_STOCKS"],
            "max_position_value": 20000.00
        }
    
    def get_emergency_permissions(self, user_id: int) -> Dict[str, Any]:
        """Get emergency permissions for user"""
        return {
            "allowed": True,
            "emergency_mode": True,
            "message": "Using emergency limits due to service unavailability",
            "limits": self.emergency_limits,
            "restrictions": [
                "Limited to conservative trading amounts",
                "Only blue-chip stocks allowed",
                "Maximum 5 orders per day"
            ],
            "valid_until": (datetime.utcnow() + timedelta(hours=1)).isoformat()
        }

class RetryQueue:
    """Queue failed operations for retry when services recover"""
    
    def __init__(self):
        self.queue: List[Dict[str, Any]] = []
        self.max_queue_size = 1000
        self.retry_intervals = [30, 60, 300, 900]  # 30s, 1m, 5m, 15m
    
    def enqueue(self, operation: Dict[str, Any]):
        """Add operation to retry queue"""
        if len(self.queue) >= self.max_queue_size:
            # Remove oldest item
            self.queue.pop(0)
        
        operation["queued_at"] = datetime.utcnow()
        operation["retry_count"] = 0
        self.queue.append(operation)
        
        logger.info(f"Operation queued for retry: {operation.get('type', 'unknown')}")
    
    def get_ready_operations(self) -> List[Dict[str, Any]]:
        """Get operations ready for retry"""
        now = datetime.utcnow()
        ready_ops = []
        
        for op in self.queue:
            retry_count = op.get("retry_count", 0)
            if retry_count >= len(self.retry_intervals):
                continue  # Max retries exceeded
            
            next_retry = op["queued_at"] + timedelta(seconds=self.retry_intervals[retry_count])
            if now >= next_retry:
                ready_ops.append(op)
        
        return ready_ops
    
    def mark_retry_attempted(self, operation: Dict[str, Any]):
        """Mark operation as retry attempted"""
        operation["retry_count"] = operation.get("retry_count", 0) + 1
        operation["last_retry"] = datetime.utcnow()
    
    def remove_operation(self, operation: Dict[str, Any]):
        """Remove operation from queue"""
        if operation in self.queue:
            self.queue.remove(operation)

class FailureHandler:
    """Handle various failure scenarios with appropriate fallback strategies"""
    
    def __init__(self):
        self.cache_manager = CacheManager()
        self.emergency_limits = EmergencyLimitsProvider()
        self.retry_queue = RetryQueue()
        self.failure_handlers: Dict[FailureMode, Callable] = {
            FailureMode.SERVICE_UNAVAILABLE: self._handle_service_unavailable,
            FailureMode.TIMEOUT: self._handle_timeout,
            FailureMode.AUTHENTICATION_FAILED: self._handle_auth_failure,
            FailureMode.RATE_LIMITED: self._handle_rate_limit,
            FailureMode.DATA_CORRUPTION: self._handle_data_corruption,
        }
    
    async def handle_failure(self, context: FailureContext, fallback_strategy: FallbackStrategy) -> Dict[str, Any]:
        """Handle failure with specified strategy"""
        
        # Log the failure
        logger.error(f"Handling failure: {context.service_name} - {context.failure_mode.value} - {context.error_message}")
        
        # Create alert
        try:
            alert_manager = get_alert_manager()
            await alert_manager.create_system_health_alert(
                service_name=context.service_name,
                component="service_communication",
                error_message=context.error_message,
                severity=AlertSeverity.ERROR
            )
        except Exception as e:
            logger.warning(f"Failed to create alert: {e}")
        
        # Handle based on failure mode
        if context.failure_mode in self.failure_handlers:
            return await self.failure_handlers[context.failure_mode](context, fallback_strategy)
        else:
            return await self._handle_generic_failure(context, fallback_strategy)
    
    async def _handle_service_unavailable(self, context: FailureContext, strategy: FallbackStrategy) -> Dict[str, Any]:
        """Handle service unavailable scenarios"""
        
        if strategy == FallbackStrategy.CACHED_DATA:
            cache_key = f"{context.service_name}_{context.user_id}_{context.trading_account_id}"
            cached_data = self.cache_manager.get(cache_key)
            
            if cached_data:
                cached_data["cached"] = True
                cached_data["warning"] = f"{context.service_name} unavailable - using cached data"
                return cached_data
            
            # No cached data available, fall back to emergency limits
            strategy = FallbackStrategy.EMERGENCY_LIMITS
        
        if strategy == FallbackStrategy.EMERGENCY_LIMITS:
            if context.service_name == "user_service" and context.user_id:
                return self.emergency_limits.get_emergency_permissions(context.user_id)
            
            return {
                "emergency_mode": True,
                "message": f"{context.service_name} unavailable - operating with restrictions",
                "restrictions": ["Limited functionality available", "Some features may be disabled"]
            }
        
        if strategy == FallbackStrategy.QUEUE_FOR_RETRY:
            self.retry_queue.enqueue({
                "type": "service_call",
                "service": context.service_name,
                "user_id": context.user_id,
                "request_data": context.request_data,
                "context": context
            })
            
            return {
                "queued": True,
                "message": "Request queued for processing when service recovers",
                "estimated_retry": (datetime.utcnow() + timedelta(seconds=30)).isoformat()
            }
        
        if strategy == FallbackStrategy.FAIL_FAST:
            raise ServiceUnavailableError(f"{context.service_name} is unavailable: {context.error_message}")
        
        return {"error": f"No fallback available for {context.service_name}"}
    
    async def _handle_timeout(self, context: FailureContext, strategy: FallbackStrategy) -> Dict[str, Any]:
        """Handle timeout scenarios"""
        
        if strategy == FallbackStrategy.QUEUE_FOR_RETRY:
            self.retry_queue.enqueue({
                "type": "timeout_retry",
                "service": context.service_name,
                "request_data": context.request_data,
                "timeout_count": context.retry_count + 1
            })
            
            return {
                "timeout": True,
                "message": "Request timed out - queued for retry with increased timeout",
                "retry_timeout": min(30 * (2 ** context.retry_count), 300)  # Exponential backoff, max 5 minutes
            }
        
        return await self._handle_service_unavailable(context, strategy)
    
    async def _handle_auth_failure(self, context: FailureContext, strategy: FallbackStrategy) -> Dict[str, Any]:
        """Handle authentication failures"""
        
        # Authentication failures require immediate attention
        try:
            alert_manager = get_alert_manager()
            await alert_manager.create_system_health_alert(
                service_name=context.service_name,
                component="authentication",
                error_message="Service authentication failed - may indicate security issue",
                severity=AlertSeverity.CRITICAL
            )
        except Exception:
            pass
        
        if strategy == FallbackStrategy.FAIL_FAST:
            raise ServiceUnavailableError(f"Authentication failed for {context.service_name}")
        
        return {
            "auth_failed": True,
            "message": "Authentication failure - service access denied",
            "action_required": "Check service credentials and tokens"
        }
    
    async def _handle_rate_limit(self, context: FailureContext, strategy: FallbackStrategy) -> Dict[str, Any]:
        """Handle rate limiting"""
        
        if strategy == FallbackStrategy.QUEUE_FOR_RETRY:
            # Calculate backoff time based on rate limit
            backoff_time = 60  # Default 1 minute
            
            self.retry_queue.enqueue({
                "type": "rate_limited_retry",
                "service": context.service_name,
                "request_data": context.request_data,
                "backoff_time": backoff_time
            })
            
            return {
                "rate_limited": True,
                "message": f"Rate limit exceeded for {context.service_name} - request queued",
                "retry_after": (datetime.utcnow() + timedelta(seconds=backoff_time)).isoformat()
            }
        
        return await self._handle_service_unavailable(context, strategy)
    
    async def _handle_data_corruption(self, context: FailureContext, strategy: FallbackStrategy) -> Dict[str, Any]:
        """Handle data corruption scenarios"""
        
        # Data corruption is serious - alert immediately
        try:
            alert_manager = get_alert_manager()
            await alert_manager.create_system_health_alert(
                service_name=context.service_name,
                component="data_integrity",
                error_message="Data corruption detected - immediate investigation required",
                severity=AlertSeverity.CRITICAL
            )
        except Exception:
            pass
        
        if strategy == FallbackStrategy.CACHED_DATA:
            # Try to use cached data as fallback
            cache_key = f"{context.service_name}_backup_{context.user_id}"
            cached_data = self.cache_manager.get(cache_key)
            
            if cached_data:
                return {
                    **cached_data,
                    "warning": "Using backup data due to data corruption",
                    "data_integrity_warning": True
                }
        
        return {
            "data_corruption": True,
            "message": "Data corruption detected - service unavailable",
            "action_required": "Contact system administrator immediately"
        }
    
    async def _handle_generic_failure(self, context: FailureContext, strategy: FallbackStrategy) -> Dict[str, Any]:
        """Handle generic failures"""
        
        return {
            "generic_failure": True,
            "failure_mode": context.failure_mode.value,
            "message": f"Service failure: {context.error_message}",
            "strategy": strategy.value
        }
    
    def cache_response(self, service_name: str, user_id: int, trading_account_id: int, response: Dict[str, Any]):
        """Cache successful response for fallback use"""
        cache_key = f"{service_name}_{user_id}_{trading_account_id}"
        self.cache_manager.set(cache_key, response, ttl=timedelta(minutes=5))
    
    async def process_retry_queue(self):
        """Process queued operations for retry"""
        ready_operations = self.retry_queue.get_ready_operations()
        
        for operation in ready_operations:
            try:
                # Attempt to retry the operation
                success = await self._retry_operation(operation)
                
                if success:
                    logger.info(f"Retry successful for operation: {operation.get('type')}")
                    self.retry_queue.remove_operation(operation)
                else:
                    self.retry_queue.mark_retry_attempted(operation)
                    
            except Exception as e:
                logger.error(f"Retry failed for operation {operation.get('type')}: {e}")
                self.retry_queue.mark_retry_attempted(operation)
    
    async def _retry_operation(self, operation: Dict[str, Any]) -> bool:
        """Retry a failed operation"""
        # Implementation would depend on operation type
        # For now, simulate retry logic
        await asyncio.sleep(0.1)
        return True  # Simulate success

# Decorator for automatic failure handling
def handle_service_failures(fallback_strategy: FallbackStrategy = FallbackStrategy.CACHED_DATA):
    """Decorator to automatically handle service failures"""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                
                # Cache successful result if applicable
                if hasattr(wrapper, '_failure_handler'):
                    # Extract context from function arguments for caching
                    # This would need to be customized per function
                    pass
                
                return result
                
            except ServiceUnavailableError as e:
                # Extract context from error and function arguments
                context = FailureContext(
                    service_name=getattr(e, 'service_name', 'unknown'),
                    failure_mode=FailureMode.SERVICE_UNAVAILABLE,
                    error_message=str(e),
                    timestamp=datetime.utcnow()
                )
                
                failure_handler = getattr(wrapper, '_failure_handler', FailureHandler())
                return await failure_handler.handle_failure(context, fallback_strategy)
            
            except asyncio.TimeoutError as e:
                context = FailureContext(
                    service_name='unknown',
                    failure_mode=FailureMode.TIMEOUT,
                    error_message=str(e),
                    timestamp=datetime.utcnow()
                )
                
                failure_handler = getattr(wrapper, '_failure_handler', FailureHandler())
                return await failure_handler.handle_failure(context, fallback_strategy)
        
        # Attach failure handler to function
        wrapper._failure_handler = FailureHandler()
        return wrapper
    
    return decorator

# Global failure handler instance
_failure_handler: Optional[FailureHandler] = None

def get_failure_handler() -> FailureHandler:
    """Get global failure handler instance"""
    global _failure_handler
    if _failure_handler is None:
        _failure_handler = FailureHandler()
    return _failure_handler