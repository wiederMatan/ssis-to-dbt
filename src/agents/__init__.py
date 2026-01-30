"""Multi-agent system for SSIS-to-dbt migration."""

from .base import BaseAgent, AgentResult, AgentStatus, LoadPattern
from .context import MigrationContext, MigrationPhase, StatePersistence
from .analyzer import AnalyzerAgent
from .builder import BuilderAgent
from .executor import ExecutorAgent
from .validator import ValidatorAgent
from .diagnoser import DiagnoserAgent
from .orchestrator import MigrationOrchestrator, run_migration

__all__ = [
    # Base
    "BaseAgent",
    "AgentResult",
    "AgentStatus",
    "LoadPattern",
    # Context
    "MigrationContext",
    "MigrationPhase",
    "StatePersistence",
    # Agents
    "AnalyzerAgent",
    "BuilderAgent",
    "ExecutorAgent",
    "ValidatorAgent",
    "DiagnoserAgent",
    # Orchestrator
    "MigrationOrchestrator",
    "run_migration",
]
