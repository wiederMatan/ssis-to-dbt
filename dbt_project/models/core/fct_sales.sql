{{
    config(
        materialized='table',
        schema='core',
        unique_key='sale_key'
    )
}}

/*
    Sales Fact Table
    Source: SalesFactETL.dtsx -> "Load Sales Facts" (Data Flow Task)

    Original SSIS Data Flow:
    1. OLE DB Source: Extract sales transactions
    2. Lookup Customer: JOIN to dim.Customer for CustomerKey
    3. Lookup Product: JOIN to dim.Product for ProductKey
    4. Lookup Date: JOIN to dim.Date for DateKey
    5. Derived Column: Calculate GrossAmount, DiscountAmount, NetAmount
    6. OLE DB Destination: fact.Sales

    dbt Implementation:
    - Uses ref() for staging model
    - JOINs replace SSIS Lookup transforms
    - Derived calculations in staging model
*/

WITH staged_sales AS (
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
        gross_amount,
        discount_amount,
        net_amount
    FROM {{ ref('stg_sales__transactions') }}
),

-- Lookup Customer dimension key (replaces SSIS Lookup transform)
with_customer_key AS (
    SELECT
        s.*,
        c.customer_key
    FROM staged_sales s
    LEFT JOIN {{ ref('dim_customer') }} c
        ON s.customer_id = c.customer_id
        AND c.is_current = 1
),

-- Lookup Product dimension key (replaces SSIS Lookup transform)
with_product_key AS (
    SELECT
        s.*,
        p.ProductKey AS product_key,
        p.CategoryID AS category_id
    FROM with_customer_key s
    LEFT JOIN {{ source('datawarehouse', 'dim_product') }} p
        ON s.product_id = p.ProductID
        AND p.IsActive = 1
),

-- Lookup Date dimension key (replaces SSIS Lookup transform)
with_date_key AS (
    SELECT
        s.*,
        d.DateKey AS date_key
    FROM with_product_key s
    LEFT JOIN {{ source('datawarehouse', 'dim_date') }} d
        ON CAST(s.sale_date AS DATE) = d.FullDate
),

final AS (
    SELECT
        -- Surrogate key
        {{ dbt_utils.generate_surrogate_key(['sale_id']) }} AS sale_key,

        -- Natural key
        sale_id,

        -- Dimension keys (from Lookups)
        date_key,
        customer_key,
        product_key,
        category_id,
        sales_rep_id,
        store_id,

        -- Degenerate dimension
        sale_date,

        -- Measures
        quantity,
        unit_price,
        discount_percent,
        gross_amount,
        discount_amount,
        net_amount,

        -- Audit
        CURRENT_TIMESTAMP AS loaded_at
    FROM with_date_key
)

SELECT * FROM final
