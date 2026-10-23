"""
Regression tests for API input validation and parse guards.
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import importlib.util

api_path = project_root / "fcgi-bin" / "api.py"
spec = importlib.util.spec_from_file_location("api", api_path)
api_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api_module)

client = TestClient(api_module.app)


def _create_parsed_task(sample_text_file) -> str:
    response = client.post(
        "/upload",
        params={"path": str(sample_text_file)}
    )
    assert response.status_code == 200
    task_id = response.json()["task_id"]

    response = client.post("/parse", json={"task_id": task_id})
    assert response.status_code == 200
    return task_id


@pytest.mark.unit
def test_upload_rejects_unsupported_extension():
    response = client.post(
        "/upload",
        files={"file": ("payload.exe", b"not a book", "application/octet-stream")}
    )
    assert response.status_code == 400


@pytest.mark.unit
def test_upload_sanitizes_client_filename():
    response = client.post(
        "/upload",
        files={"file": ("../../evil.md", b"# Chapter 1\n\n" + b"text " * 100, "text/markdown")}
    )
    assert response.status_code == 200

    task = api_module.task_manager.get_task(response.json()["task_id"])
    saved_name = Path(task.metadata["file_path"]).name
    assert ".." not in saved_name
    assert saved_name.endswith("_evil.md")


@pytest.mark.unit
def test_upload_enforces_size_limit(monkeypatch):
    monkeypatch.setattr(api_module.config, "API_MAX_UPLOAD_SIZE", 1)
    payload = b"a" * (1024 * 1024 + 1)
    response = client.post(
        "/upload",
        files={"file": ("big.txt", payload, "text/plain")}
    )
    assert response.status_code == 413


@pytest.mark.unit
def test_generate_rejects_empty_chapter_indexes(sample_text_file):
    task_id = _create_parsed_task(sample_text_file)
    response = client.post(
        "/generate",
        json={"task_id": task_id, "chapter_indexes": []}
    )
    assert response.status_code == 400


@pytest.mark.unit
def test_generate_rejects_unknown_chapter_index(sample_text_file):
    task_id = _create_parsed_task(sample_text_file)
    response = client.post(
        "/generate",
        json={"task_id": task_id, "chapter_indexes": [9999]}
    )
    assert response.status_code == 400


@pytest.mark.unit
def test_generate_rejects_invalid_rate(sample_text_file):
    task_id = _create_parsed_task(sample_text_file)
    response = client.post(
        "/generate",
        json={"task_id": task_id, "chapter_indexes": [1], "rate": 9}
    )
    assert response.status_code == 400


@pytest.mark.unit
def test_parse_rejects_reparse_after_audio(sample_text_file):
    task_id = _create_parsed_task(sample_text_file)
    task = api_module.task_manager.get_task(task_id)
    task.chapters[0].audio_path = "/tmp/existing.mp3"

    response = client.post("/parse", json={"task_id": task_id})
    assert response.status_code == 409
