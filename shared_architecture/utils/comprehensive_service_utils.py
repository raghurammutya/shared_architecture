# shared_architecture/utils/comprehensive_service_utils.py
"""
Comprehensive service startup utility that handles all infrastructure concerns,
leaving microservices to focus purely on business logic.

Provides:
- Resilient infrastructure setup with circuit breakers
- Structured logging configuration
- FastAPI app creation with standard middleware
- Configuration loading and validation
- Metrics and monitoring setup
- Error handling and graceful shutdown
- Service discovery registration
- Health check endpoints
- CORS, rate limiting, and security middleware
- Background task management
"""

import os
import sys
import signal
import asyncio
import time
import json
import logging
import traceback
from contextlib import asynccontextmanager
from typing import Optional, Dict, List, Any, Callable, Union
from datetime import datetime, timedelta
import psutil

# FastAPI and middleware imports
from fastapi import FastAPI, Request, Response, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# Shared architecture imports
from shared_architecture.config.config_loader import config_loader
from shared_architecture.utils.logging_utils import configure_logging, log_info, log_exception, get_logger
from shared_architecture.utils.prometheus_metrics import setup_metrics
from shared_architecture.connections.connection_manager import connection_manager
from shared_architecture.resilience.circuit_breaker import get_circuit_breaker, CircuitBreakerConfig
from shared_architecture.monitoring.health_checker import (
    HealthChecker, 
    DatabaseHealthCheck, 
    RedisHealthCheck, 
    SystemResourceHealthCheck,
    ApplicationHealthCheck,
    HealthStatus
)
from shared_architecture.connections.service_discovery import service_discovery

# Service configuration dataclass
from dataclasses import dataclass, field
from enum import Enum

class ServiceType(Enum):
    """Types of microservices with different requirements."""
    TRADE = "trade"
    TICKER = "ticker"
    USER = "user"
    NOTIFICATION = "notification"
    ANALYTICS = "analytics"
    GATEWAY = "gateway"
    GENERIC = "generic"

@dataclass
class ServiceConfig:
    """Configuration for service startup."""
    service_name: str
    service_type: ServiceType = ServiceType.GENERIC
    
    # Infrastructure requirements
    required_services: List[str] = field(default_factory=lambda: ["timescaledb"])
    optional_services: List[str] = field(default_factory=list)
    
    # API configuration
    title: Optional[str] = None
    description: Optional[str] = None
    version: str = "1.0.0"
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"
    openapi_url: str = "/openapi.json"
    
    # Server configuration
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # Middleware configuration
    enable_cors: bool = True
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    cors_methods: List[str] = field(default_factory=lambda: ["*"])
    cors_headers: List[str] = field(default_factory=lambda: ["*"])
    
    enable_rate_limiting: bool = True
    rate_limit_default: str = "100/minute"
    
    enable_compression: bool = True
    enable_trusted_hosts: bool = False
    trusted_hosts: List[str] = field(default_factory=lambda: ["localhost", "127.0.0.1"])
    
    # Health check configuration
    enable_health_checks: bool = True
    health_check_interval: int = 30  # seconds
    
    # Background tasks
    background_tasks: List[Callable] = field(default_factory=list)
    periodic_tasks: Dict[str, Dict] = field(default_factory=dict)  # {name: {func, interval}}
    
    # Circuit breaker configuration
    enable_circuit_breakers: bool = True
    circuit_breaker_configs: Dict[str, CircuitBreakerConfig] = field(default_factory=dict)
    
    # Observability
    enable_request_logging: bool = True
    enable_metrics: bool = True
    enable_tracing: bool = False
    
    # Graceful shutdown
    shutdown_timeout: int = 30  # seconds
    
    def __post_init__(self):
        if self.title is None:
            self.title = f"{self.service_name.replace('_', ' ').title()} Service"
        if self.description is None:
            self.description = f"API for {self.service_name} microservice"

# Global service registry for graceful shutdown
_active_services: Dict[str, FastAPI] = {}
_background_tasks: Dict[str, List[asyncio.Task]] = {}
_shutdown_handlers: Dict[str, List[Callable]] = {}
_service_configs: Dict[str, ServiceConfig] = {}

