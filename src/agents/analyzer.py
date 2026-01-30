"""Analyzer Agent - Parses and understands SSIS packages."""

import re
from pathlib import Path
from typing import Any, Optional

from ..parser.ssis_parser import SSISParser
from ..parser.models import (
    SSISPackage,
    DataFlowTask,
    ExecuteSQLTask,
    Variable,
    PrecedenceConstraint,
)
from .base import (
    BaseAgent,
    AgentResult,
    AgentStatus,
    LoadPattern,
    LoadPatternDetails,
)
from .context import MigrationContext


class DependencyNode:
    """Node in the task dependency graph."""

    def __init__(self, task_id: str, task_name: str, task_type: str):
        self.task_id = task_id
        self.task_name = task_name
        self.task_type = task_type
        self.dependencies: list[str] = []
        self.dependents: list[str] = []


class DependencyGraph:
    """Graph of task dependencies from precedence constraints."""

    def __init__(self):
        self.nodes: dict[str, DependencyNode] = {}

    def add_node(self, task_id: str, task_name: str, task_type: str) -> None:
        if task_id not in self.nodes:
            self.nodes[task_id] = DependencyNode(task_id, task_name, task_type)

    def add_edge(self, from_id: str, to_id: str) -> None:
        if from_id in self.nodes and to_id in self.nodes:
            self.nodes[from_id].dependents.append(to_id)
            self.nodes[to_id].dependencies.append(from_id)

    def get_execution_order(self) -> list[str]:
        """Get topologically sorted execution order."""
        visited: set[str] = set()
        order: list[str] = []

        def visit(node_id: str) -> None:
            if node_id in visited:
                return
            visited.add(node_id)
            for dep in self.nodes[node_id].dependencies:
                visit(dep)
            order.append(node_id)

        for node_id in self.nodes:
            visit(node_id)

        return order

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [
                {
                    "id": n.task_id,
                    "name": n.task_name,
                    "type": n.task_type,
                    "dependencies": n.dependencies,
                    "dependents": n.dependents,
                }
                for n in self.nodes.values()
            ],
            "execution_order": self.get_execution_order(),
        }


class AnalysisResult:
    """Result of package analysis."""

    def __init__(self):
        self.packages: list[dict[str, Any]] = []
        self.load_patterns: dict[str, LoadPatternDetails] = {}
        self.dependency_graphs: dict[str, DependencyGraph] = {}
        self.sql_analyses: dict[str, dict[str, Any]] = {}
        self.manual_review_items: list[dict[str, Any]] = []
        self.warnings: list[str] = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "packages": self.packages,
            "load_patterns": {
                name: pattern.model_dump()
                for name, pattern in self.load_patterns.items()
            },
            "dependency_graphs": {
                name: graph.to_dict()
                for name, graph in self.dependency_graphs.items()
            },
            "sql_analyses": self.sql_analyses,
            "manual_review_items": self.manual_review_items,
            "warnings": self.warnings,
        }


