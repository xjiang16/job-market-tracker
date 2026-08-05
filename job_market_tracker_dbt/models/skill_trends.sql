{{ config(materialized='incremental', unique_key=['snapshot_date', 'skill']) }}

-- One row per (day, skill), appended once per pipeline run. Lets the results
-- page show tool-mention rates trending over time instead of only "right now".
-- unique_key upserts same-day reruns (e.g. workflow_dispatch) instead of duplicating.

WITH base AS (
    SELECT
        mentions_python::int AS python,
        mentions_sql::int AS sql,
        mentions_airflow::int AS airflow,
        mentions_snowflake::int AS snowflake,
        mentions_dbt::int AS dbt
    FROM {{ ref('job_skills') }}
),

unpivoted AS (
    SELECT skill, mentioned
    FROM base
    UNPIVOT(mentioned FOR skill IN (python, sql, airflow, snowflake, dbt))
),

aggregated AS (
    SELECT
        CURRENT_DATE AS snapshot_date,
        skill,
        COUNT(*) AS total_postings,
        SUM(mentioned) AS mention_count
    FROM unpivoted
    GROUP BY skill
)

SELECT
    snapshot_date,
    skill,
    total_postings,
    mention_count,
    ROUND(mention_count / NULLIF(total_postings, 0) * 100, 1) AS pct
FROM aggregated
