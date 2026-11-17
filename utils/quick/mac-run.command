#!/bin/bash
# GA Sprite Birds - quick start (macOS)
# Starts the Core engine and the Control API together, then opens the GUI.

cd "$(dirname "$0")/../.."

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    PYTHON_BIN="python"
fi

port_in_use() {
    local port="$1"
    if command -v lsof >/dev/null 2>&1; then
        lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
        return $?
    fi
    if command -v nc >/dev/null 2>&1; then
        nc -z 127.0.0.1 "$port" >/dev/null 2>&1
        return $?
    fi
    "$PYTHON_BIN" - "$port" <<'PY'
import socket
import sys

port = int(sys.argv[1])
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.settimeout(0.2)
    sys.exit(0 if sock.connect_ex(("127.0.0.1", port)) == 0 else 1)
PY
}

DEFAULT_PORT="${API_PORT:-8000}"
PORT="$DEFAULT_PORT"
for offset in $(seq 0 100); do
    CANDIDATE=$((DEFAULT_PORT + offset))
    if ! port_in_use "$CANDIDATE"; then
        PORT="$CANDIDATE"
        break
    fi
done
if port_in_use "$PORT"; then
    echo "错误: ${DEFAULT_PORT} 到 $((DEFAULT_PORT + 100)) 之间没有可用端口"
    exit 1
fi
if [ "$PORT" != "$DEFAULT_PORT" ]; then
    echo "端口 ${DEFAULT_PORT} 已被占用，API 使用 ${PORT}"
fi

ENGINE_PID=""
STARTED_ENGINE=0
cleanup() {
    if [ "$STARTED_ENGINE" = "1" ] && [ -n "$ENGINE_PID" ]; then
        echo
        echo "正在停止 Core 引擎..."
        kill -TERM "$ENGINE_PID" 2>/dev/null || true
        wait "$ENGINE_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

if "$PYTHON_BIN" -m engine status >/dev/null 2>&1; then
    echo "检测到 Core 引擎已在运行，复用现有实例。"
else
    echo "启动 Core 引擎..."
    "$PYTHON_BIN" -m engine run &
    ENGINE_PID=$!
    STARTED_ENGINE=1
    for _ in $(seq 1 50); do
        [ -f run/engine.json ] && break
        sleep 0.1
    done
fi

URL="http://127.0.0.1:${PORT}/"
echo "启动 Control API + GUI: ${URL}"
echo "按 Ctrl+C 停止。"
( sleep 2 && open "$URL" >/dev/null 2>&1 ) &

"$PYTHON_BIN" -m server run --port "$PORT" --strict-port
