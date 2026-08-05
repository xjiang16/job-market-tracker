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

QUERY = """
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

HISTORY_QUERY = """
    SELECT snapshot_date, skill, pct
    FROM skill_trends
    ORDER BY snapshot_date, skill
"""

# skill_trends.skill comes from an UNPIVOT over unquoted column names, which
# Snowflake normalizes to uppercase — map defensively rather than assume case.
SKILL_LABELS = {
    "PYTHON": "Python",
    "SQL": "SQL",
    "AIRFLOW": "Airflow",
    "SNOWFLAKE": "Snowflake",
    "DBT": "dbt",
}

# Fixed order so a series always renders in the same color across renders,
# regardless of which skill currently ranks highest.
SERIES_ORDER = ["Python", "SQL", "Airflow", "Snowflake", "dbt"]


def pct(n, total):
    return round((n / total) * 100, 1) if total else 0


def compute_data(row, today):
    python, sql, airflow, snowflake_ct, dbt, total, none_mentioned = row

    data = {
        "last_updated": today,
        "total_postings": total,
        "skills": [
            {"label": "SQL", "count": sql, "pct": pct(sql, total)},
            {"label": "Python", "count": python, "pct": pct(python, total)},
            {"label": "Snowflake", "count": snowflake_ct, "pct": pct(snowflake_ct, total)},
            {"label": "Airflow", "count": airflow, "pct": pct(airflow, total)},
            {"label": "dbt", "count": dbt, "pct": pct(dbt, total)},
        ],
        "none_mentioned": none_mentioned,
        "none_mentioned_pct": pct(none_mentioned, total),
    }

    # Sort skills descending by count, matching the page's display order
    data["skills"].sort(key=lambda s: s["count"], reverse=True)

    return data


def build_history(rows):
    """rows: iterable of (snapshot_date, skill, pct) from skill_trends, any order."""
    by_date = {}
    for snapshot_date, skill, pct_value in rows:
        label = SKILL_LABELS.get(str(skill).upper())
        if label is None:
            continue
        date_key = snapshot_date.isoformat() if hasattr(snapshot_date, "isoformat") else str(snapshot_date)
        by_date.setdefault(date_key, {"date": date_key})[label] = pct_value

    history = [by_date[d] for d in sorted(by_date)]
    return {"series": SERIES_ORDER, "history": history}


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
        cursor.execute(QUERY)
        row = cursor.fetchone()
        data = compute_data(row, date.today().isoformat())

        cursor.execute(HISTORY_QUERY)
        history = build_history(cursor.fetchall())

        os.makedirs("docs", exist_ok=True)
        with open("docs/data.json", "w") as f:
            json.dump(data, f, indent=2)
        with open("docs/data_history.json", "w") as f:
            json.dump(history, f, indent=2)

        print(f"Wrote docs/data.json — {data['total_postings']} postings, last_updated={data['last_updated']}")
        print(f"Wrote docs/data_history.json — {len(history['history'])} day(s) of history")
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":  # pragma: no cover
    load_dotenv()
    run()
