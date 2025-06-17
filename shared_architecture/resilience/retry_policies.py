# shared_architecture/resilience/retry_policies.py
"""
Retry policy implementations for resilient service communication.
Provides various retry strategies with backoff and jitter.
"""

import asyncio
import random
import time
from datetime import datetime, timedelta
from typing import Type, Tuple, Callable, Optional, Any, Union, TypeVar, Generic
from dataclasses import dataclass
from enum import Enum
import math

from shared_architecture.utils.enhanced_logging import get_logger
from shared_architecture.monitoring.metrics_collector import MetricsCollector, trade_metrics

logger = get_logger(__name__)

T = TypeVar('T')

class BackoffStrategy(Enum):
    """Backoff strategies for retries."""
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    POLYNOMIAL = "polynomial"

@dataclass
class RetryConfig:
    """Configuration for retry policies."""
    max_attempts: int = 3
    base_delay: float = 1.0  # Base delay in seconds
    max_delay: float = 60.0  # Maximum delay in seconds
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    backoff_multiplier: float = 2.0
    jitter: bool = True  # Add random jitter to delays
    jitter_max: float = 0.1  # Maximum jitter as fraction of delay
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    non_retryable_exceptions: Tuple[Type[Exception], ...] = ()
    name: str = "retry_policy"

@dataclass
class RetryAttempt:
    """Information about a retry attempt."""
    attempt_number: int
    exception: Optional[Exception]
    delay: float
    timestamp: datetime
    total_elapsed: float

class RetryExhaustedError(Exception):
    """Exception raised when all retry attempts are exhausted."""
    def __init__(self, message: str, attempts: list[RetryAttempt], last_exception: Exception):
        super().__init__(message)
        self.attempts = attempts
        self.last_exception = last_exception

