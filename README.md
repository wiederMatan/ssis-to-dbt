# SSIS-to-dbt Migration Factory

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Say goodbye to manual SSIS conversions.** This tool automatically transforms your SQL Server Integration Services packages into clean, maintainable dbt models—so you can focus on building, not migrating.

---

## What Does It Do?

If you've ever stared at hundreds of SSIS packages wondering how you'll ever migrate them to a modern data stack, this is for you.

**In a nutshell:** Point it at your SSIS packages, and it generates ready-to-run dbt models complete with sources, staging layers, and documentation.

| Your Input | What You Get |
|------------|--------------|
| `.dtsx` SSIS packages | SQL models (`stg_*.sql`, `fct_*.sql`, `dim_*.sql`) |
| Complex data flows | Clean `ref()` and `source()` relationships |
| Lookup transforms | Proper SQL JOINs |
| SSIS expressions | Translated SQL expressions |

---

## Getting Started

### 1. Install

```bash
git clone https://github.com/wiederMatan/ssis-to-dbt.git
cd ssis-to-dbt
pip install -r requirements.txt
```

### 2. Run Your First Migration

```bash
# Basic usage - just point to your SSIS packages folder
python run_agents.py ./your_ssis_packages --output ./output

# Want AI-assisted analysis? Add your API key
export OPENAI_API_KEY="your-api-key"
python run_agents.py ./your_ssis_packages --output ./output
```

### 3. Check Your Results

Your generated dbt project appears in the output folder:
- `models/sources/` — Source definitions
- `models/staging/` — Staging models from data flows
- `models/core/` — Fact and dimension tables

Then just run dbt:
```bash
cd dbt_project
dbt deps && dbt run
```

That's it! You're migrated.

---

## How It Works

The migration runs through a pipeline of specialized agents, each handling one part of the job:

```
   Your SSIS         Analyzer        Builder         Executor        Validator
   Packages    --->   Agent    --->   Agent    --->   Agent    --->   Agent
                        |                                               |
                        |              Diagnoser                        |
                        +------------->  Agent  <-----------------------+
                                     (if needed)
```

**Analyzer** reads your SSIS packages and figures out what's what—tables, transforms, dependencies.

**Builder** generates the dbt models, choosing the right patterns (staging vs. core, fact vs. dimension).

**Executor** writes the files and optionally runs dbt commands.

**Validator** checks that the output matches expectations.

**Diagnoser** jumps in if something goes wrong, analyzes the issue, and suggests fixes.

---

## Configuration Options

### Command Line

```bash
# Full control
python run_agents.py ./ssis_packages \
    --output ./output \
    --dbt-project ./dbt_project \
    --auto-approve \      # Skip confirmation prompts (great for CI/CD)
    --no-llm \            # Run without AI features
    --verbose             # See what's happening

# Resume a previous run
python run_agents.py --resume <run_id>

# Just parse, don't generate
python3 -m src.parser.ssis_parser ./samples/ssis_packages -o ./output -v
```

### AI Providers

Pick your preferred AI backend—or skip AI entirely for deterministic parsing:

| Provider | Setup | Best For |
|----------|-------|----------|
| **OpenAI** | `export OPENAI_API_KEY="sk-..."` | Production use, high accuracy |
| **Google Vertex AI** | `export GOOGLE_CLOUD_PROJECT="..."` | GCP-native environments |
| **Ollama** | `ollama serve` (local) | Privacy, cost savings |
| **None** | `--no-llm` flag | Deterministic, no API needed |

---

## What Gets Converted?

Here's how SSIS components map to dbt:

| SSIS Component | dbt Output | How It's Handled |
|----------------|------------|------------------|
| Data Flow Task | `stg_*.sql` | Becomes a staging model |
| Execute SQL Task | `fct_*.sql` or `dim_*.sql` | Core model based on the SQL |
| Lookup Transform | `LEFT JOIN ref()` | Proper SQL join |
| Derived Column | SQL expression | Expression translation |
| Conditional Split | `CASE WHEN` | Multiple outputs as CASE |
| Merge Join | `JOIN` | Standard SQL join |
| Aggregate | `GROUP BY` | Aggregate model |

### Type Mappings

SSIS types are automatically converted:

| SSIS | SQL Server |
|------|------------|
| DT_WSTR | NVARCHAR |
| DT_STR | VARCHAR |
| DT_I4 | INT |
| DT_I8 | BIGINT |
| DT_NUMERIC | NUMERIC |
| DT_DBTIMESTAMP | DATETIME |
| DT_BOOL | BIT |

---

## Project Layout

```
ssis-to-dbt/
├── src/
│   ├── agents/           # The smart bits - analysis, generation, validation
│   │   ├── core/         # Framework internals (tools, memory, tracing)
│   │   └── llm/          # AI provider integrations
│   ├── parser/           # SSIS XML parsing logic
│   └── cli/              # Command-line interface
├── dbt_project/          # Your generated dbt project lands here
│   └── models/
│       ├── sources/      # src_*.yml
│       ├── staging/      # stg_*.sql
│       └── core/         # fct_*, dim_*, agg_*
├── config/               # Configuration files
├── output/               # Parsing reports and artifacts
└── tests/                # Test suite
```

---

## For Developers

<details>
<summary><strong>Extending the Framework</strong></summary>

### Custom Tools

```python
from src.agents.core import ToolRegistry, tool, ToolCategory

@tool(name="my_validator", category=ToolCategory.VALIDATION)
async def my_validator(model_name: str) -> dict:
    # Your validation logic here
    return {"passed": True}

registry = ToolRegistry()
registry.register(my_validator)
```

### Custom Hooks

```python
from src.agents.core import HookManager, HookType

async def notify_on_complete(context):
    print(f"Done: {context.agent_name}")
    return context

hooks = HookManager()
hooks.register("notifier", HookType.AFTER_EXECUTE, notify_on_complete)
```

### Memory System

The framework includes multi-level memory (short-term, long-term, semantic, episodic) for complex migrations that need context across steps.

### Tracing

OpenTelemetry-compatible tracing built in—great for debugging and monitoring production runs.

</details>

<details>
<summary><strong>Running Tests</strong></summary>

```bash
# All tests
python3 -m pytest tests/ -v

# With coverage
python3 -m pytest tests/ --cov=src --cov-report=html
```

</details>

<details>
<summary><strong>Environment Variables Reference</strong></summary>

```bash
# AI Providers (pick one)
OPENAI_API_KEY=sk-...
GOOGLE_CLOUD_PROJECT=your-project
GOOGLE_APPLICATION_CREDENTIALS=/path/to/creds.json
OLLAMA_HOST=http://localhost:11434

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

</details>

---

## Contributing

Contributions welcome! Here's how:

1. Fork the repo
2. Create your branch (`git checkout -b feature/cool-thing`)
3. Make your changes
4. Push and open a PR

---

## Learn More

- [dbt Documentation](https://docs.getdbt.com/)
- [SSIS Package Format](https://docs.microsoft.com/en-us/sql/integration-services/)
- [LangGraph](https://langchain-ai.github.io/langgraph/)

---

## License

MIT — use it however you'd like. See [LICENSE](LICENSE) for details.
