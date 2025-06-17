# shared_architecture/monitoring/metrics_collector.py
"""
Comprehensive metrics collection system for trade service.
Collects, aggregates, and exposes metrics for monitoring and alerting.
"""

import time
import asyncio
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import json
import statistics
from contextlib import contextmanager, asynccontextmanager

from shared_architecture.utils.enhanced_logging import get_logger

logger = get_logger(__name__)

class MetricType(Enum):
    """Types of metrics that can be collected."""
    COUNTER = "counter"
    GAUGE = "gauge" 
    HISTOGRAM = "histogram"
    TIMER = "timer"
    SET = "set"

@dataclass
class MetricPoint:
    """A single metric data point."""
    timestamp: datetime
    value: Union[int, float]
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "tags": self.tags
        }

@dataclass
class MetricSeries:
    """A series of metric data points."""
    name: str
    metric_type: MetricType
    description: str
    unit: str
    points: List[MetricPoint] = field(default_factory=list)
    
    def add_point(self, value: Union[int, float], tags: Optional[Dict[str, str]] = None):
        """Add a data point to the series."""
        point = MetricPoint(
            timestamp=datetime.utcnow(),
            value=value,
            tags=tags or {}
        )
        self.points.append(point)
        
        # Keep only last 1000 points to prevent memory bloat
        if len(self.points) > 1000:
            self.points = self.points[-1000:]
    
    def get_latest(self) -> Optional[MetricPoint]:
        """Get the most recent metric point."""
        return self.points[-1] if self.points else None
    
    def get_since(self, since: datetime) -> List[MetricPoint]:
        """Get all points since a specific time."""
        return [p for p in self.points if p.timestamp >= since]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.metric_type.value,
            "description": self.description,
            "unit": self.unit,
            "points": [p.to_dict() for p in self.points],
            "latest_value": self.get_latest().value if self.get_latest() else None,
            "point_count": len(self.points)
        }

class Counter:
    """A counter metric that only increases."""
    
    def __init__(self, name: str, description: str = "", tags: Optional[Dict[str, str]] = None):
        self.name = name
        self.description = description
        self.tags = tags or {}
        self._value = 0
        self._lock = threading.Lock()
    
    def increment(self, amount: Union[int, float] = 1, tags: Optional[Dict[str, str]] = None):
        """Increment the counter."""
        with self._lock:
            self._value += amount
        
        # Record the metric
        MetricsCollector.get_instance().record_metric(
            name=self.name,
            value=self._value,
            metric_type=MetricType.COUNTER,
            tags={**self.tags, **(tags or {})},
            description=self.description
        )
    
    def get_value(self) -> Union[int, float]:
        """Get current counter value."""
        with self._lock:
            return self._value

class Gauge:
    """A gauge metric that can increase or decrease."""
    
    def __init__(self, name: str, description: str = "", tags: Optional[Dict[str, str]] = None):
        self.name = name
        self.description = description
        self.tags = tags or {}
        self._value = 0
        self._lock = threading.Lock()
    
    def set(self, value: Union[int, float], tags: Optional[Dict[str, str]] = None):
        """Set the gauge value."""
        with self._lock:
            self._value = value
        
        MetricsCollector.get_instance().record_metric(
            name=self.name,
            value=value,
            metric_type=MetricType.GAUGE,
            tags={**self.tags, **(tags or {})},
            description=self.description
        )
    
    def increment(self, amount: Union[int, float] = 1, tags: Optional[Dict[str, str]] = None):
        """Increment the gauge value."""
        with self._lock:
            self._value += amount
            new_value = self._value
        
        MetricsCollector.get_instance().record_metric(
            name=self.name,
            value=new_value,
            metric_type=MetricType.GAUGE,
            tags={**self.tags, **(tags or {})},
            description=self.description
        )
    
    def decrement(self, amount: Union[int, float] = 1, tags: Optional[Dict[str, str]] = None):
        """Decrement the gauge value."""
        self.increment(-amount, tags)
    
    def get_value(self) -> Union[int, float]:
        """Get current gauge value."""
        with self._lock:
            return self._value

