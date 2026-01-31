# Test Coverage Analysis Report

## Executive Summary

The SSIS-to-dbt codebase has **~19% test-to-source ratio** (1,063 lines of test code vs 5,603 lines of source code). Tests are heavily focused on **security** (XXE prevention, SQL injection, path traversal), while core **business logic** remains largely untested.

**Critical Gap**: All 6 agent modules (3,348 lines) and the validation framework (570 lines) have **zero functional tests**.

---

## Current Test Coverage

### Modules WITH Tests (5 test files, 118 tests)

| Module | Tests | What's Tested |
|--------|-------|---------------|
| `type_mappings.py` | 14 | SSIS-to-SQL type mapping, dbt cast expressions, snake_case conversion |
| `models.py` | 17 | Pydantic model serialization, credential redaction |
| `ssis_parser.py` | 13 | **Security only**: XXE prevention, input validation |
| `executor.py` | 7 | **Security only**: Path traversal prevention |
| `sql_server.py` | 8 | **Security only**: SQL injection prevention, credential masking |
| `utils.py` | 59 | Connection string redaction, SQL identifier validation |

### Modules WITHOUT Tests (Critical Gaps)

| Module | Lines | Priority | Risk |
|--------|-------|----------|------|
| `analyzer.py` | 490 | **Critical** | Core parsing logic, load pattern detection |
| `builder.py` | 511 | **Critical** | dbt model generation, SQL conversion |
| `orchestrator.py` | 439 | **Critical** | State machine coordination |
| `validator.py` | 375 | **High** | Data validation between SSIS and dbt |
| `diagnoser.py` | 345 | **High** | Root cause analysis |
| `validation/validator.py` | 570 | **High** | Data comparison framework |
| `context.py` | 190 | Medium | State persistence |
| `cli/approval.py` | 220 | Medium | User interaction workflows |
| `llm/openai_client.py` | 200 | Medium | API integration |
| `llm/prompts.py` | 164 | Low | Prompt templates |
| `logging_config.py` | 207 | Low | Logging setup |
| `constants.py` | 60 | Low | Static mappings |
| `base.py` | 137 | Low | Base classes |

---

## Detailed Recommendations

### 1. SSIS Parser Functional Tests (CRITICAL)

**Current state**: Only security tests exist. No tests for actual XML parsing functionality.

**Missing tests**:

```python
# tests/test_ssis_parser_functional.py

class TestSSISParserFunctional:
    """Functional tests for SSIS package parsing."""

    def test_parse_connection_managers(self, sample_package_path):
        """Should extract connection managers with server/database info."""
        parser = SSISParser()
        package = parser.parse_package(sample_package_path)

        assert len(package.connection_managers) > 0
        cm = package.connection_managers[0]
        assert cm.server is not None
        assert cm.database is not None

    def test_parse_data_flow_task_with_oledb_source(self):
        """Should extract OLE DB Source columns and types."""

    def test_parse_data_flow_task_with_lookup_transform(self):
        """Should extract lookup transforms for JOIN generation."""

    def test_parse_derived_column_expressions(self):
        """Should extract SSIS expressions from derived columns."""

    def test_parse_execute_sql_task(self):
        """Should extract SQL statements from Execute SQL Tasks."""

    def test_parse_precedence_constraints(self):
        """Should build correct task execution order."""

    def test_parse_variables(self):
        """Should extract package variables with types."""

    def test_parse_script_task_flags_manual_review(self):
        """Script Tasks should be flagged for manual review."""
```

**Use existing sample files**:
- `samples/ssis_packages/CustomerDataLoad.dtsx`
- `samples/ssis_packages/SalesFactETL.dtsx`
- `samples/ssis_packages/InventorySync.dtsx`

---

### 2. Builder Agent Tests (CRITICAL)

**Current state**: Zero tests. This is the core dbt generation logic.

**Missing tests**:

