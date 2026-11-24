"""
Loads today's raw Adzuna JSON files (written by ingest.py to data/raw/) into
RAW.job_postings in a fresh local DuckDB file, on top of all previously saved
postings restored from data/warehouse/ (see warehouse.py).

Raw postings are an append-only log — nothing is cleaned or deduplicated here;
stg_job_postings handles dedup in dbt.
"""

import glob
import json
import os
from datetime import datetime

import duckdb

import warehouse

INSERT_SQL = """
    INSERT INTO RAW.job_postings (
        job_id, title, company, location, salary_min, salary_max,
        created_date, description, search_keyword, search_location, loaded_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def build_rows(file_data):
    search_keyword = file_data["search_keyword"]
    search_location = file_data["search_location"]
    jobs = file_data["response"]["results"]

    return [
        (
            job.get("id"),
            job.get("title"),
            job.get("company", {}).get("display_name"),
            job.get("location", {}).get("display_name"),
            job.get("salary_min"),
            job.get("salary_max"),
            job.get("created"),
            job.get("description"),
            search_keyword,
            search_location,
        )
        for job in jobs
    ]


def load_files(json_files, con, loaded_at):
    total_rows = 0
    for filepath in json_files:
        with open(filepath, "r") as f:
            file_data = json.load(f)

        for row in build_rows(file_data):
            con.execute(INSERT_SQL, (*row, loaded_at))
            total_rows += 1

    return total_rows


def run(db_path=warehouse.DB_PATH, store_dir=warehouse.STORE_DIR):
    # Always start from an empty database file: the CSVs in store_dir are the
    # source of truth, and a leftover local file would double-load them.
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    if os.path.exists(db_path):
        os.remove(db_path)

    con = duckdb.connect(db_path)
    try:
        warehouse.restore(con, store_dir)

        json_files = sorted(glob.glob("data/raw/*.json"))
        print(f"Found {len(json_files)} files to load")

        total_rows = load_files(json_files, con, datetime.now())
        print(f"Loaded {total_rows} job postings into DuckDB ({db_path})")
    finally:
        con.close()


if __name__ == "__main__":  # pragma: no cover
    run()
