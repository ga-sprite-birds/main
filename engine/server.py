"""Localhost HTTP command channel for the Core engine."""

from __future__ import annotations

import hmac
import json
import logging
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from engine.runtime import write_discovery

logger = logging.getLogger(__name__)

HOST = "127.0.0.1"
DEFAULT_PORT = 39300
MAX_BODY_BYTES = 4 * 1024 * 1024


class EngineHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def bind_engine_server(
    service: Any,
    token: str,
    *,
    preferred_port: int = DEFAULT_PORT,
    port_attempts: int = 100,
) -> EngineHTTPServer:
    """Bind a localhost port, advancing when the preferred one is occupied."""
    handler = _make_handler(service, token)
    last_error: OSError | None = None
    for offset in range(port_attempts):
        port = preferred_port + offset
        if port > 65535:
            break
        try:
            return EngineHTTPServer((HOST, port), handler)
        except OSError as exc:
            last_error = exc
            continue
    raise OSError(
        f"No free engine port between {preferred_port} and "
        f"{preferred_port + port_attempts - 1}"
    ) from last_error


class EngineServer:
    def __init__(
        self,
        service: Any,
        token: str,
        discovery_path: str | Path,
        *,
        preferred_port: int = DEFAULT_PORT,
    ) -> None:
        self.service = service
        self.token = token
        self.discovery_path = Path(discovery_path)
        self.httpd = bind_engine_server(
            service, token, preferred_port=preferred_port
        )
        self.port = int(self.httpd.server_address[1])
        self._thread: threading.Thread | None = None

    def start(self, *, pid: int, started_at: str) -> dict[str, Any]:
        info = write_discovery(
            self.discovery_path,
            pid=pid,
            host=HOST,
            port=self.port,
            token=self.token,
            started_at=started_at,
        )
        self._thread = threading.Thread(
            target=self.httpd.serve_forever,
            name="engine-command-http",
            daemon=True,
        )
        self._thread.start()
        return info

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    @property
    def address(self) -> str:
        return f"http://{HOST}:{self.port}"


def _make_handler(service: Any, token: str):
    class Handler(BaseHTTPRequestHandler):
        server_version = "GASpriteBirdsCore/2"

        def do_GET(self) -> None:
            if not self._authenticated():
                return
            if self.path == "/system/info":
                self._respond(200, {"code": 0, "msg": "ok", "data": service.system_info()})
            elif self.path == "/system/stats":
                self._respond(200, {"code": 0, "msg": "ok", "data": service.system_stats()})
            elif self.path == "/health":
                self._respond(200, {"code": 0, "msg": "ok", "data": {"status": "ok"}})
            else:
                self._respond(404, {"code": 3002, "msg": "Not found", "data": {}})

        def do_POST(self) -> None:
            if not self._authenticated():
                return
            if self.path != "/command":
                self._respond(404, {"code": 3002, "msg": "Not found", "data": {}})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                self._respond(400, {"code": 1001, "msg": "Invalid Content-Length", "data": {}})
                return
            if length <= 0 or length > MAX_BODY_BYTES:
                self._respond(400, {"code": 1001, "msg": "Invalid body size", "data": {}})
                return
            try:
                body = json.loads(self.rfile.read(length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._respond(400, {"code": 1001, "msg": "Invalid JSON", "data": {}})
                return
            if not isinstance(body, dict):
                self._respond(400, {"code": 1001, "msg": "Body must be an object", "data": {}})
                return
            command_id = body.get("command_id")
            command = body.get("command")
            payload = body.get("payload") or {}
            if not isinstance(command_id, str) or not isinstance(command, str):
                self._respond(
                    200,
                    {"code": 1001, "msg": "command_id and command are required", "data": {}},
                )
                return
            if not isinstance(payload, dict):
                self._respond(
                    200,
                    {"code": 1001, "msg": "payload must be an object", "data": {}},
                )
                return
            result = service.execute(command_id, command, payload)
            self._respond(200, result)

        def _authenticated(self) -> bool:
            header = self.headers.get("Authorization", "")
            expected = f"Bearer {token}"
            if not hmac.compare_digest(header, expected):
                self._respond(401, {"code": 2001, "msg": "Unauthorized", "data": {}})
                return False
            return True

        def _respond(self, status: int, payload: dict[str, Any]) -> None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, format: str, *args: Any) -> None:
            logger.debug("command channel: " + format, *args)

        def finish(self) -> None:
            # Each request runs on its own thread; release that thread's
            # tasks.db connection so per-thread connections do not accumulate.
            try:
                super().finish()
            finally:
                store = getattr(service, "store", None)
                if store is not None:
                    store.close_thread_connection()

    return Handler


def port_is_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True
