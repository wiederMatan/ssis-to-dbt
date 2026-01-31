"""
Enhanced Base Agent with integrated tools, memory, hooks, and tracing.

This is the foundation for all advanced agents in the system.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, TypeVar

from pydantic import BaseModel, Field

from .tools import ToolRegistry, ToolResult, Tool
from .memory import MemoryManager, MemoryType, MemoryPriority
from .hooks import HookManager, HookType, HookContext, HookPriority
from .events import EventBus, EventType, Event
from .tracing import Tracer, Span, SpanKind


class AgentStatus(str, Enum):
    """Status of an agent."""

    IDLE = "idle"
    INITIALIZING = "initializing"
    RUNNING = "running"
    AWAITING_INPUT = "awaiting_input"
    AWAITING_APPROVAL = "awaiting_approval"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentCapability(str, Enum):
    """Capabilities an agent can have."""

    TOOL_USE = "tool_use"
    MEMORY = "memory"
    LLM = "llm"
    FILE_IO = "file_io"
    DATABASE = "database"
    EXTERNAL_API = "external_api"
    HUMAN_INTERACTION = "human_interaction"


@dataclass
class AgentConfig:
    """Configuration for an agent."""

    name: str
    description: str = ""
    capabilities: list[AgentCapability] = field(default_factory=list)
    max_iterations: int = 10
    timeout_seconds: float = 300.0
    require_approval: bool = False
    retry_on_failure: bool = True
    max_retries: int = 3


class AgentResult(BaseModel):
    """Result from agent execution."""

    success: bool
    status: AgentStatus
    data: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    requires_approval: bool = False
    approval_context: Optional[dict[str, Any]] = None
    execution_time_ms: float = 0
    iterations: int = 0
    tool_calls: int = 0
    memory_operations: int = 0

    class Config:
        use_enum_values = True


class AgentMessage(BaseModel):
    """A message in the agent's conversation history."""

    role: str  # "user", "assistant", "system", "tool"
    content: str
    timestamp: float = Field(default_factory=time.time)
    metadata: dict[str, Any] = Field(default_factory=dict)
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None