```python
# tests/test_builder_agent.py

class TestBuilderAgent:
    """Tests for dbt model generation."""

    def test_generate_staging_model_from_data_flow_task(self):
        """Should generate stg_*.sql from Data Flow Task."""

    def test_generate_core_model_from_execute_sql_task(self):
        """Should generate fct_*/dim_* from Execute SQL Task."""

    def test_staging_model_applies_type_casting(self):
        """Generated SQL should include proper CAST expressions."""

    def test_staging_model_converts_column_names_to_snake_case(self):
        """Column aliases should use snake_case."""

    def test_core_model_detects_dimension_pattern(self):
        """Tasks with 'SCD' or 'MERGE' should generate dim_* models."""

    def test_core_model_detects_fact_pattern(self):
        """Tasks with 'FACT' or 'FCT' should generate fct_* models."""

    def test_source_yaml_generation(self):
        """Should generate valid source YAML with column info."""

    def test_incremental_config_for_incremental_load_pattern(self):
        """Incremental loads should use materialized='incremental'."""

class TestSSISExpressionConversion:
    """Tests for SSIS expression to SQL conversion."""

    def test_convert_isnull_expression(self):
        """ISNULL(col) should become ISNULL(col, '')."""
        builder = BuilderAgent(mock_context)
        result = builder._convert_ssis_expression("ISNULL(Name)")
        assert result == "ISNULL(Name, '')"

    def test_convert_ternary_to_case_when(self):
        """condition ? true : false should become CASE WHEN."""

    def test_strip_ssis_type_casts(self):
        """(DT_WSTR,50) should be removed from expressions."""
```

---

### 3. Orchestrator State Machine Tests (CRITICAL)

**Current state**: Zero tests. The orchestrator coordinates the entire pipeline.

**Missing tests**:

```python
# tests/test_orchestrator.py

class TestMigrationOrchestrator:
    """Tests for pipeline state machine."""

    def test_phase_transitions_happy_path(self):
        """Should transition: INIT -> ANALYZING -> BUILDING -> ... -> COMPLETE."""

    def test_phase_transitions_on_analysis_failure(self):
        """Should transition to FAILED when analysis fails."""

    def test_phase_transitions_on_validation_failure_with_retry(self):
        """Should transition to DIAGNOSING when validation fails."""

    def test_max_retries_exceeded_transitions_to_failed(self):
        """Should fail after max_iterations diagnosis cycles."""

    def test_keyboard_interrupt_saves_state(self):
        """Pipeline should save state on interrupt."""

    def test_resume_from_saved_state(self):
        """Should resume pipeline from persistence."""
```

---

### 4. Validation Framework Tests (HIGH)

**Current state**: Zero tests.

**Missing tests**:

```python
# tests/test_validation.py

class TestDataValidation:
    """Tests for data validation between source and target."""

    def test_row_count_validation_passes_when_equal(self):
        """Row count validation should pass when counts match."""

    def test_row_count_validation_fails_with_threshold(self):
        """Should fail when difference exceeds threshold."""

    def test_checksum_validation_detects_data_differences(self):
        """Checksum validation should detect row-level differences."""

    def test_primary_key_validation_detects_duplicates(self):
        """Should detect duplicate primary keys in target."""

    def test_generate_validation_report(self):
        """Should generate markdown report with pass/fail status."""
```

---

### 5. Analyzer Agent Tests (HIGH)

**Current state**: Zero tests.

**Missing tests**:

```python
# tests/test_analyzer_agent.py

class TestAnalyzerAgent:
    """Tests for SSIS analysis and pattern detection."""

    def test_detect_full_load_pattern(self):
        """Should detect full load when no incremental conditions exist."""

    def test_detect_incremental_load_pattern(self):
        """Should detect incremental load from WHERE clauses."""

    def test_detect_scd_pattern(self):
        """Should detect SCD from MERGE statements."""

    def test_build_dependency_graph(self):
        """Should build correct DAG from precedence constraints."""
```

