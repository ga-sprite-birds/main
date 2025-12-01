"""
测试根路径
"""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 动态导入 fcgi-bin.api
import importlib.util
api_path = project_root / "fcgi-bin" / "api.py"
spec = importlib.util.spec_from_file_location("api", api_path)
api_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api_module)

app = api_module.app
client = TestClient(app)


@pytest.mark.unit
def test_root():
    """测试根路径返回正确信息"""
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "name" in data
    assert "version" in data
    assert "status" in data
    assert data["status"] == "running"


@pytest.mark.unit
def test_root_response_structure():
    """测试根路径响应结构"""
    response = client.get("/")
    data = response.json()
    
    # 验证必需字段
    required_fields = ["name", "version", "status"]
    for field in required_fields:
        assert field in data, f"缺少必需字段: {field}"
    
    # 验证字段类型
    assert isinstance(data["name"], str)
    assert isinstance(data["version"], str)
    assert isinstance(data["status"], str)

