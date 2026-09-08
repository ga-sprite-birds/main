#!/bin/bash

cd "$(dirname "${BASH_SOURCE[0]}")/../.."

DEFAULT_PORT="${API_PORT:-8000}"
PORT="$DEFAULT_PORT"
PYTHON_BIN="${PYTHON_BIN:-python}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    PYTHON_BIN="python3"
fi

port_in_use() {
    local port="$1"
    if command -v ss >/dev/null 2>&1; then
        ss -ltn | awk '{print $4}' | grep -Eq "[:.]${port}$"
        return $?
    fi
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
    echo "端口 ${DEFAULT_PORT} 已被占用，自动切换到 ${PORT}"
fi

export API_PORT="$PORT"
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

URL="http://127.0.0.1:${PORT}/"

echo "正在启动 GA Sprite Birds 本地服务: ${URL}"
echo "按 Ctrl+C 停止服务"

( sleep 2 && xdg-open "$URL" >/dev/null 2>&1 ) &

"$PYTHON_BIN" fcgi-bin/api.py

read -r -p "服务已停止，按回车键退出..."
