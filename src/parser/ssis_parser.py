"""
SSIS Package Parser - Extracts metadata from .dtsx files.

This module parses SQL Server Integration Services (SSIS) package files
and extracts connection managers, variables, tasks, and data flow components.
"""

import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path

from lxml import etree
from rich.console import Console
from rich.table import Table

logger = logging.getLogger(__name__)

# Secure XML parser configuration to prevent XXE attacks
def _create_secure_parser() -> etree.XMLParser:
    """
    Create a secure XML parser with external entity processing disabled.

    This prevents XXE (XML External Entity) attacks that could:
    - Read arbitrary files from the filesystem
    - Perform SSRF (Server-Side Request Forgery) attacks
    - Cause denial of service via entity expansion (Billion Laughs attack)
    """
    return etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        dtd_validation=False,
        load_dtd=False,
    )

from .constants import MANUAL_REVIEW_TASKS, NAMESPACES, VARIABLE_DATA_TYPES
from .models import (
    ColumnInfo,
    ConnectionManager,
    DataFlowDestination,
    DataFlowSource,
    DataFlowTask,
    DerivedColumnDef,
    ExecuteSQLTask,
    LookupTransform,
    ParsingResult,
    PrecedenceConstraint,
    SchemaColumn,
    SchemaMetadata,
    SchemaTable,
    ScriptTask,
    SendMailTask,
    SSISPackage,
    Variable,
)
from .type_mappings import map_ssis_type_to_sql

console = Console()


