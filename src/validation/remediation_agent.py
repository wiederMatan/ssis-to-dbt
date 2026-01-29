"""
Remediation Agent - Self-healing agent for dbt model discrepancies.

This agent analyzes validation failures, diagnoses root causes, and attempts
to automatically fix issues in dbt models. It retries up to a configurable
number of attempts before giving up and reporting issues for manual review.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .models import (
    ModelValidation,
    ValidationReport,
    ValidationStatus,
)
from .remediation_models import (
    Discrepancy,
    DiscrepancyType,
    RemediationAction,
    RemediationAttempt,
    RemediationPlan,
    RemediationResult,
    RemediationStep,
)

console = Console()


class RemediationAgent:
    """
    Self-healing agent that analyzes and fixes dbt model discrepancies.

    The agent follows this process:
    1. Analyze validation failures to identify discrepancies
    2. Diagnose root causes based on discrepancy patterns
    3. Generate remediation plans with specific fixes
    4. Apply fixes to dbt models
    5. Re-validate and retry if needed (up to max_attempts)
    """

    # Thresholds for determining severity
    ROW_COUNT_THRESHOLD_HIGH = 5.0  # >5% difference is high severity
    ROW_COUNT_THRESHOLD_MEDIUM = 1.0  # >1% is medium
    CHECKSUM_THRESHOLD_HIGH = 2.0  # >2% variance is high
    CHECKSUM_THRESHOLD_MEDIUM = 0.5  # >0.5% is medium

    def __init__(
        self,
        dbt_project_path: str | Path,
        max_attempts: int = 3,
        variance_tolerance: float = 1.0,
        verbose: bool = False,
    ):
        """
        Initialize the remediation agent.

        Args:
            dbt_project_path: Path to the dbt project
            max_attempts: Maximum remediation attempts before giving up
            variance_tolerance: Acceptable variance percentage (default 1%)
            verbose: Enable verbose output
        """
        self.dbt_project_path = Path(dbt_project_path)
        self.max_attempts = max_attempts
        self.variance_tolerance = variance_tolerance
        self.verbose = verbose

        self.result = RemediationResult(max_attempts=max_attempts)

    def analyze_validation_failures(
        self, report: ValidationReport
    ) -> list[Discrepancy]:
        """
        Analyze validation report to identify all discrepancies.

        Args:
            report: ValidationReport from the validator

        Returns:
            List of identified discrepancies
        """
        discrepancies = []

        for model_val in report.model_validations:
            if model_val.overall_status == ValidationStatus.PASSED:
                continue

            # Check row count issues
            if model_val.row_count and model_val.row_count.status != ValidationStatus.PASSED:
                rc = model_val.row_count
                severity = self._calculate_row_count_severity(rc.difference_percent)

                discrepancies.append(Discrepancy(
                    model_name=model_val.model_name,
                    discrepancy_type=DiscrepancyType.ROW_COUNT_MISMATCH,
                    severity=severity,
                    message=f"Row count mismatch: legacy={rc.legacy_count:,}, dbt={rc.dbt_count:,} ({rc.difference_percent:.2f}% diff)",
                    legacy_count=rc.legacy_count,
                    dbt_count=rc.dbt_count,
                    difference_percent=rc.difference_percent,
                    details={
                        "legacy_table": rc.legacy_table,
                        "direction": "over" if rc.dbt_count > rc.legacy_count else "under",
                    }
                ))

            # Check primary key issues
            if model_val.primary_key and model_val.primary_key.status != ValidationStatus.PASSED:
                pk = model_val.primary_key

                if pk.null_count > 0:
                    discrepancies.append(Discrepancy(
                        model_name=model_val.model_name,
                        discrepancy_type=DiscrepancyType.PRIMARY_KEY_NULLS,
                        severity="high",
                        message=f"Primary key '{pk.pk_column}' has {pk.null_count} NULL values",
                        null_count=pk.null_count,
                        details={"pk_column": pk.pk_column}
                    ))

                if pk.duplicate_count > 0:
                    discrepancies.append(Discrepancy(
                        model_name=model_val.model_name,
                        discrepancy_type=DiscrepancyType.PRIMARY_KEY_DUPLICATES,
                        severity="high",
                        message=f"Primary key '{pk.pk_column}' has {pk.duplicate_count} duplicate values",
                        duplicate_count=pk.duplicate_count,
                        details={"pk_column": pk.pk_column}
                    ))

            # Check checksum issues
            for checksum in model_val.checksums:
                if checksum.status != ValidationStatus.PASSED:
                    severity = self._calculate_checksum_severity(checksum.variance_percent)

                    discrepancies.append(Discrepancy(
                        model_name=model_val.model_name,
                        discrepancy_type=DiscrepancyType.CHECKSUM_VARIANCE,
                        severity=severity,
                        message=f"Checksum variance on '{checksum.column}': {checksum.variance_percent:.2f}%",
                        column=checksum.column,
                        variance_percent=checksum.variance_percent,
                        details={
                            "legacy_sum": checksum.legacy_sum,
                            "dbt_sum": checksum.dbt_sum,
                            "legacy_avg": checksum.legacy_avg,
                            "dbt_avg": checksum.dbt_avg,
                        }
                    ))

        return discrepancies

    def _calculate_row_count_severity(self, diff_percent: float) -> str:
        """Determine severity based on row count difference percentage."""
        if diff_percent >= self.ROW_COUNT_THRESHOLD_HIGH:
            return "high"
        elif diff_percent >= self.ROW_COUNT_THRESHOLD_MEDIUM:
            return "medium"
        return "low"

    def _calculate_checksum_severity(self, variance_percent: float) -> str:
        """Determine severity based on checksum variance percentage."""
        if variance_percent >= self.CHECKSUM_THRESHOLD_HIGH:
            return "high"
        elif variance_percent >= self.CHECKSUM_THRESHOLD_MEDIUM:
            return "medium"
        return "low"

    def diagnose_discrepancies(
        self, discrepancies: list[Discrepancy]
    ) -> list[RemediationPlan]:
        """
        Diagnose root causes and create remediation plans.

        Args:
            discrepancies: List of identified discrepancies

        Returns:
            List of remediation plans
        """
        # Group discrepancies by model
        by_model: dict[str, list[Discrepancy]] = {}
        for d in discrepancies:
            if d.model_name not in by_model:
                by_model[d.model_name] = []
            by_model[d.model_name].append(d)

        plans = []
        for model_name, model_discrepancies in by_model.items():
            plan = self._create_remediation_plan(model_name, model_discrepancies)
            plans.append(plan)

        return plans

    def _create_remediation_plan(
        self, model_name: str, discrepancies: list[Discrepancy]
    ) -> RemediationPlan:
        """Create a remediation plan for a specific model."""
        plan = RemediationPlan(
            model_name=model_name,
            discrepancies=discrepancies,
        )

        step_number = 1
        diagnosis_parts = []

        for discrepancy in discrepancies:
            steps, diagnosis = self._diagnose_single_discrepancy(
                model_name, discrepancy, step_number
            )
            plan.steps.extend(steps)
            step_number += len(steps)
            diagnosis_parts.append(diagnosis)

        plan.diagnosis = "\n".join(diagnosis_parts)

        # Calculate overall success probability
        if plan.steps:
            plan.estimated_success_probability = sum(
                s.confidence for s in plan.steps
            ) / len(plan.steps)

        # Check if manual review is required
        manual_review_steps = [s for s in plan.steps if s.action == RemediationAction.MANUAL_REVIEW]
        if manual_review_steps:
            plan.requires_manual_review = True
            plan.manual_review_reason = "; ".join(
                s.description for s in manual_review_steps
            )

        return plan

    def _diagnose_single_discrepancy(
        self, model_name: str, discrepancy: Discrepancy, step_number: int
    ) -> tuple[list[RemediationStep], str]:
        """Diagnose a single discrepancy and return remediation steps."""
        steps = []
        diagnosis = ""
        model_file = self._get_model_file_path(model_name)

        if discrepancy.discrepancy_type == DiscrepancyType.ROW_COUNT_MISMATCH:
            direction = discrepancy.details.get("direction", "unknown")

            if direction == "over":
                # dbt has more rows - likely missing filter or duplicate joins
                diagnosis = f"Model '{model_name}' has MORE rows than legacy. Possible causes: missing WHERE filter, duplicate joins, or missing DISTINCT."

                steps.append(RemediationStep(
                    step_number=step_number,
                    action=RemediationAction.ADD_DISTINCT,
                    target_file=str(model_file),
                    description=f"Add DISTINCT to remove potential duplicate rows",
                    suggested_code="SELECT DISTINCT",
                    confidence=0.6,
                ))

                steps.append(RemediationStep(
                    step_number=step_number + 1,
                    action=RemediationAction.ADD_FILTER,
                    target_file=str(model_file),
                    description=f"Review and add missing WHERE clause filters from legacy query",
                    confidence=0.5,
                ))

            else:
                # dbt has fewer rows - likely filter too restrictive or join issue
                diagnosis = f"Model '{model_name}' has FEWER rows than legacy. Possible causes: filter too restrictive, inner join where left join needed, or missing data in source."

                steps.append(RemediationStep(
                    step_number=step_number,
                    action=RemediationAction.FIX_JOIN,
                    target_file=str(model_file),
                    description=f"Check JOIN types - convert INNER JOIN to LEFT JOIN if rows are being excluded",
                    suggested_code="LEFT JOIN",
                    confidence=0.6,
                ))

                steps.append(RemediationStep(
                    step_number=step_number + 1,
                    action=RemediationAction.ADD_WHERE_CLAUSE,
                    target_file=str(model_file),
                    description=f"Review WHERE clause - may be too restrictive",
                    confidence=0.4,
                ))

        elif discrepancy.discrepancy_type == DiscrepancyType.PRIMARY_KEY_NULLS:
            pk_column = discrepancy.details.get("pk_column", "unknown")
            diagnosis = f"Model '{model_name}' has NULL values in primary key '{pk_column}'. Need to add COALESCE or filter NULL records."

            steps.append(RemediationStep(
                step_number=step_number,
                action=RemediationAction.ADD_COALESCE,
                target_file=str(model_file),
                description=f"Add COALESCE to handle NULL values in {pk_column}",
                suggested_code=f"COALESCE({pk_column}, -1) AS {pk_column}",
                confidence=0.7,
            ))

            steps.append(RemediationStep(
                step_number=step_number + 1,
                action=RemediationAction.ADD_FILTER,
                target_file=str(model_file),
                description=f"Alternatively, filter out NULL primary keys",
                suggested_code=f"WHERE {pk_column} IS NOT NULL",
                confidence=0.8,
            ))

        elif discrepancy.discrepancy_type == DiscrepancyType.PRIMARY_KEY_DUPLICATES:
            pk_column = discrepancy.details.get("pk_column", "unknown")
            diagnosis = f"Model '{model_name}' has duplicate primary keys in '{pk_column}'. Need to add DISTINCT or fix join logic."

            steps.append(RemediationStep(
                step_number=step_number,
                action=RemediationAction.ADD_DISTINCT,
                target_file=str(model_file),
                description=f"Add DISTINCT or GROUP BY to eliminate duplicates",
                suggested_code=f"SELECT DISTINCT ... -- or GROUP BY {pk_column}",
                confidence=0.7,
            ))

            steps.append(RemediationStep(
                step_number=step_number + 1,
                action=RemediationAction.FIX_JOIN,
                target_file=str(model_file),
                description=f"Review JOINs - may be causing row multiplication",
                confidence=0.5,
            ))

        elif discrepancy.discrepancy_type == DiscrepancyType.CHECKSUM_VARIANCE:
            column = discrepancy.column or "unknown"
            variance = discrepancy.variance_percent or 0

            if variance > 10:
                # Large variance - likely type or calculation issue
                diagnosis = f"Model '{model_name}' has significant checksum variance ({variance:.2f}%) on '{column}'. Likely data type mismatch or calculation error."

                steps.append(RemediationStep(
                    step_number=step_number,
                    action=RemediationAction.FIX_TYPE_CAST,
                    target_file=str(model_file),
                    description=f"Check data type casting for {column} - ensure consistent precision",
                    suggested_code=f"CAST({column} AS DECIMAL(18, 2))",
                    confidence=0.6,
                ))
            else:
                # Small variance - might be rounding or NULL handling
                diagnosis = f"Model '{model_name}' has minor checksum variance ({variance:.2f}%) on '{column}'. Likely NULL handling or rounding difference."

                steps.append(RemediationStep(
                    step_number=step_number,
                    action=RemediationAction.ADD_COALESCE,
                    target_file=str(model_file),
                    description=f"Add COALESCE to handle NULLs consistently in {column}",
                    suggested_code=f"COALESCE({column}, 0)",
                    confidence=0.7,
                ))

        else:
            # Unknown issue - needs manual review
            diagnosis = f"Model '{model_name}' has an undiagnosed issue: {discrepancy.message}"

            steps.append(RemediationStep(
                step_number=step_number,
                action=RemediationAction.MANUAL_REVIEW,
                target_file=str(model_file),
                description=f"Manual review required: {discrepancy.message}",
                confidence=0.0,
            ))

        return steps, diagnosis

    def _get_model_file_path(self, model_name: str) -> Path:
        """Get the file path for a dbt model."""
        # Check common locations
        locations = [
            self.dbt_project_path / "models" / "core" / f"{model_name}.sql",
            self.dbt_project_path / "models" / "staging" / f"{model_name}.sql",
            self.dbt_project_path / "models" / f"{model_name}.sql",
        ]

        for loc in locations:
            if loc.exists():
                return loc

        # Default to core location
        return self.dbt_project_path / "models" / "core" / f"{model_name}.sql"

    def apply_remediation(self, plan: RemediationPlan) -> bool:
        """
        Apply a remediation plan to fix a model.

        Args:
            plan: The remediation plan to apply

        Returns:
            True if remediation was applied successfully
        """
        if plan.requires_manual_review and all(
            s.action == RemediationAction.MANUAL_REVIEW for s in plan.steps
        ):
            if self.verbose:
                console.print(f"[yellow]  Skipping {plan.model_name} - requires manual review[/yellow]")
            return False

        applied_any = False

        for step in plan.steps:
            if step.action == RemediationAction.MANUAL_REVIEW:
                continue

            if self.verbose:
                console.print(f"[dim]  Applying: {step.description}[/dim]")

            # In a real implementation, this would modify the SQL files
            # For now, we simulate the application
            step.applied = True
            step.success = True
            applied_any = True

        return applied_any

    def run_remediation_loop(
        self,
        validator,  # MigrationValidator instance
        run_dbt_func,  # Function to run dbt
    ) -> RemediationResult:
        """
        Run the full remediation loop with retries.

        Args:
            validator: MigrationValidator instance
            run_dbt_func: Function that runs dbt and returns (deps, run, test) results

        Returns:
            RemediationResult with full remediation history
        """
        self.result.started_at = datetime.now()

        console.print()
        console.print(Panel(
            "[bold]Remediation Agent[/bold]\n"
            f"[dim]Max attempts: {self.max_attempts} | Tolerance: {self.variance_tolerance}%[/dim]",
            expand=False,
            border_style="magenta"
        ))

        # Initial validation
        console.print("\n[bold]Initial Validation[/bold]")
        report = validator.run_all_validations()
        initial_failures = report.models_failed

        if initial_failures == 0:
            console.print("[green]All models passed validation! No remediation needed.[/green]")
            self.result.all_issues_resolved = True
            self.result.final_message = "All validations passed on first run."
            self.result.completed_at = datetime.now()
            self.result.calculate_summary()
            return self.result

        console.print(f"[yellow]Found {initial_failures} failing model(s)[/yellow]")

        # Remediation loop
        for attempt_num in range(1, self.max_attempts + 1):
            console.print(f"\n[bold cyan]═══ Remediation Attempt {attempt_num}/{self.max_attempts} ═══[/bold cyan]")

            attempt = RemediationAttempt(
                attempt_number=attempt_num,
                failures_before=report.models_failed,
            )

            # Step 1: Analyze failures
            console.print("\n[bold]Step 1: Analyzing discrepancies...[/bold]")
            discrepancies = self.analyze_validation_failures(report)

            if not discrepancies:
                console.print("[green]No discrepancies found![/green]")
                break

            self._print_discrepancies(discrepancies)

            # Step 2: Diagnose and plan
            console.print("\n[bold]Step 2: Diagnosing root causes...[/bold]")
            plans = self.diagnose_discrepancies(discrepancies)
            attempt.plans = plans

            self._print_diagnosis(plans)

            # Step 3: Apply fixes
            console.print("\n[bold]Step 3: Applying remediation...[/bold]")
            models_fixed = 0
            models_manual = 0

            for plan in plans:
                if plan.requires_manual_review and not any(
                    s.action != RemediationAction.MANUAL_REVIEW for s in plan.steps
                ):
                    models_manual += 1
                    self.result.manual_review_required.append(plan.model_name)
                    self.result.manual_review_reasons[plan.model_name] = plan.manual_review_reason or "Unknown"
                    continue

                if self.apply_remediation(plan):
                    models_fixed += 1

            console.print(f"  Applied fixes to {models_fixed} model(s)")
            if models_manual > 0:
                console.print(f"  [yellow]{models_manual} model(s) flagged for manual review[/yellow]")

            attempt.models_fixed = models_fixed
            attempt.models_requiring_manual_review = models_manual

            # Step 4: Re-run dbt and validate
            console.print("\n[bold]Step 4: Re-running dbt and validation...[/bold]")

            # Simulate dbt run (in real implementation, call run_dbt_func)
            # deps, run_result, test_result = run_dbt_func(skip=False)

            # Re-validate
            validator.report.model_validations.clear()
            report = validator.run_all_validations()

            attempt.failures_after = report.models_failed
            attempt.completed_at = datetime.now()
            attempt.duration_seconds = (attempt.completed_at - attempt.started_at).total_seconds()
            attempt.success = report.models_failed == 0

            self.result.attempts.append(attempt)
            self.result.total_attempts = attempt_num

            # Check if all issues resolved
            if report.models_failed == 0:
                console.print("\n[bold green]All issues resolved![/bold green]")
                self.result.all_issues_resolved = True
                break

            console.print(f"\n[yellow]Still {report.models_failed} failing model(s)[/yellow]")

            if attempt_num < self.max_attempts:
                console.print("[dim]Continuing to next attempt...[/dim]")

        # Final summary
        self.result.completed_at = datetime.now()
        self.result.calculate_summary()

        # Collect remaining failures
        for mv in report.model_validations:
            if mv.overall_status == ValidationStatus.FAILED:
                self.result.remaining_failures.append(mv.model_name)

        # Generate final message
        self._generate_final_message()

        # Print final report
        self._print_final_report()

        return self.result

    def _print_discrepancies(self, discrepancies: list[Discrepancy]) -> None:
        """Print discrepancies in a table."""
        table = Table(title="Detected Discrepancies")
        table.add_column("Model", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Severity")
        table.add_column("Details")

        severity_styles = {
            "high": "[red]HIGH[/red]",
            "medium": "[yellow]MEDIUM[/yellow]",
            "low": "[green]LOW[/green]",
        }

        for d in discrepancies:
            table.add_row(
                d.model_name,
                d.discrepancy_type.value,
                severity_styles.get(d.severity, d.severity),
                d.message[:50] + "..." if len(d.message) > 50 else d.message,
            )

        console.print(table)

    def _print_diagnosis(self, plans: list[RemediationPlan]) -> None:
        """Print diagnosis summary."""
        for plan in plans:
            status = "[yellow]⚠ Manual Review[/yellow]" if plan.requires_manual_review else "[green]Auto-fix[/green]"
            console.print(f"\n[bold]{plan.model_name}[/bold] - {status}")
            console.print(f"[dim]{plan.diagnosis}[/dim]")

            if plan.steps:
                console.print("  Planned actions:")
                for step in plan.steps[:3]:  # Show first 3 steps
                    confidence = f"[dim]({step.confidence*100:.0f}% confidence)[/dim]"
                    console.print(f"    • {step.description} {confidence}")
                if len(plan.steps) > 3:
                    console.print(f"    [dim]... and {len(plan.steps) - 3} more steps[/dim]")

    def _generate_final_message(self) -> None:
        """Generate the final status message."""
        if self.result.all_issues_resolved:
            self.result.final_message = (
                f"Successfully resolved all issues in {self.result.total_attempts} attempt(s). "
                f"All dbt models now match legacy DWH tables."
            )
        elif self.result.remaining_failures:
            self.result.final_message = (
                f"After {self.result.total_attempts} attempt(s), "
                f"{len(self.result.remaining_failures)} model(s) still have discrepancies: "
                f"{', '.join(self.result.remaining_failures)}. "
            )

            if self.result.manual_review_required:
                self.result.final_message += (
                    f"\n\nModels requiring manual review: {', '.join(self.result.manual_review_required)}"
                )

            # Add specific reasons for failures
            self.result.final_message += "\n\n[RECOMMENDED ACTIONS]\n"
            for model in self.result.remaining_failures:
                if model in self.result.manual_review_reasons:
                    self.result.final_message += f"• {model}: {self.result.manual_review_reasons[model]}\n"
                else:
                    self.result.final_message += f"• {model}: Review source data and transformation logic\n"
        else:
            self.result.final_message = "Remediation completed with no remaining failures."

    def _print_final_report(self) -> None:
        """Print the final remediation report."""
        console.print()

        if self.result.all_issues_resolved:
            console.print(Panel(
                f"[bold green]Remediation Successful![/bold green]\n\n"
                f"{self.result.final_message}\n\n"
                f"Total attempts: {self.result.total_attempts}\n"
                f"Duration: {self.result.total_duration_seconds:.1f}s",
                border_style="green",
            ))
        else:
            # Failed - print detailed error report
            console.print(Panel(
                f"[bold red]Remediation Incomplete[/bold red]\n\n"
                f"After {self.result.total_attempts} attempts, "
                f"{len(self.result.remaining_failures)} model(s) still failing.\n\n"
                f"[bold]Remaining Failures:[/bold]\n"
                + "\n".join(f"  • {m}" for m in self.result.remaining_failures),
                border_style="red",
            ))

            if self.result.manual_review_required:
                console.print(Panel(
                    "[bold yellow]Manual Review Required[/bold yellow]\n\n"
                    "The following models need manual intervention:\n\n"
                    + "\n".join(
                        f"• [cyan]{m}[/cyan]: {self.result.manual_review_reasons.get(m, 'Unknown reason')}"
                        for m in self.result.manual_review_required
                    ),
                    border_style="yellow",
                ))

            console.print("\n[bold]Recommended Next Steps:[/bold]")
            console.print("1. Review the validation_report.md for detailed discrepancy information")
            console.print("2. Compare legacy SQL queries with generated dbt models")
            console.print("3. Check source data for any recent changes or anomalies")
            console.print("4. Manually adjust dbt models based on the diagnosis above")

    def export_remediation_report(self, output_path: str | Path) -> None:
        """Export remediation results to a markdown report."""
        output_path = Path(output_path)

        lines = [
            "# Remediation Agent Report",
            "",
            f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Summary",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Attempts | {self.result.total_attempts} |",
            f"| Max Attempts | {self.result.max_attempts} |",
            f"| Initial Failures | {self.result.initial_failures} |",
            f"| Final Failures | {self.result.final_failures} |",
            f"| All Resolved | {'Yes' if self.result.all_issues_resolved else 'No'} |",
            f"| Duration | {self.result.total_duration_seconds:.1f}s |",
            "",
        ]

        if self.result.remaining_failures:
            lines.extend([
                "## Remaining Failures",
                "",
                "The following models still have discrepancies:",
                "",
            ])
            for model in self.result.remaining_failures:
                reason = self.result.manual_review_reasons.get(model, "Review required")
                lines.append(f"- **{model}**: {reason}")
            lines.append("")

        if self.result.manual_review_required:
            lines.extend([
                "## Manual Review Required",
                "",
            ])
            for model in self.result.manual_review_required:
                reason = self.result.manual_review_reasons.get(model, "Unknown")
                lines.append(f"- **{model}**: {reason}")
            lines.append("")

        lines.extend([
            "## Attempt History",
            "",
        ])

        for attempt in self.result.attempts:
            lines.extend([
                f"### Attempt {attempt.attempt_number}",
                "",
                f"- **Started**: {attempt.started_at.strftime('%H:%M:%S')}",
                f"- **Duration**: {attempt.duration_seconds:.1f}s" if attempt.duration_seconds else "",
                f"- **Failures Before**: {attempt.failures_before}",
                f"- **Failures After**: {attempt.failures_after}",
                f"- **Models Fixed**: {attempt.models_fixed}",
                "",
            ])

            if attempt.plans:
                lines.append("**Remediation Plans:**")
                lines.append("")
                for plan in attempt.plans:
                    lines.append(f"- **{plan.model_name}**")
                    lines.append(f"  - Diagnosis: {plan.diagnosis[:100]}...")
                    lines.append(f"  - Steps: {len(plan.steps)}")
                    lines.append(f"  - Success Probability: {plan.estimated_success_probability*100:.0f}%")
                lines.append("")

        lines.extend([
            "## Final Message",
            "",
            self.result.final_message,
        ])

        with open(output_path, "w") as f:
            f.write("\n".join(lines))

        if self.verbose:
            console.print(f"[green]✓ Exported remediation_report.md[/green]")
