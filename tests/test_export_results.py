import json
from datetime import date
from unittest.mock import MagicMock, patch

import export_results


def test_compute_data_percentages_and_sort_order():
    # python=2, sql=6, airflow=0, snowflake=1, dbt=1, total=10, none_mentioned=0
    row = (2, 6, 0, 1, 1, 10, 0)

    data = export_results.compute_data(row, "2026-08-04")

    assert data["last_updated"] == "2026-08-04"
    assert data["total_postings"] == 10
    assert [s["label"] for s in data["skills"]] == ["SQL", "Python", "Snowflake", "dbt", "Airflow"]
    assert data["skills"][0] == {"label": "SQL", "count": 6, "pct": 60.0}
    assert data["none_mentioned_pct"] == 0.0


def test_compute_data_handles_zero_total_without_dividing_by_zero():
    row = (0, 0, 0, 0, 0, 0, 0)

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


@patch("export_results.snowflake.connector.connect")
def test_run_writes_docs_data_json_and_history(mock_connect, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for var in ["SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD",
                "SNOWFLAKE_WAREHOUSE", "SNOWFLAKE_DATABASE", "SNOWFLAKE_SCHEMA"]:
        monkeypatch.setenv(var, "test")

    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (2, 6, 0, 1, 1, 10, 0)
    mock_cursor.fetchall.return_value = [(date(2026, 8, 1), "SQL", 60.0)]
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_connect.return_value = mock_conn

    export_results.run()

    written = json.loads((tmp_path / "docs" / "data.json").read_text())
    assert written["total_postings"] == 10

    history = json.loads((tmp_path / "docs" / "data_history.json").read_text())
    assert history["history"] == [{"date": "2026-08-01", "SQL": 60.0}]

    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()
