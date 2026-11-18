# GA Sprite Birds — 测试说明

本目录包含 v2 的单元测试与真实链路集成测试。

---

## 1. 目录结构

```text
tests/
├── unit/                      # 单元测试（无需启动服务）
│   ├── test_api_v2.py         # API 契约（信封、路由、错误码、缓存头）
│   ├── test_audio_exporter.py # 输出路径、前置章节、重名策略
│   ├── test_character_metadata.py
│   ├── test_config_service.py # 三层配置、覆盖、热重载
│   ├── test_dialogue_parser_metadata.py
│   ├── test_engine_service.py # 命令分发与校验
│   ├── test_engine_store.py   # TaskStore、状态机、恢复、清理
│   ├── test_prosody.py
│   ├── test_shared_pipeline.py
│   ├── test_system_config.py  # 配置 schema、枚举译文完整性
│   ├── test_task_view.py
│   ├── test_text_normalizer.py
│   ├── test_tts_preview.py
│   └── test_voice_assigner.py
├── integration/
│   └── test_full_workflow.py  # 真实 API + 引擎完整流程（不可达时自动 skip）
├── fixtures/                  # 测试文本
├── conftest.py                # 隔离临时目录、fixtures
├── pytest.ini                 # 标记、testpaths、asyncio_mode
├── run_tests.sh               # Linux/macOS 测试脚本
├── run_tests.bat              # Windows 测试脚本
├── run_quick_test.sh
└── README.md
```

当前单元测试共 **107 项**。

---

## 2. 快速开始

```bash
# 单元测试（推荐，无需服务）
python -m pytest tests/unit -q

# 单个文件
python -m pytest tests/unit/test_api_v2.py -v

# 全部测试（集成测试在 API/引擎不可达时自动跳过）
python -m pytest tests
```

也可以使用脚本：

```bash
bash tests/run_tests.sh unit          # Linux / macOS
tests\run_tests.bat unit              # Windows
```

集成测试需要先启动两个进程：

```bash
python -m engine run   # 终端 A
python -m server run   # 终端 B
API_BASE_URL=http://127.0.0.1:8000 python -m pytest tests/integration -v
```

---

## 3. 测试标记

`tests/pytest.ini` 已注册并启用 `--strict-markers`：

```bash
python -m pytest -m unit              # 只跑单元测试
python -m pytest -m integration       # 只跑集成测试
python -m pytest -m "not slow"        # 排除慢速测试
python -m pytest -m "unit and not slow"
```

标记：`unit`、`integration`、`slow`。

---

## 4. 隔离与 fixtures

`tests/conftest.py` 会把以下目录指向临时目录，避免污染仓库：

- `TASK_CACHE_DIR`
- `API_UPLOAD_DIR`
- `OUTPUT_BASE_PATH`

常用 fixtures：

| fixture | 说明 |
|---|---|
| `test_root` | 测试目录 |
| `fixtures_dir` | `tests/fixtures` |
| `sample_text_file` | 简单示例文本 |
| `sample_multi_chapter_file` | 多章节示例文本 |
| `api_base_url` | 集成测试 API 地址，可用 `API_BASE_URL` 覆盖 |

---

## 5. 编写测试

- 单元测试放 `tests/unit/`，加 `@pytest.mark.unit`；不需要启动服务。
- 集成测试放 `tests/integration/`，加 `@pytest.mark.integration`；API 不可达时用 `pytest.skip(...)`，不要直接失败。
- 优先写契约测试：信封结构、错误码、配置 schema、枚举译文、缓存头、幂等行为。
- 改动 API/CLI 行为时，同步更新 `tests/unit/test_api_v2.py` 与 [API 参考](../help/zh/api.md)。

---

## 6. 可选：报告与覆盖率

```bash
pip install pytest-html
python -m pytest tests/unit --html=report.html --self-contained-html

pip install pytest-cov
python -m pytest tests/unit --cov=ga_birds --cov=fcgi-bin --cov-report=html
```

---

## 7. 相关文档

- [开发文档](../help/zh/development.md)
- [开发者指南](../help/zh/developer-guide.md)
- [API 参考](../help/zh/api.md)

---

**更新时间**：2026-11-18
