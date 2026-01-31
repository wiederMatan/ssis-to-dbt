"""
Event Bus for Agent Communication.

Provides pub/sub messaging between agents and components.
Supports both sync and async event handling.
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine, Optional, Union
from collections import defaultdict
import threading


class EventType(str, Enum):
    """Standard event types."""

    # Agent events
    AGENT_STARTED = "agent.started"
    AGENT_COMPLETED = "agent.completed"
    AGENT_FAILED = "agent.failed"
    AGENT_PAUSED = "agent.paused"
    AGENT_RESUMED = "agent.resumed"

    # Pipeline events
    PIPELINE_STARTED = "pipeline.started"
    PIPELINE_COMPLETED = "pipeline.completed"
    PIPELINE_FAILED = "pipeline.failed"
    PHASE_STARTED = "phase.started"
    PHASE_COMPLETED = "phase.completed"

    # Tool events
    TOOL_CALLED = "tool.called"
    TOOL_COMPLETED = "tool.completed"
    TOOL_FAILED = "tool.failed"

    # Memory events
    MEMORY_STORED = "memory.stored"
    MEMORY_RETRIEVED = "memory.retrieved"
    MEMORY_DELETED = "memory.deleted"

    # Approval events
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_GRANTED = "approval.granted"
    APPROVAL_DENIED = "approval.denied"

    # Validation events
    VALIDATION_STARTED = "validation.started"
    VALIDATION_PASSED = "validation.passed"
    VALIDATION_FAILED = "validation.failed"

    # Custom events
    CUSTOM = "custom"


class EventPriority(int, Enum):
    """Event priority levels."""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Event:
    """An event in the system."""

    type: Union[EventType, str]
    source: str
    data: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    priority: EventPriority = EventPriority.NORMAL
    metadata: dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value if isinstance(self.type, EventType) else self.type,
            "source": self.source,
            "data": self.data,
            "timestamp": self.timestamp,
            "priority": self.priority.value,
            "metadata": self.metadata,
            "correlation_id": self.correlation_id,
        }


EventHandler = Union[
    Callable[[Event], None],
    Callable[[Event], Coroutine[Any, Any, None]],
]


@dataclass
class Subscription:
    """A subscription to events."""

    id: str
    event_type: Union[EventType, str]
    handler: EventHandler
    filter_fn: Optional[Callable[[Event], bool]] = None
    is_async: bool = False
    active: bool = True
    execution_count: int = 0


class EventBus:
    """
    Central event bus for pub/sub messaging.

    Features:
    - Async and sync event handlers
    - Event filtering
    - Event history
    - Dead letter queue for failed events
    - Correlation tracking
    """

    def __init__(self, max_history: int = 1000):
        self._subscriptions: dict[str, list[Subscription]] = defaultdict(list)
        self._history: list[Event] = []
        self._dead_letters: list[tuple[Event, str]] = []
        self._max_history = max_history
        self._lock = threading.Lock()
        self._paused = False

    def subscribe(
        self,
        event_type: Union[EventType, str],
        handler: EventHandler,
        filter_fn: Optional[Callable[[Event], bool]] = None,
    ) -> str:
        """Subscribe to events of a specific type."""
        event_key = event_type.value if isinstance(event_type, EventType) else event_type
        is_async = asyncio.iscoroutinefunction(handler)

        subscription = Subscription(
            id=str(uuid.uuid4()),
            event_type=event_type,
            handler=handler,
            filter_fn=filter_fn,
            is_async=is_async,
        )

        with self._lock:
            self._subscriptions[event_key].append(subscription)

        return subscription.id

    def subscribe_all(
        self,
        handler: EventHandler,
        filter_fn: Optional[Callable[[Event], bool]] = None,
    ) -> str:
        """Subscribe to all events."""
        return self.subscribe("*", handler, filter_fn)

    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events."""
        with self._lock:
            for event_type, subs in self._subscriptions.items():
                for sub in subs:
                    if sub.id == subscription_id:
                        subs.remove(sub)
                        return True
        return False

    async def publish(self, event: Event) -> int:
        """
        Publish an event to all subscribers.

        Returns the number of handlers invoked.
        """
        if self._paused:
            return 0

        # Record in history
        self._record_event(event)

        event_key = event.type.value if isinstance(event.type, EventType) else event.type

        # Get matching subscriptions
        handlers_to_invoke = []

        with self._lock:
            # Type-specific subscribers
            for sub in self._subscriptions.get(event_key, []):
                if sub.active and (not sub.filter_fn or sub.filter_fn(event)):
                    handlers_to_invoke.append(sub)

            # Wildcard subscribers
            for sub in self._subscriptions.get("*", []):
                if sub.active and (not sub.filter_fn or sub.filter_fn(event)):
                    handlers_to_invoke.append(sub)

        # Invoke handlers
        invoked = 0
        for sub in handlers_to_invoke:
            try:
                if sub.is_async:
                    await sub.handler(event)
                else:
                    sub.handler(event)

                sub.execution_count += 1
                invoked += 1

            except Exception as e:
                self._dead_letters.append((event, f"Handler failed: {str(e)}"))

        return invoked

    def publish_sync(self, event: Event) -> int:
        """Synchronous publish (for non-async contexts)."""
        return asyncio.get_event_loop().run_until_complete(self.publish(event))

    async def emit(
        self,
        event_type: Union[EventType, str],
        source: str,
        data: Optional[dict[str, Any]] = None,
        priority: EventPriority = EventPriority.NORMAL,
        correlation_id: Optional[str] = None,
    ) -> Event:
        """Convenience method to create and publish an event."""
        event = Event(
            type=event_type,
            source=source,
            data=data or {},
            priority=priority,
            correlation_id=correlation_id,
        )
        await self.publish(event)
        return event

    def _record_event(self, event: Event) -> None:
        """Record event in history."""
        self._history.append(event)

        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

    def pause(self) -> None:
        """Pause event publishing."""
        self._paused = True

    def resume(self) -> None:
        """Resume event publishing."""
        self._paused = False

    def get_history(
        self,
        event_type: Optional[Union[EventType, str]] = None,
        source: Optional[str] = None,
        limit: int = 100,
    ) -> list[Event]:
        """Get event history with optional filtering."""
        events = self._history

        if event_type:
            event_key = event_type.value if isinstance(event_type, EventType) else event_type
            events = [
                e for e in events
                if (e.type.value if isinstance(e.type, EventType) else e.type) == event_key
            ]

        if source:
            events = [e for e in events if e.source == source]

        return events[-limit:]

    def get_dead_letters(self, limit: int = 100) -> list[tuple[Event, str]]:
        """Get events that failed to deliver."""
        return self._dead_letters[-limit:]

    def clear_dead_letters(self) -> int:
        """Clear dead letter queue."""
        count = len(self._dead_letters)
        self._dead_letters = []
        return count

    def get_stats(self) -> dict[str, Any]:
        """Get event bus statistics."""
        sub_counts = {k: len(v) for k, v in self._subscriptions.items()}

        return {
            "total_subscriptions": sum(sub_counts.values()),
            "subscriptions_by_type": sub_counts,
            "history_count": len(self._history),
            "dead_letter_count": len(self._dead_letters),
            "paused": self._paused,
        }


class CorrelatedEventStream:
    """
    Track events with the same correlation ID.

    Useful for following a request through the system.
    """

    def __init__(self, event_bus: EventBus, correlation_id: str):
        self._event_bus = event_bus
        self._correlation_id = correlation_id
        self._events: list[Event] = []
        self._subscription_id: Optional[str] = None

    async def __aenter__(self):
        """Start tracking correlated events."""
        def handler(event: Event):
            if event.correlation_id == self._correlation_id:
                self._events.append(event)

        self._subscription_id = self._event_bus.subscribe("*", handler)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Stop tracking."""
        if self._subscription_id:
            self._event_bus.unsubscribe(self._subscription_id)

    @property
    def events(self) -> list[Event]:
        """Get collected events."""
        return self._events

    def to_timeline(self) -> list[dict[str, Any]]:
        """Get events as a timeline."""
        sorted_events = sorted(self._events, key=lambda e: e.timestamp)
        return [e.to_dict() for e in sorted_events]


# Global event bus instance
_global_event_bus: Optional[EventBus] = None


def get_global_event_bus() -> EventBus:
    """Get or create the global event bus."""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus
