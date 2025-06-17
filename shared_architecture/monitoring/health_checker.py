# shared_architecture/monitoring/health_checker.py
"""
Comprehensive health checking system for trade service.
Monitors all critical dependencies and system components.
"""

import asyncio
import time
import psutil
import redis
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import httpx
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from shared_architecture.utils.enhanced_logging import get_logger

logger = get_logger(__name__)

class HealthStatus(Enum):
    """Health check status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class HealthCheckResult:
    """Result of a health check."""
    component: str
    status: HealthStatus
    message: str
    response_time_ms: Optional[float] = None
    timestamp: Optional[datetime] = None
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        result['status'] = self.status.value
        result['timestamp'] = self.timestamp.isoformat() if self.timestamp else None
        return result

@dataclass
class SystemHealth:
    """Overall system health status."""
    overall_status: HealthStatus
    components: List[HealthCheckResult]
    timestamp: datetime
    response_time_ms: float
    system_info: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'overall_status': self.overall_status.value,
            'components': [comp.to_dict() for comp in self.components],
            'timestamp': self.timestamp.isoformat(),
            'response_time_ms': self.response_time_ms,
            'system_info': self.system_info or {}
        }

class BaseHealthCheck:
    """Base class for health checks."""
    
    def __init__(self, name: str, timeout: float = 5.0):
        self.name = name
        self.timeout = timeout
        self.logger = get_logger(f"health.{name}")
    
    async def check(self) -> HealthCheckResult:
        """Perform the health check."""
        start_time = time.time()
        
        try:
            result = await asyncio.wait_for(
                self._perform_check(),
                timeout=self.timeout
            )
            
            response_time = (time.time() - start_time) * 1000
            result.response_time_ms = response_time
            
            self.logger.debug(
                f"Health check completed",
                component=self.name,
                status=result.status.value,
                response_time_ms=response_time
            )
            
            return result
            
        except asyncio.TimeoutError:
            response_time = (time.time() - start_time) * 1000
            self.logger.warning(
                f"Health check timed out",
                component=self.name,
                timeout=self.timeout
            )
            
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timed out after {self.timeout}s",
                response_time_ms=response_time,
                error="timeout"
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            self.logger.error(
                f"Health check failed",
                component=self.name,
                error=str(e),
                exc_info=True
            )
            
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                response_time_ms=response_time,
                error=str(e)
            )
    
    async def _perform_check(self) -> HealthCheckResult:
        """Override this method to implement specific health check logic."""
        raise NotImplementedError("Subclasses must implement _perform_check")

class DatabaseHealthCheck(BaseHealthCheck):
    """Database connectivity and performance health check."""
    
    def __init__(self, engine, timeout: float = 5.0):
        super().__init__("database", timeout)
        self.engine = engine
    
    async def _perform_check(self) -> HealthCheckResult:
        """Check database connectivity and performance."""
        try:
            # Test basic connectivity
            with self.engine.connect() as conn:
                start_time = time.time()
                result = conn.execute(text("SELECT 1")).fetchone()
                query_time = (time.time() - start_time) * 1000
                
                if result[0] != 1:
                    return HealthCheckResult(
                        component=self.name,
                        status=HealthStatus.UNHEALTHY,
                        message="Database query returned unexpected result"
                    )
                
                # Check connection pool status
                pool = self.engine.pool
                pool_status = {
                    "size": pool.size(),
                    "checked_in": pool.checkedin(),
                    "checked_out": pool.checkedout(),
                }
                
                # Determine status based on query time and pool health
                if query_time > 1000:  # > 1 second
                    status = HealthStatus.DEGRADED
                    message = f"Database responding slowly ({query_time:.1f}ms)"
                elif pool.checkedout() / pool.size() > 0.8:  # > 80% pool utilization
                    status = HealthStatus.DEGRADED
                    message = "Database connection pool utilization high"
                else:
                    status = HealthStatus.HEALTHY
                    message = f"Database healthy ({query_time:.1f}ms)"
                
                return HealthCheckResult(
                    component=self.name,
                    status=status,
                    message=message,
                    details={
                        "query_time_ms": query_time,
                        "pool_status": pool_status,
                        "engine_info": {
                            "driver": str(self.engine.driver),
                            "url": str(self.engine.url).split('@')[0] + '@***'  # Hide credentials
                        }
                    }
                )
                
        except SQLAlchemyError as e:
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Database error: {str(e)}",
                error=str(e)
            )

class RedisHealthCheck(BaseHealthCheck):
    """Redis connectivity and performance health check."""
    
    def __init__(self, redis_url: str, timeout: float = 5.0):
        super().__init__("redis", timeout)
        self.redis_url = redis_url
        self.redis_client = None
    
    async def _perform_check(self) -> HealthCheckResult:
        """Check Redis connectivity and performance."""
        try:
            if not self.redis_client:
                self.redis_client = redis.Redis.from_url(self.redis_url)
            
            # Test basic connectivity
            start_time = time.time()
            ping_result = self.redis_client.ping()
            ping_time = (time.time() - start_time) * 1000
            
            if not ping_result:
                return HealthCheckResult(
                    component=self.name,
                    status=HealthStatus.UNHEALTHY,
                    message="Redis ping failed"
                )
            
            # Get Redis info
            info = self.redis_client.info()
            
            # Check memory usage
            used_memory = info.get('used_memory', 0)
            max_memory = info.get('maxmemory', 0)
            memory_usage = (used_memory / max_memory) if max_memory > 0 else 0
            
            # Check connected clients
            connected_clients = info.get('connected_clients', 0)
            
            # Determine status
            if ping_time > 500:  # > 500ms
                status = HealthStatus.DEGRADED
                message = f"Redis responding slowly ({ping_time:.1f}ms)"
            elif memory_usage > 0.9:  # > 90% memory usage
                status = HealthStatus.DEGRADED
                message = f"Redis memory usage high ({memory_usage:.1%})"
            else:
                status = HealthStatus.HEALTHY
                message = f"Redis healthy ({ping_time:.1f}ms)"
            
            return HealthCheckResult(
                component=self.name,
                status=status,
                message=message,
                details={
                    "ping_time_ms": ping_time,
                    "redis_version": info.get('redis_version'),
                    "connected_clients": connected_clients,
                    "used_memory_mb": used_memory / (1024 * 1024),
                    "memory_usage_percent": memory_usage * 100,
                    "uptime_seconds": info.get('uptime_in_seconds')
                }
            )
            
        except redis.RedisError as e:
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Redis error: {str(e)}",
                error=str(e)
            )
        except Exception as e:
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Unexpected Redis error: {str(e)}",
                error=str(e)
            )

class ExternalAPIHealthCheck(BaseHealthCheck):
    """External API endpoint health check."""
    
    def __init__(self, name: str, url: str, timeout: float = 10.0, 
                 expected_status: int = 200, headers: Optional[Dict] = None):
        super().__init__(f"external_api_{name}", timeout)
        self.url = url
        self.expected_status = expected_status
        self.headers = headers or {}
    
    async def _perform_check(self) -> HealthCheckResult:
        """Check external API availability and response time."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                start_time = time.time()
                response = await client.get(self.url, headers=self.headers)
                response_time = (time.time() - start_time) * 1000
                
                # Determine status based on response
                if response.status_code == self.expected_status:
                    if response_time > 5000:  # > 5 seconds
                        status = HealthStatus.DEGRADED
                        message = f"API responding slowly ({response_time:.1f}ms)"
                    else:
                        status = HealthStatus.HEALTHY
                        message = f"API healthy ({response_time:.1f}ms)"
                else:
                    status = HealthStatus.UNHEALTHY
                    message = f"API returned status {response.status_code} (expected {self.expected_status})"
                
                return HealthCheckResult(
                    component=self.name,
                    status=status,
                    message=message,
                    details={
                        "url": self.url,
                        "status_code": response.status_code,
                        "response_time_ms": response_time,
                        "headers": dict(response.headers)
                    }
                )
                
        except httpx.TimeoutException:
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"API request timed out after {self.timeout}s",
                error="timeout"
            )
        except Exception as e:
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"API check failed: {str(e)}",
                error=str(e)
            )

