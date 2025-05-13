import sqlite3
from db import createDB, reset_database

def test_createDB_and_tables(tmp_path):
    db_file = tmp_path / "test.db"
    # this should create all tables (user, content, exercise, workoutSession, issueForm)
    createDB(str(db_file))
    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cursor.fetchall()}
    expected = {"user", "content", "exercise", "workoutSession", "issueForm"}
    assert expected.issubset(tables)
    conn.close()

def test_reset_database(tmp_path):
    db_file = tmp_path / "test2.db"
    # create schema + insert one user row
    createDB(str(db_file))
    conn = sqlite3.connect(str(db_file))
    conn.execute(
        "INSERT INTO user(full_name, username, password, email) VALUES (?,?,?,?)",
        ("A", "B", "C", "D")
    )
    conn.commit()
    conn.close()

    # now reset and confirm no rows in each table
    reset_database(str(db_file))
    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()
    for tbl in ["user", "content", "exercise", "workoutSession", "issueForm"]:
        cursor.execute(f"SELECT COUNT(*) FROM {tbl}")
        assert cursor.fetchone()[0] == 0
    conn.close()
