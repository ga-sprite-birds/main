"""Operational checks for the Core engine."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from engine.server import port_is_available
from system.config import PROJECT_ROOT, settings
from system.db import connect_tasks_db


def process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes

        process_query_limited_information = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(
            process_query_limited_information, False, pid
        )
        if not handle:
            return False
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def status_report(run_dir: str | Path | None = None) -> dict[str, Any]:
    from engine.runtime import read_discovery
    from services.control.client import EngineClient, EngineUnavailable

    directory = Path(run_dir) if run_dir else settings.RUN_DIR
    discovery_path = directory / "engine.json"
    discovery = read_discovery(discovery_path)
    report: dict[str, Any] = {
        "running": False,
        "discovery_path": str(discovery_path),
    }
    if discovery is None:
        report["message"] = "Engine discovery file is missing"
        return report
    alive = process_alive(int(discovery["pid"]))
    report.update(
        {
            "pid": discovery["pid"],
            "host": discovery["host"],
            "port": discovery["port"],
            "protocol_version": discovery["protocol_version"],
            "started_at": discovery["started_at"],
            "process_alive": alive,
        }
    )
    client = EngineClient(discovery_path, timeout=3)
    try:
        report["stats"] = client.stats()
        report["running"] = alive
    except (EngineUnavailable, Exception) as exc:
        report["message"] = str(exc)
    return report


def doctor_report(run_dir: str | Path | None = None) -> dict[str, Any]:
    checks: list[dict[str, str]] = []
    directory = Path(run_dir) if run_dir else settings.RUN_DIR

    def add(name: str, status: str, message: str) -> None:
        checks.append({"name": name, "status": status, "message": message})

    for label, path in (("data_dir", settings.DATA_DIR), ("run_dir", directory)):
        try:
            path.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=path, delete=True):
                pass
            add(label, "ok", str(path))
        except OSError as exc:
            add(label, "error", f"{path}: {exc}")

    # Read-only inspection: only the Core engine may write / migrate tasks.db.
    # Opening through TaskStore here would run migrations from the ops process.
    db_path = settings.DATA_DIR / "tasks.db"
    if not db_path.exists():
        add("tasks_db", "warn", f"not initialized yet: {db_path}")
    else:
        connection = None
        try:
            connection = connect_tasks_db(db_path, readonly=True)
            row = connection.execute(
                "SELECT tasks_schema_version FROM schema_meta WHERE id = 1 LIMIT 1"
            ).fetchone()
            version = int(row[0]) if row else 0
            integrity_rows = connection.execute("PRAGMA quick_check").fetchall()
            integrity = (
                "ok"
                if len(integrity_rows) == 1 and integrity_rows[0][0] == "ok"
                else "; ".join(str(item[0]) for item in integrity_rows)
            )
            if integrity == "ok":
                add("tasks_db", "ok", f"schema version {version}")
            else:
                add(
                    "tasks_db",
                    "error",
                    f"schema version {version}; integrity check failed: {integrity}",
                )
        except Exception as exc:
            add("tasks_db", "error", str(exc))
        finally:
            if connection is not None:
                connection.close()

    try:
        import config

        service = config.get_config_service()
        values = service.get_all()
        add("system_config", "ok", f"{len(values)} effective values")
    except Exception as exc:
        add("system_config", "error", str(exc))

    ffmpeg = shutil.which("ffmpeg")
    if settings.FFMPEG_PATH:
        candidate = Path(settings.FFMPEG_PATH) / "ffmpeg"
        if candidate.exists():
            ffmpeg = str(candidate)
    if ffmpeg:
        add("ffmpeg", "ok", ffmpeg)
    else:
        add("ffmpeg", "warn", "ffmpeg not found in PATH")

    try:
        from engine.runtime import read_discovery

        discovery = read_discovery(directory / "engine.json")
    except Exception:
        discovery = None
    if discovery is None:
        add("discovery", "warn", "engine.json not found")
    else:
        add(
            "discovery",
            "ok" if process_alive(int(discovery["pid"])) else "error",
            f"pid={discovery['pid']} port={discovery['port']}",
        )

    try:
        add(
            "engine_port",
            "ok" if port_is_available("127.0.0.1", 39300) else "warn",
            "39300 is available"
            if port_is_available("127.0.0.1", 39300)
            else "39300 is occupied; the engine will use the next free port",
        )
    except Exception as exc:
        add("engine_port", "warn", str(exc))

    add("project_root", "ok", str(PROJECT_ROOT))
    has_error = any(item["status"] == "error" for item in checks)
    return {"ok": not has_error, "checks": checks}
