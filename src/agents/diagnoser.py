"""Diagnoser Agent - Analyzes validation failures and suggests fixes."""

import re
from typing import Any, Optional

from .base import BaseAgent, AgentResult, AgentStatus
from .context import MigrationContext
from .validator import ValidationStatus

# Import SQL identifier validation
from src.parser.utils import validate_sql_identifier, sanitize_sql_identifier


def safe_identifier(name: str) -> str:
    """
    Safely format an identifier for use in investigation queries.

    Args:
        name: The identifier to format

    Returns:
        Sanitized identifier or a placeholder if invalid
    """
    if not name:
        return "[INVALID]"

    # Try to sanitize the identifier
    sanitized = sanitize_sql_identifier(name)

    # Validate the result
    if validate_sql_identifier(sanitized):
        return f"[{sanitized}]"

    # If still invalid, return a safe placeholder
    return "[INVALID_IDENTIFIER]"


class DiagnosisResult:
    """Result of failure diagnosis."""

    def __init__(self):
        self.root_cause: str = ""
        self.category: str = ""
        self.confidence: float = 0.0
        self.suggested_fixes: list[dict[str, Any]] = []
        self.requires_manual_review: bool = False
        self.can_auto_fix: bool = False
        self.investigation_queries: list[str] = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "root_cause": self.root_cause,
            "category": self.category,
            "confidence": self.confidence,
            "suggested_fixes": self.suggested_fixes,
            "requires_manual_review": self.requires_manual_review,
            "can_auto_fix": self.can_auto_fix,
            "investigation_queries": self.investigation_queries,
        }


