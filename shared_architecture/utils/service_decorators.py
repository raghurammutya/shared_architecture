# shared_architecture/utils/service_decorators.py
"""
Decorator utilities for the comprehensive service system.
Provides easy-to-use decorators for common service concerns.
"""

import asyncio
import time
import functools
from typing import Optional, Dict, Any, Callable
from fastapi import HTTPException, Depends

from shared_architecture.resilience.circuit_breaker import get_circuit_breaker, CircuitBreakerConfig
from shared_architecture.utils.logging_utils import get_logger
from shared_architecture.monitoring.metrics_collector import MetricsCollector

logger = get_logger(__name__)

def with_circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None,
    fallback: Optional[Callable] = None
):
    """
    Decorator to protect functions with circuit breaker pattern.
    
    Args:
        name: Circuit breaker name
        config: Optional circuit breaker configuration
        fallback: Optional fallback function to call when circuit is open
    
    Example:
        @with_circuit_breaker("external_api", fallback=lambda: {"error": "service unavailable"})
        async def call_external_api():
            # This call is protected by circuit breaker
            pass
    """
    def decorator(func):
        circuit_breaker = get_circuit_breaker(name, config)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await circuit_breaker.call_async(func, *args, **kwargs)
            except Exception as e:
                if fallback:
                    logger.warning(f"Circuit breaker {name} triggered, using fallback")
                    if asyncio.iscoroutinefunction(fallback):
                        return await fallback(*args, **kwargs)
                    else:
                        return fallback(*args, **kwargs)
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return circuit_breaker.call(func, *args, **kwargs)
            except Exception as e:
                if fallback:
                    logger.warning(f"Circuit breaker {name} triggered, using fallback")
                    return fallback(*args, **kwargs)
                raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

def with_rate_limit(rate: str):
    """
    Decorator to add rate limiting to FastAPI endpoints.
    
    Args:
        rate: Rate limit string (e.g., "100/minute", "10/second")
    
    Example:
        @app.get("/api/data")
        @with_rate_limit("100/minute")
        async def get_data():
            pass
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # This would integrate with the rate limiter
            # For now, just pass through
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def with_metrics(
    name: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
    track_execution_time: bool = True,
    track_error_rate: bool = True
):
    """
    Decorator to automatically track metrics for functions.
    
    Args:
        name: Metric name (defaults to function name)
        tags: Additional tags for metrics
        track_execution_time: Whether to track execution time
        track_error_rate: Whether to track error rates
    
    Example:
        @with_metrics("order_processing", tags={"service": "trade"})
        async def process_order(order_id: str):
            pass
    """
    def decorator(func):
        metric_name = name or func.__name__
        metric_tags = tags or {}
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                
                if track_execution_time:
                    duration = (time.time() - start_time) * 1000
                    # Record execution time metric
                    logger.debug(f"Function {metric_name} executed in {duration:.2f}ms")
                
                return result
                
            except Exception as e:
                if track_error_rate:
                    # Record error metric
                    logger.error(f"Function {metric_name} failed: {str(e)}")
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                
                if track_execution_time:
                    duration = (time.time() - start_time) * 1000
                    logger.debug(f"Function {metric_name} executed in {duration:.2f}ms")
                
                return result
                
            except Exception as e:
                if track_error_rate:
                    logger.error(f"Function {metric_name} failed: {str(e)}")
                raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

def with_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator to add retry logic to functions.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff_factor: Multiplier for delay after each attempt
        exceptions: Tuple of exceptions to retry on
    
    Example:
        @with_retry(max_attempts=3, delay=1.0, exceptions=(ConnectionError,))
        async def unreliable_operation():
            pass
    """
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {str(e)}. "
                            f"Retrying in {current_delay}s"
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff_factor
                    else:
                        logger.error(f"All {max_attempts} attempts failed for {func.__name__}")
                        raise
            
            raise last_exception
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            import time as sync_time
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {str(e)}. "
                            f"Retrying in {current_delay}s"
                        )
                        sync_time.sleep(current_delay)
                        current_delay *= backoff_factor
                    else:
                        logger.error(f"All {max_attempts} attempts failed for {func.__name__}")
                        raise
            
            raise last_exception
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

