import glob
import json
import os

import snowflake.connector
from dotenv import load_dotenv

load_dotenv()

conn = snowflake.connector.connect(
    account=os.environ["SNOWFLAKE_ACCOUNT"],
    user=os.environ["SNOWFLAKE_USER"],
    password=os.environ["SNOWFLAKE_PASSWORD"],
    warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
    database=os.environ["SNOWFLAKE_DATABASE"],
    schema=os.environ["SNOWFLAKE_SCHEMA"],
)
cursor = conn.cursor()

insert_sql = """
    INSERT INTO JOB_POSTINGS (
        job_id, title, company, location, salary_min, salary_max,
        created_date, description, search_keyword, search_location
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

json_files = glob.glob("data/raw/*.json")
print(f"Found {len(json_files)} files to load")

total_rows = 0

for filepath in json_files:
    with open(filepath, "r") as f:
        file_data = json.load(f)

    search_keyword = file_data["search_keyword"]
    search_location = file_data["search_location"]
    jobs = file_data["response"]["results"]

    for job in jobs:
        row = (
            job.get("id"),
            job.get("title"),
            job.get("company", {}).get("display_name"),
            job.get("location", {}).get("display_name"),
            job.get("salary_min"),
            job.get("salary_max"),
            job.get("created"),
            job.get("description"),
            search_keyword,
            search_location,
        )
        cursor.execute(insert_sql, row)
        total_rows += 1

conn.commit()
print(f"Loaded {total_rows} job postings into Snowflake")

cursor.close()
conn.close()