# SSIS-to-dbt Migration Factory - Tutorial Video Script

**Video Duration**: ~8-10 minutes
**Target Audience**: Data engineers migrating from SSIS to dbt

---

## SCENE 1: Introduction (0:00 - 0:45)

### On Screen
- Title card: "SSIS-to-dbt Migration Factory"
- Subtitle: "Automated SSIS Package Conversion"

### Narration
> "If you're migrating from SQL Server Integration Services to dbt, you know it can be tedious work. Today I'll show you the SSIS-to-dbt Migration Factory - an automated tool that parses your SSIS packages, generates dbt models, and validates the results."

### Key Points to Show
- Brief view of an SSIS package XML file
- Brief view of a generated dbt model
- The dashboard overview

---

## SCENE 2: Project Overview (0:45 - 1:30)

### On Screen
- Terminal showing project structure

### Commands to Run
```bash
# Show project structure
ls -la

# Highlight key directories
ls samples/ssis_packages/
ls dbt_project/models/
```

### Narration
> "The project has three main parts:
> 1. A Python parser that extracts everything from your SSIS packages
> 2. An AI-powered agent framework that generates dbt models
> 3. A React dashboard for monitoring and validation"

---

## SCENE 3: Sample SSIS Packages (1:30 - 2:30)

### On Screen
- Show the sample .dtsx files

### Commands to Run
```bash
# List sample packages
ls -la samples/ssis_packages/

# Show contents of a package (briefly)
head -50 samples/ssis_packages/CustomerDataLoad.dtsx
```

### Narration
> "We have three sample SSIS packages to demonstrate:
> - CustomerDataLoad - loads a customer dimension
> - SalesFactETL - processes sales facts with lookups
> - InventorySync - syncs inventory with external systems
>
> These cover common patterns: data flows, Execute SQL tasks, lookups, derived columns, and even script tasks that need manual review."

---

## SCENE 4: Running the Parser (2:30 - 4:00)

### On Screen
- Terminal with parser execution

### Commands to Run
```bash
# Run the full migration pipeline
python run_agents.py ./samples/ssis_packages --output ./output --auto-approve
```

### Narration
> "Let's run the migration. The tool will:
> 1. Parse each SSIS package's XML
> 2. Extract connection managers, variables, and tasks
> 3. Build a dependency graph
> 4. Generate dbt models for each task
>
> Watch as it identifies a Script Task that needs manual review - the tool is smart enough to flag things it can't automatically convert."

### Key Output to Highlight
- Parsing progress for each package
- Task extraction messages
- Script Task flagged for manual review
- Model generation completion

---

## SCENE 5: Viewing the Output Files (4:00 - 5:30)

### On Screen
- Terminal + file contents

### Commands to Run
```bash
# View the parsing report
cat output/parsing_report.md

# View the migration mapping
cat output/migration_mapping.json | head -50
```

### Narration
> "The parser creates several output files:
> - parsing_report.md - a human-readable summary
> - migration_mapping.json - maps SSIS tasks to dbt models
> - parsed_packages.json - complete extraction data
>
> Notice how it extracted 11 tasks from 3 packages, with a 63.6% automatic migration rate. The rest are flagged for manual review."

### Key Points to Show
- Package statistics
- Task breakdown (Data Flow, Execute SQL, Script)
- Migration mapping structure

---

## SCENE 6: Generated dbt Models (5:30 - 7:00)

### On Screen
- dbt model files

### Commands to Run
```bash
# Show generated staging models
ls dbt_project/models/staging/

# View a staging model
cat dbt_project/models/staging/stg_sales__orders.sql

# Show generated core models
ls dbt_project/models/core/

# View a fact table
cat dbt_project/models/core/fct_sales.sql
```

### Narration
> "The tool generates properly structured dbt models. Let's look at what it created:
>
> **Staging models** - one for each data flow source, with:
> - Source references using the source() macro
> - Type conversions from SSIS types
> - Derived column expressions converted to SQL
>
> **Core models** - fact and dimension tables with:
> - Surrogate keys using dbt_utils
> - Lookup transforms converted to LEFT JOINs with ref()
> - Proper audit columns like loaded_at"

