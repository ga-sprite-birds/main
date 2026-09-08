@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0\..\.."

if "%API_PORT%"=="" set API_PORT=8000
set DEFAULT_PORT=%API_PORT%
set PORT=%DEFAULT_PORT%
set /A END_PORT=%DEFAULT_PORT%+100

for /L %%i in (0,1,100) do (
    set /A CANDIDATE=%DEFAULT_PORT%+%%i
    netstat -ano | findstr /R /C:":!CANDIDATE! .*LISTENING" >nul
    if errorlevel 1 (
        set PORT=!CANDIDATE!
        goto :PORT_FOUND
    )
)

echo 错误: %DEFAULT_PORT% 到 %END_PORT% 之间没有可用端口
exit /b 1

:PORT_FOUND
if not "%PORT%"=="%DEFAULT_PORT%" echo 端口 %DEFAULT_PORT% 已被占用，自动切换到 %PORT%
set API_PORT=%PORT%
set PYTHONPATH=%PYTHONPATH%;%CD%

echo 正在启动 GA Sprite Birds 本地服务: http://127.0.0.1:%API_PORT%/
echo 按 Ctrl+C 停止服务

start "" "http://127.0.0.1:%API_PORT%/index.html"

python fcgi-bin/api.py

pause
