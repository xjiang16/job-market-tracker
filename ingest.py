import json
import os
import sys
import time
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv

URL = "https://api.adzuna.com/v1/api/jobs/us/search/1"
KEYWORDS = ["data engineer", "analytics engineer", "data analytic engineer"]
LOCATIONS = ["Austin TX", "Remote"]

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5


def fetch_with_retry(params, max_retries=MAX_RETRIES, retry_delay=RETRY_DELAY_SECONDS):
    """GETs URL with params, retrying on non-2xx responses. Returns the last response received."""
    response = None
    for attempt in range(1, max_retries + 1):
        response = requests.get(URL, params=params)
        print(response.status_code)
        if response.ok:
            break
        print(f"Attempt {attempt}/{max_retries} failed with status {response.status_code}")
        if attempt < max_retries:
            time.sleep(retry_delay)
    return response


def run():
    Path("data/raw").mkdir(parents=True, exist_ok=True)

    app_id = os.environ["ADZUNA_APP_ID"]
    app_key = os.environ["ADZUNA_APP_KEY"]

    failures = []

    for keyword in KEYWORDS:
        for location in LOCATIONS:
            print(f"Fetching {keyword} in {location}...")
            params = {
                "app_id": app_id,
                "app_key": app_key,
                "what": keyword,
                "where": location,
            }

            response = fetch_with_retry(params)

            if response is None or not response.ok:
                print(f"Giving up on {keyword} in {location} after {MAX_RETRIES} attempts")
                failures.append((keyword, location, response.status_code if response is not None else None))
                continue

            safe_keyword = keyword.replace(" ", "_")
            safe_location = location.replace(" ", "_")
            filename = f"data/raw/{date.today().isoformat()}_{safe_keyword}_{safe_location}.json"

            data_to_save = {
                "search_keyword": keyword,
                "search_location": location,
                "response": response.json(),
            }

            with open(filename, "w") as f:
                json.dump(data_to_save, f, indent=2)

    if failures:
        print(f"\n{len(failures)} search(es) failed after retries:")
        for keyword, location, status_code in failures:
            print(f"  - {keyword} in {location} (status: {status_code})")
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    load_dotenv()
    run()
