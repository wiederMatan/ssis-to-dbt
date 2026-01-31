"""
Advanced Memory Management System for Agents.

Implements multiple memory types inspired by LangGraph and cognitive architectures:
- Short-term Memory: Thread-scoped conversation context
- Long-term Memory: Persistent cross-session storage
- Semantic Memory: Facts and knowledge
- Episodic Memory: Past experiences and interactions
- Procedural Memory: Learned procedures and patterns
"""

import json
import hashlib
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar
from collections import deque
import threading


class MemoryType(str, Enum):
    """Types of memory storage."""

    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    SEMANTIC = "semantic"
    EPISODIC = "episodic"
    PROCEDURAL = "procedural"


class MemoryPriority(str, Enum):
    """Priority levels for memory entries."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MemoryEntry:
    """A single memory entry."""

    id: str
    content: Any
    memory_type: MemoryType
    timestamp: float = field(default_factory=time.time)
    priority: MemoryPriority = MemoryPriority.MEDIUM
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: Optional[list[float]] = None
    ttl_seconds: Optional[float] = None
    access_count: int = 0
    last_accessed: Optional[float] = None
    tags: list[str] = field(default_factory=list)

    def is_expired(self) -> bool:
        """Check if memory has expired."""
        if self.ttl_seconds is None:
            return False
        return time.time() > (self.timestamp + self.ttl_seconds)

    def touch(self) -> None:
        """Update access tracking."""
        self.access_count += 1
        self.last_accessed = time.time()

    @property
    def age_seconds(self) -> float:
        """Get age of memory in seconds."""
        return time.time() - self.timestamp

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "timestamp": self.timestamp,
            "priority": self.priority.value,
            "metadata": self.metadata,
            "ttl_seconds": self.ttl_seconds,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryEntry":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            content=data["content"],
            memory_type=MemoryType(data["memory_type"]),
            timestamp=data.get("timestamp", time.time()),
            priority=MemoryPriority(data.get("priority", "medium")),
            metadata=data.get("metadata", {}),
            ttl_seconds=data.get("ttl_seconds"),
            access_count=data.get("access_count", 0),
            last_accessed=data.get("last_accessed"),
            tags=data.get("tags", []),
        )


class MemoryStore(ABC):
    """Abstract base class for memory stores."""

    @abstractmethod
    async def store(self, entry: MemoryEntry) -> None:
        """Store a memory entry."""
        pass

    @abstractmethod
    async def retrieve(self, id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory entry by ID."""
        pass

    @abstractmethod
    async def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[MemoryEntry]:
        """Search for memory entries."""
        pass

    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Delete a memory entry."""
        pass

    @abstractmethod
    async def clear(self) -> int:
        """Clear all entries, return count deleted."""
        pass


class ShortTermMemory(MemoryStore):
    """
    Short-term memory for conversation context.

    Uses a sliding window approach with configurable capacity.
    Memories automatically expire after TTL.
    """

    def __init__(
        self,
        capacity: int = 100,
        default_ttl_seconds: float = 3600,  # 1 hour
    ):
        self._capacity = capacity
        self._default_ttl = default_ttl_seconds
        self._entries: deque[MemoryEntry] = deque(maxlen=capacity)
        self._index: dict[str, MemoryEntry] = {}
        self._lock = threading.Lock()

    async def store(self, entry: MemoryEntry) -> None:
        """Store a memory entry."""
        with self._lock:
            if entry.ttl_seconds is None:
                entry.ttl_seconds = self._default_ttl

            # Remove old entry if exists
            if entry.id in self._index:
                self._entries = deque(
                    [e for e in self._entries if e.id != entry.id],
                    maxlen=self._capacity,
                )

            self._entries.append(entry)
            self._index[entry.id] = entry

    async def retrieve(self, id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory entry."""
        entry = self._index.get(id)
        if entry and not entry.is_expired():
            entry.touch()
            return entry
        return None

    async def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[MemoryEntry]:
        """Search for memory entries."""
        results = []
        query_lower = query.lower()

        for entry in reversed(self._entries):
            if entry.is_expired():
                continue

            # Simple text matching
            content_str = str(entry.content).lower()
            if query_lower in content_str:
                entry.touch()
                results.append(entry)

            if len(results) >= limit:
                break

        return results

    async def delete(self, id: str) -> bool:
        """Delete a memory entry."""
        with self._lock:
            if id in self._index:
                self._entries = deque(
                    [e for e in self._entries if e.id != id],
                    maxlen=self._capacity,
                )
                del self._index[id]
                return True
        return False

    async def clear(self) -> int:
        """Clear all entries."""
        with self._lock:
            count = len(self._entries)
            self._entries.clear()
            self._index.clear()
            return count

    async def get_recent(self, limit: int = 10) -> list[MemoryEntry]:
        """Get most recent non-expired entries."""
        results = []
        for entry in reversed(self._entries):
            if not entry.is_expired():
                results.append(entry)
            if len(results) >= limit:
                break
        return results

    async def prune_expired(self) -> int:
        """Remove expired entries."""
        with self._lock:
            before = len(self._entries)
            self._entries = deque(
                [e for e in self._entries if not e.is_expired()],
                maxlen=self._capacity,
            )
            self._index = {e.id: e for e in self._entries}
            return before - len(self._entries)