def start_service(
    service_name: str,
    service_config: Optional[ServiceConfig] = None,
    business_routers: Optional[List[APIRouter]] = None,
    startup_tasks: Optional[List[Callable]] = None,
    shutdown_tasks: Optional[List[Callable]] = None,
    custom_middleware: Optional[List[Callable]] = None,
    **kwargs
) -> FastAPI:
    """
    Comprehensive service initialization that handles all infrastructure concerns.
    
    Args:
        service_name: Name of the microservice
        service_config: Optional ServiceConfig instance for advanced configuration
        business_routers: List of APIRouter instances for business logic
        startup_tasks: Additional startup tasks to run
        shutdown_tasks: Additional shutdown tasks to run
        custom_middleware: Additional middleware to add
        **kwargs: Additional arguments passed to ServiceConfig if not provided
    
    Returns:
        Configured FastAPI application ready to run
    
    Example:
        app = start_service(
            service_name="trade_service",
            business_routers=[trade_router, strategy_router],
            required_services=['redis', 'timescaledb']
        )
    """
    logger = get_logger(__name__)
    
    # Create or use provided service config
    if service_config is None:
        # Extract known ServiceConfig parameters from kwargs
        config_kwargs = {}
        for field_name in ServiceConfig.__dataclass_fields__:
            if field_name in kwargs:
                config_kwargs[field_name] = kwargs.pop(field_name)
        
        service_config = ServiceConfig(service_name=service_name, **config_kwargs)
    
    # Store config globally for shutdown handling
    _service_configs[service_name] = service_config
    
    logger.info(f"🚀 Starting comprehensive initialization for '{service_name}'")
    
    # 1. Load configuration
    _load_configuration(service_name, logger)
    
    # 2. Setup logging
    configure_logging(service_name)
    logger = get_logger(__name__)  # Refresh logger after configuration
    
    # 3. Create FastAPI app with comprehensive configuration
    app = _create_fastapi_app(service_config, logger)
    
    # 4. Add comprehensive middleware stack
    _add_middleware_stack(app, service_config, logger)
    
    # 5. Setup metrics and observability
    if service_config.enable_metrics:
        setup_metrics(app)
        logger.info("✅ Metrics and observability configured")
    
    # 6. Add health check endpoints
    if service_config.enable_health_checks:
        _add_health_endpoints(app, service_config, logger)
    
    # 7. Include business routers
    if business_routers:
        _include_business_routers(app, business_routers, logger)
    
    # 8. Setup startup and shutdown events
    _setup_lifecycle_events(
        app, service_config, startup_tasks, shutdown_tasks, logger
    )
    
    # 9. Register service globally
    _active_services[service_name] = app
    
    logger.info(f"✅ Service '{service_name}' initialization complete")
    return app

def _load_configuration(service_name: str, logger: logging.Logger):
    """Load service configuration."""
    try:
        config_loader.load(service_name)
        logger.info("✅ Configuration loaded successfully")
    except Exception as e:
        logger.error(f"❌ Failed to load configuration: {e}")
        raise

def _create_fastapi_app(config: ServiceConfig, logger: logging.Logger) -> FastAPI:
    """Create FastAPI application with comprehensive configuration."""
    app = FastAPI(
        title=config.title,
        description=config.description,
        version=config.version,
        docs_url=config.docs_url if not config.debug else None,
        redoc_url=config.redoc_url if not config.debug else None,
        openapi_url=config.openapi_url if not config.debug else None,
        debug=config.debug
    )
    
    # Store service configuration in app state
    app.state.service_config = config
    app.state.service_name = config.service_name
    app.state.startup_time = datetime.utcnow()
    
    logger.info(f"✅ FastAPI app created: {config.title} v{config.version}")
    return app

