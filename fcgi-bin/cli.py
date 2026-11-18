"""CLI client for the standalone Core engine.

The CLI never executes parsing, LLM, TTS, or merging itself. It submits
commands through the same localhost channel used by the HTTP API.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
import json
import time
from typing import Any

from services.config_service import ConfigValidationError
from services.control.client import (
    EngineCommandError,
    EngineUnavailable,
    EngineProtocolError,
)
from services.control.service import ControlService

TERMINAL = {"succeeded", "failed", "canceled", "removed"}
COMMANDS = {
    "add",
    "list",
    "get",
    "status",
    "pause",
    "resume",
    "cancel",
    "retry",
    "remove",
    "cancel-chapter",
    "events",
    "logs",
    "clean",
    "config",
    "system",
}


def _print(payload: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _task_line(task: dict[str, Any]) -> str:
    progress = task.get("progress", 0)
    return (
        f"{task.get('task_id')}  {task.get('status'):9} "
        f"{progress * 100:5.1f}%  {task.get('phase') or '-'}  "
        f"{task.get('error') or ''}".rstrip()
    )


def _wait_for_task(
    control: ControlService,
    task_id: str,
    *,
    follow: bool,
    as_json: bool,
) -> dict[str, Any]:
    task = control.status(task_id) or {"task_id": task_id, "status": "unknown"}
    if not follow:
        _print(task, as_json)
        return task
    last = None
    while True:
        task = control.status(task_id)
        if task is None:
            raise EngineCommandError(
                {"code": 3002, "msg": "Task not found", "data": {"task_id": task_id}}
            )
        signature = (
            task.get("status"),
            task.get("phase"),
            task.get("completed_chapters"),
            task.get("error"),
        )
        if signature != last and not as_json:
            print(_task_line(task), flush=True)
            last = signature
        if task.get("status") in TERMINAL:
            if as_json:
                _print(task, as_json)
            return task
        time.sleep(1.0)


def _wait_for_parse(
    control: ControlService,
    task_id: str,
    *,
    as_json: bool,
    timeout: float = 900.0,
) -> dict[str, Any]:
    """Poll until the background parse finishes (phase becomes ready)."""
    deadline = time.monotonic() + timeout
    last_phase = None
    while True:
        task = control.status(task_id)
        if task is None:
            raise EngineCommandError(
                {"code": 3002, "msg": "Task not found", "data": {"task_id": task_id}}
            )
        phase = task.get("phase")
        if phase == "ready":
            return task
        if phase == "parse_failed" or task.get("status") == "failed":
            raise EngineCommandError(
                {
                    "code": 3003,
                    "msg": task.get("error") or "Parse failed",
                    "data": {"task_id": task_id, "phase": phase},
                }
            )
        if time.monotonic() > deadline:
            raise EngineCommandError(
                {"code": 3003, "msg": "Parse timed out", "data": {"task_id": task_id}}
            )
        if phase != last_phase and not as_json:
            print(f"parsing... phase={phase}", flush=True)
            last_phase = phase
        time.sleep(0.5)


def _legacy_options(args: argparse.Namespace) -> dict[str, Any]:
    indexes = None
    if args.start or args.end:
        start = args.start or 1
        end = args.end
        if end is None:
            raise ValueError("--end is required when --start is used")
        indexes = list(range(start, end + 1))
    options: dict[str, Any] = {
        "voice": args.voice,
        "output_path": args.output,
        "enable_llm": False if args.no_llm else None,
        "rate": args.rate,
        "prosody_mode": args.prosody,
        "chapter_indexes": indexes,
        "multi_voice": bool(args.multi_voice),
        "character_template": args.character_template,
    }
    return {key: value for key, value in options.items() if value is not None}


def _add_and_run(args: argparse.Namespace, control: ControlService) -> dict[str, Any]:
    source = Path(args.input).expanduser()
    if not source.is_file():
        raise ValueError(f"Input file does not exist: {source}")
    base_command_id = getattr(args, "command_id", None)

    def command_id(step: str) -> str | None:
        return f"{base_command_id}:{step}" if base_command_id else None

    task = control.add_task(
        {
            "file_path": str(source.resolve()),
            "output_path": args.output,
            "filename": source.name,
            "source_name": source.name,
        },
        command_id=command_id("add"),
    )
    task_id = task["task_id"]
    if not args.json:
        print(f"created {task_id}")
    control.parse(task_id, command_id=command_id("parse"))
    subject = _wait_for_parse(control, task_id, as_json=args.json)
    if args.json:
        _print(subject, True)
    else:
        print(
            f"parsed {subject.get('total_chapters', 0)} chapter(s), status="
            f"{subject.get('status')} phase={subject.get('phase')}"
        )
    options = _legacy_options(args)
    control.generate(task_id, options, command_id=command_id("generate"))
    return _wait_for_task(
        control, task_id, follow=args.follow, as_json=args.json
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cli.py",
        description="GA Sprite Birds Core CLI (control client)",
        epilog=(
            "commands: "
            + ", ".join(sorted(COMMANDS))
            + "\nlegacy: cli.py -i input.txt [--voice ...] "
            "(add + parse + generate in one call)"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("command", nargs="?", choices=sorted(COMMANDS))
    parser.add_argument("target", nargs="?")
    parser.add_argument("--json", action="store_true", help="Raw JSON output")
    parser.add_argument("--follow", action="store_true", help="Follow progress")
    parser.add_argument("--command-id")
    return parser


def _common_add_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-i", "--input", required=True)
    parser.add_argument("-o", "--output", default=None)
    parser.add_argument("--voice")
    parser.add_argument("--rate", type=float)
    parser.add_argument("--prosody", choices=("off", "pause", "prosody"))
    parser.add_argument("--no-llm", action="store_true")
    parser.add_argument("--multi-voice", action="store_true")
    parser.add_argument("--character-template")
    parser.add_argument("--start", type=int, default=None)
    parser.add_argument("--end", type=int, default=None)
    parser.add_argument("--analyze-characters", action="store_true")


def _legacy_namespace(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="cli.py")
    _common_add_flags(parser)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--follow", action="store_true")
    parser.add_argument("--log-level", default=None)
    parser.add_argument("--language", default=None)
    parser.add_argument("--analysis-mode", default=None)
    parser.add_argument("--character-list", default=None)
    return parser.parse_intermixed_args(argv)


def _subcommand_parser(command: str, argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog=f"cli.py {command}")
    parser.add_argument("--json", action="store_true")
    if command == "add":
        _common_add_flags(parser)
        parser.add_argument("--follow", action="store_true")
    elif command in ("get", "status"):
        parser.add_argument("task_id")
    elif command == "list":
        parser.add_argument("--status", choices=(
            "pending", "queued", "running", "paused", "succeeded",
            "failed", "canceled", "removed",
        ))
        parser.add_argument("--type")
        parser.add_argument("--page", type=int, default=1)
        parser.add_argument("--page-size", type=int, default=20)
    elif command in ("pause", "resume", "cancel", "retry"):
        parser.add_argument("task_id")
    elif command == "remove":
        parser.add_argument("task_id")
        parser.add_argument("--delete-outputs", action="store_true")
    elif command == "cancel-chapter":
        parser.add_argument("task_id")
        parser.add_argument("chapter_index", type=int)
    elif command in ("events", "logs"):
        parser.add_argument("task_id")
        parser.add_argument("--after-id", type=int, default=0)
        parser.add_argument("--limit", type=int, default=100)
        parser.add_argument("--follow", action="store_true")
    elif command == "clean":
        parser.add_argument("--ttl-seconds", type=int)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--delete-outputs", action="store_true")
    elif command == "config":
        parser.add_argument("action", choices=("get", "set"))
        parser.add_argument("values", nargs="*")
    elif command == "system":
        parser.add_argument("action", choices=("info", "stats", "doctor", "status"))
    return parser.parse_args(argv)


def run(argv: list[str]) -> int:
    control = ControlService()
    try:
        if not argv or argv[0] in ("-h", "--help"):
            build_parser().print_help()
            return 0
        if argv[0] not in COMMANDS:
            if argv[0].startswith("-"):
                args = _legacy_namespace(argv)
                if args.analyze_characters:
                    print(
                        "Character analysis must be generated by a character-analysis "
                        "task; the legacy inline path was removed in v2.",
                        file=sys.stderr,
                    )
                    return 2
                _add_and_run(args, control)
                return 0
        command = argv[0]
        args = _subcommand_parser(command, argv[1:])

        if command == "add":
            if args.analyze_characters:
                print(
                    "Character analysis is not available through the default add flow.",
                    file=sys.stderr,
                )
                return 2
            _add_and_run(args, control)
        elif command in ("get", "status"):
            task = control.status(args.task_id)
            if task is None:
                print(f"Task not found: {args.task_id}", file=sys.stderr)
                return 1
            _print(task, args.json)
        elif command == "list":
            _print(
                control.list_tasks(
                    status=args.status,
                    task_type=args.type,
                    page=args.page,
                    page_size=args.page_size,
                ),
                args.json,
            )
        elif command == "pause":
            _print(control.pause(args.task_id), args.json)
        elif command == "resume":
            _print(control.resume(args.task_id), args.json)
        elif command == "cancel":
            _print(control.cancel(args.task_id), args.json)
        elif command == "retry":
            _print(control.retry(args.task_id), args.json)
        elif command == "remove":
            _print(
                control.remove(
                    args.task_id, delete_outputs=args.delete_outputs
                ),
                args.json,
            )
        elif command == "cancel-chapter":
            _print(
                control.remove_chapter(args.task_id, args.chapter_index),
                args.json,
            )
        elif command in ("events", "logs"):
            after_id = args.after_id
            while True:
                events = control.events(
                    args.task_id, after_id=after_id, limit=args.limit
                )
                _print({"events": events}, args.json)
                if not args.follow or not events:
                    break
                after_id = max(event["event_id"] for event in events)
                time.sleep(1.0)
        elif command == "clean":
            _print(
                control.cleanup(
                    ttl_seconds=args.ttl_seconds,
                    dry_run=args.dry_run,
                    delete_outputs=args.delete_outputs,
                ),
                args.json,
            )
        elif command == "config":
            if args.action == "get":
                payload = {"key": args.values[0]} if args.values else {}
                _print(
                    control.client.command("config.get", payload),
                    args.json,
                )
            else:
                if len(args.values) != 2:
                    print("usage: cli.py config set KEY value", file=sys.stderr)
                    return 1
                key, raw = args.values
                try:
                    value = json.loads(raw)
                except json.JSONDecodeError:
                    value = raw
                _print(
                    control.client.command("config.set", {"values": {key: value}}),
                    args.json,
                )
        elif command == "system":
            if args.action == "doctor":
                from engine.ops import doctor_report

                _print(doctor_report(), args.json)
            elif args.action == "status":
                from engine.ops import status_report

                _print(status_report(), args.json)
            elif args.action == "info":
                _print(control.client.info(), args.json)
            else:
                _print(control.client.stats(), args.json)
        return 0
    except EngineUnavailable as exc:
        print(f"engine unavailable: {exc}", file=sys.stderr)
        return 2
    except EngineProtocolError as exc:
        print(f"engine protocol error: {exc}", file=sys.stderr)
        return 2
    except EngineCommandError as exc:
        print(
            json.dumps(
                {"code": exc.code, "msg": str(exc), "data": exc.data},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1
    except (ValueError, ConfigValidationError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


def main() -> int:
    return run(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
