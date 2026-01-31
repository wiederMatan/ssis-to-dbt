# SSIS-to-dbt Migration Factory

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An enterprise-grade, AI-powered migration framework that converts SQL Server Integration Services (SSIS) packages to dbt models. Built with a sophisticated multi-agent architecture featuring advanced memory management, dynamic tool orchestration, and comprehensive observability.

## Key Features

- **Multi-Agent Pipeline** - Specialized agents for analysis, code generation, execution, validation, and diagnosis
- **LLM-Enhanced Processing** - OpenAI GPT-4 integration for intelligent pattern detection and code generation
- **Advanced Memory System** - Short-term, long-term, semantic, episodic, and procedural memory stores
- **Dynamic Tool Registry** - ReAct-pattern tool calling with automatic discovery
- **Graph-Based Orchestration** - Parallel execution, conditional branching, and state checkpointing
- **Lifecycle Hooks** - Extensible pre/post execution, error handling, and custom event hooks
- **Full Observability** - Distributed tracing, metrics collection, and structured logging
- **Human-in-the-Loop** - Approval gates for critical operations with rich CLI interface

## Quick Start

```bash
# Clone and install
git clone https://github.com/wiederMatan/ssis-to-dbt.git
cd ssis-to-dbt
pip install -r requirements.txt

# Set up environment (optional, for LLM features)
export OPENAI_API_KEY="your-api-key"

# Run the migration pipeline
python run_agents.py ./samples/ssis_packages --output ./output

# Or with auto-approval for CI/CD
python run_agents.py ./samples/ssis_packages --auto-approve
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SSIS-to-dbt Migration Factory                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐              │
│  │  Analyzer   │───▶│   Builder   │───▶│  Executor   │              │
│  │   Agent     │    │   Agent     │    │   Agent     │              │
│  └─────────────┘    └─────────────┘    └─────────────┘              │
│         │                                      │                     │
│         │                                      ▼                     │
│         │                              ┌─────────────┐              │
│         │                              │  Validator  │              │
│         │                              │   Agent     │              │
│         │                              └─────────────┘              │
│         │                                      │                     │
│         │         ┌─────────────┐              │                     │
│         └────────▶│  Diagnoser  │◀─────────────┘                    │
│                   │   Agent     │     (on failure)                  │
│                   └─────────────┘                                    │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                        Core Framework                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │  Tools   │ │  Memory  │ │  Hooks   │ │  Events  │ │ Tracing  │  │
│  │ Registry │ │ Manager  │ │ Manager  │ │   Bus    │ │ & Metrics│  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Agent Framework

### Core Components

#### 1. Tool Registry

Dynamic tool management with ReAct-pattern execution:

```python
from src.agents.core import ToolRegistry, tool, ToolCategory

registry = ToolRegistry()

# Register tools using decorators
@tool(
    name="analyze_sql",
    category=ToolCategory.DATABASE,
    description="Analyze SQL statement structure"
)
async def analyze_sql(sql: str) -> dict:
    # Tool implementation
    return {"tables": [...], "joins": [...]}

registry.register(analyze_sql)

# Execute tools
result = await registry.execute("analyze_sql", agent_id="analyzer", sql="SELECT ...")
```

#### 2. Memory Manager

Multi-level memory system inspired by cognitive architectures:

```python
from src.agents.core import MemoryManager, MemoryType, MemoryPriority
from pathlib import Path

memory = MemoryManager(storage_path=Path("./memory"))

# Short-term memory (conversation context)
await memory.store(
    content={"user_query": "migrate orders table"},
    memory_type=MemoryType.SHORT_TERM,
    ttl_seconds=3600
)

# Long-term memory (persistent facts)
await memory.store(
    content="Customer table has SCD Type 2",
    memory_type=MemoryType.LONG_TERM,
    priority=MemoryPriority.HIGH,
    tags=["schema", "scd"]
)

# Semantic memory (knowledge)
await memory.semantic.store_fact(
    fact_id="dt_wstr",
    fact="DT_WSTR maps to NVARCHAR in SQL Server",
    confidence=1.0
)

# Episodic memory (past experiences)
await memory.episodic.start_episode("migration_001", {"package": "orders.dtsx"})
await memory.episodic.record_event("analysis", {"tables": 5})
await memory.episodic.end_episode(success=True, summary="Migration completed")

# Search across memory types
results = await memory.search("orders table", limit=10)
```

#### 3. Hook System

Extensible lifecycle management:

```python
from src.agents.core import HookManager, HookType, before_execute, after_execute

hooks = HookManager()

# Register hooks using decorators
@before_execute()
async def validate_input(context):
    if not context.data.get("packages"):
        context.should_continue = False
    return context

@after_execute()
async def log_result(context):
    print(f"Agent {context.agent_name} completed")
    return context

# Or register programmatically
hooks.register(
    name="audit_log",
    hook_type=HookType.AFTER_EXECUTE,
    handler=lambda ctx: log_to_audit(ctx)
)

