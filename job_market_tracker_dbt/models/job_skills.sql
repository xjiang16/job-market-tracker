SELECT
    job_id,
    title,
    company,
    location,
    salary_min,
    salary_max,
    search_keyword,
    search_location,

    description ILIKE '%python%' AS mentions_python,
    description ILIKE '%sql%' AS mentions_sql,
    description ILIKE '%airflow%' AS mentions_airflow,
    description ILIKE '%dbt%' AS mentions_dbt,
    description ILIKE '%snowflake%' AS mentions_snowflake,
    description ILIKE '%aws%' AS mentions_aws,
    description ILIKE '%spark%' AS mentions_spark,
    description ILIKE '%kafka%' AS mentions_kafka

FROM {{ ref('stg_job_postings') }}