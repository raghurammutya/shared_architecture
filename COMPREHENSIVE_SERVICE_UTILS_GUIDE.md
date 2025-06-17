# Comprehensive Service Utilities Guide

## Overview

The comprehensive service utilities provide a complete infrastructure framework that handles all common microservice concerns, allowing developers to focus purely on business logic. This system eliminates the need for repetitive infrastructure setup code across microservices.

## Key Features

### 🚀 **Infrastructure Setup**
- Automatic database connection management with health monitoring
- Redis connection with circuit breaker protection
- RabbitMQ integration for messaging
- MongoDB support for document storage
- Service discovery registration

### 🛡️ **Resilience & Protection**
- Circuit breaker pattern implementation
- Automatic retry logic with exponential backoff
- Rate limiting protection
- Timeout handling
- Graceful degradation

### 📊 **Observability**
- Prometheus metrics collection
- Structured logging with request tracing
- Comprehensive health checks (basic, detailed, readiness, liveness)
- Performance monitoring
- Error tracking and reporting

### 🔧 **Middleware Stack**
- CORS configuration
- Request/response compression
- Security headers
- Error handling middleware
- Request logging

### ⚙️ **Background Tasks**
- Periodic task management
- One-time startup tasks
- Graceful shutdown handling
- Task monitoring and recovery

## Quick Start

### Basic Service Creation

```python
from shared_architecture.utils.comprehensive_service_utils import start_service
from fastapi import APIRouter

# Create your business logic router
business_router = APIRouter()

@business_router.get("/api/data")
async def get_data():
    return {"message": "Hello from business logic!"}

# Create service with minimal configuration
app = start_service(
    service_name="my_service",
    business_routers=[business_router],
    required_services=['redis', 'timescaledb']
)
```

That's it! Your service now has:
- ✅ Database connections with health monitoring
- ✅ Redis caching with circuit breakers
- ✅ Comprehensive health checks
- ✅ Structured logging
- ✅ Metrics collection
- ✅ Rate limiting
- ✅ Error handling
- ✅ Graceful shutdown

### Advanced Configuration

```python
from shared_architecture.utils.comprehensive_service_utils import (
    start_service, ServiceConfig, ServiceType
)

# Advanced configuration
config = ServiceConfig(
    service_name="advanced_service",
    service_type=ServiceType.TRADE,
    
    # API settings
    title="Advanced Trading Service",
    description="High-performance trading operations",
    version="2.0.0",
    port=8004,
    
    # Infrastructure requirements
    required_services=["timescaledb", "redis"],
    optional_services=["rabbitmq", "mongodb"],
    
    # Security & Performance
    enable_cors=True,
    cors_origins=["http://localhost:3000"],
    enable_rate_limiting=True,
    rate_limit_default="1000/minute",
    enable_compression=True,
    
    # Observability
    enable_request_logging=True,
    enable_metrics=True,
    enable_health_checks=True,
    
    # Background tasks
    periodic_tasks={
        "cleanup": {
            "func": cleanup_old_data,
            "interval": 3600  # Every hour
        }
    },
    
    # Circuit breakers
    enable_circuit_breakers=True,
    
    # Graceful shutdown
    shutdown_timeout=30
)

app = start_service(
    service_name="advanced_service",
    service_config=config,
    business_routers=[trade_router, analytics_router],
    startup_tasks=[initialize_strategies],
    shutdown_tasks=[save_state]
)
```

## Service Decorators

The system includes powerful decorators for common patterns:

### Circuit Breaker Protection

```python
from shared_architecture.utils.service_decorators import with_circuit_breaker

@with_circuit_breaker(
    "external_api",
    fallback=lambda: {"error": "Service unavailable"}
)
async def call_external_service():
    # This call is protected by circuit breaker
    pass
```

### Retry Logic

```python
from shared_architecture.utils.service_decorators import with_retry

@with_retry(max_attempts=3, delay=1.0, exceptions=(ConnectionError,))
async def unreliable_operation():
    # Automatically retries on failure
    pass
```

