"""
Resilience module for shared architecture.

This module provides resilience patterns and utilities for all microservices:
- Circuit breakers for fault tolerance
- Rate limiting for resource protection
- Retry policies for transient failures
- Infrastructure-aware operations with automatic fallbacks
"""

from .circuit_breaker import CircuitBreaker, circuit_breaker
from .rate_limiter import (
    BaseRateLimiter,
    RateLimitConfig,
    RateLimitResult,
    RateLimitExceededError,
    RateLimiterManager,
    get_rate_limiter_manager,
    rate_limit
)
from .retry_policies import RetryPolicy, retry_with_exponential_backoff
from .infrastructure_aware import (
    InfrastructureAwareService,
    OperationMode,
    OperationResult,
    infrastructure_service,
    with_fallback
)

__all__ = [
    # Circuit breaker
    'CircuitBreaker',
    'circuit_breaker',
    
    # Rate limiter
    'BaseRateLimiter',
    'RateLimitConfig',
    'RateLimitResult',
    'RateLimitExceededError',
    'RateLimiterManager',
    'get_rate_limiter_manager',
    'rate_limit',
    
    # Retry policies
    'RetryPolicy',
    'retry_with_exponential_backoff',
    
    # Infrastructure aware
    'InfrastructureAwareService',
    'OperationMode',
    'OperationResult',
    'infrastructure_service',
    'with_fallback',
]