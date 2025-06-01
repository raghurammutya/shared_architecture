import time
import logging
from prometheus_client import Counter, Histogram

# Example Prometheus Metrics
REQUEST_COUNT = Counter(
    'request_count', 'Total number of requests', ['endpoint']
)
ERROR_COUNT = Counter(
    'error_count', 'Total number of errors', ['endpoint']
)
REQUEST_LATENCY = Histogram(
    'request_latency_seconds', 'Request latency in seconds', ['endpoint']
)

def track_execution_time(endpoint_name: str):
    """
    Prometheus decorator to track execution time and error count for a given endpoint.

    Example:
        @track_execution_time("my_function")
        def my_function():
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            REQUEST_COUNT.labels(endpoint=endpoint_name).inc()
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                REQUEST_LATENCY.labels(endpoint=endpoint_name).observe(duration)
                return result
            except Exception as e:
                ERROR_COUNT.labels(endpoint=endpoint_name).inc()
                logging.exception(f"Error in {endpoint_name}: {e}")
                raise
        return wrapper
    return decorator