# Trigger hooks
context = await hooks.trigger(
    HookType.BEFORE_EXECUTE,
    agent_name="Analyzer",
    data={"packages": [...]}
)
```

#### 4. Event Bus

Pub/sub messaging for agent communication:

```python
from src.agents.core import EventBus, EventType

bus = EventBus()

# Subscribe to events
bus.subscribe(EventType.AGENT_COMPLETED, lambda e: print(f"Agent done: {e.source}"))

# Subscribe with filter
bus.subscribe(
    EventType.VALIDATION_FAILED,
    handler=lambda e: alert_team(e),
    filter_fn=lambda e: e.data.get("severity") == "critical"
)

# Emit events
await bus.emit(
    EventType.AGENT_COMPLETED,
    source="AnalyzerAgent",
    data={"packages_analyzed": 5}
)
```

#### 5. Distributed Tracing

OpenTelemetry-compatible observability:

```python
from src.agents.core import Tracer, SpanKind, FileExporter
from pathlib import Path

tracer = Tracer(
    service_name="ssis-to-dbt",
    exporters=[FileExporter(Path("./traces.json"))]
)

# Create spans
async with tracer.async_span("analyze_package", kind=SpanKind.INTERNAL) as span:
    span.set_attribute("package.name", "orders.dtsx")
    result = await analyze_package(package)
    span.add_event("analysis_complete", {"tables": len(result.tables)})

# Or use decorator
@tracer.trace("process_dataflow")
async def process_dataflow(task):
    ...
```

#### 6. Graph-Based Orchestration

LangGraph-inspired workflow execution:

```python
from src.agents.core import StateGraph, GraphState, EdgeCondition

# Define the workflow graph
graph = StateGraph("migration_pipeline")

# Add nodes (agents)
graph.add_node("analyze", analyzer_func)
graph.add_node("build", builder_func)
graph.add_node("validate", validator_func)
graph.add_node("diagnose", diagnoser_func)

# Add edges with conditions
graph.add_edge("analyze", "build", condition=EdgeCondition.ON_SUCCESS)
graph.add_edge("build", "validate")
graph.add_conditional_edges(
    "validate",
    conditions={
        "diagnose": lambda s: not s.get("validation_passed"),
    },
    default="complete"
)

# Set entry and exit points
graph.set_entry_point("analyze")
graph.set_finish_point("complete")

# Execute with parallel support
result = await graph.execute(
    initial_state={"packages": [...]},
    max_parallel=3  # Run up to 3 nodes in parallel
)
```

## Migration Agents

### 1. AnalyzerAgent

Parses SSIS packages and extracts metadata:

- **Input**: SSIS package paths
- **Output**: Package analysis, dependency graphs, load patterns
- **Tools**: SSIS parser, SQL analyzer, pattern detector
- **LLM**: Optional boost for complex SQL analysis

### 2. BuilderAgent

Generates dbt models from analysis:

- **Input**: Analysis results
- **Output**: SQL models, YAML schemas, source definitions
- **Tools**: Template generator, expression converter
- **LLM**: Optional code generation enhancement

### 3. ExecutorAgent

Writes files and runs dbt commands:

- **Input**: Generated files
- **Output**: Execution results, dbt run status
- **Requires**: Human approval before writing
- **Tools**: File writer, dbt runner

### 4. ValidatorAgent

Validates dbt output against source data:

- **Input**: Model mappings, DB connections
- **Output**: Validation report
- **Checks**: Row counts, primary keys, checksums

### 5. DiagnoserAgent

Analyzes failures and suggests fixes:

- **Input**: Validation failures
- **Output**: Diagnosis report, suggested remediations
- **LLM**: Root cause analysis and fix generation

## Configuration

### Agent Configuration (`config/agents.yaml`)

```yaml
agents:
  analyzer:
    detect_incremental: true
    detect_scd: true
    use_llm_analysis: true

  builder:
    generate_staging: true
    generate_core: true
    use_llm_generation: true

  executor:
    require_approval: true
    write_backup: false
    dbt_commands:
      - deps
      - run
      - test

  validator:
    validate_row_counts: true
    row_count_tolerance: 0.01
    validate_primary_keys: true
    validate_checksums: true

  diagnoser:
    max_retries: 3
    generate_investigation_queries: true
    use_llm_diagnosis: true

llm:
  provider: openai
  model: gpt-4o
  temperature: 0.2
  max_tokens: 4096

memory:
  short_term_capacity: 100
  short_term_ttl_seconds: 3600
  long_term_storage: ./memory

tracing:
  enabled: true
  sample_rate: 1.0
  export_path: ./traces
