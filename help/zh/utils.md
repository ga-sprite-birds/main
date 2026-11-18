# Utils 开发规范

> English version：[../en/utils.md](../en/utils.md) · 开发者指南：[developer-guide.md](developer-guide.md) · 开发文档：[development.md](development.md)

`utils/` 是项目的独立开发者工具集合。本文档约定这些工具如何编写与组织。

---

## 1. 定位

- `utils/` 下的工具是**独立的辅助模块**，不属于 Core 引擎或 Control API。
- 可以复用项目模块，但必须保持松耦合。
- 优先使用标准库与已有公共模块，不要重复造轮子。
- 每个工具职责单一，CLI 参数少而明确。

## 2. 原则

### 2.1 读取配置，不要修改配置

部署级配置（路径、日志、FFmpeg、LLM 凭据、并发等）从 `system.config.settings` 读取：

```python
from system.config import settings

log_file = settings.LOG_FILE
models_dir = settings.MODEL_CACHE_DIR
```

业务配置（音色、语速、章节规则、输出策略等）通过 `config` 门面读取，
它会解析 ConfigService 的生效值：

```python
import config

output_path = config.OUTPUT_BASE_PATH
```

工具里**不要写回配置**；修改配置请走 API/CLI/GUI。

### 2.2 独立性

每个工具应能独立运行，不得 import 另一个 `utils/` 工具：

```text
utils/your_tool/
├── __init__.py
├── cli.py          # 命令行入口
├── analyzer.py     # 核心逻辑
├── generator.py    # 可选的第二个模块
└── README.md       # 工具自身的简短说明（可选）
```

已有示例：`utils/quick/`（启动脚本）、`utils/retry_generator/`、`utils/try_tts/`。

### 2.3 代码精简

优先写直观的代码，不要用注释复述代码。只有在**决策原因**不明显时才加简短注释。

### 2.4 错误清晰

失败时给出可操作的错误信息，不要吞异常：

```python
if not source.exists():
    print(f"error: input file not found: {source}", file=sys.stderr)
    sys.exit(1)
```

## 3. 避免

### 3.1 硬编码路径

```python
# ❌ 错误：写死某台机器的绝对路径
log_file = "F:/web/ga-sprite-birds/logs/app.log"

# ✅ 正确：从项目根推导
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
log_file = project_root / "logs" / "app.log"
```

### 3.2 修改共享配置

```python
# ❌ 错误：修改进程全局状态
import config
config.LOG_LEVEL = "DEBUG"

# ✅ 正确：读取生效值
from system.config import settings
log_level = settings.LOG_LEVEL
```

### 3.3 重复实现已有功能

```python
# ❌ 错误：已有公共实现时，自己再写一份日志解析
# ✅ 正确：复用项目模块或标准库
```

## 4. 标准目录结构

```text
utils/your_tool/
├── __init__.py      # 包初始化
├── cli.py           # 命令行入口
├── analyzer.py      # 核心模块
├── generator.py     # 可选模块
└── README.md        # 工具说明（可选；项目级文档放 help/）
```

项目级文档统一放 `help/en/` 与 `help/zh/`；工具目录里的 README 保持简短即可。

## 5. 示例：一个小型日志分析工具

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

这是示例，仓库中并没有 `utils/log_analyzer/` 这个工具。

## 6. 检查单

1. 工具职责单一、目标明确。
2. 部署项来自 `system.config.settings`；业务项走 `config` 门面。
3. 没有硬编码机器路径；没有修改配置。
4. 错误信息明确，失败时返回非零状态码。
5. 复用已有模块，不复制逻辑。
6. 项目级说明写在 `help/en/` + `help/zh/`；`utils/<tool>/README.md` 只保留工具自身说明。
