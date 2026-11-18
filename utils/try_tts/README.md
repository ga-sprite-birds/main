# Edge TTS Voice Audition Tool

Fetches every voice supported by Microsoft Edge TTS and generates audition audio files.

To listen to the official voices in a browser first, you can also visit:
<https://edge-tts.com>

## Features

- List all available voices
- Filter by language (e.g. `zh-CN`, `en-US`) and gender
- Generate a sample for one voice or batch-generate many
- Save results as both JSON and Markdown
- Automatic retry for transient synthesis failures
- Unique filenames on collisions (Windows-style: `file.mp3` → `file (1).mp3`)
- Export the voice catalog as a Markdown document
- English/Chinese console output via `--language` or the system `LANGUAGE` setting

## Quick start

### 1. List voices

```bash
# All voices
python utils/try_tts/cli.py list

# Chinese voices
python utils/try_tts/cli.py list --lang zh-CN

# Chinese male voices
python utils/try_tts/cli.py list --lang zh-CN --gender male

# Chinese female voices
python utils/try_tts/cli.py list --lang zh-CN --gender female
```

### 2. Generate audition audio

```bash
# One voice
python utils/try_tts/cli.py generate --voice zh-CN-XiaoxiaoNeural

# All Chinese voices
python utils/try_tts/cli.py generate --lang zh-CN

# All English voices (uses the built-in English sample text)
python utils/try_tts/cli.py generate --lang en-US

# Chinese male voices
python utils/try_tts/cli.py generate --lang zh-CN --gender male

# Custom sample text
python utils/try_tts/cli.py generate --voice zh-CN-XiaoxiaoNeural --text "This is a custom sample."

# Custom output directory
python utils/try_tts/cli.py generate --lang zh-CN --output ./my_samples
```

### 3. Export the voice catalog

```bash
# All voices as Markdown
python utils/try_tts/cli.py list --save-doc voices.md

# Chinese voices only
python utils/try_tts/cli.py list --lang zh-CN --save-doc zh-CN-voices.md
```

## Console language

The tool has its own English/Chinese console strings. The precedence is:

1. local translation files in `utils/try_tts/langues/`
2. project i18n (`ga_birds/Langues/*.json`)
3. hardcoded fallback strings

The default language comes from the system `LANGUAGE` business setting (a fresh install uses
`zh_CN`). Override it per invocation with `--language`.

```bash
# English console output
python utils/try_tts/cli.py list --language en_US

# Chinese console output
python utils/try_tts/cli.py list --language zh_CN
```

To change the default for the whole project, edit `LANGUAGE` in **System config** (GUI) or run:

```bash
python fcgi-bin/cli.py config set LANGUAGE en_US
```

> `LANGUAGE` is a business setting stored in `data/system.db` + `cache/config/system.json`; it is
> **not** read from `.env` in v2.

### Parameter distinctions

- `--lang` filters the **voice language** (e.g. `zh-CN`, `en-US`).
- `--language` sets the **console language** (`en_US`, `zh_CN`).
- `--text` is optional: `zh-*` voices use a built-in Chinese sample, `en-*` voices use a built-in
  English sample. Other languages require an explicit `--text`.

## Command-line reference

### Actions

- `list` — list voices
- `generate` — generate audition audio

### Filtering

- `--lang <locale>` — voice locale (e.g. `zh-CN`, `en-US`, `ja-JP`)
- `--gender <gender>` — `male`/`1` or `female`/`0`

### Generation

- `--voice <ShortName>` — one voice (e.g. `zh-CN-XiaoxiaoNeural`)
- `--text <text>` — custom sample text
- `--output <dir>` — output directory (default `./output/tts_samples`)

### Export

- `--save-doc <file>` — save the voice list as Markdown

### Console language

- `--language <en_US|zh_CN>` — console output language

## Output files

### Audition audio

Each sample is named after the voice: `{voice}.mp3`.

```text
output/tts_samples/
├── voices.json                      # generation result (JSON)
├── voices.md                        # generation result (Markdown)
├── zh-CN-XiaoxiaoNeural.mp3
├── zh-CN-YunxiNeural.mp3
├── zh-CN-XiaoyiNeural.mp3
└── ...
```

### `voices.json`

```json
{
  "code": 1,
  "msg": "All generated successfully",
  "data": {
    "generated_at": "2025-12-01 14:30:00",
    "filter": {
      "language": "zh-CN",
      "gender": "All"
    },
    "output_dir": "./output/tts_samples",
    "total": 38,
    "success": 34,
    "failed": 4,
    "voices": [
      {
        "name": "zh-CN-XiaoxiaoNeural",
        "gender": "Female",
        "language": "zh-CN",
        "friendly_name": "Microsoft Xiaoxiao Online (Natural) - Chinese (Mainland)",
        "audio_file": "output/tts_samples/zh-CN-XiaoxiaoNeural.mp3",
        "status": "success"
      },
      {
        "name": "zh-CN-XiaoshuangMultilingualNeural",
        "gender": "Female",
        "language": "zh-CN",
        "friendly_name": "Microsoft Xiaoshuang Multilingual Online (Natural)",
        "audio_file": null,
        "status": "failed",
        "error": "No audio was received. Please verify that your parameters are correct."
      }
    ]
  }
}
```

