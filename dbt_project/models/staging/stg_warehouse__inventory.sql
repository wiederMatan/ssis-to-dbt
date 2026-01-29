{{
    config(
        materialized='view',
        schema='staging'
    )
}}

/*
    Staging model for inventory data from API
    Source: InventorySync.dtsx -> Load Inventory Updates (Data Flow Task)

    Transformations applied:
    - Type casting to target SQL Server types
    - Column renaming to snake_case
    - Filter: ProcessedFlag = 0 (unprocessed records only)
    - Derived columns: inventory_value, stock_status, days_of_supply
*/

WITH source_data AS (
    SELECT
        ProductSKU,
        WarehouseCode,
        QuantityOnHand,
        QuantityReserved,
        QuantityAvailable,
        LastCountDate,
        ReorderPoint,
        MaxStockLevel,
        UnitCost,
        ProcessedFlag
    FROM {{ source('warehouse', 'inventory_api') }}
    WHERE ProcessedFlag = 0  -- Filter from SSIS source query
),

cleaned AS (
    SELECT
        -- Natural keys
        CAST(NULLIF(TRIM(ProductSKU), '') AS NVARCHAR(50)) AS product_sku,
        CAST(NULLIF(TRIM(WarehouseCode), '') AS NVARCHAR(10)) AS warehouse_code,

        -- Quantity fields
        CAST(COALESCE(QuantityOnHand, 0) AS INT) AS quantity_on_hand,
        CAST(COALESCE(QuantityReserved, 0) AS INT) AS quantity_reserved,
        CAST(COALESCE(QuantityAvailable, 0) AS INT) AS quantity_available,

        -- Inventory management fields
        CAST(COALESCE(ReorderPoint, 0) AS INT) AS reorder_point,
        CAST(COALESCE(MaxStockLevel, 0) AS INT) AS max_stock_level,
        CAST(COALESCE(UnitCost, 0) AS NUMERIC(18,4)) AS unit_cost,

        -- Date
        CAST(LastCountDate AS DATE) AS last_count_date
    FROM source_data
),

with_derived_columns AS (
    SELECT
        product_sku,
        warehouse_code,
        quantity_on_hand,
        quantity_reserved,
        quantity_available,
        reorder_point,
        max_stock_level,
        unit_cost,
        last_count_date,

        -- Derived columns from SSIS "Calculate Metrics" transform
        -- Expression: [QuantityOnHand] * [UnitCost]
        CAST(quantity_on_hand * unit_cost AS NUMERIC(18,4)) AS inventory_value,

        -- Expression: [QuantityAvailable] <= 0 ? "Out of Stock" : ([QuantityAvailable] < [ReorderPoint] ? "Low Stock" : "In Stock")
        CASE
            WHEN quantity_available <= 0 THEN 'Out of Stock'
            WHEN quantity_available < reorder_point THEN 'Low Stock'
            ELSE 'In Stock'
        END AS stock_status,

        -- Expression: [ReorderPoint] > 0 ? ([QuantityAvailable] / [ReorderPoint]) * 30 : 0
        CASE
            WHEN reorder_point > 0
            THEN CAST((quantity_available * 1.0 / reorder_point) * 30 AS INT)
            ELSE 0
        END AS days_of_supply
    FROM cleaned
)

SELECT * FROM with_derived_columns
