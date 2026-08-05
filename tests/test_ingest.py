import json
from unittest.mock import MagicMock, patch

import pytest

import ingest


def make_response(status_code, json_data=None, raise_on_json=False):
    resp = MagicMock()
    resp.status_code = status_code
    resp.ok = 200 <= status_code < 300
    if raise_on_json:
        resp.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)
    else:
        resp.json.return_value = json_data or {"results": []}
    return resp


@patch("ingest.time.sleep")
@patch("ingest.requests.get")
def test_fetch_with_retry_succeeds_first_try(mock_get, mock_sleep):
    mock_get.return_value = make_response(200)

    response = ingest.fetch_with_retry({})

    assert response.ok
    assert mock_get.call_count == 1
    mock_sleep.assert_not_called()


@patch("ingest.time.sleep")
@patch("ingest.requests.get")
def test_fetch_with_retry_recovers_after_transient_failures(mock_get, mock_sleep):
    # Reproduces the 2026-08-04 incident: a 502 with a non-JSON body, then success.
    mock_get.side_effect = [make_response(502, raise_on_json=True), make_response(200)]

    response = ingest.fetch_with_retry({})

    assert response.ok
    assert mock_get.call_count == 2
    mock_sleep.assert_called_once_with(ingest.RETRY_DELAY_SECONDS)


@patch("ingest.time.sleep")
@patch("ingest.requests.get")
def test_fetch_with_retry_gives_up_after_max_attempts(mock_get, mock_sleep):
    mock_get.return_value = make_response(502, raise_on_json=True)

    response = ingest.fetch_with_retry({}, max_retries=3, retry_delay=0)

    assert not response.ok
    assert mock_get.call_count == 3
    assert mock_sleep.call_count == 2  # no sleep after the final attempt


@patch("ingest.time.sleep")
@patch("ingest.requests.get")
def test_run_writes_a_file_per_search_on_success(mock_get, mock_sleep, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ADZUNA_APP_ID", "id")
    monkeypatch.setenv("ADZUNA_APP_KEY", "key")
    mock_get.return_value = make_response(200, {"results": [{"id": "1"}]})

    ingest.run()

    files = sorted((tmp_path / "data" / "raw").glob("*.json"))
    assert len(files) == len(ingest.KEYWORDS) * len(ingest.LOCATIONS)

    saved = json.loads(files[0].read_text())
    assert saved["response"] == {"results": [{"id": "1"}]}
    assert saved["search_keyword"] in ingest.KEYWORDS
    assert saved["search_location"] in ingest.LOCATIONS


@patch("ingest.time.sleep")
@patch("ingest.requests.get")
def test_run_skips_failed_search_but_completes_the_rest(mock_get, mock_sleep, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ADZUNA_APP_ID", "id")
    monkeypatch.setenv("ADZUNA_APP_KEY", "key")

    # Every search succeeds except "Remote", which always 502s (like the real incident).
    def fake_get(url, params):
        if params["where"] == "Remote":
            return make_response(502, raise_on_json=True)
        return make_response(200, {"results": []})

    mock_get.side_effect = fake_get

    with pytest.raises(SystemExit) as exc_info:
        ingest.run()

    assert exc_info.value.code == 1

    files = list((tmp_path / "data" / "raw").glob("*.json"))
    # Only the non-Remote searches (one per keyword) should have been saved.
    assert len(files) == len(ingest.KEYWORDS)
    for f in files:
        assert "Remote" not in f.name