def _add_middleware_stack(app: FastAPI, config: ServiceConfig, logger: logging.Logger):
    """Add comprehensive middleware stack to the FastAPI app."""
    
    # 1. CORS middleware
    if config.enable_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors_origins,
            allow_credentials=True,
            allow_methods=config.cors_methods,
            allow_headers=config.cors_headers,
        )
        logger.info("✅ CORS middleware added")
    
    # 2. Trusted host middleware
    if config.enable_trusted_hosts:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=config.trusted_hosts
        )
        logger.info("✅ Trusted host middleware added")
    
    # 3. Compression middleware
    if config.enable_compression:
        app.add_middleware(GZipMiddleware, minimum_size=1000)
        logger.info("✅ Compression middleware added")
    
    # 4. Rate limiting middleware
    if config.enable_rate_limiting:
        limiter = Limiter(key_func=get_remote_address)
        app.state.limiter = limiter
        app.add_middleware(SlowAPIMiddleware)
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        logger.info("✅ Rate limiting middleware added")
    
    # 5. Request logging middleware
    if config.enable_request_logging:
        @app.middleware("http")
        async def request_logging_middleware(request: Request, call_next):
            start_time = time.time()
            
            # Log request start
            logger.info(
                f"📥 {request.method} {request.url.path}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": str(request.query_params),
                    "client_ip": request.client.host if request.client else "unknown"
                }
            )
            
            try:
                response = await call_next(request)
                process_time = time.time() - start_time
                
                # Log successful response
                logger.info(
                    f"📤 {request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s",
                    extra={
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                        "response_time": process_time,
                        "client_ip": request.client.host if request.client else "unknown"
                    }
                )
                
                # Add response time header
                response.headers["X-Response-Time"] = f"{process_time:.3f}s"
                return response
                
            except Exception as e:
                process_time = time.time() - start_time
                logger.error(
                    f"❌ {request.method} {request.url.path} - ERROR - {process_time:.3f}s - {str(e)}",
                    extra={
                        "method": request.method,
                        "path": request.url.path,
                        "error": str(e),
                        "response_time": process_time,
                        "client_ip": request.client.host if request.client else "unknown"
                    },
                    exc_info=True
                )
                raise
        
        logger.info("✅ Request logging middleware added")
    
    # 6. Error handling middleware
    @app.middleware("http")
    async def error_handling_middleware(request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as e:
            logger.error(
                f"❌ Unhandled error in {request.method} {request.url.path}: {str(e)}",
                exc_info=True
            )
            
            # Return structured error response
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "message": "An unexpected error occurred",
                    "timestamp": datetime.utcnow().isoformat(),
                    "path": request.url.path,
                    "method": request.method
                }
            )
    
    logger.info("✅ Error handling middleware added")

def _add_health_endpoints(app: FastAPI, config: ServiceConfig, logger: logging.Logger):
    """Add comprehensive health check endpoints."""
    health_checker = HealthChecker()
    
    # Add health checks based on required services
    for service in config.required_services:
        if service == "timescaledb" and hasattr(connection_manager, 'timescaledb_sync'):
            health_checker.add_check(
                DatabaseHealthCheck(connection_manager.timescaledb_sync)
            )
        elif service == "redis":
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            health_checker.add_check(RedisHealthCheck(redis_url))
    
    # Add system resource check
    health_checker.add_check(SystemResourceHealthCheck())
    health_checker.add_check(ApplicationHealthCheck())
    
    # Store health checker in app state
    app.state.health_checker = health_checker
    
    @app.get("/health")
    async def health_check_endpoint():
        """Basic health check endpoint."""
        try:
            system_health = await health_checker.check_all()
            
            status_code = 200
            if system_health.overall_status == HealthStatus.UNHEALTHY:
                status_code = 503
            elif system_health.overall_status == HealthStatus.DEGRADED:
                status_code = 200  # Service is still functional
            
            return Response(
                content=json.dumps(system_health.to_dict()),
                status_code=status_code,
                media_type="application/json"
            )
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "overall_status": "error",
                    "message": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
    
    @app.get("/health/detailed")
    async def detailed_health_check():
        """Detailed health check with component breakdown."""
        try:
            system_health = await health_checker.check_all(use_cache=False)
            return system_health.to_dict()
        except Exception as e:
            logger.error(f"❌ Detailed health check failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail={"error": str(e), "timestamp": datetime.utcnow().isoformat()}
            )
    
    @app.get("/health/ready")
    async def readiness_check():
        """Kubernetes readiness probe endpoint."""
        try:
            # Check only critical services for readiness
            if hasattr(app.state, 'connection_manager'):
                health_status = await app.state.connection_manager.health_check()
                
                # Check if critical services are healthy
                critical_services = config.required_services
                for service in critical_services:
                    service_status = health_status.get(service, {}).get('status')
                    if service_status in ['unhealthy', 'unavailable']:
                        return JSONResponse(
                            status_code=503,
                            content={"ready": False, "reason": f"{service} not ready"}
                        )
                
                return {"ready": True}
            else:
                return JSONResponse(
                    status_code=503,
                    content={"ready": False, "reason": "connection manager not initialized"}
                )
        except Exception as e:
            return JSONResponse(
                status_code=503,
                content={"ready": False, "reason": str(e)}
            )
    
    @app.get("/health/live")
    async def liveness_check():
        """Kubernetes liveness probe endpoint."""
        return {"alive": True, "timestamp": datetime.utcnow().isoformat()}
    
    logger.info("✅ Health check endpoints added")

