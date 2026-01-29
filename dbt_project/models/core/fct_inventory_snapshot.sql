{{
    config(
        materialized='table',
        schema='core',
        unique_key='inventory_snapshot_key'
    )
}}

/*
    Inventory Snapshot Fact Table
    Source: InventorySync.dtsx -> "Load Inventory Updates" (Data Flow Task)

    Original SSIS Data Flow:
    1. OLE DB Source: Read from stg.InventoryAPI (ProcessedFlag = 0)
    2. Lookup Product: JOIN to dim.Product for ProductKey using SKU
    3. Lookup Warehouse: JOIN to dim.Warehouse for WarehouseKey using Code
    4. Derived Column: Calculate InventoryValue, StockStatus, DaysOfSupply
    5. OLE DB Destination: fact.InventorySnapshot

    NOTE: The SSIS Script Task "Call Inventory API" that populates
    stg.InventoryAPI requires manual implementation (Python script or
    Airbyte/Fivetran connector).

    dbt Implementation:
    - Uses ref() for staging model
    - JOINs replace SSIS Lookup transforms
    - Derived calculations in staging model
*/

WITH staged_inventory AS (
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
        inventory_value,
        stock_status,
        days_of_supply
    FROM {{ ref('stg_warehouse__inventory') }}
),

-- Lookup Product dimension key (replaces SSIS Lookup transform)
with_product_key AS (
    SELECT
        s.*,
        p.ProductKey AS product_key
    FROM staged_inventory s
    LEFT JOIN {{ source('datawarehouse', 'dim_product') }} p
        ON s.product_sku = p.SKU
        AND p.IsActive = 1
),

-- Lookup Warehouse dimension key (replaces SSIS Lookup transform)
with_warehouse_key AS (
    SELECT
        s.*,
        w.WarehouseKey AS warehouse_key
    FROM with_product_key s
    LEFT JOIN {{ source('datawarehouse', 'dim_warehouse') }} w
        ON s.warehouse_code = w.WarehouseCode
),

-- Get snapshot date key
with_date_key AS (
    SELECT
        s.*,
        d.DateKey AS snapshot_date_key
    FROM with_warehouse_key s
    LEFT JOIN {{ source('datawarehouse', 'dim_date') }} d
        ON CAST(GETDATE() AS DATE) = d.FullDate
),

final AS (
    SELECT
        -- Surrogate key
        {{ dbt_utils.generate_surrogate_key([
            'product_sku',
            'warehouse_code',
            'last_count_date'
        ]) }} AS inventory_snapshot_key,

        -- Dimension keys (from Lookups)
        product_key,
        warehouse_key,
        snapshot_date_key,

        -- Degenerate dimensions
        product_sku,
        warehouse_code,
        last_count_date,

        -- Measures
        quantity_on_hand,
        quantity_reserved,
        quantity_available,
        reorder_point,
        max_stock_level,
        unit_cost,
        inventory_value,

        -- Calculated attributes
        stock_status,
        days_of_supply,

        -- Audit
        CURRENT_TIMESTAMP AS loaded_at
    FROM with_date_key
)

SELECT * FROM final
