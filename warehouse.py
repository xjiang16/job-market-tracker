"""
Where the pipeline's data lives between daily runs.

The pipeline used to keep its tables in Snowflake. It now uses DuckDB, a free
embedded database that is just a local file. GitHub Actions starts every run on
a fresh machine, though, so that file would vanish between runs.

So the tables that *can't* be rebuilt from anything else are saved to plain,
sorted CSV files in data/warehouse/ and committed to git by the daily workflow:

  - RAW.job_postings       every posting ever loaded (append-only log)
  - ANALYTICS.skill_trends one row per (day, skill), a snapshot taken each run —
                           a past day's snapshot can't be recomputed later

Each run: restore() rebuilds a fresh DuckDB file from those CSVs, the loader
appends today's postings, dbt rebuilds everything else, and save() writes the
CSVs back. CSV (not the .duckdb file itself) because git stores an append-only
text file as small deltas, while a binary database file would add megabytes of
history every day.

The file is named JOB_MARKET_TRACKER.duckdb on purpose: dbt-duckdb names its
catalog after the file's basename, which matches the `database:` hardcoded in
job_market_tracker_dbt/models/sources.yml.
"""

import os

DB_PATH = "warehouse/JOB_MARKET_TRACKER.duckdb"
STORE_DIR = "data/warehouse"

RAW_FILE = "raw_job_postings.csv"
TRENDS_FILE = "skill_trends.csv"

RAW_DDL = """
    CREATE TABLE RAW.job_postings (
        job_id VARCHAR, title VARCHAR, company VARCHAR, location VARCHAR,
        salary_min DOUBLE, salary_max DOUBLE, created_date TIMESTAMP,
        description VARCHAR, search_keyword VARCHAR, search_location VARCHAR,
        loaded_at TIMESTAMP
    )
"""

TRENDS_DDL = """
    CREATE TABLE ANALYTICS.skill_trends (
        snapshot_date DATE, skill VARCHAR, total_postings BIGINT,
        mention_count BIGINT, pct DOUBLE
    )
"""

# Full sort keys, so every save writes rows in the same order and git diffs
# only show the genuinely new rows.
RAW_ORDER = "loaded_at, job_id, search_keyword, search_location"
TRENDS_ORDER = "snapshot_date, skill"


def restore(con, store_dir=STORE_DIR):
    """Recreate the persisted tables in an empty DuckDB connection from the CSVs."""
    con.execute("CREATE SCHEMA IF NOT EXISTS RAW")
    con.execute("CREATE SCHEMA IF NOT EXISTS ANALYTICS")

    # RAW.job_postings always exists, even on the very first run, so the loader
    # has somewhere to insert.
    con.execute(RAW_DDL)
    raw_path = os.path.join(store_dir, RAW_FILE)
    if os.path.exists(raw_path):
        con.execute(f"COPY RAW.job_postings FROM '{raw_path}' (HEADER)")

    # skill_trends is a dbt incremental model. Only pre-create it when there's
    # history to restore — if it doesn't exist, dbt creates it itself.
    trends_path = os.path.join(store_dir, TRENDS_FILE)
    if os.path.exists(trends_path):
        con.execute(TRENDS_DDL)
        con.execute(f"COPY ANALYTICS.skill_trends FROM '{trends_path}' (HEADER)")


def save(con, store_dir=STORE_DIR):
    """Write the persisted tables back out to the CSVs, in a stable order."""
    os.makedirs(store_dir, exist_ok=True)
    con.execute(
        f"COPY (SELECT * FROM RAW.job_postings ORDER BY {RAW_ORDER}) "
        f"TO '{os.path.join(store_dir, RAW_FILE)}' (HEADER)"
    )
    con.execute(
        f"COPY (SELECT * FROM ANALYTICS.skill_trends ORDER BY {TRENDS_ORDER}) "
        f"TO '{os.path.join(store_dir, TRENDS_FILE)}' (HEADER)"
    )
