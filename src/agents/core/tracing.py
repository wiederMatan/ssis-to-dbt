"""
Distributed Tracing and Observability.

Provides OpenTelemetry-compatible tracing for agent operations.
Tracks execution flow, performance, and errors across the system.
"""

import json
import time
import uuid
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional, Union
import threading


class SpanStatus(str, Enum):
    """Status of a span."""

    UNSET = "unset"
    OK = "ok"
    ERROR = "error"


class SpanKind(str, Enum):
    """Type of span."""

    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"


@dataclass
class SpanContext:
    """Context for span propagation."""

    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    trace_flags: int = 1  # Sampled
    trace_state: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "trace_flags": self.trace_flags,
        }


@dataclass
class SpanEvent:
    """An event within a span."""

    name: str
    timestamp: float
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class Span:
    """A single span representing an operation."""

    name: str
    context: SpanContext
    kind: SpanKind = SpanKind.INTERNAL
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    status: SpanStatus = SpanStatus.UNSET
    status_message: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[SpanEvent] = field(default_factory=list)
    links: list[SpanContext] = field(default_factory=list)

    # Computed properties
    @property
    def duration_ms(self) -> float:
        """Get duration in milliseconds."""
        if self.end_time is None:
            return (time.time() - self.start_time) * 1000
        return (self.end_time - self.start_time) * 1000

    @property
    def is_root(self) -> bool:
        """Check if this is a root span."""
        return self.context.parent_span_id is None

    def set_attribute(self, key: str, value: Any) -> "Span":
        """Set an attribute."""
        self.attributes[key] = value
        return self

    def set_attributes(self, attributes: dict[str, Any]) -> "Span":
        """Set multiple attributes."""
        self.attributes.update(attributes)
        return self

    def add_event(
        self,
        name: str,
        attributes: Optional[dict[str, Any]] = None,
    ) -> "Span":
        """Add an event to the span."""
        self.events.append(SpanEvent(
            name=name,
            timestamp=time.time(),
            attributes=attributes or {},
        ))
        return self

    def set_status(
        self,
        status: SpanStatus,
        message: str = "",
    ) -> "Span":
        """Set span status."""
        self.status = status
        self.status_message = message
        return self

    def set_ok(self) -> "Span":
        """Mark span as successful."""
        return self.set_status(SpanStatus.OK)

    def set_error(self, message: str) -> "Span":
        """Mark span as errored."""
        return self.set_status(SpanStatus.ERROR, message)

    def end(self, end_time: Optional[float] = None) -> "Span":
        """End the span."""
        self.end_time = end_time or time.time()
        return self

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary (OpenTelemetry-like format)."""
        return {
            "name": self.name,
            "context": self.context.to_dict(),
            "kind": self.kind.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": {
                "code": self.status.value,
                "message": self.status_message,
            },
            "attributes": self.attributes,
            "events": [
                {
                    "name": e.name,
                    "timestamp": e.timestamp,
                    "attributes": e.attributes,
                }
                for e in self.events
            ],
        }


class SpanExporter:
    """Base class for span exporters."""

    def export(self, spans: list[Span]) -> bool:
        """Export spans. Return True if successful."""
        raise NotImplementedError


class ConsoleExporter(SpanExporter):
    """Export spans to console."""

    def export(self, spans: list[Span]) -> bool:
        for span in spans:
            status_icon = "✓" if span.status == SpanStatus.OK else "✗" if span.status == SpanStatus.ERROR else "○"
            print(f"[{status_icon}] {span.name} ({span.duration_ms:.2f}ms)")
        return True


class FileExporter(SpanExporter):
    """Export spans to JSON file."""

    def __init__(self, output_path: Path):
        self._output_path = Path(output_path)
        self._output_path.parent.mkdir(parents=True, exist_ok=True)

    def export(self, spans: list[Span]) -> bool:
        try:
            existing = []
            if self._output_path.exists():
                with open(self._output_path) as f:
                    existing = json.load(f)

            existing.extend([s.to_dict() for s in spans])

            with open(self._output_path, "w") as f:
                json.dump(existing, f, indent=2, default=str)

            return True
        except Exception:
            return False


class Tracer:
    """
    Distributed tracer for agent operations.

    Features:
    - Hierarchical span tracking
    - Context propagation
    - Multiple exporters
    - Sampling support
    - Async context management
    """

    def __init__(
        self,
        service_name: str,
        exporters: Optional[list[SpanExporter]] = None,
        sample_rate: float = 1.0,
    ):
        self._service_name = service_name
        self._exporters = exporters or []
        self._sample_rate = sample_rate
        self._spans: list[Span] = []
        self._active_spans: dict[str, Span] = {}
        self._context_stack: list[SpanContext] = []
        self._lock = threading.Lock()

    def _generate_id(self) -> str:
        """Generate a random ID."""
        return uuid.uuid4().hex[:16]

    def _should_sample(self) -> bool:
        """Determine if this trace should be sampled."""
        import random
        return random.random() < self._sample_rate

    def get_current_context(self) -> Optional[SpanContext]:
        """Get the current active span context."""
        if self._context_stack:
            return self._context_stack[-1]
        return None

    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[dict[str, Any]] = None,
        parent_context: Optional[SpanContext] = None,
    ) -> Span:
        """Start a new span."""
        current_context = parent_context or self.get_current_context()

        if current_context:
            context = SpanContext(
                trace_id=current_context.trace_id,
                span_id=self._generate_id(),
                parent_span_id=current_context.span_id,
            )
        else:
            context = SpanContext(
                trace_id=self._generate_id(),
                span_id=self._generate_id(),
            )

        span = Span(
            name=name,
            context=context,
            kind=kind,
            attributes={
                "service.name": self._service_name,
                **(attributes or {}),
            },
        )

        with self._lock:
            self._active_spans[context.span_id] = span
            self._context_stack.append(context)

        return span

    def end_span(self, span: Span) -> None:
        """End a span and export it."""
        span.end()

        with self._lock:
            if span.context.span_id in self._active_spans:
                del self._active_spans[span.context.span_id]

            if self._context_stack and self._context_stack[-1].span_id == span.context.span_id:
                self._context_stack.pop()

            self._spans.append(span)

        # Export immediately if we have exporters
        if self._exporters:
            for exporter in self._exporters:
                try:
                    exporter.export([span])
                except Exception:
                    pass

    @contextmanager
    def span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[dict[str, Any]] = None,
    ):
        """Context manager for creating spans."""
        span = self.start_span(name, kind, attributes)
        try:
            yield span
            if span.status == SpanStatus.UNSET:
                span.set_ok()
        except Exception as e:
            span.set_error(str(e))
            span.add_event("exception", {"message": str(e)})
            raise
        finally:
            self.end_span(span)

    @asynccontextmanager
    async def async_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[dict[str, Any]] = None,
    ):
        """Async context manager for creating spans."""
        span = self.start_span(name, kind, attributes)
        try:
            yield span
            if span.status == SpanStatus.UNSET:
                span.set_ok()
        except Exception as e:
            span.set_error(str(e))
            span.add_event("exception", {"message": str(e)})
            raise
        finally:
            self.end_span(span)

    def trace(
        self,
        name: Optional[str] = None,
        kind: SpanKind = SpanKind.INTERNAL,
    ):
        """Decorator to trace a function."""
        def decorator(func: Callable) -> Callable:
            span_name = name or func.__name__

            if asyncio.iscoroutinefunction(func):
                async def async_wrapper(*args, **kwargs):
                    async with self.async_span(span_name, kind):
                        return await func(*args, **kwargs)
                return async_wrapper
            else:
                def sync_wrapper(*args, **kwargs):
                    with self.span(span_name, kind):
                        return func(*args, **kwargs)
                return sync_wrapper

        return decorator

    def get_trace(self, trace_id: str) -> list[Span]:
        """Get all spans for a trace."""
        return [s for s in self._spans if s.context.trace_id == trace_id]

    def get_active_spans(self) -> list[Span]:
        """Get currently active spans."""
        return list(self._active_spans.values())

    def get_stats(self) -> dict[str, Any]:
        """Get tracer statistics."""
        completed_spans = [s for s in self._spans if s.end_time is not None]

        status_counts = {
            SpanStatus.OK: 0,
            SpanStatus.ERROR: 0,
            SpanStatus.UNSET: 0,
        }
        for span in completed_spans:
            status_counts[span.status] += 1

        avg_duration = (
            sum(s.duration_ms for s in completed_spans) / len(completed_spans)
            if completed_spans else 0
        )

        return {
            "service_name": self._service_name,
            "total_spans": len(self._spans),
            "active_spans": len(self._active_spans),
            "status_counts": {k.value: v for k, v in status_counts.items()},
            "avg_duration_ms": avg_duration,
            "sample_rate": self._sample_rate,
        }

    def export_all(self) -> bool:
        """Export all recorded spans."""
        if not self._exporters:
            return False

        success = True
        for exporter in self._exporters:
            try:
                if not exporter.export(self._spans):
                    success = False
            except Exception:
                success = False

        return success

    def clear(self) -> None:
        """Clear all recorded spans."""
        with self._lock:
            self._spans = []


# Import for asynccontextmanager
import asyncio


class MetricsCollector:
    """
    Simple metrics collector for agent operations.

    Tracks counters, gauges, and histograms.
    """

    def __init__(self):
        self._counters: dict[str, int] = {}
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def increment(self, name: str, value: int = 1, tags: Optional[dict[str, str]] = None) -> None:
        """Increment a counter."""
        key = self._make_key(name, tags)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + value

    def gauge(self, name: str, value: float, tags: Optional[dict[str, str]] = None) -> None:
        """Set a gauge value."""
        key = self._make_key(name, tags)
        with self._lock:
            self._gauges[key] = value

    def histogram(self, name: str, value: float, tags: Optional[dict[str, str]] = None) -> None:
        """Record a histogram value."""
        key = self._make_key(name, tags)
        with self._lock:
            if key not in self._histograms:
                self._histograms[key] = []
            self._histograms[key].append(value)

    def _make_key(self, name: str, tags: Optional[dict[str, str]]) -> str:
        """Create a unique key for the metric."""
        if not tags:
            return name
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{name}{{{tag_str}}}"

    def get_metrics(self) -> dict[str, Any]:
        """Get all metrics."""
        result = {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {},
        }

        for key, values in self._histograms.items():
            if values:
                sorted_vals = sorted(values)
                result["histograms"][key] = {
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "p50": sorted_vals[len(sorted_vals) // 2],
                    "p95": sorted_vals[int(len(sorted_vals) * 0.95)] if len(sorted_vals) >= 20 else sorted_vals[-1],
                    "p99": sorted_vals[int(len(sorted_vals) * 0.99)] if len(sorted_vals) >= 100 else sorted_vals[-1],
                }

        return result

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()


# Global instances
_global_tracer: Optional[Tracer] = None
_global_metrics: Optional[MetricsCollector] = None


def get_global_tracer(service_name: str = "ssis-to-dbt") -> Tracer:
    """Get or create the global tracer."""
    global _global_tracer
    if _global_tracer is None:
        _global_tracer = Tracer(service_name)
    return _global_tracer


def get_global_metrics() -> MetricsCollector:
    """Get or create the global metrics collector."""
    global _global_metrics
    if _global_metrics is None:
        _global_metrics = MetricsCollector()
    return _global_metrics
