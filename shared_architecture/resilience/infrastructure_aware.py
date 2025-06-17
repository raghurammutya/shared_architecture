"""
Infrastructure-Aware Service Layer
Provides graceful degradation and fallback mechanisms for core operations

This module offers a unified approach to handle infrastructure failures across
all microservices, with automatic fallback strategies and operation mode management.
"""

import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum
import json
from datetime import datetime

from shared_architecture.utils.enhanced_logging import get_logger
from shared_architecture.connections.connection_manager import connection_manager
from shared_architecture.monitoring.metrics_collector import MetricsCollector

logger = get_logger(__name__)

class OperationMode(Enum):
    """System operation modes based on infrastructure health."""
    FULL_OPERATION = "full_operation"
    DEGRADED_OPERATION = "degraded_operation"
    EMERGENCY_MODE = "emergency_mode"
    READ_ONLY = "read_only"

@dataclass
class OperationResult:
    """Result of an infrastructure-aware operation."""
    success: bool
    data: Any = None
    mode: OperationMode = OperationMode.FULL_OPERATION
    warnings: List[str] = None
    errors: List[str] = None
    fallback_used: bool = False
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.errors is None:
            self.errors = []

class InfrastructureAwareService:
    """
    Service layer that adapts operations based on infrastructure health.
    
    This class provides:
    - Automatic fallback mechanisms
    - Graceful degradation based on system health
    - In-memory fallback storage when external systems fail
    - Operation mode management
    - System health monitoring and recommendations
    """
    
    def __init__(self):
        self.operation_mode = OperationMode.FULL_OPERATION
        self._last_health_check = None
        self._fallback_data = {}
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        
        # Initialize metrics
        self.metrics = MetricsCollector.get_instance()
        self.operation_counter = self.metrics.counter(
            "infrastructure_aware_operations_total",
            "Total operations executed with infrastructure awareness",
            tags={"service": "infrastructure_aware"}
        )
        self.fallback_counter = self.metrics.counter(
            "infrastructure_aware_fallbacks_total",
            "Total fallback operations executed",
            tags={"service": "infrastructure_aware"}
        )
        self.mode_gauge = self.metrics.gauge(
            "infrastructure_aware_mode",
            "Current operation mode (1=full, 2=degraded, 3=read_only, 4=emergency)",
            tags={"service": "infrastructure_aware"}
        )
    
    async def execute_with_fallback(self, 
                              primary_operation: Callable,
                              fallback_operation: Optional[Callable] = None,
                              operation_name: str = "unknown") -> OperationResult:
        """
        Execute operation with automatic fallback handling.
        
        Args:
            primary_operation: The main operation to execute
            fallback_operation: Optional fallback operation if primary fails
            operation_name: Name of the operation for logging and metrics
            
        Returns:
            OperationResult with success status, data, and any warnings/errors
        """
        result = OperationResult(success=False)
        self.operation_counter.increment(tags={"operation": operation_name})
        
        try:
            # Update operation mode based on infrastructure health
            await self._update_operation_mode()
            result.mode = self.operation_mode
            
            # Try primary operation
            if self.operation_mode in [OperationMode.FULL_OPERATION, OperationMode.DEGRADED_OPERATION]:
                try:
                    # Support both sync and async operations
                    if asyncio.iscoroutinefunction(primary_operation):
                        data = await primary_operation()
                    else:
                        data = primary_operation()
                    
                    result.success = True
                    result.data = data
                    
                    if self.operation_mode == OperationMode.DEGRADED_OPERATION:
                        result.warnings.append("Operating in degraded mode due to infrastructure issues")
                    
                    return result
                    
                except Exception as e:
                    self.logger.warning(f"Primary operation '{operation_name}' failed: {e}")
                    result.errors.append(f"Primary operation failed: {str(e)}")
            
            # Try fallback operation
            if fallback_operation and self.operation_mode != OperationMode.EMERGENCY_MODE:
                try:
                    self.logger.info(f"Attempting fallback for operation '{operation_name}'")
                    
                    # Support both sync and async fallback operations
                    if asyncio.iscoroutinefunction(fallback_operation):
                        data = await fallback_operation()
                    else:
                        data = fallback_operation()
                    
                    result.success = True
                    result.data = data
                    result.fallback_used = True
                    result.warnings.append(f"Used fallback mechanism for {operation_name}")
                    
                    self.fallback_counter.increment(tags={"operation": operation_name})
                    return result
                    
                except Exception as e:
                    self.logger.error(f"Fallback operation '{operation_name}' failed: {e}")
                    result.errors.append(f"Fallback operation failed: {str(e)}")
            
            # Emergency/read-only mode handling
            if self.operation_mode == OperationMode.EMERGENCY_MODE:
                result.errors.append("System in emergency mode - operation blocked")
            elif self.operation_mode == OperationMode.READ_ONLY:
                result.errors.append("System in read-only mode - write operations blocked")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Critical error in execute_with_fallback for '{operation_name}': {e}", exc_info=True)
            result.errors.append(f"Critical system error: {str(e)}")
            return result
    
    async def _update_operation_mode(self):
        """Update operation mode based on infrastructure health."""
        try:
            health_status = await connection_manager.health_check()
            
            # Count healthy vs unhealthy services
            total_services = len(health_status)
            healthy_services = sum(1 for status in health_status.values() 
                                 if status.get("status") == "healthy")
            degraded_services = sum(1 for status in health_status.values() 
                                  if status.get("status") == "degraded")
            
            # Determine operation mode
            if healthy_services == total_services:
                new_mode = OperationMode.FULL_OPERATION
            elif healthy_services + degraded_services >= total_services * 0.7:  # 70% threshold
                new_mode = OperationMode.DEGRADED_OPERATION
            elif healthy_services + degraded_services >= total_services * 0.3:  # 30% threshold
                new_mode = OperationMode.READ_ONLY
            else:
                new_mode = OperationMode.EMERGENCY_MODE
            
            # Log mode changes
            if not hasattr(self, '_last_operation_mode') or self._last_operation_mode != new_mode:
                self.logger.warning(f"Operation mode changed from {getattr(self, '_last_operation_mode', 'unknown')} to: {new_mode.value}")
                self._last_operation_mode = new_mode
                
                # Update metrics
                mode_value = {
                    OperationMode.FULL_OPERATION: 1,
                    OperationMode.DEGRADED_OPERATION: 2,
                    OperationMode.READ_ONLY: 3,
                    OperationMode.EMERGENCY_MODE: 4
                }.get(new_mode, 0)
                self.mode_gauge.set(mode_value)
            
            self.operation_mode = new_mode
            
        except Exception as e:
            self.logger.error(f"Error updating operation mode: {e}")
            # Default to degraded mode on error
            self.operation_mode = OperationMode.DEGRADED_OPERATION
    
    async def store_data_with_fallback(self, key: str, data: Any, ttl: int = 3600) -> OperationResult:
        """
        Store data with Redis fallback to in-memory storage.
        
        Args:
            key: Storage key
            data: Data to store
            ttl: Time to live in seconds (default: 1 hour)
            
        Returns:
            OperationResult indicating success/failure and storage location
        """
        async def primary_redis_store():
            redis_conn = connection_manager.get_redis_connection()
            
            # Store as JSON string
            json_data = json.dumps(data) if not isinstance(data, str) else data
            await redis_conn.setex(key, ttl, json_data)
            return {"stored": True, "location": "redis", "key": key}
        
        def fallback_memory_store():
            # Store in fallback memory
            self._fallback_data[key] = {
                "data": data,
                "timestamp": datetime.utcnow().isoformat(),
                "ttl": ttl
            }
            self.logger.warning(f"Stored {key} in fallback memory storage")
            return {"stored": True, "location": "memory", "key": key}
        
        return await self.execute_with_fallback(
            primary_operation=primary_redis_store,
            fallback_operation=fallback_memory_store,
            operation_name=f"store_data_{key}"
        )
    
    async def retrieve_data_with_fallback(self, key: str) -> OperationResult:
        """
        Retrieve data with Redis fallback to in-memory storage.
        
        Args:
            key: Storage key
            
        Returns:
            OperationResult with retrieved data or error
        """
        async def primary_redis_retrieve():
            redis_conn = connection_manager.get_redis_connection()
            
            data = await redis_conn.get(key)
            if data is None:
                raise Exception(f"Key {key} not found in Redis")
            
            # Try to parse as JSON
            try:
                parsed_data = json.loads(data)
                return parsed_data
            except json.JSONDecodeError:
                return data
        
        def fallback_memory_retrieve():
            if key not in self._fallback_data:
                raise Exception(f"Key {key} not found in fallback storage")
            
            stored_item = self._fallback_data[key]
            
            # Check TTL
            stored_time = datetime.fromisoformat(stored_item["timestamp"])
            current_time = datetime.utcnow()
            if (current_time - stored_time).total_seconds() > stored_item["ttl"]:
                del self._fallback_data[key]
                raise Exception(f"Key {key} expired in fallback storage")
            
            return stored_item["data"]
        
        return await self.execute_with_fallback(
            primary_operation=primary_redis_retrieve,
            fallback_operation=fallback_memory_retrieve,
            operation_name=f"retrieve_data_{key}"
        )
    
    async def get_system_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system status.
        
        Returns:
            Dictionary with operation mode, health status, and recommendations
        """
        try:
            health_status = await connection_manager.health_check()
        except Exception as e:
            self.logger.error(f"Error getting health status: {e}")
            health_status = {}
        
        return {
            "operation_mode": self.operation_mode.value,
            "infrastructure_health": health_status,
            "fallback_data_keys": len(self._fallback_data),
            "system_resilience": self._calculate_resilience_score(health_status),
            "recommendations": self._get_operational_recommendations(health_status),
            "last_health_check": self._last_health_check.isoformat() if self._last_health_check else None
        }
    
    def _calculate_resilience_score(self, health_status: Dict) -> float:
        """
        Calculate system resilience score (0-100).
        
        Args:
            health_status: Service health status dictionary
            
        Returns:
            Resilience score from 0 to 100
        """
        if not health_status:
            return 0.0
        
        total_services = len(health_status)
        healthy_count = sum(1 for status in health_status.values() 
                           if status.get("status") == "healthy")
        degraded_count = sum(1 for status in health_status.values() 
                            if status.get("status") == "degraded")
        
        # Healthy services = 100%, Degraded = 50%, Unhealthy = 0%
        score = (healthy_count * 100 + degraded_count * 50) / total_services
        return round(score, 1)
    
    def _get_operational_recommendations(self, health_status: Dict) -> List[str]:
        """
        Get operational recommendations based on system health.
        
        Args:
            health_status: Service health status dictionary
            
        Returns:
            List of recommendations for system operators
        """
        recommendations = []
        
        for service, status in health_status.items():
            if status.get("status") == "unhealthy":
                recommendations.append(f"Service '{service}' is unhealthy - check service logs and restart if needed")
            elif status.get("status") == "degraded":
                recommendations.append(f"Service '{service}' is degraded - monitor performance and consider maintenance")
            elif status.get("status") == "unavailable":
                recommendations.append(f"Service '{service}' is not initialized - check configuration and dependencies")
        
        if self.operation_mode == OperationMode.DEGRADED_OPERATION:
            recommendations.append("System in degraded mode - non-critical features may be limited")
        elif self.operation_mode == OperationMode.READ_ONLY:
            recommendations.append("System in read-only mode - write operations are blocked")
        elif self.operation_mode == OperationMode.EMERGENCY_MODE:
            recommendations.append("System in emergency mode - immediate intervention required")
        
        if len(self._fallback_data) > 0:
            recommendations.append(f"{len(self._fallback_data)} items in fallback storage - data will be lost on restart")
        
        return recommendations
    
    def clear_fallback_storage(self):
        """Clear all data from fallback storage."""
        count = len(self._fallback_data)
        self._fallback_data.clear()
        self.logger.info(f"Cleared {count} items from fallback storage")
        return count

# Import asyncio only when needed
import asyncio

# Global infrastructure-aware service instance
infrastructure_service = InfrastructureAwareService()

# Convenience decorators
def with_fallback(fallback_func: Optional[Callable] = None, operation_name: Optional[str] = None):
    """
    Decorator to add infrastructure-aware fallback to functions.
    
    Args:
        fallback_func: Optional fallback function
        operation_name: Optional operation name for logging
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            name = operation_name or func.__name__
            return await infrastructure_service.execute_with_fallback(
                primary_operation=lambda: func(*args, **kwargs),
                fallback_operation=fallback_func,
                operation_name=name
            )
        
        def sync_wrapper(*args, **kwargs):
            name = operation_name or func.__name__
            return asyncio.run(infrastructure_service.execute_with_fallback(
                primary_operation=lambda: func(*args, **kwargs),
                fallback_operation=fallback_func,
                operation_name=name
            ))
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator