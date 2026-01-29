{{
    config(
        materialized='view',
        schema='staging'
    )
}}

/*
    Staging model for sales transactions
    Source: SalesFactETL.dtsx -> Load Sales Facts (Data Flow Task)

    Transformations applied:
    - Type casting to target SQL Server types
    - Column renaming to snake_case
    - Filter: IsVoided = 0 (non-voided transactions only)
    - Derived columns: gross_amount, discount_amount, net_amount
*/

WITH source_data AS (
    SELECT
        SaleID,
        CustomerID,
        ProductID,
        SaleDate,
        Quantity,
        UnitPrice,
        DiscountPercent,
        SalesRepID,
        StoreID,
        IsVoided
    FROM {{ source('sales', 'transactions') }}
    WHERE IsVoided = 0  -- Filter from SSIS source query
),

cleaned AS (
    SELECT
        -- Primary key
        CAST(SaleID AS BIGINT) AS sale_id,

        -- Foreign keys
        CAST(CustomerID AS INT) AS customer_id,
        CAST(ProductID AS INT) AS product_id,
        CAST(SalesRepID AS INT) AS sales_rep_id,
        CAST(StoreID AS INT) AS store_id,

        -- Date
        CAST(SaleDate AS DATETIME) AS sale_date,

        -- Measures
        CAST(Quantity AS INT) AS quantity,
        CAST(UnitPrice AS NUMERIC(18,2)) AS unit_price,
        CAST(COALESCE(DiscountPercent, 0) AS NUMERIC(5,2)) AS discount_percent
    FROM source_data
),

with_derived_columns AS (
    SELECT
        sale_id,
        customer_id,
        product_id,
        sales_rep_id,
        store_id,
        sale_date,
        quantity,
        unit_price,
        discount_percent,

        -- Derived columns from SSIS "Calculate Amounts" transform
        -- Expression: [Quantity] * [UnitPrice]
        CAST(quantity * unit_price AS NUMERIC(18,2)) AS gross_amount,

        -- Expression: ([Quantity] * [UnitPrice]) * ([DiscountPercent] / 100)
        CAST((quantity * unit_price) * (discount_percent / 100.0) AS NUMERIC(18,2)) AS discount_amount,

        -- Expression: ([Quantity] * [UnitPrice]) - (([Quantity] * [UnitPrice]) * ([DiscountPercent] / 100))
        CAST((quantity * unit_price) - ((quantity * unit_price) * (discount_percent / 100.0)) AS NUMERIC(18,2)) AS net_amount
    FROM cleaned
)

SELECT * FROM with_derived_columns