class Histogram:
    """A histogram metric for tracking distributions."""
    
    def __init__(self, name: str, description: str = "", 
                 buckets: Optional[List[float]] = None, tags: Optional[Dict[str, str]] = None):
        self.name = name
        self.description = description
        self.tags = tags or {}
        self.buckets = buckets or [0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 50.0, 100.0]
        self._values = deque(maxlen=10000)  # Keep last 10k values
        self._lock = threading.Lock()
    
    def observe(self, value: Union[int, float], tags: Optional[Dict[str, str]] = None):
        """Record an observation."""
        with self._lock:
            self._values.append(value)
        
        MetricsCollector.get_instance().record_metric(
            name=self.name,
            value=value,
            metric_type=MetricType.HISTOGRAM,
            tags={**self.tags, **(tags or {})},
            description=self.description
        )
    
    def get_statistics(self) -> Dict[str, float]:
        """Get histogram statistics."""
        with self._lock:
            values = list(self._values)
        
        if not values:
            return {}
        
        return {
            "count": len(values),
            "sum": sum(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "p95": self._percentile(values, 0.95),
            "p99": self._percentile(values, 0.99),
            "stddev": statistics.stdev(values) if len(values) > 1 else 0
        }
    
    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile value."""
        if not values:
            return 0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile)
        return sorted_values[min(index, len(sorted_values) - 1)]

class Timer:
    """A timer metric for measuring durations."""
    
    def __init__(self, name: str, description: str = "", tags: Optional[Dict[str, str]] = None):
        self.name = name
        self.description = description
        self.tags = tags or {}
        self.histogram = Histogram(f"{name}_duration", description, tags=tags)
    
    @contextmanager
    def time(self, tags: Optional[Dict[str, str]] = None):
        """Context manager for timing operations."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = (time.time() - start_time) * 1000  # Convert to milliseconds
            self.record(duration, tags)
    
    @asynccontextmanager
    async def time_async(self, tags: Optional[Dict[str, str]] = None):
        """Async context manager for timing operations."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = (time.time() - start_time) * 1000  # Convert to milliseconds
            self.record(duration, tags)
    
    def record(self, duration_ms: float, tags: Optional[Dict[str, str]] = None):
        """Record a duration measurement."""
        self.histogram.observe(duration_ms, tags)
    
    def get_statistics(self) -> Dict[str, float]:
        """Get timing statistics."""
        return self.histogram.get_statistics()

class MetricsCollector:
    """Central metrics collection and management system."""
    
    _instance: Optional['MetricsCollector'] = None
    _lock = threading.Lock()
    
    def __init__(self):
        self.metrics: Dict[str, MetricSeries] = {}
        self.counters: Dict[str, Counter] = {}
        self.gauges: Dict[str, Gauge] = {}
        self.histograms: Dict[str, Histogram] = {}
        self.timers: Dict[str, Timer] = {}
        self._lock = threading.Lock()
        self.logger = get_logger(__name__)
        
        # Start background aggregation
        self._aggregation_task = None
        self._should_stop = False
    
    @classmethod
    def get_instance(cls) -> 'MetricsCollector':
        """Get singleton instance of MetricsCollector."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def counter(self, name: str, description: str = "", tags: Optional[Dict[str, str]] = None) -> Counter:
        """Create or get a counter metric."""
        key = f"{name}:{json.dumps(tags or {}, sort_keys=True)}"
        if key not in self.counters:
            self.counters[key] = Counter(name, description, tags)
        return self.counters[key]
    
    def gauge(self, name: str, description: str = "", tags: Optional[Dict[str, str]] = None) -> Gauge:
        """Create or get a gauge metric."""
        key = f"{name}:{json.dumps(tags or {}, sort_keys=True)}"
        if key not in self.gauges:
            self.gauges[key] = Gauge(name, description, tags)
        return self.gauges[key]
    
    def histogram(self, name: str, description: str = "", 
                  buckets: Optional[List[float]] = None, tags: Optional[Dict[str, str]] = None) -> Histogram:
        """Create or get a histogram metric."""
        key = f"{name}:{json.dumps(tags or {}, sort_keys=True)}"
        if key not in self.histograms:
            self.histograms[key] = Histogram(name, description, buckets, tags)
        return self.histograms[key]
    
    def timer(self, name: str, description: str = "", tags: Optional[Dict[str, str]] = None) -> Timer:
        """Create or get a timer metric."""
        key = f"{name}:{json.dumps(tags or {}, sort_keys=True)}"
        if key not in self.timers:
            self.timers[key] = Timer(name, description, tags)
        return self.timers[key]
    
    def record_metric(self, name: str, value: Union[int, float], metric_type: MetricType,
                     tags: Optional[Dict[str, str]] = None, description: str = "", unit: str = ""):
        """Record a metric data point."""
        series_key = f"{name}:{metric_type.value}:{json.dumps(tags or {}, sort_keys=True)}"
        
        with self._lock:
            if series_key not in self.metrics:
                self.metrics[series_key] = MetricSeries(
                    name=name,
                    metric_type=metric_type,
                    description=description,
                    unit=unit
                )
            
            self.metrics[series_key].add_point(value, tags)
    
    def get_metric(self, name: str, tags: Optional[Dict[str, str]] = None) -> Optional[MetricSeries]:
        """Get a specific metric series."""
        # Try different metric types
        for metric_type in MetricType:
            series_key = f"{name}:{metric_type.value}:{json.dumps(tags or {}, sort_keys=True)}"
            if series_key in self.metrics:
                return self.metrics[series_key]
        return None
    
    def get_all_metrics(self) -> Dict[str, MetricSeries]:
        """Get all metric series."""
        with self._lock:
            return self.metrics.copy()
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of all metrics."""
        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_series": len(self.metrics),
            "metric_types": {},
            "recent_activity": {}
        }
        
        # Count by type
        type_counts = defaultdict(int)
        recent_cutoff = datetime.utcnow() - timedelta(minutes=5)
        recent_activity = defaultdict(int)
        
        with self._lock:
            for series in self.metrics.values():
                type_counts[series.metric_type.value] += 1
                
                # Count recent activity
                recent_points = series.get_since(recent_cutoff)
                if recent_points:
                    recent_activity[series.name] += len(recent_points)
        
        summary["metric_types"] = dict(type_counts)
        summary["recent_activity"] = dict(recent_activity)
        
        return summary
    
    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        
        with self._lock:
            for series in self.metrics.values():
                latest = series.get_latest()
                if not latest:
                    continue
                
                # Add help and type comments
                lines.append(f"# HELP {series.name} {series.description}")
                lines.append(f"# TYPE {series.name} {series.metric_type.value}")
                
                # Format tags
                tag_str = ""
                if latest.tags:
                    tag_pairs = [f'{k}="{v}"' for k, v in latest.tags.items()]
                    tag_str = "{" + ",".join(tag_pairs) + "}"
                
                # Add metric line
                lines.append(f"{series.name}{tag_str} {latest.value}")
        
        return "\n".join(lines)
    
    def export_json(self) -> Dict[str, Any]:
        """Export metrics in JSON format."""
        with self._lock:
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "metrics": {
                    key: series.to_dict() 
                    for key, series in self.metrics.items()
                }
            }
    
    def clear_old_metrics(self, older_than: timedelta = timedelta(hours=1)):
        """Clear metric points older than specified time."""
        cutoff = datetime.utcnow() - older_than
        
        with self._lock:
            for series in self.metrics.values():
                series.points = [p for p in series.points if p.timestamp >= cutoff]
        
        self.logger.info(f"Cleared metric points older than {older_than}")
    
    def start_aggregation(self):
        """Start background metric aggregation."""
        if self._aggregation_task is None:
            self._should_stop = False
            self._aggregation_task = asyncio.create_task(self._aggregation_loop())
    
    def stop_aggregation(self):
        """Stop background metric aggregation."""
        self._should_stop = True
        if self._aggregation_task:
            self._aggregation_task.cancel()
    
    async def _aggregation_loop(self):
        """Background loop for metric aggregation and cleanup."""
        while not self._should_stop:
            try:
                # Clear old metrics every hour
                self.clear_old_metrics()
                
                # Wait 1 hour before next cleanup
                await asyncio.sleep(3600)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in metric aggregation loop: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait 1 minute before retrying

# Predefined metrics for common operations
class TradeMetrics:
    """Predefined metrics for trade service operations."""
    
    def __init__(self):
        self.collector = MetricsCollector.get_instance()
        
        # Order metrics
        self.orders_placed = self.collector.counter(
            "trade_orders_placed_total",
            "Total number of orders placed"
        )
        
        self.orders_failed = self.collector.counter(
            "trade_orders_failed_total", 
            "Total number of failed orders"
        )
        
        self.order_processing_time = self.collector.timer(
            "trade_order_processing_duration",
            "Time taken to process orders"
        )
        
        # Data fetch metrics
        self.data_fetches = self.collector.counter(
            "trade_data_fetches_total",
            "Total number of data fetch operations"
        )
        
        self.data_fetch_time = self.collector.timer(
            "trade_data_fetch_duration",
            "Time taken to fetch data from external APIs"
        )
        
        # Database metrics
        self.db_queries = self.collector.counter(
            "trade_db_queries_total",
            "Total number of database queries"
        )
        
        self.db_query_time = self.collector.timer(
            "trade_db_query_duration",
            "Database query execution time"
        )
        
        # API metrics
        self.api_requests = self.collector.counter(
            "trade_api_requests_total",
            "Total number of API requests"
        )
        
        self.api_response_time = self.collector.timer(
            "trade_api_response_duration",
            "API response time"
        )
        
        # Error metrics
        self.errors = self.collector.counter(
            "trade_errors_total",
            "Total number of errors"
        )
        
        # Resource metrics
        self.active_connections = self.collector.gauge(
            "trade_active_connections",
            "Number of active connections"
        )
        
        self.memory_usage = self.collector.gauge(
            "trade_memory_usage_bytes",
            "Memory usage in bytes"
        )

# Global metrics instance
trade_metrics = TradeMetrics()

# Convenience functions for quick metric recording
def increment_counter(name: str, amount: Union[int, float] = 1, tags: Optional[Dict[str, str]] = None):
    """Increment a counter metric."""
    collector = MetricsCollector.get_instance()
    counter = collector.counter(name)
    counter.increment(amount, tags)

def set_gauge(name: str, value: Union[int, float], tags: Optional[Dict[str, str]] = None):
    """Set a gauge metric value."""
    collector = MetricsCollector.get_instance()
    gauge = collector.gauge(name)
    gauge.set(value, tags)

def record_histogram(name: str, value: Union[int, float], tags: Optional[Dict[str, str]] = None):
    """Record a histogram observation."""
    collector = MetricsCollector.get_instance()
    histogram = collector.histogram(name)
    histogram.observe(value, tags)

def time_function(name: str, tags: Optional[Dict[str, str]] = None):
    """Decorator to time function execution."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            collector = MetricsCollector.get_instance()
            timer = collector.timer(name)
            with timer.time(tags):
                return func(*args, **kwargs)
        return wrapper
    return decorator

def time_async_function(name: str, tags: Optional[Dict[str, str]] = None):
    """Decorator to time async function execution."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            collector = MetricsCollector.get_instance()
            timer = collector.timer(name)
            async with timer.time_async(tags):
                return await func(*args, **kwargs)
        return wrapper
    return decorator