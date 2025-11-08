#!/bin/bash

# GA Sprite Birds - 启动脚本
# 版本: v1.0

echo "正在启动 GA Sprite Birds 音频朗读系统..."

# 设置代理（如果需要，可以注释掉）
export http_proxy=http://127.0.0.1:1080
export https_proxy=http://127.0.0.1:1080

# 设置 Python 路径（重要！）
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 检查 Python 环境
if ! command -v python &> /dev/null; then
    echo "错误：未找到 Python，请先安装 Python 3.10+"
    exit 1
fi

# 显示 Python 版本
echo "Python 版本："
python --version

# 启动 FastAPI 服务
echo "正在启动 API 服务..."
echo "访问 http://localhost:8000/docs 查看 API 文档"
echo "按 Ctrl+C 停止服务"
echo ""

python fcgi-bin/api.py

