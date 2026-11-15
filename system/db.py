"""SQLite connections for system configuration and task persistence."""

import logging
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

from system.config import PROJECT_ROOT

logger = logging.getLogger(__name__)

SYSTEM_DB_PATH = PROJECT_ROOT / "data" / "system.db"
TASKS_DB_PATH = PROJECT_ROOT / "data" / "tasks.db"


def utc_now_iso() -> str:
    """Return the current UTC time in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def _connect(db_path: str | Path, readonly: bool) -> sqlite3.Connection:
    path = Path(db_path).expanduser().resolve()
    if not readonly:
        path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(
        path,
        timeout=30.0,
        check_same_thread=False,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 30000")
    if readonly:
        connection.execute("PRAGMA query_only = ON")
    else:
        _enable_wal(connection)
    return connection


def _enable_wal(connection: sqlite3.Connection, attempts: int = 3) -> None:
    """Switch to WAL, degrading gracefully when the filesystem refuses.

    Switching journal mode takes a short exclusive lock. On network shares
    (SMB/NFS) that can fail with "unable to open database file" while the other
    process holds the database, so retry briefly and fall back to the rollback
    journal instead of breaking the caller.
    """
    last_error: sqlite3.OperationalError | None = None
    for attempt in range(attempts):
        try:
            connection.execute("PRAGMA journal_mode = WAL")
            return
        except sqlite3.OperationalError as exc:
            last_error = exc
            time.sleep(0.1 * (attempt + 1))
    logger.warning("切换到 WAL 失败，改用回滚日志模式：%s", last_error)
    try:
        connection.execute("PRAGMA journal_mode = DELETE")
    except sqlite3.OperationalError as exc:
        logger.warning("无法设置日志模式，沿用数据库现有设置：%s", exc)


def connect_system_db(
    db_path: str | Path | None = None,
    *,
    readonly: bool = False,
) -> sqlite3.Connection:
    """Open the system configuration database."""
    return _connect(db_path or SYSTEM_DB_PATH, readonly)


def connect_tasks_db(
    db_path: str | Path | None = None,
    *,
    readonly: bool = False,
) -> sqlite3.Connection:
    """Open tasks.db; API callers must pass readonly=True."""
    return _connect(db_path or TASKS_DB_PATH, readonly)