class RetryPolicy(Generic[T]):
    """
    Retry policy implementation with configurable backoff strategies.
    """
    
    def __init__(self, config: RetryConfig):
        self.config = config
        self.logger = get_logger(f"retry_policy.{config.name}")
        
        # Metrics
        self.metrics_collector = MetricsCollector.get_instance()
        self.attempts_counter = self.metrics_collector.counter(
            "retry_attempts_total",
            "Total retry attempts",
            tags={"policy": config.name}
        )
        self.success_counter = self.metrics_collector.counter(
            "retry_success_total", 
            "Successful operations after retries",
            tags={"policy": config.name}
        )
        self.exhausted_counter = self.metrics_collector.counter(
            "retry_exhausted_total",
            "Operations that exhausted all retries",
            tags={"policy": config.name}
        )
        self.retry_delay_histogram = self.metrics_collector.histogram(
            "retry_delay_seconds",
            "Retry delay distribution",
            tags={"policy": config.name}
        )
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number."""
        if self.config.backoff_strategy == BackoffStrategy.FIXED:
            delay = self.config.base_delay
            
        elif self.config.backoff_strategy == BackoffStrategy.LINEAR:
            delay = self.config.base_delay * attempt
            
        elif self.config.backoff_strategy == BackoffStrategy.EXPONENTIAL:
            delay = self.config.base_delay * (self.config.backoff_multiplier ** (attempt - 1))
            
        elif self.config.backoff_strategy == BackoffStrategy.POLYNOMIAL:
            delay = self.config.base_delay * (attempt ** self.config.backoff_multiplier)
            
        else:
            delay = self.config.base_delay
        
        # Apply maximum delay limit
        delay = min(delay, self.config.max_delay)
        
        # Add jitter if enabled
        if self.config.jitter:
            jitter_amount = delay * self.config.jitter_max * random.random()
            delay += jitter_amount
        
        return delay
    
    def _is_retryable(self, exception: Exception) -> bool:
        """Check if an exception is retryable."""
        # Check non-retryable exceptions first
        if isinstance(exception, self.config.non_retryable_exceptions):
            return False
        
        # Check retryable exceptions
        return isinstance(exception, self.config.retryable_exceptions)
    
    def execute(self, func: Callable[[], T], *args, **kwargs) -> T:
        """
        Execute a function with retry logic.
        
        Args:
            func: Function to execute
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Function result
            
        Raises:
            RetryExhaustedError: If all retry attempts are exhausted
        """
        attempts = []
        start_time = time.time()
        
        for attempt_num in range(1, self.config.max_attempts + 1):
            self.attempts_counter.increment(tags={
                "policy": self.config.name,
                "attempt": str(attempt_num)
            })
            
            try:
                result = func(*args, **kwargs)
                
                # Success
                if attempt_num > 1:
                    total_elapsed = time.time() - start_time
                    self.success_counter.increment(tags={
                        "policy": self.config.name,
                        "attempts_used": str(attempt_num)
                    })
                    
                    self.logger.info(
                        f"Operation succeeded after {attempt_num} attempts",
                        policy=self.config.name,
                        attempts=attempt_num,
                        total_elapsed=total_elapsed
                    )
                
                return result
                
            except Exception as e:
                current_time = time.time()
                elapsed = current_time - start_time
                
                attempt = RetryAttempt(
                    attempt_number=attempt_num,
                    exception=e,
                    delay=0.0,  # Will be set below if retrying
                    timestamp=datetime.utcnow(),
                    total_elapsed=elapsed
                )
                attempts.append(attempt)
                
                # Check if we should retry
                if attempt_num >= self.config.max_attempts or not self._is_retryable(e):
                    self.exhausted_counter.increment(tags={
                        "policy": self.config.name,
                        "exception_type": type(e).__name__,
                        "attempts_used": str(attempt_num)
                    })
                    
                    self.logger.error(
                        f"Retry exhausted after {attempt_num} attempts",
                        policy=self.config.name,
                        attempts=attempt_num,
                        total_elapsed=elapsed,
                        last_exception=str(e),
                        exc_info=True
                    )
                    
                    raise RetryExhaustedError(
                        f"Retry policy '{self.config.name}' exhausted after {attempt_num} attempts",
                        attempts,
                        e
                    )
                
                # Calculate delay and wait
                delay = self._calculate_delay(attempt_num)
                attempt.delay = delay
                
                self.retry_delay_histogram.observe(delay, tags={
                    "policy": self.config.name,
                    "attempt": str(attempt_num)
                })
                
                self.logger.warning(
                    f"Attempt {attempt_num} failed, retrying in {delay:.2f}s",
                    policy=self.config.name,
                    attempt=attempt_num,
                    delay=delay,
                    exception=str(e)
                )
                
                time.sleep(delay)
        
        # This shouldn't be reached, but just in case
        raise RetryExhaustedError(
            f"Retry policy '{self.config.name}' exhausted",
            attempts,
            attempts[-1].exception if attempts else Exception("Unknown error")
        )
    
    async def execute_async(self, func: Callable[[], Union[T, Any]], *args, **kwargs) -> T:
        """
        Execute an async function with retry logic.
        
        Args:
            func: Async function to execute
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Function result
            
        Raises:
            RetryExhaustedError: If all retry attempts are exhausted
        """
        attempts = []
        start_time = time.time()
        
        for attempt_num in range(1, self.config.max_attempts + 1):
            self.attempts_counter.increment(tags={
                "policy": self.config.name,
                "attempt": str(attempt_num)
            })
            
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # Success
                if attempt_num > 1:
                    total_elapsed = time.time() - start_time
                    self.success_counter.increment(tags={
                        "policy": self.config.name,
                        "attempts_used": str(attempt_num)
                    })
                    
                    self.logger.info(
                        f"Async operation succeeded after {attempt_num} attempts",
                        policy=self.config.name,
                        attempts=attempt_num,
                        total_elapsed=total_elapsed
                    )
                
                return result
                
            except Exception as e:
                current_time = time.time()
                elapsed = current_time - start_time
                
                attempt = RetryAttempt(
                    attempt_number=attempt_num,
                    exception=e,
                    delay=0.0,  # Will be set below if retrying
                    timestamp=datetime.utcnow(),
                    total_elapsed=elapsed
                )
                attempts.append(attempt)
                
                # Check if we should retry
                if attempt_num >= self.config.max_attempts or not self._is_retryable(e):
                    self.exhausted_counter.increment(tags={
                        "policy": self.config.name,
                        "exception_type": type(e).__name__,
                        "attempts_used": str(attempt_num)
                    })
                    
                    self.logger.error(
                        f"Async retry exhausted after {attempt_num} attempts",
                        policy=self.config.name,
                        attempts=attempt_num,
                        total_elapsed=elapsed,
                        last_exception=str(e),
                        exc_info=True
                    )
                    
                    raise RetryExhaustedError(
                        f"Retry policy '{self.config.name}' exhausted after {attempt_num} attempts",
                        attempts,
                        e
                    )
                
                # Calculate delay and wait
                delay = self._calculate_delay(attempt_num)
                attempt.delay = delay
                
                self.retry_delay_histogram.observe(delay, tags={
                    "policy": self.config.name,
                    "attempt": str(attempt_num)
                })
                
                self.logger.warning(
                    f"Async attempt {attempt_num} failed, retrying in {delay:.2f}s",
                    policy=self.config.name,
                    attempt=attempt_num,
                    delay=delay,
                    exception=str(e)
                )
                
                await asyncio.sleep(delay)
        
        # This shouldn't be reached, but just in case
        raise RetryExhaustedError(
            f"Retry policy '{self.config.name}' exhausted",
            attempts,
            attempts[-1].exception if attempts else Exception("Unknown error")
        )

class RetryPolicyRegistry:
    """Registry for managing retry policies."""
    
    def __init__(self):
        self.policies: dict[str, RetryPolicy] = {}
        self.logger = get_logger(__name__)
    
    def get_policy(self, name: str, config: Optional[RetryConfig] = None) -> RetryPolicy:
        """Get or create a retry policy."""
        if name not in self.policies:
            if config is None:
                config = RetryConfig(name=name)
            self.policies[name] = RetryPolicy(config)
            self.logger.info(f"Created retry policy: {name}")
        
        return self.policies[name]
    
    def remove_policy(self, name: str):
        """Remove a retry policy from the registry."""
        if name in self.policies:
            del self.policies[name]
            self.logger.info(f"Removed retry policy: {name}")

# Global retry policy registry
retry_policy_registry = RetryPolicyRegistry()

def get_retry_policy(name: str, config: Optional[RetryConfig] = None) -> RetryPolicy:
    """Get or create a retry policy from the global registry."""
    return retry_policy_registry.get_policy(name, config)

def retry(name: str, config: Optional[RetryConfig] = None):
    """Decorator for adding retry logic to functions."""
    def decorator(func):
        policy = get_retry_policy(name, config)
        
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                return await policy.execute_async(func, *args, **kwargs)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                return policy.execute(func, *args, **kwargs)
            return sync_wrapper
    
    return decorator

# Predefined retry configurations for common scenarios
DATABASE_RETRY_CONFIG = RetryConfig(
    name="database",
    max_attempts=3,
    base_delay=0.5,
    max_delay=10.0,
    backoff_strategy=BackoffStrategy.EXPONENTIAL,
    backoff_multiplier=2.0,
    jitter=True,
    retryable_exceptions=(Exception,),
    non_retryable_exceptions=()
)

API_RETRY_CONFIG = RetryConfig(
    name="api",
    max_attempts=3,
    base_delay=1.0,
    max_delay=30.0,
    backoff_strategy=BackoffStrategy.EXPONENTIAL,
    backoff_multiplier=2.0,
    jitter=True,
    retryable_exceptions=(Exception,),
    non_retryable_exceptions=()
)

AUTOTRADER_RETRY_CONFIG = RetryConfig(
    name="autotrader",
    max_attempts=2,
    base_delay=2.0,
    max_delay=60.0,
    backoff_strategy=BackoffStrategy.EXPONENTIAL,
    backoff_multiplier=3.0,
    jitter=True,
    retryable_exceptions=(Exception,),
    non_retryable_exceptions=()
)

REDIS_RETRY_CONFIG = RetryConfig(
    name="redis",
    max_attempts=2,
    base_delay=0.1,
    max_delay=5.0,
    backoff_strategy=BackoffStrategy.LINEAR,
    backoff_multiplier=2.0,
    jitter=True,
    retryable_exceptions=(Exception,),
    non_retryable_exceptions=()
)

# Convenience functions for common retry patterns
def retry_with_exponential_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    multiplier: float = 2.0
):
    """Create retry decorator with exponential backoff."""
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        backoff_strategy=BackoffStrategy.EXPONENTIAL,
        backoff_multiplier=multiplier,
        jitter=True
    )
    return retry("exponential_backoff", config)

def retry_with_linear_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0
):
    """Create retry decorator with linear backoff."""
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        backoff_strategy=BackoffStrategy.LINEAR,
        jitter=True
    )
    return retry("linear_backoff", config)

def retry_with_fixed_delay(
    max_attempts: int = 3,
    delay: float = 1.0
):
    """Create retry decorator with fixed delay."""
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=delay,
        max_delay=delay,
        backoff_strategy=BackoffStrategy.FIXED,
        jitter=False
    )
    return retry("fixed_delay", config)

# Retry policy builder for fluent configuration
class RetryPolicyBuilder:
    """Builder for creating retry policies with fluent interface."""
    
    def __init__(self, name: str):
        self.config = RetryConfig(name=name)
    
    def max_attempts(self, attempts: int) -> 'RetryPolicyBuilder':
        """Set maximum number of attempts."""
        self.config.max_attempts = attempts
        return self
    
    def base_delay(self, delay: float) -> 'RetryPolicyBuilder':
        """Set base delay in seconds."""
        self.config.base_delay = delay
        return self
    
    def max_delay(self, delay: float) -> 'RetryPolicyBuilder':
        """Set maximum delay in seconds."""
        self.config.max_delay = delay
        return self
    
    def exponential_backoff(self, multiplier: float = 2.0) -> 'RetryPolicyBuilder':
        """Use exponential backoff strategy."""
        self.config.backoff_strategy = BackoffStrategy.EXPONENTIAL
        self.config.backoff_multiplier = multiplier
        return self
    
    def linear_backoff(self, multiplier: float = 2.0) -> 'RetryPolicyBuilder':
        """Use linear backoff strategy."""
        self.config.backoff_strategy = BackoffStrategy.LINEAR
        self.config.backoff_multiplier = multiplier
        return self
    
    def fixed_backoff(self) -> 'RetryPolicyBuilder':
        """Use fixed backoff strategy."""
        self.config.backoff_strategy = BackoffStrategy.FIXED
        return self
    
    def with_jitter(self, max_jitter: float = 0.1) -> 'RetryPolicyBuilder':
        """Enable jitter with maximum jitter fraction."""
        self.config.jitter = True
        self.config.jitter_max = max_jitter
        return self
    
    def without_jitter(self) -> 'RetryPolicyBuilder':
        """Disable jitter."""
        self.config.jitter = False
        return self
    
    def retryable_exceptions(self, *exceptions: Type[Exception]) -> 'RetryPolicyBuilder':
        """Set retryable exception types."""
        self.config.retryable_exceptions = exceptions
        return self
    
    def non_retryable_exceptions(self, *exceptions: Type[Exception]) -> 'RetryPolicyBuilder':
        """Set non-retryable exception types."""
        self.config.non_retryable_exceptions = exceptions
        return self
    
    def build(self) -> RetryPolicy:
        """Build the retry policy."""
        return RetryPolicy(self.config)
    
    def as_decorator(self):
        """Return as decorator function."""
        return retry(self.config.name, self.config)

def retry_policy(name: str) -> RetryPolicyBuilder:
    """Create a retry policy builder."""
    return RetryPolicyBuilder(name)