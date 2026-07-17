import json
import os
from datetime import date
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

Path("data/raw").mkdir(parents=True, exist_ok=True)

app_id = os.environ["ADZUNA_APP_ID"]
app_key = os.environ["ADZUNA_APP_KEY"]

url = "https://api.adzuna.com/v1/api/jobs/us/search/1"

keywords = ["data engineer", "analytics engineer", "data analytic engineer"]

for keyword in keywords:
    print(f"Fetching {keyword}...")
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "what": keyword,
    }
    response = requests.get(url, params=params)
    print(response.status_code)

    safe_keyword = keyword.replace(" ", "_")
    filename = f"data/raw/{date.today().isoformat()}_{safe_keyword}.json"
    with open(filename, "w") as f:
        json.dump(response.json(), f, indent=2)
    print(f"Saved to {filename}")