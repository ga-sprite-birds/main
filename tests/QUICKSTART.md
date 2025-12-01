# API 测试工具 - 快速开始

## 🚀 5 分钟快速测试

### **方法 1：使用测试脚本（推荐）**

#### Linux / macOS

```bash
# 运行单元测试（最快）
bash tests/run_tests.sh unit

# 生成测试报告
bash tests/run_tests.sh report
```

#### Windows

```cmd
# 运行单元测试（最快）
tests\run_tests.bat unit

# 生成测试报告
tests\run_tests.bat report
```

---

### **方法 2：直接使用 pytest**

```bash
# 运行所有单元测试
pytest tests/unit -v

# 运行特定测试
pytest tests/unit/test_upload.py -v

# 只看通过/失败统计
pytest tests/unit --tb=no
```

---

## 📊 测试结果示例

```
======================== test session starts =========================
collected 22 items

tests/unit/test_root.py::test_root PASSED                      [  4%]
tests/unit/test_root.py::test_root_response_structure PASSED   [  9%]
tests/unit/test_upload.py::test_upload_with_file PASSED        [ 13%]
tests/unit/test_upload.py::test_upload_with_path PASSED        [ 18%]
tests/unit/test_upload.py::test_upload_without_file_or_path PASSED [ 22%]
tests/unit/test_upload.py::test_upload_with_nonexistent_path PASSED [ 27%]
tests/unit/test_upload.py::test_upload_with_language_en PASSED [ 31%]
tests/unit/test_upload.py::test_upload_with_language_zh PASSED [ 36%]
tests/unit/test_upload.py::test_upload_with_custom_output_path PASSED [ 40%]
tests/unit/test_parse.py::test_parse_success PASSED            [ 45%]
tests/unit/test_parse.py::test_parse_nonexistent_task PASSED   [ 50%]
tests/unit/test_parse.py::test_parse_with_language PASSED      [ 54%]
tests/unit/test_parse.py::test_parse_response_structure PASSED [ 59%]
tests/unit/test_generate.py::test_generate_success PASSED      [ 63%]
tests/unit/test_generate.py::test_generate_nonexistent_task PASSED [ 68%]
tests/unit/test_generate.py::test_generate_with_custom_voice PASSED [ 72%]
tests/unit/test_generate.py::test_generate_disable_llm PASSED  [ 77%]
tests/unit/test_generate.py::test_generate_with_language PASSED [ 81%]
tests/unit/test_task_status.py::test_get_task_status_success PASSED [ 86%]
tests/unit/test_task_status.py::test_get_task_status_nonexistent PASSED [ 90%]
tests/unit/test_task_status.py::test_get_task_status_after_parse PASSED [ 95%]

======================= 21 passed in 2.34s ==========================
```

---

## ❓ 常见问题

### Q: 测试失败怎么办？

**查看详细错误信息**：
```bash
pytest tests/unit/test_upload.py -v -s
```

### Q: 如何只运行某个测试？

```bash
# 运行单个测试文件
pytest tests/unit/test_upload.py

# 运行单个测试函数
pytest tests/unit/test_upload.py::test_upload_with_file
```

### Q: 如何生成 HTML 报告？

```bash
# 使用脚本
bash tests/run_tests.sh report

# 或直接使用 pytest
pip install pytest-html
pytest tests/unit --html=report.html --self-contained-html
```

---

## 📚 更多信息

- 完整文档：[tests/README.md](README.md)
- 开发指南：[help/development-guide.md](../help/development-guide.md)
- 安装指南：[help/INSTALL.md](../help/INSTALL.md)

---

**版本**: 1.0.0  
**更新时间**: 2025-12-01

