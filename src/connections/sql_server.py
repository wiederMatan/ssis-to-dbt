"""SQL Server connection handler using pyodbc."""

import logging
import os
from contextlib import contextmanager
from typing import Any, Generator, Optional

from pydantic import BaseModel, Field, SecretStr

# Import SQL identifier validation using canonical path
from src.parser.utils import SQLIdentifierError, validate_sql_identifier

try:
    import pyodbc
except ImportError:
    pyodbc = None  # type: ignore


logger = logging.getLogger(__name__)


class SQLServerConfig(BaseModel):
    """SQL Server connection configuration."""

    server: str
    database: str
    driver: str = "ODBC Driver 17 for SQL Server"
    trusted_connection: bool = True
    username: Optional[str] = None
    password: Optional[SecretStr] = None  # Use SecretStr to prevent accidental logging
    timeout: int = 30

    def __repr__(self) -> str:
        """Safe repr that doesn't expose password."""
        return (
            f"SQLServerConfig(server={self.server!r}, database={self.database!r}, "
            f"driver={self.driver!r}, trusted_connection={self.trusted_connection}, "
            f"username={self.username!r}, password=***)"
        )

    @classmethod
    def from_env(cls, prefix: str = "") -> "SQLServerConfig":
        """Create config from environment variables."""
        p = prefix.upper() + "_" if prefix else ""
        pwd = os.getenv(f"{p}SQL_SERVER_PASSWORD")
        return cls(
            server=os.getenv(f"{p}SQL_SERVER_HOST", "localhost"),
            database=os.getenv(f"{p}SQL_SERVER_DB", "master"),
            driver=os.getenv(f"{p}SQL_SERVER_DRIVER", "ODBC Driver 17 for SQL Server"),
            trusted_connection=os.getenv(f"{p}SQL_SERVER_TRUSTED", "true").lower() == "true",
            username=os.getenv(f"{p}SQL_SERVER_USER"),
            password=SecretStr(pwd) if pwd else None,
        )


class SQLServerConnection:
    """SQL Server connection handler using pyodbc."""

    def __init__(self, config: SQLServerConfig):
        if pyodbc is None:
            raise ImportError(
                "pyodbc is required for SQL Server connections. "
                "Install with: pip install pyodbc"
            )
        self.config = config
        self._connection: Optional[Any] = None

    def _build_connection_string(self) -> str:
        """Build the ODBC connection string."""
        parts = [
            f"DRIVER={{{self.config.driver}}}",
            f"SERVER={self.config.server}",
            f"DATABASE={self.config.database}",
        ]

        if self.config.trusted_connection:
            parts.append("Trusted_Connection=yes")
        else:
            if self.config.username:
                parts.append(f"UID={self.config.username}")
            if self.config.password:
                # SecretStr.get_secret_value() to access the actual password
                parts.append(f"PWD={self.config.password.get_secret_value()}")

        return ";".join(parts)

    @contextmanager
    def get_connection(self) -> Generator[Any, None, None]:
        """Context manager for database connection."""
        conn = None
        try:
            conn_str = self._build_connection_string()
            conn = pyodbc.connect(conn_str, timeout=self.config.timeout)
            yield conn
        finally:
            if conn:
                conn.close()

    def execute_query(
        self,
        query: str,
        params: Optional[tuple] = None,
    ) -> list[dict[str, Any]]:
        """
        Execute a query and return results as list of dicts.

        Args:
            query: SQL query to execute
            params: Optional query parameters

        Returns:
            List of row dictionaries
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            if cursor.description is None:
                return []

            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def execute_scalar(
        self,
        query: str,
        params: Optional[tuple] = None,
    ) -> Any:
        """
        Execute a query and return single value.

        Args:
            query: SQL query to execute
            params: Optional query parameters

        Returns:
            Single scalar value
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            row = cursor.fetchone()
            return row[0] if row else None

    def _validate_identifier(self, name: str, identifier_type: str = "identifier") -> None:
        """Validate SQL identifier to prevent injection."""
        if not validate_sql_identifier(name):
            raise SQLIdentifierError(name, f"Invalid SQL {identifier_type}")

    def get_row_count(self, table: str, schema: str = "dbo") -> int:
        """Get row count for a table."""
        self._validate_identifier(table, "table name")
        self._validate_identifier(schema, "schema name")

        query = f"SELECT COUNT(*) FROM [{schema}].[{table}]"
        logger.debug(f"Executing row count query for {schema}.{table}")
        result = self.execute_scalar(query)
        return int(result) if result else 0

    def get_checksum(
        self,
        table: str,
        columns: list[str],
        schema: str = "dbo",
    ) -> dict[str, float]:
        """
        Get checksums (SUM, AVG) for numeric columns.

        Args:
            table: Table name
            columns: List of numeric column names
            schema: Schema name

        Returns:
            Dict with SUM and AVG for each column

        Raises:
            SQLIdentifierError: If any identifier is invalid
        """
        self._validate_identifier(table, "table name")
        self._validate_identifier(schema, "schema name")
        for col in columns:
            self._validate_identifier(col, "column name")

        checksums: dict[str, float] = {}

        for col in columns:
            query = f"""
                SELECT
                    ISNULL(SUM(CAST([{col}] AS FLOAT)), 0) AS sum_val,
                    ISNULL(AVG(CAST([{col}] AS FLOAT)), 0) AS avg_val
                FROM [{schema}].[{table}]
            """
            logger.debug(f"Executing checksum query for {schema}.{table}.{col}")
            result = self.execute_query(query)
            if result:
                checksums[f"{col}_sum"] = float(result[0].get("sum_val", 0))
                checksums[f"{col}_avg"] = float(result[0].get("avg_val", 0))

        return checksums

    def check_primary_key(
        self,
        table: str,
        pk_column: str,
        schema: str = "dbo",
    ) -> dict[str, int]:
        """
        Check primary key integrity.

        Args:
            table: Table name
            pk_column: Primary key column name
            schema: Schema name

        Returns:
            Dict with null_count and duplicate_count

        Raises:
            SQLIdentifierError: If any identifier is invalid
        """
        self._validate_identifier(table, "table name")
        self._validate_identifier(schema, "schema name")
        self._validate_identifier(pk_column, "column name")

        null_query = f"""
            SELECT COUNT(*) AS null_count
            FROM [{schema}].[{table}]
            WHERE [{pk_column}] IS NULL
        """
        dup_query = f"""
            SELECT COUNT(*) AS dup_count
            FROM (
                SELECT [{pk_column}], COUNT(*) AS cnt
                FROM [{schema}].[{table}]
                GROUP BY [{pk_column}]
                HAVING COUNT(*) > 1
            ) AS dups
        """

        logger.debug(f"Checking primary key integrity for {schema}.{table}.{pk_column}")
        null_result = self.execute_scalar(null_query)
        dup_result = self.execute_scalar(dup_query)

        return {
            "null_count": int(null_result) if null_result else 0,
            "duplicate_count": int(dup_result) if dup_result else 0,
        }

    def test_connection(self) -> bool:
        """Test if connection can be established."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                return True
        except Exception:
            return False
