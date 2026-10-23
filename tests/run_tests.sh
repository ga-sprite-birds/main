#!/bin/bash
# GA Sprite Birds - 测试运行脚本

set -e

echo "========================================="
echo "  GA Sprite Birds - API 测试工具"
echo "========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

PYTHON_BIN="${PYTHON_BIN:-python}"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    PYTHON_BIN="python3"
fi

# 检查 pytest 是否安装
if ! "${PYTHON_BIN}" -c "import pytest" &> /dev/null; then
    echo -e "${RED}错误: pytest 未安装${NC}"
    echo "请运行: ${PYTHON_BIN} -m pip install pytest pytest-asyncio"
    exit 1
fi

# 解析参数
TEST_TYPE=${1:-unit}

case $TEST_TYPE in
    unit)
        echo -e "${GREEN}运行单元测试...${NC}"
        echo "（不需要启动服务器）"
        echo ""
        "${PYTHON_BIN}" -m pytest tests/unit -v -m unit
        ;;

    integration)
        echo -e "${YELLOW}运行集成测试...${NC}"
        echo "（需要先启动 API 服务器）"
        echo ""
        echo "请确保已在另一个终端运行："
        echo "  bash api.sh"
        echo ""
        read -p "按 Enter 继续，或 Ctrl+C 取消..."
        "${PYTHON_BIN}" -m pytest tests/integration -v -m integration
        ;;

    all)
        echo -e "${GREEN}运行所有测试...${NC}"
        echo ""

        # 先运行单元测试
        echo -e "${GREEN}1. 单元测试${NC}"
        "${PYTHON_BIN}" -m pytest tests/unit -v -m unit

        echo ""
        echo -e "${YELLOW}2. 集成测试${NC}"
        echo "请确保已在另一个终端运行："
        echo "  bash api.sh"
        echo ""
        read -p "按 Enter 继续，或 Ctrl+C 取消..."
        "${PYTHON_BIN}" -m pytest tests/integration -v -m integration
        ;;

    report)
        echo -e "${GREEN}生成测试报告...${NC}"
        echo ""

        # 检查 pytest-html 是否安装
        if ! "${PYTHON_BIN}" -c "import pytest_html" &> /dev/null; then
            echo -e "${YELLOW}安装 pytest-html...${NC}"
            "${PYTHON_BIN}" -m pip install pytest-html
        fi

        "${PYTHON_BIN}" -m pytest tests/unit -v --html=report.html --self-contained-html
        echo ""
        echo -e "${GREEN}✓ 报告已生成: report.html${NC}"
        ;;

    coverage)
        echo -e "${GREEN}生成测试覆盖率报告...${NC}"
        echo ""

        # 检查 pytest-cov 是否安装
        if ! "${PYTHON_BIN}" -c "import pytest_cov" &> /dev/null; then
            echo -e "${YELLOW}安装 pytest-cov...${NC}"
            "${PYTHON_BIN}" -m pip install pytest-cov
        fi

        "${PYTHON_BIN}" -m pytest tests/unit --cov=ga_birds --cov=fcgi-bin --cov-report=html
        echo ""
        echo -e "${GREEN}✓ 覆盖率报告已生成: htmlcov/index.html${NC}"
        ;;
    
    help|--help|-h)
        echo "用法: bash tests/run_tests.sh [选项]"
        echo ""
        echo "选项:"
        echo "  unit         运行单元测试（默认，不需要启动服务器）"
        echo "  integration  运行集成测试（需要启动服务器）"
        echo "  all          运行所有测试"
        echo "  report       生成 HTML 测试报告"
        echo "  coverage     生成测试覆盖率报告"
        echo "  help         显示此帮助信息"
        echo ""
        echo "示例:"
        echo "  bash tests/run_tests.sh unit"
        echo "  bash tests/run_tests.sh integration"
        echo "  bash tests/run_tests.sh report"
        ;;
    
    *)
        echo -e "${RED}错误: 未知选项 '$TEST_TYPE'${NC}"
        echo "运行 'bash tests/run_tests.sh help' 查看帮助"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}  测试完成！${NC}"
echo -e "${GREEN}=========================================${NC}"

