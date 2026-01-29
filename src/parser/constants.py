"""XML namespaces and constants for SSIS parsing."""

# SSIS XML Namespaces
NAMESPACES = {
    "DTS": "www.microsoft.com/SqlServer/Dts",
    "SQLTask": "www.microsoft.com/sqlserver/dts/tasks/sqltask",
    "SendMailTask": "www.microsoft.com/sqlserver/dts/tasks/sendmailtask",
}

# Executable types mapping
EXECUTABLE_TYPES = {
    "Microsoft.ExecuteSQLTask": "ExecuteSQLTask",
    "Microsoft.Pipeline": "DataFlowTask",
    "Microsoft.ScriptTask": "ScriptTask",
    "Microsoft.SendMailTask": "SendMailTask",
    "Microsoft.ForEachLoop": "ForEachLoopContainer",
    "Microsoft.ForLoop": "ForLoopContainer",
    "Microsoft.Sequence": "SequenceContainer",
}

# Data Flow component types
COMPONENT_TYPES = {
    "Microsoft.OLEDBSource": "OLEDBSource",
    "Microsoft.OLEDBDestination": "OLEDBDestination",
    "Microsoft.Lookup": "Lookup",
    "Microsoft.DerivedColumn": "DerivedColumn",
    "Microsoft.Merge": "Merge",
    "Microsoft.MergeJoin": "MergeJoin",
    "Microsoft.UnionAll": "UnionAll",
    "Microsoft.ConditionalSplit": "ConditionalSplit",
    "Microsoft.Aggregate": "Aggregate",
    "Microsoft.Sort": "Sort",
    "Microsoft.RowCount": "RowCount",
    "Microsoft.DataConversion": "DataConversion",
    "Microsoft.FlatFileSource": "FlatFileSource",
    "Microsoft.FlatFileDestination": "FlatFileDestination",
    "Microsoft.ExcelSource": "ExcelSource",
    "Microsoft.ExcelDestination": "ExcelDestination",
}

# Variable data types (DTS:DataType attribute values)
VARIABLE_DATA_TYPES = {
    "2": "DT_I2",  # Short (Int16)
    "3": "DT_I4",  # Integer (Int32)
    "7": "DT_DATE",  # Date
    "8": "DT_WSTR",  # Unicode String
    "11": "DT_BOOL",  # Boolean
    "13": "DT_VARIANT",  # Object/Variant
    "20": "DT_I8",  # Long (Int64)
    "135": "DT_DBTIMESTAMP",  # DateTime
}

# Tasks that require manual review
MANUAL_REVIEW_TASKS = {
    "Microsoft.ScriptTask": "Script Tasks require manual conversion to dbt macros or Python",
    "Microsoft.SendMailTask": "Send Mail Tasks are not converted - notification should be handled externally",
    "Microsoft.ExecuteProcessTask": "Execute Process Tasks require manual review for dbt conversion",
    "Microsoft.FTPTask": "FTP Tasks require manual conversion to Python scripts",
    "Microsoft.FileSystemTask": "File System Tasks require manual conversion",
}