class SSISParser:
    """Parser for SSIS .dtsx package files."""

    def __init__(self, verbose: bool = False):
        """
        Initialize the SSIS parser.

        Args:
            verbose: If True, print detailed progress information
        """
        self.verbose = verbose
        self.packages: list[SSISPackage] = []
        self.schema_metadata = SchemaMetadata()
        self._tables_seen: set[str] = set()

    def parse_directory(self, directory: str | Path) -> list[SSISPackage]:
        """
        Parse all .dtsx files in a directory recursively.

        Args:
            directory: Path to directory containing SSIS packages

        Returns:
            List of parsed SSISPackage objects
        """
        directory = Path(directory)
        dtsx_files = list(directory.glob("**/*.dtsx"))

        logger.info(f"Found {len(dtsx_files)} SSIS packages in {directory}")
        if self.verbose:
            console.print(f"[bold blue]Found {len(dtsx_files)} SSIS packages[/bold blue]")
            for f in dtsx_files:
                size_kb = f.stat().st_size / 1024
                console.print(f"  - {f.name} ({size_kb:.1f} KB)")

        for dtsx_file in dtsx_files:
            try:
                logger.debug(f"Parsing package: {dtsx_file}")
                package = self.parse_package(dtsx_file)
                self.packages.append(package)
                logger.info(f"Successfully parsed: {package.name}")
                if self.verbose:
                    console.print(f"[green]✓ Parsed: {package.name}[/green]")
            except Exception as e:
                logger.error(f"Error parsing {dtsx_file}: {e}", exc_info=True)
                console.print(f"[red]✗ Error parsing {dtsx_file}: {e}[/red]")

        return self.packages

    def parse_package(self, file_path: str | Path) -> SSISPackage:
        """
        Parse a single SSIS package file.

        Args:
            file_path: Path to the .dtsx file

        Returns:
            Parsed SSISPackage object
        """
        file_path = Path(file_path)
        # Use secure parser to prevent XXE attacks
        secure_parser = _create_secure_parser()
        tree = etree.parse(str(file_path), parser=secure_parser)
        root = tree.getroot()

        ns = NAMESPACES["DTS"]

        # Extract package metadata
        package = SSISPackage(
            name=root.get(f"{{{ns}}}ObjectName", file_path.stem),
            description=root.get(f"{{{ns}}}Description"),
            creation_date=root.get(f"{{{ns}}}CreationDate"),
            creator_name=root.get(f"{{{ns}}}CreatorName"),
            creator_computer=root.get(f"{{{ns}}}CreatorComputerName"),
            file_path=str(file_path.absolute()),
            file_size_bytes=file_path.stat().st_size,
        )

        # Parse components
        package.connection_managers = self._parse_connection_managers(root)
        package.variables = self._parse_variables(root)

        # Parse executables (tasks)
        self._parse_executables(root, package)

        # Parse precedence constraints
        package.precedence_constraints = self._parse_precedence_constraints(root)

        return package

    def _parse_connection_managers(
        self, root: etree._Element
    ) -> list[ConnectionManager]:
        """Extract connection managers from package."""
        managers = []
        ns = NAMESPACES["DTS"]

        for cm in root.findall(f".//{{{ns}}}ConnectionManager"):
            conn_str = ""
            obj_data = cm.find(f"{{{ns}}}ObjectData/{{{ns}}}ConnectionManager")
            if obj_data is not None:
                conn_str = obj_data.get(f"{{{ns}}}ConnectionString", "")

            manager = ConnectionManager(
                id=cm.get(f"{{{ns}}}DTSID", ""),
                name=cm.get(f"{{{ns}}}ObjectName", ""),
                description=cm.get(f"{{{ns}}}Description"),
                connection_string=conn_str,
                server=self._extract_server_from_conn_string(conn_str),
                database=self._extract_database_from_conn_string(conn_str),
                provider=self._extract_provider_from_conn_string(conn_str),
            )
            managers.append(manager)

        return managers

    def _parse_variables(self, root: etree._Element) -> list[Variable]:
        """Extract variables from package."""
        variables = []
        ns = NAMESPACES["DTS"]

        for var in root.findall(f".//{{{ns}}}Variable"):
            value_elem = var.find(f"{{{ns}}}VariableValue")
            value = value_elem.text if value_elem is not None else None
            data_type_code = (
                value_elem.get(f"{{{ns}}}DataType", "8")
                if value_elem is not None
                else "8"
            )

            variable = Variable(
                namespace=var.get(f"{{{ns}}}Namespace", "User"),
                name=var.get(f"{{{ns}}}ObjectName", ""),
                data_type=VARIABLE_DATA_TYPES.get(data_type_code, "DT_WSTR"),
                value=value,
                expression=var.get(f"{{{ns}}}Expression"),
                description=var.get(f"{{{ns}}}Description"),
            )
            variables.append(variable)

        return variables

    def _parse_executables(
        self, root: etree._Element, package: SSISPackage
    ) -> None:
        """Parse all executable elements (tasks and containers)."""
        ns = NAMESPACES["DTS"]

        for executable in root.findall(f".//{{{ns}}}Executable"):
            exec_type = executable.get(f"{{{ns}}}ExecutableType", "")
            task_name = executable.get(f"{{{ns}}}ObjectName", "")

            if exec_type == "Microsoft.ExecuteSQLTask":
                task = self._parse_execute_sql_task(executable)
                if task:
                    package.execute_sql_tasks.append(task)

            elif exec_type == "Microsoft.Pipeline":
                task = self._parse_data_flow_task(executable)
                if task:
                    package.data_flow_tasks.append(task)

            elif exec_type == "Microsoft.ScriptTask":
                task = self._parse_script_task(executable)
                if task:
                    package.script_tasks.append(task)
                    package.parsing_warnings.append(
                        f"Script Task '{task.name}' flagged for manual review"
                    )

            elif exec_type == "Microsoft.SendMailTask":
                task = self._parse_send_mail_task(executable)
                if task:
                    package.send_mail_tasks.append(task)
                    package.parsing_warnings.append(
                        f"Send Mail Task '{task.name}' will not be converted"
                    )

            elif exec_type in MANUAL_REVIEW_TASKS:
                package.parsing_warnings.append(
                    f"Task '{task_name}' ({exec_type}) flagged: {MANUAL_REVIEW_TASKS[exec_type]}"
                )

    def _parse_execute_sql_task(
        self, executable: etree._Element
    ) -> ExecuteSQLTask | None:
        """Parse an Execute SQL Task."""
        ns_dts = NAMESPACES["DTS"]
        ns_sql = NAMESPACES["SQLTask"]

        sql_data = executable.find(f".//{{{ns_sql}}}SqlTaskData")
        if sql_data is None:
            return None

        return ExecuteSQLTask(
            name=executable.get(f"{{{ns_dts}}}ObjectName", ""),
            description=executable.get(f"{{{ns_dts}}}Description"),
            connection_manager=sql_data.get(f"{{{ns_sql}}}Connection", ""),
            sql_statement=sql_data.get(f"{{{ns_sql}}}SqlStatementSource", ""),
            result_set=sql_data.get(f"{{{ns_sql}}}ResultType", "None"),
        )

    def _parse_data_flow_task(
        self, executable: etree._Element
    ) -> DataFlowTask | None:
        """Parse a Data Flow Task with all components."""
        ns = NAMESPACES["DTS"]

        task = DataFlowTask(
            name=executable.get(f"{{{ns}}}ObjectName", ""),
            description=executable.get(f"{{{ns}}}Description"),
        )

        pipeline = executable.find(".//pipeline")
        if pipeline is None:
            return task

        for component in pipeline.findall(".//component"):
            comp_class = component.get("componentClassID", "")

            if comp_class == "Microsoft.OLEDBSource":
                source = self._parse_oledb_source(component)
                if source:
                    task.sources.append(source)
                    self._add_table_to_metadata(source.table_name, source.columns, task.name)

            elif comp_class == "Microsoft.OLEDBDestination":
                dest = self._parse_oledb_destination(component)
                if dest:
                    task.destinations.append(dest)
                    self._add_table_to_metadata(dest.table_name, [], task.name)

            elif comp_class == "Microsoft.Lookup":
                lookup = self._parse_lookup_transform(component)
                if lookup:
                    task.lookups.append(lookup)

            elif comp_class == "Microsoft.DerivedColumn":
                derived_cols = self._parse_derived_column(component)
                task.derived_columns.extend(derived_cols)

        return task

    def _parse_oledb_source(self, component: etree._Element) -> DataFlowSource | None:
        """Parse OLE DB Source component."""
        sql_command = None
        table_name = None

        for prop in component.findall(".//property"):
            prop_name = prop.get("name", "")
            if prop_name == "SqlCommand":
                sql_command = prop.text
            elif prop_name == "OpenRowset":
                table_name = prop.text

        # Extract column metadata
        columns = []
        for col in component.findall(".//outputColumn"):
            length = col.get("length")
            precision = col.get("precision")
            scale = col.get("scale")

            col_info = ColumnInfo(
                name=col.get("name", ""),
                ssis_type=col.get("dataType", "wstr"),
                sql_type=map_ssis_type_to_sql(
                    col.get("dataType", "wstr"),
                    length=int(length) if length else None,
                    precision=int(precision) if precision else None,
                    scale=int(scale) if scale else None,
                ),
                length=int(length) if length else None,
                precision=int(precision) if precision else None,
                scale=int(scale) if scale else None,
            )
            columns.append(col_info)

        # Get connection manager reference
        conn_ref = None
        conn_elem = component.find(".//connection")
        if conn_elem is not None:
            conn_ref = conn_elem.get("connectionManagerRefId", "")

        return DataFlowSource(
            name=component.get("name", ""),
            component_type="OLEDBSource",
            description=component.get("description"),
            connection_manager=conn_ref,
            sql_command=sql_command,
            table_name=table_name,
            columns=columns,
        )

    def _parse_oledb_destination(
        self, component: etree._Element
    ) -> DataFlowDestination | None:
        """Parse OLE DB Destination component."""
        table_name = None
        for prop in component.findall(".//property"):
            if prop.get("name") == "OpenRowset":
                table_name = prop.text

        conn_ref = None
        conn_elem = component.find(".//connection")
        if conn_elem is not None:
            conn_ref = conn_elem.get("connectionManagerRefId", "")

        return DataFlowDestination(
            name=component.get("name", ""),
            component_type="OLEDBDestination",
            description=component.get("description"),
            connection_manager=conn_ref,
            table_name=table_name,
        )

    def _parse_lookup_transform(
        self, component: etree._Element
    ) -> LookupTransform | None:
        """Parse Lookup transformation (represents JOINs)."""
        sql_command = None
        cache_type = "Full"
        no_match_behavior = "FailComponent"

        for prop in component.findall(".//property"):
            prop_name = prop.get("name", "")
            if prop_name == "SqlCommand":
                sql_command = prop.text
            elif prop_name == "CacheType":
                cache_type = "Full" if prop.text == "0" else "Partial"
            elif prop_name == "NoMatchBehavior":
                no_match_behavior = (
                    "FailComponent" if prop.text == "0" else "IgnoreFailure"
                )

        conn_ref = None
        conn_elem = component.find(".//connection")
        if conn_elem is not None:
            conn_ref = conn_elem.get("connectionManagerRefId", "")

        # Extract output columns
        output_columns = []
        for col in component.findall(".//outputColumn"):
            output_columns.append(col.get("name", ""))

        return LookupTransform(
            name=component.get("name", ""),
            description=component.get("description"),
            connection_manager=conn_ref or "",
            sql_command=sql_command,
            cache_mode=cache_type,
            no_match_behavior=no_match_behavior,
            output_columns=output_columns,
        )

    def _parse_derived_column(
        self, component: etree._Element
    ) -> list[DerivedColumnDef]:
        """Parse Derived Column transformation."""
        derived_cols = []

        for col in component.findall(".//outputColumn"):
            expression = None
            friendly_expression = None

            for prop in col.findall(".//property"):
                prop_name = prop.get("name", "")
                if prop_name == "Expression":
                    expression = prop.text
                elif prop_name == "FriendlyExpression":
                    friendly_expression = prop.text

            if expression:
                length = col.get("length")
                derived_cols.append(
                    DerivedColumnDef(
                        name=col.get("name", ""),
                        expression=expression,
                        friendly_expression=friendly_expression,
                        output_type=col.get("dataType", "wstr"),
                        output_length=int(length) if length else None,
                    )
                )

        return derived_cols

    def _parse_script_task(self, executable: etree._Element) -> ScriptTask:
        """Parse Script Task and flag for manual review."""
        ns = NAMESPACES["DTS"]

        # Try to extract variable info from script project
        read_only_vars = []
        read_write_vars = []
        script_lang = "CSharp"

        script_project = executable.find(".//ScriptProject")
        if script_project is not None:
            script_lang = script_project.get("Language", "CSharp")
            ro_vars = script_project.find("ReadOnlyVariables")
            if ro_vars is not None and ro_vars.text:
                read_only_vars = [v.strip() for v in ro_vars.text.split(",")]
            rw_vars = script_project.find("ReadWriteVariables")
            if rw_vars is not None and rw_vars.text:
                read_write_vars = [v.strip() for v in rw_vars.text.split(",")]

        return ScriptTask(
            name=executable.get(f"{{{ns}}}ObjectName", ""),
            description=executable.get(f"{{{ns}}}Description"),
            script_language=script_lang,
            read_only_variables=read_only_vars,
            read_write_variables=read_write_vars,
            manual_review_required=True,
            review_reason="Script Tasks require manual conversion to dbt macros or Python",
        )

    def _parse_send_mail_task(self, executable: etree._Element) -> SendMailTask:
        """Parse Send Mail Task - document but don't convert."""
        ns_dts = NAMESPACES["DTS"]
        ns_mail = NAMESPACES.get("SendMailTask", "www.microsoft.com/sqlserver/dts/tasks/sendmailtask")

        mail_data = executable.find(f".//{{{ns_mail}}}SendMailTaskData")

        smtp_server = None
        from_addr = None
        to_addr = None
        subject = None
        message = None

        if mail_data is not None:
            smtp_server = mail_data.get(f"{{{ns_mail}}}SMTPServer")
            from_addr = mail_data.get(f"{{{ns_mail}}}From")
            to_addr = mail_data.get(f"{{{ns_mail}}}To")
            subject = mail_data.get(f"{{{ns_mail}}}Subject")
            message = mail_data.get(f"{{{ns_mail}}}MessageSource")

        return SendMailTask(
            name=executable.get(f"{{{ns_dts}}}ObjectName", ""),
            description=executable.get(f"{{{ns_dts}}}Description"),
            smtp_server=smtp_server,
            from_address=from_addr,
            to_address=to_addr,
            subject=subject,
            message_source=message,
        )

    def _parse_precedence_constraints(
        self, root: etree._Element
    ) -> list[PrecedenceConstraint]:
        """Parse precedence constraints (task execution order)."""
        constraints = []
        ns = NAMESPACES["DTS"]

        for constraint in root.findall(f".//{{{ns}}}PrecedenceConstraint"):
            from_task = constraint.get(f"{{{ns}}}From", "")
            to_task = constraint.get(f"{{{ns}}}To", "")

            # Clean up task paths (remove "Package\" prefix)
            from_task = from_task.replace("Package\\", "")
            to_task = to_task.replace("Package\\", "")

            constraints.append(
                PrecedenceConstraint(
                    from_task=from_task,
                    to_task=to_task,
                    constraint_type="Success",
                )
            )

        return constraints

    def _add_table_to_metadata(
        self, table_name: str | None, columns: list[ColumnInfo], task_name: str
    ) -> None:
        """Add table and column info to schema metadata."""
        if not table_name:
            return

        # Parse schema and table name
        clean_name = table_name.strip("[]")
        parts = clean_name.split(".")
        if len(parts) >= 2:
            schema_name = parts[-2].strip("[]")
            tbl_name = parts[-1].strip("[]")
        else:
            schema_name = None
            tbl_name = clean_name

        full_name = f"{schema_name}.{tbl_name}" if schema_name else tbl_name

        # Add table if not seen
        if full_name not in self._tables_seen:
            self._tables_seen.add(full_name)
            self.schema_metadata.tables.append(
                SchemaTable(
                    schema_name=schema_name,
                    table_name=tbl_name,
                    full_name=full_name,
                    referenced_in=[task_name],
                )
            )
        else:
            # Update referenced_in
            for tbl in self.schema_metadata.tables:
                if tbl.full_name == full_name and task_name not in tbl.referenced_in:
                    tbl.referenced_in.append(task_name)

        # Add columns
        for col in columns:
            self.schema_metadata.columns.append(
                SchemaColumn(
                    table_full_name=full_name,
                    column_name=col.name,
                    ssis_type=col.ssis_type,
                    sql_type=col.sql_type,
                    length=col.length,
                    precision=col.precision,
                    scale=col.scale,
                )
            )

    # Helper methods for connection string parsing
    def _extract_server_from_conn_string(self, conn_str: str) -> str | None:
        """Extract server name from connection string."""
        for part in conn_str.split(";"):
            if "Data Source=" in part:
                return part.split("=", 1)[1]
        return None

    def _extract_database_from_conn_string(self, conn_str: str) -> str | None:
        """Extract database name from connection string."""
        for part in conn_str.split(";"):
            if "Initial Catalog=" in part:
                return part.split("=", 1)[1]
        return None

    def _extract_provider_from_conn_string(self, conn_str: str) -> str | None:
        """Extract provider from connection string."""
        for part in conn_str.split(";"):
            if "Provider=" in part:
                return part.split("=", 1)[1]
        return None

    def get_parsing_result(self) -> ParsingResult:
        """Build complete parsing result with statistics."""
        result = ParsingResult(
            packages=self.packages,
            schema_metadata=self.schema_metadata,
            total_packages=len(self.packages),
            total_execute_sql_tasks=sum(
                len(p.execute_sql_tasks) for p in self.packages
            ),
            total_data_flow_tasks=sum(len(p.data_flow_tasks) for p in self.packages),
            total_script_tasks=sum(len(p.script_tasks) for p in self.packages),
            total_warnings=sum(len(p.parsing_warnings) for p in self.packages),
            total_errors=sum(len(p.parsing_errors) for p in self.packages),
        )
        return result

    def export_json(self, output_dir: str | Path) -> None:
        """Export parsed packages to JSON files."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Export parsed_packages.json
        packages_data = [pkg.model_dump() for pkg in self.packages]
        with open(output_dir / "parsed_packages.json", "w") as f:
            json.dump(packages_data, f, indent=2, default=str)

        if self.verbose:
            console.print(f"[green]✓ Exported parsed_packages.json[/green]")

        # Export schema_metadata.json
        schema_data = self.schema_metadata.model_dump()
        with open(output_dir / "schema_metadata.json", "w") as f:
            json.dump(schema_data, f, indent=2)

        if self.verbose:
            console.print(f"[green]✓ Exported schema_metadata.json[/green]")

    def generate_report(self, output_dir: str | Path) -> None:
        """Generate parsing_report.md with summary statistics."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        result = self.get_parsing_result()

        report_lines = [
            "# SSIS Package Parsing Report",
            "",
            f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Summary",
            "",
            f"| Metric | Count |",
            f"|--------|-------|",
            f"| Total Packages Parsed | {result.total_packages} |",
            f"| Execute SQL Tasks | {result.total_execute_sql_tasks} |",
            f"| Data Flow Tasks | {result.total_data_flow_tasks} |",
            f"| Script Tasks (Manual Review) | {result.total_script_tasks} |",
            f"| Tables Referenced | {len(self.schema_metadata.tables)} |",
            f"| Total Warnings | {result.total_warnings} |",
            "",
        ]

        # Package details
        report_lines.append("## Package Details")
        report_lines.append("")

        for pkg in self.packages:
            size_kb = pkg.file_size_bytes / 1024
            report_lines.extend(
                [
                    f"### {pkg.name}",
                    "",
                    f"- **File**: `{os.path.basename(pkg.file_path)}`",
                    f"- **Size**: {size_kb:.1f} KB",
                    f"- **Description**: {pkg.description or 'N/A'}",
                    f"- **Creator**: {pkg.creator_name or 'N/A'}",
                    f"- **Created**: {pkg.creation_date or 'N/A'}",
                    "",
                    "#### Components",
                    "",
                    f"| Component Type | Count |",
                    f"|----------------|-------|",
                    f"| Connection Managers | {len(pkg.connection_managers)} |",
                    f"| Variables | {len(pkg.variables)} |",
                    f"| Execute SQL Tasks | {len(pkg.execute_sql_tasks)} |",
                    f"| Data Flow Tasks | {len(pkg.data_flow_tasks)} |",
                    f"| Script Tasks | {len(pkg.script_tasks)} |",
                    f"| Send Mail Tasks | {len(pkg.send_mail_tasks)} |",
                    "",
                ]
            )

            # Connection managers
            if pkg.connection_managers:
                report_lines.append("#### Connection Managers")
                report_lines.append("")
                for cm in pkg.connection_managers:
                    report_lines.append(
                        f"- **{cm.name}**: `{cm.server or 'N/A'}` / `{cm.database or 'N/A'}`"
                    )
                report_lines.append("")

            # Warnings
            if pkg.parsing_warnings:
                report_lines.append("#### Warnings")
                report_lines.append("")
                for warning in pkg.parsing_warnings:
                    report_lines.append(f"- ⚠️ {warning}")
                report_lines.append("")

            # Task execution order
            if pkg.precedence_constraints:
                report_lines.append("#### Execution Order")
                report_lines.append("")
                report_lines.append("```")
                for pc in pkg.precedence_constraints:
                    report_lines.append(f"{pc.from_task} → {pc.to_task}")
                report_lines.append("```")
                report_lines.append("")

        # Schema summary
        if self.schema_metadata.tables:
            report_lines.append("## Tables Referenced")
            report_lines.append("")
            report_lines.append("| Table | Referenced In |")
            report_lines.append("|-------|---------------|")
            for tbl in self.schema_metadata.tables:
                refs = ", ".join(tbl.referenced_in)
                report_lines.append(f"| `{tbl.full_name}` | {refs} |")
            report_lines.append("")

        with open(output_dir / "parsing_report.md", "w") as f:
            f.write("\n".join(report_lines))

        if self.verbose:
            console.print(f"[green]✓ Generated parsing_report.md[/green]")

    def print_summary(self) -> None:
        """Print a summary table to the console."""
        result = self.get_parsing_result()

        table = Table(title="SSIS Parsing Summary")
        table.add_column("Package", style="cyan")
        table.add_column("SQL Tasks", justify="right")
        table.add_column("Data Flows", justify="right")
        table.add_column("Script Tasks", justify="right", style="yellow")
        table.add_column("Warnings", justify="right", style="red")

        for pkg in self.packages:
            table.add_row(
                pkg.name,
                str(len(pkg.execute_sql_tasks)),
                str(len(pkg.data_flow_tasks)),
                str(len(pkg.script_tasks)),
                str(len(pkg.parsing_warnings)),
            )

        console.print(table)
        console.print()
        console.print(f"[bold]Total Packages:[/bold] {result.total_packages}")
        console.print(
            f"[bold]Total Tasks:[/bold] {result.total_execute_sql_tasks + result.total_data_flow_tasks}"
        )
        console.print(
            f"[bold yellow]Manual Review Required:[/bold yellow] {result.total_script_tasks} script task(s)"
        )


def main():
    """CLI entry point for SSIS parser."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Parse SSIS packages (.dtsx) to JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.parser.ssis_parser ./samples/ssis_packages
  python -m src.parser.ssis_parser ./packages -o ./output -v
        """,
    )
    parser.add_argument("input_dir", help="Directory containing .dtsx files")
    parser.add_argument(
        "-o", "--output", default="output", help="Output directory (default: output)"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    console.print("[bold blue]SSIS Package Parser[/bold blue]")
    console.print()

    ssis_parser = SSISParser(verbose=args.verbose)
    ssis_parser.parse_directory(args.input_dir)

    if not ssis_parser.packages:
        console.print("[yellow]No packages found to parse.[/yellow]")
        return

    ssis_parser.print_summary()
    ssis_parser.export_json(args.output)
    ssis_parser.generate_report(args.output)

    console.print()
    console.print(f"[green bold]✓ Parsing complete![/green bold]")
    console.print(f"  Output saved to: {args.output}/")


if __name__ == "__main__":
    main()
