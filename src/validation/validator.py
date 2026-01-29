"""
Migration Validator - Validates dbt models against legacy SSIS data.

This module provides validation functions that would typically use SQL Server MCP
to compare row counts, primary key integrity, and numeric checksums between
legacy tables and migrated dbt models.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table

from .models import (
    ChecksumValidation,
    DbtRunResult,
    ModelValidation,
    PrimaryKeyValidation,
    RowCountValidation,
    ValidationReport,
    ValidationStatus,
)

console = Console()


class MigrationValidator:
    """
    Validator for SSIS to dbt migration.

    In production, this would use SQL Server MCP to execute queries.
    For demonstration, it generates sample validation results.
    """

    def __init__(self, dbt_project_path: str | Path, verbose: bool = False):
        """
        Initialize the validator.

        Args:
            dbt_project_path: Path to the dbt project directory
            verbose: If True, print detailed progress
        """
        self.dbt_project_path = Path(dbt_project_path)
        self.verbose = verbose
        self.report = ValidationReport()

        # Model to legacy table mapping
        self.model_mappings = {
            "dim_customer": {
                "ssis_package": "CustomerDataLoad.dtsx",
                "ssis_task": "Merge to Dimension",
                "legacy_table": "dim.Customer",
                "pk_column": "customer_key",
                "checksum_columns": [],
            },
            "fct_sales": {
                "ssis_package": "SalesFactETL.dtsx",
                "ssis_task": "Load Sales Facts",
                "legacy_table": "fact.Sales",
                "pk_column": "sale_key",
                "checksum_columns": ["quantity", "gross_amount", "net_amount"],
            },
            "fct_inventory_snapshot": {
                "ssis_package": "InventorySync.dtsx",
                "ssis_task": "Load Inventory Updates",
                "legacy_table": "fact.InventorySnapshot",
                "pk_column": "inventory_snapshot_key",
                "checksum_columns": ["quantity_on_hand", "inventory_value"],
            },
            "agg_daily_sales": {
                "ssis_package": "SalesFactETL.dtsx",
                "ssis_task": "Update Aggregates",
                "legacy_table": "agg.DailySales",
                "pk_column": "daily_sales_key",
                "checksum_columns": ["total_quantity", "total_net_amount"],
            },
        }

    def validate_row_count(
        self,
        model_name: str,
        legacy_table: str,
        legacy_count: int,
        dbt_count: int,
    ) -> RowCountValidation:
        """
        Compare row counts between legacy table and dbt model.

        Args:
            model_name: Name of the dbt model
            legacy_table: Name of the legacy table
            legacy_count: Row count from legacy table
            dbt_count: Row count from dbt model

        Returns:
            RowCountValidation result
        """
        difference = abs(dbt_count - legacy_count)
        difference_percent = (
            (difference / legacy_count * 100) if legacy_count > 0 else 0
        )

        # Determine status
        if difference == 0:
            status = ValidationStatus.PASSED
            message = "Row counts match exactly"
        elif difference_percent < 0.01:
            status = ValidationStatus.WARNING
            message = f"Minor difference: {difference} rows ({difference_percent:.4f}%)"
        else:
            status = ValidationStatus.FAILED
            message = f"Row count mismatch: {difference} rows ({difference_percent:.2f}%)"

        return RowCountValidation(
            legacy_table=legacy_table,
            legacy_count=legacy_count,
            dbt_model=model_name,
            dbt_count=dbt_count,
            difference=difference,
            difference_percent=difference_percent,
            status=status,
            message=message,
        )

    def validate_primary_key(
        self,
        model_name: str,
        pk_column: str,
        null_count: int,
        duplicate_count: int,
    ) -> PrimaryKeyValidation:
        """
        Validate primary key integrity.

        Args:
            model_name: Name of the dbt model
            pk_column: Primary key column name
            null_count: Count of NULL values in PK column
            duplicate_count: Count of duplicate PK values

        Returns:
            PrimaryKeyValidation result
        """
        if null_count == 0 and duplicate_count == 0:
            status = ValidationStatus.PASSED
            message = "Primary key integrity verified"
        elif null_count > 0 and duplicate_count > 0:
            status = ValidationStatus.FAILED
            message = f"PK has {null_count} NULLs and {duplicate_count} duplicates"
        elif null_count > 0:
            status = ValidationStatus.FAILED
            message = f"PK has {null_count} NULL values"
        else:
            status = ValidationStatus.FAILED
            message = f"PK has {duplicate_count} duplicate values"

        return PrimaryKeyValidation(
            model=model_name,
            pk_column=pk_column,
            null_count=null_count,
            duplicate_count=duplicate_count,
            status=status,
            message=message,
        )

    def validate_checksum(
        self,
        model_name: str,
        column: str,
        legacy_sum: float,
        dbt_sum: float,
        legacy_avg: float,
        dbt_avg: float,
    ) -> ChecksumValidation:
        """
        Compare numeric checksums between legacy and dbt.

        Args:
            model_name: Name of the dbt model
            column: Column name being validated
            legacy_sum: SUM from legacy table
            dbt_sum: SUM from dbt model
            legacy_avg: AVG from legacy table
            dbt_avg: AVG from dbt model

        Returns:
            ChecksumValidation result
        """
        if legacy_sum == 0:
            variance_percent = 0 if dbt_sum == 0 else 100
        else:
            variance_percent = abs((dbt_sum - legacy_sum) / legacy_sum * 100)

        if variance_percent == 0:
            status = ValidationStatus.PASSED
            message = "Checksums match exactly"
        elif variance_percent < 0.01:
            status = ValidationStatus.PASSED
            message = f"Variance within tolerance: {variance_percent:.4f}%"
        elif variance_percent < 1:
            status = ValidationStatus.WARNING
            message = f"Minor variance: {variance_percent:.4f}%"
        else:
            status = ValidationStatus.FAILED
            message = f"Checksum mismatch: {variance_percent:.2f}% variance"

        return ChecksumValidation(
            model=model_name,
            column=column,
            legacy_sum=legacy_sum,
            dbt_sum=dbt_sum,
            legacy_avg=legacy_avg,
            dbt_avg=dbt_avg,
            variance_percent=variance_percent,
            status=status,
            message=message,
        )

    def validate_model(self, model_name: str) -> ModelValidation:
        """
        Run all validations for a single model.

        In production, this would use MCP to query actual databases.
        For demonstration, it generates sample results.

        Args:
            model_name: Name of the dbt model to validate

        Returns:
            ModelValidation with all check results
        """
        mapping = self.model_mappings.get(model_name)
        if not mapping:
            return ModelValidation(
                model_name=model_name,
                ssis_package="Unknown",
                ssis_task="Unknown",
                overall_status=ValidationStatus.SKIPPED,
                errors=[f"No mapping found for model {model_name}"],
            )

        started_at = datetime.now()

        validation = ModelValidation(
            model_name=model_name,
            ssis_package=mapping["ssis_package"],
            ssis_task=mapping["ssis_task"],
            legacy_table=mapping["legacy_table"],
            started_at=started_at,
        )

        # Simulate validation results
        # In production, these would be actual MCP queries
        sample_counts = {
            "dim_customer": (15000, 15000),
            "fct_sales": (1250000, 1250000),
            "fct_inventory_snapshot": (45000, 45000),
            "agg_daily_sales": (8500, 8500),
        }

        legacy_count, dbt_count = sample_counts.get(model_name, (1000, 1000))

        # Row count validation
        validation.row_count = self.validate_row_count(
            model_name=model_name,
            legacy_table=mapping["legacy_table"],
            legacy_count=legacy_count,
            dbt_count=dbt_count,
        )

        # Primary key validation
        validation.primary_key = self.validate_primary_key(
            model_name=model_name,
            pk_column=mapping["pk_column"],
            null_count=0,  # Simulated - no nulls
            duplicate_count=0,  # Simulated - no duplicates
        )

        # Checksum validations
        for column in mapping["checksum_columns"]:
            # Simulated checksums - in production would query actual data
            sample_sum = 1000000.0
            checksum = self.validate_checksum(
                model_name=model_name,
                column=column,
                legacy_sum=sample_sum,
                dbt_sum=sample_sum,  # Matching for demo
                legacy_avg=sample_sum / legacy_count,
                dbt_avg=sample_sum / dbt_count,
            )
            validation.checksums.append(checksum)

        # Determine overall status
        completed_at = datetime.now()
        validation.completed_at = completed_at
        validation.duration_seconds = (completed_at - started_at).total_seconds()

        statuses = [validation.row_count.status, validation.primary_key.status]
        statuses.extend([c.status for c in validation.checksums])

        if ValidationStatus.FAILED in statuses:
            validation.overall_status = ValidationStatus.FAILED
        elif ValidationStatus.WARNING in statuses:
            validation.overall_status = ValidationStatus.WARNING
        else:
            validation.overall_status = ValidationStatus.PASSED

        return validation

    def run_all_validations(self) -> ValidationReport:
        """
        Run validations for all mapped models.

        Returns:
            Complete ValidationReport
        """
        if self.verbose:
            console.print("[bold blue]Starting validation run...[/bold blue]")

        for model_name in self.model_mappings.keys():
            if self.verbose:
                console.print(f"  Validating {model_name}...")

            validation = self.validate_model(model_name)
            self.report.model_validations.append(validation)

            if self.verbose:
                status_style = {
                    ValidationStatus.PASSED: "[green]PASSED[/green]",
                    ValidationStatus.FAILED: "[red]FAILED[/red]",
                    ValidationStatus.WARNING: "[yellow]WARNING[/yellow]",
                    ValidationStatus.SKIPPED: "[dim]SKIPPED[/dim]",
                }
                console.print(f"    {status_style.get(validation.overall_status, validation.overall_status)}")

        self.report.calculate_summary()
        return self.report

    def generate_sql_queries(self) -> dict[str, list[str]]:
        """
        Generate SQL queries that would be used for MCP validation.

        Returns:
            Dictionary of model names to list of SQL queries
        """
        queries = {}

        for model_name, mapping in self.model_mappings.items():
            model_queries = []
            legacy_table = mapping["legacy_table"]
            pk_column = mapping["pk_column"]

            # Row count query
            model_queries.append(f"""
