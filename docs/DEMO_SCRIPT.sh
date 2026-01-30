#!/bin/bash
# =============================================================================
# SSIS-to-dbt Migration Factory - Demo Script
# =============================================================================
# Run this script step-by-step during video recording.
# Each section is separated by a pause for narration.
# =============================================================================

echo "=============================================="
echo "  SSIS-to-dbt Migration Factory Demo"
echo "=============================================="
echo ""

# -----------------------------------------------------------------------------
# PART 1: Show project structure
# -----------------------------------------------------------------------------
echo "📁 PROJECT STRUCTURE"
echo "--------------------"
ls -la
echo ""
read -p "Press Enter to continue..."

# -----------------------------------------------------------------------------
# PART 2: Show sample SSIS packages
# -----------------------------------------------------------------------------
echo ""
echo "📦 SAMPLE SSIS PACKAGES"
echo "-----------------------"
ls -lh samples/ssis_packages/
echo ""
read -p "Press Enter to continue..."

# -----------------------------------------------------------------------------
# PART 3: Peek inside an SSIS package
# -----------------------------------------------------------------------------
echo ""
echo "🔍 INSIDE AN SSIS PACKAGE (CustomerDataLoad.dtsx)"
echo "-------------------------------------------------"
head -30 samples/ssis_packages/CustomerDataLoad.dtsx
echo "..."
echo ""
read -p "Press Enter to continue..."

# -----------------------------------------------------------------------------
# PART 4: Run the migration
# -----------------------------------------------------------------------------
echo ""
echo "🚀 RUNNING THE MIGRATION"
echo "------------------------"
echo "Command: python run_agents.py ./samples/ssis_packages --auto-approve"
echo ""
read -p "Press Enter to run migration..."

python run_agents.py ./samples/ssis_packages --output ./output --auto-approve

echo ""
read -p "Press Enter to continue..."

# -----------------------------------------------------------------------------
# PART 5: View parsing report
# -----------------------------------------------------------------------------
echo ""
echo "📊 PARSING REPORT"
echo "-----------------"
cat output/parsing_report.md
echo ""
read -p "Press Enter to continue..."

# -----------------------------------------------------------------------------
# PART 6: Show generated dbt models
# -----------------------------------------------------------------------------
echo ""
echo "📂 GENERATED DBT MODELS - STAGING"
echo "----------------------------------"
ls -la dbt_project/models/staging/
echo ""
read -p "Press Enter to continue..."

echo ""
echo "📂 GENERATED DBT MODELS - CORE"
echo "------------------------------"
ls -la dbt_project/models/core/
echo ""
read -p "Press Enter to continue..."

# -----------------------------------------------------------------------------
# PART 7: View a staging model
# -----------------------------------------------------------------------------
echo ""
echo "📄 STAGING MODEL: stg_sales__orders.sql"
echo "----------------------------------------"
if [ -f "dbt_project/models/staging/stg_sales__orders.sql" ]; then
    cat dbt_project/models/staging/stg_sales__orders.sql
else
    echo "Model not found - showing stg_warehouse__inventory.sql instead:"
    cat dbt_project/models/staging/stg_warehouse__inventory.sql 2>/dev/null || ls dbt_project/models/staging/
fi
echo ""
read -p "Press Enter to continue..."

# -----------------------------------------------------------------------------
# PART 8: View a core model (fact table)
# -----------------------------------------------------------------------------
echo ""
echo "📄 CORE MODEL: fct_sales.sql"
echo "----------------------------"
if [ -f "dbt_project/models/core/fct_sales.sql" ]; then
    cat dbt_project/models/core/fct_sales.sql
else
    echo "Model not found - showing fct_inventory_snapshot.sql instead:"
    cat dbt_project/models/core/fct_inventory_snapshot.sql 2>/dev/null || ls dbt_project/models/core/
fi
echo ""
read -p "Press Enter to continue..."

# -----------------------------------------------------------------------------
# PART 9: View migration mapping
# -----------------------------------------------------------------------------
echo ""
echo "🗺️  MIGRATION MAPPING (SSIS Task → dbt Model)"
echo "----------------------------------------------"
cat output/migration_mapping.json | head -60
echo ""
read -p "Press Enter to continue..."

# -----------------------------------------------------------------------------
# PART 10: View validation report
# -----------------------------------------------------------------------------
echo ""
echo "✅ VALIDATION REPORT"
echo "--------------------"
if [ -f "output/validation_report.md" ]; then
    cat output/validation_report.md
else
    echo "Run validation with: python run_migration.py --skip-dbt"
fi
echo ""

# -----------------------------------------------------------------------------
# DONE
# -----------------------------------------------------------------------------
echo ""
echo "=============================================="
echo "  Demo Complete!"
echo "=============================================="
echo ""
echo "Next steps:"
echo "  1. Start the dashboard: cd ui && npm run dev"
echo "  2. Open http://localhost:5173"
echo "  3. Explore packages, logs, and validation"
echo ""
