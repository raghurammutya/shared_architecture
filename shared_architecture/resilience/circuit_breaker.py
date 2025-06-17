# shared_architecture/resilience/circuit_breaker.py
"""
Circuit breaker pattern implementation for resilient service communication.
Prevents cascade failures by stopping calls to failing services.
"""

import asyncio
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, Union, TypeVar, Generic
from dataclasses import dataclass
from enum import Enum
from contextlib import asynccontextmanager, contextmanager

from shared_architecture.utils.enhanced_logging import get_logger
from shared_architecture.monitoring.metrics_collector import MetricsCollector, trade_metrics

logger = get_logger(__name__)

T = TypeVar('T')

class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, failing fast
    HALF_OPEN = "half_open"  # Testing if service has recovered

@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5  # Number of failures before opening
    recovery_timeout: float = 60.0  # Seconds before trying half-open
    success_threshold: int = 2  # Successes needed to close from half-open
    timeout: float = 30.0  # Request timeout in seconds
    expected_exception: tuple = (Exception,)  # Exceptions that count as failures
    ignore_exceptions: tuple = ()  # Exceptions to ignore
    name: str = "circuit_breaker"

@dataclass
class CircuitBreakerStats:
    """Circuit breaker statistics."""
    state: CircuitState
    failure_count: int
    success_count: int
    total_requests: int
    last_failure_time: Optional[datetime]
    state_changed_time: datetime
    next_attempt_time: Optional[datetime]

