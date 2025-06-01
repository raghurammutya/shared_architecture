from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry

# Shared registry for reuse across services
registry = CollectorRegistry(auto_describe=True)

# Define some standard metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint'],
    registry=registry
)

REQUEST_LATENCY = Histogram(
    'http_request_latency_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint'],
    registry=registry
)

SERVICE_HEALTH = Gauge(
    'service_health_status',
    'Health status of the service (1 for healthy, 0 for unhealthy)',
    registry=registry
)


def record_request(method: str, endpoint: str, latency_seconds: float):
    REQUEST_COUNT.labels(method=method, endpoint=endpoint).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(latency_seconds)


def set_service_health(is_healthy: bool):
    SERVICE_HEALTH.set(1 if is_healthy else 0)
