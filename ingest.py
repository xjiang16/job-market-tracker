import requests

app_id = "b65e4d14"
app_key = "3a38770353cd861859730adfafca31d5"

url = "https://api.adzuna.com/v1/api/jobs/us/search/1"
params = {
    "app_id": app_id,
    "app_key": app_key,
    "what": "data engineer"
}

response = requests.get(url, params=params)
print(response.status_code)
print(response.json())