-- Fails if today's raw ingest looks empty or near-empty — catches a silent
-- Adzuna response (200 OK, no data) that ingest.py's retry logic wouldn't
-- otherwise flag, since that only fires on non-2xx responses.
SELECT COUNT(*) AS today_row_count
FROM {{ source('raw', 'job_postings') }}
WHERE loaded_at::date = CURRENT_DATE
HAVING COUNT(*) < {{ var('min_daily_postings', 5) }}