class DiagnoserAgent(BaseAgent):
    """
    Diagnoses validation failures and suggests remediation.

    Responsibilities:
    - Analyze validation failures
    - Identify root causes
    - Suggest fixes
    - Determine if retry is possible
    """

    def __init__(
        self,
        context: MigrationContext,
        llm_client: Optional[Any] = None,
    ):
        super().__init__(context)
        self.llm_client = llm_client

    async def execute(self, input_data: dict[str, Any]) -> AgentResult:
        """
        Diagnose validation failures.

        Args:
            input_data: Must contain "validation_report" from ValidatorAgent

        Returns:
            AgentResult with diagnosis and recommendations
        """
        self.status = AgentStatus.RUNNING
        self.log("Starting failure diagnosis")

        try:
            validation_report = input_data.get("validation_report", {})
            model_mappings = input_data.get("model_mappings", {})

            if not validation_report:
                return AgentResult(
                    success=False,
                    status=AgentStatus.FAILED,
                    errors=["No validation report provided"],
                )

            models = validation_report.get("models", [])
            failed_models = [
                m for m in models
                if m.get("overall_status") in [
                    ValidationStatus.FAILED.value,
                    "failed",
                ]
            ]

            if not failed_models:
                self.log("No failures to diagnose")
                return AgentResult(
                    success=True,
                    status=AgentStatus.COMPLETED,
                    data={
                        "has_failures": False,
                        "can_retry": False,
                        "diagnoses": [],
                    },
                )

            diagnoses = []
            overall_can_retry = True
            overall_requires_manual = False

            for model in failed_models:
                model_name = model.get("model_name", "unknown")
                self.log(f"Diagnosing: {model_name}")

                mapping = model_mappings.get(model_name, {})
                diagnosis = await self._diagnose_model_failure(model, mapping)
                diagnoses.append({
                    "model": model_name,
                    "diagnosis": diagnosis.to_dict(),
                })

                if not diagnosis.can_auto_fix:
                    overall_can_retry = False
                if diagnosis.requires_manual_review:
                    overall_requires_manual = True

            # Generate summary report
            report = self._generate_report(diagnoses, overall_can_retry)

            self.status = AgentStatus.COMPLETED

            return AgentResult(
                success=True,
                status=AgentStatus.COMPLETED,
                data={
                    "has_failures": True,
                    "failed_count": len(failed_models),
                    "diagnoses": diagnoses,
                    "can_retry": overall_can_retry and not overall_requires_manual,
                    "requires_manual_review": overall_requires_manual,
                    "report": report,
                },
                requires_approval=overall_can_retry and not overall_requires_manual,
                approval_context={
                    "action": "retry_migration",
                    "suggested_fixes": [
                        d["diagnosis"]["suggested_fixes"]
                        for d in diagnoses
                    ],
                },
            )

        except Exception as e:
            self.status = AgentStatus.FAILED
            return AgentResult(
                success=False,
                status=AgentStatus.FAILED,
                errors=[str(e)],
            )

    async def _diagnose_model_failure(
        self,
        model: dict[str, Any],
        mapping: dict[str, Any],
    ) -> DiagnosisResult:
        """Diagnose a single model's validation failure."""
        diagnosis = DiagnosisResult()
        model_name = model.get("model_name", "unknown")

        # Analyze row count issues
        row_count = model.get("row_count")
        if row_count and row_count.get("status") in ["failed", ValidationStatus.FAILED.value]:
            legacy = row_count.get("legacy_count", 0)
            dbt = row_count.get("dbt_count", 0)
            diff_pct = row_count.get("percentage_diff", 0) * 100

            if dbt < legacy:
                diagnosis.root_cause = f"Missing rows: dbt has {legacy - dbt} fewer rows ({diff_pct:.1f}%)"
                diagnosis.category = "data_mismatch"
                diagnosis.confidence = 0.8
                diagnosis.suggested_fixes.append({
                    "description": "Check source filter conditions in staging model",
                    "location": f"models/staging/stg_*__{model_name}.sql",
                    "priority": "high",
                })
                diagnosis.suggested_fixes.append({
                    "description": "Verify incremental logic if using incremental materialization",
                    "location": f"models/core/{model_name}.sql",
                    "priority": "high",
                })
                safe_model = safe_identifier(model_name)
                diagnosis.investigation_queries.append(
                    f"-- Find missing records\n"
                    f"SELECT * FROM [legacy_table]\n"
                    f"WHERE [id] NOT IN (SELECT [id] FROM {safe_model})"
                )
            else:
                diagnosis.root_cause = f"Extra rows: dbt has {dbt - legacy} more rows ({diff_pct:.1f}%)"
                diagnosis.category = "data_mismatch"
                diagnosis.confidence = 0.7
                diagnosis.suggested_fixes.append({
                    "description": "Check for duplicate records in join logic",
                    "location": f"models/core/{model_name}.sql",
                    "priority": "high",
                })
            diagnosis.can_auto_fix = False

        # Analyze primary key issues
        pk = model.get("primary_key")
        if pk and pk.get("status") in ["failed", ValidationStatus.FAILED.value]:
            null_count = pk.get("null_count", 0)
            dup_count = pk.get("duplicate_count", 0)

            if null_count > 0:
                diagnosis.root_cause = f"NULL primary keys: {null_count} records"
                diagnosis.category = "schema_mismatch"
                diagnosis.confidence = 0.9
                diagnosis.suggested_fixes.append({
                    "description": "Add NOT NULL filter or COALESCE for primary key",
                    "location": f"models/staging/stg_*__{model_name}.sql",
                    "priority": "high",
                })
                diagnosis.can_auto_fix = True

            if dup_count > 0:
                diagnosis.root_cause = f"Duplicate primary keys: {dup_count} duplicates"
                diagnosis.category = "logic_error"
                diagnosis.confidence = 0.85
                diagnosis.suggested_fixes.append({
                    "description": "Add DISTINCT or ROW_NUMBER() deduplication",
                    "location": f"models/staging/stg_*__{model_name}.sql",
                    "priority": "high",
                })
                safe_model = safe_identifier(model_name)
                diagnosis.investigation_queries.append(
                    f"-- Find duplicate keys\n"
                    f"SELECT [id], COUNT(*) AS cnt\n"
                    f"FROM {safe_model}\n"
                    f"GROUP BY [id] HAVING COUNT(*) > 1"
                )
                diagnosis.can_auto_fix = True

        # Analyze checksum issues
        checksums = model.get("checksums", [])
        failed_checksums = [
            c for c in checksums
            if c.get("status") in ["failed", ValidationStatus.FAILED.value]
        ]
        if failed_checksums:
            cols = [c.get("column") for c in failed_checksums]
            variances = [c.get("sum_variance", 0) * 100 for c in failed_checksums]
            diagnosis.root_cause = f"Numeric mismatch in columns: {', '.join(cols)}"
            diagnosis.category = "data_mismatch"
            diagnosis.confidence = 0.75
            diagnosis.suggested_fixes.append({
                "description": f"Check type casting for columns: {', '.join(cols)}",
                "location": f"models/staging/stg_*__{model_name}.sql",
                "priority": "medium",
            })
            diagnosis.suggested_fixes.append({
                "description": "Verify rounding/precision in calculations",
                "location": f"models/core/{model_name}.sql",
                "priority": "medium",
            })
            safe_model = safe_identifier(model_name)
            for col, var in zip(cols, variances):
                safe_col = safe_identifier(col)
                diagnosis.investigation_queries.append(
                    f"-- Compare {col} values\n"
                    f"SELECT 'legacy' AS src, SUM({safe_col}) AS total FROM [legacy_table]\n"
                    f"UNION ALL\n"
                    f"SELECT 'dbt' AS src, SUM({safe_col}) AS total FROM {safe_model}"
                )

        # Use LLM for deeper analysis if available
        if self.llm_client and diagnosis.confidence < 0.8:
            try:
                llm_diagnosis = await self.llm_client.diagnose_validation_failure(
                    model, mapping
                )
                if llm_diagnosis.get("confidence", 0) > diagnosis.confidence:
                    diagnosis.root_cause = llm_diagnosis.get(
                        "root_cause", diagnosis.root_cause
                    )
                    diagnosis.confidence = llm_diagnosis.get(
                        "confidence", diagnosis.confidence
                    )
                    diagnosis.suggested_fixes.extend(
                        llm_diagnosis.get("suggested_fixes", [])
                    )
                    diagnosis.requires_manual_review = llm_diagnosis.get(
                        "requires_manual_review", False
                    )
            except Exception as e:
                self.log(f"LLM diagnosis failed: {e}")

        # Set manual review flag for complex issues
        if diagnosis.confidence < 0.6 or not diagnosis.suggested_fixes:
            diagnosis.requires_manual_review = True
            diagnosis.can_auto_fix = False

        return diagnosis

    def _generate_report(
        self,
        diagnoses: list[dict[str, Any]],
        can_retry: bool,
    ) -> str:
        """Generate a markdown report of diagnoses."""
        lines = [
            "# Validation Failure Diagnosis Report",
            "",
            f"**Failed Models:** {len(diagnoses)}",
            f"**Can Auto-Retry:** {'Yes' if can_retry else 'No'}",
            "",
            "---",
            "",
        ]

        for d in diagnoses:
            model = d["model"]
            diag = d["diagnosis"]

            lines.extend([
                f"## {model}",
                "",
                f"**Root Cause:** {diag['root_cause']}",
                f"**Category:** {diag['category']}",
                f"**Confidence:** {diag['confidence']*100:.0f}%",
                "",
                "### Suggested Fixes",
                "",
            ])

            for fix in diag.get("suggested_fixes", []):
                if isinstance(fix, dict):
                    lines.append(
                        f"- [{fix.get('priority', 'medium')}] {fix.get('description', '')}"
                    )
                    if fix.get("location"):
                        lines.append(f"  - Location: `{fix['location']}`")
                else:
                    lines.append(f"- {fix}")

            if diag.get("investigation_queries"):
                lines.extend([
                    "",
                    "### Investigation Queries",
                    "",
                    "```sql",
                ])
                lines.extend(diag["investigation_queries"])
                lines.extend(["```", ""])

            lines.append("---")
            lines.append("")

        return "\n".join(lines)
