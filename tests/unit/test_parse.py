"""
Test the parsing endpoint
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
def test_parse_success(sample_multi_chapter_file):
    """Test parsing succeeds"""
    # 1. Upload the file first
    upload_response = client.post(
        "/upload",
        params={"path": str(sample_multi_chapter_file)}
    )
    task_id = upload_response.json()["task_id"]
    
    # 2. Parse text
    parse_response = client.post(
        "/parse",
        json={"task_id": task_id}
    )
    
    assert parse_response.status_code == 200
    data = parse_response.json()
    
    # Verify response structure
    assert "task_id" in data
    assert "status" in data
    assert "message" in data
    
    # Verify status
    assert data["status"] == "parsed"
    assert data["task_id"] == task_id


@pytest.mark.unit
def test_parse_nonexistent_task():
    """Test parsing a non-existent task"""
    response = client.post(
        "/parse",
        json={"task_id": "nonexistent_task_id"}
    )
    
    assert response.status_code == 404
    assert "detail" in response.json()


@pytest.mark.unit
def test_parse_with_language(sample_text_file):
    """Test multi-language parsing"""
    # Upload file
    upload_response = client.post(
        "/upload",
        params={"path": str(sample_text_file)}
    )
    task_id = upload_response.json()["task_id"]
    
    # Parse using the English interface
    parse_response = client.post(
        "/parse",
        json={
            "task_id": task_id,
            "language": "en_US"
        }
    )
    
    assert parse_response.status_code == 200


@pytest.mark.unit
def test_parse_response_structure(sample_multi_chapter_file):
    """Test the parsing response structure"""
    # Upload file
    upload_response = client.post(
        "/upload",
        params={"path": str(sample_multi_chapter_file)}
    )
    task_id = upload_response.json()["task_id"]
    
    # Parse
    parse_response = client.post(
        "/parse",
        json={"task_id": task_id}
    )
    
    data = parse_response.json()
    
    # Verify required fields
    required_fields = ["task_id", "status", "message"]
    for field in required_fields:
        assert field in data, f"缺少必需字段: {field}"

