"""Utility functions for SSIS parser."""

import re
from typing import Any


# SECURITY: Patterns for credentials in connection strings
# These patterns handle various formats including quoted values and special characters
CREDENTIAL_PATTERNS = [
    # Handle quoted passwords: Password="secret;value"
    (re.compile(r'(Password\s*=\s*)"([^"]*)"', re.IGNORECASE), r'\1"***REDACTED***"'),
    (re.compile(r"(Password\s*=\s*)'([^']*)'", re.IGNORECASE), r"\1'***REDACTED***'"),
    # Handle unquoted passwords (stop at semicolon or end of string)
    (re.compile(r'(Password\s*=\s*)([^;"\'\s][^;]*)', re.IGNORECASE), r'\1***REDACTED***'),
    # PWD variants
    (re.compile(r'(PWD\s*=\s*)"([^"]*)"', re.IGNORECASE), r'\1"***REDACTED***"'),
    (re.compile(r"(PWD\s*=\s*)'([^']*)'", re.IGNORECASE), r"\1'***REDACTED***'"),
    (re.compile(r'(PWD\s*=\s*)([^;"\'\s][^;]*)', re.IGNORECASE), r'\1***REDACTED***'),
    # User Password
    (re.compile(r'(User Password\s*=\s*)"([^"]*)"', re.IGNORECASE), r'\1"***REDACTED***"'),
    (re.compile(r"(User Password\s*=\s*)'([^']*)'", re.IGNORECASE), r"\1'***REDACTED***'"),
    (re.compile(r'(User Password\s*=\s*)([^;"\'\s][^;]*)', re.IGNORECASE), r'\1***REDACTED***'),
    # Secret/API Key
    (re.compile(r'(Secret\s*=\s*)([^;]+)', re.IGNORECASE), r'\1***REDACTED***'),
    (re.compile(r'(API[_-]?Key\s*=\s*)([^;]+)', re.IGNORECASE), r'\1***REDACTED***'),
    (re.compile(r'(Token\s*=\s*)([^;]+)', re.IGNORECASE), r'\1***REDACTED***'),
    (re.compile(r'(Bearer\s+)([^\s;]+)', re.IGNORECASE), r'\1***REDACTED***'),
]

# SECURITY: SQL identifier validation pattern
# Restricted to alphanumeric and underscore only (no @, #, $ which can be exploited)
# This is more restrictive than SQL Server allows, but safer for dynamic SQL
SQL_IDENTIFIER_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

# Maximum identifier length (SQL Server limit)
MAX_IDENTIFIER_LENGTH = 128

# Reserved SQL keywords that shouldn't be used as identifiers
SQL_RESERVED_KEYWORDS = frozenset({
    'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'TABLE',
    'INDEX', 'VIEW', 'DATABASE', 'SCHEMA', 'EXEC', 'EXECUTE', 'DECLARE', 'SET',
    'GRANT', 'REVOKE', 'TRUNCATE', 'UNION', 'ALL', 'AND', 'OR', 'NOT', 'NULL',
    'WHERE', 'FROM', 'JOIN', 'ON', 'AS', 'INTO', 'VALUES', 'ORDER', 'BY', 'GROUP',
    'HAVING', 'LIMIT', 'OFFSET', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'BEGIN',
    'COMMIT', 'ROLLBACK', 'TRANSACTION', 'PROCEDURE', 'FUNCTION', 'TRIGGER',
})


def redact_connection_string(connection_string: str) -> str:
    """
    Redact sensitive credentials from a connection string.

    Handles various formats including:
    - Unquoted values: Password=secret;
    - Single-quoted values: Password='secret;with;semicolons';
    - Double-quoted values: Password="secret;with;semicolons";

    Args:
        connection_string: The original connection string potentially containing passwords.

    Returns:
        Connection string with sensitive values replaced with ***REDACTED***.

    Example:
        >>> redact_connection_string("Server=localhost;User=sa;Password=secret123;")
        'Server=localhost;User=sa;Password=***REDACTED***;'
        >>> redact_connection_string('Password="pass;word";Database=test')
        'Password="***REDACTED***";Database=test'
    """
    if not connection_string:
        return connection_string

    result = connection_string
    for pattern, replacement in CREDENTIAL_PATTERNS:
        result = pattern.sub(replacement, result)

    return result


