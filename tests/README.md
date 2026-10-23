# GA Sprite Birds - API 测试工具

API 接口自动化测试工具，用于验证系统功能的正确性。

---

## 📋 目录结构

```
tests/
├── unit/                    # 单元测试（快速，不需要启动服务）
│   ├── test_root.py         # 测试根路径
│   ├── test_upload.py       # 测试上传接口
│   ├── test_parse.py        # 测试解析接口
│   ├── test_generate.py     # 测试生成接口
│   ├── test_api_validation.py       # 上传/解析/生成校验
│   ├── test_generation_control.py   # 暂停、继续与任务控制
│   ├── test_shared_pipeline.py      # 共享章节加载与重名处理
│   ├── test_task_persistence.py     # 任务 JSON 持久化
│   ├── test_character_metadata.py   # 角色元数据
│   ├── test_dialogue_parser_metadata.py # 对话解析元数据
│   ├── test_text_normalizer.py      # 章节标题规范化
│   ├── test_voice_assigner.py       # 音色分配
│   └── test_task_status.py  # 测试任务状态查询
│
├── integration/             # 集成测试（需要启动服务）
│   └── test_full_workflow.py # 完整流程测试
│
├── fixtures/                # 测试数据
│   ├── sample.txt           # 简单文本
│   └── sample_multi_chapter.txt # 多章节文本
│
├── conftest.py              # pytest 全局配置
├── pytest.ini               # pytest 配置文件
└── README.md                # 本文档
```

---

## 🚀 快速开始

### **1. 运行单元测试（推荐）**

单元测试使用 FastAPI TestClient，**不需要启动服务器**，速度快。

```bash
# 运行所有单元测试
pytest tests/unit -v

# 运行特定测试文件
pytest tests/unit/test_upload.py -v

# 运行特定测试函数
pytest tests/unit/test_upload.py::test_upload_with_file -v
```

### **2. 运行集成测试**

集成测试使用真实 HTTP 请求，**需要先启动 API 服务器**。

```bash
# 步骤 1: 启动 API 服务器（新终端）
bash api.sh

# 步骤 2: 运行集成测试（另一个终端）
# 默认连接 http://localhost:8000；可用 API_BASE_URL 覆盖
API_BASE_URL=http://127.0.0.1:8000 pytest tests/integration -v
```

### **3. 运行所有测试**

```bash
# 只运行单元测试（快速）
pytest -m unit -v

# 运行所有测试（需要先启动服务器）
pytest -v
```

---

## 📊 测试标记

使用 pytest 标记来筛选测试：

```bash
# 只运行单元测试
pytest -m unit

# 只运行集成测试
pytest -m integration

# 排除慢速测试
pytest -m "not slow"

# 运行单元测试，排除慢速测试
pytest -m "unit and not slow"
```

---

## 🎯 测试用例说明

### **单元测试（unit/）**

| 文件 | 测试内容 | 用例数 |
|------|---------|--------|
| `test_root.py` | 根路径响应 | 2 |
| `test_upload.py` | 文件上传、路径上传、多语言 | 7 |
| `test_parse.py` | 文本解析、错误处理 | 4 |
| `test_generate.py` | 音频生成、参数配置 | 6 |
| `test_api_validation.py` | 上传、章节范围、语速、重复解析校验 | 7 |
| `test_generation_control.py` | 暂停、继续、任务状态与控制 | 9 |
| `test_shared_pipeline.py` | 共享章节加载、重名策略、0 字节文件 | 4 |
| `test_task_persistence.py` | JSON 持久化、恢复与 TTL | 4 |
| `test_character_metadata.py` | 角色元数据解析 | 2 |
| `test_dialogue_parser_metadata.py` | 对话解析元数据 | 1 |
| `test_text_normalizer.py` | Markdown/加粗标题规范化 | 7 |
| `test_voice_assigner.py` | 音色分配与语言回退 | 7 |
| `test_task_status.py` | 任务状态查询 | 3 |

### **集成测试（integration/）**

| 文件 | 测试内容 | 用例数 |
|------|---------|--------|
| `test_full_workflow.py` | 完整流程、多章节、多语言、错误处理 | 4 |

---

## 📈 测试报告

### **生成 HTML 报告**

```bash
# 安装 pytest-html（可选）
pip install pytest-html

# 生成 HTML 报告
pytest --html=report.html --self-contained-html

# 在浏览器中打开 report.html 查看
```

### **查看测试覆盖率**

```bash
# 安装 pytest-cov（可选）
pip install pytest-cov

# 生成覆盖率报告
pytest --cov=ga_birds --cov=fcgi-bin --cov-report=html

# 在浏览器中打开 htmlcov/index.html 查看
```

---

## 🔧 常见问题

### **Q1: 集成测试失败，提示连接被拒绝**

**原因**：API 服务器未启动

**解决**：
```bash
# 启动 API 服务器
bash api.sh
```

### **Q2: 测试超时**

**原因**：TTS 生成或 LLM 处理时间过长

**解决**：
- 集成测试已禁用 LLM（`enable_llm: False`）
- 使用简单文本文件测试
- 增加超时时间（修改 `timeout` 参数）

### **Q3: 如何跳过某些测试？**

```bash
# 跳过慢速测试
pytest -m "not slow"

# 跳过集成测试
pytest -m "not integration"
```

---

## 📝 添加新测试

### **添加单元测试**

1. 在 `tests/unit/` 创建新文件 `test_xxx.py`
2. 使用 `@pytest.mark.unit` 标记
3. 使用 `TestClient` 进行测试

```python
import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

project_root = Path(__file__).parent.parent.parent
spec = importlib.util.spec_from_file_location(
    "api", project_root / "fcgi-bin" / "api.py"
)
api_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api_module)

client = TestClient(api_module.app)

@pytest.mark.unit
def test_my_feature():
    response = client.get("/my-endpoint")
    assert response.status_code == 200
```

### **添加集成测试**

1. 在 `tests/integration/` 创建新文件 `test_xxx.py`
2. 使用 `@pytest.mark.integration` 标记
3. 使用 `httpx.AsyncClient` 进行测试

```python
import pytest
import httpx

@pytest.mark.integration
@pytest.mark.asyncio
async def test_my_integration(api_base_url):
    async with httpx.AsyncClient(base_url=api_base_url) as client:
        response = await client.get("/my-endpoint")
        assert response.status_code == 200
```

---

## 🎓 最佳实践

1. **优先运行单元测试** - 快速验证基本功能
2. **定期运行集成测试** - 验证完整流程
3. **使用测试标记** - 灵活筛选测试用例
4. **保持测试数据简单** - 加快测试速度
5. **禁用 LLM** - 集成测试中禁用 LLM 加快速度

---

## 📚 参考文档

- [pytest 官方文档](https://docs.pytest.org/)
- [FastAPI 测试文档](https://fastapi.tiangolo.com/tutorial/testing/)
- [httpx 文档](https://www.python-httpx.org/)

---

**版本**: 1.0.0  
**更新时间**: 2026-10-23

