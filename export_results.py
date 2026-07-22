"""
Queries the current skills breakdown from Snowflake and writes it to
docs/data.json, so the public results page can display real, current
numbers without needing a live database connection of its own.

Run this any time after `dbt run` to refresh the public page's data.
"""

import json
import os
from datetime import date

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

query = """
    SELECT
        SUM(CASE WHEN mentions_python THEN how_many ELSE 0 END) AS python,
        SUM(CASE WHEN mentions_sql THEN how_many ELSE 0 END) AS sql,
        SUM(CASE WHEN mentions_airflow THEN how_many ELSE 0 END) AS airflow,
        SUM(CASE WHEN mentions_snowflake THEN how_many ELSE 0 END) AS snowflake,
        SUM(CASE WHEN mentions_dbt THEN how_many ELSE 0 END) AS dbt,
        SUM(how_many) AS total,
        SUM(CASE WHEN NOT mentions_python AND NOT mentions_sql AND NOT mentions_airflow
                 AND NOT mentions_snowflake AND NOT mentions_dbt THEN how_many ELSE 0 END) AS none_mentioned
    FROM (
        SELECT
            mentions_python, mentions_sql, mentions_airflow, mentions_snowflake, mentions_dbt,
            COUNT(*) AS how_many
        FROM job_skills
        GROUP BY 1,2,3,4,5
    )
"""

cursor.execute(query)
row = cursor.fetchone()
python, sql, airflow, snowflake_ct, dbt, total, none_mentioned = row

def pct(n):
    return round((n / total) * 100, 1) if total else 0

data = {
    "last_updated": date.today().isoformat(),
    "total_postings": total,
    "skills": [
        {"label": "SQL", "count": sql, "pct": pct(sql)},
        {"label": "Python", "count": python, "pct": pct(python)},
        {"label": "Snowflake", "count": snowflake_ct, "pct": pct(snowflake_ct)},
        {"label": "Airflow", "count": airflow, "pct": pct(airflow)},
        {"label": "dbt", "count": dbt, "pct": pct(dbt)},
    ],
    "none_mentioned": none_mentioned,
    "none_mentioned_pct": pct(none_mentioned),
}

# Sort skills descending by count, matching the page's display order
data["skills"].sort(key=lambda s: s["count"], reverse=True)

os.makedirs("docs", exist_ok=True)
with open("docs/data.json", "w") as f:
    json.dump(data, f, indent=2)

print(f"Wrote docs/data.json — {total} postings, last_updated={data['last_updated']}")

cursor.close()
conn.close()
