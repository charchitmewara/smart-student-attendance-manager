"""
database.py — Database connection factory and schema initializer.

Supports:
  - SQLite for local development (default, zero-config)
  - PostgreSQL via DATABASE_URL env / Streamlit secret for cloud deployment

The rest of the application imports only from this module and models.py —
swapping the backend never requires touching UI or business-logic code.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from typing import Generator

# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

def _get_database_url() -> str | None:
    """Return the DATABASE_URL from Streamlit secrets or environment, or None."""
    # Try Streamlit secrets first (available on Streamlit Community Cloud)
    try:
        import streamlit as st
        url = st.secrets.get("DATABASE_URL", None)
        if url:
            return url
    except Exception:
        pass

    # Fall back to environment variable (local .env or system env)
    return os.environ.get("DATABASE_URL", None)


def _get_db_path() -> str:
    """Return the local SQLite database file path."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_dir = os.path.join(base_dir, "database")
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, "attendance.db")


@contextmanager
def get_connection() -> Generator:
    """
    Context manager that yields a database connection.

    Automatically selects SQLite (local) or PostgreSQL (cloud) based on
    whether DATABASE_URL is configured.

    Usage:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
    """
    database_url = _get_database_url()

    if database_url:
        # PostgreSQL via psycopg2
        try:
            import psycopg2
            conn = psycopg2.connect(database_url)
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
        except ImportError:
            raise RuntimeError(
                "psycopg2 is not installed. "
                "Add 'psycopg2-binary' to requirements.txt for PostgreSQL support."
            )
    else:
        # SQLite (local development)
        db_path = _get_db_path()
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # rows accessible as dicts
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def placeholder() -> str:
    """Return the correct SQL placeholder for the active backend."""
    database_url = _get_database_url()
    return "%s" if database_url else "?"


# ---------------------------------------------------------------------------
# Schema initializer
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS students (
    id                  INTEGER PRIMARY KEY {autoincrement},
    username            TEXT UNIQUE NOT NULL,
    password_hash       TEXT NOT NULL,
    name                TEXT NOT NULL DEFAULT '',
    student_id          TEXT DEFAULT '',
    university          TEXT DEFAULT '',
    course              TEXT DEFAULT '',
    semester            TEXT DEFAULT '',
    required_percentage REAL NOT NULL DEFAULT 75.0,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS semesters (
    id          INTEGER PRIMARY KEY {autoincrement},
    student_id  INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    is_active   INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS subjects (
    id              INTEGER PRIMARY KEY {autoincrement},
    semester_id     INTEGER NOT NULL REFERENCES semesters(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    code            TEXT DEFAULT '',
    threshold       REAL,
    is_archived     INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(semester_id, name)
);

CREATE TABLE IF NOT EXISTS attendance (
    id          INTEGER PRIMARY KEY {autoincrement},
    subject_id  INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    date        DATE NOT NULL,
    status      TEXT NOT NULL CHECK(status IN ('Present','Absent','Medical')),
    session_num INTEGER NOT NULL DEFAULT 1,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(subject_id, date)
);
"""


def init_db() -> None:
    """
    Initialize the database schema.

    Creates all tables if they do not already exist.
    Safe to call on every application start.
    """
    database_url = _get_database_url()
    autoincrement = "AUTOINCREMENT" if not database_url else ""

    sql = _SCHEMA_SQL.format(autoincrement=autoincrement)

    # For PostgreSQL: AUTOINCREMENT → SERIAL syntax is different; use SERIAL
    if database_url:
        sql = sql.replace("INTEGER PRIMARY KEY ", "SERIAL PRIMARY KEY ")

    with get_connection() as conn:
        cursor = conn.cursor()
        # Split on semicolons and run each statement
        for statement in sql.strip().split(";"):
            stmt = statement.strip()
            if stmt:
                cursor.execute(stmt)


# Run schema init when the module is first imported
try:
    init_db()
except Exception as _exc:
    import warnings
    warnings.warn(f"Database initialization failed: {_exc}", RuntimeWarning)
