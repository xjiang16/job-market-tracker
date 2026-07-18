# Job Market Tracker

A data pipeline that tracks data engineering job postings to surface trends in
in-demand skills, salary ranges, and hiring locations.

## What it does

Pulls job posting data from the Adzuna API across multiple job titles and
locations, lands the raw results as JSON files, then loads them into
Snowflake for downstream analysis. The eventual goal is a full pipeline:
raw data → Snowflake → dbt models → Airflow orchestration, answering
questions like "what skills show up most in DE postings right now" and
"how do salaries compare by location."

## Architecture

Adzuna API → Python ingestion script → Snowflake (raw + clean tables) →
dbt (transform + test) → Airflow (daily orchestration)

## Status

🚧 In active development.

Currently working:
- Ingestion script pulls postings across multiple keywords and locations
- Raw API responses saved locally as dated JSON files
- API credentials secured via environment variables (not committed to git)
- Snowflake connection tested and working
- Loader script inserts raw postings from local JSON into Snowflake

## Setup

1. Clone this repo
2. Create a virtual environment:
```bash
   python3 -m venv .venv
   source .venv/bin/activate
```
3. Install dependencies:
```bash
   pip install requests python-dotenv snowflake-connector-python
```
4. Create a `.env` file in the project root (see `.env.example` for the
   required keys). You'll need:
   - Adzuna credentials (free at https://developer.adzuna.com)
   - A Snowflake account, with a database/schema/warehouse set up (see
     Snowflake Setup below)
5. Run the ingestion script:
```bash
   python ingest.py
```
   Check `data/raw/` for the saved JSON output — one file per
   keyword/location combination.
6. Test the Snowflake connection:
```bash
   python test_snowflake_connection.py
```
7. Load the raw data into Snowflake:
```bash
   python load_to_snowflake.py
```

## Snowflake Setup

This project expects a database, schema, and table already created in
Snowflake. From a Snowsight worksheet:

```sql
CREATE DATABASE JOB_MARKET_TRACKER;
CREATE SCHEMA JOB_MARKET_TRACKER.RAW;

CREATE TABLE JOB_MARKET_TRACKER.RAW.JOB_POSTINGS (
    job_id STRING,
    title STRING,
    company STRING,
    location STRING,
    salary_min FLOAT,
    salary_max FLOAT,
    created_date TIMESTAMP,
    description STRING,
    search_keyword STRING,
    search_location STRING,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);
```

Note: the raw layer is intentionally append-only — re-running the loader
will insert duplicate rows for postings already loaded. Deduplication is
handled downstream in the dbt transformation layer, not at load time.

## Configuration

Keywords and locations searched are defined near the top of `ingest.py`:

```python
keywords = ["data engineer", "analytics engineer", "data analytic engineer"]
locations = ["Austin TX", "Remote"]
```

Add or remove entries to change what gets searched.

## Roadmap

- [x] Adzuna ingestion script
- [x] Loop across multiple keywords and locations
- [x] Secure credential handling via `.env`
- [x] Load raw data into Snowflake
- [ ] dbt models: clean jobs table + skills extraction
- [ ] dbt tests for data quality
- [ ] Airflow DAG to orchestrate daily runs