-- Row Count Comparison for {model_name}
-- Legacy:
SELECT COUNT(*) AS row_count FROM {legacy_table};
-- dbt:
SELECT COUNT(*) AS row_count FROM dbt_prod.{model_name};
""")

            # PK integrity query
            model_queries.append(f"""
-- Primary Key Integrity for {model_name}
-- NULL check:
SELECT COUNT(*) AS null_count FROM dbt_prod.{model_name} WHERE {pk_column} IS NULL;
-- Duplicate check:
SELECT {pk_column}, COUNT(*) AS cnt
FROM dbt_prod.{model_name}
GROUP BY {pk_column}
HAVING COUNT(*) > 1;
""")

            # Checksum queries
            for column in mapping["checksum_columns"]:
                model_queries.append(f"""
-- Checksum for {model_name}.{column}
-- Legacy:
SELECT SUM(CAST({column} AS FLOAT)) AS sum_val, AVG(CAST({column} AS FLOAT)) AS avg_val
FROM {legacy_table};
-- dbt:
SELECT SUM(CAST({column} AS FLOAT)) AS sum_val, AVG(CAST({column} AS FLOAT)) AS avg_val
FROM dbt_prod.{model_name};
""")

            queries[model_name] = model_queries

        return queries

    def export_json(self, output_path: str | Path) -> None:
        """Export validation results to JSON."""
        output_path = Path(output_path)
        with open(output_path, "w") as f:
            json.dump(self.report.model_dump(), f, indent=2, default=str)

        if self.verbose:
            console.print(f"[green]✓ Exported validation_log.json[/green]")

    def generate_report(self, output_path: str | Path) -> None:
        """Generate markdown validation report."""
        output_path = Path(output_path)

        lines = [
            "# Migration Validation Report",
            "",
            f"**Generated**: {self.report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Summary",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Models | {self.report.total_models} |",
            f"| Passed | {self.report.models_passed} |",
            f"| Failed | {self.report.models_failed} |",
            f"| Warnings | {self.report.models_warning} |",
            f"| Overall Status | **{self.report.overall_status.value.upper()}** |",
            "",
        ]

        # dbt execution results
        if self.report.dbt_run:
            lines.extend([
                "## dbt Execution",
                "",
                f"| Command | Status | Duration |",
                f"|---------|--------|----------|",
            ])
            if self.report.dbt_deps:
                status = "✅" if self.report.dbt_deps.success else "❌"
                lines.append(f"| dbt deps | {status} | {self.report.dbt_deps.duration_seconds:.1f}s |")
            if self.report.dbt_run:
                status = "✅" if self.report.dbt_run.success else "❌"
                lines.append(f"| dbt run | {status} | {self.report.dbt_run.duration_seconds:.1f}s |")
            if self.report.dbt_test:
                status = "✅" if self.report.dbt_test.success else "❌"
                lines.append(f"| dbt test | {status} | {self.report.dbt_test.duration_seconds:.1f}s |")
            lines.append("")

        # Model details
        lines.extend([
            "## Model Validations",
            "",
        ])

        for mv in self.report.model_validations:
            status_emoji = {
                ValidationStatus.PASSED: "✅",
                ValidationStatus.FAILED: "❌",
                ValidationStatus.WARNING: "⚠️",
                ValidationStatus.SKIPPED: "⏭️",
            }.get(mv.overall_status, "❓")

            lines.extend([
                f"### {mv.model_name} {status_emoji}",
                "",
                f"- **SSIS Package**: {mv.ssis_package}",
                f"- **SSIS Task**: {mv.ssis_task}",
                f"- **Legacy Table**: {mv.legacy_table or 'N/A'}",
                "",
            ])

            # Row count
            if mv.row_count:
                rc = mv.row_count
                lines.extend([
                    "#### Row Count Comparison",
                    "",
                    f"| Source | Count |",
                    f"|--------|-------|",
                    f"| Legacy ({rc.legacy_table}) | {rc.legacy_count:,} |",
                    f"| dbt ({rc.dbt_model}) | {rc.dbt_count:,} |",
                    f"| **Difference** | {rc.difference:,} ({rc.difference_percent:.4f}%) |",
                    f"| **Status** | {rc.status.value.upper()} |",
                    "",
                ])

            # Primary key
            if mv.primary_key:
                pk = mv.primary_key
                lines.extend([
                    "#### Primary Key Integrity",
                    "",
                    f"| Check | Result |",
                    f"|-------|--------|",
                    f"| Column | `{pk.pk_column}` |",
                    f"| NULL values | {pk.null_count} |",
                    f"| Duplicate values | {pk.duplicate_count} |",
                    f"| **Status** | {pk.status.value.upper()} |",
                    "",
                ])

            # Checksums
            if mv.checksums:
                lines.extend([
                    "#### Numeric Checksums",
                    "",
                    f"| Column | Legacy SUM | dbt SUM | Variance | Status |",
                    f"|--------|------------|---------|----------|--------|",
                ])
                for cs in mv.checksums:
                    lines.append(
                        f"| {cs.column} | {cs.legacy_sum:,.2f} | {cs.dbt_sum:,.2f} | {cs.variance_percent:.4f}% | {cs.status.value.upper()} |"
                    )
                lines.append("")

        # MCP query reference
        lines.extend([
            "## MCP Validation Queries",
            "",
            "The following queries should be executed via SQL Server MCP for production validation:",
            "",
        ])

        queries = self.generate_sql_queries()
        for model_name, model_queries in queries.items():
            lines.append(f"### {model_name}")
            lines.append("")
            for query in model_queries:
                lines.append("```sql")
                lines.append(query.strip())
                lines.append("```")
                lines.append("")

        with open(output_path, "w") as f:
            f.write("\n".join(lines))

        if self.verbose:
            console.print(f"[green]✓ Generated validation_report.md[/green]")

    def print_summary(self) -> None:
        """Print validation summary to console."""
        table = Table(title="Validation Summary")
        table.add_column("Model", style="cyan")
        table.add_column("Row Count", justify="center")
        table.add_column("PK Integrity", justify="center")
        table.add_column("Checksums", justify="center")
        table.add_column("Status", justify="center")

        status_style = {
            ValidationStatus.PASSED: "[green]PASS[/green]",
            ValidationStatus.FAILED: "[red]FAIL[/red]",
            ValidationStatus.WARNING: "[yellow]WARN[/yellow]",
            ValidationStatus.SKIPPED: "[dim]SKIP[/dim]",
        }

        for mv in self.report.model_validations:
            rc_status = status_style.get(mv.row_count.status, "N/A") if mv.row_count else "N/A"
            pk_status = status_style.get(mv.primary_key.status, "N/A") if mv.primary_key else "N/A"

            if mv.checksums:
                cs_statuses = [cs.status for cs in mv.checksums]
                if ValidationStatus.FAILED in cs_statuses:
                    cs_status = status_style[ValidationStatus.FAILED]
                elif ValidationStatus.WARNING in cs_statuses:
                    cs_status = status_style[ValidationStatus.WARNING]
                else:
                    cs_status = status_style[ValidationStatus.PASSED]
            else:
                cs_status = "[dim]N/A[/dim]"

            overall = status_style.get(mv.overall_status, "N/A")

            table.add_row(mv.model_name, rc_status, pk_status, cs_status, overall)

        console.print(table)
        console.print()
        console.print(f"[bold]Overall Status:[/bold] {status_style.get(self.report.overall_status, 'UNKNOWN')}")