### Metrics Collection

```python
from shared_architecture.utils.service_decorators import with_metrics

@with_metrics("order_processing", tags={"service": "trade"})
async def process_order(order_data):
    # Automatically tracks execution time and error rates
    pass
```

### Combined API Endpoint Protection

```python
from shared_architecture.utils.service_decorators import api_endpoint

@router.post("/orders")
@api_endpoint(
    rate_limit="500/minute",
    timeout=30.0,
    circuit_breaker_name="broker_api",
    cache_ttl=60,
    metrics_name="create_order"
)
async def create_order(order_data):
    # Comprehensive protection with one decorator
    pass
```

### Background Task Protection

```python
from shared_architecture.utils.service_decorators import background_task

@background_task(
    retry_attempts=5,
    circuit_breaker_name="email_service",
    metrics_name="send_notification"
)
async def send_email_notification():
    # Protected background task
    pass
```

## Health Checks

The system provides multiple health check endpoints:

### Basic Health Check
```
GET /health
```
Returns overall service health status.

### Detailed Health Check
```
GET /health/detailed
```
Returns detailed component-by-component health information.

### Readiness Probe (Kubernetes)
```
GET /health/ready
```
Indicates if the service is ready to receive traffic.

### Liveness Probe (Kubernetes)
```
GET /health/live
```
Indicates if the service is alive and functioning.

## Service Types

Pre-configured service types with sensible defaults:

### Trade Service
```python
from shared_architecture.utils.comprehensive_service_utils import create_trade_service

app = create_trade_service(
    business_routers=[trade_router],
    rate_limit_default="1000/minute"
)
```

### Ticker Service
```python
from shared_architecture.utils.comprehensive_service_utils import create_ticker_service

app = create_ticker_service(
    business_routers=[ticker_router],
    rate_limit_default="10000/minute"  # Higher for data ingestion
)
```

### User Service
```python
from shared_architecture.utils.comprehensive_service_utils import create_user_service

app = create_user_service(
    business_routers=[user_router],
    required_services=["timescaledb", "redis"]
)
```

## Environment-Based Configuration

The system automatically adjusts requirements based on deployment environment:

```bash
# Development
DEPLOYMENT_ENV=development  # Minimal services
DEPLOYMENT_ENV=production   # Full services
DEPLOYMENT_ENV=testing      # Mock services
DEPLOYMENT_ENV=minimal      # Only essential services
DEPLOYMENT_ENV=full         # All available services
```

## Background Tasks

### One-time Startup Tasks

```python
async def initialize_data(app):
    """Run once during startup"""
    await load_configuration()
    await setup_caches()

app = start_service(
    service_name="my_service",
    startup_tasks=[initialize_data]
)
```

### Periodic Tasks

```python
async def cleanup_task(app):
    """Run periodically"""
    await cleanup_old_records()

config = ServiceConfig(
    service_name="my_service",
    periodic_tasks={
        "cleanup": {
            "func": cleanup_task,
            "interval": 3600  # Every hour
        }
    }
)
```

### Shutdown Tasks

```python
async def save_state(app):
    """Run during graceful shutdown"""
    await save_application_state()

app = start_service(
    service_name="my_service",
    shutdown_tasks=[save_state]
)
```

## Circuit Breaker Configuration

### Default Circuit Breakers

The system includes pre-configured circuit breakers:

- **Database**: 3 failures, 30s recovery, 10s timeout
- **Redis**: 5 failures, 20s recovery, 5s timeout
- **External API**: 3 failures, 60s recovery, 30s timeout

### Custom Circuit Breaker

```python
from shared_architecture.resilience.circuit_breaker import CircuitBreakerConfig

custom_config = CircuitBreakerConfig(
    name="payment_api",
    failure_threshold=2,
    recovery_timeout=45.0,
    success_threshold=3,
    timeout=15.0
)

config = ServiceConfig(
    service_name="payment_service",
    circuit_breaker_configs={
        "payment_api": custom_config
    }
)
```

## Monitoring and Metrics

### Automatic Metrics

