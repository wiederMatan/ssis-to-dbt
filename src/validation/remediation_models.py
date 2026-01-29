"""Pydantic models for remediation agent."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class DiscrepancyType(str, Enum):
    """Type of discrepancy detected."""
    ROW_COUNT_MISMATCH = "row_count_mismatch"
    PRIMARY_KEY_NULLS = "primary_key_nulls"
    PRIMARY_KEY_DUPLICATES = "primary_key_duplicates"
    CHECKSUM_VARIANCE = "checksum_variance"
    TYPE_MISMATCH = "type_mismatch"
    MISSING_FILTER = "missing_filter"
    JOIN_ISSUE = "join_issue"
    AGGREGATION_ERROR = "aggregation_error"
    UNKNOWN = "unknown"


class RemediationAction(str, Enum):
    """Type of remediation action to take."""
    ADD_FILTER = "add_filter"
    FIX_JOIN = "fix_join"
    ADD_COALESCE = "add_coalesce"
    ADD_DISTINCT = "add_distinct"
    FIX_TYPE_CAST = "fix_type_cast"
    FIX_AGGREGATION = "fix_aggregation"
    ADD_WHERE_CLAUSE = "add_where_clause"
    MODIFY_GROUP_BY = "modify_group_by"
    MANUAL_REVIEW = "manual_review"


class Discrepancy(BaseModel):
    """A detected discrepancy between legacy and dbt data."""
    model_name: str
    discrepancy_type: DiscrepancyType
    severity: str = "high"  # high, medium, low
    details: dict = Field(default_factory=dict)
    message: str

    # For row count issues
    legacy_count: Optional[int] = None
    dbt_count: Optional[int] = None
    difference_percent: Optional[float] = None

    # For checksum issues
    column: Optional[str] = None
    variance_percent: Optional[float] = None

    # For PK issues
    null_count: Optional[int] = None
    duplicate_count: Optional[int] = None


class RemediationStep(BaseModel):
    """A single step in the remediation plan."""
    step_number: int
    action: RemediationAction
    target_file: str
    description: str
    original_code: Optional[str] = None
    suggested_code: Optional[str] = None
    confidence: float = 0.0  # 0-1, how confident we are this will fix the issue
    applied: bool = False
    success: Optional[bool] = None


class RemediationPlan(BaseModel):
    """A plan to remediate discrepancies for a model."""
    model_name: str
    discrepancies: list[Discrepancy] = Field(default_factory=list)
    steps: list[RemediationStep] = Field(default_factory=list)
    diagnosis: str = ""
    estimated_success_probability: float = 0.0
    requires_manual_review: bool = False
    manual_review_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)


class RemediationAttempt(BaseModel):
    """Record of a single remediation attempt."""
    attempt_number: int
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None

    # Plans created for this attempt
    plans: list[RemediationPlan] = Field(default_factory=list)

    # Results after remediation
    models_fixed: int = 0
    models_still_failing: int = 0
    models_requiring_manual_review: int = 0

    # Validation results before and after
    failures_before: int = 0
    failures_after: int = 0

    success: bool = False
    notes: list[str] = Field(default_factory=list)


class RemediationResult(BaseModel):
    """Final result of the remediation process."""
    total_attempts: int = 0
    max_attempts: int = 3

    attempts: list[RemediationAttempt] = Field(default_factory=list)

    # Final state
    all_issues_resolved: bool = False
    remaining_failures: list[str] = Field(default_factory=list)

    # Models that need manual intervention
    manual_review_required: list[str] = Field(default_factory=list)
    manual_review_reasons: dict[str, str] = Field(default_factory=dict)

    # Summary
    initial_failures: int = 0
    final_failures: int = 0

    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    total_duration_seconds: Optional[float] = None

    final_message: str = ""

    def calculate_summary(self) -> None:
        """Calculate summary statistics."""
        if self.completed_at and self.started_at:
            self.total_duration_seconds = (self.completed_at - self.started_at).total_seconds()

        if self.attempts:
            self.initial_failures = self.attempts[0].failures_before
            self.final_failures = self.attempts[-1].failures_after

        self.all_issues_resolved = self.final_failures == 0 and len(self.manual_review_required) == 0
