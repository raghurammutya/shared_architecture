# shared_architecture/observability/tracing.py
"""
Distributed tracing implementation for trade service observability.
Provides request tracking across service boundaries and external APIs.
"""

import asyncio
import time
import uuid
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, field
from contextlib import contextmanager, asynccontextmanager
from contextvars import ContextVar
import json

from shared_architecture.utils.enhanced_logging import get_logger
from shared_architecture.monitoring.metrics_collector import MetricsCollector

logger = get_logger(__name__)

# Context variables for tracing
trace_id_var: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)
span_id_var: ContextVar[Optional[str]] = ContextVar('span_id', default=None)
parent_span_id_var: ContextVar[Optional[str]] = ContextVar('parent_span_id', default=None)

@dataclass
class SpanTag:
    """A key-value tag for spans."""
    key: str
    value: str

@dataclass
class SpanLog:
    """A log entry within a span."""
    timestamp: datetime
    level: str
    message: str
    fields: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Span:
    """A trace span representing an operation."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    tags: Dict[str, str] = field(default_factory=dict)
    logs: List[SpanLog] = field(default_factory=list)
    status: str = "started"  # started, finished, error
    error: Optional[str] = None
    service_name: str = "trade_service"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary for serialization."""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "operation_name": self.operation_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "tags": self.tags,
            "logs": [
                {
                    "timestamp": log.timestamp.isoformat(),
                    "level": log.level,
                    "message": log.message,
                    "fields": log.fields
                }
                for log in self.logs
            ],
            "status": self.status,
            "error": self.error,
            "service_name": self.service_name
        }

@dataclass
class Trace:
    """A complete trace containing multiple spans."""
    trace_id: str
    spans: List[Span] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    root_operation: Optional[str] = None
    
    def add_span(self, span: Span):
        """Add a span to the trace."""
        self.spans.append(span)
        
        # Update trace timing
        if self.start_time is None or span.start_time < self.start_time:
            self.start_time = span.start_time
        
        if span.end_time:
            if self.end_time is None or span.end_time > self.end_time:
                self.end_time = span.end_time
        
        # Set root operation if this is the first span or has no parent
        if not span.parent_span_id:
            self.root_operation = span.operation_name
        
        # Recalculate duration
        if self.start_time and self.end_time:
            self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert trace to dictionary for serialization."""
        return {
            "trace_id": self.trace_id,
            "spans": [span.to_dict() for span in self.spans],
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "root_operation": self.root_operation,
            "span_count": len(self.spans)
        }

class SpanContext:
    """Context manager for tracing spans."""
    
    def __init__(self, operation_name: str, tracer: 'Tracer', 
                 tags: Optional[Dict[str, str]] = None, parent_span_id: Optional[str] = None):
        self.operation_name = operation_name
        self.tracer = tracer
        self.tags = tags or {}
        self.parent_span_id = parent_span_id
        self.span: Optional[Span] = None
        self._start_time = 0.0
        
    def __enter__(self) -> Span:
        """Start the span."""
        self._start_time = time.time()
        
        # Get current trace context
        trace_id = trace_id_var.get()
        if not trace_id:
            trace_id = self.tracer.generate_trace_id()
            trace_id_var.set(trace_id)
        
        # Generate span ID
        span_id = self.tracer.generate_span_id()
        
        # Get parent span ID from context or parameter
        parent_id = self.parent_span_id or span_id_var.get()
        
        # Create span
        self.span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_id,
            operation_name=self.operation_name,
            start_time=datetime.utcnow(),
            tags=self.tags.copy()
        )
        
        # Set context variables
        span_id_var.set(span_id)
        parent_span_id_var.set(parent_id)
        
        # Register span with tracer
        self.tracer.register_span(self.span)
        
        return self.span
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End the span."""
        if self.span:
            self.span.end_time = datetime.utcnow()
            self.span.duration_ms = (time.time() - self._start_time) * 1000
            
            if exc_type:
                self.span.status = "error"
                self.span.error = str(exc_val)
                self.span.tags["error"] = "true"
                self.span.tags["error.type"] = exc_type.__name__
            else:
                self.span.status = "finished"
            
            self.tracer.finish_span(self.span)

