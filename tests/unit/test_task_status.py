"""
Test the task status query endpoint
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


@pytest.mark.unit
def test_get_task_status_success(sample_text_file):
    """Test querying task status succeeds"""
    # Create task
    upload_response = client.post(
        "/upload",
        params={"path": str(sample_text_file)}
    )
    task_id = upload_response.json()["task_id"]
    
    # Query status
    status_response = client.get(f"/task/{task_id}/status")
    
    assert status_response.status_code == 200
    data = status_response.json()
    
    # Verify the response contains the necessary fields
    assert "task_id" in data or "status" in data


@pytest.mark.unit
def test_get_task_status_nonexistent():
    """Test querying a non-existent task"""
    response = client.get("/task/nonexistent_task_id/status")
    
    assert response.status_code == 404
    assert "detail" in response.json()


@pytest.mark.unit
def test_get_task_status_after_parse(sample_text_file):
    """Test task status after parsing"""
    # Create and parse the task
    upload_response = client.post(
        "/upload",
        params={"path": str(sample_text_file)}
    )
    task_id = upload_response.json()["task_id"]
    
    client.post("/parse", json={"task_id": task_id})
    
    # Query status
    status_response = client.get(f"/task/{task_id}/status")
    
    assert status_response.status_code == 200
    data = status_response.json()
    
    # Status should be parsed or later
    if "status" in data:
        assert data["status"] in ["parsed", "generating", "completed"]

