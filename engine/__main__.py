"""Entry point: python -m engine run|status|doctor."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path

from engine.lock import AlreadyRunningError, InstanceLock
from engine.ops import doctor_report, status_report
from engine.runtime import new_token, remove_discovery
from engine.scheduler import Scheduler
from engine.server import DEFAULT_PORT, EngineServer
from engine.service import EngineService
from engine.store import TaskStore
from system.config import settings
from system.logging_setup import configure_logging


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


async def run_core(
    *,
    run_dir: Path,
    data_dir: Path,
    preferred_port: int,
    max_concurrent: int,
    grace_seconds: float,
) -> int:
    configure_logging("engine")
    run_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    lock = InstanceLock(run_dir / "engine.lock")
    try:
        lock.acquire()
    except AlreadyRunningError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    store = TaskStore(data_dir / "tasks.db")
    scheduler = Scheduler(
        store,
        max_concurrent=max_concurrent,
        grace_seconds=grace_seconds,
        cleanup_ttl_seconds=settings.TASK_RESULT_TTL,
    )
    started_at = _now_iso()
    service = EngineService(
        store,
        scheduler,
        started_at=started_at,
        max_concurrent=max_concurrent,
    )
    token = new_token()
    server: EngineServer | None = None
    try:
        recovered = store.recover_interrupted_tasks()
        store.reset_interrupted_parse()
        server = EngineServer(
            service,
            token,
            run_dir / "engine.json",
            preferred_port=preferred_port,
        )
        server.start(pid=os.getpid(), started_at=started_at)
        scheduler.start()
        print(
            f"Core engine running at {server.address} "
            f"(pid={os.getpid()}, recovered={len(recovered)})"
        )

        shutdown = asyncio.Event()
        loop = asyncio.get_running_loop()

        def request_shutdown(*_args) -> None:
            loop.call_soon_threadsafe(shutdown.set)

        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                signal.signal(sig, request_shutdown)
            except (ValueError, OSError):
                pass

        await shutdown.wait()
        print("Core engine stopping...")
        await scheduler.stop()
        return 0
    finally:
        if server is not None:
            server.stop()
        remove_discovery(run_dir / "engine.json", pid=os.getpid())
        store.close()
        lock.release()


def _print_payload(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if "checks" in payload:
        print(f"doctor: {'OK' if payload.get('ok') else 'ERROR'}")
        for check in payload["checks"]:
            print(
                f"  [{check['status'].upper():5}] {check['name']}: {check['message']}"
            )
        return
    if payload.get("running"):
        stats = payload.get("stats") or {}
        print(
            f"engine: running pid={payload.get('pid')} "
            f"port={payload.get('port')} protocol={payload.get('protocol_version')}"
        )
        print(
            "workers: "
            f"{stats.get('active_count', 0)}/{stats.get('max_concurrent', '?')} "
            f"active"
        )
        print("tasks:", json.dumps(stats.get("tasks", {}), ensure_ascii=False))
    else:
        print("engine: stopped")
        if payload.get("message"):
            print(payload["message"])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m engine")
    sub = parser.add_subparsers(dest="action", required=True)

    run = sub.add_parser("run", help="Run the Core engine in the foreground")
    run.add_argument("--run-dir", type=Path, default=settings.RUN_DIR)
    run.add_argument("--data-dir", type=Path, default=settings.DATA_DIR)
    run.add_argument("--port", type=int, default=DEFAULT_PORT)
    run.add_argument(
        "--max-concurrent", type=int, default=settings.TASK_MAX_CONCURRENT
    )
    run.add_argument(
        "--grace-seconds", type=float, default=settings.TASK_GRACE_SECONDS
    )

    for action in ("status", "doctor"):
        command = sub.add_parser(action)
        command.add_argument("--run-dir", type=Path, default=settings.RUN_DIR)
        command.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.action == "run":
        return asyncio.run(
            run_core(
                run_dir=args.run_dir,
                data_dir=args.data_dir,
                preferred_port=args.port,
                max_concurrent=args.max_concurrent,
                grace_seconds=args.grace_seconds,
            )
        )
    if args.action == "status":
        payload = status_report(args.run_dir)
        _print_payload(payload, args.json)
        return 0 if payload.get("running") else 1
    if args.action == "doctor":
        payload = doctor_report(args.run_dir)
        _print_payload(payload, args.json)
        return 0 if payload.get("ok") else 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