def redact_dict_credentials(data: dict[str, Any]) -> dict[str, Any]:
    """
    Recursively redact credentials from a dictionary.

    Looks for keys containing 'connection_string', 'password', 'secret', etc.
    and redacts their values.

    Args:
        data: Dictionary potentially containing credential fields.

    Returns:
        New dictionary with credentials redacted.
    """
    # Keys that indicate the entire value should be redacted
    fully_sensitive_keys = {
        'password', 'pwd', 'secret', 'api_key', 'apikey',
        'token', 'bearer', 'credential', 'private_key', 'access_key',
        'secret_key', 'auth_token', 'refresh_token', 'access_token'
    }
    # Keys that may contain credentials within the value (like connection strings)
    partial_sensitive_keys = {'connection_string'}

    result = {}

    for key, value in data.items():
        lower_key = key.lower()
        # Normalize key for matching (handle variations like access_token, accessToken)
        normalized_key = lower_key.replace('_', '').replace('-', '')

        if isinstance(value, dict):
            result[key] = redact_dict_credentials(value)
        elif isinstance(value, list):
            result[key] = [
                redact_dict_credentials(item) if isinstance(item, dict) else item
                for item in value
            ]
        elif isinstance(value, str):
            # Check if key matches any fully sensitive pattern
            is_fully_sensitive = any(
                sk.replace('_', '') in normalized_key or normalized_key in sk.replace('_', '')
                for sk in fully_sensitive_keys
            )
            # Check if key matches partial sensitive pattern
            is_partial_sensitive = any(sk in lower_key for sk in partial_sensitive_keys)

            if is_fully_sensitive:
                # Fully redact the entire value
                result[key] = '***REDACTED***'
            elif is_partial_sensitive:
                # Apply pattern-based redaction
                result[key] = redact_connection_string(value)
            else:
                result[key] = value
        else:
            result[key] = value

    return result


def validate_sql_identifier(identifier: str, allow_reserved: bool = False) -> bool:
    """
    Validate that a string is a safe SQL identifier.

    This uses a restrictive pattern that only allows alphanumeric characters
    and underscores. While SQL Server allows @, #, and $ in identifiers,
    these are excluded for security as they have special meanings in dynamic SQL.

    Args:
        identifier: The identifier to validate.
        allow_reserved: If True, allow SQL reserved keywords (default: False).

    Returns:
        True if the identifier is valid, False otherwise.

    Example:
        >>> validate_sql_identifier("customer_id")
        True
        >>> validate_sql_identifier("1invalid")
        False
        >>> validate_sql_identifier("has spaces")
        False
        >>> validate_sql_identifier("'; DROP TABLE users; --")
        False
        >>> validate_sql_identifier("@variable")
        False
        >>> validate_sql_identifier("SELECT")
        False
        >>> validate_sql_identifier("SELECT", allow_reserved=True)
        True
    """
    if not identifier:
        return False

    if len(identifier) > MAX_IDENTIFIER_LENGTH:
        return False

    if not SQL_IDENTIFIER_PATTERN.match(identifier):
        return False

    # Check for reserved keywords unless explicitly allowed
    if not allow_reserved and identifier.upper() in SQL_RESERVED_KEYWORDS:
        return False

    return True


def sanitize_sql_identifier(identifier: str) -> str:
    """
    Sanitize a string to be a valid SQL identifier.

    Replaces invalid characters with underscores and ensures the identifier
    starts with a valid character.

    Args:
        identifier: The identifier to sanitize.

    Returns:
        A sanitized version of the identifier.

    Example:
        >>> sanitize_sql_identifier("123column")
        '_123column'
        >>> sanitize_sql_identifier("column name")
        'column_name'
        >>> sanitize_sql_identifier("@variable")
        '_variable'
    """
    if not identifier:
        return "_unnamed"

    # Replace invalid characters with underscores (more restrictive - no @, #, $)
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', identifier)

    # Ensure it starts with a valid character
    if sanitized and not sanitized[0].isalpha() and sanitized[0] != '_':
        sanitized = '_' + sanitized

    # Remove consecutive underscores
    sanitized = re.sub(r'_+', '_', sanitized)

    # Truncate if too long
    if len(sanitized) > MAX_IDENTIFIER_LENGTH:
        sanitized = sanitized[:MAX_IDENTIFIER_LENGTH]

    # Handle reserved keywords by adding suffix
    if sanitized.upper() in SQL_RESERVED_KEYWORDS:
        sanitized = sanitized + '_col'

    return sanitized or "_unnamed"


class SQLIdentifierError(ValueError):
    """Raised when an invalid SQL identifier is encountered."""

    def __init__(self, identifier: str, reason: str = "Invalid SQL identifier"):
        self.identifier = identifier
        self.reason = reason
        super().__init__(f"{reason}: '{identifier}'")


class PathTraversalError(ValueError):
    """Raised when a path traversal attempt is detected."""

    def __init__(self, path: str, reason: str = "Path traversal detected"):
        self.path = path
        self.reason = reason
        super().__init__(f"{reason}: '{path}'")


def validate_safe_path(file_path: str, base_path: str) -> bool:
    """
    Validate that a file path doesn't escape the base directory.

    Args:
        file_path: The file path to validate.
        base_path: The base directory that the path must stay within.

    Returns:
        True if the path is safe, False otherwise.

    Raises:
        PathTraversalError: If path traversal is detected.
    """
    from pathlib import Path

    if not file_path or not base_path:
        return False

    # Check for obvious path traversal patterns
    if '..' in file_path:
        raise PathTraversalError(file_path, "Path contains '..'")

    try:
        resolved_base = Path(base_path).resolve()
        resolved_file = (resolved_base / file_path).resolve()

        # Ensure the resolved path is under the base path
        resolved_file.relative_to(resolved_base)
        return True

    except ValueError:
        raise PathTraversalError(file_path, "Path escapes base directory")
