import json
import os
from datetime import date
from pathlib import Path

Path("data/raw").mkdir(parents=True, exist_ok=True)

import requests
from dotenv import load_dotenv

load_dotenv()

app_id = os.environ["ADZUNA_APP_ID"]
app_key = os.environ["ADZUNA_APP_KEY"]

url = "https://api.adzuna.com/v1/api/jobs/us/search/1"
params = {
    "app_id": app_id,
    "app_key": app_key,
    "what": "data engineer"
}

response = requests.get(url, params=params)
print(response.status_code)
print(response.json())

filename = f"data/raw/{date.today().isoformat()}_data_engineer.json"
with open(filename, "w") as f:
    json.dump(response.json(), f, indent=2)

print(f"Saved to {filename}")