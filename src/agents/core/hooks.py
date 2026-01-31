"""
Advanced Hook System for Agent Lifecycle Management.

Provides extensible hooks for:
- Pre/post execution
- Error handling
- Tool calls
- State changes
- Custom events

Inspired by Claude Agent SDK hooks pattern.
"""

import asyncio
import time
from abc import ABC
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, Coroutine, Optional, TypeVar, Union
import traceback


class HookType(str, Enum):
    """Types of lifecycle hooks."""

    # Agent lifecycle
    BEFORE_EXECUTE = "before_execute"
    AFTER_EXECUTE = "after_execute"
    ON_ERROR = "on_error"

    # Tool hooks
    BEFORE_TOOL_CALL = "before_tool_call"
    AFTER_TOOL_CALL = "after_tool_call"
    ON_TOOL_ERROR = "on_tool_error"

    # State hooks
    ON_STATE_CHANGE = "on_state_change"
    ON_PHASE_TRANSITION = "on_phase_transition"

    # Memory hooks
    ON_MEMORY_STORE = "on_memory_store"
    ON_MEMORY_RETRIEVE = "on_memory_retrieve"

    # Approval hooks
    BEFORE_APPROVAL = "before_approval"
    AFTER_APPROVAL = "after_approval"

    # Custom
    CUSTOM = "custom"


class HookPriority(int, Enum):
    """Priority levels for hook execution order."""

    HIGHEST = 0
    HIGH = 25
    NORMAL = 50
    LOW = 75
    LOWEST = 100


@dataclass
class HookContext:
    """Context passed to hook handlers."""

    hook_type: HookType
    agent_name: str
    timestamp: float = field(default_factory=time.time)
    data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    # Mutable state that hooks can modify
    should_continue: bool = True
    modified_data: Optional[dict[str, Any]] = None
    error: Optional[Exception] = None


@dataclass
class HookResult:
    """Result from hook execution."""

    success: bool
    hook_name: str
    hook_type: HookType
    execution_time_ms: float = 0
    error: Optional[str] = None
    modified_context: Optional[HookContext] = None


HookHandler = Callable[[HookContext], Coroutine[Any, Any, Optional[HookContext]]]


@dataclass
class Hook:
    """A registered hook."""

    name: str
    hook_type: HookType
    handler: HookHandler
    priority: HookPriority = HookPriority.NORMAL
    enabled: bool = True
    description: str = ""
    tags: list[str] = field(default_factory=list)
    timeout_seconds: float = 30.0

    # Execution stats
    execution_count: int = 0
    total_execution_time_ms: float = 0
    last_error: Optional[str] = None

    def __hash__(self):
        return hash(self.name)


