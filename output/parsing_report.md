# SSIS Package Parsing Report

**Generated**: 2026-01-31 12:09:59

## Summary

| Metric | Count |
|--------|-------|
| Total Packages Parsed | 3 |
| Execute SQL Tasks | 6 |
| Data Flow Tasks | 3 |
| Script Tasks (Manual Review) | 1 |
| Tables Referenced | 3 |
| Total Warnings | 2 |

## Package Details

### InventorySync

- **File**: `InventorySync.dtsx`
- **Size**: 17.6 KB
- **Description**: Inventory synchronization with external API - includes Script Task for manual review
- **Creator**: ETLDeveloper
- **Created**: 2024-02-01T09:00:00

#### Components

| Component Type | Count |
|----------------|-------|
| Connection Managers | 4 |
| Variables | 4 |
| Execute SQL Tasks | 2 |
| Data Flow Tasks | 1 |
| Script Tasks | 1 |
| Send Mail Tasks | 1 |

#### Connection Managers

- **InventoryAPI**: `N/A` / `N/A`
- ****: `N/A` / `N/A`
- **WarehouseDW**: `DWSRV` / `WarehouseDM`
- ****: `N/A` / `N/A`

#### Warnings

- ⚠️ Script Task 'Call Inventory API' flagged for manual review
- ⚠️ Send Mail Task 'Send Completion Email' will not be converted

#### Execution Order

```
Get Last Sync Time → Call Inventory API
Call Inventory API → Load Inventory Updates
Load Inventory Updates → Update Sync Log
Update Sync Log → Send Completion Email
```

### CustomerDataLoad

- **File**: `CustomerDataLoad.dtsx`
- **Size**: 10.5 KB
- **Description**: Load customer data from CRM to DW dimension table
- **Creator**: ETLDeveloper
- **Created**: 2024-01-15T10:30:00

#### Components

| Component Type | Count |
|----------------|-------|
| Connection Managers | 4 |
| Variables | 2 |
| Execute SQL Tasks | 2 |
| Data Flow Tasks | 1 |
| Script Tasks | 0 |
| Send Mail Tasks | 0 |

#### Connection Managers

- **SourceDB**: `CRMSRV` / `CRM_Production`
- ****: `N/A` / `N/A`
- **TargetDW**: `DWSRV` / `DataWarehouse`
- ****: `N/A` / `N/A`

#### Execution Order

```
Truncate Staging → Load Customer Data
Load Customer Data → Merge to Dimension
```

### SalesFactETL

- **File**: `SalesFactETL.dtsx`
- **Size**: 17.8 KB
- **Description**: Sales fact table ETL with dimension lookups
- **Creator**: ETLDeveloper
- **Created**: 2024-01-20T14:00:00

#### Components

| Component Type | Count |
|----------------|-------|
| Connection Managers | 4 |
| Variables | 3 |
| Execute SQL Tasks | 2 |
| Data Flow Tasks | 1 |
| Script Tasks | 0 |
| Send Mail Tasks | 0 |

#### Connection Managers

- **SalesDB**: `SALESSRV` / `Sales_OLTP`
- ****: `N/A` / `N/A`
- **DW**: `DWSRV` / `DataWarehouse`
- ****: `N/A` / `N/A`

#### Execution Order

```
Pre-ETL Validation → Load Sales Facts
Load Sales Facts → Update Aggregates
```

## Tables Referenced

| Table | Referenced In |
|-------|---------------|
| `fact.InventorySnapshot` | Load Inventory Updates |
| `stg.Customer` | Load Customer Data |
| `fact.Sales` | Load Sales Facts |
