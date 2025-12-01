"""
测试任务状态查询接口
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
def test_get_task_status_success(sample_text_file):
    """测试查询任务状态成功"""
    # 创建任务
    upload_response = client.post(
        "/upload",
        params={"path": str(sample_text_file)}
    )
    task_id = upload_response.json()["task_id"]
    
    # 查询状态
    status_response = client.get(f"/task/{task_id}/status")
    
    assert status_response.status_code == 200
    data = status_response.json()
    
    # 验证响应包含必要字段
    assert "task_id" in data or "status" in data


@pytest.mark.unit
def test_get_task_status_nonexistent():
    """测试查询不存在的任务"""
    response = client.get("/task/nonexistent_task_id/status")
    
    assert response.status_code == 404
    assert "detail" in response.json()


@pytest.mark.unit
def test_get_task_status_after_parse(sample_text_file):
    """测试解析后的任务状态"""
    # 创建并解析任务
    upload_response = client.post(
        "/upload",
        params={"path": str(sample_text_file)}
    )
    task_id = upload_response.json()["task_id"]
    
    client.post("/parse", json={"task_id": task_id})
    
    # 查询状态
    status_response = client.get(f"/task/{task_id}/status")
    
    assert status_response.status_code == 200
    data = status_response.json()
    
    # 状态应该是 parsed 或更高
    if "status" in data:
        assert data["status"] in ["parsed", "generating", "completed"]

