"""SSIS to SQL Server data type mappings."""

# SSIS to SQL Server type mapping
# Based on Microsoft Integration Services Data Types documentation
SSIS_TO_SQL_TYPE_MAP = {
    # String types
    "DT_STR": "VARCHAR",
    "DT_WSTR": "NVARCHAR",
    "DT_TEXT": "VARCHAR(MAX)",
    "DT_NTEXT": "NVARCHAR(MAX)",
    # Integer types
    "DT_I1": "TINYINT",
    "DT_I2": "SMALLINT",
    "DT_I4": "INT",
    "DT_I8": "BIGINT",
    "DT_UI1": "TINYINT",
    "DT_UI2": "INT",
    "DT_UI4": "BIGINT",
    "DT_UI8": "NUMERIC(20,0)",
    # Decimal/Numeric types
    "DT_DECIMAL": "DECIMAL",
    "DT_NUMERIC": "NUMERIC",
    "DT_CY": "MONEY",
    "DT_R4": "REAL",
    "DT_R8": "FLOAT",
    # Date/Time types
    "DT_DATE": "DATETIME",
    "DT_DBDATE": "DATE",
    "DT_DBTIME": "TIME",
    "DT_DBTIME2": "TIME",
    "DT_DBTIMESTAMP": "DATETIME",
    "DT_DBTIMESTAMP2": "DATETIME2",
    "DT_DBTIMESTAMPOFFSET": "DATETIMEOFFSET",
    "DT_FILETIME": "DATETIME",
    # Other types
    "DT_BOOL": "BIT",
    "DT_GUID": "UNIQUEIDENTIFIER",
    "DT_BYTES": "VARBINARY",
    "DT_IMAGE": "VARBINARY(MAX)",
    # Internal SSIS column types (lowercase in component XML)
    "i1": "TINYINT",
    "i2": "SMALLINT",
    "i4": "INT",
    "i8": "BIGINT",
    "ui1": "TINYINT",
    "ui2": "INT",
    "ui4": "BIGINT",
    "r4": "REAL",
    "r8": "FLOAT",
    "wstr": "NVARCHAR",
    "str": "VARCHAR",
    "bool": "BIT",
    "dbTimeStamp": "DATETIME",
    "dbDate": "DATE",
    "dbTime": "TIME",
    "guid": "UNIQUEIDENTIFIER",
    "bytes": "VARBINARY",
    "numeric": "NUMERIC",
    "cy": "MONEY",
}


def map_ssis_type_to_sql(
    ssis_type: str,
    length: int | None = None,
    precision: int | None = None,
    scale: int | None = None,
) -> str:
    """
    Map SSIS data type to SQL Server type with optional size parameters.

    Args:
        ssis_type: The SSIS data type (e.g., 'DT_WSTR', 'i4', 'numeric')
        length: String/binary length
        precision: Numeric precision
        scale: Numeric scale

    Returns:
        SQL Server data type string (e.g., 'NVARCHAR(50)', 'NUMERIC(18,2)')
    """
    base_type = SSIS_TO_SQL_TYPE_MAP.get(ssis_type, "NVARCHAR(MAX)")

    # Handle string types with length
    if ssis_type in ("DT_WSTR", "DT_STR", "wstr", "str") and length:
        return f"{base_type}({length})"

    # Handle numeric types with precision and scale
    if ssis_type in ("DT_DECIMAL", "DT_NUMERIC", "numeric") and precision:
        if scale is not None:
            return f"NUMERIC({precision},{scale})"
        return f"NUMERIC({precision})"

    # Handle binary types with length
    if ssis_type in ("DT_BYTES", "bytes") and length:
        return f"VARBINARY({length})"

    return base_type


def get_dbt_cast_expression(column_name: str, ssis_type: str, sql_type: str) -> str:
    """
    Generate a dbt CAST expression for type conversion.

    Args:
        column_name: The source column name
        ssis_type: The SSIS data type
        sql_type: The target SQL Server type

    Returns:
        A CAST expression string for use in dbt models
    """
    # For most types, a simple CAST is sufficient
    return f"CAST({column_name} AS {sql_type})"


def get_snake_case(name: str) -> str:
    """
    Convert a column name to snake_case.

    Args:
        name: The original column name (e.g., 'CustomerID', 'FirstName')

    Returns:
        Snake case version (e.g., 'customer_id', 'first_name')
    """
    import re

    # Insert underscore before uppercase letters (except at start)
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    # Insert underscore before uppercase letters followed by lowercase
    s2 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1)
    return s2.lower()
