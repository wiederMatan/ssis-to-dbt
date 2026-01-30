"""Tests for SSIS to SQL type mappings."""

import pytest

from src.parser.type_mappings import (
    SSIS_TO_SQL_TYPE_MAP,
    get_dbt_cast_expression,
    get_snake_case,
    map_ssis_type_to_sql,
)
from src.parser.utils import SQLIdentifierError


class TestSSISToSQLTypeMap:
    """Tests for SSIS type mapping dictionary."""

    def test_common_string_types(self):
        """Should map common string types correctly."""
        assert SSIS_TO_SQL_TYPE_MAP["DT_WSTR"] == "NVARCHAR"
        assert SSIS_TO_SQL_TYPE_MAP["DT_STR"] == "VARCHAR"
        assert SSIS_TO_SQL_TYPE_MAP["wstr"] == "NVARCHAR"
        assert SSIS_TO_SQL_TYPE_MAP["str"] == "VARCHAR"

    def test_integer_types(self):
        """Should map integer types correctly."""
        assert SSIS_TO_SQL_TYPE_MAP["DT_I4"] == "INT"
        assert SSIS_TO_SQL_TYPE_MAP["DT_I8"] == "BIGINT"
        assert SSIS_TO_SQL_TYPE_MAP["i4"] == "INT"
        assert SSIS_TO_SQL_TYPE_MAP["i8"] == "BIGINT"

    def test_datetime_types(self):
        """Should map datetime types correctly."""
        assert SSIS_TO_SQL_TYPE_MAP["DT_DBTIMESTAMP"] == "DATETIME"
        assert SSIS_TO_SQL_TYPE_MAP["DT_DBDATE"] == "DATE"
        assert SSIS_TO_SQL_TYPE_MAP["dbTimeStamp"] == "DATETIME"

    def test_boolean_type(self):
        """Should map boolean to BIT."""
        assert SSIS_TO_SQL_TYPE_MAP["DT_BOOL"] == "BIT"
        assert SSIS_TO_SQL_TYPE_MAP["bool"] == "BIT"

    def test_numeric_types(self):
        """Should map numeric types correctly."""
        assert SSIS_TO_SQL_TYPE_MAP["DT_NUMERIC"] == "NUMERIC"
        assert SSIS_TO_SQL_TYPE_MAP["DT_DECIMAL"] == "DECIMAL"
        assert SSIS_TO_SQL_TYPE_MAP["DT_CY"] == "MONEY"


class TestMapSSISTypeToSQL:
    """Tests for map_ssis_type_to_sql function."""

    def test_string_with_length(self):
        """Should include length for string types."""
        result = map_ssis_type_to_sql("DT_WSTR", length=50)
        assert result == "NVARCHAR(50)"

        result = map_ssis_type_to_sql("wstr", length=100)
        assert result == "NVARCHAR(100)"

    def test_string_without_length(self):
        """Should return base type when no length provided."""
        result = map_ssis_type_to_sql("DT_WSTR")
        assert result == "NVARCHAR"

    def test_numeric_with_precision_and_scale(self):
        """Should include precision and scale for numeric types."""
        result = map_ssis_type_to_sql("DT_NUMERIC", precision=18, scale=2)
        assert result == "NUMERIC(18,2)"

    def test_numeric_with_precision_only(self):
        """Should include only precision when scale not provided."""
        result = map_ssis_type_to_sql("DT_NUMERIC", precision=10)
        assert result == "NUMERIC(10)"

    def test_binary_with_length(self):
        """Should include length for binary types."""
        result = map_ssis_type_to_sql("DT_BYTES", length=256)
        assert result == "VARBINARY(256)"

    def test_unknown_type_defaults(self):
        """Should default to NVARCHAR(MAX) for unknown types."""
        result = map_ssis_type_to_sql("UNKNOWN_TYPE")
        assert result == "NVARCHAR(MAX)"

    def test_integer_ignores_length(self):
        """Should ignore length parameter for integer types."""
        result = map_ssis_type_to_sql("DT_I4", length=10)
        assert result == "INT"


class TestGetDbtCastExpression:
    """Tests for get_dbt_cast_expression function."""

    def test_simple_cast(self):
        """Should generate simple CAST expression."""
        result = get_dbt_cast_expression("customer_id", "DT_I4", "INT")
        assert result == "CAST(customer_id AS INT)"

    def test_cast_with_varchar(self):
        """Should generate CAST with VARCHAR type."""
        result = get_dbt_cast_expression("name", "DT_WSTR", "NVARCHAR(100)")
        assert result == "CAST(name AS NVARCHAR(100))"

    def test_rejects_invalid_column_name_strict(self):
        """Should raise error for invalid column names in strict mode."""
        with pytest.raises(SQLIdentifierError) as exc_info:
            get_dbt_cast_expression("'; DROP TABLE users;--", "DT_I4", "INT", strict=True)
        assert "invalid characters" in str(exc_info.value).lower()

    def test_sanitizes_invalid_column_name_non_strict(self):
        """Should sanitize invalid column names in non-strict mode."""
        result = get_dbt_cast_expression("column name", "DT_I4", "INT", strict=False)
        assert "column_name" in result
        assert " " not in result.split("AS")[0]  # No space in column part

    def test_rejects_invalid_sql_type(self):
        """Should raise error for invalid SQL types."""
        with pytest.raises(SQLIdentifierError):
            get_dbt_cast_expression("col", "DT_I4", "; DROP TABLE")

    def test_accepts_type_with_parentheses(self):
        """Should accept SQL types with size specifications."""
        result = get_dbt_cast_expression("col", "DT_WSTR", "NVARCHAR(50)")
        assert result == "CAST(col AS NVARCHAR(50))"


class TestGetSnakeCase:
    """Tests for get_snake_case function."""

    def test_camel_case(self):
        """Should convert CamelCase to snake_case."""
        assert get_snake_case("CustomerID") == "customer_id"
        assert get_snake_case("FirstName") == "first_name"

    def test_pascal_case(self):
        """Should convert PascalCase to snake_case."""
        assert get_snake_case("OrderDate") == "order_date"

    def test_already_snake_case(self):
        """Should preserve already snake_case names."""
        assert get_snake_case("customer_id") == "customer_id"

    def test_all_caps(self):
        """Should handle all caps abbreviations."""
        assert get_snake_case("HTTPRequest") == "http_request"
        assert get_snake_case("XMLParser") == "xml_parser"

    def test_mixed_case_with_numbers(self):
        """Should handle mixed case with numbers."""
        assert get_snake_case("Order2Customer") == "order2_customer"

    def test_single_word(self):
        """Should handle single lowercase word."""
        assert get_snake_case("name") == "name"
        assert get_snake_case("ID") == "id"
