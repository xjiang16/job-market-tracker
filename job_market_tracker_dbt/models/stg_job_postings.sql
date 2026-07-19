SELECT
    job_id,
    title,
    company,
    location,
    salary_min,
    salary_max,
    created_date,
    description,
    search_keyword,
    search_location,
    loaded_at
FROM {{ source('raw', 'job_postings') }}
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY job_id
    ORDER BY loaded_at DESC
) = 1