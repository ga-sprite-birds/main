"""
测试生成接口
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
def test_generate_success(sample_text_file):
    """测试生成音频请求成功"""
    # 1. 上传文件
    upload_response = client.post(
        "/upload",
        params={"path": str(sample_text_file)}
    )
    task_id = upload_response.json()["task_id"]
    
    # 2. 解析文本
    client.post("/parse", json={"task_id": task_id})
    
    # 3. 生成音频
    generate_response = client.post(
        "/generate",
        json={"task_id": task_id}
    )
    
    assert generate_response.status_code == 200
    data = generate_response.json()
    
    # 验证响应结构
    assert "task_id" in data
    assert "status" in data
    assert "message" in data
    
    # 验证状态
    assert data["status"] == "generating"
    assert data["task_id"] == task_id


@pytest.mark.unit
def test_generate_nonexistent_task():
    """测试生成不存在的任务"""
    response = client.post(
        "/generate",
        json={"task_id": "nonexistent_task_id"}
    )
    
    assert response.status_code == 404
    assert "detail" in response.json()


@pytest.mark.unit
def test_generate_without_parse(sample_text_file):
    """测试未解析就生成"""
    # 只上传，不解析
    upload_response = client.post(
        "/upload",
        params={"path": str(sample_text_file)}
    )
    task_id = upload_response.json()["task_id"]
    
    # 直接生成
    generate_response = client.post(
        "/generate",
        json={"task_id": task_id}
    )

    assert generate_response.status_code == 400
    assert "detail" in generate_response.json()


@pytest.mark.unit
def test_generate_with_custom_voice(sample_text_file):
    """测试自定义音色"""
    # 上传和解析
    upload_response = client.post(
        "/upload",
        params={"path": str(sample_text_file)}
    )
    task_id = upload_response.json()["task_id"]
    client.post("/parse", json={"task_id": task_id})
    
    # 使用自定义音色生成
    generate_response = client.post(
        "/generate",
        json={
            "task_id": task_id,
            "voice": "zh-CN-YunxiNeural"
        }
    )
    
    assert generate_response.status_code == 200


@pytest.mark.unit
def test_generate_disable_llm(sample_text_file):
    """测试禁用 LLM"""
    # 上传和解析
    upload_response = client.post(
        "/upload",
        params={"path": str(sample_text_file)}
    )
    task_id = upload_response.json()["task_id"]
    client.post("/parse", json={"task_id": task_id})
    
    # 禁用 LLM 生成
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
    """测试多语言生成"""
    # 上传和解析
    upload_response = client.post(
        "/upload",
        params={"path": str(sample_text_file)}
    )
    task_id = upload_response.json()["task_id"]
    client.post("/parse", json={"task_id": task_id})
    
    # 使用英语界面生成
    generate_response = client.post(
        "/generate",
        json={
            "task_id": task_id,
            "language": "en_US"
        }
    )
    
    assert generate_response.status_code == 200