class SystemResourceHealthCheck(BaseHealthCheck):
    """System resource utilization health check."""
    
    def __init__(self, timeout: float = 2.0):
        super().__init__("system_resources", timeout)
    
    async def _perform_check(self) -> HealthCheckResult:
        """Check system resource utilization."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # Network statistics (if available)
            try:
                network = psutil.net_io_counters()
                network_stats = {
                    "bytes_sent": network.bytes_sent,
                    "bytes_recv": network.bytes_recv,
                    "packets_sent": network.packets_sent,
                    "packets_recv": network.packets_recv
                }
            except:
                network_stats = {}
            
            # Determine overall status
            if cpu_percent > 90 or memory_percent > 90 or disk_percent > 90:
                status = HealthStatus.UNHEALTHY
                message = "System resources critically high"
            elif cpu_percent > 80 or memory_percent > 80 or disk_percent > 80:
                status = HealthStatus.DEGRADED
                message = "System resources elevated"
            else:
                status = HealthStatus.HEALTHY
                message = "System resources normal"
            
            return HealthCheckResult(
                component=self.name,
                status=status,
                message=message,
                details={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory_percent,
                    "memory_total_gb": memory.total / (1024**3),
                    "memory_available_gb": memory.available / (1024**3),
                    "disk_percent": disk_percent,
                    "disk_total_gb": disk.total / (1024**3),
                    "disk_free_gb": disk.free / (1024**3),
                    "network_stats": network_stats,
                    "load_average": list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else None
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNKNOWN,
                message=f"Could not check system resources: {str(e)}",
                error=str(e)
            )

class ApplicationHealthCheck(BaseHealthCheck):
    """Application-specific health check."""
    
    def __init__(self, timeout: float = 3.0):
        super().__init__("application", timeout)
    
    async def _perform_check(self) -> HealthCheckResult:
        """Check application-specific health indicators."""
        try:
            # Check application version
            try:
                from app import __version__
                app_version = __version__
            except:
                app_version = "unknown"
            
            # Check critical configuration
            config_status = self._check_configuration()
            
            # Check recent error rates (would integrate with error tracking)
            error_rate = await self._check_error_rate()
            
            # Determine status
            if not config_status["valid"]:
                status = HealthStatus.UNHEALTHY
                message = f"Configuration error: {config_status['error']}"
            elif error_rate > 0.1:  # > 10% error rate
                status = HealthStatus.DEGRADED
                message = f"High error rate: {error_rate:.1%}"
            else:
                status = HealthStatus.HEALTHY
                message = "Application healthy"
            
            return HealthCheckResult(
                component=self.name,
                status=status,
                message=message,
                details={
                    "version": app_version,
                    "configuration": config_status,
                    "error_rate": error_rate,
                    "uptime_seconds": time.time() - psutil.Process().create_time()
                }
            )
            
        except Exception as e:
            return HealthCheckResult(
                component=self.name,
                status=HealthStatus.UNKNOWN,
                message=f"Application health check failed: {str(e)}",
                error=str(e)
            )
    
    def _check_configuration(self) -> Dict[str, Any]:
        """Check critical configuration parameters."""
        try:
            import os
            
            required_env_vars = [
                "DATABASE_URL",
                "REDIS_URL"
            ]
            
            missing_vars = []
            for var in required_env_vars:
                if not os.getenv(var):
                    missing_vars.append(var)
            
            if missing_vars:
                return {
                    "valid": False,
                    "error": f"Missing environment variables: {', '.join(missing_vars)}"
                }
            
            return {"valid": True, "error": None}
            
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    async def _check_error_rate(self) -> float:
        """Check recent error rate (placeholder - would integrate with metrics)."""
        # This would integrate with actual metrics collection
        # For now, return a simulated low error rate
        return 0.01  # 1% error rate

class HealthChecker:
    """Comprehensive health checking orchestrator."""
    
    def __init__(self):
        self.checks: List[BaseHealthCheck] = []
        self.logger = get_logger(__name__)
        self._last_check_time: Optional[datetime] = None
        self._last_results: Optional[SystemHealth] = None
        self._cache_duration = timedelta(seconds=30)  # Cache results for 30 seconds
    
    def add_check(self, health_check: BaseHealthCheck):
        """Add a health check to the system."""
        self.checks.append(health_check)
        self.logger.info(f"Added health check: {health_check.name}")
    
    async def check_all(self, use_cache: bool = True) -> SystemHealth:
        """Perform all health checks and return aggregated results."""
        # Check cache
        if (use_cache and self._last_results and self._last_check_time and 
            datetime.utcnow() - self._last_check_time < self._cache_duration):
            self.logger.debug("Returning cached health check results")
            return self._last_results
        
        start_time = time.time()
        
        self.logger.info(f"Starting health checks for {len(self.checks)} components")
        
        # Run all health checks concurrently
        tasks = [check.check() for check in self.checks]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        component_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Handle failed health checks
                component_results.append(HealthCheckResult(
                    component=self.checks[i].name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check failed: {str(result)}",
                    error=str(result)
                ))
            else:
                component_results.append(result)
        
        # Determine overall status
        overall_status = self._determine_overall_status(component_results)
        
        total_time = (time.time() - start_time) * 1000
        
        # Create system health result
        system_health = SystemHealth(
            overall_status=overall_status,
            components=component_results,
            timestamp=datetime.utcnow(),
            response_time_ms=total_time,
            system_info=self._get_system_info()
        )
        
        # Cache results
        self._last_results = system_health
        self._last_check_time = datetime.utcnow()
        
        self.logger.info(
            f"Health check completed",
            overall_status=overall_status.value,
            total_time_ms=total_time,
            healthy_components=len([r for r in component_results if r.status == HealthStatus.HEALTHY]),
            total_components=len(component_results)
        )
        
        return system_health
    
    def _determine_overall_status(self, results: List[HealthCheckResult]) -> HealthStatus:
        """Determine overall system status from component results."""
        if not results:
            return HealthStatus.UNKNOWN
        
        statuses = [result.status for result in results]
        
        # If any component is unhealthy, system is unhealthy
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        
        # If any component is degraded, system is degraded
        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        
        # If any component is unknown, system is degraded
        if HealthStatus.UNKNOWN in statuses:
            return HealthStatus.DEGRADED
        
        # All components are healthy
        return HealthStatus.HEALTHY
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get general system information."""
        try:
            import platform
            
            return {
                "hostname": platform.node(),
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "architecture": platform.architecture()[0],
                "processor": platform.processor() or "unknown",
                "boot_time": psutil.boot_time(),
                "timezone": str(datetime.now().astimezone().tzinfo)
            }
        except Exception as e:
            self.logger.warning(f"Could not get system info: {e}")
            return {"error": str(e)}
    
    async def get_component_health(self, component_name: str) -> Optional[HealthCheckResult]:
        """Get health status for a specific component."""
        check = next((c for c in self.checks if c.name == component_name), None)
        if not check:
            return None
        
        return await check.check()
    
    def get_check_names(self) -> List[str]:
        """Get list of all registered health check names."""
        return [check.name for check in self.checks]