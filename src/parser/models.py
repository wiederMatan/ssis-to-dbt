"""Pydantic models for parsed SSIS package data."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    """Types of SSIS tasks/executables."""

    EXECUTE_SQL = "ExecuteSQLTask"
    DATA_FLOW = "DataFlowTask"
    SCRIPT = "ScriptTask"
    SEND_MAIL = "SendMailTask"
    FOR_EACH_LOOP = "ForEachLoopContainer"
    FOR_LOOP = "ForLoopContainer"
    SEQUENCE = "SequenceContainer"
    UNKNOWN = "Unknown"


class ColumnInfo(BaseModel):
    """Column metadata from data flow components."""

    name: str
    ssis_type: str
    sql_type: str
    length: Optional[int] = None
    precision: Optional[int] = None
    scale: Optional[int] = None
    nullable: bool = True


class ConnectionManager(BaseModel):
    """SSIS Connection Manager configuration."""

    id: str
    name: str
    description: Optional[str] = None
    connection_string: str
    server: Optional[str] = None
    database: Optional[str] = None
    provider: Optional[str] = None


class Variable(BaseModel):
    """SSIS Package Variable."""

    namespace: str
    name: str
    data_type: str
    value: Optional[str] = None
    expression: Optional[str] = None
    description: Optional[str] = None


class DerivedColumnDef(BaseModel):
    """Derived Column transformation definition."""

    name: str
    expression: str
    friendly_expression: Optional[str] = None
    output_type: str
    output_length: Optional[int] = None


class LookupTransform(BaseModel):
    """Lookup transformation (represents JOINs in dbt)."""

    name: str
    description: Optional[str] = None
    connection_manager: str
    sql_command: Optional[str] = None
    cache_mode: str = "Full"
    no_match_behavior: str = "FailComponent"
    input_columns: list[str] = Field(default_factory=list)
    join_columns: list[tuple[str, str]] = Field(default_factory=list)
    output_columns: list[str] = Field(default_factory=list)


class DataFlowSource(BaseModel):
    """Data Flow source component (OLE DB Source, Flat File, etc.)."""

    name: str
    component_type: str
    description: Optional[str] = None
    connection_manager: Optional[str] = None
    sql_command: Optional[str] = None
    table_name: Optional[str] = None
    columns: list[ColumnInfo] = Field(default_factory=list)


class DataFlowDestination(BaseModel):
    """Data Flow destination component."""

    name: str
    component_type: str
    description: Optional[str] = None
    connection_manager: Optional[str] = None
    table_name: Optional[str] = None
    columns: list[ColumnInfo] = Field(default_factory=list)


class DataFlowTask(BaseModel):
    """Data Flow Task containing sources, transforms, and destinations."""

    name: str
    description: Optional[str] = None
    sources: list[DataFlowSource] = Field(default_factory=list)
    destinations: list[DataFlowDestination] = Field(default_factory=list)
    lookups: list[LookupTransform] = Field(default_factory=list)
    derived_columns: list[DerivedColumnDef] = Field(default_factory=list)


class ExecuteSQLTask(BaseModel):
    """Execute SQL Task containing SQL statements."""

    name: str
    description: Optional[str] = None
    connection_manager: str
    sql_statement: str
    result_set: str = "None"  # None, SingleRow, Full
    parameters: list[dict] = Field(default_factory=list)


class ScriptTask(BaseModel):
    """Script Task - flagged for manual review."""

    name: str
    description: Optional[str] = None
    script_language: str = "CSharp"
    read_only_variables: list[str] = Field(default_factory=list)
    read_write_variables: list[str] = Field(default_factory=list)
    manual_review_required: bool = True
    review_reason: str = "Script Tasks require manual conversion to dbt macros or Python"


class SendMailTask(BaseModel):
    """Send Mail Task - documented but not converted."""

    name: str
    description: Optional[str] = None
    smtp_server: Optional[str] = None
    from_address: Optional[str] = None
    to_address: Optional[str] = None
    subject: Optional[str] = None
    message_source: Optional[str] = None
    skip_reason: str = "Send Mail Tasks are not converted - handle notifications externally"


class PrecedenceConstraint(BaseModel):
    """Precedence constraint defining task execution order."""

    from_task: str
    to_task: str
    constraint_type: str = "Success"  # Success, Failure, Completion, Expression


class SSISPackage(BaseModel):
    """Root model for a parsed SSIS package."""

    name: str
    description: Optional[str] = None
    creation_date: Optional[str] = None
    creator_name: Optional[str] = None
    creator_computer: Optional[str] = None
    file_path: str
    file_size_bytes: int = 0

    # Package components
    connection_managers: list[ConnectionManager] = Field(default_factory=list)
    variables: list[Variable] = Field(default_factory=list)

    # Tasks
    execute_sql_tasks: list[ExecuteSQLTask] = Field(default_factory=list)
    data_flow_tasks: list[DataFlowTask] = Field(default_factory=list)
    script_tasks: list[ScriptTask] = Field(default_factory=list)
    send_mail_tasks: list[SendMailTask] = Field(default_factory=list)

    # Execution order
    precedence_constraints: list[PrecedenceConstraint] = Field(default_factory=list)

    # Parsing metadata
    parsing_warnings: list[str] = Field(default_factory=list)
    parsing_errors: list[str] = Field(default_factory=list)

    def total_tasks(self) -> int:
        """Return total number of tasks in the package."""
        return (
            len(self.execute_sql_tasks)
            + len(self.data_flow_tasks)
            + len(self.script_tasks)
            + len(self.send_mail_tasks)
        )

    def has_manual_review_items(self) -> bool:
        """Check if package contains items requiring manual review."""
        return len(self.script_tasks) > 0


class SchemaTable(BaseModel):
    """Table metadata extracted from package references."""

    schema_name: Optional[str] = None
    table_name: str
    full_name: str
    source_system: Optional[str] = None
    referenced_in: list[str] = Field(default_factory=list)


class SchemaColumn(BaseModel):
    """Column metadata extracted from data flow components."""

    table_full_name: str
    column_name: str
    ssis_type: str
    sql_type: str
    length: Optional[int] = None
    precision: Optional[int] = None
    scale: Optional[int] = None


class SchemaMetadata(BaseModel):
    """Aggregated schema metadata from all parsed packages."""

    tables: list[SchemaTable] = Field(default_factory=list)
    columns: list[SchemaColumn] = Field(default_factory=list)
    source_systems: list[dict] = Field(default_factory=list)


class ParsingResult(BaseModel):
    """Complete parsing result containing all packages and metadata."""

    packages: list[SSISPackage] = Field(default_factory=list)
    schema_metadata: SchemaMetadata = Field(default_factory=SchemaMetadata)
    total_packages: int = 0
    total_execute_sql_tasks: int = 0
    total_data_flow_tasks: int = 0
    total_script_tasks: int = 0
    total_warnings: int = 0
    total_errors: int = 0