class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open."""
    def __init__(self, message: str, circuit_name: str, stats: CircuitBreakerStats):
        super().__init__(message)
        self.circuit_name = circuit_name
        self.stats = stats

class CircuitBreaker(Generic[T]):
    """
    Circuit breaker implementation with automatic failure detection and recovery.
    
    The circuit breaker has three states:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Circuit is open, requests fail fast
    - HALF_OPEN: Testing if service has recovered
    """
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.total_requests = 0
        self.last_failure_time: Optional[datetime] = None
        self.state_changed_time = datetime.utcnow()
        self._lock = threading.Lock()
        self.logger = get_logger(f"circuit_breaker.{config.name}")
        
        # Metrics
        self.metrics_collector = MetricsCollector.get_instance()
        self.state_gauge = self.metrics_collector.gauge(
            f"circuit_breaker_state",
            "Circuit breaker state (0=closed, 1=half_open, 2=open)",
            tags={"circuit": config.name}
        )
        self.requests_counter = self.metrics_collector.counter(
            f"circuit_breaker_requests_total",
            "Total requests through circuit breaker",
            tags={"circuit": config.name}
        )
        self.failures_counter = self.metrics_collector.counter(
            f"circuit_breaker_failures_total", 
            "Total failures in circuit breaker",
            tags={"circuit": config.name}
        )
        
        # Initial state metric
        self._update_state_metric()
    
    def get_stats(self) -> CircuitBreakerStats:
        """Get current circuit breaker statistics."""
        with self._lock:
            next_attempt_time = None
            if self.state == CircuitState.OPEN and self.last_failure_time:
                next_attempt_time = self.last_failure_time + timedelta(seconds=self.config.recovery_timeout)
            
            return CircuitBreakerStats(
                state=self.state,
                failure_count=self.failure_count,
                success_count=self.success_count,
                total_requests=self.total_requests,
                last_failure_time=self.last_failure_time,
                state_changed_time=self.state_changed_time,
                next_attempt_time=next_attempt_time
            )
    
    def _update_state_metric(self):
        """Update the state metric."""
        state_value = {
            CircuitState.CLOSED: 0,
            CircuitState.HALF_OPEN: 1,
            CircuitState.OPEN: 2
        }[self.state]
        self.state_gauge.set(state_value)
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset from OPEN to HALF_OPEN."""
        if self.state != CircuitState.OPEN:
            return False
        
        if not self.last_failure_time:
            return True
        
        return datetime.utcnow() >= self.last_failure_time + timedelta(seconds=self.config.recovery_timeout)
    
    def _record_success(self):
        """Record a successful request."""
        with self._lock:
            self.total_requests += 1
            
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                self.logger.info(
                    f"Success in HALF_OPEN state",
                    circuit=self.config.name,
                    success_count=self.success_count,
                    success_threshold=self.config.success_threshold
                )
                
                if self.success_count >= self.config.success_threshold:
                    self._transition_to_closed()
            
            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success in CLOSED state
                if self.failure_count > 0:
                    self.failure_count = 0
    
    def _record_failure(self, exception: Exception):
        """Record a failed request."""
        with self._lock:
            self.total_requests += 1
            self.failure_count += 1
            self.last_failure_time = datetime.utcnow()
            
            self.failures_counter.increment(tags={
                "circuit": self.config.name,
                "exception_type": type(exception).__name__
            })
            
            self.logger.warning(
                f"Request failed",
                circuit=self.config.name,
                failure_count=self.failure_count,
                exception=str(exception),
                state=self.state.value
            )
            
            if self.state == CircuitState.CLOSED:
                if self.failure_count >= self.config.failure_threshold:
                    self._transition_to_open()
            
            elif self.state == CircuitState.HALF_OPEN:
                self._transition_to_open()
    
    def _transition_to_open(self):
        """Transition circuit breaker to OPEN state."""
        old_state = self.state
        self.state = CircuitState.OPEN
        self.success_count = 0
        self.state_changed_time = datetime.utcnow()
        self._update_state_metric()
        
        self.logger.error(
            f"Circuit breaker opened",
            circuit=self.config.name,
            previous_state=old_state.value,
            failure_count=self.failure_count,
            failure_threshold=self.config.failure_threshold
        )
        
        trade_metrics.errors.increment(tags={
            "type": "circuit_breaker_opened",
            "circuit": self.config.name
        })
    
    def _transition_to_half_open(self):
        """Transition circuit breaker to HALF_OPEN state."""
        old_state = self.state
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        self.state_changed_time = datetime.utcnow()
        self._update_state_metric()
        
        self.logger.info(
            f"Circuit breaker half-opened",
            circuit=self.config.name,
            previous_state=old_state.value
        )
    
    def _transition_to_closed(self):
        """Transition circuit breaker to CLOSED state."""
        old_state = self.state
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.state_changed_time = datetime.utcnow()
        self._update_state_metric()
        
        self.logger.info(
            f"Circuit breaker closed",
            circuit=self.config.name,
            previous_state=old_state.value
        )
    
    def _can_execute(self) -> bool:
        """Check if request can be executed."""
        with self._lock:
            if self.state == CircuitState.CLOSED:
                return True
            
            elif self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._transition_to_half_open()
                    return True
                return False
            
            elif self.state == CircuitState.HALF_OPEN:
                return True
            
            return False
    
    def call(self, func: Callable[[], T], *args, **kwargs) -> T:
        """
        Execute a function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerError: If circuit is open
        """
        self.requests_counter.increment(tags={"circuit": self.config.name})
        
        if not self._can_execute():
            stats = self.get_stats()
            raise CircuitBreakerError(
                f"Circuit breaker '{self.config.name}' is OPEN",
                self.config.name,
                stats
            )
        
        try:
            start_time = time.time()
            result = func(*args, **kwargs)
            duration = (time.time() - start_time) * 1000
            
            self._record_success()
            
            trade_metrics.api_response_time.record(duration, tags={
                "circuit": self.config.name,
                "status": "success"
            })
            
            return result
            
        except self.config.ignore_exceptions:
            # These exceptions don't count as failures
            raise
            
        except self.config.expected_exception as e:
            self._record_failure(e)
            raise
    
    async def call_async(self, func: Callable[[], Union[T, Any]], *args, **kwargs) -> T:
        """
        Execute an async function with circuit breaker protection.
        
        Args:
            func: Async function to execute
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerError: If circuit is open
        """
        self.requests_counter.increment(tags={"circuit": self.config.name})
        
        if not self._can_execute():
            stats = self.get_stats()
            raise CircuitBreakerError(
                f"Circuit breaker '{self.config.name}' is OPEN",
                self.config.name,
                stats
            )
        
        try:
            start_time = time.time()
            
            # Execute with timeout
            result = await asyncio.wait_for(
                func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs),
                timeout=self.config.timeout
            )
            
            duration = (time.time() - start_time) * 1000
            
            self._record_success()
            
            trade_metrics.api_response_time.record(duration, tags={
                "circuit": self.config.name,
                "status": "success"
            })
            
            return result
            
        except asyncio.TimeoutError as e:
            duration = (time.time() - start_time) * 1000
            trade_metrics.api_response_time.record(duration, tags={
                "circuit": self.config.name,
                "status": "timeout"
            })
            self._record_failure(e)
            raise
            
        except self.config.ignore_exceptions:
            # These exceptions don't count as failures
            raise
            
        except self.config.expected_exception as e:
            duration = (time.time() - start_time) * 1000
            trade_metrics.api_response_time.record(duration, tags={
                "circuit": self.config.name,
                "status": "error"
            })
            self._record_failure(e)
            raise
    
    @contextmanager
    def protect(self):
        """Context manager for protecting code blocks."""
        if not self._can_execute():
            stats = self.get_stats()
            raise CircuitBreakerError(
                f"Circuit breaker '{self.config.name}' is OPEN",
                self.config.name,
                stats
            )
        
        self.requests_counter.increment(tags={"circuit": self.config.name})
        start_time = time.time()
        
        try:
            yield
            duration = (time.time() - start_time) * 1000
            self._record_success()
            
            trade_metrics.api_response_time.record(duration, tags={
                "circuit": self.config.name,
                "status": "success"
            })
            
        except self.config.ignore_exceptions:
            raise
            
        except self.config.expected_exception as e:
            duration = (time.time() - start_time) * 1000
            trade_metrics.api_response_time.record(duration, tags={
                "circuit": self.config.name,
                "status": "error"
            })
            self._record_failure(e)
            raise
    
    @asynccontextmanager
    async def protect_async(self):
        """Async context manager for protecting code blocks."""
        if not self._can_execute():
            stats = self.get_stats()
            raise CircuitBreakerError(
                f"Circuit breaker '{self.config.name}' is OPEN",
                self.config.name,
                stats
            )
        
        self.requests_counter.increment(tags={"circuit": self.config.name})
        start_time = time.time()
        
        try:
            yield
            duration = (time.time() - start_time) * 1000
            self._record_success()
            
            trade_metrics.api_response_time.record(duration, tags={
                "circuit": self.config.name,
                "status": "success"
            })
            
        except asyncio.TimeoutError as e:
            duration = (time.time() - start_time) * 1000
            trade_metrics.api_response_time.record(duration, tags={
                "circuit": self.config.name,
                "status": "timeout"
            })
            self._record_failure(e)
            raise
            
        except self.config.ignore_exceptions:
            raise
            
        except self.config.expected_exception as e:
            duration = (time.time() - start_time) * 1000
            trade_metrics.api_response_time.record(duration, tags={
                "circuit": self.config.name,
                "status": "error"
            })
            self._record_failure(e)
            raise

