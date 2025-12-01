"""
测试解析接口
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
def test_parse_success(sample_multi_chapter_file):
    """测试解析成功"""
    # 1. 先上传文件
    upload_response = client.post(
        "/upload",
        params={"path": str(sample_multi_chapter_file)}
    )
    task_id = upload_response.json()["task_id"]
    
    # 2. 解析文本
    parse_response = client.post(
        "/parse",
        json={"task_id": task_id}
    )
    
    assert parse_response.status_code == 200
    data = parse_response.json()
    
    # 验证响应结构
    assert "task_id" in data
    assert "status" in data
    assert "message" in data
    
    # 验证状态
    assert data["status"] == "parsed"
    assert data["task_id"] == task_id


@pytest.mark.unit
def test_parse_nonexistent_task():
    """测试解析不存在的任务"""
    response = client.post(
        "/parse",
        json={"task_id": "nonexistent_task_id"}
    )
    
    assert response.status_code == 404
    assert "detail" in response.json()


@pytest.mark.unit
def test_parse_with_language(sample_text_file):
    """测试多语言解析"""
    # 上传文件
    upload_response = client.post(
        "/upload",
        params={"path": str(sample_text_file)}
    )
    task_id = upload_response.json()["task_id"]
    
    # 使用英语界面解析
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
    """测试解析响应结构"""
    # 上传文件
    upload_response = client.post(
        "/upload",
        params={"path": str(sample_multi_chapter_file)}
    )
    task_id = upload_response.json()["task_id"]
    
    # 解析
    parse_response = client.post(
        "/parse",
        json={"task_id": task_id}
    )
    
    data = parse_response.json()
    
    # 验证必需字段
    required_fields = ["task_id", "status", "message"]
    for field in required_fields:
        assert field in data, f"缺少必需字段: {field}"