class AnalyzerAgent(BaseAgent):
    """
    Analyzes SSIS packages to understand their structure and patterns.

    Responsibilities:
    - Parse SSIS packages using existing SSISParser
    - Detect load patterns (incremental vs full load)
    - Use LLM to understand complex SQL transformations
    - Build dependency graph from precedence constraints
    - Flag items requiring manual review
    """

    # Patterns indicating incremental loads
    INCREMENTAL_VARIABLE_PATTERNS = [
        r"lastsync",
        r"lastrun",
        r"lastload",
        r"modified",
        r"updated",
        r"incremental",
        r"delta",
        r"watermark",
    ]

    INCREMENTAL_SQL_PATTERNS = [
        r"WHERE.*>=\s*[@?]",  # Parameterized date filters
        r"WHERE.*ModifiedDate",
        r"WHERE.*UpdatedAt",
        r"WHERE.*LastModified",
        r"SyncLog",
        r"etl\..*Log",
        r"audit\.",
    ]

    SCD_PATTERNS = [
        r"\bMERGE\b",
        r"WHEN\s+MATCHED",
        r"WHEN\s+NOT\s+MATCHED",
        r"SCD",
        r"Type\s*2",
        r"valid_from",
        r"valid_to",
        r"is_current",
    ]

    def __init__(
        self,
        context: MigrationContext,
        llm_client: Optional[Any] = None,
    ):
        super().__init__(context)
        self.parser = SSISParser(verbose=True)
        self.llm_client = llm_client

    async def execute(self, input_data: dict[str, Any]) -> AgentResult:
        """
        Execute the analysis pipeline.

        Args:
            input_data: Must contain "package_paths" - list of paths to analyze

        Returns:
            AgentResult with analysis data
        """
        self.status = AgentStatus.RUNNING
        self.log("Starting SSIS package analysis")

        try:
            package_paths = input_data.get("package_paths", [])
            if not package_paths:
                return AgentResult(
                    success=False,
                    status=AgentStatus.FAILED,
                    errors=["No package paths provided"],
                )

            result = AnalysisResult()

            # Parse all packages
            for path in package_paths:
                self.log(f"Parsing packages in: {path}")
                packages = self.parser.parse_directory(path)

                for package in packages:
                    self.log(f"Analyzing package: {package.name}")

                    # Convert to dict for storage
                    package_dict = package.model_dump()
                    result.packages.append(package_dict)

                    # Detect load pattern
                    pattern = await self._detect_load_pattern(package)
                    result.load_patterns[package.name] = pattern

                    # Build dependency graph
                    graph = self._build_dependency_graph(package)
                    result.dependency_graphs[package.name] = graph

                    # Analyze SQL statements (with LLM if available)
                    sql_analysis = await self._analyze_sql_statements(package)
                    result.sql_analyses[package.name] = sql_analysis

                    # Flag items for manual review
                    manual_items = self._find_manual_review_items(package)
                    result.manual_review_items.extend(manual_items)

            # Add any parsing warnings
            result.warnings = self.parser.get_parsing_result().validation_log

            self.log(f"Analysis complete: {len(result.packages)} packages analyzed")
            self.status = AgentStatus.COMPLETED

            return AgentResult(
                success=True,
                status=AgentStatus.COMPLETED,
                data=result.to_dict(),
                warnings=result.warnings,
            )

        except Exception as e:
            self.status = AgentStatus.FAILED
            return AgentResult(
                success=False,
                status=AgentStatus.FAILED,
                errors=[str(e)],
            )

    async def _detect_load_pattern(
        self, package: SSISPackage
    ) -> LoadPatternDetails:
        """Detect the load pattern of a package."""
        indicators: list[str] = []
        variables_used: list[str] = []
        date_columns: list[str] = []
        sync_table: Optional[str] = None

        # Check variables for incremental indicators
        for var in package.variables:
            var_name_lower = var.name.lower()
            for pattern in self.INCREMENTAL_VARIABLE_PATTERNS:
                if re.search(pattern, var_name_lower, re.IGNORECASE):
                    indicators.append(f"Variable '{var.name}' suggests incremental")
                    variables_used.append(var.name)
                    break

        # Check SQL statements
        all_sql = self._collect_all_sql(package)
        for sql_name, sql_text in all_sql.items():
            sql_lower = sql_text.lower()

            # Check for incremental patterns
            for pattern in self.INCREMENTAL_SQL_PATTERNS:
                if re.search(pattern, sql_text, re.IGNORECASE):
                    indicators.append(f"SQL '{sql_name}' has incremental pattern")

                    # Extract date columns
                    date_match = re.search(
                        r"WHERE.*?(\w+Date|\w+Time|\w+At)\s*>=",
                        sql_text,
                        re.IGNORECASE,
                    )
                    if date_match:
                        date_columns.append(date_match.group(1))

                    # Check for sync table
                    sync_match = re.search(
                        r"(?:FROM|INTO|UPDATE)\s+(\w+\.?\w*(?:Sync|Log|Audit)\w*)",
                        sql_text,
                        re.IGNORECASE,
                    )
                    if sync_match:
                        sync_table = sync_match.group(1)
                    break

            # Check for SCD/MERGE patterns
            for pattern in self.SCD_PATTERNS:
                if re.search(pattern, sql_text, re.IGNORECASE):
                    indicators.append(f"SQL '{sql_name}' has SCD/MERGE pattern")
                    break

        # Determine pattern based on indicators
        if any("SCD" in ind or "MERGE" in ind for ind in indicators):
            pattern = LoadPattern.MERGE_SCD
            confidence = 0.9
        elif len(indicators) >= 2:
            pattern = LoadPattern.INCREMENTAL
            confidence = min(0.9, 0.5 + 0.1 * len(indicators))
        elif len(indicators) == 1:
            pattern = LoadPattern.INCREMENTAL
            confidence = 0.6
        else:
            pattern = LoadPattern.FULL_LOAD
            confidence = 0.7

        # Use LLM for enhanced detection if available
        if self.llm_client and confidence < 0.8:
            try:
                llm_result = await self.llm_client.detect_load_pattern(
                    package.model_dump()
                )
                if llm_result.get("confidence", 0) > confidence:
                    pattern = LoadPattern(llm_result.get("pattern", pattern.value))
                    confidence = llm_result.get("confidence", confidence)
                    indicators.extend(llm_result.get("indicators", []))
            except Exception as e:
                self.log(f"LLM pattern detection failed: {e}")

        return LoadPatternDetails(
            pattern=pattern,
            confidence=confidence,
            indicators=list(set(indicators)),
            variables_used=list(set(variables_used)),
            date_columns=list(set(date_columns)),
            sync_table=sync_table,
        )

    def _collect_all_sql(self, package: SSISPackage) -> dict[str, str]:
        """Collect all SQL statements from the package."""
        sql_statements: dict[str, str] = {}

        # From Execute SQL Tasks
        for task in package.execute_sql_tasks:
            if task.sql_statement:
                sql_statements[task.name] = task.sql_statement

        # From Data Flow sources
        for df_task in package.data_flow_tasks:
            for source in df_task.sources:
                if source.sql_command:
                    sql_statements[f"{df_task.name}.{source.name}"] = source.sql_command

            # From Lookup transforms
            for lookup in df_task.lookups:
                if lookup.sql_command:
                    sql_statements[f"{df_task.name}.{lookup.name}"] = lookup.sql_command

        return sql_statements

    def _build_dependency_graph(self, package: SSISPackage) -> DependencyGraph:
        """Build task dependency graph from precedence constraints."""
        graph = DependencyGraph()

        # Add all tasks as nodes
        for task in package.execute_sql_tasks:
            graph.add_node(task.name, task.name, "ExecuteSQLTask")

        for task in package.data_flow_tasks:
            graph.add_node(task.name, task.name, "DataFlowTask")

        for task in package.script_tasks:
            graph.add_node(task.name, task.name, "ScriptTask")

        # Add edges from precedence constraints
        for constraint in package.precedence_constraints:
            graph.add_edge(constraint.from_task, constraint.to_task)

        return graph

    async def _analyze_sql_statements(
        self, package: SSISPackage
    ) -> dict[str, Any]:
        """Analyze SQL statements for understanding transformations."""
        analyses: dict[str, Any] = {}
        all_sql = self._collect_all_sql(package)

        for sql_name, sql_text in all_sql.items():
            analysis = self._basic_sql_analysis(sql_text)

            # Use LLM for complex SQL if available
            if self.llm_client and analysis.get("complexity") == "complex":
                try:
                    llm_analysis = await self.llm_client.analyze_sql(sql_text)
                    analysis["llm_analysis"] = llm_analysis
                except Exception as e:
                    self.log(f"LLM SQL analysis failed for {sql_name}: {e}")

            analyses[sql_name] = analysis

        return analyses

    def _basic_sql_analysis(self, sql: str) -> dict[str, Any]:
        """Perform basic SQL analysis without LLM."""
        sql_upper = sql.upper().strip()

        # Determine statement type
        if sql_upper.startswith("SELECT"):
            stmt_type = "SELECT"
        elif sql_upper.startswith("INSERT"):
            stmt_type = "INSERT"
        elif sql_upper.startswith("UPDATE"):
            stmt_type = "UPDATE"
        elif sql_upper.startswith("DELETE"):
            stmt_type = "DELETE"
        elif sql_upper.startswith("MERGE"):
            stmt_type = "MERGE"
        elif sql_upper.startswith("TRUNCATE"):
            stmt_type = "TRUNCATE"
        else:
            stmt_type = "OTHER"

        # Extract tables (basic regex)
        table_pattern = r"(?:FROM|JOIN|INTO|UPDATE|MERGE\s+INTO?)\s+(\[?\w+\]?\.?\[?\w+\]?)"
        tables = re.findall(table_pattern, sql, re.IGNORECASE)

        # Check for JOINs
        has_joins = bool(re.search(r"\bJOIN\b", sql, re.IGNORECASE))

        # Check for aggregations
        has_aggregations = bool(
            re.search(r"\b(SUM|COUNT|AVG|MIN|MAX|GROUP BY)\b", sql, re.IGNORECASE)
        )

        # Check for subqueries
        has_subqueries = sql.count("SELECT") > 1

        # Determine complexity
        complexity_score = sum([
            has_joins,
            has_aggregations,
            has_subqueries,
            len(tables) > 3,
            len(sql) > 500,
        ])
        complexity = (
            "simple" if complexity_score <= 1
            else "moderate" if complexity_score <= 3
            else "complex"
        )

        return {
            "statement_type": stmt_type,
            "tables": list(set(tables)),
            "has_joins": has_joins,
            "has_aggregations": has_aggregations,
            "has_subqueries": has_subqueries,
            "complexity": complexity,
            "length": len(sql),
        }

    def _find_manual_review_items(
        self, package: SSISPackage
    ) -> list[dict[str, Any]]:
        """Find items that require manual review."""
        items: list[dict[str, Any]] = []

        # Script tasks always need review
        for task in package.script_tasks:
            items.append({
                "package": package.name,
                "task": task.name,
                "type": "ScriptTask",
                "reason": "Script tasks contain custom code that cannot be auto-converted",
                "language": task.script_language,
            })

        # Complex SQL might need review
        for sql_task in package.execute_sql_tasks:
            if sql_task.sql_statement:
                analysis = self._basic_sql_analysis(sql_task.sql_statement)
                if analysis["complexity"] == "complex":
                    items.append({
                        "package": package.name,
                        "task": sql_task.name,
                        "type": "ExecuteSQLTask",
                        "reason": "Complex SQL requires manual verification",
                        "complexity": analysis["complexity"],
                    })

        # Send mail tasks
        for task in package.send_mail_tasks:
            items.append({
                "package": package.name,
                "task": task.name,
                "type": "SendMailTask",
                "reason": "Email notifications should be handled by dbt notifications or orchestrator",
            })

        return items
