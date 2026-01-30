<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/wiederMatan/ssis-to-dbt/main/.github/banner-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/wiederMatan/ssis-to-dbt/main/.github/banner-light.svg">
  <img alt="SSIS to dbt Migration Factory" src="https://raw.githubusercontent.com/wiederMatan/ssis-to-dbt/main/.github/banner-light.svg">
</picture>

<div align="center">

# 🏭 SSIS-to-dbt Migration Factory

### _Transform your legacy SSIS packages into modern dbt models with confidence_

[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![dbt](https://img.shields.io/badge/dbt-1.5+-FF694B?style=for-the-badge&logo=dbt&logoColor=white)](https://www.getdbt.com/)
[![React](https://img.shields.io/badge/React-19.x-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-88%20Passing-success?style=for-the-badge&logo=pytest&logoColor=white)](tests/)

<br>

[🚀 Quick Start](#-quick-start) •
[📖 Documentation](#-documentation) •
[🎯 Features](#-features) •
[🖥️ Dashboard](#%EF%B8%8F-monitoring-dashboard) •
[🤝 Contributing](#-contributing)

<br>

---

</div>

## ✨ What is this?

**SSIS-to-dbt Migration Factory** is an intelligent automation tool that converts SQL Server Integration Services (SSIS) packages into modern **dbt** (data build tool) models — complete with validation, real-time monitoring, and AI-assisted analysis.

<div align="center">

```
   📦 SSIS Packages    ──────▶    🔄 Migration Engine    ──────▶    📊 dbt Models

   ┌─────────────┐               ┌─────────────────┐               ┌─────────────┐
   │  .dtsx      │               │  🤖 AI-Powered  │               │  stg_*.sql  │
   │  files      │    ═════▶     │    Analysis     │    ═════▶     │  fct_*.sql  │
   │             │               │  📋 Validation  │               │  dim_*.sql  │
   └─────────────┘               └─────────────────┘               └─────────────┘
```

</div>

---

## 🎯 Features

<table>
<tr>
<td width="50%">

### 🔍 Smart Parsing
- **XXE-Hardened** XML parsing for security
- Extracts connections, variables, data flows
- Handles complex SSIS components
- Type mapping (SSIS → SQL Server)

</td>
<td width="50%">

### 🏗️ Intelligent Scaffolding
- Generates **sources**, **staging**, and **core** models
- Follows dbt best practices
- Automatic naming conventions
- Schema documentation included

</td>
</tr>
<tr>
<td width="50%">

### ✅ Data Validation
- Row count comparison
- Primary key integrity checks
- Numeric checksum verification
- Detailed variance reporting

</td>
<td width="50%">

### 📊 Live Dashboard
- Real-time migration progress
- Package explorer with drill-down
- Validation result visualization
- SQL diff comparison view

</td>
</tr>
</table>

---

## 🚀 Quick Start

### Prerequisites

```bash
Python 3.9+  │  Node.js 18+  │  dbt-core 1.5+  │  SQL Server
```

### Installation

```bash
# 1️⃣ Clone the repository
git clone https://github.com/wiederMatan/ssis-to-dbt.git
cd ssis-to-dbt

# 2️⃣ Install dependencies
pip install -r requirements.txt

# 3️⃣ Start SQL Server (Docker)
docker-compose up -d

# 4️⃣ Run your first migration!
python3 run_agents.py ./samples/ssis_packages --output ./output
```

<details>
<summary>📦 <b>Full Setup Instructions</b></summary>

```bash
# Install dbt packages
cd dbt_project && dbt deps && cd ..

# Install UI dependencies (optional)
cd ui && npm install && cd ..

# Configure SQL Server connection
cp .env.example .env
# Edit .env with your credentials
```

</details>

---

## 🔄 Migration Pipeline

<div align="center">

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                                                                                  │
│   ╔═══════════╗      ╔═══════════╗      ╔═══════════╗      ╔═══════════╗       │
│   ║  Phase 1  ║ ───▶ ║  Phase 2  ║ ───▶ ║  Phase 3  ║ ───▶ ║  Phase 4  ║       │
│   ║  PARSE    ║      ║  BUILD    ║      ║  VALIDATE ║      ║  MONITOR  ║       │
│   ╚═══════════╝      ╚═══════════╝      ╚═══════════╝      ╚═══════════╝       │
│        │                  │                  │                  │               │
│        ▼                  ▼                  ▼                  ▼               │
│   ┌─────────┐        ┌─────────┐        ┌─────────┐        ┌─────────┐         │
│   │ Extract │        │ Generate│        │ Compare │        │  React  │         │
│   │ .dtsx   │        │ dbt SQL │        │  Data   │        │   UI    │         │
│   │ → JSON  │        │ models  │        │ Quality │        │Dashboard│         │
│   └─────────┘        └─────────┘        └─────────┘        └─────────┘         │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

</div>

---

## 🗺️ Component Mapping

> How SSIS components transform into dbt equivalents

| SSIS Component | → | dbt Equivalent | Notes |
|:---------------|:-:|:---------------|:------|
| 📊 **Data Flow Task** | → | `stg_*.sql` (view) | Staging model |
| 🔄 **Execute SQL (MERGE)** | → | `fct_*.sql` (table) | Fact table |
| 🔗 **Lookup Transform** | → | `LEFT JOIN ref()` | Dimension join |
| ➕ **Derived Column** | → | `CAST / expression` | SQL transformation |
| ⚠️ **Script Task** | → | `⚠️ Manual Review` | Requires conversion |

---

## 🖥️ Monitoring Dashboard

<div align="center">

### Main Dashboard

```
╔═══════════════════════════════════════════════════════════════════════════════════╗
║  ☰  SSIS-to-dbt Migration Dashboard                           🌙 Dark  ↻ Refresh  ║
╠═══════════════════════════════════════════════════════════════════════════════════╣
║                                                                                   ║
║   ┌─────────────┬─────────────┬─────────────┬─────────────┐                      ║
║   │ 📦 Packages │ 📊 Tasks    │ ✅ Converted │ ⚠️  Review  │                      ║
║   │      3      │     12      │      9      │      3      │                      ║
║   │ ▄▄▄▄▄▄▄▄▄▄ │ ▄▄▄▄▄▄▄▄▄▄ │ ▄▄▄▄▄▄▄▄▄▄ │ ▄▄▄▄▄▄▄▄▄▄ │                      ║
║   └─────────────┴─────────────┴─────────────┴─────────────┘                      ║
║                                                                                   ║
║   ┌─ Navigation ─────────────────────────────────────────────────────────────┐   ║
║   │  📦 Packages    📜 Live Logs    ✅ Validation    📝 SQL Diff            │   ║
║   └──────────────────────────────────────────────────────────────────────────┘   ║
║                                                                                   ║
║   ┌─ Package Explorer ───────────────────────────────────────────────────────┐   ║
║   │                                                                          │   ║
║   │  ▼ 📦 CustomerDataLoad.dtsx                           ✅ Migrated       │   ║
║   │    ├─ 🔌 Connection Managers: 2                                         │   ║
║   │    ├─ 📊 Data Flow Tasks: 1                                             │   ║
║   │    ├─ 🔄 Execute SQL Tasks: 2                                           │   ║
║   │    └─ ⚠️  Manual Review Items: 0                                         │   ║
║   │                                                                          │   ║
║   │  ▶ 📦 SalesFactETL.dtsx                               ✅ Migrated       │   ║
║   │  ▶ 📦 InventorySync.dtsx                              ⚠️  Needs Review   │   ║
║   │                                                                          │   ║
║   └──────────────────────────────────────────────────────────────────────────┘   ║
╚═══════════════════════════════════════════════════════════════════════════════════╝
```

### Validation Results

```
╔═══════════════════════════════════════════════════════════════════════════════════╗
║  ✅ Validation Results                                              All Passed!   ║
╠═══════════════════════════════════════════════════════════════════════════════════╣
║                                                                                   ║
║   ┌───────────────────────────────────────────────────────────────────────────┐  ║
║   │  Model              │ Row Count │ PK Check │ Checksum │     Status       │  ║
║   ├───────────────────────────────────────────────────────────────────────────┤  ║
║   │  🟢 dim_customer    │   ✅ OK   │   ✅ OK  │   ✅ OK  │  ✅ PASSED       │  ║
║   │  🟢 fct_sales       │   ✅ OK   │   ✅ OK  │   ✅ OK  │  ✅ PASSED       │  ║
║   │  🟢 fct_inventory   │   ✅ OK   │   ✅ OK  │   ✅ OK  │  ✅ PASSED       │  ║
║   │  🟢 agg_daily_sales │   ✅ OK   │   ✅ OK  │   ✅ OK  │  ✅ PASSED       │  ║
║   └───────────────────────────────────────────────────────────────────────────┘  ║
║                                                                                   ║
║   📊 dim_customer - Details                                                       ║
║   ┌───────────────────────────────────────────────────────────────────────────┐  ║
║   │  📈 Row Count: Legacy 12,847 → dbt 12,847  (Δ 0.00%)                     │  ║
║   │  🔑 Primary Key: 0 nulls, 0 duplicates                                    │  ║
║   │  🔢 Checksums: All columns within 0.01% tolerance                        │  ║
║   └───────────────────────────────────────────────────────────────────────────┘  ║
╚═══════════════════════════════════════════════════════════════════════════════════╝
```

</div>

---

## 📖 Documentation

### 📁 Project Structure

```
ssis-to-dbt/
├── 🐍 src/
│   ├── parser/           # SSIS XML parsing (XXE-hardened)
│   ├── agents/           # Multi-agent migration framework
│   ├── validation/       # Data validation logic
│   ├── connections/      # SQL Server connectivity
│   └── logging_config.py # Structured logging
│
├── 📊 dbt_project/
│   └── models/
│       ├── sources/      # src_*.yml definitions
│       ├── staging/      # stg_*.sql views
│       └── core/         # fct_*, dim_*, agg_* tables
│
├── ⚛️  ui/                # React monitoring dashboard
├── 🧪 tests/             # 88 pytest tests
├── 📦 samples/           # Sample SSIS packages
└── 📄 output/            # Generated reports
```

### 🔄 Type Mappings

| SSIS Type | SQL Server | Description |
|:----------|:-----------|:------------|
| `DT_WSTR` | `NVARCHAR` | Unicode string |
| `DT_STR` | `VARCHAR` | ANSI string |
| `DT_I4` | `INT` | 32-bit integer |
| `DT_I8` | `BIGINT` | 64-bit integer |
| `DT_NUMERIC` | `NUMERIC(p,s)` | Decimal number |
| `DT_DBTIMESTAMP` | `DATETIME` | Date and time |
| `DT_BOOL` | `BIT` | Boolean |
| `DT_GUID` | `UNIQUEIDENTIFIER` | UUID |

### 📛 Naming Conventions

| Layer | Pattern | Example |
|:------|:--------|:--------|
| 🗄️ Sources | `src_{system}_{table}` | `src_crm_customers` |
| 📥 Staging | `stg_{domain}__{entity}` | `stg_sales__transactions` |
| 📊 Facts | `fct_{business_process}` | `fct_sales` |
| 📐 Dimensions | `dim_{entity}` | `dim_customer` |
| 📈 Aggregates | `agg_{grain}_{subject}` | `agg_daily_sales` |

---

## 🔒 Security

<table>
<tr>
<td width="33%">

### 🛡️ XXE Protection
XML External Entity attacks are blocked with hardened parser settings

</td>
<td width="33%">

### 🔐 Credential Safety
Passwords auto-redacted from logs using `SecretStr` and sanitizing filters

</td>
<td width="33%">

### 🚫 SQL Injection
All identifiers validated before query execution

</td>
</tr>
</table>

---

## 🧪 Testing

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run with coverage
python3 -m pytest tests/ --cov=src --cov-report=html

# Current status: 88 tests passing ✅
```

---

## ⚠️ Manual Review Items

Some SSIS components require manual intervention:

| Component | Reason | Recommendation |
|:----------|:-------|:---------------|
| 📜 Script Task | Custom C#/VB.NET code | Convert to dbt macro or Python |
| 📧 Send Mail Task | Email notifications | Use external alerting (PagerDuty, etc.) |
| 📁 FTP Task | File transfers | Use dbt external tables |
| ⚙️ Execute Process | External programs | Move to orchestration layer |

---

## 🤝 Contributing

We love contributions! Here's how to get started:

```bash
# 1. Fork the repository
# 2. Create your feature branch
git checkout -b feature/amazing-feature

# 3. Make your changes and test
python3 -m pytest tests/

# 4. Commit with conventional commits
git commit -m 'feat: add amazing feature'

# 5. Push and create a PR
git push origin feature/amazing-feature
```

---

## 📜 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

### 🌟 Star us on GitHub!

If you find this project useful, please consider giving it a ⭐

<br>

Built with ❤️ using [dbt](https://www.getdbt.com/) • [lxml](https://lxml.de/) • [Pydantic](https://pydantic.dev/) • [React](https://react.dev/)

<br>

**[⬆ Back to Top](#-ssis-to-dbt-migration-factory)**

</div>
