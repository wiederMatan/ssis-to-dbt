"""Utility functions for SSIS parser."""

import re
from typing import Any


# Patterns for credentials in connection strings
CREDENTIAL_PATTERNS = [
    (re.compile(r'(Password\s*=\s*)([^;]+)', re.IGNORECASE), r'\1***REDACTED***'),
    (re.compile(r'(PWD\s*=\s*)([^;]+)', re.IGNORECASE), r'\1***REDACTED***'),
    (re.compile(r'(User Password\s*=\s*)([^;]+)', re.IGNORECASE), r'\1***REDACTED***'),
    (re.compile(r'(Secret\s*=\s*)([^;]+)', re.IGNORECASE), r'\1***REDACTED***'),
    (re.compile(r'(API[_-]?Key\s*=\s*)([^;]+)', re.IGNORECASE), r'\1***REDACTED***'),
]

# SQL identifier validation pattern (standard SQL identifier rules)
SQL_IDENTIFIER_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_@#$]*$')

# Maximum identifier length (SQL Server limit)
MAX_IDENTIFIER_LENGTH = 128


def redact_connection_string(connection_string: str) -> str:
    """
    Redact sensitive credentials from a connection string.

    Args:
        connection_string: The original connection string potentially containing passwords.

    Returns:
        Connection string with sensitive values replaced with ***REDACTED***.

    Example:
        >>> redact_connection_string("Server=localhost;User=sa;Password=secret123;")
        'Server=localhost;User=sa;Password=***REDACTED***;'
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
    sensitive_keys = {'connection_string', 'password', 'pwd', 'secret', 'api_key', 'apikey'}
    result = {}

    for key, value in data.items():
        lower_key = key.lower()

        if isinstance(value, dict):
            result[key] = redact_dict_credentials(value)
        elif isinstance(value, list):
            result[key] = [
                redact_dict_credentials(item) if isinstance(item, dict) else item
                for item in value
            ]
        elif isinstance(value, str) and any(sk in lower_key for sk in sensitive_keys):
            result[key] = redact_connection_string(value)
        else:
            result[key] = value

    return result


def validate_sql_identifier(identifier: str) -> bool:
    """
    Validate that a string is a safe SQL identifier.

    Args:
        identifier: The identifier to validate.

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
    """
    if not identifier:
        return False

    if len(identifier) > MAX_IDENTIFIER_LENGTH:
        return False

    return bool(SQL_IDENTIFIER_PATTERN.match(identifier))


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
    """
    if not identifier:
        return "_unnamed"

    # Replace invalid characters with underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_@#$]', '_', identifier)

    # Ensure it starts with a valid character
    if sanitized and not sanitized[0].isalpha() and sanitized[0] != '_':
        sanitized = '_' + sanitized

    # Truncate if too long
    if len(sanitized) > MAX_IDENTIFIER_LENGTH:
        sanitized = sanitized[:MAX_IDENTIFIER_LENGTH]

    return sanitized or "_unnamed"


class SQLIdentifierError(ValueError):
    """Raised when an invalid SQL identifier is encountered."""

    def __init__(self, identifier: str, reason: str = "Invalid SQL identifier"):
        self.identifier = identifier
        self.reason = reason
        super().__init__(f"{reason}: '{identifier}'")
