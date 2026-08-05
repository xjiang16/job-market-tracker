import json
from unittest.mock import MagicMock, patch

import load_to_snowflake


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

    rows = load_to_snowflake.build_rows(file_data)

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

    rows = load_to_snowflake.build_rows(file_data)

    assert rows == [("1", None, None, None, None, None, None, None, "data engineer", "Remote")]


def test_load_files_executes_a_row_per_job(tmp_path):
    file_data = {
        "search_keyword": "data engineer",
        "search_location": "Remote",
        "response": {"results": [{"id": "1"}, {"id": "2"}]},
    }
    filepath = tmp_path / "postings.json"
    filepath.write_text(json.dumps(file_data))

    mock_cursor = MagicMock()

    total = load_to_snowflake.load_files([str(filepath)], mock_cursor)

    assert total == 2
    assert mock_cursor.execute.call_count == 2


@patch("load_to_snowflake.glob.glob")
@patch("load_to_snowflake.snowflake.connector.connect")
def test_run_commits_after_loading(mock_connect, mock_glob, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for var in ["SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD",
                "SNOWFLAKE_WAREHOUSE", "SNOWFLAKE_DATABASE", "SNOWFLAKE_SCHEMA"]:
        monkeypatch.setenv(var, "test")
    mock_glob.return_value = []

    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_connect.return_value = mock_conn

    load_to_snowflake.run()

    mock_conn.commit.assert_called_once()
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()
