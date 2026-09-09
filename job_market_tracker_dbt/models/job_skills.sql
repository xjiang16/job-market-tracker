SELECT
    job_id,
    title,
    company,
    location,
    salary_min,
    salary_max,
    created_date,
    search_keyword,
    search_location,

    description ILIKE '%python%' AS mentions_python,
    description ILIKE '%sql%' AS mentions_sql,
    description ILIKE '%airflow%' AS mentions_airflow,
    description ILIKE '%dbt%' AS mentions_dbt,
    description ILIKE '%snowflake%' AS mentions_snowflake,
    description ILIKE '%aws%' AS mentions_aws,
    description ILIKE '%spark%' AS mentions_spark,
    description ILIKE '%kafka%' AS mentions_kafka,
    description ILIKE '%redshift%' AS mentions_redshift,
    description ILIKE '%bigquery%' AS mentions_bigquery,
    description ILIKE '%gcp%' AS mentions_gcp,
    description ILIKE '%docker%' AS mentions_docker,
    description ILIKE '%databricks%' AS mentions_databricks,
    description ILIKE '%terraform%' AS mentions_terraform,
    (description ILIKE '%java%' AND description NOT ILIKE '%javascript%') AS mentions_java,
    (description ILIKE '%scala%' AND description NOT ILIKE '%scalab%') AS mentions_scala

FROM {{ ref('stg_job_postings') }}