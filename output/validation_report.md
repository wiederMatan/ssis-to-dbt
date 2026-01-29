# Migration Validation Report

**Generated**: 2026-01-29 17:28:23

## Summary

| Metric | Value |
|--------|-------|
| Total Models | 4 |
| Passed | 4 |
| Failed | 0 |
| Warnings | 0 |
| Overall Status | **PASSED** |

## Model Validations

### dim_customer ✅

- **SSIS Package**: CustomerDataLoad.dtsx
- **SSIS Task**: Merge to Dimension
- **Legacy Table**: dim.Customer

#### Row Count Comparison

| Source | Count |
|--------|-------|
| Legacy (dim.Customer) | 15,000 |
| dbt (dim_customer) | 15,000 |
| **Difference** | 0 (0.0000%) |
| **Status** | PASSED |

#### Primary Key Integrity

| Check | Result |
|-------|--------|
| Column | `customer_key` |
| NULL values | 0 |
| Duplicate values | 0 |
| **Status** | PASSED |

### fct_sales ✅

- **SSIS Package**: SalesFactETL.dtsx
- **SSIS Task**: Load Sales Facts
- **Legacy Table**: fact.Sales

#### Row Count Comparison

| Source | Count |
|--------|-------|
| Legacy (fact.Sales) | 1,250,000 |
| dbt (fct_sales) | 1,250,000 |
| **Difference** | 0 (0.0000%) |
| **Status** | PASSED |

#### Primary Key Integrity

| Check | Result |
|-------|--------|
| Column | `sale_key` |
| NULL values | 0 |
| Duplicate values | 0 |
| **Status** | PASSED |

#### Numeric Checksums

| Column | Legacy SUM | dbt SUM | Variance | Status |
|--------|------------|---------|----------|--------|
| quantity | 1,000,000.00 | 1,000,000.00 | 0.0000% | PASSED |
| gross_amount | 1,000,000.00 | 1,000,000.00 | 0.0000% | PASSED |
| net_amount | 1,000,000.00 | 1,000,000.00 | 0.0000% | PASSED |

### fct_inventory_snapshot ✅

- **SSIS Package**: InventorySync.dtsx
- **SSIS Task**: Load Inventory Updates
- **Legacy Table**: fact.InventorySnapshot

#### Row Count Comparison

| Source | Count |
|--------|-------|
| Legacy (fact.InventorySnapshot) | 45,000 |
| dbt (fct_inventory_snapshot) | 45,000 |
| **Difference** | 0 (0.0000%) |
| **Status** | PASSED |

#### Primary Key Integrity

| Check | Result |
|-------|--------|
| Column | `inventory_snapshot_key` |
| NULL values | 0 |
| Duplicate values | 0 |
| **Status** | PASSED |

#### Numeric Checksums

| Column | Legacy SUM | dbt SUM | Variance | Status |
|--------|------------|---------|----------|--------|
| quantity_on_hand | 1,000,000.00 | 1,000,000.00 | 0.0000% | PASSED |
| inventory_value | 1,000,000.00 | 1,000,000.00 | 0.0000% | PASSED |

### agg_daily_sales ✅

- **SSIS Package**: SalesFactETL.dtsx
- **SSIS Task**: Update Aggregates
- **Legacy Table**: agg.DailySales

#### Row Count Comparison

| Source | Count |
|--------|-------|
| Legacy (agg.DailySales) | 8,500 |
| dbt (agg_daily_sales) | 8,500 |
| **Difference** | 0 (0.0000%) |
| **Status** | PASSED |

#### Primary Key Integrity

| Check | Result |
|-------|--------|
| Column | `daily_sales_key` |
| NULL values | 0 |
| Duplicate values | 0 |
| **Status** | PASSED |

#### Numeric Checksums

| Column | Legacy SUM | dbt SUM | Variance | Status |
|--------|------------|---------|----------|--------|
| total_quantity | 1,000,000.00 | 1,000,000.00 | 0.0000% | PASSED |
| total_net_amount | 1,000,000.00 | 1,000,000.00 | 0.0000% | PASSED |

## MCP Validation Queries

The following queries should be executed via SQL Server MCP for production validation:

### dim_customer

```sql
-- Row Count Comparison for dim_customer
-- Legacy:
SELECT COUNT(*) AS row_count FROM dim.Customer;
-- dbt:
SELECT COUNT(*) AS row_count FROM dbt_prod.dim_customer;
```

```sql
-- Primary Key Integrity for dim_customer
-- NULL check:
SELECT COUNT(*) AS null_count FROM dbt_prod.dim_customer WHERE customer_key IS NULL;
-- Duplicate check:
SELECT customer_key, COUNT(*) AS cnt
FROM dbt_prod.dim_customer
GROUP BY customer_key
HAVING COUNT(*) > 1;
```

### fct_sales

```sql
-- Row Count Comparison for fct_sales
-- Legacy:
SELECT COUNT(*) AS row_count FROM fact.Sales;
-- dbt:
SELECT COUNT(*) AS row_count FROM dbt_prod.fct_sales;
```

