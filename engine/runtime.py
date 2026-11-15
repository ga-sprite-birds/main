"""Runtime discovery file for the Core command channel."""

from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from typing import Any

from system.config import PROJECT_ROOT

APP_NAME = "ga-sprite-birds"
PROTOCOL_VERSION = 1
DEFAULT_RUN_DIR = PROJECT_ROOT / "run"


def new_token() -> str:
    return secrets.token_urlsafe(32)


def write_discovery(
    path: str | Path,
    *,
    pid: int,
    host: str,
    port: int,
    token: str,
    started_at: str,
) -> dict[str, Any]:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "app": APP_NAME,
        "pid": pid,
        "host": host,
        "port": port,
        "protocol_version": PROTOCOL_VERSION,
        "token": token,
        "started_at": started_at,
    }
    temporary = target.with_name(f"{target.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if os.name != "nt":
        os.chmod(temporary, 0o600)
    os.replace(temporary, target)
    if os.name != "nt":
        os.chmod(target, 0o600)
    return payload


def read_discovery(path: str | Path) -> dict[str, Any] | None:
    target = Path(path)
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    required = {
        "app",
        "pid",
        "host",
        "port",
        "protocol_version",
        "token",
        "started_at",
    }
    if not required.issubset(payload):
        return None
    if payload.get("app") != APP_NAME:
        return None
    return payload


def remove_discovery(path: str | Path, *, pid: int | None = None) -> None:
    target = Path(path)
    if pid is not None:
        current = read_discovery(target)
        if current and int(current.get("pid", -1)) != pid:
            return
    try:
        target.unlink(missing_ok=True)
    except OSError:
        pass
