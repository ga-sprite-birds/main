# 测试快速开始

```bash
# 单元测试（最快，无需启动服务）
bash tests/run_tests.sh unit          # Linux / macOS
tests\run_tests.bat unit              # Windows

# 或直接使用 pytest
python -m pytest tests/unit -q
python -m pytest tests/unit/test_api_v2.py -v
```

集成测试需要先启动引擎与 API（不可达时会自动跳过）：

```bash
python -m engine run   # 终端 A
python -m server run   # 终端 B
python -m pytest tests/integration -v
```

更多说明（目录结构、标记、fixtures、覆盖率）：

- [tests/README.md](README.md)
- [开发文档](../help/zh/development.md)
- [开发者指南](../help/zh/developer-guide.md)

---

**更新时间**：2026-11-18