The system automatically collects:
- Request count and latency
- Error rates by endpoint
- Circuit breaker states
- Database connection health
- System resource utilization

### Custom Metrics

```python
from shared_architecture.utils.service_decorators import with_metrics

@with_metrics(
    "business_metric",
    tags={"department": "trading"},
    track_execution_time=True,
    track_error_rate=True
)
async def business_operation():
    pass
```

## Error Handling

### Automatic Error Handling

The system provides:
- Structured error responses
- Error logging with context
- Automatic retry for transient failures
- Circuit breaker protection
- Graceful degradation

### Custom Error Handling

```python
@router.get("/custom-endpoint")
async def custom_endpoint():
    try:
        result = await risky_operation()
        return result
    except ExternalServiceError as e:
        # Custom handling for specific errors
        logger.error(f"External service failed: {e}")
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
```

## Service Discovery

Services are automatically registered with service discovery, including:
- Service name and type
- Host and port information
- Health check endpoints
- Startup timestamp
- Service metadata

## Migration from Existing Services

### Step 1: Install Dependencies

Make sure your service has access to the shared_architecture package.

### Step 2: Replace Service Initialization

**Before:**
```python
from fastapi import FastAPI
app = FastAPI()
# ... manual setup of connections, logging, etc.
```

**After:**
```python
from shared_architecture.utils.comprehensive_service_utils import start_service

app = start_service(
    service_name="my_service",
    business_routers=[my_router],
    required_services=['redis', 'timescaledb']
)
```

### Step 3: Add Protection to Critical Endpoints

```python
from shared_architecture.utils.service_decorators import api_endpoint

@router.post("/critical-operation")
@api_endpoint(
    rate_limit="100/minute",
    circuit_breaker_name="external_service",
    timeout=30.0
)
async def critical_operation():
    pass
```

### Step 4: Convert Background Tasks

**Before:**
```python
@app.on_event("startup")
async def startup():
    asyncio.create_task(background_worker())
```

**After:**
```python
config = ServiceConfig(
    service_name="my_service",
    periodic_tasks={
        "background_worker": {
            "func": background_worker,
            "interval": 60
        }
    }
)
```

## Best Practices

### 1. Service Configuration
- Use environment-specific configurations
- Set appropriate timeouts for your use case
- Configure rate limits based on expected load
- Enable all observability features in production

### 2. Circuit Breakers
- Use circuit breakers for all external service calls
- Configure appropriate fallback responses
- Set realistic failure thresholds
- Monitor circuit breaker metrics

### 3. Background Tasks
- Use periodic tasks for maintenance operations
- Implement proper error handling in tasks
- Monitor task execution metrics
- Use startup/shutdown tasks for initialization/cleanup

### 4. Monitoring
- Enable comprehensive health checks
- Use custom metrics for business operations
- Monitor error rates and performance
- Set up alerting on health check failures

### 5. Error Handling
- Let decorators handle common error patterns
- Implement custom handling for business-specific errors
- Use structured error responses
- Log errors with sufficient context

## Examples

See the following files for complete examples:
- `trade_service/simplified_main.py` - Basic service setup
- `trade_service/example_using_decorators.py` - Advanced patterns with decorators

## Troubleshooting

### Common Issues

1. **Service won't start**: Check required services are available
2. **Circuit breaker always open**: Review failure thresholds and external service health
3. **High memory usage**: Check background task intervals and cleanup
4. **Slow responses**: Review timeout settings and circuit breaker configs

### Debug Mode

Enable debug mode for additional logging:

```python
config = ServiceConfig(
    service_name="my_service",
    debug=True  # Enables detailed logging
)
```

### Health Check Debugging

Use the detailed health endpoint for troubleshooting:

```bash
curl http://localhost:8000/health/detailed
```

This will show the status of all components and help identify issues.

## Conclusion

The comprehensive service utilities eliminate the need for repetitive infrastructure code and provide enterprise-grade reliability, observability, and performance out of the box. By using this system, developers can focus on business logic while getting production-ready infrastructure automatically.