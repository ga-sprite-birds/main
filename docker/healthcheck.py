"""Docker healthcheck: API alive and Core engine reachable."""

from __future__ import annotations

import json
import os
import sys
import urllib.request

BASE = "http://127.0.0.1:8000"
TOKEN = (os.getenv("API_AUTH_TOKEN") or "").strip()
HEADERS = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}


def healthy(path: str) -> bool:
    try:
        request = urllib.request.Request(BASE + path, headers=HEADERS)
        with urllib.request.urlopen(request, timeout=3) as response:
            status = response.status
            payload = json.load(response)
        return status == 200 and payload.get("code") == 0
    except Exception:
        return False


sys.exit(0 if healthy("/fcgi-bin/api/status") and healthy("/fcgi-bin/api/engine") else 1)