class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""
    
    def __init__(self):
        self.breakers: Dict[str, CircuitBreaker] = {}
        self._lock = threading.Lock()
        self.logger = get_logger(__name__)
    
    def get_circuit_breaker(self, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """Get or create a circuit breaker."""
        with self._lock:
            if name not in self.breakers:
                if config is None:
                    config = CircuitBreakerConfig(name=name)
                self.breakers[name] = CircuitBreaker(config)
                self.logger.info(f"Created circuit breaker: {name}")
            
            return self.breakers[name]
    
    def get_all_stats(self) -> Dict[str, CircuitBreakerStats]:
        """Get statistics for all circuit breakers."""
        with self._lock:
            return {name: breaker.get_stats() for name, breaker in self.breakers.items()}
    
    def reset_circuit_breaker(self, name: str):
        """Manually reset a circuit breaker to CLOSED state."""
        with self._lock:
            if name in self.breakers:
                breaker = self.breakers[name]
                with breaker._lock:
                    breaker._transition_to_closed()
                self.logger.info(f"Manually reset circuit breaker: {name}")
    
    def remove_circuit_breaker(self, name: str):
        """Remove a circuit breaker from the registry."""
        with self._lock:
            if name in self.breakers:
                del self.breakers[name]
                self.logger.info(f"Removed circuit breaker: {name}")

# Global circuit breaker registry
circuit_breaker_registry = CircuitBreakerRegistry()

def get_circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
    """Get or create a circuit breaker from the global registry."""
    return circuit_breaker_registry.get_circuit_breaker(name, config)

def circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None):
    """Decorator for protecting functions with circuit breaker."""
    def decorator(func):
        breaker = get_circuit_breaker(name, config)
        
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                return await breaker.call_async(func, *args, **kwargs)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                return breaker.call(func, *args, **kwargs)
            return sync_wrapper
    
    return decorator

# Predefined circuit breakers for common services
DATABASE_CIRCUIT_CONFIG = CircuitBreakerConfig(
    name="database",
    failure_threshold=3,
    recovery_timeout=30.0,
    success_threshold=2,
    timeout=10.0,
    expected_exception=(Exception,)
)

REDIS_CIRCUIT_CONFIG = CircuitBreakerConfig(
    name="redis",
    failure_threshold=5,
    recovery_timeout=20.0,
    success_threshold=2,
    timeout=5.0,
    expected_exception=(Exception,)
)

AUTOTRADER_CIRCUIT_CONFIG = CircuitBreakerConfig(
    name="autotrader",
    failure_threshold=3,
    recovery_timeout=60.0,
    success_threshold=2,
    timeout=30.0,
    expected_exception=(Exception,)
)