@echo off
REM GA Sprite Birds - 测试运行脚本 (Windows)

setlocal enabledelayedexpansion

echo =========================================
echo   GA Sprite Birds - API 测试工具
echo =========================================
echo.

REM 检查 pytest 是否安装
python -c "import pytest" 2>nul
if errorlevel 1 (
    echo 错误: pytest 未安装
    echo 请运行: pip install pytest pytest-asyncio
    exit /b 1
)

REM 解析参数
set TEST_TYPE=%1
if "%TEST_TYPE%"=="" set TEST_TYPE=unit

if "%TEST_TYPE%"=="unit" (
    echo 运行单元测试...
    echo （不需要启动服务器）
    echo.
    pytest tests/unit -v -m unit
    goto :end
)

if "%TEST_TYPE%"=="integration" (
    echo 运行集成测试...
    echo （需要先启动 API 服务器）
    echo.
    echo 请确保已在另一个终端运行：
    echo   uvicorn fcgi-bin.api:app --host 0.0.0.0 --port 8000
    echo.
    pause
    pytest tests/integration -v -m integration
    goto :end
)

if "%TEST_TYPE%"=="all" (
    echo 运行所有测试...
    echo.
    
    echo 1. 单元测试
    pytest tests/unit -v -m unit
    
    echo.
    echo 2. 集成测试
    echo 请确保已在另一个终端运行：
    echo   uvicorn fcgi-bin.api:app --host 0.0.0.0 --port 8000
    echo.
    pause
    pytest tests/integration -v -m integration
    goto :end
)

if "%TEST_TYPE%"=="report" (
    echo 生成测试报告...
    echo.
    
    REM 检查 pytest-html 是否安装
    python -c "import pytest_html" 2>nul
    if errorlevel 1 (
        echo 安装 pytest-html...
        pip install pytest-html
    )
    
    pytest tests/unit -v --html=report.html --self-contained-html
    echo.
    echo ✓ 报告已生成: report.html
    goto :end
)

if "%TEST_TYPE%"=="coverage" (
    echo 生成测试覆盖率报告...
    echo.
    
    REM 检查 pytest-cov 是否安装
    python -c "import pytest_cov" 2>nul
    if errorlevel 1 (
        echo 安装 pytest-cov...
        pip install pytest-cov
    )
    
    pytest tests/unit --cov=ga_birds --cov=fcgi-bin --cov-report=html
    echo.
    echo ✓ 覆盖率报告已生成: htmlcov/index.html
    goto :end
)

if "%TEST_TYPE%"=="help" goto :help
if "%TEST_TYPE%"=="--help" goto :help
if "%TEST_TYPE%"=="-h" goto :help

echo 错误: 未知选项 '%TEST_TYPE%'
echo 运行 'tests\run_tests.bat help' 查看帮助
exit /b 1

:help
echo 用法: tests\run_tests.bat [选项]
echo.
echo 选项:
echo   unit         运行单元测试（默认，不需要启动服务器）
echo   integration  运行集成测试（需要启动服务器）
echo   all          运行所有测试
echo   report       生成 HTML 测试报告
echo   coverage     生成测试覆盖率报告
echo   help         显示此帮助信息
echo.
echo 示例:
echo   tests\run_tests.bat unit
echo   tests\run_tests.bat integration
echo   tests\run_tests.bat report
goto :end

:end
echo.
echo =========================================
echo   测试完成！
echo =========================================