### Key Code to Highlight
```sql
-- Show these patterns:
{{ source('sales', 'raw_orders') }}
{{ dbt_utils.generate_surrogate_key(['sale_id']) }} AS sale_key
LEFT JOIN {{ ref('dim_customer') }} c ON s.customer_id = c.customer_id
```

---

## SCENE 7: The Dashboard UI (7:00 - 8:30)

### On Screen
- React dashboard in browser

### Setup (before recording)
```bash
cd ui
npm install
npm run dev
# Open http://localhost:5173
```

### Walkthrough Tabs

#### Tab 1: Packages
> "The Packages tab shows all migrated SSIS packages. You can expand each to see:
> - Package metadata
> - Individual task status
> - Which tasks were auto-converted vs need manual review"

#### Tab 2: Live Logs
> "Live Logs shows real-time execution output. You can filter by log level, search, and export logs for debugging."

#### Tab 3: Validation
> "The Validation tab shows data quality results:
> - Row count comparisons between legacy and dbt
> - Primary key integrity checks
> - Numeric checksums to verify data accuracy"

#### Tab 4: SQL Diff
> "Finally, the SQL Diff view lets you compare the original SSIS code with the generated dbt model side-by-side."

---

## SCENE 8: Validation (8:30 - 9:30)

### On Screen
- Terminal with validation output

### Commands to Run
```bash
# Run validation (assuming dbt is configured)
python run_migration.py --skip-dbt --verbose

# View validation report
cat output/validation_report.md
```

### Narration
> "Once your dbt models run in your environment, the tool validates results against your legacy data:
> - Row counts should match within 1% tolerance
> - Checksums verify no data was lost
> - Primary key integrity is preserved
>
> This gives you confidence that your migration is accurate."

---

## SCENE 9: Conclusion (9:30 - 10:00)

### On Screen
- Split screen: SSIS package → dbt model

### Narration
> "That's the SSIS-to-dbt Migration Factory. It automates the tedious parts of migration while flagging anything that needs your attention.
>
> To get started:
> 1. Clone the repository
> 2. Add your SSIS packages to the samples folder
> 3. Run the migration command
> 4. Review and customize the generated models
>
> Check out the README for full documentation. Happy migrating!"

### End Card
- GitHub repository URL
- "Star the repo if you found this useful!"

---

## B-ROLL SUGGESTIONS

- Typing code in VS Code
- Terminal scrolling with colorful output
- Dashboard with data loading
- Side-by-side comparison animations

---

## QUICK REFERENCE: Key Commands

```bash
# Full migration with auto-approve
python run_agents.py ./samples/ssis_packages --auto-approve

# Parser only (no agents)
python3 -m src.parser.ssis_parser ./samples/ssis_packages -o ./output -v

# Validation only
python run_migration.py --skip-dbt

# Start dashboard
cd ui && npm run dev
```

---

## QUICK REFERENCE: Key Files to Show

| Purpose | File |
|---------|------|
| Sample SSIS Package | `samples/ssis_packages/SalesFactETL.dtsx` |
| Parsing Report | `output/parsing_report.md` |
| Generated Staging Model | `dbt_project/models/staging/stg_sales__orders.sql` |
| Generated Fact Table | `dbt_project/models/core/fct_sales.sql` |
| Validation Report | `output/validation_report.md` |
| Dashboard Entry | `ui/src/components/Dashboard.tsx` |

---

## RECORDING TIPS

1. **Terminal Settings**: Use a large font (18-20pt) with high contrast theme
2. **Window Size**: 1920x1080 or larger for readability
3. **Typing Speed**: Type slowly so viewers can follow
4. **Pause Points**: Pause 2-3 seconds after each command completes
5. **Mouse Pointer**: Use a large, visible cursor
6. **Clean Desktop**: Hide unnecessary windows and notifications
