"""
Advanced Tool Registry with dynamic discovery and ReAct pattern support.

Inspired by Claude Agent SDK and LangChain tool patterns.
"""

import asyncio
import inspect
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional, TypeVar, Union, get_type_hints
from pydantic import BaseModel, Field


class ToolCategory(str, Enum):
    """Categories for tool organization."""

    DATABASE = "database"
    FILE_SYSTEM = "file_system"
    LLM = "llm"
    VALIDATION = "validation"
    TRANSFORMATION = "transformation"
    EXTERNAL_API = "external_api"
    SYSTEM = "system"


class ToolPermission(str, Enum):
    """Permission levels for tool execution."""

    READ_ONLY = "read_only"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"


@dataclass
class ToolParameter:
    """Definition of a tool parameter."""

    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None
    enum_values: Optional[list[str]] = None


@dataclass
class ToolResult:
    """Result from tool execution."""

    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "metadata": self.metadata,
        }


class Tool(ABC):
    """
    Base class for all tools.

    Implements the ReAct pattern: Reasoning + Acting in an interleaved manner.
    Each tool can be dynamically discovered and invoked by agents.
    """

    name: str
    description: str
    category: ToolCategory = ToolCategory.SYSTEM
    permission: ToolPermission = ToolPermission.READ_ONLY
    parameters: list[ToolParameter] = field(default_factory=list)
    requires_approval: bool = False
    timeout_seconds: float = 30.0
    retry_count: int = 0

    def __init__(self):
        self._execution_count = 0
        self._total_execution_time = 0.0
        self._last_error: Optional[str] = None

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        pass

    def validate_parameters(self, **kwargs) -> tuple[bool, Optional[str]]:
        """Validate input parameters against schema."""
        for param in self.parameters:
            if param.required and param.name not in kwargs:
                return False, f"Missing required parameter: {param.name}"

            if param.name in kwargs and param.enum_values:
                if kwargs[param.name] not in param.enum_values:
                    return False, f"Invalid value for {param.name}: must be one of {param.enum_values}"

        return True, None

    def get_schema(self) -> dict[str, Any]:
        """Get JSON Schema representation for LLM tool calling."""
        properties = {}
        required = []

        for param in self.parameters:
            prop = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum_values:
                prop["enum"] = param.enum_values
            if param.default is not None:
                prop["default"] = param.default

            properties[param.name] = prop
            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }

    async def safe_execute(self, **kwargs) -> ToolResult:
        """Execute with timeout, validation, and error handling."""
        # Validate parameters
        valid, error = self.validate_parameters(**kwargs)
        if not valid:
            return ToolResult(success=False, error=error)

        start_time = time.time()

        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                self.execute(**kwargs),
                timeout=self.timeout_seconds
            )

            execution_time = (time.time() - start_time) * 1000
            result.execution_time_ms = execution_time

            # Update stats
            self._execution_count += 1
            self._total_execution_time += execution_time

            return result

        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                error=f"Tool execution timed out after {self.timeout_seconds}s",
                execution_time_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            self._last_error = str(e)
            return ToolResult(
                success=False,
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000,
            )

    @property
    def stats(self) -> dict[str, Any]:
        """Get execution statistics."""
        return {
            "execution_count": self._execution_count,
            "total_execution_time_ms": self._total_execution_time,
            "avg_execution_time_ms": (
                self._total_execution_time / self._execution_count
                if self._execution_count > 0 else 0
            ),
            "last_error": self._last_error,
        }


class FunctionTool(Tool):
    """Tool wrapper for regular async functions."""

    def __init__(
        self,
        func: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None,
        category: ToolCategory = ToolCategory.SYSTEM,
        permission: ToolPermission = ToolPermission.READ_ONLY,
        requires_approval: bool = False,
    ):
        super().__init__()
        self._func = func
        self.name = name or func.__name__
        self.description = description or func.__doc__ or ""
        self.category = category
        self.permission = permission
        self.requires_approval = requires_approval
        self.parameters = self._extract_parameters(func)

    def _extract_parameters(self, func: Callable) -> list[ToolParameter]:
        """Extract parameters from function signature."""
        params = []
        sig = inspect.signature(func)
        hints = get_type_hints(func) if hasattr(func, "__annotations__") else {}

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue

            param_type = hints.get(param_name, Any)
            type_str = self._type_to_string(param_type)

            params.append(ToolParameter(
                name=param_name,
                type=type_str,
                description=f"Parameter {param_name}",
                required=param.default == inspect.Parameter.empty,
                default=None if param.default == inspect.Parameter.empty else param.default,
            ))

        return params

    def _type_to_string(self, t: type) -> str:
        """Convert Python type to JSON Schema type string."""
        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
        }
        return type_map.get(t, "string")

    async def execute(self, **kwargs) -> ToolResult:
        """Execute the wrapped function."""
        try:
            if asyncio.iscoroutinefunction(self._func):
                result = await self._func(**kwargs)
            else:
                result = self._func(**kwargs)

            return ToolResult(success=True, data=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))


def tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    category: ToolCategory = ToolCategory.SYSTEM,
    permission: ToolPermission = ToolPermission.READ_ONLY,
    requires_approval: bool = False,
):
    """Decorator to convert a function into a Tool."""
    def decorator(func: Callable) -> FunctionTool:
        return FunctionTool(
            func=func,
            name=name,
            description=description,
            category=category,
            permission=permission,
            requires_approval=requires_approval,
        )
    return decorator


