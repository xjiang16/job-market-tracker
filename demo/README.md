# Local demo (no Snowflake account needed)

Runs the real dbt models — `stg_job_postings`, `job_skills`, `skill_trends` — against
[DuckDB](https://duckdb.org/) instead of Snowflake, using small fixture data instead of
live Adzuna postings. Nothing in `job_market_tracker_dbt/models/` is modified or
duplicated for this: the same SQL files that run in production run here.

This exists because the real pipeline needs a Snowflake account + `ADZUNA_APP_ID`/`ADZUNA_APP_KEY`
to run at all, which meant nobody without one of those could ever verify the dbt models actually
work — not a reviewer, not a contributor, not even in CI. This gives all three a way to.

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

It does **not** prove the models work on Snowflake specifically. DuckDB and Snowflake
share most SQL, including the less common features these models lean on (`QUALIFY`,
`UNPIVOT`), but they aren't identical dialects — something that passes here could still
fail against real Snowflake, and vice versa. This replaced the CI's old `dbt parse`
check, which only validated Jinja/YAML compiled — never real execution, on any warehouse.
Real execution against DuckDB is a strictly stronger check than that, just not a
substitute for occasionally running the actual production workflow.
