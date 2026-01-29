"""Pydantic models for validation results."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ValidationStatus(str, Enum):
    """Status of a validation check."""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"
    ERROR = "error"


class RowCountValidation(BaseModel):
    """Row count comparison between legacy and dbt."""
    legacy_table: str
    legacy_count: int
    dbt_model: str
    dbt_count: int
    difference: int
    difference_percent: float
    status: ValidationStatus
    message: Optional[str] = None


class PrimaryKeyValidation(BaseModel):
    """Primary key integrity check."""
    model: str
    pk_column: str
    null_count: int
    duplicate_count: int
    status: ValidationStatus
    message: Optional[str] = None


class ChecksumValidation(BaseModel):
    """Numeric column checksum comparison."""
    model: str
    column: str
    legacy_sum: Optional[float] = None
    dbt_sum: Optional[float] = None
    legacy_avg: Optional[float] = None
    dbt_avg: Optional[float] = None
    variance_percent: float
    status: ValidationStatus
    message: Optional[str] = None


class ModelValidation(BaseModel):
    """Complete validation result for a single model."""
    model_name: str
    ssis_package: str
    ssis_task: str
    legacy_table: Optional[str] = None

    row_count: Optional[RowCountValidation] = None
    primary_key: Optional[PrimaryKeyValidation] = None
    checksums: list[ChecksumValidation] = Field(default_factory=list)

    overall_status: ValidationStatus = ValidationStatus.SKIPPED
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None


class DbtRunResult(BaseModel):
    """Result of dbt command execution."""
    command: str
    exit_code: int
    success: bool
    stdout: str
    stderr: str
    duration_seconds: float
    models_run: int = 0
    models_success: int = 0
    models_error: int = 0
    models_skipped: int = 0


class ValidationReport(BaseModel):
    """Complete validation report."""
    generated_at: datetime = Field(default_factory=datetime.now)

    # dbt execution results
    dbt_deps: Optional[DbtRunResult] = None
    dbt_run: Optional[DbtRunResult] = None
    dbt_test: Optional[DbtRunResult] = None

    # Model validations
    model_validations: list[ModelValidation] = Field(default_factory=list)

    # Summary
    total_models: int = 0
    models_passed: int = 0
    models_failed: int = 0
    models_warning: int = 0
    models_skipped: int = 0

    overall_status: ValidationStatus = ValidationStatus.SKIPPED

    def calculate_summary(self) -> None:
        """Calculate summary statistics from model validations."""
        self.total_models = len(self.model_validations)
        self.models_passed = sum(1 for m in self.model_validations if m.overall_status == ValidationStatus.PASSED)
        self.models_failed = sum(1 for m in self.model_validations if m.overall_status == ValidationStatus.FAILED)
        self.models_warning = sum(1 for m in self.model_validations if m.overall_status == ValidationStatus.WARNING)
        self.models_skipped = sum(1 for m in self.model_validations if m.overall_status == ValidationStatus.SKIPPED)

        if self.models_failed > 0:
            self.overall_status = ValidationStatus.FAILED
        elif self.models_warning > 0:
            self.overall_status = ValidationStatus.WARNING
        elif self.models_passed > 0:
            self.overall_status = ValidationStatus.PASSED
        else:
            self.overall_status = ValidationStatus.SKIPPED