class HookManager:
    """
    Central hook management system.

    Features:
    - Register/unregister hooks dynamically
    - Priority-based execution order
    - Async hook execution
    - Hook chaining and context modification
    - Error isolation (one hook failure doesn't stop others)
    - Execution analytics
    """

    def __init__(self):
        self._hooks: dict[HookType, list[Hook]] = {ht: [] for ht in HookType}
        self._global_hooks: list[Hook] = []
        self._paused: bool = False
        self._execution_history: list[HookResult] = []
        self._max_history = 500

    def register(
        self,
        name: str,
        hook_type: HookType,
        handler: HookHandler,
        priority: HookPriority = HookPriority.NORMAL,
        description: str = "",
        tags: Optional[list[str]] = None,
        timeout_seconds: float = 30.0,
    ) -> Hook:
        """Register a new hook."""
        hook = Hook(
            name=name,
            hook_type=hook_type,
            handler=handler,
            priority=priority,
            description=description,
            tags=tags or [],
            timeout_seconds=timeout_seconds,
        )

        # Insert in priority order
        hooks_list = self._hooks[hook_type]
        insert_idx = 0
        for i, existing in enumerate(hooks_list):
            if existing.priority.value > priority.value:
                insert_idx = i
                break
            insert_idx = i + 1

        hooks_list.insert(insert_idx, hook)
        return hook

    def register_global(
        self,
        name: str,
        handler: HookHandler,
        priority: HookPriority = HookPriority.NORMAL,
    ) -> Hook:
        """Register a global hook that runs for all hook types."""
        hook = Hook(
            name=name,
            hook_type=HookType.CUSTOM,
            handler=handler,
            priority=priority,
        )
        self._global_hooks.append(hook)
        return hook

    def unregister(self, name: str) -> bool:
        """Unregister a hook by name."""
        for hook_type, hooks in self._hooks.items():
            for hook in hooks:
                if hook.name == name:
                    hooks.remove(hook)
                    return True

        for hook in self._global_hooks:
            if hook.name == name:
                self._global_hooks.remove(hook)
                return True

        return False

    def enable(self, name: str) -> bool:
        """Enable a hook."""
        hook = self._find_hook(name)
        if hook:
            hook.enabled = True
            return True
        return False

    def disable(self, name: str) -> bool:
        """Disable a hook."""
        hook = self._find_hook(name)
        if hook:
            hook.enabled = False
            return True
        return False

    def _find_hook(self, name: str) -> Optional[Hook]:
        """Find a hook by name."""
        for hooks in self._hooks.values():
            for hook in hooks:
                if hook.name == name:
                    return hook

        for hook in self._global_hooks:
            if hook.name == name:
                return hook

        return None

    def pause(self) -> None:
        """Pause all hook execution."""
        self._paused = True

    def resume(self) -> None:
        """Resume hook execution."""
        self._paused = False

    async def trigger(
        self,
        hook_type: HookType,
        agent_name: str,
        data: Optional[dict[str, Any]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> HookContext:
        """
        Trigger hooks of a specific type.

        Returns the final context after all hooks have run.
        """
        if self._paused:
            return HookContext(
                hook_type=hook_type,
                agent_name=agent_name,
                data=data or {},
                metadata=metadata or {},
            )

        context = HookContext(
            hook_type=hook_type,
            agent_name=agent_name,
            data=data or {},
            metadata=metadata or {},
        )

        # Collect hooks to run
        hooks_to_run = [
            h for h in self._hooks[hook_type] if h.enabled
        ] + [h for h in self._global_hooks if h.enabled]

        # Sort by priority
        hooks_to_run.sort(key=lambda h: h.priority.value)

        # Execute hooks in order
        for hook in hooks_to_run:
            if not context.should_continue:
                break

            result = await self._execute_hook(hook, context)
            self._record_result(result)

            # Update context if hook returned modifications
            if result.success and result.modified_context:
                context = result.modified_context

        return context

    async def _execute_hook(self, hook: Hook, context: HookContext) -> HookResult:
        """Execute a single hook with timeout and error handling."""
        start_time = time.time()

        try:
            # Execute with timeout
            modified_context = await asyncio.wait_for(
                hook.handler(context),
                timeout=hook.timeout_seconds,
            )

            execution_time = (time.time() - start_time) * 1000

            # Update hook stats
            hook.execution_count += 1
            hook.total_execution_time_ms += execution_time

            return HookResult(
                success=True,
                hook_name=hook.name,
                hook_type=hook.hook_type,
                execution_time_ms=execution_time,
                modified_context=modified_context or context,
            )

        except asyncio.TimeoutError:
            error_msg = f"Hook '{hook.name}' timed out after {hook.timeout_seconds}s"
            hook.last_error = error_msg
            return HookResult(
                success=False,
                hook_name=hook.name,
                hook_type=hook.hook_type,
                execution_time_ms=(time.time() - start_time) * 1000,
                error=error_msg,
            )

        except Exception as e:
            error_msg = f"Hook '{hook.name}' failed: {str(e)}"
            hook.last_error = error_msg
            return HookResult(
                success=False,
                hook_name=hook.name,
                hook_type=hook.hook_type,
                execution_time_ms=(time.time() - start_time) * 1000,
                error=error_msg,
            )

    def _record_result(self, result: HookResult) -> None:
        """Record hook execution result."""
        self._execution_history.append(result)

        if len(self._execution_history) > self._max_history:
            self._execution_history = self._execution_history[-self._max_history:]

    def list_hooks(
        self,
        hook_type: Optional[HookType] = None,
        enabled_only: bool = False,
    ) -> list[Hook]:
        """List registered hooks."""
        if hook_type:
            hooks = self._hooks[hook_type]
        else:
            hooks = []
            for h_list in self._hooks.values():
                hooks.extend(h_list)
            hooks.extend(self._global_hooks)

        if enabled_only:
            hooks = [h for h in hooks if h.enabled]

        return hooks

    def get_analytics(self) -> dict[str, Any]:
        """Get hook execution analytics."""
        hook_stats = {}

        for hooks in self._hooks.values():
            for hook in hooks:
                hook_stats[hook.name] = {
                    "type": hook.hook_type.value,
                    "executions": hook.execution_count,
                    "avg_time_ms": (
                        hook.total_execution_time_ms / hook.execution_count
                        if hook.execution_count > 0 else 0
                    ),
                    "last_error": hook.last_error,
                    "enabled": hook.enabled,
                }

        return {
            "total_hooks": sum(len(h) for h in self._hooks.values()) + len(self._global_hooks),
            "total_executions": len(self._execution_history),
            "hook_stats": hook_stats,
            "paused": self._paused,
        }


# Decorator factories for easy hook registration

def hook(
    hook_type: HookType,
    name: Optional[str] = None,
    priority: HookPriority = HookPriority.NORMAL,
    description: str = "",
):
    """Decorator to mark a function as a hook handler."""
    def decorator(func: HookHandler) -> HookHandler:
        func._hook_type = hook_type
        func._hook_name = name or func.__name__
        func._hook_priority = priority
        func._hook_description = description
        return func
    return decorator


def before_execute(
    name: Optional[str] = None,
    priority: HookPriority = HookPriority.NORMAL,
):
    """Decorator for before_execute hooks."""
    return hook(HookType.BEFORE_EXECUTE, name, priority)


def after_execute(
    name: Optional[str] = None,
    priority: HookPriority = HookPriority.NORMAL,
):
    """Decorator for after_execute hooks."""
    return hook(HookType.AFTER_EXECUTE, name, priority)


def on_error(
    name: Optional[str] = None,
    priority: HookPriority = HookPriority.NORMAL,
):
    """Decorator for on_error hooks."""
    return hook(HookType.ON_ERROR, name, priority)


def on_tool_call(
    name: Optional[str] = None,
    priority: HookPriority = HookPriority.NORMAL,
):
    """Decorator for tool call hooks."""
    return hook(HookType.AFTER_TOOL_CALL, name, priority)


def on_state_change(
    name: Optional[str] = None,
    priority: HookPriority = HookPriority.NORMAL,
):
    """Decorator for state change hooks."""
    return hook(HookType.ON_STATE_CHANGE, name, priority)


class HookableAgent(ABC):
    """
    Mixin class that adds hook support to agents.

    Use this to automatically trigger hooks at appropriate lifecycle points.
    """

    def __init__(self, hook_manager: Optional[HookManager] = None):
        self._hook_manager = hook_manager or HookManager()
        self._agent_name = self.__class__.__name__

    async def _trigger_hook(
        self,
        hook_type: HookType,
        data: Optional[dict[str, Any]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> HookContext:
        """Trigger a hook and return the context."""
        return await self._hook_manager.trigger(
            hook_type=hook_type,
            agent_name=self._agent_name,
            data=data,
            metadata=metadata,
        )

    def register_hook(
        self,
        name: str,
        hook_type: HookType,
        handler: HookHandler,
        priority: HookPriority = HookPriority.NORMAL,
    ) -> Hook:
        """Register a hook for this agent."""
        return self._hook_manager.register(
            name=name,
            hook_type=hook_type,
            handler=handler,
            priority=priority,
        )

    def discover_hooks(self) -> int:
        """Discover and register hooks from decorated methods."""
        count = 0
        for name in dir(self):
            method = getattr(self, name)
            if hasattr(method, "_hook_type"):
                self._hook_manager.register(
                    name=getattr(method, "_hook_name", name),
                    hook_type=method._hook_type,
                    handler=method,
                    priority=getattr(method, "_hook_priority", HookPriority.NORMAL),
                    description=getattr(method, "_hook_description", ""),
                )
                count += 1
        return count


# Pre-built hooks for common patterns

async def logging_hook(context: HookContext) -> HookContext:
    """Log all hook executions."""
    print(f"[Hook] {context.hook_type.value} triggered for {context.agent_name}")
    return context


async def timing_hook(context: HookContext) -> HookContext:
    """Add timing metadata."""
    context.metadata["hook_triggered_at"] = time.time()
    return context


async def validation_hook(context: HookContext) -> HookContext:
    """Validate context data."""
    if not context.data:
        context.should_continue = False
        context.error = ValueError("Empty data in context")
    return context


# Global hook manager instance
_global_hook_manager: Optional[HookManager] = None


def get_global_hook_manager() -> HookManager:
    """Get or create the global hook manager."""
    global _global_hook_manager
    if _global_hook_manager is None:
        _global_hook_manager = HookManager()
    return _global_hook_manager
