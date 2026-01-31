"""
Graph-Based Workflow Orchestrator.

Implements a directed graph execution model inspired by LangGraph:
- Nodes represent agents or functions
- Edges define execution flow with conditions
- Supports parallel execution of independent nodes
- State management with checkpointing
"""

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine, Optional, Union
from collections import defaultdict


class NodeStatus(str, Enum):
    """Status of a graph node."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class EdgeCondition(str, Enum):
    """Pre-defined edge conditions."""

    ALWAYS = "always"
    ON_SUCCESS = "on_success"
    ON_FAILURE = "on_failure"
    CONDITIONAL = "conditional"


@dataclass
class GraphState:
    """State passed through the graph."""

    data: dict[str, Any] = field(default_factory=dict)
    node_results: dict[str, Any] = field(default_factory=dict)
    node_statuses: dict[str, NodeStatus] = field(default_factory=dict)
    execution_path: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from state data."""
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a value in state data."""
        self.data[key] = value

    def update(self, updates: dict[str, Any]) -> None:
        """Update state data with multiple values."""
        self.data.update(updates)

    def copy(self) -> "GraphState":
        """Create a copy of the state."""
        return GraphState(
            data=dict(self.data),
            node_results=dict(self.node_results),
            node_statuses=dict(self.node_statuses),
            execution_path=list(self.execution_path),
            errors=list(self.errors),
            metadata=dict(self.metadata),
        )


# Type for node functions
NodeFunction = Callable[[GraphState], Coroutine[Any, Any, dict[str, Any]]]
ConditionFunction = Callable[[GraphState], bool]


@dataclass
class GraphNode:
    """A node in the execution graph."""

    id: str
    name: str
    func: NodeFunction
    description: str = ""
    timeout_seconds: float = 300.0
    retry_count: int = 0
    retry_delay_seconds: float = 1.0
    required: bool = True  # If False, failure won't stop execution


@dataclass
class GraphEdge:
    """An edge connecting two nodes."""

    source: str
    target: str
    condition: EdgeCondition = EdgeCondition.ALWAYS
    condition_fn: Optional[ConditionFunction] = None
    priority: int = 0  # Higher priority edges are evaluated first


@dataclass
class ExecutionResult:
    """Result of graph execution."""

    success: bool
    final_state: GraphState
    execution_time_ms: float
    nodes_executed: int
    nodes_failed: int
    execution_order: list[str]


class WorkflowGraph:
    """
    Directed graph for workflow execution.

    Features:
    - Topological execution order
    - Parallel execution of independent nodes
    - Conditional branching
    - State checkpointing
    - Error handling and retries
    """

    def __init__(self, name: str = "workflow"):
        self.name = name
        self._nodes: dict[str, GraphNode] = {}
        self._edges: list[GraphEdge] = []
        self._start_node: Optional[str] = None
        self._end_nodes: set[str] = set()
        self._checkpoints: dict[str, GraphState] = {}

    def add_node(
        self,
        id: str,
        func: NodeFunction,
        name: Optional[str] = None,
        description: str = "",
        timeout_seconds: float = 300.0,
        retry_count: int = 0,
        required: bool = True,
    ) -> "WorkflowGraph":
        """Add a node to the graph."""
        self._nodes[id] = GraphNode(
            id=id,
            name=name or id,
            func=func,
            description=description,
            timeout_seconds=timeout_seconds,
            retry_count=retry_count,
            required=required,
        )
        return self

    def add_edge(
        self,
        source: str,
        target: str,
        condition: EdgeCondition = EdgeCondition.ALWAYS,
        condition_fn: Optional[ConditionFunction] = None,
        priority: int = 0,
    ) -> "WorkflowGraph":
        """Add an edge between nodes."""
        if source not in self._nodes:
            raise ValueError(f"Source node '{source}' not found")
        if target not in self._nodes:
            raise ValueError(f"Target node '{target}' not found")

        self._edges.append(GraphEdge(
            source=source,
            target=target,
            condition=condition,
            condition_fn=condition_fn,
            priority=priority,
        ))
        return self

    def set_entry_point(self, node_id: str) -> "WorkflowGraph":
        """Set the starting node."""
        if node_id not in self._nodes:
            raise ValueError(f"Node '{node_id}' not found")
        self._start_node = node_id
        return self

    def set_finish_point(self, node_id: str) -> "WorkflowGraph":
        """Mark a node as an end point."""
        if node_id not in self._nodes:
            raise ValueError(f"Node '{node_id}' not found")
        self._end_nodes.add(node_id)
        return self

    def _get_outgoing_edges(self, node_id: str) -> list[GraphEdge]:
        """Get all outgoing edges from a node."""
        edges = [e for e in self._edges if e.source == node_id]
        return sorted(edges, key=lambda e: -e.priority)  # Higher priority first

    def _get_incoming_edges(self, node_id: str) -> list[GraphEdge]:
        """Get all incoming edges to a node."""
        return [e for e in self._edges if e.target == node_id]

    def _evaluate_edge_condition(self, edge: GraphEdge, state: GraphState) -> bool:
        """Check if an edge condition is satisfied."""
        source_status = state.node_statuses.get(edge.source, NodeStatus.PENDING)

        if edge.condition == EdgeCondition.ALWAYS:
            return source_status == NodeStatus.COMPLETED

        if edge.condition == EdgeCondition.ON_SUCCESS:
            return source_status == NodeStatus.COMPLETED

        if edge.condition == EdgeCondition.ON_FAILURE:
            return source_status == NodeStatus.FAILED

        if edge.condition == EdgeCondition.CONDITIONAL:
            if edge.condition_fn:
                return edge.condition_fn(state)
            return True

        return False

    def _get_ready_nodes(self, state: GraphState) -> list[str]:
        """Get nodes that are ready to execute."""
        ready = []

        for node_id in self._nodes:
            # Skip already processed nodes
            if state.node_statuses.get(node_id) in [NodeStatus.COMPLETED, NodeStatus.FAILED, NodeStatus.SKIPPED]:
                continue

            # Skip running nodes
            if state.node_statuses.get(node_id) == NodeStatus.RUNNING:
                continue

            # Check if this is the start node
            if node_id == self._start_node:
                incoming = self._get_incoming_edges(node_id)
                if not incoming:
                    ready.append(node_id)
                    continue

            # Check if all incoming edges are satisfied
            incoming_edges = self._get_incoming_edges(node_id)
            if not incoming_edges:
                continue  # No incoming edges and not start node

            # At least one incoming edge must be satisfied
            for edge in incoming_edges:
                if self._evaluate_edge_condition(edge, state):
                    ready.append(node_id)
                    break

        return ready

    async def _execute_node(
        self,
        node: GraphNode,
        state: GraphState,
    ) -> tuple[bool, dict[str, Any]]:
        """Execute a single node with retries."""
        attempts = 0
        last_error = None

        while attempts <= node.retry_count:
            try:
                # Execute with timeout
                result = await asyncio.wait_for(
                    node.func(state.copy()),
                    timeout=node.timeout_seconds,
                )
                return True, result

            except asyncio.TimeoutError:
                last_error = f"Node '{node.id}' timed out after {node.timeout_seconds}s"
            except Exception as e:
                last_error = str(e)

            attempts += 1
            if attempts <= node.retry_count:
                await asyncio.sleep(node.retry_delay_seconds * attempts)

        return False, {"error": last_error}

    async def execute(
        self,
        initial_state: Optional[dict[str, Any]] = None,
        checkpoint_id: Optional[str] = None,
        max_parallel: int = 5,
    ) -> ExecutionResult:
        """
        Execute the workflow graph.

        Args:
            initial_state: Initial data for the state
            checkpoint_id: Resume from a checkpoint
            max_parallel: Maximum parallel node executions
        """
        start_time = time.time()

        # Initialize or load state
        if checkpoint_id and checkpoint_id in self._checkpoints:
            state = self._checkpoints[checkpoint_id].copy()
        else:
            state = GraphState(data=initial_state or {})

        if not self._start_node:
            raise ValueError("No entry point set")

        nodes_executed = 0
        nodes_failed = 0

        # Main execution loop
        while True:
            ready_nodes = self._get_ready_nodes(state)

            if not ready_nodes:
                # Check if we've reached an end node or are stuck
                break

            # Execute ready nodes in parallel (up to max_parallel)
            batch = ready_nodes[:max_parallel]
            tasks = []

            for node_id in batch:
                node = self._nodes[node_id]
                state.node_statuses[node_id] = NodeStatus.RUNNING
                tasks.append(self._execute_node(node, state))

            # Wait for batch to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for node_id, result in zip(batch, results):
                node = self._nodes[node_id]
                nodes_executed += 1

                if isinstance(result, Exception):
                    state.node_statuses[node_id] = NodeStatus.FAILED
                    state.errors.append(f"Node '{node_id}': {str(result)}")
                    nodes_failed += 1

                    if node.required:
                        # Required node failed - stop execution
                        return ExecutionResult(
                            success=False,
                            final_state=state,
                            execution_time_ms=(time.time() - start_time) * 1000,
                            nodes_executed=nodes_executed,
                            nodes_failed=nodes_failed,
                            execution_order=state.execution_path,
                        )
                else:
                    success, data = result
                    if success:
                        state.node_statuses[node_id] = NodeStatus.COMPLETED
                        state.node_results[node_id] = data
                        state.update(data)  # Merge node output into state
                        state.execution_path.append(node_id)
                    else:
                        state.node_statuses[node_id] = NodeStatus.FAILED
                        state.errors.append(f"Node '{node_id}': {data.get('error', 'Unknown error')}")
                        nodes_failed += 1

                        if node.required:
                            return ExecutionResult(
                                success=False,
                                final_state=state,
                                execution_time_ms=(time.time() - start_time) * 1000,
                                nodes_executed=nodes_executed,
                                nodes_failed=nodes_failed,
                                execution_order=state.execution_path,
                            )

        # Check if we reached an end node
        success = any(
            state.node_statuses.get(end_node) == NodeStatus.COMPLETED
            for end_node in self._end_nodes
        ) if self._end_nodes else nodes_failed == 0

        return ExecutionResult(
            success=success,
            final_state=state,
            execution_time_ms=(time.time() - start_time) * 1000,
            nodes_executed=nodes_executed,
            nodes_failed=nodes_failed,
            execution_order=state.execution_path,
        )

    def checkpoint(self, checkpoint_id: str, state: GraphState) -> None:
        """Save a checkpoint."""
        self._checkpoints[checkpoint_id] = state.copy()

    def get_checkpoint(self, checkpoint_id: str) -> Optional[GraphState]:
        """Get a checkpoint."""
        return self._checkpoints.get(checkpoint_id)

    def visualize(self) -> str:
        """Generate a text visualization of the graph."""
        lines = [f"Workflow: {self.name}", "=" * 40, ""]

        # Nodes
        lines.append("Nodes:")
        for node_id, node in self._nodes.items():
            marker = ""
            if node_id == self._start_node:
                marker = " [START]"
            if node_id in self._end_nodes:
                marker = " [END]"
            lines.append(f"  - {node_id}: {node.name}{marker}")

        lines.append("")

        # Edges
        lines.append("Edges:")
        for edge in self._edges:
            condition_str = edge.condition.value
            if edge.condition == EdgeCondition.CONDITIONAL:
                condition_str = "conditional"
            lines.append(f"  {edge.source} --[{condition_str}]--> {edge.target}")

        return "\n".join(lines)


class StateGraph(WorkflowGraph):
    """
    LangGraph-style state graph with typed state.

    Provides a more structured API for building workflows.
    """

    def __init__(self, name: str = "state_graph"):
        super().__init__(name)
        self._conditional_edges: dict[str, list[tuple[ConditionFunction, str]]] = defaultdict(list)

    def add_conditional_edges(
        self,
        source: str,
        conditions: dict[str, ConditionFunction],
        default: Optional[str] = None,
    ) -> "StateGraph":
        """
        Add conditional edges from a source node.

        Args:
            source: Source node ID
            conditions: Dict mapping target node IDs to condition functions
            default: Default target if no condition matches
        """
        for target, condition_fn in conditions.items():
            self.add_edge(
                source,
                target,
                condition=EdgeCondition.CONDITIONAL,
                condition_fn=condition_fn,
            )

        if default:
            self.add_edge(
                source,
                default,
                condition=EdgeCondition.ALWAYS,
                priority=-1,  # Lower priority than conditional edges
            )

        return self

    def compile(self) -> WorkflowGraph:
        """Compile the state graph (validate and return)."""
        # Validate graph structure
        if not self._start_node:
            raise ValueError("No entry point set")

        if not self._end_nodes:
            raise ValueError("No finish point set")

        # Check all nodes are reachable from start
        reachable = set()
        to_visit = [self._start_node]

        while to_visit:
            current = to_visit.pop()
            if current in reachable:
                continue
            reachable.add(current)

            for edge in self._get_outgoing_edges(current):
                if edge.target not in reachable:
                    to_visit.append(edge.target)

        unreachable = set(self._nodes.keys()) - reachable
        if unreachable:
            raise ValueError(f"Unreachable nodes: {unreachable}")

        return self


# Builder pattern for common workflow patterns

class WorkflowBuilder:
    """Builder for common workflow patterns."""

    @staticmethod
    def sequential(*node_funcs: tuple[str, NodeFunction]) -> WorkflowGraph:
        """Create a sequential workflow."""
        graph = WorkflowGraph("sequential")

        prev_id = None
        for i, (node_id, func) in enumerate(node_funcs):
            graph.add_node(node_id, func)

            if prev_id:
                graph.add_edge(prev_id, node_id)
            else:
                graph.set_entry_point(node_id)

            prev_id = node_id

        if prev_id:
            graph.set_finish_point(prev_id)

        return graph

    @staticmethod
    def parallel(*node_funcs: tuple[str, NodeFunction], join_node: Optional[tuple[str, NodeFunction]] = None) -> WorkflowGraph:
        """Create a parallel workflow with optional join."""
        graph = WorkflowGraph("parallel")

        # Add start node
        async def start_func(state: GraphState) -> dict[str, Any]:
            return {}

        graph.add_node("__start__", start_func)
        graph.set_entry_point("__start__")

        # Add parallel nodes
        for node_id, func in node_funcs:
            graph.add_node(node_id, func)
            graph.add_edge("__start__", node_id)

        # Add join node if specified
        if join_node:
            join_id, join_func = join_node
            graph.add_node(join_id, join_func)

            for node_id, _ in node_funcs:
                graph.add_edge(node_id, join_id)

            graph.set_finish_point(join_id)
        else:
            for node_id, _ in node_funcs:
                graph.set_finish_point(node_id)

        return graph
