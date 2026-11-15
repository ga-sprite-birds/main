"""End-to-end workflow against a running Control API + Core engine.

Start both processes first:
    python -m engine run
    python fcgi-bin/api.py

The tests skip themselves when the API is unreachable, so they are safe to run
in a normal ``pytest`` session without a server.
"""

import asyncio
import time

import httpx
import pytest

API = "/fcgi-bin/api"
TERMINAL = {"succeeded", "failed", "canceled", "removed"}


def _data(response: httpx.Response) -> dict:
    """Unwrap the {code, msg, data} envelope."""
    payload = response.json()
    assert payload.get("code") == 0, payload
    return payload.get("data") or {}


async def _skip_without_server(client: httpx.AsyncClient) -> None:
    try:
        response = await client.get(f"{API}/status")
    except httpx.HTTPError as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"API not reachable: {exc}")
    if response.status_code != 200 or response.json().get("code") != 0:
        pytest.skip("API is not healthy")


async def _require_engine(client: httpx.AsyncClient) -> None:
    response = await client.get(f"{API}/engine")
    if response.status_code != 200 or response.json().get("code") != 0:
        pytest.skip("Core engine is not running")


async def _wait_for(
    client: httpx.AsyncClient,
    task_id: str,
    timeout: float,
    stop_statuses: set[str] | None = None,
) -> dict:
    wanted = (stop_statuses or set()) | TERMINAL
    deadline = time.time() + timeout
    last: dict = {}
    while time.time() < deadline:
        last = _data(await client.get(f"{API}/task/{task_id}/status"))
        if last.get("status") in wanted:
            return last
        await asyncio.sleep(1.5)
    pytest.fail(f"任务超时，最后一次状态：{last}")


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_complete_workflow_simple(api_base_url, sample_text_file):
    """上传 → 解析 → 生成，走完整命令链路并等待终态。"""
    async with httpx.AsyncClient(base_url=api_base_url, timeout=120.0) as client:
        await _skip_without_server(client)
        await _require_engine(client)

        with open(sample_text_file, "rb") as handle:
            upload = await client.post(
                f"{API}/upload",
                files={"file": ("sample.txt", handle, "text/plain")},
            )
        task = _data(upload)
        task_id = task["task_id"]
        assert task["status"] in {"pending", "queued"}

        parsed = _data(
            await client.post(f"{API}/parse", json={"task_id": task_id})
        )
        assert parsed["task_id"] == task_id

        status = _data(await client.get(f"{API}/task/{task_id}/status"))
        assert status["total_chapters"] >= 1

        _data(await client.post(f"{API}/generate", json={"task_id": task_id}))

        final = await _wait_for(client, task_id, timeout=180)
        assert final["status"] == "succeeded", final.get("error")
        assert final["completed_chapters"] >= 1

        events = _data(await client.get(f"{API}/task/{task_id}/events"))
        kinds = [event["type"] for event in events["events"]]
        assert "task.created" in kinds
        assert "task.succeeded" in kinds


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_pause_and_resume_round_trip(api_base_url, sample_multi_chapter_file):
    """暂停后状态落为 paused，继续后可再次完成。"""
    async with httpx.AsyncClient(base_url=api_base_url, timeout=120.0) as client:
        await _skip_without_server(client)
        await _require_engine(client)

        with open(sample_multi_chapter_file, "rb") as handle:
            task = _data(
                await client.post(
                    f"{API}/upload",
                    files={
                        "file": (
                            "sample_multi_chapter.txt",
                            handle,
                            "text/plain",
                        )
                    },
                )
            )
        task_id = task["task_id"]
        _data(await client.post(f"{API}/parse", json={"task_id": task_id}))
        _data(await client.post(f"{API}/generate", json={"task_id": task_id}))

        _data(await client.post(f"{API}/task/{task_id}/pause", json={}))
        paused = await _wait_for(
            client, task_id, timeout=120, stop_statuses={"paused"}
        )
        assert paused["status"] in {"paused", "succeeded"}

        if paused["status"] == "paused":
            _data(await client.post(f"{API}/task/{task_id}/resume", json={}))
            final = await _wait_for(client, task_id, timeout=180)
            assert final["status"] in {"succeeded", "failed"}

        _data(await client.delete(f"{API}/task/{task_id}"))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_handling(api_base_url):
    """缺失资源与缺参都返回统一信封，而不是裸 4xx。"""
    async with httpx.AsyncClient(base_url=api_base_url, timeout=30.0) as client:
        await _skip_without_server(client)

        missing_file = await client.post(
            f"{API}/upload", params={"path": "/nonexistent/file.txt"}
        )
        assert missing_file.json()["code"] == 3002

        missing_task = await client.post(
            f"{API}/parse", json={"task_id": "nonexistent_task"}
        )
        assert missing_task.json()["code"] != 0

        no_source = await client.post(f"{API}/upload")
        assert no_source.json()["code"] == 1001

        bad_extension = await client.post(
            f"{API}/upload",
            files={"file": ("novel.exe", b"binary", "application/octet-stream")},
        )
        assert bad_extension.json()["code"] == 1000
