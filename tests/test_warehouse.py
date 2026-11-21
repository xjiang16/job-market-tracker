from datetime import date, datetime

import duckdb

import warehouse


def test_restore_with_no_saved_data_creates_empty_raw_table_only(tmp_path):
    con = duckdb.connect()

    warehouse.restore(con, str(tmp_path / "does-not-exist"))

    assert con.execute("SELECT COUNT(*) FROM RAW.job_postings").fetchone() == (0,)
    # skill_trends is left for dbt to create on its first run.
    tables = con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'ANALYTICS'"
    ).fetchall()
    assert tables == []


def test_save_then_restore_round_trips_both_tables(tmp_path):
    store_dir = str(tmp_path / "store")
    description = 'Has "quotes", commas,\nand a newline.'

    con = duckdb.connect()
    warehouse.restore(con, store_dir)
    con.execute(
        "INSERT INTO RAW.job_postings VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("1", "Data Engineer", "Acme", "Remote", 100000.0, None,
         datetime(2026, 8, 1), description, "data engineer", "Remote",
         datetime(2026, 11, 20, 7, 17, 3, 123456)),
    )
    con.execute(warehouse.TRENDS_DDL)
    con.execute("INSERT INTO ANALYTICS.skill_trends VALUES ('2026-11-20', 'sql', NULL, NULL, 14.3)")
    warehouse.save(con, store_dir)
    con.close()

    restored = duckdb.connect()
    warehouse.restore(restored, store_dir)

    assert restored.execute("SELECT * FROM RAW.job_postings").fetchall() == [
        ("1", "Data Engineer", "Acme", "Remote", 100000.0, None,
         datetime(2026, 8, 1), description, "data engineer", "Remote",
         datetime(2026, 11, 20, 7, 17, 3, 123456)),
    ]
    assert restored.execute("SELECT * FROM ANALYTICS.skill_trends").fetchall() == [
        (date(2026, 11, 20), "sql", None, None, 14.3),
    ]


def test_save_writes_rows_in_a_stable_sorted_order(tmp_path):
    store_dir = tmp_path / "store"
    con = duckdb.connect()
    warehouse.restore(con, str(store_dir))
    con.execute(warehouse.TRENDS_DDL)
    con.execute("""
        INSERT INTO ANALYTICS.skill_trends VALUES
            ('2026-11-20', 'sql', 5, 1, 20.0),
            ('2026-11-19', 'sql', 5, 1, 20.0),
            ('2026-11-20', 'dbt', 5, 1, 20.0)
    """)

    warehouse.save(con, str(store_dir))

    lines = (store_dir / warehouse.TRENDS_FILE).read_text().splitlines()
    assert [line.split(",")[:2] for line in lines[1:]] == [
        ["2026-11-19", "sql"],
        ["2026-11-20", "dbt"],
        ["2026-11-20", "sql"],
    ]