class LongTermMemory(MemoryStore):
    """
    Long-term memory with persistent storage.

    Stores memories to disk as JSON with optional compression.
    Supports cross-session persistence.
    """

    def __init__(
        self,
        storage_path: Path,
        max_entries: int = 10000,
    ):
        self._storage_path = Path(storage_path)
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._max_entries = max_entries
        self._index_path = self._storage_path / "index.json"
        self._index: dict[str, dict[str, Any]] = {}
        self._load_index()

    def _load_index(self) -> None:
        """Load index from disk."""
        if self._index_path.exists():
            with open(self._index_path) as f:
                self._index = json.load(f)

    def _save_index(self) -> None:
        """Save index to disk."""
        with open(self._index_path, "w") as f:
            json.dump(self._index, f, indent=2)

    def _get_entry_path(self, id: str) -> Path:
        """Get file path for an entry."""
        # Use hash-based subdirectories for large-scale storage
        hash_prefix = hashlib.md5(id.encode()).hexdigest()[:4]
        subdir = self._storage_path / hash_prefix
        subdir.mkdir(exist_ok=True)
        return subdir / f"{id}.json"

    async def store(self, entry: MemoryEntry) -> None:
        """Store a memory entry to disk."""
        entry_path = self._get_entry_path(entry.id)

        with open(entry_path, "w") as f:
            json.dump(entry.to_dict(), f, indent=2, default=str)

        # Update index
        self._index[entry.id] = {
            "path": str(entry_path),
            "timestamp": entry.timestamp,
            "tags": entry.tags,
            "priority": entry.priority.value,
        }
        self._save_index()

    async def retrieve(self, id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory entry from disk."""
        if id not in self._index:
            return None

        entry_path = Path(self._index[id]["path"])
        if not entry_path.exists():
            return None

        with open(entry_path) as f:
            data = json.load(f)

        entry = MemoryEntry.from_dict(data)
        entry.touch()

        # Update on disk
        await self.store(entry)

        return entry

    async def search(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[MemoryEntry]:
        """Search for memory entries."""
        results = []
        query_lower = query.lower()

        # Sort by timestamp (most recent first)
        sorted_ids = sorted(
            self._index.keys(),
            key=lambda x: self._index[x]["timestamp"],
            reverse=True,
        )

        for id in sorted_ids:
            if len(results) >= limit:
                break

            # Apply tag filter if specified
            if filters and "tags" in filters:
                entry_tags = set(self._index[id].get("tags", []))
                filter_tags = set(filters["tags"])
                if not filter_tags.intersection(entry_tags):
                    continue

            entry = await self.retrieve(id)
            if entry:
                content_str = str(entry.content).lower()
                if query_lower in content_str:
                    results.append(entry)

        return results

    async def delete(self, id: str) -> bool:
        """Delete a memory entry."""
        if id not in self._index:
            return False

        entry_path = Path(self._index[id]["path"])
        if entry_path.exists():
            entry_path.unlink()

        del self._index[id]
        self._save_index()
        return True

    async def clear(self) -> int:
        """Clear all entries."""
        count = len(self._index)

        for id in list(self._index.keys()):
            await self.delete(id)

        return count

    async def get_by_tags(self, tags: list[str], limit: int = 100) -> list[MemoryEntry]:
        """Get entries by tags."""
        return await self.search("", limit=limit, filters={"tags": tags})


class SemanticMemory(LongTermMemory):
    """
    Semantic memory for facts and knowledge.

    Optimized for storing and retrieving factual information
    with optional embedding-based similarity search.
    """

    def __init__(
        self,
        storage_path: Path,
        embedding_fn: Optional[Callable[[str], list[float]]] = None,
    ):
        super().__init__(storage_path / "semantic")
        self._embedding_fn = embedding_fn

    async def store_fact(
        self,
        fact_id: str,
        fact: str,
        source: Optional[str] = None,
        confidence: float = 1.0,
    ) -> None:
        """Store a fact."""
        entry = MemoryEntry(
            id=f"fact_{fact_id}",
            content=fact,
            memory_type=MemoryType.SEMANTIC,
            metadata={
                "source": source,
                "confidence": confidence,
                "fact_type": "general",
            },
            tags=["fact"],
        )

        # Generate embedding if available
        if self._embedding_fn:
            entry.embedding = self._embedding_fn(fact)

        await self.store(entry)

    async def get_facts(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get relevant facts."""
        entries = await self.search(query, limit=limit, filters={"tags": ["fact"]})
        return [
            {
                "fact": e.content,
                "source": e.metadata.get("source"),
                "confidence": e.metadata.get("confidence", 1.0),
            }
            for e in entries
        ]


class EpisodicMemory(LongTermMemory):
    """
    Episodic memory for past experiences and interactions.

    Stores sequences of events with temporal relationships.
    Useful for learning from past successes and failures.
    """

    def __init__(self, storage_path: Path):
        super().__init__(storage_path / "episodic")
        self._current_episode: Optional[str] = None
        self._episode_events: list[dict[str, Any]] = []

    async def start_episode(self, episode_id: str, context: dict[str, Any]) -> None:
        """Start a new episode."""
        self._current_episode = episode_id
        self._episode_events = []

        entry = MemoryEntry(
            id=f"episode_{episode_id}",
            content={
                "status": "in_progress",
                "context": context,
                "events": [],
            },
            memory_type=MemoryType.EPISODIC,
            tags=["episode", "in_progress"],
        )
        await self.store(entry)

    async def record_event(
        self,
        event_type: str,
        data: dict[str, Any],
        outcome: Optional[str] = None,
    ) -> None:
        """Record an event in the current episode."""
        if not self._current_episode:
            return

        event = {
            "type": event_type,
            "data": data,
            "outcome": outcome,
            "timestamp": time.time(),
        }
        self._episode_events.append(event)

    async def end_episode(
        self,
        success: bool,
        summary: str,
        learnings: Optional[list[str]] = None,
    ) -> None:
        """End the current episode."""
        if not self._current_episode:
            return

        entry = await self.retrieve(f"episode_{self._current_episode}")
        if entry:
            entry.content = {
                "status": "completed",
                "context": entry.content.get("context", {}),
                "events": self._episode_events,
                "success": success,
                "summary": summary,
                "learnings": learnings or [],
            }
            entry.tags = ["episode", "completed", "success" if success else "failure"]
            await self.store(entry)

        self._current_episode = None
        self._episode_events = []

    async def get_similar_episodes(
        self,
        context: dict[str, Any],
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Find similar past episodes."""
        context_str = json.dumps(context)
        entries = await self.search(context_str, limit=limit, filters={"tags": ["episode", "completed"]})

        return [
            {
                "episode_id": e.id,
                "context": e.content.get("context"),
                "success": e.content.get("success"),
                "summary": e.content.get("summary"),
                "learnings": e.content.get("learnings", []),
            }
            for e in entries
        ]


class ProceduralMemory(LongTermMemory):
    """
    Procedural memory for learned procedures and patterns.

    Stores reusable patterns, templates, and procedures
    that agents can apply to similar situations.
    """

    def __init__(self, storage_path: Path):
        super().__init__(storage_path / "procedural")

    async def store_procedure(
        self,
        procedure_id: str,
        name: str,
        description: str,
        steps: list[dict[str, Any]],
        trigger_conditions: list[str],
        success_rate: float = 0.0,
        usage_count: int = 0,
    ) -> None:
        """Store a procedure."""
        entry = MemoryEntry(
            id=f"proc_{procedure_id}",
            content={
                "name": name,
                "description": description,
                "steps": steps,
                "trigger_conditions": trigger_conditions,
                "success_rate": success_rate,
                "usage_count": usage_count,
            },
            memory_type=MemoryType.PROCEDURAL,
            tags=["procedure"] + trigger_conditions,
        )
        await self.store(entry)

    async def get_applicable_procedures(
        self,
        situation: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Find procedures applicable to a situation."""
        entries = await self.search(situation, limit=limit, filters={"tags": ["procedure"]})

        return [
            {
                "procedure_id": e.id,
                "name": e.content.get("name"),
                "description": e.content.get("description"),
                "steps": e.content.get("steps", []),
                "success_rate": e.content.get("success_rate", 0.0),
            }
            for e in entries
        ]

    async def record_procedure_outcome(
        self,
        procedure_id: str,
        success: bool,
    ) -> None:
        """Record the outcome of using a procedure."""
        entry = await self.retrieve(f"proc_{procedure_id}")
        if not entry:
            return

        usage_count = entry.content.get("usage_count", 0) + 1
        success_count = entry.content.get("success_rate", 0) * (usage_count - 1)
        if success:
            success_count += 1

        entry.content["usage_count"] = usage_count
        entry.content["success_rate"] = success_count / usage_count

        await self.store(entry)


class MemoryManager:
    """
    Central memory management system.

    Coordinates all memory types and provides unified access.
    Implements memory consolidation and garbage collection.
    """

    def __init__(
        self,
        storage_path: Path,
        short_term_capacity: int = 100,
        short_term_ttl: float = 3600,
        embedding_fn: Optional[Callable[[str], list[float]]] = None,
    ):
        self._storage_path = Path(storage_path) / "memory"
        self._storage_path.mkdir(parents=True, exist_ok=True)

        # Initialize memory stores
        self.short_term = ShortTermMemory(
            capacity=short_term_capacity,
            default_ttl_seconds=short_term_ttl,
        )
        self.long_term = LongTermMemory(self._storage_path / "long_term")
        self.semantic = SemanticMemory(self._storage_path, embedding_fn=embedding_fn)
        self.episodic = EpisodicMemory(self._storage_path)
        self.procedural = ProceduralMemory(self._storage_path)

        self._stores: dict[MemoryType, MemoryStore] = {
            MemoryType.SHORT_TERM: self.short_term,
            MemoryType.LONG_TERM: self.long_term,
            MemoryType.SEMANTIC: self.semantic,
            MemoryType.EPISODIC: self.episodic,
            MemoryType.PROCEDURAL: self.procedural,
        }

    async def store(
        self,
        content: Any,
        memory_type: MemoryType,
        id: Optional[str] = None,
        priority: MemoryPriority = MemoryPriority.MEDIUM,
        tags: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
        ttl_seconds: Optional[float] = None,
    ) -> str:
        """Store content in the specified memory type."""
        entry_id = id or f"{memory_type.value}_{int(time.time() * 1000)}"

        entry = MemoryEntry(
            id=entry_id,
            content=content,
            memory_type=memory_type,
            priority=priority,
            tags=tags or [],
            metadata=metadata or {},
            ttl_seconds=ttl_seconds,
        )

        store = self._stores[memory_type]
        await store.store(entry)

        return entry_id

    async def retrieve(
        self,
        id: str,
        memory_type: Optional[MemoryType] = None,
    ) -> Optional[MemoryEntry]:
        """Retrieve a memory entry."""
        if memory_type:
            return await self._stores[memory_type].retrieve(id)

        # Search all stores
        for store in self._stores.values():
            entry = await store.retrieve(id)
            if entry:
                return entry

        return None

    async def search(
        self,
        query: str,
        memory_types: Optional[list[MemoryType]] = None,
        limit: int = 10,
        filters: Optional[dict[str, Any]] = None,
    ) -> list[MemoryEntry]:
        """Search across memory stores."""
        types_to_search = memory_types or list(MemoryType)
        all_results = []

        for mem_type in types_to_search:
            store = self._stores[mem_type]
            results = await store.search(query, limit=limit, filters=filters)
            all_results.extend(results)

        # Sort by relevance (most recent and highest priority first)
        all_results.sort(
            key=lambda x: (x.priority.value, x.timestamp),
            reverse=True,
        )

        return all_results[:limit]

    async def consolidate(self) -> dict[str, int]:
        """
        Consolidate memory - move important short-term memories to long-term.

        Returns count of consolidated entries.
        """
        consolidated = 0

        # Get high-priority short-term memories
        recent = await self.short_term.get_recent(limit=50)

        for entry in recent:
            if entry.priority in [MemoryPriority.HIGH, MemoryPriority.CRITICAL]:
                # Move to long-term
                entry.memory_type = MemoryType.LONG_TERM
                await self.long_term.store(entry)
                await self.short_term.delete(entry.id)
                consolidated += 1

        # Prune expired short-term memories
        pruned = await self.short_term.prune_expired()

        return {
            "consolidated": consolidated,
            "pruned": pruned,
        }

    async def get_context(
        self,
        query: str,
        max_tokens: int = 4000,
    ) -> str:
        """
        Build a context string from relevant memories.

        Useful for providing context to LLM calls.
        """
        memories = await self.search(query, limit=20)

        context_parts = []
        total_length = 0

        for mem in memories:
            content_str = str(mem.content)
            if total_length + len(content_str) > max_tokens * 4:  # Rough token estimate
                break

            context_parts.append(f"[{mem.memory_type.value}] {content_str}")
            total_length += len(content_str)

        return "\n\n".join(context_parts)

    async def get_stats(self) -> dict[str, Any]:
        """Get memory statistics."""
        return {
            "short_term_count": len(self.short_term._entries),
            "long_term_count": len(self.long_term._index),
            "semantic_count": len(self.semantic._index),
            "episodic_count": len(self.episodic._index),
            "procedural_count": len(self.procedural._index),
            "storage_path": str(self._storage_path),
        }
