"""Path safety helpers for user-supplied filesystem paths.

The Control API accepts local paths for uploads/output and character templates.
Those paths must stay inside explicitly configured roots; this module is the
single place that enforces that rule.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from system.config import PROJECT_ROOT

# Keep filenames usable on Windows, macOS and Linux and prevent path traversal.
_ILLEGAL_FILENAME_CHARS = {"<", ">", ":", '"', "/", "\\", "|", "?", "*"}


class PathSafetyError(ValueError):
    """Raised when a path escapes its configured root."""


def resolve_path(value: str | Path, *, base: Path | None = None) -> Path:
    """Resolve a user path relative to ``base`` (default: project root)."""
    raw = Path(str(value)).expanduser()
    if not raw.is_absolute():
        raw = (base or PROJECT_ROOT) / raw
    return raw.resolve(strict=False)


def ensure_under(
    root: str | Path,
    value: str | Path,
    *,
    base: Path | None = None,
) -> Path:
    """Return the resolved path, or raise if it is outside ``root``."""
    root_path = resolve_path(root)
    target = resolve_path(value, base=base)
    try:
        target.relative_to(root_path)
    except ValueError as exc:
        raise PathSafetyError(
            f"Path is outside the allowed root: {target} (root: {root_path})"
        ) from exc
    return target


def ensure_under_any(
    roots: Iterable[str | Path],
    value: str | Path,
    *,
    base: Path | None = None,
) -> Path:
    """Return the first resolved path under any root; raise when none match."""
    errors: list[str] = []
    for root in roots:
        try:
            return ensure_under(root, value, base=base)
        except PathSafetyError as exc:
            errors.append(str(exc))
    raise PathSafetyError(
        "Path is outside every allowed root: "
        + "; ".join(errors or ["no roots configured"])
    )


def safe_filename(value: str) -> str:
    """Validate one path component (no separators, no traversal)."""
    name = str(value)
    if not name or name in {".", ".."}:
        raise PathSafetyError("Filename is empty or reserved")
    if "\0" in name or any(char in name for char in _ILLEGAL_FILENAME_CHARS):
        raise PathSafetyError(f"Filename contains illegal characters: {name!r}")
    return name


def validate_output_path(value: str | Path, output_root: str | Path) -> Path:
    """Validate a per-task output directory against the configured output root."""
    return ensure_under(output_root, value)


def validate_filename_template(template: str) -> None:
    """Reject templates that could escape the output directory."""
    if not template or "\0" in template:
        raise PathSafetyError("Filename template is empty")
    if any(char in template for char in ("/", "\\")):
        raise PathSafetyError("Filename template must not contain path separators")
    if ".." in template:
        raise PathSafetyError("Filename template must not contain '..'")
