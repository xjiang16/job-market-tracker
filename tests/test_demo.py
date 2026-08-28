"""
Integration test: runs the real dbt models against DuckDB fixture data, the
same way demo/README.md documents for local/manual use. This is the only
test in the suite that exercises actual dbt execution rather than mocked
Python logic — it's what verifies stg_job_postings' dedup, job_skills'
ILIKE matching, and skill_trends' UNPIVOT actually produce correct output.
"""

import subprocess
from pathlib import Path

import duckdb
import pytest

from demo.seed import FIXTURE_ROWS, TODAY, seed

DBT_PROJECT_DIR = Path(__file__).parent.parent / "job_market_tracker_dbt"


def write_profiles(profiles_dir, db_path):
    (profiles_dir / "profiles.yml").write_text(f"""\
job_market_tracker_dbt:
  target: duckdb
  outputs:
    duckdb:
      type: duckdb
      path: '{db_path}'
      schema: ANALYTICS
""")


def run_dbt(*args, profiles_dir, check=True):
    return subprocess.run(
        ["dbt", *args, "--profiles-dir", str(profiles_dir)],
        cwd=DBT_PROJECT_DIR, capture_output=True, text=True, check=check,
    )


@pytest.fixture
def duckdb_path(tmp_path):
    db_path = tmp_path / "JOB_MARKET_TRACKER.duckdb"
    seed(str(db_path))
    write_profiles(tmp_path, db_path)
    run_dbt("run", profiles_dir=tmp_path)
    return db_path, tmp_path


def test_dbt_models_produce_correct_values(duckdb_path):
    db_path, _ = duckdb_path
    con = duckdb.connect(str(db_path))

    # stg_job_postings: job_id "1" appears twice in the fixture; the newer
    # (today-dated) version should win the QUALIFY dedup.
    title = con.execute(
        "SELECT title FROM ANALYTICS.stg_job_postings WHERE job_id = '1'"
    ).fetchone()[0]
    assert title == "Senior Data Engineer"

    # job_skills: job_id "3" mentions no tracked tool by name.
    mentions = con.execute("""
        SELECT mentions_python, mentions_sql, mentions_airflow,
               mentions_snowflake, mentions_dbt
        FROM ANALYTICS.job_skills WHERE job_id = '3'
    """).fetchone()
    assert mentions == (False, False, False, False, False)

    # skill_trends: 5 unique postings after dedup (job_ids 1-5); python is
    # mentioned by 1, 4, 5 = 3/5 = 60.0%.
    total, mention_count, pct = con.execute("""
        SELECT total_postings, mention_count, pct
        FROM ANALYTICS.skill_trends WHERE skill = 'python'
    """).fetchone()
    assert (total, mention_count, pct) == (5, 3, 60.0)

    con.close()


def test_dbt_run_is_idempotent_on_rerun(duckdb_path):
    db_path, profiles_dir = duckdb_path

    run_dbt("run", profiles_dir=profiles_dir)  # simulate a same-day workflow_dispatch rerun

    con = duckdb.connect(str(db_path))
    row_count = con.execute("SELECT COUNT(*) FROM ANALYTICS.skill_trends").fetchone()[0]
    con.close()

    assert row_count == 5  # one row per skill, not 10 — the unique_key upserted


def test_daily_ingest_volume_test_passes_with_fixture_data(duckdb_path):
    _, profiles_dir = duckdb_path
    result = run_dbt("test", profiles_dir=profiles_dir, check=False)
    assert result.returncode == 0, result.stdout


def test_daily_ingest_volume_test_fails_when_todays_volume_is_low(tmp_path):
    db_path = tmp_path / "JOB_MARKET_TRACKER.duckdb"
    # Only 2 rows dated today (loaded_at is index 10), below the default
    # min_daily_postings=5 floor.
    sparse_fixture = [r for r in FIXTURE_ROWS if r[10].startswith(TODAY)][:2]
    seed(str(db_path), sparse_fixture)
    write_profiles(tmp_path, db_path)

    run_dbt("run", profiles_dir=tmp_path)
    result = run_dbt("test", "--select", "assert_daily_ingest_volume",
                      profiles_dir=tmp_path, check=False)

    assert result.returncode == 1, result.stdout
