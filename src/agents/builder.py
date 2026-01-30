"""Builder Agent - Generates dbt models from SSIS analysis."""

import re
from typing import Any, Optional

from ..parser.type_mappings import get_snake_case, map_ssis_type_to_sql
from .base import (
    BaseAgent,
    AgentResult,
    AgentStatus,
    GeneratedFile,
    LoadPattern,
)
from .context import MigrationContext


class BuilderAgent(BaseAgent):
    """
    Generates dbt models from analyzed SSIS packages.

    Responsibilities:
    - Generate staging models from Data Flow Tasks
    - Generate core models from Execute SQL Tasks
    - Map SSIS expressions to SQL
    - Convert Lookup transforms to JOINs
    - Create YAML schema files with tests
    """

    def __init__(
        self,
        context: MigrationContext,
        llm_client: Optional[Any] = None,
    ):
        super().__init__(context)
        self.llm_client = llm_client
        self.generated_files: list[GeneratedFile] = []
        self.model_mappings: dict[str, dict[str, Any]] = {}

    async def execute(self, input_data: dict[str, Any]) -> AgentResult:
        """
        Generate dbt models from analysis results.

        Args:
            input_data: Must contain "analysis" - output from AnalyzerAgent

        Returns:
            AgentResult with generated files (not written to disk yet)
        """
        self.status = AgentStatus.RUNNING
        self.log("Starting dbt model generation")

        try:
            analysis = input_data.get("analysis", {})
            if not analysis:
                return AgentResult(
                    success=False,
                    status=AgentStatus.FAILED,
                    errors=["No analysis data provided"],
                )

            packages = analysis.get("packages", [])
            load_patterns = analysis.get("load_patterns", {})

            for package in packages:
                package_name = package.get("name", "unknown")
                self.log(f"Generating models for package: {package_name}")

                pattern = load_patterns.get(package_name, {})
                load_pattern = LoadPattern(
                    pattern.get("pattern", "full_load")
                )

                # Generate staging models from Data Flow Tasks
                for df_task in package.get("data_flow_tasks", []):
                    await self._generate_staging_model(
                        df_task, package_name, load_pattern
                    )

                # Generate core models from Execute SQL Tasks
                for sql_task in package.get("execute_sql_tasks", []):
                    await self._generate_core_model(
                        sql_task, package_name, load_pattern
                    )

            # Generate source definitions
            self._generate_source_definitions(packages)

            self.log(f"Generated {len(self.generated_files)} files")
            self.status = AgentStatus.COMPLETED

            return AgentResult(
                success=True,
                status=AgentStatus.COMPLETED,
                data={
                    "files": [f.model_dump() for f in self.generated_files],
                    "model_mappings": self.model_mappings,
                    "file_count": len(self.generated_files),
                },
            )

        except Exception as e:
            self.status = AgentStatus.FAILED
            return AgentResult(
                success=False,
                status=AgentStatus.FAILED,
                errors=[str(e)],
            )

    async def _generate_staging_model(
        self,
        df_task: dict[str, Any],
        package_name: str,
        load_pattern: LoadPattern,
    ) -> None:
        """Generate a staging model from a Data Flow Task."""
        task_name = df_task.get("name", "unknown")
        sources = df_task.get("sources", [])
        derived_columns = df_task.get("derived_columns", [])
        lookups = df_task.get("lookups", [])

        if not sources:
            self.log(f"Skipping {task_name}: no sources found")
            return

        # Determine model name from source
        source = sources[0]
        source_table = source.get("table_name", "unknown")
        domain = self._extract_domain(source_table)
        entity = get_snake_case(source_table.split(".")[-1])
        model_name = f"stg_{domain}__{entity}"

        # Generate SQL
        sql_content = self._build_staging_sql(
            model_name=model_name,
            source=source,
            derived_columns=derived_columns,
            package_name=package_name,
            task_name=task_name,
        )

        self.generated_files.append(
            GeneratedFile(
                path=f"models/staging/{model_name}.sql",
                content=sql_content,
                file_type="sql",
                model_name=model_name,
                layer="staging",
            )
        )

        # Track mapping
        self.model_mappings[model_name] = {
            "ssis_package": package_name,
            "ssis_task": task_name,
            "ssis_type": "DataFlowTask",
            "source_table": source_table,
            "load_pattern": load_pattern.value,
        }

    def _build_staging_sql(
        self,
        model_name: str,
        source: dict[str, Any],
        derived_columns: list[dict[str, Any]],
        package_name: str,
        task_name: str,
    ) -> str:
        """Build the SQL content for a staging model."""
        source_table = source.get("table_name", "unknown")
        columns = source.get("columns", [])
        connection = source.get("connection_manager", "")

        # Extract schema and table
        parts = source_table.replace("[", "").replace("]", "").split(".")
        if len(parts) >= 2:
            schema_name = parts[-2]
            table_name = parts[-1]
        else:
            schema_name = "dbo"
            table_name = parts[-1]

        # Build column list
        column_lines = []
        for col in columns:
            col_name = col.get("name", "")
            ssis_type = col.get("ssis_type", "")
            sql_type = col.get("sql_type", "")

            snake_name = get_snake_case(col_name)

            if sql_type:
                column_lines.append(
                    f"        CAST({col_name} AS {sql_type}) AS {snake_name}"
                )
            else:
                column_lines.append(f"        {col_name} AS {snake_name}")

        # Add derived columns
        for derived in derived_columns:
            name = derived.get("name", "")
            expression = derived.get("expression", "")
            sql_expr = self._convert_ssis_expression(expression)
            snake_name = get_snake_case(name)
            column_lines.append(f"        {sql_expr} AS {snake_name}")

        columns_sql = ",\n".join(column_lines) if column_lines else "        *"

        sql = f'''/*
    Staging model: {model_name}
    Source: {package_name} -> {task_name} (Data Flow Task)

    Transformations applied:
    - Type casting to target SQL Server types
    - Column renaming to snake_case
    - Derived columns from SSIS transformations
*/

WITH source AS (
    SELECT *
    FROM {{{{ source('{schema_name}', '{table_name}') }}}}
)

SELECT
{columns_sql}
FROM source
'''
        return sql

    async def _generate_core_model(
        self,
        sql_task: dict[str, Any],
        package_name: str,
        load_pattern: LoadPattern,
    ) -> None:
        """Generate a core model from an Execute SQL Task."""
        task_name = sql_task.get("name", "unknown")
        sql_statement = sql_task.get("sql_statement", "")

        if not sql_statement:
            self.log(f"Skipping {task_name}: no SQL statement")
            return

        # Determine model type and name
        sql_upper = sql_statement.upper()
        if "MERGE" in sql_upper or "SCD" in task_name.upper():
            model_type = "dim"
        elif "AGG" in task_name.upper() or "AGGREGATE" in task_name.upper():
            model_type = "agg"
        elif "FACT" in task_name.upper() or "FCT" in task_name.upper():
            model_type = "fct"
        else:
            model_type = "fct"  # Default to fact

        entity = get_snake_case(
            task_name.replace("Load", "")
            .replace("Update", "")
            .replace("Insert", "")
            .strip()
        )
        model_name = f"{model_type}_{entity}"

        # Determine materialization
        if load_pattern == LoadPattern.INCREMENTAL:
            materialization = "incremental"
        else:
            materialization = "table"

        # Generate SQL (simplified - use LLM for complex cases)
        sql_content = self._build_core_sql(
            model_name=model_name,
            sql_statement=sql_statement,
            package_name=package_name,
            task_name=task_name,
            materialization=materialization,
            load_pattern=load_pattern,
        )

        self.generated_files.append(
            GeneratedFile(
                path=f"models/core/{model_name}.sql",
                content=sql_content,
                file_type="sql",
                model_name=model_name,
                layer="core",
            )
        )

        # Track mapping
        self.model_mappings[model_name] = {
            "ssis_package": package_name,
            "ssis_task": task_name,
            "ssis_type": "ExecuteSQLTask",
            "materialization": materialization,
            "load_pattern": load_pattern.value,
        }

    def _build_core_sql(
        self,
        model_name: str,
        sql_statement: str,
        package_name: str,
        task_name: str,
        materialization: str,
        load_pattern: LoadPattern,
    ) -> str:
        """Build the SQL content for a core model."""
        # Add config block
        config_lines = [f"materialized='{materialization}'"]

        if materialization == "incremental":
            config_lines.append("unique_key='id'")
            config_lines.append("incremental_strategy='merge'")

        config_str = ", ".join(config_lines)

        # Convert SSIS SQL to dbt SQL (basic conversion)
        dbt_sql = self._convert_sql_to_dbt(sql_statement)

        # Add incremental logic if needed
        incremental_block = ""
        if materialization == "incremental":
            incremental_block = """
{% if is_incremental() %}
WHERE updated_at > (SELECT MAX(updated_at) FROM {{ this }})
{% endif %}
"""

        sql = f'''{{{{
    config(
        {config_str}
    )
}}}}

/*
    Core model: {model_name}
    Source: {package_name} -> {task_name} (Execute SQL Task)
    Load Pattern: {load_pattern.value}

    Original SSIS SQL (converted):
    {sql_statement[:200]}{'...' if len(sql_statement) > 200 else ''}
*/

{dbt_sql}
{incremental_block}
'''
        return sql

    def _convert_sql_to_dbt(self, sql: str) -> str:
        """Convert SSIS SQL to dbt SQL with ref() and source()."""
        # Basic conversion - replace table references
        # In a real implementation, this would be more sophisticated
        result = sql

        # Remove INSERT/UPDATE/DELETE parts, keep SELECT
        if "SELECT" in sql.upper():
            select_start = sql.upper().find("SELECT")
            result = sql[select_start:]

            # Remove INTO clause if present
            into_match = re.search(
                r"\bINTO\s+\[?\w+\]?\.\[?\w+\]?",
                result,
                re.IGNORECASE,
            )
            if into_match:
                result = result[: into_match.start()] + result[into_match.end() :]

        return result.strip()

    def _generate_source_definitions(
        self, packages: list[dict[str, Any]]
    ) -> None:
        """Generate source YAML definitions."""
        sources_by_schema: dict[str, dict[str, Any]] = {}

        for package in packages:
            for conn in package.get("connection_managers", []):
                database = conn.get("database", "unknown_db")
                server = conn.get("server", "")

                # Collect tables from data flow sources
                for df_task in package.get("data_flow_tasks", []):
                    for source in df_task.get("sources", []):
                        table_name = source.get("table_name", "")
                        if not table_name:
                            continue

                        parts = table_name.replace("[", "").replace("]", "").split(".")
                        if len(parts) >= 2:
                            schema = parts[-2]
                            table = parts[-1]
                        else:
                            schema = "dbo"
                            table = parts[-1]

                        key = f"{database}_{schema}"
                        if key not in sources_by_schema:
                            sources_by_schema[key] = {
                                "database": database,
                                "schema": schema,
                                "tables": {},
                                "connection": conn.get("name", ""),
                            }

                        columns = source.get("columns", [])
                        sources_by_schema[key]["tables"][table] = {
                            "columns": [
                                {
                                    "name": col.get("name"),
                                    "description": "",
                                    "data_type": col.get("sql_type", ""),
                                }
                                for col in columns
                            ]
                        }

        # Generate YAML for each schema
        for key, source_info in sources_by_schema.items():
            yaml_content = self._build_source_yaml(
                source_name=key.replace("_", "_"),
                database=source_info["database"],
                schema=source_info["schema"],
                tables=source_info["tables"],
            )

            self.generated_files.append(
                GeneratedFile(
                    path=f"models/sources/src_{key.lower()}.yml",
                    content=yaml_content,
                    file_type="yaml",
                    layer="sources",
                )
            )

    def _build_source_yaml(
        self,
        source_name: str,
        database: str,
        schema: str,
        tables: dict[str, Any],
    ) -> str:
        """Build YAML content for source definitions."""
        table_entries = []
        for table_name, table_info in tables.items():
            columns_yaml = ""
            if table_info.get("columns"):
                col_lines = []
                for col in table_info["columns"]:
                    col_lines.append(
                        f"          - name: {col['name']}\n"
                        f"            data_type: {col['data_type']}"
                    )
                columns_yaml = "\n        columns:\n" + "\n".join(col_lines)

            table_entries.append(
                f"      - name: {table_name}\n"
                f"        description: 'Source table from {database}.{schema}'"
                f"{columns_yaml}"
            )

        tables_yaml = "\n".join(table_entries)

        yaml = f"""version: 2

sources:
  - name: {schema}
    description: 'Source from {database}'
    database: {database}
    schema: {schema}
    tables:
{tables_yaml}
"""
        return yaml

    def _convert_ssis_expression(self, expression: str) -> str:
        """Convert SSIS expression syntax to SQL."""
        if not expression:
            return "NULL"

        result = expression

        # Convert SSIS ISNULL to SQL ISNULL
        # SSIS: ISNULL(col) returns boolean
        # SQL: ISNULL(col, replacement)
        result = re.sub(
            r"ISNULL\(([^,)]+)\)",
            r"ISNULL(\1, '')",
            result,
            flags=re.IGNORECASE,
        )

        # Convert ternary operator: condition ? true : false
        # to CASE WHEN
        ternary_match = re.search(r"(.+?)\s*\?\s*(.+?)\s*:\s*(.+)", result)
        if ternary_match:
            condition = ternary_match.group(1).strip()
            true_val = ternary_match.group(2).strip()
            false_val = ternary_match.group(3).strip()
            result = f"CASE WHEN {condition} THEN {true_val} ELSE {false_val} END"

        # Remove SSIS type casts like (DT_WSTR,50)
        result = re.sub(r"\(DT_\w+(?:,\d+)?\)", "", result)

        return result

    def _extract_domain(self, table_name: str) -> str:
        """Extract domain from table name for model naming."""
        parts = table_name.replace("[", "").replace("]", "").split(".")
        if len(parts) >= 2:
            return parts[-2].lower()
        return "default"