def _include_business_routers(app: FastAPI, routers: List[APIRouter], logger: logging.Logger):
    """Include business logic routers."""
    for router in routers:
        app.include_router(router)
        logger.info(f"✅ Business router included: {router.prefix or '/'}")

def _setup_lifecycle_events(
    app: FastAPI,
    config: ServiceConfig,
    startup_tasks: Optional[List[Callable]],
    shutdown_tasks: Optional[List[Callable]],
    logger: logging.Logger
):
    """Setup comprehensive startup and shutdown events."""
    
    @app.on_event("startup")
    async def startup_event():
        """Comprehensive startup event handler."""
        logger.info(f"🚀 Starting infrastructure initialization for {config.service_name}")
        
        try:
            # 1. Initialize connections
            await _initialize_infrastructure(app, config, logger)
            
            # 2. Setup circuit breakers
            if config.enable_circuit_breakers:
                _setup_circuit_breakers(app, config, logger)
            
            # 3. Start background tasks
            if config.background_tasks or config.periodic_tasks:
                await _start_background_tasks(app, config, logger)
            
            # 4. Run additional startup tasks
            if startup_tasks:
                for task in startup_tasks:
                    try:
                        if asyncio.iscoroutinefunction(task):
                            await task(app)
                        else:
                            task(app)
                        logger.info(f"✅ Startup task completed: {task.__name__}")
                    except Exception as e:
                        logger.error(f"❌ Startup task failed: {task.__name__} - {e}", exc_info=True)
                        # Don't fail startup for non-critical tasks
            
            # 5. Register service with discovery
            _register_service_discovery(app, config, logger)
            
            logger.info(f"✅ Service {config.service_name} startup completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Service startup failed: {e}", exc_info=True)
            raise
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Comprehensive shutdown event handler."""
        logger.info(f"🛑 Starting graceful shutdown for {config.service_name}")
        
        try:
            # 1. Stop background tasks
            await _stop_background_tasks(config.service_name, logger)
            
            # 2. Run custom shutdown tasks
            if shutdown_tasks:
                for task in shutdown_tasks:
                    try:
                        if asyncio.iscoroutinefunction(task):
                            await task(app)
                        else:
                            task(app)
                        logger.info(f"✅ Shutdown task completed: {task.__name__}")
                    except Exception as e:
                        logger.error(f"❌ Shutdown task failed: {task.__name__} - {e}")
            
            # 3. Close connections
            await _shutdown_infrastructure(app, config, logger)
            
            # 4. Cleanup service registration
            _cleanup_service_registration(config.service_name, logger)
            
            logger.info(f"✅ Service {config.service_name} shutdown completed")
            
        except Exception as e:
            logger.error(f"❌ Shutdown error: {e}", exc_info=True)

async def _initialize_infrastructure(app: FastAPI, config: ServiceConfig, logger: logging.Logger):
    """Initialize infrastructure connections and dependencies."""
    # Determine required services
    deployment_env = os.getenv("DEPLOYMENT_ENV", "development")
    required_services = config.required_services or _get_required_services_for_environment(deployment_env, config.service_name)
    
    logger.info(f"🎯 Initializing infrastructure with required services: {required_services}")
    
    # Initialize connection manager
    await connection_manager.initialize(required_services=required_services)
    
    # Verify critical connections
    if connection_manager.timescaledb:
        from sqlalchemy import text
        async with connection_manager.timescaledb() as test_session:
            await test_session.execute(text("SELECT 1"))
        logger.info("✅ TimescaleDB connection verified")
    
    # Store connections in app state
    app.state.connections = {
        "redis": connection_manager.redis,
        "mongodb": connection_manager.mongodb,
        "timescaledb": connection_manager.timescaledb,
        "timescaledb_sync": connection_manager.timescaledb_sync,
        "rabbitmq": connection_manager.rabbitmq,
    }
    app.state.connection_manager = connection_manager
    
    # Store configuration
    app.state.config = {
        "common": config_loader.common_config,
        "private": config_loader.private_config,
    }
    
    # Perform health check
    health_status = await connection_manager.health_check()
    logger.info(f"📊 Infrastructure health: {health_status}")

def _setup_circuit_breakers(app: FastAPI, config: ServiceConfig, logger: logging.Logger):
    """Setup circuit breakers for external dependencies."""
    circuit_breakers = {}
    
    # Default circuit breaker configs
    default_configs = {
        "database": CircuitBreakerConfig(
            name="database",
            failure_threshold=3,
            recovery_timeout=30.0,
            success_threshold=2,
            timeout=10.0
        ),
        "redis": CircuitBreakerConfig(
            name="redis",
            failure_threshold=5,
            recovery_timeout=20.0,
            success_threshold=2,
            timeout=5.0
        ),
        "external_api": CircuitBreakerConfig(
            name="external_api",
            failure_threshold=3,
            recovery_timeout=60.0,
            success_threshold=2,
            timeout=30.0
        )
    }
    
    # Merge with custom configs
    all_configs = {**default_configs, **config.circuit_breaker_configs}
    
    for name, cb_config in all_configs.items():
        circuit_breakers[name] = get_circuit_breaker(name, cb_config)
    
    app.state.circuit_breakers = circuit_breakers
    logger.info(f"✅ Circuit breakers configured: {list(circuit_breakers.keys())}")

async def _start_background_tasks(app: FastAPI, config: ServiceConfig, logger: logging.Logger):
    """Start background and periodic tasks."""
    service_tasks = []
    
    # Start one-time background tasks
    for task in config.background_tasks:
        try:
            if asyncio.iscoroutinefunction(task):
                task_coroutine = task(app)
            else:
                # Wrap sync function in async
                async def _async_wrapper():
                    return task(app)
                task_coroutine = _async_wrapper()
            
            asyncio_task = asyncio.create_task(task_coroutine)
            service_tasks.append(asyncio_task)
            logger.info(f"✅ Background task started: {task.__name__}")
        except Exception as e:
            logger.error(f"❌ Failed to start background task {task.__name__}: {e}")
    
    # Start periodic tasks
    for task_name, task_config in config.periodic_tasks.items():
        try:
            task_func = task_config['func']
            interval = task_config['interval']
            
            async def periodic_task_wrapper(func, interval_seconds):
                while True:
                    try:
                        if asyncio.iscoroutinefunction(func):
                            await func(app)
                        else:
                            func(app)
                        logger.debug(f"✅ Periodic task executed: {func.__name__}")
                    except Exception as e:
                        logger.error(f"❌ Periodic task error {func.__name__}: {e}")
                    
                    await asyncio.sleep(interval_seconds)
            
            periodic_task = asyncio.create_task(
                periodic_task_wrapper(task_func, interval)
            )
            service_tasks.append(periodic_task)
            logger.info(f"✅ Periodic task started: {task_name} (interval: {interval}s)")
        except Exception as e:
            logger.error(f"❌ Failed to start periodic task {task_name}: {e}")
    
    # Store tasks for cleanup
    _background_tasks[config.service_name] = service_tasks

async def _stop_background_tasks(service_name: str, logger: logging.Logger):
    """Stop all background tasks for a service."""
    if service_name in _background_tasks:
        tasks = _background_tasks[service_name]
        for task in tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error(f"❌ Error stopping background task: {e}")
        
        del _background_tasks[service_name]
        logger.info(f"✅ Background tasks stopped for {service_name}")

def _register_service_discovery(app: FastAPI, config: ServiceConfig, logger: logging.Logger):
    """Register service with service discovery."""
    try:
        # This would integrate with actual service discovery
        # For now, just log the registration
        service_info = {
            "name": config.service_name,
            "type": config.service_type.value,
            "host": config.host,
            "port": config.port,
            "health_endpoint": "/health",
            "started_at": app.state.startup_time.isoformat()
        }
        
        logger.info(f"📡 Service registered: {service_info}")
        app.state.service_registration = service_info
    except Exception as e:
        logger.error(f"❌ Service discovery registration failed: {e}")

async def _shutdown_infrastructure(app: FastAPI, config: ServiceConfig, logger: logging.Logger):
    """Shutdown infrastructure connections."""
    try:
        await connection_manager.close()
        logger.info("✅ Infrastructure connections closed")
    except Exception as e:
        logger.error(f"❌ Error closing infrastructure: {e}")

def _cleanup_service_registration(service_name: str, logger: logging.Logger):
    """Cleanup service registration and global state."""
    try:
        if service_name in _active_services:
            del _active_services[service_name]
        if service_name in _service_configs:
            del _service_configs[service_name]
        if service_name in _shutdown_handlers:
            del _shutdown_handlers[service_name]
        
        logger.info(f"✅ Service registration cleaned up: {service_name}")
    except Exception as e:
        logger.error(f"❌ Cleanup error: {e}")

def _get_required_services_for_environment(deployment_env: str, service_name: str) -> List[str]:
    """
    Determine required services based on deployment environment and service type
    """
    # Service-specific requirements
    service_requirements: Dict[str, Dict[str, List[str]]] = {
        "trade_service": {
            "development": ["timescaledb"],
            "production": ["timescaledb", "redis", "rabbitmq"],
            "minimal": ["timescaledb"],
            "full": ["timescaledb", "redis", "rabbitmq", "mongodb"],
            "testing": [],
        },
        "ticker_service": {
            "development": ["timescaledb", "redis"],
            "production": ["timescaledb", "redis", "rabbitmq"],
            "minimal": ["timescaledb"],
            "full": ["timescaledb", "redis", "rabbitmq", "mongodb"],
            "testing": [],
        },
        "user_service": {
            "development": ["timescaledb"],
            "production": ["timescaledb", "redis"],
            "minimal": ["timescaledb"],
            "full": ["timescaledb", "redis", "mongodb"],
            "testing": [],
        }
    }
    
    # Default requirements if service not specifically configured
    default_requirements: Dict[str, List[str]] = {
        "development": ["timescaledb"],
        "production": ["timescaledb", "redis"],
        "minimal": ["timescaledb"],
        "full": ["timescaledb", "redis", "rabbitmq", "mongodb"],
        "testing": [],
    }
    
    # Get requirements for specific service or use defaults
    requirements = service_requirements.get(service_name, default_requirements)
    return requirements.get(deployment_env, requirements["development"])

async def stop_service(service_name: str) -> None:
    """
    Properly stop service and close all connections
    """
    logger = get_logger(__name__)
    logger.info(f"🛑 Stopping service: {service_name}")
    
    try:
        # Stop background tasks
        await _stop_background_tasks(service_name, logger)
        
        # Close connections
        await connection_manager.close()
        
        # Cleanup registration
        _cleanup_service_registration(service_name, logger)
        
        logger.info(f"✅ Service {service_name} stopped successfully")
    except Exception as e:
        logger.error(f"❌ Error stopping service {service_name}: {e}", exc_info=True)

async def restart_service(service_name: str, **kwargs) -> FastAPI:
    """
    Restart service by stopping and starting again
    """
    logger = get_logger(__name__)
    logger.info(f"🔄 Restarting service: {service_name}")
    
    # Get existing config if available
    existing_config = _service_configs.get(service_name)
    
    # Stop the service
    await stop_service(service_name)
    
    # Restart with existing config or new parameters
    if existing_config:
        # Update config with any new parameters
        for key, value in kwargs.items():
            if hasattr(existing_config, key):
                setattr(existing_config, key, value)
        
        return start_service(service_name, service_config=existing_config)
    else:
        return start_service(service_name, **kwargs)

# Signal handlers for graceful shutdown
def _setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""
    logger = get_logger(__name__)
    
    def signal_handler(signum, frame):
        logger.info(f"🛑 Received signal {signum}, initiating graceful shutdown")
        
        # Stop all services
        async def shutdown_all():
            for service_name in list(_active_services.keys()):
                try:
                    await stop_service(service_name)
                except Exception as e:
                    logger.error(f"❌ Error stopping {service_name}: {e}")
        
        # Run shutdown in asyncio context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(shutdown_all())
        finally:
            loop.close()
        
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

# Health and status utilities
async def get_service_health(service_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Get current service health status
    """
    try:
        if service_name and service_name in _active_services:
            app = _active_services[service_name]
            if hasattr(app.state, 'health_checker'):
                system_health = await app.state.health_checker.check_all()
                return system_health.to_dict()
        
        # Fallback to connection manager health
        return await connection_manager.health_check()
    except Exception as e:
        return {"error": str(e), "status": "unavailable"}

