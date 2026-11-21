import json
from datetime import datetime

import duckdb

import load_to_duckdb
import warehouse


def _write_raw_file(directory, name, results):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(json.dumps({
        "search_keyword": "data engineer",
        "search_location": "Remote",
        "response": {"results": results},
    }))
    return path


def test_build_rows_maps_fields_from_adzuna_response():
    file_data = {
        "search_keyword": "data engineer",
        "search_location": "Austin TX",
        "response": {
            "results": [
                {
                    "id": "123",
                    "title": "Data Engineer",
                    "company": {"display_name": "Acme"},
                    "location": {"display_name": "Austin, TX"},
                    "salary_min": 100000,
                    "salary_max": 140000,
                    "created": "2026-08-01T00:00:00Z",
                    "description": "Build pipelines.",
                }
            ]
        },
    }

    rows = load_to_duckdb.build_rows(file_data)

    assert rows == [
        ("123", "Data Engineer", "Acme", "Austin, TX", 100000, 140000,
         "2026-08-01T00:00:00Z", "Build pipelines.", "data engineer", "Austin TX")
    ]


def test_build_rows_handles_missing_optional_fields():
    file_data = {
        "search_keyword": "data engineer",
        "search_location": "Remote",
        "response": {"results": [{"id": "1"}]},
    }

    rows = load_to_duckdb.build_rows(file_data)

    assert rows == [("1", None, None, None, None, None, None, None, "data engineer", "Remote")]


def test_load_files_inserts_a_row_per_job_with_loaded_at(tmp_path):
    path = _write_raw_file(tmp_path, "postings.json", [
        {"id": "1", "created": "2026-08-01T00:00:00Z"},
        {"id": "2"},
    ])
    con = duckdb.connect()
    warehouse.restore(con, str(tmp_path / "empty-store"))
    loaded_at = datetime(2026, 11, 20, 7, 17)

    total = load_to_duckdb.load_files([str(path)], con, loaded_at)

    assert total == 2
    rows = con.execute(
        "SELECT job_id, created_date, loaded_at FROM RAW.job_postings ORDER BY job_id"
    ).fetchall()
    # Adzuna's "...Z" timestamp strings must cast cleanly into the TIMESTAMP column.
    assert rows == [
        ("1", datetime(2026, 8, 1), loaded_at),
        ("2", None, loaded_at),
    ]


def test_run_appends_todays_files_to_restored_history(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    db_path = str(tmp_path / "warehouse" / "JOB_MARKET_TRACKER.duckdb")
    store_dir = str(tmp_path / "store")

    # A previous run saved one posting.
    con = duckdb.connect()
    warehouse.restore(con, store_dir)
    con.execute("""
        INSERT INTO RAW.job_postings (job_id, loaded_at)
        VALUES ('old', '2026-11-19 07:17:00')
    """)
    con.execute("CREATE TABLE ANALYTICS.skill_trends AS SELECT DATE '2026-11-19' AS snapshot_date, "
                "'python' AS skill, 10 AS total_postings, 5 AS mention_count, 50.0 AS pct")
    warehouse.save(con, store_dir)
    con.close()

    # Today's ingest wrote one new file.
    _write_raw_file(tmp_path / "data" / "raw", "today.json", [{"id": "new"}])

    load_to_duckdb.run(db_path, store_dir)
    load_to_duckdb.run(db_path, store_dir)  # rerun replaces the file instead of double-loading

    con = duckdb.connect(db_path)
    job_ids = [r[0] for r in con.execute(
        "SELECT job_id FROM RAW.job_postings ORDER BY job_id"
    ).fetchall()]
    assert job_ids == ["new", "old"]
    con.close()
