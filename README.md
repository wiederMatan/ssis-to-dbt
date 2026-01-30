# SSIS-to-dbt Migration Factory

Automated conversion of SQL Server Integration Services (SSIS) packages to dbt models.

## What It Does

This tool parses `.dtsx` SSIS packages and generates equivalent dbt models, complete with:
- Source definitions
- Staging models
- Fact and dimension tables
- Data validation

## Quick Start

**Requirements:** Python 3.9+, dbt-core 1.5+

```bash
# Clone and install
git clone https://github.com/wiederMatan/ssis-to-dbt.git
cd ssis-to-dbt
pip install -r requirements.txt

# Run the parser
python3 -m src.parser.ssis_parser ./samples/ssis_packages -o ./output -v
```

## How It Works

```
SSIS Package (.dtsx)  →  Parser  →  dbt Models (.sql/.yml)
```

**SSIS to dbt Mapping:**

| SSIS Component | dbt Output |
|----------------|------------|
| Data Flow Task | `stg_*.sql` (staging model) |
| Execute SQL Task (MERGE) | `fct_*.sql` (fact table) |
| Lookup Transform | `LEFT JOIN ref()` |
| Derived Column | SQL expression |
| Script Task | Manual review required |

## Project Structure

```
ssis-to-dbt/
├── src/
│   ├── parser/         # SSIS XML parsing
│   ├── agents/         # Migration framework
│   └── validation/     # Data validation
├── dbt_project/
│   └── models/
│       ├── sources/    # src_*.yml
│       ├── staging/    # stg_*.sql
│       └── core/       # fct_*, dim_*, agg_*
├── ui/                 # React dashboard
├── tests/              # Test suite
└── output/             # Generated files
```

## Output Files

- `parsed_packages.json` - Extracted SSIS package data
- `schema_metadata.json` - Tables and columns referenced
- `parsing_report.md` - Human-readable summary
- `migration_mapping.json` - SSIS task to dbt model mapping

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

## dbt Naming Conventions

| Layer | Pattern | Example |
|-------|---------|---------|
| Sources | `src_{system}_{table}` | `src_crm_customers` |
| Staging | `stg_{domain}__{entity}` | `stg_sales__orders` |
| Facts | `fct_{process}` | `fct_sales` |
| Dimensions | `dim_{entity}` | `dim_customer` |
| Aggregates | `agg_{grain}_{subject}` | `agg_daily_sales` |

## Running dbt

```bash
cd dbt_project
dbt deps    # Install packages
dbt run     # Run models
dbt test    # Run tests
```

## Testing

```bash
python3 -m pytest tests/ -v
```

## Manual Review Required

Some SSIS components cannot be automatically converted:

- **Script Task** - Custom C#/VB.NET code needs manual conversion
- **Send Mail Task** - Use external alerting instead
- **FTP Task** - Consider dbt external tables
- **Execute Process** - Move to orchestration layer

## License

MIT