def get_service_info(service_name: str) -> Dict[str, Any]:
    """Get information about a running service."""
    if service_name not in _active_services:
        return {"error": "Service not found", "running": False}
    
    app = _active_services[service_name]
    config = _service_configs.get(service_name)
    
    return {
        "service_name": service_name,
        "running": True,
        "startup_time": app.state.startup_time.isoformat() if hasattr(app.state, 'startup_time') else None,
        "uptime_seconds": (datetime.utcnow() - app.state.startup_time).total_seconds() if hasattr(app.state, 'startup_time') else None,
        "service_type": config.service_type.value if config else "unknown",
        "version": config.version if config else "unknown",
        "required_services": config.required_services if config else [],
        "endpoints": {
            "health": "/health",
            "detailed_health": "/health/detailed",
            "readiness": "/health/ready",
            "liveness": "/health/live",
            "docs": config.docs_url if config else "/docs"
        }
    }

def list_active_services() -> List[str]:
    """List all currently active services."""
    return list(_active_services.keys())

# Utility functions for easy service creation
def create_trade_service(**kwargs) -> FastAPI:
    """Create a trade service with sensible defaults."""
    defaults = {
        "service_type": ServiceType.TRADE,
        "required_services": ["timescaledb", "redis"],
        "port": 8004,
        "enable_rate_limiting": True,
        "rate_limit_default": "1000/minute"
    }
    defaults.update(kwargs)
    
    config = ServiceConfig(service_name="trade_service", **defaults)
    return start_service("trade_service", service_config=config)