def with_cache(
    ttl: int = 300,  # 5 minutes default
    key_prefix: Optional[str] = None,
    cache_exceptions: bool = False
):
    """
    Decorator to add caching to functions.
    
    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache keys
        cache_exceptions: Whether to cache exceptions
    
    Example:
        @with_cache(ttl=600, key_prefix="user_data")
        async def get_user_data(user_id: str):
            pass
    """
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # This would integrate with Redis caching
            # For now, just pass through
            return await func(*args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # This would integrate with Redis caching
            # For now, just pass through
            return func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

def with_timeout(seconds: float):
    """
    Decorator to add timeout to async functions.
    
    Args:
        seconds: Timeout in seconds
    
    Example:
        @with_timeout(30.0)
        async def slow_operation():
            pass
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                logger.error(f"Function {func.__name__} timed out after {seconds} seconds")
                raise HTTPException(
                    status_code=504,
                    detail=f"Operation timed out after {seconds} seconds"
                )
        
        if not asyncio.iscoroutinefunction(func):
            raise ValueError("@with_timeout can only be applied to async functions")
        
        return wrapper
    return decorator

def with_validation(schema_class):
    """
    Decorator to add Pydantic validation to function parameters.
    
    Args:
        schema_class: Pydantic model class for validation
    
    Example:
        @with_validation(UserCreateSchema)
        async def create_user(user_data: dict):
            pass
    """
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Validate first argument if it's a dict
            if args and isinstance(args[0], dict):
                try:
                    validated_data = schema_class(**args[0])
                    args = (validated_data.dict(), *args[1:])
                except Exception as e:
                    logger.error(f"Validation failed for {func.__name__}: {str(e)}")
                    raise HTTPException(status_code=422, detail=str(e))
            
            return await func(*args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Validate first argument if it's a dict
            if args and isinstance(args[0], dict):
                try:
                    validated_data = schema_class(**args[0])
                    args = (validated_data.dict(), *args[1:])
                except Exception as e:
                    logger.error(f"Validation failed for {func.__name__}: {str(e)}")
                    raise HTTPException(status_code=422, detail=str(e))
            
            return func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

# Combine multiple decorators into common patterns
def api_endpoint(
    rate_limit: str = "100/minute",
    timeout: float = 30.0,
    circuit_breaker_name: Optional[str] = None,
    cache_ttl: Optional[int] = None,
    metrics_name: Optional[str] = None
):
    """
    Combine common API endpoint decorators.
    
    Example:
        @api_endpoint(
            rate_limit="1000/minute",
            timeout=45.0,
            circuit_breaker_name="external_service",
            cache_ttl=300
        )
        async def api_handler():
            pass
    """
    def decorator(func):
        # Apply decorators in reverse order (innermost first)
        decorated = func
        
        if metrics_name:
            decorated = with_metrics(metrics_name)(decorated)
        
        if cache_ttl:
            decorated = with_cache(ttl=cache_ttl)(decorated)
        
        if circuit_breaker_name:
            decorated = with_circuit_breaker(circuit_breaker_name)(decorated)
        
        if timeout:
            decorated = with_timeout(timeout)(decorated)
        
        if rate_limit:
            decorated = with_rate_limit(rate_limit)(decorated)
        
        return decorated
    
    return decorator

def background_task(
    retry_attempts: int = 3,
    retry_delay: float = 5.0,
    circuit_breaker_name: Optional[str] = None,
    metrics_name: Optional[str] = None
):
    """
    Combine common background task decorators.
    
    Example:
        @background_task(
            retry_attempts=5,
            circuit_breaker_name="email_service"
        )
        async def send_notification():
            pass
    """
    def decorator(func):
        decorated = func
        
        if metrics_name:
            decorated = with_metrics(metrics_name)(decorated)
        
        if circuit_breaker_name:
            decorated = with_circuit_breaker(circuit_breaker_name)(decorated)
        
        if retry_attempts > 1:
            decorated = with_retry(
                max_attempts=retry_attempts,
                delay=retry_delay
            )(decorated)
        
        return decorated
    
    return decorator