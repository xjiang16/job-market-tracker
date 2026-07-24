![GitHub Actions](https://img.shields.io/github/actions/workflow/status/xjiang16/job-market-tracker/refresh-results.yml?branch=main&label=daily%20pipeline)

# Data Engineer Job Market Tracker

**An automated data pipeline that tracks what data engineering job postings actually ask for.**

[![Live Results](https://img.shields.io/badge/results-auto--updated_daily-5fd4c4?style=flat-square)](https://xjiang16.github.io/job-market-tracker/)
![Python](https://img.shields.io/badge/Python-3.10-3776AB?style=flat-square&logo=python&logoColor=white)
![Snowflake](https://img.shields.io/badge/Snowflake-warehouse-29B5E8?style=flat-square&logo=snowflake&logoColor=white)
![dbt](https://img.shields.io/badge/dbt-transform-FF694B?style=flat-square&logo=dbt&logoColor=white)
![Airflow](https://img.shields.io/badge/Airflow-orchestration-017CEE?style=flat-square&logo=apacheairflow&logoColor=white)



## What this is

A data pipeline that pulls job postings from the **Adzuna API**, lands them in **Snowflake**, transforms and validates them with **dbt**, and automatically refreshes a public dashboard through **GitHub Actions**.

The pipeline is also orchestrated locally with **Apache Airflow** to demonstrate production-style workflow scheduling and dependency management.

Built to answer one question:

> **What do data engineering job postings actually ask for, and how often do they mention specific tools?**

** [View the results page — auto-updated daily](https://xjiang16.github.io/job-market-tracker/)**



## Table of Contents

- [Architecture](#architecture)
- [What the data shows](#what-the-data-shows)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [Setup](#setup)
- [Running the pipeline](#running-the-pipeline)
- [Data quality](#data-quality)
- [Roadmap](#roadmap)
- [What I learned building this](#what-i-learned-building-this)



## Architecture

```mermaid
flowchart LR
    A["Adzuna API"] --> B["Python\nIngestion"]
    B --> C[("Snowflake\nRAW.JOB_POSTINGS")]
    C --> D["dbt\nstg_job_postings\n(deduplication)"]
    D --> E["dbt\njob_skills\n(skill extraction)"]
    E --> F[("Snowflake\nANALYTICS")]
    F --> G["export_results.py"]
    G --> H["docs/data.json"]
    H --> I["GitHub Pages\nDashboard"]

    J["GitHub Actions\nDaily automation"] -.runs.-> B
    J -.runs.-> C
    J -.runs.-> D
    J -.runs.-> G

    K["Apache Airflow\nLocal orchestration"] -.demo.-> B
    K -.demo.-> C
    K -.demo.-> D
```

**Jump to source:**

[`ingest.py`](ingest.py) ·
[`load_to_snowflake.py`](load_to_snowflake.py) ·
[`stg_job_postings.sql`](job_market_tracker_dbt/models/stg_job_postings.sql) ·
[`job_skills.sql`](job_market_tracker_dbt/models/job_skills.sql) ·
[`export_results.py`](export_results.py)

Every automated refresh:

- Fetches current job postings from the Adzuna API
- Loads raw records into Snowflake (append-only)
- Transforms and deduplicates data with dbt
- Runs dbt data-quality tests
- Exports aggregated analytics to `docs/data.json`
- Regenerates the README statistics section
- Publishes the updated dashboard through GitHub Pages

GitHub Actions runs the production pipeline automatically every day, keeping both the dashboard and README synchronized with the latest data.

Apache Airflow is included as a local orchestration implementation demonstrating the same end-to-end workflow using an industry-standard scheduler.


<!-- AUTO-GENERATED:RESULTS:START -->
## What the data shows

Current snapshot (updated July 24, 2026): **111 postings** after deduplication.

| Tool | Mentioned in | Share |
|------|-------------:|------:|
| SQL | 16 postings | 14.4% |
| Python | 6 postings | 5.4% |
| Snowflake | 3 postings | 2.7% |
| Airflow | 3 postings | 2.7% |
| dbt | 1 posting | 0.9% |

The most notable finding is that **82.0% of postings (91 out of 111) mention none of the 5 tracked tools explicitly**.

Instead, most postings describe responsibilities in general terms such as *"build data pipelines"* or *"own the data platform"* rather than naming a specific technology stack. Of the five tracked tools, **SQL** appears most often in this sample (14.4%).

This is a growing sample, refreshed automatically once a day via [GitHub Actions](https://github.com/xjiang16/job-market-tracker/actions/workflows/refresh-results.yml). See the [live results page](https://xjiang16.github.io/job-market-tracker/) for the current interactive chart, or the roadmap below for what's next.
<!-- AUTO-GENERATED:RESULTS:END -->



## Tech Stack

| Layer | Tool | Why |
|-------|------|-----|
| Source | Adzuna API | Free API aggregating postings from thousands of employers |
| Ingestion | Python (`requests`) | Lightweight and easy to test |
| Warehouse | Snowflake | Modern cloud data warehouse with independent compute/storage |
| Transformation | dbt | Version-controlled SQL models with dependency management and testing |
| Orchestration | Apache Airflow | Industry-standard workflow scheduler |
| Secrets | `python-dotenv` | Keeps credentials out of source control |



## Project Structure

```text
job-market-tracker/
├── ingest.py
├── load_to_snowflake.py
├── export_results.py
├── requirements.txt
├── .env.example
├── .github/
│   └── workflows/
│       └── refresh-results.yml
├── data/
│   └── raw/
├── job_market_tracker_dbt/
│   ├── models/
│   │   ├── sources.yml
│   │   ├── schema.yml
│   │   ├── stg_job_postings.sql
│   │   └── job_skills.sql
├── docs/
│   ├── index.html
│   └── data.json
└── README.md
```

> **Note:** Airflow's DAG file lives outside this repository in `~/airflow/dags/`, since Airflow manages its own DAG directory independently.



## Setup

### 1. Clone the repository

```bash
git clone https://github.com/xjiang16/job-market-tracker.git
cd job-market-tracker

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
pip install dbt-snowflake
```



### 2. Configure credentials

Copy:

```text
.env.example
```

to:

```text
.env
```

Fill in:

- Adzuna API credentials
- Snowflake account
- User
- Password
- Warehouse
- Database
- Schema



### 3. Create Snowflake objects

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



### 4. Configure dbt

Initialize dbt:

```bash
dbt init
```

Configure `~/.dbt/profiles.yml` to point to your Snowflake account using the `ANALYTICS` schema.



### 5. Configure Airflow *(optional)*

Airflow should be installed in its own virtual environment.

Place the DAG file in:

```text
~/airflow/dags/
```

The DAG references this project's virtual environment directly to execute:

- `ingest.py`
- `load_to_snowflake.py`
- `dbt run`
- `dbt test`

Airflow provides a production-style orchestration workflow with task dependencies, scheduling, and monitoring.

### 6. Configure GitHub Actions *(automated refresh)*

This repository includes a GitHub Actions workflow that automatically refreshes the public results dashboard daily without requiring a local machine.

The workflow:

1. Runs the Python ingestion script
2. Loads new job postings into Snowflake
3. Executes dbt transformations and data quality tests
4. Exports analytics results into `docs/data.json`
5. Updates the GitHub Pages dashboard

Required credentials are securely stored using GitHub Actions Secrets.

Workflow file:

```text
.github/workflows/refresh-results.yml
```

To configure GitHub Actions:

1. Add repository secrets in:

```text
GitHub Repository → Settings → Secrets and variables → Actions
```

Required secrets:

```text
ADZUNA_APP_ID
ADZUNA_APP_KEY
SNOWFLAKE_ACCOUNT
SNOWFLAKE_USER
SNOWFLAKE_PASSWORD
```

2. Enable workflow permissions:

```text
GitHub Repository → Settings → Actions → General → Workflow permissions

Select:
Read and write permissions
```

3. Trigger the workflow manually from:

```text
GitHub Repository → Actions → Refresh Job Market Tracker Data → Run workflow
```

The scheduled workflow runs automatically using GitHub-hosted runners and keeps the public results page updated without requiring a local machine.


## Running the Pipeline

### Manual execution

Run each step locally:

```bash
python ingest.py

python load_to_snowflake.py

cd job_market_tracker_dbt

dbt run

dbt test
```



### Automated execution

The production refresh runs through GitHub Actions on a daily schedule:

```text
GitHub Actions
      ↓
Python ingestion
      ↓
Snowflake raw layer
      ↓
dbt transformations
      ↓
dbt data quality tests
      ↓
Export analytics results
      ↓
GitHub Pages dashboard
```

### Local orchestration with Airflow

To run the workflow locally:

```bash
airflow standalone
```

Enable the `job_market_tracker` DAG in the Airflow UI:

```text
http://localhost:8080
```

The Airflow DAG executes the pipeline using dependency-based task ordering:

```text
ingest → load → dbt run → dbt test
```

Airflow is included as a local orchestration demonstration of production-style workflow scheduling, while GitHub Actions provides automated cloud execution for the public dashboard refresh.


## Data Quality

dbt validates the transformed data on every run:

- `not_null`
- `unique`
- One row per `job_id` after deduplication

The raw ingestion layer is intentionally append-only.

Duplicate records are preserved in the raw table so transformations can be rerun later if business logic changes.



## Roadmap

- [x] Adzuna ingestion
- [x] Secure credentials with `.env`
- [x] Snowflake raw layer
- [x] dbt staging model
- [x] Skills extraction model
- [x] dbt tests
- [x] Airflow orchestration
- [x] Public results page

## Potential Improvements
- [ ] Larger keyword/location coverage
- [ ] NLP-based skill extraction
- [ ] Additional job sources (company ATS boards)



## What I Learned Building This

This project served as a hands-on introduction to several technologies I hadn't previously used in production:

- Snowflake's warehouse/database/schema architecture
- dbt's dependency graph (`ref()` and `source()`)
- Airflow DAG scheduling and orchestration

Along the way I debugged several real-world issues, including:

- Python virtual environment mismatches
- Airflow installation and metadata migration conflicts
- Git merge conflicts after repository initialization

None of these problems were solved in one step. Like most data engineering work, each issue was resolved by reading logs, isolating failures, and debugging incrementally.



## Author

**Xiaoqi Jiang**

- GitHub: https://github.com/xjiang16
- LinkedIn: https://www.linkedin.com/in/xjiang16
