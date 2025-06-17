"""
Enhanced Connection Manager with Circuit Breakers and Health Monitoring

This module extends the basic connection manager with advanced resilience features:
- Circuit breakers for each service
- Background health monitoring
- Automatic fallback mechanisms  
- Mock implementations for testing/fallback scenarios
"""

import logging
import time
import os
import asyncio
import threading
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta

from shared_architecture.connections.connection_manager import ConnectionManager
from shared_architecture.utils.enhanced_logging import get_logger
from shared_architecture.monitoring.metrics_collector import MetricsCollector

logger = get_logger(__name__)

class ServiceStatus(Enum):
    """Service health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class ServiceHealth:
    """Health information for a service."""
    status: ServiceStatus
    last_check: datetime
    error_count: int
    last_error: Optional[str]
    response_time: Optional[float]
    circuit_breaker_open: bool = False
    circuit_breaker_opens_at: Optional[datetime] = None

class SimpleCircuitBreaker:
    """Simple circuit breaker implementation to avoid circular imports."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.is_open = False
    
    def __enter__(self):
        if self.is_open:
            # Check if we should try to recover
            if (self.last_failure_time and 
                datetime.utcnow() - self.last_failure_time > timedelta(seconds=self.recovery_timeout)):
                self.is_open = False
                self.failure_count = 0
            else:
                raise RuntimeError("Circuit breaker is open")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.failure_count += 1
            self.last_failure_time = datetime.utcnow()
            if self.failure_count >= self.failure_threshold:
                self.is_open = True
        else:
            # Success - gradually reduce failure count
            self.failure_count = max(0, self.failure_count - 1)
    
    def reset(self):
        """Manually reset the circuit breaker."""
        self.is_open = False
        self.failure_count = 0
        self.last_failure_time = None

class MockRedis:
    """Mock Redis implementation for fallback when Redis is unavailable."""
    
    def __init__(self):
        self._data = {}
        self._expiry = {}
        self.logger = get_logger(f"{__name__}.MockRedis")
        self.logger.info("MockRedis initialized - operations will work but data won't persist")
    
    async def get(self, key):
        """Get value from mock storage."""
        if key in self._expiry and datetime.utcnow() > self._expiry[key]:
            del self._data[key]
            del self._expiry[key]
            return None
        return self._data.get(key)
    
    async def set(self, key, value, ex=None):
        """Set value in mock storage."""
        self._data[key] = value
        if ex:
            self._expiry[key] = datetime.utcnow() + timedelta(seconds=ex)
        return True
    
    async def setex(self, key, time, value):
        """Set value with expiry in mock storage."""
        self._data[key] = value
        self._expiry[key] = datetime.utcnow() + timedelta(seconds=time)
        return True
    
    async def delete(self, *keys):
        """Delete keys from mock storage."""
        count = 0
        for key in keys:
            if key in self._data:
                del self._data[key]
                if key in self._expiry:
                    del self._expiry[key]
                count += 1
        return count
    
    async def exists(self, key):
        """Check if key exists."""
        if key in self._expiry and datetime.utcnow() > self._expiry[key]:
            del self._data[key]
            del self._expiry[key]
            return False
        return key in self._data
    
    async def ping(self):
        """Mock ping response."""
        return True
    
    async def keys(self, pattern="*"):
        """Get keys matching pattern."""
        # Simple pattern matching
        if pattern == "*":
            return list(self._data.keys())
        # Add more sophisticated pattern matching if needed
        return [k for k in self._data.keys() if pattern.replace("*", "") in k]
    
    async def aclose(self):
        """Close mock connection."""
        self.logger.info("MockRedis connection closed")

