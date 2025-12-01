"""
测试上传接口
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
def test_upload_with_file(sample_text_file):
    """测试文件上传"""
    with open(sample_text_file, "rb") as f:
        response = client.post(
            "/upload",
            files={"file": ("sample.txt", f, "text/plain")}
        )
    
    assert response.status_code == 200
    data = response.json()
    
    # 验证响应结构
    assert "task_id" in data
    assert "status" in data
    assert "message" in data
    
    # 验证状态
    assert data["status"] == "pending"
    assert len(data["task_id"]) > 0


@pytest.mark.unit
def test_upload_with_path(sample_text_file):
    """测试本地路径上传"""
    response = client.post(
        "/upload",
        params={"path": str(sample_text_file)}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "task_id" in data
    assert data["status"] == "pending"


@pytest.mark.unit
def test_upload_without_file_or_path():
    """测试缺少文件和路径的错误"""
    response = client.post("/upload")
    
    assert response.status_code == 400
    assert "detail" in response.json()


@pytest.mark.unit
def test_upload_with_nonexistent_path():
    """测试不存在的文件路径"""
    response = client.post(
        "/upload",
        params={"path": "/nonexistent/file.txt"}
    )
    
    assert response.status_code == 404
    assert "detail" in response.json()


@pytest.mark.unit
def test_upload_with_language_en(sample_text_file):
    """测试英语界面"""
    response = client.post(
        "/upload",
        params={
            "path": str(sample_text_file),
            "language": "en_US"
        }
    )
    
    assert response.status_code == 200


@pytest.mark.unit
def test_upload_with_language_zh(sample_text_file):
    """测试中文界面"""
    response = client.post(
        "/upload",
        params={
            "path": str(sample_text_file),
            "language": "zh_CN"
        }
    )
    
    assert response.status_code == 200


@pytest.mark.unit
def test_upload_with_custom_output_path(sample_text_file):
    """测试自定义输出路径"""
    response = client.post(
        "/upload",
        params={
            "path": str(sample_text_file),
            "output_path": "./test_output"
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data