class AdvancedAgent(ABC):
    """
    Enhanced base agent with full integration of tools, memory, hooks, and tracing.

    Features:
    - Dynamic tool calling with ReAct pattern
    - Multi-level memory (short-term, long-term, semantic, episodic, procedural)
    - Lifecycle hooks for extensibility
    - Distributed tracing for observability
    - Event-driven communication
    - Conversation history management
    """

    def __init__(
        self,
        config: AgentConfig,
        tool_registry: Optional[ToolRegistry] = None,
        memory_manager: Optional[MemoryManager] = None,
        hook_manager: Optional[HookManager] = None,
        event_bus: Optional[EventBus] = None,
        tracer: Optional[Tracer] = None,
    ):
        self.config = config
        self._status = AgentStatus.IDLE
        self._iteration = 0

        # Core components (use provided or create new)
        self.tools = tool_registry or ToolRegistry()
        self.memory = memory_manager
        self.hooks = hook_manager or HookManager()
        self.events = event_bus or EventBus()
        self.tracer = tracer

        # Conversation history
        self._messages: list[AgentMessage] = []
        self._max_messages = 100

        # Execution stats
        self._total_executions = 0
        self._total_tool_calls = 0
        self._total_errors = 0
        self._start_time: Optional[float] = None

        # Register built-in hooks
        self._register_builtin_hooks()

    @property
    def name(self) -> str:
        """Agent name."""
        return self.config.name

    @property
    def status(self) -> AgentStatus:
        """Current status."""
        return self._status

    @status.setter
    def status(self, value: AgentStatus) -> None:
        """Set status and emit event."""
        old_status = self._status
        self._status = value

        asyncio.create_task(self.events.emit(
            EventType.CUSTOM,
            self.name,
            {"old_status": old_status.value, "new_status": value.value},
        ))

    def _register_builtin_hooks(self) -> None:
        """Register built-in lifecycle hooks."""
        # These can be overridden by subclasses
        pass

    async def execute(self, input_data: dict[str, Any]) -> AgentResult:
        """
        Execute the agent's main logic.

        This method handles the full lifecycle:
        1. Trigger before_execute hooks
        2. Initialize execution context
        3. Run the main agent loop (think -> act -> observe)
        4. Handle errors and retries
        5. Trigger after_execute hooks
        6. Return result
        """
        self._start_time = time.time()
        self._iteration = 0
        self._total_executions += 1

        result = AgentResult(
            success=False,
            status=AgentStatus.RUNNING,
        )

        # Create trace span if tracer available
        span: Optional[Span] = None
        if self.tracer:
            span = self.tracer.start_span(
                f"agent.{self.name}.execute",
                kind=SpanKind.INTERNAL,
                attributes={
                    "agent.name": self.name,
                    "agent.capabilities": [c.value for c in self.config.capabilities],
                },
            )

        try:
            # Trigger before_execute hooks
            hook_context = await self.hooks.trigger(
                HookType.BEFORE_EXECUTE,
                self.name,
                data=input_data,
            )

            if not hook_context.should_continue:
                result.errors.append("Execution blocked by hook")
                result.status = AgentStatus.FAILED
                return result

            # Use potentially modified input
            input_data = hook_context.modified_data or input_data

            self.status = AgentStatus.RUNNING

            # Store input in memory
            if self.memory:
                await self.memory.store(
                    content={"type": "input", "data": input_data},
                    memory_type=MemoryType.SHORT_TERM,
                    tags=["execution_input"],
                )

            # Emit start event
            await self.events.emit(
                EventType.AGENT_STARTED,
                self.name,
                {"input_keys": list(input_data.keys())},
            )

            # Main execution with retries
            retries = 0
            while retries <= self.config.max_retries:
                try:
                    result = await self._execute_with_timeout(input_data)
                    break
                except Exception as e:
                    retries += 1
                    self._total_errors += 1

                    if retries > self.config.max_retries or not self.config.retry_on_failure:
                        result.errors.append(str(e))
                        result.status = AgentStatus.FAILED
                        result.success = False

                        # Trigger error hook
                        await self.hooks.trigger(
                            HookType.ON_ERROR,
                            self.name,
                            data={"error": str(e), "retry": retries},
                        )
                        break

                    # Wait before retry (exponential backoff)
                    await asyncio.sleep(2 ** retries)

            # Trigger after_execute hooks
            await self.hooks.trigger(
                HookType.AFTER_EXECUTE,
                self.name,
                data={"result": result.model_dump()},
            )

            # Update span
            if span:
                span.set_attributes({
                    "agent.success": result.success,
                    "agent.iterations": result.iterations,
                    "agent.tool_calls": result.tool_calls,
                })
                if result.success:
                    span.set_ok()
                else:
                    span.set_error("; ".join(result.errors))

        except Exception as e:
            result.errors.append(f"Unexpected error: {str(e)}")
            result.status = AgentStatus.FAILED

            if span:
                span.set_error(str(e))

        finally:
            # Calculate execution time
            result.execution_time_ms = (time.time() - self._start_time) * 1000

            # End span
            if span:
                self.tracer.end_span(span)

            # Emit completion event
            await self.events.emit(
                EventType.AGENT_COMPLETED if result.success else EventType.AGENT_FAILED,
                self.name,
                {"success": result.success, "duration_ms": result.execution_time_ms},
            )

            self.status = result.status

        return result

    async def _execute_with_timeout(self, input_data: dict[str, Any]) -> AgentResult:
        """Execute with timeout wrapper."""
        return await asyncio.wait_for(
            self._run(input_data),
            timeout=self.config.timeout_seconds,
        )

    @abstractmethod
    async def _run(self, input_data: dict[str, Any]) -> AgentResult:
        """
        Main agent logic to be implemented by subclasses.

        This should implement the core agent loop:
        1. Think: Analyze the situation
        2. Act: Use tools or generate output
        3. Observe: Process results
        4. Repeat until done
        """
        pass

    # Tool calling methods

    async def call_tool(
        self,
        tool_name: str,
        **kwargs,
    ) -> ToolResult:
        """Call a tool and track the execution."""
        self._total_tool_calls += 1

        # Trigger before tool hook
        hook_context = await self.hooks.trigger(
            HookType.BEFORE_TOOL_CALL,
            self.name,
            data={"tool_name": tool_name, "parameters": kwargs},
        )

        if not hook_context.should_continue:
            return ToolResult(success=False, error="Tool call blocked by hook")

        # Create span for tool call
        span: Optional[Span] = None
        if self.tracer:
            span = self.tracer.start_span(
                f"tool.{tool_name}",
                kind=SpanKind.CLIENT,
                attributes={"tool.name": tool_name},
            )

        try:
            result = await self.tools.execute(tool_name, self.name, **kwargs)

            # Trigger after tool hook
            await self.hooks.trigger(
                HookType.AFTER_TOOL_CALL,
                self.name,
                data={"tool_name": tool_name, "result": result.to_dict()},
            )

            # Add to conversation history
            self._add_message(AgentMessage(
                role="tool",
                content=str(result.data) if result.success else result.error,
                tool_name=tool_name,
                metadata={"success": result.success},
            ))

            if span:
                if result.success:
                    span.set_ok()
                else:
                    span.set_error(result.error or "Unknown error")

            return result

        except Exception as e:
            if span:
                span.set_error(str(e))
            raise

        finally:
            if span:
                self.tracer.end_span(span)

    def get_available_tools(self) -> list[dict[str, Any]]:
        """Get schemas for all available tools."""
        return self.tools.get_schemas()

    # Memory methods

    async def remember(
        self,
        content: Any,
        memory_type: MemoryType = MemoryType.SHORT_TERM,
        tags: Optional[list[str]] = None,
        priority: MemoryPriority = MemoryPriority.MEDIUM,
    ) -> Optional[str]:
        """Store something in memory."""
        if not self.memory:
            return None

        return await self.memory.store(
            content=content,
            memory_type=memory_type,
            tags=tags,
            priority=priority,
            metadata={"agent": self.name},
        )

    async def recall(
        self,
        query: str,
        memory_types: Optional[list[MemoryType]] = None,
        limit: int = 10,
    ) -> list[Any]:
        """Retrieve from memory."""
        if not self.memory:
            return []

        entries = await self.memory.search(query, memory_types, limit)
        return [e.content for e in entries]

    async def get_context(self, query: str, max_tokens: int = 4000) -> str:
        """Get memory context for LLM."""
        if not self.memory:
            return ""
        return await self.memory.get_context(query, max_tokens)

    # Message/conversation methods

    def _add_message(self, message: AgentMessage) -> None:
        """Add a message to history."""
        self._messages.append(message)

        # Trim if needed
        if len(self._messages) > self._max_messages:
            self._messages = self._messages[-self._max_messages:]

    def add_user_message(self, content: str) -> None:
        """Add a user message."""
        self._add_message(AgentMessage(role="user", content=content))

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message."""
        self._add_message(AgentMessage(role="assistant", content=content))

    def add_system_message(self, content: str) -> None:
        """Add a system message."""
        self._add_message(AgentMessage(role="system", content=content))

    def get_messages(self, limit: Optional[int] = None) -> list[AgentMessage]:
        """Get conversation history."""
        if limit:
            return self._messages[-limit:]
        return self._messages

    def clear_messages(self) -> None:
        """Clear conversation history."""
        self._messages = []

    # Approval methods

    async def request_approval(
        self,
        action: str,
        details: dict[str, Any],
    ) -> bool:
        """Request human approval for an action."""
        self.status = AgentStatus.AWAITING_APPROVAL

        # Trigger approval hook
        hook_context = await self.hooks.trigger(
            HookType.BEFORE_APPROVAL,
            self.name,
            data={"action": action, "details": details},
        )

        if not hook_context.should_continue:
            return False

        # Emit approval event
        await self.events.emit(
            EventType.APPROVAL_REQUESTED,
            self.name,
            {"action": action, "details": details},
        )

        # Actual approval logic should be implemented by orchestrator/UI
        # This is a placeholder that returns the hook decision
        return hook_context.data.get("approved", False)

    # Stats and info

    def get_stats(self) -> dict[str, Any]:
        """Get agent execution statistics."""
        return {
            "name": self.name,
            "status": self.status.value,
            "total_executions": self._total_executions,
            "total_tool_calls": self._total_tool_calls,
            "total_errors": self._total_errors,
            "message_count": len(self._messages),
            "capabilities": [c.value for c in self.config.capabilities],
        }

    def get_info(self) -> dict[str, Any]:
        """Get agent information."""
        return {
            "name": self.name,
            "description": self.config.description,
            "capabilities": [c.value for c in self.config.capabilities],
            "available_tools": len(self.tools.list_tools()),
            "status": self.status.value,
        }


class ReactAgent(AdvancedAgent):
    """
    Agent implementing the ReAct (Reasoning + Acting) pattern.

    The agent follows a think-act-observe loop:
    1. Think: Analyze the current state
    2. Act: Choose and execute a tool
    3. Observe: Process the result
    4. Repeat until task is complete
    """

    def __init__(
        self,
        config: AgentConfig,
        llm_client: Any = None,  # Type depends on LLM implementation
        **kwargs,
    ):
        super().__init__(config, **kwargs)
        self.llm = llm_client

    @abstractmethod
    async def think(self, state: dict[str, Any]) -> dict[str, Any]:
        """
        Analyze the current state and decide next action.

        Returns a dict with:
        - thought: reasoning about current state
        - action: next action to take (tool name or "finish")
        - action_input: parameters for the action
        """
        pass

    @abstractmethod
    async def observe(self, action_result: ToolResult, state: dict[str, Any]) -> dict[str, Any]:
        """
        Process the result of an action.

        Returns updated state.
        """
        pass

    async def _run(self, input_data: dict[str, Any]) -> AgentResult:
        """Execute the ReAct loop."""
        state = {"input": input_data, "observations": [], "complete": False}
        result = AgentResult(success=False, status=AgentStatus.RUNNING)

        while self._iteration < self.config.max_iterations and not state.get("complete"):
            self._iteration += 1
            result.iterations = self._iteration

            # Think
            thought = await self.think(state)
            self.add_assistant_message(f"Thought: {thought.get('thought', '')}")

            action = thought.get("action")
            action_input = thought.get("action_input", {})

            # Check if done
            if action == "finish":
                state["complete"] = True
                result.success = True
                result.status = AgentStatus.COMPLETED
                result.data = thought.get("output", {})
                break

            # Act
            if action:
                tool_result = await self.call_tool(action, **action_input)
                result.tool_calls += 1

                # Observe
                state = await self.observe(tool_result, state)
                state["observations"].append({
                    "action": action,
                    "result": tool_result.to_dict(),
                })

        if not state.get("complete"):
            result.status = AgentStatus.FAILED
            result.errors.append(f"Max iterations ({self.config.max_iterations}) reached")

        return result
