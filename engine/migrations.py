"""Versioned tasks.db migrations."""

from pathlib import Path

from system.db import connect_tasks_db, utc_now_iso

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
TASKS_SCHEMA_VERSION = 1


def migrate_tasks_db(db_path: str | Path | None = None) -> int:
    """Apply all forward migrations and return the resulting version."""
    connection = connect_tasks_db(db_path)
    try:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_meta (
                  id INTEGER PRIMARY KEY CHECK (id = 1),
                  tasks_schema_version INTEGER NOT NULL,
                  updated_at TEXT NOT NULL
                )
                """
            )
            row = connection.execute(
                """
                SELECT tasks_schema_version
                FROM schema_meta
                WHERE id = 1
                LIMIT 1
                """
            ).fetchone()
            current = int(row["tasks_schema_version"]) if row else 0

            if current < 1:
                sql = (MIGRATIONS_DIR / "001_tasks_initial.sql").read_text(
                    encoding="utf-8"
                )
                connection.executescript(sql)

            now = utc_now_iso()
            connection.execute(
                """
                INSERT INTO schema_meta (id, tasks_schema_version, updated_at)
                VALUES (1, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  tasks_schema_version = excluded.tasks_schema_version,
                  updated_at = excluded.updated_at
                """,
                (TASKS_SCHEMA_VERSION, now),
            )
        return TASKS_SCHEMA_VERSION
    finally:
        connection.close()
