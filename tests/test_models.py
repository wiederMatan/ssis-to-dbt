"""Tests for Pydantic models and credential redaction."""

import pytest

from src.parser.models import (
    ColumnInfo,
    ConnectionManager,
    DataFlowSource,
    DataFlowTask,
    ExecuteSQLTask,
    PrecedenceConstraint,
    SSISPackage,
    Variable,
)


class TestConnectionManagerRedaction:
    """Tests for ConnectionManager credential redaction during serialization."""

    def test_redacts_password_on_dump(self):
        """Should redact password when serializing to dict."""
        cm = ConnectionManager(
            id="conn1",
            name="TestConnection",
            connection_string="Server=localhost;Password=secret123;Database=test;",
            server="localhost",
            database="test",
        )
        data = cm.model_dump()
        assert "secret123" not in data["connection_string"]
        assert "***REDACTED***" in data["connection_string"]

    def test_redacts_pwd_on_json(self):
        """Should redact PWD when serializing to JSON."""
        cm = ConnectionManager(
            id="conn1",
            name="TestConnection",
            connection_string="Server=prod;UID=sa;PWD=MyP@ssw0rd;",
        )
        json_str = cm.model_dump_json()
        assert "MyP@ssw0rd" not in json_str
        assert "***REDACTED***" in json_str

    def test_preserves_original_value(self):
        """Should preserve original value in memory (only redacts on serialization)."""
        cm = ConnectionManager(
            id="conn1",
            name="TestConnection",
            connection_string="Server=localhost;Password=secret123;",
        )
        # Original value should still be accessible
        assert "secret123" in cm.connection_string

    def test_redacts_in_package_dump(self):
        """Should redact when dumping entire package with connections."""
        package = SSISPackage(
            name="TestPackage",
            file_path="/path/to/test.dtsx",
            connection_managers=[
                ConnectionManager(
                    id="conn1",
                    name="Source",
                    connection_string="Server=src;Password=pass1;",
                ),
                ConnectionManager(
                    id="conn2",
                    name="Dest",
                    connection_string="Server=dst;PWD=pass2;",
                ),
            ],
        )
        data = package.model_dump()
        json_str = package.model_dump_json()

        # Check dict
        assert "pass1" not in str(data)
        assert "pass2" not in str(data)

        # Check JSON
        assert "pass1" not in json_str
        assert "pass2" not in json_str


class TestSSISPackageModel:
    """Tests for SSISPackage model."""

    def test_total_tasks_count(self):
        """Should correctly count all tasks."""
        package = SSISPackage(
            name="TestPackage",
            file_path="/path/test.dtsx",
            execute_sql_tasks=[
                ExecuteSQLTask(name="SQL1", connection_manager="conn1", sql_statement="SELECT 1"),
                ExecuteSQLTask(name="SQL2", connection_manager="conn1", sql_statement="SELECT 2"),
            ],
            data_flow_tasks=[
                DataFlowTask(name="DFT1"),
            ],
        )
        assert package.total_tasks() == 3

    def test_total_tasks_empty(self):
        """Should return 0 for empty package."""
        package = SSISPackage(name="Empty", file_path="/path/empty.dtsx")
        assert package.total_tasks() == 0

    def test_has_manual_review_items(self):
        """Should detect script tasks requiring manual review."""
        from src.parser.models import ScriptTask

        package = SSISPackage(
            name="TestPackage",
            file_path="/path/test.dtsx",
            script_tasks=[
                ScriptTask(name="Script1"),
            ],
        )
        assert package.has_manual_review_items() is True

    def test_no_manual_review_items(self):
        """Should return False when no script tasks."""
        package = SSISPackage(
            name="TestPackage",
            file_path="/path/test.dtsx",
            execute_sql_tasks=[
                ExecuteSQLTask(name="SQL1", connection_manager="conn1", sql_statement="SELECT 1"),
            ],
        )
        assert package.has_manual_review_items() is False


class TestColumnInfoModel:
    """Tests for ColumnInfo model."""

    def test_default_nullable(self):
        """Should default nullable to True."""
        col = ColumnInfo(name="col1", ssis_type="DT_I4", sql_type="INT")
        assert col.nullable is True

    def test_optional_fields(self):
        """Should allow optional fields to be None."""
        col = ColumnInfo(name="col1", ssis_type="DT_I4", sql_type="INT")
        assert col.length is None
        assert col.precision is None
        assert col.scale is None

    def test_with_all_fields(self):
        """Should accept all fields."""
        col = ColumnInfo(
            name="amount",
            ssis_type="DT_NUMERIC",
            sql_type="NUMERIC(18,2)",
            length=None,
            precision=18,
            scale=2,
            nullable=False,
        )
        assert col.precision == 18
        assert col.scale == 2
        assert col.nullable is False


class TestVariableModel:
    """Tests for Variable model."""

    def test_basic_variable(self):
        """Should create basic variable."""
        var = Variable(
            namespace="User",
            name="StartDate",
            data_type="DateTime",
            value="2024-01-01",
        )
        assert var.namespace == "User"
        assert var.name == "StartDate"

    def test_variable_with_expression(self):
        """Should support expression-based variables."""
        var = Variable(
            namespace="User",
            name="FilePath",
            data_type="String",
            expression='@[User::BaseDir] + "\\output.csv"',
        )
        assert var.expression is not None


class TestPrecedenceConstraintModel:
    """Tests for PrecedenceConstraint model."""

    def test_default_constraint_type(self):
        """Should default to Success constraint."""
        pc = PrecedenceConstraint(from_task="Task1", to_task="Task2")
        assert pc.constraint_type == "Success"

    def test_failure_constraint(self):
        """Should support failure constraints."""
        pc = PrecedenceConstraint(
            from_task="Task1",
            to_task="ErrorHandler",
            constraint_type="Failure",
        )
        assert pc.constraint_type == "Failure"


class TestDataFlowTaskModel:
    """Tests for DataFlowTask model."""

    def test_empty_data_flow(self):
        """Should create data flow with empty lists."""
        dft = DataFlowTask(name="EmptyDFT")
        assert dft.sources == []
        assert dft.destinations == []
        assert dft.lookups == []
        assert dft.derived_columns == []

    def test_data_flow_with_source(self):
        """Should create data flow with source."""
        dft = DataFlowTask(
            name="LoadCustomers",
            sources=[
                DataFlowSource(
                    name="OLE DB Source",
                    component_type="OLEDBSource",
                    table_name="dbo.Customers",
                )
            ],
        )
        assert len(dft.sources) == 1
        assert dft.sources[0].table_name == "dbo.Customers"
