import json
from datetime import date
from decimal import Decimal

import duckdb

import export_results
import warehouse


def _row(**counts):
    """Build a query-result row: one count per SKILL_COLUMNS entry (default 0), then total, then none_mentioned."""
    skill_counts = [counts.get(key, 0) for key, _ in export_results.SKILL_COLUMNS]
    total = counts.pop("total", sum(skill_counts))
    none_mentioned = counts.pop("none_mentioned", 0)
    return (*skill_counts, total, none_mentioned)


def test_compute_data_percentages_and_sort_order():
    row = _row(python=2, sql=6, snowflake=1, dbt=1, total=10, none_mentioned=0)

    data = export_results.compute_data(row, "2026-08-04")

    assert data["last_updated"] == "2026-08-04"
    assert data["total_postings"] == 10
    assert len(data["skills"]) == len(export_results.SKILL_COLUMNS)
    assert [s["label"] for s in data["skills"][:4]] == ["SQL", "Python", "Snowflake", "dbt"]
    assert data["skills"][0] == {"label": "SQL", "count": 6, "pct": 60.0}
    assert data["none_mentioned_pct"] == 0.0


def test_compute_data_handles_zero_total_without_dividing_by_zero():
    row = _row()

    data = export_results.compute_data(row, "2026-08-04")

    assert data["total_postings"] == 0
    assert all(s["pct"] == 0 for s in data["skills"])
    assert data["none_mentioned_pct"] == 0


def test_build_history_groups_by_date_and_normalizes_skill_case():
    rows = [
        (date(2026, 8, 1), "PYTHON", 5.0),
        (date(2026, 8, 1), "SQL", 15.0),
        (date(2026, 8, 2), "python", 6.0),
        (date(2026, 8, 2), "sql", 16.0),
    ]

    result = export_results.build_history(rows)

    assert result["series"] == ["Python", "SQL", "Airflow", "Snowflake", "dbt"]
    assert result["history"] == [
        {"date": "2026-08-01", "Python": 5.0, "SQL": 15.0},
        {"date": "2026-08-02", "Python": 6.0, "SQL": 16.0},
    ]


def test_build_history_ignores_unknown_skill_labels():
    rows = [
        (date(2026, 8, 1), "RUST", 1.0),
        (date(2026, 8, 2), "RUST", 1.0),
        (date(2026, 8, 2), "SQL", 16.0),
    ]

    result = export_results.build_history(rows)

    # 08-01 had only an unrecognized skill, so it contributes no row at all;
    # 08-02 still surfaces with just the known skill.
    assert result["history"] == [{"date": "2026-08-02", "SQL": 16.0}]


def test_build_history_handles_string_dates():
    rows = [("2026-08-01", "DBT", 1.3)]

    result = export_results.build_history(rows)

    assert result["history"] == [{"date": "2026-08-01", "dbt": 1.3}]


def test_build_history_empty_input():
    assert export_results.build_history([]) == {
        "series": ["Python", "SQL", "Airflow", "Snowflake", "dbt"],
        "history": [],
    }


def test_build_history_output_is_json_serializable_with_decimal_pct():
    # Snowflake returned NUMBER(x,1) columns (like skill_trends.pct) as
    # decimal.Decimal, not float — using a real Decimal here, instead of a
    # plain float literal, is what catches json.dump() blowing up on it.
    rows = [(date(2026, 8, 1), "SQL", Decimal("14.9"))]

    result = export_results.build_history(rows)

    assert result["history"] == [{"date": "2026-08-01", "SQL": 14.9}]
    json.dumps(result)  # should not raise TypeError: Object of type Decimal is not JSON serializable


def test_run_writes_docs_json_and_saves_warehouse(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    db_path = str(tmp_path / "JOB_MARKET_TRACKER.duckdb")
    store_dir = tmp_path / "store"

    # The shape dbt leaves behind: job_skills + skill_trends in ANALYTICS.
    con = duckdb.connect(db_path)
    warehouse.restore(con, str(store_dir))
    mention_cols = ", ".join(f"FALSE AS mentions_{key}" for key, _ in export_results.SKILL_COLUMNS)
    con.execute(f"CREATE TABLE ANALYTICS.job_skills AS SELECT {mention_cols} FROM range(4)")
    con.execute("UPDATE ANALYTICS.job_skills SET mentions_sql = TRUE WHERE rowid < 3")
    con.execute(warehouse.TRENDS_DDL)
    con.execute("INSERT INTO ANALYTICS.skill_trends VALUES ('2026-08-01', 'sql', 4, 3, 75.0)")
    con.close()

    export_results.run(db_path, str(store_dir))

    written = json.loads((tmp_path / "docs" / "data.json").read_text())
    assert written["total_postings"] == 4
    assert written["skills"][0] == {"label": "SQL", "count": 3, "pct": 75.0}
    assert written["none_mentioned"] == 1

    history = json.loads((tmp_path / "docs" / "data_history.json").read_text())
    assert history["history"] == [{"date": "2026-08-01", "SQL": 75.0}]

    assert (store_dir / warehouse.TRENDS_FILE).exists()
    assert (store_dir / warehouse.RAW_FILE).exists()
