"""Migration context and state management."""

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from pydantic import BaseModel, Field


class MigrationPhase(str, Enum):
    """Phases of the migration pipeline."""

    INITIALIZED = "initialized"
    ANALYZING = "analyzing"
    ANALYSIS_COMPLETE = "analysis_complete"
    BUILDING = "building"
    BUILD_COMPLETE = "build_complete"
    AWAITING_APPROVAL = "awaiting_approval"
    EXECUTING = "executing"
    EXECUTION_COMPLETE = "execution_complete"
    VALIDATING = "validating"
    VALIDATION_COMPLETE = "validation_complete"
    VALIDATION_FAILED = "validation_failed"
    DIAGNOSING = "diagnosing"
    COMPLETE = "complete"
    FAILED = "failed"


class ApprovalRequest(BaseModel):
    """A pending approval request."""

    action: str
    details: dict[str, Any]
    requested_at: datetime = Field(default_factory=datetime.now)


class MigrationContext(BaseModel):
    """Shared state passed between agents throughout the pipeline."""

    # Identification
    run_id: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S")
    )
    started_at: datetime = Field(default_factory=datetime.now)

    # Configuration
    input_dir: str
    output_dir: str
    dbt_project_path: str
    config_path: Optional[str] = None

    # Phase tracking
    current_phase: MigrationPhase = MigrationPhase.INITIALIZED
    phase_history: list[dict[str, Any]] = Field(default_factory=list)

    # Agent outputs (populated as pipeline progresses)
    analysis_result: Optional[dict[str, Any]] = None
    build_result: Optional[dict[str, Any]] = None
    execution_result: Optional[dict[str, Any]] = None
    validation_result: Optional[dict[str, Any]] = None
    diagnosis_result: Optional[dict[str, Any]] = None

    # Human approvals
    pending_approvals: list[ApprovalRequest] = Field(default_factory=list)
    approval_responses: dict[str, bool] = Field(default_factory=dict)

    # Feedback loop
    iteration_count: int = 0
    max_iterations: int = 3
    feedback_history: list[dict[str, Any]] = Field(default_factory=list)

    # Error tracking
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    class Config:
        use_enum_values = True

    def transition_to(
        self, phase: MigrationPhase, metadata: Optional[dict[str, Any]] = None
    ) -> None:
        """Record a phase transition."""
        self.phase_history.append(
            {
                "from_phase": self.current_phase,
                "to_phase": phase.value if isinstance(phase, MigrationPhase) else phase,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {},
            }
        )
        self.current_phase = phase

    def request_approval(self, action: str, details: dict[str, Any]) -> None:
        """Request human approval for an action."""
        self.pending_approvals.append(
            ApprovalRequest(action=action, details=details)
        )

    def grant_approval(self, action: str) -> None:
        """Grant approval for an action."""
        self.approval_responses[action] = True
        # Remove from pending
        self.pending_approvals = [
            req for req in self.pending_approvals if req.action != action
        ]

    def deny_approval(self, action: str) -> None:
        """Deny approval for an action."""
        self.approval_responses[action] = False
        self.pending_approvals = [
            req for req in self.pending_approvals if req.action != action
        ]

    def record_feedback(
        self, feedback_type: str, details: dict[str, Any]
    ) -> None:
        """Record feedback from validation failure for retry."""
        self.feedback_history.append(
            {
                "iteration": self.iteration_count,
                "type": feedback_type,
                "details": details,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def can_retry(self) -> bool:
        """Check if we can retry after a failure."""
        return self.iteration_count < self.max_iterations

    def increment_iteration(self) -> None:
        """Increment the iteration counter for retry."""
        self.iteration_count += 1

    def get_duration(self) -> float:
        """Get total duration in seconds."""
        return (datetime.now() - self.started_at).total_seconds()

    def to_summary(self) -> dict[str, Any]:
        """Generate a summary of the migration run."""
        return {
            "run_id": self.run_id,
            "started_at": self.started_at.isoformat(),
            "duration_seconds": self.get_duration(),
            "current_phase": self.current_phase,
            "iteration_count": self.iteration_count,
            "errors_count": len(self.errors),
            "warnings_count": len(self.warnings),
            "phase_transitions": len(self.phase_history),
        }


class StatePersistence:
    """Persist migration state for recovery and debugging."""

    def __init__(self, state_dir: Path):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def save_state(self, context: MigrationContext) -> Path:
        """Save current state to disk."""
        state_file = self.state_dir / f"migration_{context.run_id}.json"
        with open(state_file, "w") as f:
            json.dump(
                context.model_dump(mode="json"),
                f,
                indent=2,
                default=str,
            )
        return state_file

    def load_state(self, run_id: str) -> MigrationContext:
        """Load state from disk."""
        state_file = self.state_dir / f"migration_{run_id}.json"
        with open(state_file) as f:
            data = json.load(f)
        return MigrationContext(**data)

    def list_runs(self) -> list[str]:
        """List all migration runs."""
        return [
            f.stem.replace("migration_", "")
            for f in self.state_dir.glob("migration_*.json")
        ]

    def get_latest_run(self) -> Optional[str]:
        """Get the most recent run ID."""
        runs = sorted(self.list_runs(), reverse=True)
        return runs[0] if runs else None