```

## SSIS to dbt Mapping

| SSIS Component | dbt Output | Notes |
|----------------|------------|-------|
| Data Flow Task | `stg_*.sql` | Staging model with source ref |
| Execute SQL Task | `fct_*.sql` / `dim_*.sql` | Core model based on SQL pattern |
| Lookup Transform | `LEFT JOIN ref()` | Converted to SQL join |
| Derived Column | SQL expression | SSIS expressions mapped |
| Conditional Split | `CASE WHEN` | Multiple outputs as CASE |
| Merge Join | `JOIN` | Standard SQL join |
| Sort | `ORDER BY` | In model or as macro |
| Aggregate | `GROUP BY` | Aggregate model |

## Project Structure

```
ssis-to-dbt/
├── src/
│   ├── agents/
│   │   ├── core/              # Advanced agent framework
│   │   │   ├── tools.py       # Tool registry and ReAct pattern
│   │   │   ├── memory.py      # Multi-level memory system
│   │   │   ├── hooks.py       # Lifecycle hooks
│   │   │   ├── events.py      # Event bus
│   │   │   ├── tracing.py     # Distributed tracing
│   │   │   ├── agent.py       # Advanced base agent
│   │   │   └── graph.py       # Graph-based orchestration
│   │   ├── analyzer.py        # SSIS analysis agent
│   │   ├── builder.py         # dbt generation agent
│   │   ├── executor.py        # Execution agent
│   │   ├── validator.py       # Validation agent
│   │   ├── diagnoser.py       # Diagnosis agent
│   │   ├── orchestrator.py    # Pipeline orchestrator
│   │   └── llm/               # LLM integration
│   │       ├── openai_client.py
│   │       └── prompts.py
│   ├── parser/                # SSIS XML parsing
│   │   ├── ssis_parser.py
│   │   ├── models.py
│   │   └── type_mappings.py
│   ├── cli/                   # CLI and approval UI
│   └── connections/           # Database connections
├── dbt_project/
│   └── models/
│       ├── sources/           # src_*.yml
│       ├── staging/           # stg_*.sql
│       └── core/              # fct_*, dim_*, agg_*
├── config/
│   └── agents.yaml            # Agent configuration
├── ui/                        # React dashboard
├── tests/                     # Test suite
└── output/                    # Generated files
```

## CLI Commands

```bash
# Basic migration
python run_agents.py <input_dir> --output <output_dir>

# With options
python run_agents.py ./ssis_packages \
    --output ./output \
    --dbt-project ./dbt_project \
    --auto-approve \
    --no-llm \
    --verbose

# Resume a previous run
python run_agents.py --resume <run_id>

# List all runs
python run_agents.py --list-runs

# Parser only (without agents)
python3 -m src.parser.ssis_parser ./samples/ssis_packages -o ./output -v
```

## Environment Variables

```bash
# LLM Configuration
OPENAI_API_KEY=sk-...

# Source Database
SOURCE_DB_HOST=localhost
SOURCE_DB_PORT=1433
SOURCE_DB_NAME=source_db
SOURCE_DB_USER=user
SOURCE_DB_PASSWORD=password

# Target Database
TARGET_DB_HOST=localhost
TARGET_DB_PORT=1433
TARGET_DB_NAME=target_db
TARGET_DB_USER=user
TARGET_DB_PASSWORD=password
```

## Advanced Usage

### Custom Tool Registration

```python
from src.agents.core import Tool, ToolRegistry, ToolCategory

class CustomValidationTool(Tool):
    name = "custom_validator"
    description = "Custom validation logic"
    category = ToolCategory.VALIDATION

    async def execute(self, model_name: str, rules: list) -> dict:
        # Custom validation implementation
        return {"passed": True, "violations": []}

registry = ToolRegistry()
registry.register(CustomValidationTool())
```

### Custom Hooks

```python
from src.agents.core import HookManager, HookType

async def slack_notification_hook(context):
    """Send Slack notification on completion."""
    if context.hook_type == HookType.AFTER_EXECUTE:
        await send_slack_message(
            f"Agent {context.agent_name} completed",
            context.data
        )
    return context

hooks = HookManager()
hooks.register(
    name="slack_notify",
    hook_type=HookType.AFTER_EXECUTE,
    handler=slack_notification_hook
)
```

### Custom Memory Store

```python
from src.agents.core.memory import MemoryStore, MemoryEntry

class RedisMemoryStore(MemoryStore):
    """Redis-backed memory store for distributed deployments."""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def store(self, entry: MemoryEntry) -> None:
        await self.redis.set(entry.id, entry.to_dict())

    async def retrieve(self, id: str) -> MemoryEntry:
        data = await self.redis.get(id)
        return MemoryEntry.from_dict(data)
```

## Testing

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run with coverage
python3 -m pytest tests/ --cov=src --cov-report=html

# Run specific test file
python3 -m pytest tests/test_agents.py -v
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) for details.

## References

- [dbt Documentation](https://docs.getdbt.com/)
- [SSIS Package Format](https://docs.microsoft.com/en-us/sql/integration-services/)
- [LangGraph](https://langchain-ai.github.io/langgraph/)
- [Claude Agent SDK](https://docs.anthropic.com/en/docs/agents-and-tools)
- [OpenTelemetry](https://opentelemetry.io/)
