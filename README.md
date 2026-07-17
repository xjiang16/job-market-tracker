# Job Market Tracker

A data pipeline that tracks data engineering job postings to surface trends in
in-demand skills, salary ranges, and hiring locations.

## What it does

Pulls job posting data from the Adzuna API across multiple job titles and
locations, and lands the raw results as JSON files for downstream analysis.
The eventual goal is a full pipeline: raw data → Snowflake → dbt models →
Airflow orchestration, answering questions like "what skills show up most in
DE postings right now" and "how do salaries compare by location."

## Architecture

Adzuna API → Python ingestion script → Snowflake (raw + clean tables) →
dbt (transform + test) → Airflow (daily orchestration)

## Status

🚧 In active development.

Currently working:
- Ingestion script pulls postings across multiple keywords and locations
- Raw API responses saved locally as dated JSON files
- API credentials secured via environment variables (not committed to git)

## Setup

1. Clone this repo
2. Create a virtual environment:
```bash
   python3 -m venv .venv
   source .venv/bin/activate
```
3. Install dependencies:
```bash
   pip install requests python-dotenv
```
4. Create a `.env` file in the project root with your Adzuna credentials
   (get them free at https://developer.adzuna.com):
```
    ADZUNA_APP_ID=your_app_id_here
    ADZUNA_APP_KEY=your_app_key_here
```
5. Run the ingestion script:
```bash
   python ingest.py
```
6. Check `data/raw/` for the saved JSON output — one file per
   keyword/location combination

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
- [ ] Load raw data into Snowflake
- [ ] dbt models: clean jobs table + skills extraction
- [ ] dbt tests for data quality
- [ ] Airflow DAG to orchestrate daily runs