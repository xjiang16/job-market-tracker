# Local demo (no API keys needed)

Runs the real dbt models — `stg_job_postings`, `job_skills`, `skill_trends` — against
[DuckDB](https://duckdb.org/) using small fixture data instead of live Adzuna postings.
Nothing in `job_market_tracker_dbt/models/` is modified or duplicated for this: the same
SQL files that run in production run here.

Production also runs on DuckDB now (it moved off Snowflake when the trial ended — see
`warehouse.py`), but it needs `ADZUNA_APP_ID`/`ADZUNA_APP_KEY` and real data. This gives
reviewers, contributors, and CI a way to verify the models without either.

## Run it

From the repo root:

```bash
pip install -r requirements-dev.txt   # includes dbt-duckdb

python demo/seed.py

cd job_market_tracker_dbt
dbt run  --profiles-dir ../demo
dbt test --profiles-dir ../demo
```

Then inspect the results directly:

```bash
python3 -c "
import duckdb
con = duckdb.connect('demo/JOB_MARKET_TRACKER.duckdb')
print(con.execute('SELECT * FROM ANALYTICS.skill_trends ORDER BY skill').fetchall())
"
```

`demo/JOB_MARKET_TRACKER.duckdb` is generated on demand and git-ignored — delete it and
rerun `python demo/seed.py` any time to reset.

## What this does and doesn't prove

Confirms the actual model logic is correct — deduplication, `ILIKE` skill matching, and
the `skill_trends` `UNPIVOT`/incremental-upsert behavior all run against real (if small)
data and produce hand-checkable output. `tests/test_demo.py` asserts on the exact values.

It runs on the same database engine as production, so dialect differences are no longer a
concern. What it doesn't cover is real data — Adzuna's actual descriptions and volumes —
which only the daily production workflow exercises. This replaced the CI's old `dbt parse`
check, which only validated Jinja/YAML compiled — never real execution.