class AsyncSpanContext:
    """Async context manager for tracing spans."""
    
    def __init__(self, operation_name: str, tracer: 'Tracer',
                 tags: Optional[Dict[str, str]] = None, parent_span_id: Optional[str] = None):
        self.operation_name = operation_name
        self.tracer = tracer
        self.tags = tags or {}
        self.parent_span_id = parent_span_id
        self.span: Optional[Span] = None
        self._start_time = 0.0
    
    async def __aenter__(self) -> Span:
        """Start the span."""
        self._start_time = time.time()
        
        # Get current trace context
        trace_id = trace_id_var.get()
        if not trace_id:
            trace_id = self.tracer.generate_trace_id()
            trace_id_var.set(trace_id)
        
        # Generate span ID
        span_id = self.tracer.generate_span_id()
        
        # Get parent span ID from context or parameter
        parent_id = self.parent_span_id or span_id_var.get()
        
        # Create span
        self.span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_id,
            operation_name=self.operation_name,
            start_time=datetime.utcnow(),
            tags=self.tags.copy()
        )
        
        # Set context variables
        span_id_var.set(span_id)
        parent_span_id_var.set(parent_id)
        
        # Register span with tracer
        self.tracer.register_span(self.span)
        
        return self.span
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """End the span."""
        if self.span:
            self.span.end_time = datetime.utcnow()
            self.span.duration_ms = (time.time() - self._start_time) * 1000
            
            if exc_type:
                self.span.status = "error"
                self.span.error = str(exc_val)
                self.span.tags["error"] = "true"
                self.span.tags["error.type"] = exc_type.__name__
            else:
                self.span.status = "finished"
            
            self.tracer.finish_span(self.span)