class EnhancedConnectionManager(ConnectionManager):
    """
    Enhanced connection manager with circuit breakers and health monitoring.
    
    Extends the base ConnectionManager with:
    - Circuit breakers for fault tolerance
    - Background health monitoring
    - Service-specific health checks
    - Fallback implementations for testing/degraded modes
    """
    
    def __init__(self):
        super().__init__()
        self.health_status: Dict[str, ServiceHealth] = {}
        self.circuit_breakers: Dict[str, SimpleCircuitBreaker] = {}
        self._health_check_thread = None
        self._health_check_interval = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))
        self._use_mock_fallbacks = os.getenv("USE_MOCK_FALLBACKS", "true").lower() == "true"
        
        # Initialize metrics
        self.metrics = MetricsCollector.get_instance()
        self.health_check_counter = self.metrics.counter(
            "connection_health_checks_total",
            "Total health checks performed",
            tags={"manager": "enhanced"}
        )
        self.connection_errors_counter = self.metrics.counter(
            "connection_errors_total",
            "Total connection errors",
            tags={"manager": "enhanced"}
        )
        self.service_status_gauge = self.metrics.gauge(
            "service_status",
            "Service status (1=healthy, 2=degraded, 3=unhealthy, 0=unknown)",
            tags={"manager": "enhanced"}
        )
        
        self._initialize_circuit_breakers()
        self._initialize_health_status()
    
    def _initialize_circuit_breakers(self):
        """Initialize circuit breakers for each service."""
        services = ["redis", "mongodb", "timescaledb", "rabbitmq"]
        
        for service in services:
            self.circuit_breakers[service] = SimpleCircuitBreaker(
                failure_threshold=int(os.getenv(f"{service.upper()}_CIRCUIT_BREAKER_THRESHOLD", "5")),
                recovery_timeout=int(os.getenv(f"{service.upper()}_CIRCUIT_BREAKER_TIMEOUT", "60"))
            )
    
    def _initialize_health_status(self):
        """Initialize health status for all services."""
        services = ["redis", "mongodb", "timescaledb", "rabbitmq"]
        
        for service in services:
            self.health_status[service] = ServiceHealth(
                status=ServiceStatus.UNKNOWN,
                last_check=datetime.utcnow(),
                error_count=0,
                last_error=None,
                response_time=None
            )
    
    async def initialize(self, required_services: Optional[List[str]] = None):
        """Initialize connections and start health monitoring."""
        await super().initialize(required_services)
        self._start_health_monitoring()
    
    def get_redis_connection(self):
        """Get Redis connection with circuit breaker and fallback."""
        # Check circuit breaker
        if self.circuit_breakers["redis"].is_open:
            if self._use_mock_fallbacks:
                self.logger.warning("Redis circuit breaker open, using MockRedis fallback")
                return MockRedis()
            else:
                raise RuntimeError("Redis connection unavailable (circuit breaker open)")
        
        try:
            with self.circuit_breakers["redis"]:
                if not self.redis:
                    raise RuntimeError("Redis connection not initialized")
                return self.redis
        except Exception as e:
            self._update_health_status("redis", ServiceStatus.UNHEALTHY, str(e))
            if self._use_mock_fallbacks:
                self.logger.warning(f"Redis connection failed: {e}, using MockRedis fallback")
                return MockRedis()
            raise
    
    async def get_redis_connection_async(self):
        """Get async Redis connection with circuit breaker and fallback."""
        return self.get_redis_connection()
    
    def _update_health_status(self, service: str, status: ServiceStatus, error: Optional[str] = None):
        """Update health status for a service."""
        health = self.health_status[service]
        health.status = status
        health.last_check = datetime.utcnow()
        
        if error:
            health.error_count += 1
            health.last_error = error
            self.connection_errors_counter.increment(tags={"service": service})
        else:
            health.error_count = max(0, health.error_count - 1)  # Gradually reduce error count
        
        # Update metrics
        status_value = {
            ServiceStatus.HEALTHY: 1,
            ServiceStatus.DEGRADED: 2,
            ServiceStatus.UNHEALTHY: 3,
            ServiceStatus.UNKNOWN: 0
        }.get(status, 0)
        self.service_status_gauge.set(status_value, tags={"service": service})
        
        # Update circuit breaker status
        health.circuit_breaker_open = self.circuit_breakers.get(service, None) and self.circuit_breakers[service].is_open
    
    def _start_health_monitoring(self):
        """Start background health monitoring thread."""
        if self._health_check_thread and self._health_check_thread.is_alive():
            return
        
        def health_monitor():
            while True:
                try:
                    # Run health checks in event loop
                    asyncio.run(self._perform_health_checks())
                    time.sleep(self._health_check_interval)
                except Exception as e:
                    self.logger.error(f"Health monitor error: {e}", exc_info=True)
                    time.sleep(60)  # Longer delay on error
        
        self._health_check_thread = threading.Thread(target=health_monitor, daemon=True)
        self._health_check_thread.start()
        self.logger.info(f"Health monitoring started (interval: {self._health_check_interval}s)")
    
    async def _perform_health_checks(self):
        """Perform health checks on all services."""
        self.health_check_counter.increment()
        
        # Check Redis
        await self._health_check_redis()
        
        # Check MongoDB
        await self._health_check_mongodb()
        
        # Check TimescaleDB
        await self._health_check_timescaledb()
        
        # Check RabbitMQ
        await self._health_check_rabbitmq()
    
    async def _health_check_redis(self):
        """Perform Redis health check."""
        try:
            if self.redis:
                start_time = time.time()
                await self.redis.ping()
                response_time = time.time() - start_time
                
                health = self.health_status["redis"]
                health.response_time = response_time
                
                if response_time > 1.0:  # Slow response
                    self._update_health_status("redis", ServiceStatus.DEGRADED, f"Slow response: {response_time:.3f}s")
                else:
                    self._update_health_status("redis", ServiceStatus.HEALTHY)
            else:
                self._update_health_status("redis", ServiceStatus.UNHEALTHY, "Connection not initialized")
        except Exception as e:
            self._update_health_status("redis", ServiceStatus.UNHEALTHY, str(e))
    
    async def _health_check_mongodb(self):
        """Perform MongoDB health check."""
        try:
            if self.mongodb:
                start_time = time.time()
                await asyncio.wait_for(self.mongodb.admin.command("ping"), timeout=5.0)
                response_time = time.time() - start_time
                
                health = self.health_status["mongodb"]
                health.response_time = response_time
                
                if response_time > 2.0:  # Slow response
                    self._update_health_status("mongodb", ServiceStatus.DEGRADED, f"Slow response: {response_time:.3f}s")
                else:
                    self._update_health_status("mongodb", ServiceStatus.HEALTHY)
            else:
                self._update_health_status("mongodb", ServiceStatus.UNHEALTHY, "Connection not initialized")
        except Exception as e:
            self._update_health_status("mongodb", ServiceStatus.UNHEALTHY, str(e))
    
    async def _health_check_timescaledb(self):
        """Perform TimescaleDB health check."""
        try:
            if self.timescaledb:
                start_time = time.time()
                async with self.timescaledb() as session:
                    await session.execute(text("SELECT 1"))
                response_time = time.time() - start_time
                
                health = self.health_status["timescaledb"]
                health.response_time = response_time
                
                if response_time > 2.0:  # Slow response
                    self._update_health_status("timescaledb", ServiceStatus.DEGRADED, f"Slow response: {response_time:.3f}s")
                else:
                    self._update_health_status("timescaledb", ServiceStatus.HEALTHY)
            else:
                self._update_health_status("timescaledb", ServiceStatus.UNHEALTHY, "Connection not initialized")
        except Exception as e:
            self._update_health_status("timescaledb", ServiceStatus.UNHEALTHY, str(e))
    
    async def _health_check_rabbitmq(self):
        """Perform RabbitMQ health check."""
        try:
            if self.rabbitmq and not self.rabbitmq.is_closed:
                # Simple check - just verify connection is not closed
                self._update_health_status("rabbitmq", ServiceStatus.HEALTHY)
            else:
                self._update_health_status("rabbitmq", ServiceStatus.UNHEALTHY, "Connection closed or not initialized")
        except Exception as e:
            self._update_health_status("rabbitmq", ServiceStatus.UNHEALTHY, str(e))
    
    async def health_check(self) -> Dict[str, Dict[str, str]]:
        """Get comprehensive health status including circuit breaker states."""
        base_health = await super().health_check()
        
        # Enhance with circuit breaker and detailed health info
        for service, health in self.health_status.items():
            if service in base_health:
                base_health[service].update({
                    "error_count": health.error_count,
                    "last_error": health.last_error,
                    "response_time": f"{health.response_time:.3f}s" if health.response_time else None,
                    "circuit_breaker_open": health.circuit_breaker_open,
                    "last_check": health.last_check.isoformat()
                })
        
        return base_health
    
    def get_service_health(self, service: str) -> Optional[ServiceHealth]:
        """Get detailed health information for a specific service."""
        return self.health_status.get(service)
    
    def reset_circuit_breaker(self, service: str):
        """Manually reset a circuit breaker for a service."""
        if service in self.circuit_breakers:
            self.circuit_breakers[service].reset()
            self.logger.info(f"Circuit breaker reset for service: {service}")

# Global enhanced connection manager instance
enhanced_connection_manager = EnhancedConnectionManager()