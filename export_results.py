"""
Queries the current skills breakdown from the local DuckDB warehouse and writes
it to docs/data.json (plus the trend history to docs/data_history.json), so the
public results page can display real, current numbers without needing a live
database connection of its own.

Then saves the persisted tables back to data/warehouse/ (see warehouse.py), so
the next run picks up where this one left off.

Run this after `dbt run` to refresh the public page's data.
"""

import json
import os
from datetime import date

import duckdb

import warehouse

SKILL_COLUMNS = [
    ("python", "Python"),
    ("sql", "SQL"),
    ("airflow", "Airflow"),
    ("snowflake", "Snowflake"),
    ("dbt", "dbt"),
    ("aws", "AWS"),
    ("spark", "Spark"),
    ("kafka", "Kafka"),
    ("redshift", "Redshift"),
    ("bigquery", "BigQuery"),
    ("gcp", "GCP"),
    ("docker", "Docker"),
    ("databricks", "Databricks"),
    ("terraform", "Terraform"),
    ("java", "Java"),
    ("scala", "Scala"),
]

_mentions_cols = ", ".join(f"mentions_{key}" for key, _ in SKILL_COLUMNS)
_sums = ",\n        ".join(
    f"SUM(CASE WHEN mentions_{key} THEN how_many ELSE 0 END) AS {key}" for key, _ in SKILL_COLUMNS
)
_none_condition = " AND ".join(f"NOT mentions_{key}" for key, _ in SKILL_COLUMNS)

QUERY = f"""
    SELECT
        {_sums},
        SUM(how_many) AS total,
        SUM(CASE WHEN {_none_condition} THEN how_many ELSE 0 END) AS none_mentioned
    FROM (
        SELECT
            {_mentions_cols},
            COUNT(*) AS how_many
        FROM ANALYTICS.job_skills
        GROUP BY {", ".join(str(i) for i in range(1, len(SKILL_COLUMNS) + 1))}
    )
"""

HISTORY_QUERY = """
    SELECT snapshot_date, skill, pct
    FROM ANALYTICS.skill_trends
    ORDER BY snapshot_date, skill
"""

# skill_trends.skill comes from an UNPIVOT over unquoted column names. DuckDB
# keeps them lowercase; Snowflake (which this pipeline used to run on) uppercased
# them — map defensively rather than assume case.
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
    *skill_counts, total, none_mentioned = row

    data = {
        "last_updated": today,
        "total_postings": total,
        "skills": [
            {"label": label, "count": count, "pct": pct(count, total)}
            for (_, label), count in zip(SKILL_COLUMNS, skill_counts)
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
        # Database drivers can return numeric columns like pct as decimal.Decimal
        # (Snowflake did), which json.dump() can't serialize — convert to float
        # here, at the point it enters the dict that becomes JSON.
        by_date.setdefault(date_key, {"date": date_key})[label] = float(pct_value)

    history = [by_date[d] for d in sorted(by_date)]
    return {"series": SERIES_ORDER, "history": history}


def run(db_path=warehouse.DB_PATH, store_dir=warehouse.STORE_DIR):
    con = duckdb.connect(db_path)

    try:
        row = con.execute(QUERY).fetchone()
        data = compute_data(row, date.today().isoformat())

        history = build_history(con.execute(HISTORY_QUERY).fetchall())

        os.makedirs("docs", exist_ok=True)
        with open("docs/data.json", "w") as f:
            json.dump(data, f, indent=2)
        with open("docs/data_history.json", "w") as f:
            json.dump(history, f, indent=2)

        print(f"Wrote docs/data.json — {data['total_postings']} postings, last_updated={data['last_updated']}")
        print(f"Wrote docs/data_history.json — {len(history['history'])} day(s) of history")

        warehouse.save(con, store_dir)
        print(f"Saved warehouse tables to {store_dir}/")
    finally:
        con.close()


if __name__ == "__main__":  # pragma: no cover
    run()