class ToolRegistry:
    """
    Central registry for tool management with dynamic discovery.

    Features:
    - Dynamic tool registration and discovery
    - Category-based organization
    - Permission checking
    - Usage tracking and analytics
    - Tool schema generation for LLM
    """

    def __init__(self):
        self._tools: dict[str, Tool] = {}
        self._categories: dict[ToolCategory, list[str]] = {cat: [] for cat in ToolCategory}
        self._execution_history: list[dict[str, Any]] = []
        self._max_history = 1000

    def register(self, tool: Tool) -> None:
        """Register a tool."""
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")

        self._tools[tool.name] = tool
        self._categories[tool.category].append(tool.name)

    def register_function(
        self,
        func: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None,
        category: ToolCategory = ToolCategory.SYSTEM,
        permission: ToolPermission = ToolPermission.READ_ONLY,
        requires_approval: bool = False,
    ) -> None:
        """Register a function as a tool."""
        tool = FunctionTool(
            func=func,
            name=name,
            description=description,
            category=category,
            permission=permission,
            requires_approval=requires_approval,
        )
        self.register(tool)

    def unregister(self, name: str) -> None:
        """Unregister a tool."""
        if name in self._tools:
            tool = self._tools[name]
            self._categories[tool.category].remove(name)
            del self._tools[name]

    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_tools(
        self,
        category: Optional[ToolCategory] = None,
        permission: Optional[ToolPermission] = None,
    ) -> list[Tool]:
        """List tools with optional filtering."""
        tools = list(self._tools.values())

        if category:
            tools = [t for t in tools if t.category == category]

        if permission:
            tools = [t for t in tools if t.permission == permission]

        return tools

    def get_schemas(
        self,
        tool_names: Optional[list[str]] = None,
        category: Optional[ToolCategory] = None,
    ) -> list[dict[str, Any]]:
        """Get JSON schemas for tools (for LLM tool calling)."""
        if tool_names:
            tools = [self._tools[name] for name in tool_names if name in self._tools]
        elif category:
            tools = [self._tools[name] for name in self._categories[category]]
        else:
            tools = list(self._tools.values())

        return [tool.get_schema() for tool in tools]

    async def execute(
        self,
        tool_name: str,
        agent_id: str,
        **kwargs,
    ) -> ToolResult:
        """Execute a tool and record history."""
        tool = self._tools.get(tool_name)
        if not tool:
            return ToolResult(success=False, error=f"Tool '{tool_name}' not found")

        start_time = time.time()
        result = await tool.safe_execute(**kwargs)

        # Record execution
        self._record_execution(
            tool_name=tool_name,
            agent_id=agent_id,
            parameters=kwargs,
            result=result,
            start_time=start_time,
        )

        return result

    def _record_execution(
        self,
        tool_name: str,
        agent_id: str,
        parameters: dict[str, Any],
        result: ToolResult,
        start_time: float,
    ) -> None:
        """Record tool execution for analytics."""
        record = {
            "tool_name": tool_name,
            "agent_id": agent_id,
            "parameters": parameters,
            "success": result.success,
            "error": result.error,
            "execution_time_ms": result.execution_time_ms,
            "timestamp": start_time,
        }

        self._execution_history.append(record)

        # Trim history if needed
        if len(self._execution_history) > self._max_history:
            self._execution_history = self._execution_history[-self._max_history:]

    def get_analytics(self) -> dict[str, Any]:
        """Get tool usage analytics."""
        if not self._execution_history:
            return {"total_executions": 0}

        tool_stats = {}
        for record in self._execution_history:
            name = record["tool_name"]
            if name not in tool_stats:
                tool_stats[name] = {
                    "executions": 0,
                    "successes": 0,
                    "failures": 0,
                    "total_time_ms": 0,
                }

            tool_stats[name]["executions"] += 1
            if record["success"]:
                tool_stats[name]["successes"] += 1
            else:
                tool_stats[name]["failures"] += 1
            tool_stats[name]["total_time_ms"] += record["execution_time_ms"]

        return {
            "total_executions": len(self._execution_history),
            "unique_tools_used": len(tool_stats),
            "tool_stats": tool_stats,
        }

    def discover_tools(self, module) -> int:
        """Auto-discover and register tools from a module."""
        count = 0
        for name in dir(module):
            obj = getattr(module, name)
            if isinstance(obj, Tool):
                try:
                    self.register(obj)
                    count += 1
                except ValueError:
                    pass  # Already registered
        return count

    def get_tool_description(self) -> str:
        """Generate a human-readable description of all tools."""
        lines = ["# Available Tools\n"]

        for category in ToolCategory:
            tools = self.list_tools(category=category)
            if not tools:
                continue

            lines.append(f"\n## {category.value.replace('_', ' ').title()}\n")

            for tool in tools:
                lines.append(f"### {tool.name}")
                lines.append(f"{tool.description}\n")

                if tool.parameters:
                    lines.append("**Parameters:**")
                    for param in tool.parameters:
                        req = "(required)" if param.required else "(optional)"
                        lines.append(f"- `{param.name}` ({param.type}) {req}: {param.description}")
                    lines.append("")

        return "\n".join(lines)


# Global registry instance
_global_registry: Optional[ToolRegistry] = None


def get_global_registry() -> ToolRegistry:
    """Get or create the global tool registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry
