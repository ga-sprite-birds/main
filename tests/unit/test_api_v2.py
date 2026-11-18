"""Contract tests for the v2 Control API.

The API is a thin control plane: it validates inputs, forwards commands to the
Core engine and reads task state from ``tasks.db``. These tests replace the
engine with a recording fake so the HTTP contract can be asserted without a
running Core process.
"""

import importlib.util
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.control.client import EngineUnavailable  # noqa: E402
from system.deps import get_control_service  # noqa: E402

SPEC = importlib.util.spec_from_file_location(
    "fcgi_api_v2", PROJECT_ROOT / "fcgi-bin" / "api.py"
)
api = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(api)

API = "/fcgi-bin/api"


class _FakeQuery:
    def get_chapter(self, task_id: str, chapter_index: int):
        return {"task_id": task_id, "chapter_index": chapter_index, "status": "done"}


class _FakeClient:
    def stats(self):
        return {"max_concurrent": 2, "active_count": 0, "tasks": {}}


class FakeControl:
    """Records forwarded commands instead of talking to the engine."""

    def __init__(self):
        self.calls: list[tuple[str, tuple, dict]] = []
        self.query = _FakeQuery()
        self.client = _FakeClient()
        self.fail_with: Exception | None = None

    def _record(self, name, *args, **kwargs):
        if self.fail_with is not None:
            raise self.fail_with
        self.calls.append((name, args, kwargs))
        return {"task_id": kwargs.get("task_id") or (args[0] if args else "t1")}

    def add_task(self, payload, **kwargs):
        return self._record("add_task", payload, **kwargs)

    def parse(self, task_id, **kwargs):
        return self._record("parse", task_id, **kwargs)

    def generate(self, task_id, options, **kwargs):
        return self._record("generate", task_id, options, **kwargs)

    def pause(self, task_id, **kwargs):
        return self._record("pause", task_id, **kwargs)

    def resume(self, task_id, **kwargs):
        return self._record("resume", task_id, **kwargs)

    def cancel(self, task_id, **kwargs):
        return self._record("cancel", task_id, **kwargs)

    def retry(self, task_id, **kwargs):
        return self._record("retry", task_id, **kwargs)

    def remove(self, task_id, **kwargs):
        return self._record("remove", task_id, **kwargs)

    def remove_chapter(self, task_id, chapter_index, **kwargs):
        return self._record("remove_chapter", task_id, chapter_index, **kwargs)

    def status(self, task_id):
        return self._record("status", task_id)

    def events(self, task_id, **kwargs):
        return []

    def list_tasks(self, **kwargs):
        return {"tasks": [], "total": 0}

    def cleanup(self, **kwargs):
        return self._record("cleanup", **kwargs)


@pytest.fixture
def control():
    fake = FakeControl()
    api.app.dependency_overrides[get_control_service] = lambda: fake
    yield fake
    api.app.dependency_overrides.clear()


@pytest.fixture
def client(control):
    return TestClient(api.app)


@pytest.mark.unit
def test_root_serves_packaged_gui(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert 'id="app"' in response.text


@pytest.mark.unit
def test_spa_history_fallback_serves_gui(client):
    response = client.get("/policy/system/config")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


@pytest.mark.unit
def test_status_uses_response_envelope(client):
    payload = client.get(f"{API}/status").json()

    assert payload["code"] == 0
    data = payload["data"]
    assert data["name"] == "GA Sprite Birds"
    assert data["status"] == "running"
    assert data["defaults"]["prosody_mode"] in {"off", "pause", "prosody"}


@pytest.mark.unit
def test_unknown_route_returns_envelope(client):
    response = client.get(f"{API}/does-not-exist")

    assert response.status_code == 404
    payload = response.json()
    assert payload["code"] == 3002


@pytest.mark.unit
def test_error_responses_are_not_cacheable(client):
    """404 属于浏览器可启发式缓存的状态码。

    路由后来才加上时，被缓存的 404 会让同一个 URL 一直失败（试听接口踩过坑），
    所以所有错误响应都必须带 no-store。
    """
    response = client.get(f"{API}/does-not-exist")

    assert response.status_code == 404
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.unit
def test_upload_rejects_unsupported_extension(client, control):
    response = client.post(
        f"{API}/upload",
        files={"file": ("novel.exe", b"binary", "application/octet-stream")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 1000
    assert control.calls == []


@pytest.mark.unit
def test_upload_sanitizes_client_filename(client, control, tmp_path, monkeypatch):
    monkeypatch.setattr(api.settings, "API_UPLOAD_DIR", tmp_path)

    payload = client.post(
        f"{API}/upload",
        files={"file": ("..\\..\\evil\\chapter.txt", "第一章 你好".encode(), "text/plain")},
    ).json()

    assert payload["code"] == 0
    name, args, kwargs = control.calls[0]
    assert name == "add_task"
    stored = Path(args[0]["file_path"])
    assert stored.parent == tmp_path
    assert stored.name.endswith("_chapter.txt")
    assert stored.name.count("_chapter") == 1
    assert args[0]["source_name"] == "chapter.txt"


@pytest.mark.unit
def test_upload_forwards_idempotency_key(client, control):
    client.post(
        f"{API}/upload",
        files={"file": ("chapter.txt", b"hello", "text/plain")},
        headers={"Idempotency-Key": "abc123"},
    )

    _, _, kwargs = control.calls[0]
    assert kwargs["command_id"] == "abc123"
    assert kwargs["idempotency_key"] == "abc123"


@pytest.mark.unit
def test_upload_requires_a_source(client):
    payload = client.post(f"{API}/upload").json()

    assert payload["code"] == 1001


@pytest.mark.unit
def test_upload_rejects_missing_path(client, tmp_path, monkeypatch):
    monkeypatch.setattr(api.settings, "API_UPLOAD_DIR", tmp_path)
    payload = client.post(
        f"{API}/upload", params={"path": str(tmp_path / "missing.txt")}
    ).json()

    assert payload["code"] == 3002


@pytest.mark.unit
def test_parse_forwards_command(client, control):
    payload = client.post(
        f"{API}/parse", json={"task_id": "t1", "command_id": "c1"}
    ).json()

    assert payload["code"] == 0
    name, args, kwargs = control.calls[0]
    assert name == "parse"
    assert args == ("t1",)
    assert kwargs["command_id"] == "c1"


@pytest.mark.unit
def test_generate_forwards_options_without_transport_fields(client, control):
    client.post(
        f"{API}/generate",
        json={
            "task_id": "t1",
            "command_id": "c2",
            "chapter_indexes": [1, 2],
            "voice": "zh-CN-YunjianNeural",
            "rate": 1.1,
        },
    )

    _, args, kwargs = control.calls[0]
    assert kwargs["command_id"] == "c2"
    options = args[1]
    assert "task_id" not in options
    assert "command_id" not in options
    assert options["chapter_indexes"] == [1, 2]
    assert options["rate"] == 1.1


@pytest.mark.unit
def test_generate_rejects_invalid_rate(client, control):
    response = client.post(
        f"{API}/generate", json={"task_id": "t1", "rate": 5.0}
    )

    payload = response.json()
    assert payload["code"] != 0
    assert control.calls == []


@pytest.mark.unit
def test_task_commands_are_forwarded(client, control):
    for action in ("pause", "resume", "cancel", "retry"):
        control.calls.clear()
        payload = client.post(
            f"{API}/task/t1/{action}", json={"command_id": f"cmd-{action}"}
        ).json()
        assert payload["code"] == 0, action
        name, args, kwargs = control.calls[0]
        assert name == action
        assert args == ("t1",)
        assert kwargs["command_id"] == f"cmd-{action}"


@pytest.mark.unit
def test_delete_task_passes_delete_outputs_flag(client, control):
    client.delete(f"{API}/task/t1", params={"delete_outputs": "true"})

    name, args, kwargs = control.calls[0]
    assert name == "remove"
    assert args == ("t1",)
    assert kwargs["delete_outputs"] is True


@pytest.mark.unit
def test_delete_chapter_is_forwarded(client, control):
    client.delete(f"{API}/task/t1/chapter/3")

    name, args, _ = control.calls[0]
    assert name == "remove_chapter"
    assert args == ("t1", 3)


@pytest.mark.unit
def test_status_is_not_cached(client, control):
    response = client.get(f"{API}/task/t1/status")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert control.calls[0][0] == "status"


@pytest.mark.unit
def test_engine_unavailable_maps_to_503(control):
    control.fail_with = EngineUnavailable("Core engine is not running")
    client = TestClient(api.app)

    response = client.post(f"{API}/task/t1/pause", json={})

    assert response.status_code == 503
    assert response.json()["code"] == 3004


@pytest.mark.unit
def test_cleanup_is_forwarded(client, control):
    payload = client.post(
        f"{API}/tasks/cleanup", json={"ttl_seconds": 60, "dry_run": True}
    ).json()

    assert payload["code"] == 0
    assert control.calls[0][0] == "cleanup"


@pytest.mark.unit
def test_idempotent_upload_reuses_the_same_stored_path(
    client, control, tmp_path, monkeypatch
):
    """同一 Idempotency-Key 重试必须产生完全相同的命令载荷，否则引擎会判定输入冲突。"""
    monkeypatch.setattr(api.settings, "API_UPLOAD_DIR", tmp_path)

    for _ in range(2):
        client.post(
            f"{API}/upload",
            files={"file": ("book.txt", b"hello", "text/plain")},
            headers={"Idempotency-Key": "same-key"},
        )

    payloads = [call[1][0] for call in control.calls]
    assert len(payloads) == 2
    assert payloads[0]["file_path"] == payloads[1]["file_path"]
    assert payloads[0]["source_name"] == payloads[1]["source_name"]


@pytest.mark.unit
def test_idempotent_upload_reuses_the_same_stored_path(
    client, control, tmp_path, monkeypatch
):
    """同一 Idempotency-Key 重试必须产生完全相同的命令载荷，否则引擎会判定输入冲突。"""
    monkeypatch.setattr(api.settings, "API_UPLOAD_DIR", tmp_path)

    for _ in range(2):
        client.post(
            f"{API}/upload",
            files={"file": ("book.txt", b"hello", "text/plain")},
            headers={"Idempotency-Key": "same-key"},
        )

    payloads = [call[1][0] for call in control.calls]
    assert len(payloads) == 2
    assert payloads[0]["file_path"] == payloads[1]["file_path"]
    assert payloads[0]["source_name"] == payloads[1]["source_name"]


@pytest.mark.unit
def test_api_auth_requires_bearer_or_cookie(client, control, monkeypatch):
    token = "audit-token-0123456789abcdef"
    monkeypatch.setattr(api.settings, "API_AUTH_ENABLED", True)
    monkeypatch.setattr(api.settings, "API_AUTH_TOKEN", token)

    denied = client.get(f"{API}/tasks")
    assert denied.status_code == 401
    assert denied.json()["code"] == 2001

    allowed = client.get(
        f"{API}/tasks", headers={"Authorization": f"Bearer {token}"}
    )
    assert allowed.status_code == 200
    assert allowed.json()["code"] == 0

    header_allowed = client.get(
        f"{API}/tasks", headers={"X-API-Token": token}
    )
    assert header_allowed.status_code == 200

    client.cookies.set(api.API_TOKEN_COOKIE, token)
    try:
        cookie_allowed = client.get(f"{API}/tasks")
        assert cookie_allowed.status_code == 200
    finally:
        client.cookies.clear()


@pytest.mark.unit
def test_upload_rejects_path_outside_read_roots(client, control):
    payload = client.post(
        f"{API}/upload", params={"path": "/etc/hosts.txt"}
    ).json()

    assert payload["code"] == 1000
    assert control.calls == []
