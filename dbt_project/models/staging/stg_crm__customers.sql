{{
    config(
        materialized='view',
        schema='staging'
    )
}}

/*
    Staging model for CRM customers
    Source: CustomerDataLoad.dtsx -> Load Customer Data (Data Flow Task)

    Transformations applied:
    - Type casting to target SQL Server types
    - Column renaming to snake_case
    - Basic cleaning (TRIM, NULLIF)
    - Derived columns: full_name, email_domain
*/

WITH source_data AS (
    SELECT
        CustomerID,
        FirstName,
        LastName,
        Email,
        Phone,
        CreatedDate,
        ModifiedDate
    FROM {{ source('crm', 'customers') }}
),

cleaned AS (
    SELECT
        -- Primary key
        CAST(CustomerID AS INT) AS customer_id,

        -- String fields with cleaning
        CAST(NULLIF(TRIM(FirstName), '') AS NVARCHAR(50)) AS first_name,
        CAST(NULLIF(TRIM(LastName), '') AS NVARCHAR(50)) AS last_name,
        CAST(NULLIF(TRIM(Email), '') AS NVARCHAR(255)) AS email,
        CAST(NULLIF(TRIM(Phone), '') AS NVARCHAR(20)) AS phone,

        -- Timestamps
        CAST(CreatedDate AS DATETIME) AS created_date,
        CAST(ModifiedDate AS DATETIME) AS modified_date
    FROM source_data
),

with_derived_columns AS (
    SELECT
        customer_id,
        first_name,
        last_name,
        email,
        phone,
        created_date,
        modified_date,

        -- Derived columns from SSIS Derived Column transform
        -- Expression: [FirstName] + " " + [LastName]
        CONCAT(first_name, ' ', last_name) AS full_name,

        -- Expression: SUBSTRING([Email], FINDSTRING([Email], "@", 1) + 1, LEN([Email]))
        CASE
            WHEN CHARINDEX('@', email) > 0
            THEN SUBSTRING(email, CHARINDEX('@', email) + 1, LEN(email))
            ELSE NULL
        END AS email_domain
    FROM cleaned
)

SELECT * FROM with_derived_columns
