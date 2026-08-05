import glob
import json
import os

import snowflake.connector
from dotenv import load_dotenv

INSERT_SQL = """
    INSERT INTO JOB_POSTINGS (
        job_id, title, company, location, salary_min, salary_max,
        created_date, description, search_keyword, search_location
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


def build_rows(file_data):
    search_keyword = file_data["search_keyword"]
    search_location = file_data["search_location"]
    jobs = file_data["response"]["results"]

    return [
        (
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
        for job in jobs
    ]


def load_files(json_files, cursor):
    total_rows = 0
    for filepath in json_files:
        with open(filepath, "r") as f:
            file_data = json.load(f)

        for row in build_rows(file_data):
            cursor.execute(INSERT_SQL, row)
            total_rows += 1

    return total_rows


def run():
    conn = snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        database=os.environ["SNOWFLAKE_DATABASE"],
        schema=os.environ["SNOWFLAKE_SCHEMA"],
    )
    cursor = conn.cursor()

    try:
        json_files = glob.glob("data/raw/*.json")
        print(f"Found {len(json_files)} files to load")

        total_rows = load_files(json_files, cursor)

        conn.commit()
        print(f"Loaded {total_rows} job postings into Snowflake")
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    load_dotenv()
    run()