| Field | Type | Description |
|---|---|---|
| `code` | int | `1` all succeeded, `2` partial success, `0` all failed |
| `msg` | string | Status message |
| `data.generated_at` | string | Generation time |
| `data.filter.language` | string | Language filter |
| `data.filter.gender` | string | Gender filter |
| `data.output_dir` | string | Output directory |
| `data.total` | int | Total voices |
| `data.success` | int | Succeeded count |
| `data.failed` | int | Failed count |
| `data.voices[].name` | string | Voice ShortName |
| `data.voices[].gender` | string | Gender |
| `data.voices[].language` | string | Locale |
| `data.voices[].friendly_name` | string | Friendly name |
| `data.voices[].audio_file` | string/null | Audio path (null on failure) |
| `data.voices[].status` | string | `success` / `failed` |
| `data.voices[].error` | string | Error detail (failed entries only) |

### `voices.md`

Contains:

- generation time, filters and statistics
- a result table (status, voice, gender, language, audio file)
- failure details when applicable

## Recommended voices

### Chinese

| Voice | Gender | Character |
|---|---|---|
| `zh-CN-XiaoxiaoNeural` | Female | gentle, natural |
| `zh-CN-YunxiNeural` | Male | calm, clear |
| `zh-CN-XiaoyiNeural` | Female | lively, young |
| `zh-CN-YunjianNeural` | Male | mature, rich |

### English

| Voice | Gender | Character |
|---|---|---|
| `en-US-JennyNeural` | Female | standard US English |
| `en-US-GuyNeural` | Male | standard US English |
| `en-GB-SoniaNeural` | Female | standard British English |
| `en-GB-RyanNeural` | Male | standard British English |

## Tips

1. **Audition Chinese voices quickly**
   ```bash
   python utils/try_tts/cli.py generate --lang zh-CN
   # writes voices.json and voices.md automatically
   ```
2. **Male voices only**
   ```bash
   python utils/try_tts/cli.py generate --lang zh-CN --gender male
   ```
3. **Export the full catalog**
   ```bash
   python utils/try_tts/cli.py list --save-doc all-voices.md
   ```
4. **Test a specific voice**
   ```bash
   python utils/try_tts/cli.py generate --voice zh-CN-XiaoxiaoNeural --text "A sample for this voice."
   ```
5. **Use the Chinese console**
   ```bash
   python utils/try_tts/cli.py list --lang zh-CN --language zh_CN
   # or set LANGUAGE in System config
   ```
6. **Inspect results**
   ```bash
   cat output/tts_samples/voices.json
   cat output/tts_samples/voices.md
   ```

## Development notes

```text
utils/try_tts/
├── __init__.py
├── cli.py               # command-line entry point
├── voice_fetcher.py     # voice catalog fetcher
├── sample_generator.py  # audition audio generator
├── doc_exporter.py      # Markdown exporter
├── i18n.py              # console i18n
├── langues/
│   ├── en_US.json
│   └── zh_CN.json
└── README.md
```

Core modules:

- **VoiceFetcher** — fetches and filters the Edge TTS voice catalog
- **SampleGenerator** — generates audition audio
- **DocExporter** — exports the catalog as Markdown
- **UtilsI18n** — console translations with local/project/hardcoded fallback

## Automatic retry

Synthesis uses Tenacity:

- **Attempts:** up to 3
- **Backoff:** exponential, about 1s then 2s (capped at 10s)
- **Applies to:** network timeouts, connection failures and transient errors

After the final failure the voice is marked `failed` in `voices.json` / `voices.md`, and batch
generation continues with the next voice.

## Notes

1. Network access is required to fetch voices and synthesize audio.
2. Batch generation is sequential; expect it to take a while.
3. Samples are MP3.
4. The default sample text is Chinese; pass `--text` to customize.
5. Filename collisions are handled automatically (`file.mp3` → `file (1).mp3`).
6. Every batch run writes `voices.json` and `voices.md`.

## FAQ

**How do I see all supported languages?**
Run `python utils/try_tts/cli.py list` and check the Locale column.

**What if generation fails?**
The tool retries up to 3 times. If it still fails, the reason is recorded in `voices.json` and
`voices.md`; check the network and access to the Microsoft Edge TTS service.

**How do I change the console language?**
Use `--language en_US` / `--language zh_CN`, or change the system `LANGUAGE` setting (GUI System
config or `python fcgi-bin/cli.py config set LANGUAGE ...`).

**How do I use these voices in the project?**
Set `TTS_VOICE` in the GUI **System config** (or `python fcgi-bin/cli.py config set TTS_VOICE ...`),
or pass `--voice` to the main CLI. `TTS_VOICE` is not read from `.env` in v2.

**Can `voices.json` be used by the API?**
It follows the `{code, msg, data}` envelope and is convenient for tooling, but it is a local file,
not an HTTP endpoint.
