"""HTTP client for the Core localhost command channel."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Mapping

from engine.runtime import PROTOCOL_VERSION, read_discovery
from system.config import settings


class EngineUnavailable(RuntimeError):
    def __init__(self, message: str = "Engine is not running") -> None:
        super().__init__(message)


class EngineProtocolError(RuntimeError):
    pass


class EngineClient:
    def __init__(
        self,
        discovery_path: str | Path | None = None,
        *,
        timeout: float = 300.0,
    ) -> None:
        self.discovery_path = Path(discovery_path) if discovery_path else (
            settings.RUN_DIR / "engine.json"
        )
        self.timeout = timeout

    def discovery(self) -> dict[str, Any]:
        info = read_discovery(self.discovery_path)
        if info is None:
            raise EngineUnavailable(
                f"Engine discovery file is missing: {self.discovery_path}"
            )
        if int(info.get("protocol_version", -1)) != PROTOCOL_VERSION:
            raise EngineProtocolError(
                "Engine protocol version is incompatible: "
                f"expected {PROTOCOL_VERSION}, got {info.get('protocol_version')}"
            )
        return info

    def request(
        self,
        method: str,
        path: str,
        body: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        info = self.discovery()
        url = f"http://{info['host']}:{int(info['port'])}{path}"
        data = None
        headers = {
            "Authorization": f"Bearer {info['token']}",
            "Accept": "application/json",
        }
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json; charset=utf-8"
        request = urllib.request.Request(
            url, data=data, headers=headers, method=method
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            raise EngineUnavailable(
                f"Engine returned HTTP {exc.code}"
            ) from exc
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            raise EngineUnavailable("Engine is not reachable") from exc
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise EngineProtocolError("Engine returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise EngineProtocolError("Engine returned a non-object response")
        return payload

    def info(self) -> dict[str, Any]:
        return self._unwrap(self.request("GET", "/system/info"))

    def stats(self) -> dict[str, Any]:
        return self._unwrap(self.request("GET", "/system/stats"))

    def command(
        self,
        command: str,
        payload: Mapping[str, Any] | None = None,
        *,
        command_id: str | None = None,
    ) -> dict[str, Any]:
        envelope = self.request(
            "POST",
            "/command",
            {
                "command_id": command_id or str(uuid.uuid4()),
                "command": command,
                "payload": dict(payload or {}),
            },
        )
        return self._unwrap(envelope)

    def raw_command(
        self,
        command: str,
        payload: Mapping[str, Any] | None = None,
        *,
        command_id: str | None = None,
    ) -> dict[str, Any]:
        return self.request(
            "POST",
            "/command",
            {
                "command_id": command_id or str(uuid.uuid4()),
                "command": command,
                "payload": dict(payload or {}),
            },
        )

    @staticmethod
    def _unwrap(envelope: Mapping[str, Any]) -> dict[str, Any]:
        if int(envelope.get("code", -1)) != 0:
            error = {
                "code": envelope.get("code"),
                "msg": envelope.get("msg"),
                "data": envelope.get("data"),
            }
            raise EngineCommandError(error)
        data = envelope.get("data")
        return data if isinstance(data, dict) else {"value": data}


class EngineCommandError(RuntimeError):
    def __init__(self, error: Mapping[str, Any]) -> None:
        super().__init__(str(error.get("msg") or "Engine command failed"))
        self.code = int(error.get("code") or 4000)
        self.data = error.get("data") or {}
