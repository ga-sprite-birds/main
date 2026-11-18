# Utils Development Guide

> 中文版：[../zh/utils.md](../zh/utils.md) · Developer guide: [developer-guide.md](developer-guide.md) · Development setup: [development.md](development.md)

`utils/` is the project's collection of standalone developer tools. This guide defines how to
write and organize them.

---

## 1. Positioning

- A tool under `utils/` is an **independent auxiliary module**, not part of the Core engine or
  the Control API.
- It may reuse project modules, but must stay loosely coupled.
- Prefer the standard library and existing shared modules; do not reimplement what already exists.
- Each tool has one clear responsibility and a small, predictable CLI surface.

## 2. Principles

### 2.1 Read configuration, do not mutate it

Read deployment settings (paths, logging, FFmpeg, LLM credentials, concurrency) from
`system.config.settings`:

```python
from system.config import settings

log_file = settings.LOG_FILE
models_dir = settings.MODEL_CACHE_DIR
```

Read business settings (voice, rate, chapter rules, output strategy, etc.) through the `config`
facade, which resolves the effective ConfigService values:

```python
import config

output_path = config.OUTPUT_BASE_PATH
```

Never write back to config from a tool. Use the API/CLI/GUI for configuration changes.

### 2.2 Independence

Each tool should work on its own and must not import another `utils/` tool:

```text
utils/your_tool/
├── __init__.py
├── cli.py          # command-line entry point
├── analyzer.py     # core logic
├── generator.py    # optional second module
└── README.md       # tool-specific notes (if needed)
```

Existing examples: `utils/quick/` (startup scripts), `utils/retry_generator/`,
`utils/try_tts/`.

### 2.3 Keep the code lean

Prefer obvious code over comments that restate it. Add a short comment only when the *reason* for
a decision is non-obvious.

### 2.4 Clear errors

Fail loudly with an actionable message; do not swallow exceptions:

```python
if not source.exists():
    print(f"error: input file not found: {source}", file=sys.stderr)
    sys.exit(1)
```

## 3. Avoid

### 3.1 Hard-coded paths

```python
# ❌ bad: absolute path from one machine
log_file = "F:/web/ga-sprite-birds/logs/app.log"

# ✅ good: derive from project root
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
log_file = project_root / "logs" / "app.log"
```

### 3.2 Mutating shared config

```python
# ❌ bad: changes process-global state
import config
config.LOG_LEVEL = "DEBUG"

# ✅ good: read the effective value
from system.config import settings
log_level = settings.LOG_LEVEL
```

### 3.3 Duplicating existing functionality

```python
# ❌ bad: a private log parser when a shared helper exists
# ✅ good: reuse project modules or the standard library
```

## 4. Standard layout

```text
utils/your_tool/
├── __init__.py      # package init
├── cli.py           # command-line entry point
├── analyzer.py      # core module
├── generator.py     # optional module
└── README.md        # tool notes (optional; project docs live under help/)
```

Project-wide documentation belongs under `help/en/` and `help/zh/`; keep tool-local READMEs short.

## 5. Example: a small log analyzer

### `utils/log_analyzer/cli.py`

```python
#!/usr/bin/env python3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.log_analyzer.analyzer import LogAnalyzer


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python utils/log_analyzer/cli.py <log-file>", file=sys.stderr)
        return 1

    log_file = Path(sys.argv[1]).expanduser()
    if not log_file.exists():
        print(f"error: log file not found: {log_file}", file=sys.stderr)
        return 1

    failed = LogAnalyzer(log_file).analyze()
    print(f"failed chapters: {len(failed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

### `utils/log_analyzer/analyzer.py`

```python
import re
from pathlib import Path


class LogAnalyzer:
    ERROR_PATTERN = re.compile(r"ERROR.*TTS 生成失败")
    CHAPTER_PATTERN = re.compile(r"\[(\d+)/\d+\]")

    def __init__(self, log_file: Path):
        self.log_file = log_file

    def analyze(self) -> list[int]:
        lines = self.log_file.read_text(encoding="utf-8").splitlines()
        failed: set[int] = set()
        for index, line in enumerate(lines):
            if not self.ERROR_PATTERN.search(line):
                continue
            chapter = self._find_chapter(lines, index)
            if chapter is not None:
                failed.add(chapter)
        return sorted(failed)

    def _find_chapter(self, lines: list[str], error_index: int) -> int | None:
        start = max(0, error_index - 10)
        for cursor in range(error_index, start - 1, -1):
            match = self.CHAPTER_PATTERN.search(lines[cursor])
            if match:
                return int(match.group(1))
        return None
```

This is an illustrative example; `utils/log_analyzer/` is not shipped.

## 6. Checklist

1. Tool has a single, clear responsibility.
2. Deployment settings come from `system.config.settings`; business settings use the `config`
   facade.
3. No hard-coded machine paths; no config mutation.
4. Errors are explicit and exit with a non-zero status.
5. Reuse existing modules instead of copying logic.
6. Document project-wide behavior under `help/en/` + `help/zh/`; keep only tool-local notes in
   `utils/<tool>/README.md`.
