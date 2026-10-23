"""
Test the generation endpoint
"""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Add the project root directory to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Dynamically import fcgi-bin.api
import importlib.util
api_path = project_root / "fcgi-bin" / "api.py"
spec = importlib.util.spec_from_file_location("api", api_path)
api_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api_module)

app = api_module.app
client = TestClient(app)


@pytest.fixture(autouse=True)
def stub_generation(monkeypatch):
    """Keep unit tests offline: never start a real TTS job."""
    def fake_launch(task, **kwargs):
        api_module.task_manager.update_task_status(
            task.task_id,
            api_module.TaskStatus.GENERATING
        )

    monkeypatch.setattr(api_module, "_launch_generation", fake_launch)


@pytest.mark.unit
def test_generate_success(sample_text_file):
    """Test that an audio generation request succeeds"""
    # 1. Upload file
    upload_response = client.post(
        "/upload",
        params={"path": str(sample_text_file)}
    )
    task_id = upload_response.json()["task_id"]

    # 2. Parse text
    client.post("/parse", json={"task_id": task_id})

    # 3. Generate audio
    generate_response = client.post(
        "/generate",
        json={"task_id": task_id}
    )

    assert generate_response.status_code == 200
    data = generate_response.json()

    # Verify response structure
    assert "task_id" in data
    assert "status" in data
    assert "message" in data

    # Verify status
    assert data["status"] == "generating"
    assert data["task_id"] == task_id


@pytest.mark.unit
def test_generate_nonexistent_task():
    """Test generating for a non-existent task"""
    response = client.post(
        "/generate",
        json={"task_id": "nonexistent_task_id"}
    )

    assert response.status_code == 404
    assert "detail" in response.json()


@pytest.mark.unit
def test_generate_without_parse(sample_text_file):
    """Test generating without parsing first"""
    # Only upload, do not parse
    upload_response = client.post(
        "/upload",
        params={"path": str(sample_text_file)}
    )
    task_id = upload_response.json()["task_id"]

    # Generate directly
    generate_response = client.post(
        "/generate",
        json={"task_id": task_id}
    )

    assert generate_response.status_code == 400
    assert "detail" in generate_response.json()


@pytest.mark.unit
def test_generate_with_custom_voice(sample_text_file):
    """Test custom voice"""
    # Upload and parse
    upload_response = client.post(
        "/upload",
        params={"path": str(sample_text_file)}
    )
    task_id = upload_response.json()["task_id"]
    client.post("/parse", json={"task_id": task_id})

    # Generate using a custom voice
    generate_response = client.post(
        "/generate",
        json={
            "task_id": task_id,
            "voice": "zh-CN-YunxiNeural"
        }
    )

    assert generate_response.status_code == 200


@pytest.mark.unit
def test_generate_stores_prosody_mode(sample_text_file, monkeypatch):
    """The selected pause/tone mode is passed through and saved for resume."""
    captured = {}

    def fake_launch(task, **kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(api_module, "_launch_generation", fake_launch)

    upload_response = client.post(
        "/upload",
        params={"path": str(sample_text_file)}
    )
    task_id = upload_response.json()["task_id"]
    client.post("/parse", json={"task_id": task_id})

    response = client.post(
        "/generate",
        json={"task_id": task_id, "prosody_mode": "pause"}
    )

    assert response.status_code == 200
    assert captured["prosody_mode"] == "pause"
    task = api_module.task_manager.get_task(task_id)
    assert task.metadata["generation"]["prosody_mode"] == "pause"


@pytest.mark.unit
def test_generate_disable_llm(sample_text_file):
    """Test disabling the LLM"""
    # Upload and parse
    upload_response = client.post(
        "/upload",
        params={"path": str(sample_text_file)}
    )
    task_id = upload_response.json()["task_id"]
    client.post("/parse", json={"task_id": task_id})

    # Generate with the LLM disabled
    generate_response = client.post(
        "/generate",
        json={
            "task_id": task_id,
            "enable_llm": False
        }
    )

    assert generate_response.status_code == 200


@pytest.mark.unit
def test_generate_with_language(sample_text_file):
    """Test multi-language generation"""
    # Upload and parse
    upload_response = client.post(
        "/upload",
        params={"path": str(sample_text_file)}
    )
    task_id = upload_response.json()["task_id"]
    client.post("/parse", json={"task_id": task_id})

    # Generate using the English interface
    generate_response = client.post(
        "/generate",
        json={
            "task_id": task_id,
            "language": "en_US"
        }
    )

    assert generate_response.status_code == 200

