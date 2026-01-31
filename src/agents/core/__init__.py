"""Advanced agent core framework with tools, memory, hooks, and graph orchestration."""

from .tools import Tool, ToolRegistry, ToolResult, ToolParameter, tool, ToolCategory, ToolPermission
from .memory import (
    MemoryManager,
    MemoryType,
    MemoryEntry,
    MemoryPriority,
    ShortTermMemory,
    LongTermMemory,
    SemanticMemory,
    EpisodicMemory,
    ProceduralMemory,
)
from .hooks import (
    HookManager,
    HookType,
    HookPriority,
    Hook,
    HookContext,
    hook,
    before_execute,
    after_execute,
    on_error,
    on_tool_call,
    on_state_change,
    HookableAgent,
)
from .events import EventBus, Event, EventType, EventPriority
from .tracing import Tracer, Span, SpanContext, SpanStatus, MetricsCollector
from .agent import (
    AdvancedAgent,
    ReactAgent,
    AgentConfig,
    AgentResult,
    AgentStatus,
    AgentCapability,
    AgentMessage,
)
from .graph import (
    WorkflowGraph,
    StateGraph,
    GraphState,
    GraphNode,
    GraphEdge,
    NodeStatus,
    EdgeCondition,
    ExecutionResult,
    WorkflowBuilder,
)

__all__ = [
    # Tools
    "Tool",
    "ToolRegistry",
    "ToolResult",
    "ToolParameter",
    "ToolCategory",
    "ToolPermission",
    "tool",
    # Memory
    "MemoryManager",
    "MemoryType",
    "MemoryEntry",
    "MemoryPriority",
    "ShortTermMemory",
    "LongTermMemory",
    "SemanticMemory",
    "EpisodicMemory",
    "ProceduralMemory",
    # Hooks
    "HookManager",
    "HookType",
    "HookPriority",
    "Hook",
    "HookContext",
    "HookableAgent",
    "hook",
    "before_execute",
    "after_execute",
    "on_error",
    "on_tool_call",
    "on_state_change",
    # Events
    "EventBus",
    "Event",
    "EventType",
    "EventPriority",
    # Tracing
    "Tracer",
    "Span",
    "SpanContext",
    "SpanStatus",
    "MetricsCollector",
    # Agent
    "AdvancedAgent",
    "ReactAgent",
    "AgentConfig",
    "AgentResult",
    "AgentStatus",
    "AgentCapability",
    "AgentMessage",
    # Graph
    "WorkflowGraph",
    "StateGraph",
    "GraphState",
    "GraphNode",
    "GraphEdge",
    "NodeStatus",
    "EdgeCondition",
    "ExecutionResult",
    "WorkflowBuilder",
]
