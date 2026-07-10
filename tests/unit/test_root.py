"""
Test the root path
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
def test_root():
    """Test that the root path returns correct information"""
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "name" in data
    assert "version" in data
    assert "status" in data
    assert data["status"] == "running"


@pytest.mark.unit
def test_root_response_structure():
    """Test the root path response structure"""
    response = client.get("/")
    data = response.json()
    
    # Verify required fields
    required_fields = ["name", "version", "status"]
    for field in required_fields:
        assert field in data, f"缺少必需字段: {field}"
    
    # Verify field types
    assert isinstance(data["name"], str)
    assert isinstance(data["version"], str)
    assert isinstance(data["status"], str)