---

### 6. Integration Tests (HIGH)

**Current state**: No integration tests exist.

**Recommendations**:

```python
# tests/integration/test_end_to_end.py

class TestEndToEndMigration:
    """Integration tests using sample SSIS packages."""

    @pytest.fixture
    def sample_packages_dir(self):
        return Path("samples/ssis_packages")

    def test_parse_and_build_customer_data_load(self, sample_packages_dir):
        """Full pipeline: parse CustomerDataLoad.dtsx -> generate dbt models."""
        parser = SSISParser()
        package = parser.parse_package(sample_packages_dir / "CustomerDataLoad.dtsx")

        # Verify parsing
        assert package.name == "CustomerDataLoad"
        assert len(package.data_flow_tasks) > 0

        # Run builder
        context = MigrationContext(...)
        builder = BuilderAgent(context)
        result = await builder.execute({"analysis": {...}})

        # Verify generated files
        assert result.success
        assert any("stg_" in f["path"] for f in result.data["files"])
```

---

### 7. Edge Case Tests (MEDIUM)

**Missing tests for edge cases**:

```python
# tests/test_edge_cases.py

class TestEdgeCases:
    """Tests for unusual or edge-case inputs."""

    def test_parse_empty_package(self):
        """Should handle SSIS package with no tasks."""

    def test_parse_package_with_unicode_names(self):
        """Should handle Unicode in table/column names."""

    def test_parse_deeply_nested_containers(self):
        """Should handle nested Sequence/ForLoop containers."""

    def test_builder_handles_reserved_sql_keywords(self):
        """Column names like 'select', 'from' should be quoted."""

    def test_builder_handles_very_long_column_names(self):
        """Should truncate or handle 128+ character column names."""
```

---

## Test Infrastructure Recommendations

### 1. Add pytest-cov for Coverage Reporting

```bash
pip install pytest-cov
```

```ini
# pytest.ini
addopts = -v --tb=short --cov=src --cov-report=html --cov-report=term-missing
```

### 2. Create a `conftest.py` with Shared Fixtures

```python
# tests/conftest.py
import pytest
from pathlib import Path

@pytest.fixture
def sample_packages_dir():
    return Path(__file__).parent.parent / "samples" / "ssis_packages"

@pytest.fixture
def temp_output_dir(tmp_path):
    return tmp_path / "output"

@pytest.fixture
def mock_migration_context(temp_output_dir):
    from src.agents.context import MigrationContext
    return MigrationContext(
        input_dir="/tmp/input",
        output_dir=str(temp_output_dir),
        dbt_project_path="/tmp/dbt",
    )
```

### 3. Add Test Categories with Markers

```ini
# pytest.ini
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (slower, use real files)
    security: Security-focused tests
```

---

## Prioritized Action Plan

| Priority | Area | Estimated Tests | Impact |
|----------|------|-----------------|--------|
| 1 | SSIS Parser functional tests | 15-20 | Core parsing reliability |
| 2 | Builder Agent tests | 15-20 | dbt model correctness |
| 3 | Orchestrator state machine tests | 10-15 | Pipeline reliability |
| 4 | End-to-end integration tests | 5-10 | System confidence |
| 5 | Validation framework tests | 10-15 | Data quality assurance |
| 6 | Analyzer Agent tests | 8-12 | Pattern detection accuracy |
| 7 | Edge case and error handling | 10-15 | Robustness |

**Target**: Add 75-100 tests to achieve ~40% code coverage on critical paths.

---

## Conclusion

The current test suite provides strong security coverage but lacks **functional tests for core business logic**. The highest priority gaps are:

1. **Parser**: No tests for actual XML parsing behavior
2. **Builder**: No tests for dbt model generation
3. **Orchestrator**: No tests for pipeline state transitions
4. **Integration**: No end-to-end tests using sample packages

Addressing these gaps would significantly improve confidence in the migration pipeline's correctness and reliability.
