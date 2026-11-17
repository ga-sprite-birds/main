#!/bin/sh
# Run the Core engine and the Control API in one container.
# They share loopback, so the API can reach the engine command channel
# (127.0.0.1:39300) and read run/engine.json.
set -u
cd /app

python -m engine run &
ENGINE_PID=$!

# Wait briefly for the engine to publish its discovery file.
i=0
while [ ! -f run/engine.json ] && [ "$i" -lt 100 ]; do
    i=$((i + 1))
    sleep 0.1
done

python -m server run "$@" &
SERVER_PID=$!

terminate() {
    kill -TERM "$SERVER_PID" 2>/dev/null || true
    kill -TERM "$ENGINE_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
    wait "$ENGINE_PID" 2>/dev/null || true
}
trap terminate TERM INT

wait "$SERVER_PID"
STATUS=$?
terminate
exit "$STATUS"
