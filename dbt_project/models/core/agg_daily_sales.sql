{{
    config(
        materialized='table',
        schema='core',
        unique_key=['date_key', 'product_key', 'customer_key']
    )
}}

/*
    Daily Sales Aggregate
    Source: SalesFactETL.dtsx -> "Update Aggregates" (Execute SQL Task)

    Original SSIS SQL:
    DELETE FROM agg.DailySales WHERE SaleDate BETWEEN @StartDate AND @EndDate;

    INSERT INTO agg.DailySales (DateKey, ProductKey, CustomerKey, TotalQuantity, TotalNetAmount, TransactionCount)
    SELECT
        DateKey,
        ProductKey,
        CustomerKey,
        SUM(Quantity) AS TotalQuantity,
        SUM(NetAmount) AS TotalNetAmount,
        COUNT(*) AS TransactionCount
    FROM fact.Sales
    WHERE DateKey IN (SELECT DateKey FROM dim.Date WHERE FullDate BETWEEN @StartDate AND @EndDate)
    GROUP BY DateKey, ProductKey, CustomerKey;

    dbt Implementation:
    - Uses ref() for fact table
    - Date range can be controlled via dbt vars
    - Full refresh replaces DELETE+INSERT pattern
*/

WITH sales_facts AS (
    SELECT
        date_key,
        product_key,
        customer_key,
        quantity,
        net_amount
    FROM {{ ref('fct_sales') }}
    {% if is_incremental() %}
    WHERE date_key >= (
        SELECT MIN(DateKey)
        FROM {{ source('datawarehouse', 'dim_date') }}
        WHERE FullDate >= '{{ var("start_date") }}'
    )
    AND date_key <= (
        SELECT MAX(DateKey)
        FROM {{ source('datawarehouse', 'dim_date') }}
        WHERE FullDate <= '{{ var("end_date") }}'
    )
    {% endif %}
),

aggregated AS (
    SELECT
        date_key,
        product_key,
        customer_key,
        SUM(quantity) AS total_quantity,
        SUM(net_amount) AS total_net_amount,
        COUNT(*) AS transaction_count
    FROM sales_facts
    GROUP BY
        date_key,
        product_key,
        customer_key
),

final AS (
    SELECT
        -- Composite key
        {{ dbt_utils.generate_surrogate_key([
            'date_key',
            'product_key',
            'customer_key'
        ]) }} AS daily_sales_key,

        -- Dimensions
        date_key,
        product_key,
        customer_key,

        -- Measures
        total_quantity,
        total_net_amount,
        transaction_count,

        -- Derived
        CASE
            WHEN transaction_count > 0
            THEN CAST(total_net_amount / transaction_count AS NUMERIC(18,2))
            ELSE 0
        END AS avg_transaction_value,

        -- Audit
        CURRENT_TIMESTAMP AS loaded_at
    FROM aggregated
)

SELECT * FROM final
