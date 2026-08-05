import json
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


@patch("export_results.snowflake.connector.connect")
def test_run_writes_docs_data_json(mock_connect, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for var in ["SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD",
                "SNOWFLAKE_WAREHOUSE", "SNOWFLAKE_DATABASE", "SNOWFLAKE_SCHEMA"]:
        monkeypatch.setenv(var, "test")

    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = (2, 6, 0, 1, 1, 10, 0)
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_connect.return_value = mock_conn

    export_results.run()

    written = json.loads((tmp_path / "docs" / "data.json").read_text())
    assert written["total_postings"] == 10
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()
