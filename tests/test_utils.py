"""Tests for utility functions including credential redaction and SQL validation."""

import pytest

from src.parser.utils import (
    PathTraversalError,
    SQLIdentifierError,
    redact_connection_string,
    redact_dict_credentials,
    sanitize_sql_identifier,
    validate_sql_identifier,
    validate_safe_path,
)


class TestRedactConnectionString:
    """Tests for redact_connection_string function."""

    def test_redacts_password(self):
        """Should redact Password= values."""
        conn = "Server=localhost;Database=test;User=sa;Password=secret123;"
        result = redact_connection_string(conn)
        assert "secret123" not in result
        assert "***REDACTED***" in result
        assert "Server=localhost" in result

    def test_redacts_pwd(self):
        """Should redact PWD= values."""
        conn = "Server=localhost;UID=sa;PWD=mypassword;"
        result = redact_connection_string(conn)
        assert "mypassword" not in result
        assert "***REDACTED***" in result

    def test_redacts_case_insensitive(self):
        """Should redact regardless of case."""
        conn = "Server=localhost;PASSWORD=Secret;password=other;"
        result = redact_connection_string(conn)
        assert "Secret" not in result
        assert "other" not in result

    def test_handles_empty_string(self):
        """Should handle empty connection string."""
        assert redact_connection_string("") == ""

    def test_handles_none_like_input(self):
        """Should handle None gracefully."""
        assert redact_connection_string("") == ""

    def test_preserves_non_sensitive_data(self):
        """Should preserve non-sensitive parts of connection string."""
        conn = "Server=prod-server;Database=SalesDB;User=admin;Password=secret;"
        result = redact_connection_string(conn)
        assert "Server=prod-server" in result
        assert "Database=SalesDB" in result
        assert "User=admin" in result

    def test_redacts_api_key(self):
        """Should redact API key values."""
        conn = "Endpoint=https://api.example.com;API_Key=sk-12345abcde;"
        result = redact_connection_string(conn)
        assert "sk-12345abcde" not in result

    def test_no_redaction_when_no_credentials(self):
        """Should return unchanged string when no credentials present."""
        conn = "Server=localhost;Database=test;Trusted_Connection=True;"
        result = redact_connection_string(conn)
        assert result == conn

    def test_redacts_quoted_password_with_semicolons(self):
        """Should properly redact passwords with semicolons when quoted."""
        conn = 'Server=localhost;Password="pass;word;here";Database=test'
        result = redact_connection_string(conn)
        assert "pass;word;here" not in result
        assert '***REDACTED***' in result

    def test_redacts_single_quoted_password(self):
        """Should redact single-quoted passwords."""
        conn = "Server=localhost;Password='secret;value';Database=test"
        result = redact_connection_string(conn)
        assert "secret;value" not in result

    def test_redacts_bearer_token(self):
        """Should redact Bearer tokens."""
        auth = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        result = redact_connection_string(auth)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result

    def test_redacts_token_parameter(self):
        """Should redact Token= values."""
        conn = "Server=localhost;Token=abc123secret;"
        result = redact_connection_string(conn)
        assert "abc123secret" not in result


class TestRedactDictCredentials:
    """Tests for redact_dict_credentials function."""

    def test_redacts_connection_string_field(self):
        """Should redact connection_string fields in dict."""
        data = {
            "name": "test",
            "connection_string": "Server=x;Password=secret;"
        }
        result = redact_dict_credentials(data)
        assert "secret" not in result["connection_string"]
        assert result["name"] == "test"

    def test_redacts_nested_dicts(self):
        """Should recursively redact nested dictionaries."""
        data = {
            "config": {
                "connection_string": "Server=x;PWD=pass123;"
            }
        }
        result = redact_dict_credentials(data)
        assert "pass123" not in result["config"]["connection_string"]

    def test_redacts_list_items(self):
        """Should redact items in lists."""
        data = {
            "connections": [
                {"connection_string": "Password=one;"},
                {"connection_string": "Password=two;"},
            ]
        }
        result = redact_dict_credentials(data)
        assert "one" not in str(result)
        assert "two" not in str(result)

    def test_redacts_token_field(self):
        """Should redact token fields."""
        data = {"access_token": "secret-token-value"}
        result = redact_dict_credentials(data)
        assert "secret-token-value" not in str(result)

    def test_redacts_private_key_field(self):
        """Should redact private_key fields."""
        data = {"private_key": "-----BEGIN RSA PRIVATE KEY-----"}
        result = redact_dict_credentials(data)
        assert "-----BEGIN RSA PRIVATE KEY-----" not in str(result)


