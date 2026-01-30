"""Security tests for path traversal and SQL injection protection."""

import tempfile
from pathlib import Path

import pytest

from src.agents.executor import ExecutorAgent, PathTraversalError
from src.parser.utils import SQLIdentifierError, validate_sql_identifier

# Check if pyodbc is available
try:
    import pyodbc
    PYODBC_AVAILABLE = True
except ImportError:
    PYODBC_AVAILABLE = False


class TestPathTraversalProtection:
    """Tests for path traversal protection in ExecutorAgent."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_blocks_parent_directory_traversal(self, temp_dir):
        """Should block attempts to write outside base directory with ../"""
        # Create a mock context (minimal)
        from unittest.mock import MagicMock

        mock_context = MagicMock()
        mock_context.dbt_project_path = str(temp_dir)

        executor = ExecutorAgent(context=mock_context)

        # Attempt path traversal
        with pytest.raises(PathTraversalError) as exc_info:
            executor._validate_path(Path("../../../etc/passwd"), temp_dir)

        assert "escape" in str(exc_info.value).lower()

    def test_blocks_absolute_path_escape(self, temp_dir):
        """Should block absolute paths that escape base directory."""
        from unittest.mock import MagicMock

        mock_context = MagicMock()
        executor = ExecutorAgent(context=mock_context)

        # Absolute path outside base
        with pytest.raises(PathTraversalError):
            executor._validate_path(Path("/etc/passwd"), temp_dir)

    def test_allows_valid_relative_path(self, temp_dir):
        """Should allow valid relative paths within base directory."""
        from unittest.mock import MagicMock

        mock_context = MagicMock()
        executor = ExecutorAgent(context=mock_context)

        # Valid relative path
        result = executor._validate_path(Path("models/staging/test.sql"), temp_dir)

        assert result.is_absolute()
        assert str(temp_dir) in str(result)

    def test_allows_nested_directory(self, temp_dir):
        """Should allow deeply nested paths within base."""
        from unittest.mock import MagicMock

        mock_context = MagicMock()
        executor = ExecutorAgent(context=mock_context)

        nested_path = Path("a/b/c/d/e/file.sql")
        result = executor._validate_path(nested_path, temp_dir)

        assert result.is_absolute()


class TestSQLInjectionProtection:
    """Tests for SQL injection protection using validate_sql_identifier."""

    def test_rejects_sql_injection_in_table_name(self):
        """Should reject malicious table names."""
        # Test the validation function directly
        assert validate_sql_identifier("users; DROP TABLE users;--") is False

    def test_rejects_sql_injection_in_column_name(self):
        """Should reject malicious column names."""
        assert validate_sql_identifier("col' OR '1'='1") is False

    def test_rejects_union_injection(self):
        """Should reject UNION-based injection attempts."""
        assert validate_sql_identifier("col UNION SELECT * FROM") is False

    def test_accepts_valid_identifiers(self):
        """Should accept valid SQL identifiers."""
        assert validate_sql_identifier("valid_table_name") is True
        assert validate_sql_identifier("CustomerID") is True
        assert validate_sql_identifier("dbo") is True
        assert validate_sql_identifier("_private_col") is True

    @pytest.mark.skipif(not PYODBC_AVAILABLE, reason="pyodbc not installed")
    def test_sql_server_connection_validates(self):
        """Test that SQLServerConnection validates identifiers."""
        from src.connections.sql_server import SQLServerConfig, SQLServerConnection

        config = SQLServerConfig(
            server="localhost",
            database="test",
            trusted_connection=True,
        )
        conn = SQLServerConnection(config)

        with pytest.raises(SQLIdentifierError):
            conn._validate_identifier("bad;name", "table name")


class TestCredentialProtection:
    """Tests for credential masking in config objects."""

    @pytest.mark.skipif(not PYODBC_AVAILABLE, reason="pyodbc not installed")
    def test_config_repr_hides_password(self):
        """Config repr should not expose password."""
        from pydantic import SecretStr
        from src.connections.sql_server import SQLServerConfig

        config = SQLServerConfig(
            server="localhost",
            database="test",
            trusted_connection=False,
            username="sa",
            password=SecretStr("supersecret123"),
        )

        repr_str = repr(config)
        assert "supersecret123" not in repr_str
        assert "***" in repr_str

    def test_secret_str_prevents_logging(self):
        """SecretStr should mask value in string conversion."""
        from pydantic import SecretStr

        secret = SecretStr("mypassword")

        # str() should show masked value
        assert "mypassword" not in str(secret)

        # get_secret_value() should return actual value
        assert secret.get_secret_value() == "mypassword"
