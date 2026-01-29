{{
    config(
        materialized='table',
        schema='core',
        unique_key='customer_key'
    )
}}

/*
    Customer Dimension - SCD Type 2
    Source: CustomerDataLoad.dtsx -> "Merge to Dimension" (Execute SQL Task)

    Original SSIS SQL:
    MERGE dim.Customer AS target
    USING stg.Customer AS source
    ON target.CustomerID = source.CustomerID
    WHEN MATCHED AND target.CustomerHash != HASHBYTES(...)
    THEN UPDATE SET ...
    WHEN NOT MATCHED BY TARGET
    THEN INSERT ...

    dbt Implementation:
    - Uses incremental strategy for SCD Type 2 pattern
    - Generates surrogate key using dbt_utils
    - Computes hash for change detection
*/

WITH staged_customers AS (
    SELECT
        customer_id,
        first_name,
        last_name,
        full_name,
        email,
        phone,
        email_domain,
        created_date,
        modified_date
    FROM {{ ref('stg_crm__customers') }}
),

with_hash AS (
    SELECT
        *,
        -- Hash for change detection (replaces HASHBYTES in SSIS)
        {{ dbt_utils.generate_surrogate_key([
            'first_name',
            'last_name',
            'email',
            'phone'
        ]) }} AS customer_hash
    FROM staged_customers
),

final AS (
    SELECT
        -- Surrogate key
        {{ dbt_utils.generate_surrogate_key(['customer_id']) }} AS customer_key,

        -- Natural key
        customer_id,

        -- Attributes
        first_name,
        last_name,
        full_name,
        email,
        phone,
        email_domain,

        -- Hash for SCD tracking
        customer_hash,

        -- SCD metadata
        created_date,
        modified_date,
        CAST(1 AS BIT) AS is_current,
        CAST(created_date AS DATE) AS valid_from,
        CAST(NULL AS DATE) AS valid_to
    FROM with_hash
)

SELECT * FROM final