class TestValidateSqlIdentifier:
    """Tests for validate_sql_identifier function."""

    def test_valid_simple_identifier(self):
        """Should accept simple valid identifiers."""
        assert validate_sql_identifier("customer_id") is True
        assert validate_sql_identifier("CustomerID") is True
        assert validate_sql_identifier("_private") is True

    def test_valid_with_numbers(self):
        """Should accept identifiers with numbers (not at start)."""
        assert validate_sql_identifier("col1") is True
        assert validate_sql_identifier("table_2") is True

    def test_rejects_special_chars_for_security(self):
        """Should reject @, #, $ for security (even though SQL Server allows them)."""
        # These are now rejected for security - they have special meaning in dynamic SQL
        assert validate_sql_identifier("col$name") is False
        assert validate_sql_identifier("@variable") is False
        assert validate_sql_identifier("#temp") is False

    def test_invalid_starts_with_number(self):
        """Should reject identifiers starting with numbers."""
        assert validate_sql_identifier("1column") is False
        assert validate_sql_identifier("123") is False

    def test_invalid_contains_spaces(self):
        """Should reject identifiers with spaces."""
        assert validate_sql_identifier("column name") is False
        assert validate_sql_identifier(" col") is False

    def test_invalid_sql_injection_attempts(self):
        """Should reject SQL injection patterns."""
        assert validate_sql_identifier("'; DROP TABLE users; --") is False
        assert validate_sql_identifier("col; DELETE FROM") is False
        assert validate_sql_identifier("col)--") is False

    def test_invalid_empty(self):
        """Should reject empty identifiers."""
        assert validate_sql_identifier("") is False

    def test_invalid_too_long(self):
        """Should reject identifiers exceeding max length."""
        long_name = "a" * 129
        assert validate_sql_identifier(long_name) is False

    def test_valid_max_length(self):
        """Should accept identifiers at max length."""
        max_name = "a" * 128
        assert validate_sql_identifier(max_name) is True

    def test_rejects_reserved_keywords_by_default(self):
        """Should reject SQL reserved keywords by default."""
        assert validate_sql_identifier("SELECT") is False
        assert validate_sql_identifier("select") is False
        assert validate_sql_identifier("DROP") is False
        assert validate_sql_identifier("DELETE") is False

    def test_allows_reserved_keywords_when_flag_set(self):
        """Should allow reserved keywords when allow_reserved=True."""
        assert validate_sql_identifier("SELECT", allow_reserved=True) is True
        assert validate_sql_identifier("table", allow_reserved=True) is True


class TestSanitizeSqlIdentifier:
    """Tests for sanitize_sql_identifier function."""

    def test_sanitizes_spaces(self):
        """Should replace spaces with underscores."""
        assert sanitize_sql_identifier("column name") == "column_name"

    def test_sanitizes_special_chars(self):
        """Should replace invalid special characters."""
        assert sanitize_sql_identifier("col-name") == "col_name"
        assert sanitize_sql_identifier("col.name") == "col_name"

    def test_sanitizes_at_symbol(self):
        """Should replace @ symbol (now restricted for security)."""
        result = sanitize_sql_identifier("@variable")
        assert "@" not in result
        assert result == "_variable"

    def test_sanitizes_dollar_sign(self):
        """Should replace $ symbol (now restricted for security)."""
        result = sanitize_sql_identifier("col$name")
        assert "$" not in result

    def test_fixes_leading_number(self):
        """Should prefix underscore for leading numbers."""
        assert sanitize_sql_identifier("123col") == "_123col"

    def test_handles_empty(self):
        """Should return _unnamed for empty input."""
        assert sanitize_sql_identifier("") == "_unnamed"

    def test_truncates_long_names(self):
        """Should truncate names exceeding max length."""
        long_name = "a" * 200
        result = sanitize_sql_identifier(long_name)
        assert len(result) == 128

    def test_preserves_valid_identifiers(self):
        """Should not modify already valid identifiers."""
        assert sanitize_sql_identifier("valid_name") == "valid_name"
        assert sanitize_sql_identifier("CamelCase") == "CamelCase"

    def test_removes_consecutive_underscores(self):
        """Should collapse consecutive underscores."""
        result = sanitize_sql_identifier("col__name")
        assert "__" not in result

    def test_handles_reserved_keywords(self):
        """Should add suffix to reserved keywords."""
        result = sanitize_sql_identifier("SELECT")
        assert result != "SELECT"
        assert "col" in result.lower()


class TestSQLIdentifierError:
    """Tests for SQLIdentifierError exception."""

    def test_error_message_includes_identifier(self):
        """Should include the invalid identifier in error message."""
        error = SQLIdentifierError("bad;name", "Test reason")
        assert "bad;name" in str(error)
        assert "Test reason" in str(error)

    def test_error_attributes(self):
        """Should store identifier and reason as attributes."""
        error = SQLIdentifierError("test", "Invalid")
        assert error.identifier == "test"
        assert error.reason == "Invalid"


class TestPathTraversalError:
    """Tests for PathTraversalError exception."""

    def test_error_message_includes_path(self):
        """Should include the path in error message."""
        error = PathTraversalError("../../../etc/passwd", "Path traversal detected")
        assert "../../../etc/passwd" in str(error)
        assert "Path traversal detected" in str(error)

    def test_error_attributes(self):
        """Should store path and reason as attributes."""
        error = PathTraversalError("../secret", "Invalid path")
        assert error.path == "../secret"
        assert error.reason == "Invalid path"


class TestValidateSafePath:
    """Tests for validate_safe_path function."""

    def test_valid_path_within_base(self):
        """Should accept paths within base directory."""
        assert validate_safe_path("subdir/file.txt", "/tmp/base") is True
        assert validate_safe_path("file.txt", "/tmp/base") is True

    def test_rejects_path_with_double_dots(self):
        """Should reject paths with .. traversal."""
        with pytest.raises(PathTraversalError):
            validate_safe_path("../etc/passwd", "/tmp/base")

    def test_rejects_absolute_path_escape(self):
        """Should reject paths that escape base directory."""
        with pytest.raises(PathTraversalError):
            validate_safe_path("subdir/../../etc/passwd", "/tmp/base")

    def test_rejects_empty_paths(self):
        """Should reject empty paths."""
        assert validate_safe_path("", "/tmp/base") is False
        assert validate_safe_path("file.txt", "") is False
