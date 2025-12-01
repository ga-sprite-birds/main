#!/bin/bash
# 快速测试脚本 - 只运行几个关键测试

echo "========================================="
echo "  快速测试 - 验证 API 修复"
echo "========================================="
echo ""

# 运行关键测试
python -m pytest tests/unit/test_root.py -v
python -m pytest tests/unit/test_upload.py::test_upload_with_file -v
python -m pytest tests/unit/test_upload.py::test_upload_without_file_or_path -v
python -m pytest tests/unit/test_parse.py::test_parse_success -v

echo ""
echo "========================================="
echo "  快速测试完成"
echo "========================================="

