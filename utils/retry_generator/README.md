# Retry Generator — Failed-Chapter Retry Tool

Analyzes TTS generation logs, detects failed chapters, and generates retry commands. Three output
modes are supported:

1. **Shell script** — an executable bash script
2. **Plain text** — a command list
3. **Direct execution** — run the retries immediately (asks for confirmation)

## Quick start

### Basic usage

```bash
# Generate a shell script (recommended)
python utils/retry_generator/cli.py logs/app.log sh output/retry.sh

# Generate plain text
python utils/retry_generator/cli.py logs/app.log txt output/retry.txt

# Execute retries directly (dangerous: asks for confirmation)
python utils/retry_generator/cli.py logs/app.log exec
```

### Advanced usage

```bash
# Custom batch size (10 chapters per batch)
python utils/retry_generator/cli.py logs/app.log sh output/retry.sh --batch-size 10

# Specify the source file
python utils/retry_generator/cli.py logs/app.log sh output/retry.sh --input books/novel.pdf

# Only include network errors
python utils/retry_generator/cli.py logs/app.log sh output/retry.sh --filter network
```

## Parameters

### Required

| Parameter | Description | Example |
|---|---|---|
| `log_file` | Path to the log file | `logs/app.log` |
| `output_type` | Output type | `sh` / `txt` / `exec` |
| `output_path` | Output file path | `output/retry.sh` |

> `output_path` may be omitted in `exec` mode.

### Optional

| Parameter | Description | Default |
|---|---|---|
| `--batch-size` | Chapters per batch | `20` |
| `--input` | Source input file | `debug/ga.pdf` |
| `--filter` | Error-type filter | `all` |

#### Error-type filters

- `all` — all errors (default)
- `network` — network/connection errors only
- `timeout` — timeout errors only

## Output examples

### Shell script (`sh`)

The generated script includes:

- automatic error detection
- per-batch confirmation
- a prompt to continue after a failed batch

```bash
#!/bin/bash
# Auto-generated retry script
# Generated at: 2025-11-11 16:00:00
# Failed chapters: 133
# Batches: 7

echo 'Starting failed-chapter retries...'

# Batch 1: chapters 67-86 (20 chapters)
echo 'Running batch 1/7...'
python fcgi-bin/cli.py -i debug/ga.pdf --start 67 --end 86
if [ $? -ne 0 ]; then
    echo 'Batch 1 failed. Continue? (y/n)'
    read -r response
    if [ "$response" != "y" ]; then exit 1; fi
fi
```

### Plain text (`txt`)

Produces a concise command list:

```text
Failed-chapter retry commands
Generated at: 2025-11-11 16:00:00
Failed chapters: 133
Batches: 7

============================================================

Batch 1: chapters 67-86 (20 chapters)
python fcgi-bin/cli.py -i debug/ga.pdf --start 67 --end 86

Batch 2: chapters 87-106 (20 chapters)
python fcgi-bin/cli.py -i debug/ga.pdf --start 87 --end 106
```

### Direct execution (`exec`)

Interactive flow:

```text
============================================================
WARNING: direct execution mode
============================================================

About to run:
   - Batches: 7
   - Input: debug/ga.pdf

Batch list:
   1. chapters 67-86 (20 chapters)
   2. chapters 87-106 (20 chapters)
   ...

Warning: retries will run immediately and cannot be undone.
Continue? (yes/no):
```

## How it works

### 1. Log analysis

Scans the log for error lines matching:

- `Cannot connect to host` — connection failure
- `getaddrinfo failed` — DNS failure
- `timeout` / `timed out` — timeout
- `TTS 生成失败` / `✗ 生成失败` — TTS engine failure

> The Chinese strings above are **literal log patterns emitted by the engine**, not untranslated
> documentation text. Keep them exactly as shown when grepping logs.

### 2. Chapter extraction

Looks backward from each error line for chapter information:

- pattern `[67/458]` → chapter 67
- results are deduplicated and sorted

### 3. Batch grouping

- contiguous chapters are merged into one batch
- a batch contains at most `--batch-size` chapters
- chapters separated by a gap of 3 or less are merged as well

### 4. Command generation

Depending on `output_type`:

- Shell script: error handling + interactive confirmation
- Plain text: concise command list
- Direct execution: runs commands and prints progress

## File structure

```text
utils/retry_generator/
├── cli.py              # command-line entry point
├── analyzer.py         # log analyzer
├── generator.py        # command generator
├── executor.py         # direct executor
└── README.md
```

## Use cases

### 1. Network instability caused many failures

```bash
# 1. Analyze the log and generate a retry script
python utils/retry_generator/cli.py logs/app.log sh retry.sh

# 2. Review the script
cat retry.sh

# 3. Run the retries
bash retry.sh
```

### 2. Inspect failed chapters quickly

```bash
python utils/retry_generator/cli.py logs/app.log txt failed_list.txt
cat failed_list.txt
```

### 3. Retry immediately (small failure sets)

```bash
python utils/retry_generator/cli.py logs/app.log exec
```

## Caveats

1. **`exec` mode is immediate and irreversible.**
   - Prefer `sh` or `txt` first.
   - It asks for confirmation before running.
2. **Batch size guidance**
   - stable network: 20–30 chapters per batch
   - unstable network: 5–10 chapters per batch
   - many failures: split into several runs
3. **Log requirements**
   - must contain chapter markers such as `[N/Total]`
   - must contain the error messages listed above
   - use the most recent log file

## Troubleshooting

### No failed chapters detected

**Cause:** the log format does not match.

```bash
# Check for errors and chapter markers
grep "失败" logs/app.log
grep "\[.*/.*\]" logs/app.log
```

### Too many batches

**Cause:** the batch size is too small.

```bash
python utils/retry_generator/cli.py logs/app.log sh retry.sh --batch-size 50
```

### `exec` mode fails

**Cause:** the working directory is wrong.

```bash
cd /path/to/ga-sprite-birds
python utils/retry_generator/cli.py logs/app.log exec
```

## Related documentation

- [Project usage guide](../../help/en/README.md)
- [CLI/API reference](../../help/en/api.md)
- [CLI source](../../fcgi-bin/cli.py)
- [Development setup](../../help/en/development.md)