class Tracer:
    """Distributed tracer for collecting and managing spans."""
    
    def __init__(self, service_name: str = "trade_service"):
        self.service_name = service_name
        self.active_spans: Dict[str, Span] = {}
        self.completed_traces: Dict[str, Trace] = {}
        self._lock = threading.Lock()
        self.logger = get_logger(__name__)
        
        # Metrics
        self.metrics_collector = MetricsCollector.get_instance()
        self.spans_created = self.metrics_collector.counter(
            "tracing_spans_created_total",
            "Total spans created"
        )
        self.spans_finished = self.metrics_collector.counter(
            "tracing_spans_finished_total",
            "Total spans finished"
        )
        self.traces_completed = self.metrics_collector.counter(
            "tracing_traces_completed_total",
            "Total traces completed"
        )
        self.span_duration = self.metrics_collector.histogram(
            "tracing_span_duration_ms",
            "Span duration distribution"
        )
    
    def generate_trace_id(self) -> str:
        """Generate a unique trace ID."""
        return str(uuid.uuid4().hex)
    
    def generate_span_id(self) -> str:
        """Generate a unique span ID."""
        return str(uuid.uuid4().hex[:16])
    
    def start_span(self, operation_name: str, tags: Optional[Dict[str, str]] = None,
                   parent_span_id: Optional[str] = None) -> SpanContext:
        """Start a new span."""
        return SpanContext(operation_name, self, tags, parent_span_id)
    
    def start_span_async(self, operation_name: str, tags: Optional[Dict[str, str]] = None,
                         parent_span_id: Optional[str] = None) -> AsyncSpanContext:
        """Start a new async span."""
        return AsyncSpanContext(operation_name, self, tags, parent_span_id)
    
    def register_span(self, span: Span):
        """Register an active span."""
        with self._lock:
            self.active_spans[span.span_id] = span
        
        self.spans_created.increment(tags={
            "operation": span.operation_name,
            "service": self.service_name
        })
        
        self.logger.debug(
            f"Started span: {span.operation_name}",
            trace_id=span.trace_id,
            span_id=span.span_id,
            parent_span_id=span.parent_span_id
        )
    
    def finish_span(self, span: Span):
        """Finish a span and add to trace."""
        with self._lock:
            # Remove from active spans
            if span.span_id in self.active_spans:
                del self.active_spans[span.span_id]
            
            # Add to trace
            if span.trace_id not in self.completed_traces:
                self.completed_traces[span.trace_id] = Trace(trace_id=span.trace_id)
            
            self.completed_traces[span.trace_id].add_span(span)
        
        # Record metrics
        self.spans_finished.increment(tags={
            "operation": span.operation_name,
            "status": span.status,
            "service": self.service_name
        })
        
        if span.duration_ms:
            self.span_duration.observe(span.duration_ms, tags={
                "operation": span.operation_name,
                "service": self.service_name
            })
        
        self.logger.debug(
            f"Finished span: {span.operation_name}",
            trace_id=span.trace_id,
            span_id=span.span_id,
            duration_ms=span.duration_ms,
            status=span.status
        )
        
        # Check if trace is complete (no more active spans for this trace)
        active_spans_for_trace = [
            s for s in self.active_spans.values() 
            if s.trace_id == span.trace_id
        ]
        
        if not active_spans_for_trace:
            self._complete_trace(span.trace_id)
    
    def _complete_trace(self, trace_id: str):
        """Mark a trace as complete."""
        if trace_id in self.completed_traces:
            trace = self.completed_traces[trace_id]
            self.traces_completed.increment(tags={
                "root_operation": trace.root_operation or "unknown",
                "service": self.service_name
            })
            
            self.logger.info(
                f"Completed trace",
                trace_id=trace_id,
                duration_ms=trace.duration_ms,
                span_count=len(trace.spans),
                root_operation=trace.root_operation
            )
    
    def get_current_span(self) -> Optional[Span]:
        """Get the current active span."""
        span_id = span_id_var.get()
        if span_id:
            return self.active_spans.get(span_id)
        return None
    
    def get_trace(self, trace_id: str) -> Optional[Trace]:
        """Get a trace by ID."""
        return self.completed_traces.get(trace_id)
    
    def get_traces(self, limit: int = 100, 
                   since: Optional[datetime] = None) -> List[Trace]:
        """Get recent traces."""
        traces = list(self.completed_traces.values())
        
        if since:
            traces = [t for t in traces if t.start_time and t.start_time >= since]
        
        # Sort by start time, most recent first
        traces.sort(key=lambda t: t.start_time or datetime.min, reverse=True)
        
        return traces[:limit]
    
    def clear_old_traces(self, older_than: timedelta = timedelta(hours=1)):
        """Clear traces older than specified time."""
        cutoff = datetime.utcnow() - older_than
        
        with self._lock:
            traces_to_remove = [
                trace_id for trace_id, trace in self.completed_traces.items()
                if trace.end_time and trace.end_time < cutoff
            ]
            
            for trace_id in traces_to_remove:
                del self.completed_traces[trace_id]
        
        self.logger.info(f"Cleared {len(traces_to_remove)} old traces")
    
    def add_log_to_current_span(self, level: str, message: str, **fields):
        """Add a log entry to the current span."""
        current_span = self.get_current_span()
        if current_span:
            log_entry = SpanLog(
                timestamp=datetime.utcnow(),
                level=level,
                message=message,
                fields=fields
            )
            current_span.logs.append(log_entry)
    
    def add_tag_to_current_span(self, key: str, value: str):
        """Add a tag to the current span."""
        current_span = self.get_current_span()
        if current_span:
            current_span.tags[key] = value

# Global tracer instance
_tracer: Optional[Tracer] = None

