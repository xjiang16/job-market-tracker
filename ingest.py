import os
from dotenv import load_dotenv

load_dotenv()

import requests

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