def create_ticker_service(**kwargs) -> FastAPI:
    """Create a ticker service with sensible defaults."""
    defaults = {
        "service_type": ServiceType.TICKER,
        "required_services": ["timescaledb", "redis", "rabbitmq"],
        "port": 8005,
        "enable_rate_limiting": True,
        "rate_limit_default": "10000/minute"  # Higher rate limit for data ingestion
    }
    defaults.update(kwargs)
    
    config = ServiceConfig(service_name="ticker_service", **defaults)
    return start_service("ticker_service", service_config=config)

def create_user_service(**kwargs) -> FastAPI:
    """Create a user service with sensible defaults."""
    defaults = {
        "service_type": ServiceType.USER,
        "required_services": ["timescaledb", "redis"],
        "port": 8003,
        "enable_rate_limiting": True,
        "rate_limit_default": "100/minute"
    }
    defaults.update(kwargs)
    
    config = ServiceConfig(service_name="user_service", **defaults)
    return start_service("user_service", service_config=config)

# Legacy compatibility functions
async def initialize_all_connections() -> Dict[str, Any]:
    """
    Legacy function for backward compatibility.
    Now uses the new connection manager.
    """
    await connection_manager.initialize()
    return {
        "redis": connection_manager.redis,
        "timescaledb": connection_manager.timescaledb,
        "timescaledb_sync": connection_manager.timescaledb_sync,
        "rabbitmq": connection_manager.rabbitmq,
        "mongodb": connection_manager.mongodb,
    }

async def close_all_connections(connections: Optional[Dict[str, Any]] = None) -> None:
    """
    Legacy function for backward compatibility.
    Now uses the connection manager's close method.
    """
    await connection_manager.close()

# Initialize signal handlers when module is imported
_setup_signal_handlers()