def get_tracer() -> Tracer:
    """Get the global tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = Tracer()
    return _tracer

def trace_function(operation_name: Optional[str] = None, tags: Optional[Dict[str, str]] = None):
    """Decorator for tracing function calls."""
    def decorator(func):
        func_operation_name = operation_name or f"{func.__module__}.{func.__name__}"
        tracer = get_tracer()
        
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                async with tracer.start_span_async(func_operation_name, tags):
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                with tracer.start_span(func_operation_name, tags):
                    return func(*args, **kwargs)
            return sync_wrapper
    
    return decorator

def trace_external_call(service_name: str, operation: str, tags: Optional[Dict[str, str]] = None):
    """Decorator for tracing external service calls."""
    external_tags = {"external.service": service_name, "span.kind": "client"}
    if tags:
        external_tags.update(tags)
    
    return trace_function(f"external.{service_name}.{operation}", external_tags)

def trace_database_call(operation: str, table: Optional[str] = None):
    """Decorator for tracing database calls."""
    db_tags = {"db.type": "postgresql", "span.kind": "client"}
    if table:
        db_tags["db.table"] = table
    
    return trace_function(f"db.{operation}", db_tags)

# Context propagation utilities
def get_trace_headers() -> Dict[str, str]:
    """Get trace headers for propagating context to external services."""
    headers = {}
    
    trace_id = trace_id_var.get()
    if trace_id:
        headers["X-Trace-Id"] = trace_id
    
    span_id = span_id_var.get()
    if span_id:
        headers["X-Span-Id"] = span_id
    
    return headers

def set_trace_context_from_headers(headers: Dict[str, str]):
    """Set trace context from incoming headers."""
    if "X-Trace-Id" in headers:
        trace_id_var.set(headers["X-Trace-Id"])
    
    if "X-Span-Id" in headers:
        parent_span_id_var.set(headers["X-Span-Id"])

# Trace analysis utilities
class TraceAnalyzer:
    """Utilities for analyzing trace data."""
    
    def __init__(self, tracer: Tracer):
        self.tracer = tracer
    
    def get_slow_traces(self, threshold_ms: float = 1000, limit: int = 10) -> List[Trace]:
        """Get traces that exceed duration threshold."""
        all_traces = self.tracer.get_traces(limit=1000)
        slow_traces = [
            trace for trace in all_traces
            if trace.duration_ms and trace.duration_ms > threshold_ms
        ]
        
        # Sort by duration, slowest first
        slow_traces.sort(key=lambda t: t.duration_ms or 0, reverse=True)
        return slow_traces[:limit]
    
    def get_error_traces(self, limit: int = 10) -> List[Trace]:
        """Get traces that contain errors."""
        all_traces = self.tracer.get_traces(limit=1000)
        error_traces = [
            trace for trace in all_traces
            if any(span.status == "error" for span in trace.spans)
        ]
        
        # Sort by start time, most recent first
        error_traces.sort(key=lambda t: t.start_time or datetime.min, reverse=True)
        return error_traces[:limit]
    
    def get_operation_stats(self, operation_name: str) -> Dict[str, Any]:
        """Get statistics for a specific operation."""
        all_traces = self.tracer.get_traces(limit=1000)
        
        # Find spans for this operation
        spans = []
        for trace in all_traces:
            for span in trace.spans:
                if span.operation_name == operation_name:
                    spans.append(span)
        
        if not spans:
            return {"error": "No spans found for operation"}
        
        durations = [span.duration_ms for span in spans if span.duration_ms]
        errors = [span for span in spans if span.status == "error"]
        
        stats = {
            "operation": operation_name,
            "total_calls": len(spans),
            "error_count": len(errors),
            "error_rate": len(errors) / len(spans) if spans else 0,
        }
        
        if durations:
            import statistics
            stats.update({
                "avg_duration_ms": statistics.mean(durations),
                "min_duration_ms": min(durations),
                "max_duration_ms": max(durations),
                "p95_duration_ms": self._percentile(durations, 0.95),
                "p99_duration_ms": self._percentile(durations, 0.99)
            })
        
        return stats
    
    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile value."""
        if not values:
            return 0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile)
        return sorted_values[min(index, len(sorted_values) - 1)]

def get_trace_analyzer() -> TraceAnalyzer:
    """Get trace analyzer instance."""
    return TraceAnalyzer(get_tracer())