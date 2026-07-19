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

keywords = [
    "data engineer",
    "data engineer II",
    "analytics engineer",
    "senior data engineer",
    "data platform engineer",
]

locations = [
    "Austin TX",
    "Remote",
    "Texas",
]

for keyword in keywords:
    for location in locations:
        print(f"Fetching {keyword} in {location}...")
        params = {
            "app_id": app_id,
            "app_key": app_key,
            "what": keyword,
            "where": location,
        }
        response = requests.get(url, params=params)
        print(response.status_code)

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