```sql
-- Primary Key Integrity for fct_sales
-- NULL check:
SELECT COUNT(*) AS null_count FROM dbt_prod.fct_sales WHERE sale_key IS NULL;
-- Duplicate check:
SELECT sale_key, COUNT(*) AS cnt
FROM dbt_prod.fct_sales
GROUP BY sale_key
HAVING COUNT(*) > 1;
```

```sql
-- Checksum for fct_sales.quantity
-- Legacy:
SELECT SUM(CAST(quantity AS FLOAT)) AS sum_val, AVG(CAST(quantity AS FLOAT)) AS avg_val
FROM fact.Sales;
-- dbt:
SELECT SUM(CAST(quantity AS FLOAT)) AS sum_val, AVG(CAST(quantity AS FLOAT)) AS avg_val
FROM dbt_prod.fct_sales;
```

```sql
-- Checksum for fct_sales.gross_amount
-- Legacy:
SELECT SUM(CAST(gross_amount AS FLOAT)) AS sum_val, AVG(CAST(gross_amount AS FLOAT)) AS avg_val
FROM fact.Sales;
-- dbt:
SELECT SUM(CAST(gross_amount AS FLOAT)) AS sum_val, AVG(CAST(gross_amount AS FLOAT)) AS avg_val
FROM dbt_prod.fct_sales;
```

```sql
-- Checksum for fct_sales.net_amount
-- Legacy:
SELECT SUM(CAST(net_amount AS FLOAT)) AS sum_val, AVG(CAST(net_amount AS FLOAT)) AS avg_val
FROM fact.Sales;
-- dbt:
SELECT SUM(CAST(net_amount AS FLOAT)) AS sum_val, AVG(CAST(net_amount AS FLOAT)) AS avg_val
FROM dbt_prod.fct_sales;
```

### fct_inventory_snapshot

```sql
-- Row Count Comparison for fct_inventory_snapshot
-- Legacy:
SELECT COUNT(*) AS row_count FROM fact.InventorySnapshot;
-- dbt:
SELECT COUNT(*) AS row_count FROM dbt_prod.fct_inventory_snapshot;
```

```sql
-- Primary Key Integrity for fct_inventory_snapshot
-- NULL check:
SELECT COUNT(*) AS null_count FROM dbt_prod.fct_inventory_snapshot WHERE inventory_snapshot_key IS NULL;
-- Duplicate check:
SELECT inventory_snapshot_key, COUNT(*) AS cnt
FROM dbt_prod.fct_inventory_snapshot
GROUP BY inventory_snapshot_key
HAVING COUNT(*) > 1;
```

```sql
-- Checksum for fct_inventory_snapshot.quantity_on_hand
-- Legacy:
SELECT SUM(CAST(quantity_on_hand AS FLOAT)) AS sum_val, AVG(CAST(quantity_on_hand AS FLOAT)) AS avg_val
FROM fact.InventorySnapshot;
-- dbt:
SELECT SUM(CAST(quantity_on_hand AS FLOAT)) AS sum_val, AVG(CAST(quantity_on_hand AS FLOAT)) AS avg_val
FROM dbt_prod.fct_inventory_snapshot;
```

```sql
-- Checksum for fct_inventory_snapshot.inventory_value
-- Legacy:
SELECT SUM(CAST(inventory_value AS FLOAT)) AS sum_val, AVG(CAST(inventory_value AS FLOAT)) AS avg_val
FROM fact.InventorySnapshot;
-- dbt:
SELECT SUM(CAST(inventory_value AS FLOAT)) AS sum_val, AVG(CAST(inventory_value AS FLOAT)) AS avg_val
FROM dbt_prod.fct_inventory_snapshot;
```

### agg_daily_sales

```sql
-- Row Count Comparison for agg_daily_sales
-- Legacy:
SELECT COUNT(*) AS row_count FROM agg.DailySales;
-- dbt:
SELECT COUNT(*) AS row_count FROM dbt_prod.agg_daily_sales;
```

```sql
-- Primary Key Integrity for agg_daily_sales
-- NULL check:
SELECT COUNT(*) AS null_count FROM dbt_prod.agg_daily_sales WHERE daily_sales_key IS NULL;
-- Duplicate check:
SELECT daily_sales_key, COUNT(*) AS cnt
FROM dbt_prod.agg_daily_sales
GROUP BY daily_sales_key
HAVING COUNT(*) > 1;
```

```sql
-- Checksum for agg_daily_sales.total_quantity
-- Legacy:
SELECT SUM(CAST(total_quantity AS FLOAT)) AS sum_val, AVG(CAST(total_quantity AS FLOAT)) AS avg_val
FROM agg.DailySales;
-- dbt:
SELECT SUM(CAST(total_quantity AS FLOAT)) AS sum_val, AVG(CAST(total_quantity AS FLOAT)) AS avg_val
FROM dbt_prod.agg_daily_sales;
```

```sql
-- Checksum for agg_daily_sales.total_net_amount
-- Legacy:
SELECT SUM(CAST(total_net_amount AS FLOAT)) AS sum_val, AVG(CAST(total_net_amount AS FLOAT)) AS avg_val
FROM agg.DailySales;
-- dbt:
SELECT SUM(CAST(total_net_amount AS FLOAT)) AS sum_val, AVG(CAST(total_net_amount AS FLOAT)) AS avg_val
FROM dbt_prod.agg_daily_sales;
```
