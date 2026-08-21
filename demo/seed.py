"""
Seeds a local DuckDB file with fixture data shaped like RAW.JOB_POSTINGS,
so the dbt models can be run and tested without a Snowflake account.

The file is named JOB_MARKET_TRACKER.duckdb on purpose: dbt-duckdb names its
catalog after the database file's basename, so this matches the `database:`
already hardcoded in job_market_tracker_dbt/models/sources.yml — the real
model files run completely unmodified against it.

Used by the local workflow in demo/README.md and by the integration test in
tests/test_demo.py.
"""

from datetime import date, timedelta

import duckdb

TODAY = date.today().isoformat()
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()

# (job_id, title, company, location, salary_min, salary_max, created_date,
#  description, search_keyword, search_location, loaded_at)
#
# job_id "1" appears twice (like a repost Adzuna returns again the next day)
# so the fixture exercises stg_job_postings' dedup-by-loaded_at logic.
FIXTURE_ROWS = [
    ("1", "Data Engineer", "Acme", "Austin, TX", 100000, 140000,
     YESTERDAY, "Python, SQL, and Airflow orchestration.",
     "data engineer", "Austin TX", f"{YESTERDAY}T09:00:00"),
    ("1", "Senior Data Engineer", "Acme", "Austin, TX", 110000, 150000,
     TODAY, "Python, SQL, Airflow, and Snowflake.",
     "data engineer", "Austin TX", f"{TODAY}T09:00:00"),
    ("2", "Analytics Engineer", "Beta", "Remote", 90000, 120000,
     TODAY, "dbt and Snowflake experience preferred.",
     "analytics engineer", "Remote", f"{TODAY}T09:05:00"),
    ("3", "Data Analytic Engineer", "Gamma", "Remote", None, None,
     TODAY, "General data responsibilities, no specific tools named.",
     "data analytic engineer", "Remote", f"{TODAY}T09:10:00"),
    ("4", "Data Engineer", "Delta", "Austin, TX", 95000, 130000,
     TODAY, "SQL heavy role, some Python.",
     "data engineer", "Austin TX", f"{TODAY}T09:15:00"),
    ("5", "Analytics Engineer", "Epsilon", "Remote", 105000, 135000,
     TODAY, "Python and SQL all day.",
     "analytics engineer", "Remote", f"{TODAY}T09:20:00"),
]


def seed(db_path, rows=FIXTURE_ROWS):
    con = duckdb.connect(db_path)
    con.execute("CREATE SCHEMA IF NOT EXISTS RAW")
    con.execute("""
        CREATE OR REPLACE TABLE RAW.job_postings (
            job_id STRING, title STRING, company STRING, location STRING,
            salary_min DOUBLE, salary_max DOUBLE, created_date TIMESTAMP,
            description STRING, search_keyword STRING, search_location STRING,
            loaded_at TIMESTAMP
        )
    """)
    con.executemany(
        "INSERT INTO RAW.job_postings VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    con.close()


if __name__ == "__main__":  # pragma: no cover
    seed("demo/JOB_MARKET_TRACKER.duckdb")
    print(f"Seeded {len(FIXTURE_ROWS)} fixture rows into demo/JOB_MARKET_TRACKER.duckdb")
