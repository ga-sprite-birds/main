"""Entry point: python -m server run.

Only starts the Control API process. The Core engine is separate
(``python -m engine run``); start it separately or use ``utils/quick``.
"""

from __future__ import annotations

import argparse
import importlib.util
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from system.config import settings  # noqa: E402

API_APP_FILE = ROOT / "fcgi-bin" / "api.py"


def load_app():
    """Load the FastAPI app from fcgi-bin/api.py by path.

    ``fcgi-bin`` contains a hyphen, so it cannot be imported as a normal
    package; load the module file explicitly instead.
    """
    spec = importlib.util.spec_from_file_location("ga_control_api", API_APP_FILE)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Cannot load the API app from {API_APP_FILE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.app


def port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def resolve_port(host: str, port: int, auto: bool) -> int:
    if port_available(host, port):
        return port
    if not auto:
        raise SystemExit(
            f"Port {port} is already in use ({host}). "
            "Pass --port <port>, or stop the process using it."
        )
    for candidate in range(port + 1, min(port + 101, 65536)):
        if port_available(host, candidate):
            print(
                f"Warning: port {port} is already in use ({host}); "
                f"using {candidate} instead.",
                file=sys.stderr,
                flush=True,
            )
            return candidate
    raise SystemExit(f"No free port between {port} and {port + 100}.")


def run(args: argparse.Namespace) -> int:
    port = resolve_port(args.host, args.port, not args.strict_port)
    display_host = "127.0.0.1" if args.host in ("0.0.0.0", "::") else args.host
    print(f"GA Sprite Birds Control API -> http://{display_host}:{port}/", flush=True)

    import uvicorn

    from system.logging_setup import configure_logging

    configure_logging("api")
    uvicorn.run(
        load_app(),
        host=args.host,
        port=port,
        log_level=settings.LOG_LEVEL.lower(),
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m server")
    sub = parser.add_subparsers(dest="action", required=True)

    run_parser = sub.add_parser("run", help="Run the Control API (HTTP server)")
    run_parser.add_argument("--host", default=settings.API_HOST)
    run_parser.add_argument("--port", type=int, default=settings.API_PORT)
    run_parser.add_argument(
        "--strict-port",
        action="store_true",
        help=(
            "Fail if the requested port is occupied instead of auto-shifting "
            "(default: shift to the next free port and print a warning)"
        ),
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.action == "run":
        return run(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
