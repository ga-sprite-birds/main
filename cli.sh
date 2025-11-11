#!/bin/bash

# GA Sprite Birds - CLI 启动脚本
# 版本: v1.0

# 设置代理（如果需要，可以注释掉）
export http_proxy=http://127.0.0.1:1080
export https_proxy=http://127.0.0.1:1080

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 切换到项目目录
cd "${SCRIPT_DIR}"


# 设置 PYTHONPATH 并运行 CLI
PYTHONPATH=. python fcgi-bin/cli.py "$@"

