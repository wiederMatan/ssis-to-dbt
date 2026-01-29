# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

SSIS-to-dbt Migration Factory: Automated conversion of SSIS (SQL Server Integration Services) packages to dbt (data build tool) models with validation and monitoring UI.

## Commands

```bash
# Run SSIS parser
python3 -m src.parser.ssis_parser ./samples/ssis_packages -o ./output -v

# Install Python dependencies
pip3 install -r requirements.txt

# dbt commands (from dbt_project directory)
cd dbt_project
dbt deps        # Install dbt packages
dbt run         # Run all models
dbt test        # Run tests
dbt build       # Run + test
```

## Architecture

### Phase 1: SSIS Parser
- `src/parser/ssis_parser.py` - Main parser class using lxml
- `src/parser/models.py` - Pydantic models (SSISPackage, DataFlowTask, ExecuteSQLTask, etc.)
- `src/parser/type_mappings.py` - SSIS to SQL Server type conversions
- `src/parser/constants.py` - XML namespaces and task type mappings

### Phase 2: dbt Project
- `dbt_project/models/sources/` - Source definitions (src_*.yml)
- `dbt_project/models/staging/` - Staging models (stg_*.sql)
- `dbt_project/models/core/` - Fact and dimension models (fct_*, dim_*, agg_*)

### Output Files
- `output/parsed_packages.json` - Complete extraction of all SSIS packages
- `output/schema_metadata.json` - Tables and columns referenced
- `output/parsing_report.md` - Human-readable parsing summary
- `output/migration_mapping.json` - SSIS task to dbt model mapping
- `output/scaffolding_report.md` - dbt scaffolding summary

## Key Concepts

- **SSIS packages (.dtsx)**: XML files containing data flow tasks, control flow logic, connection managers, and transformations
- **dbt models**: SQL SELECT statements that define transformations, organized with YAML schema files for documentation and testing
- SSIS Data Flow Tasks map to dbt staging models; Execute SQL Tasks map to core models
- SSIS Lookup transforms map to SQL JOINs; Derived Columns map to SQL expressions

## Type Mappings

| SSIS Type | SQL Server Type |
|-----------|-----------------|
| DT_WSTR | NVARCHAR |
| DT_STR | VARCHAR |
| DT_I4 | INT |
| DT_I8 | BIGINT |
| DT_NUMERIC | NUMERIC |
| DT_DBTIMESTAMP | DATETIME |
| DT_BOOL | BIT |

## Naming Conventions (dbt)

- Sources: `src_{system}_{table}`
- Staging: `stg_{domain}__{entity}`
- Facts: `fct_{business_process}`
- Dimensions: `dim_{entity}`
- Aggregates: `agg_{grain}_{subject}`
