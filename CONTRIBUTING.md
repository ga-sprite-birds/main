# Contributing to GA Sprite Birds

Thank you for your interest in `GA Sprite Birds`. This document explains how to file issues, contribute code, and the licensing rules that apply when contributions are merged.

## Project Info

- Author: `adam`
- Email: `dev@ebf.hk`
- Website: <http://ebf.cc>
- GitHub Source: <https://github.com/tiger-sprite/ga-sprite-birds>

## 1. How to Contribute

We welcome the following types of contributions:

- Bug reports with reproduction steps
- Documentation fixes and sample additions
- Unit test and integration test improvements
- CLI / API / core module bug fixes
- New platform integration, self-hosting experience improvements, and developer experience enhancements

If you are planning a large change, please open an issue first to describe the goal, scope, and design approach to avoid conflicts with project direction.

## 2. Before You Start

It is recommended to read the following documents first:

- `README.md`
- `help/INSTALL.md`
- `help/development-guide.md`
- `tests/README.md`

This project is currently Python-based and includes:

- CLI entry point: `fcgi-bin/cli.py`
- API entry point: `fcgi-bin/api.py`
- Core modules: `ga_birds/`
- Tests: `tests/`

## 3. Development Environment

Python `3.10+` is recommended.

Basic setup:

```bash
python -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

If you use Conda or another environment manager, you can also follow the instructions in `help/INSTALL.md`.

## 4. Development Principles

When submitting changes, please follow these guidelines:

- Keep changes focused; do not mix unrelated issues in the same PR
- Prefer fixing the root cause over surface-level patches
- Reuse existing module boundaries; do not arbitrarily break directory layering
- Add tests for new features or fixes that carry regression risk
- Do not commit keys, tokens, credentials, real sensitive text, or any other secrets
- Avoid unnecessary large-scale formatting to reduce review noise

## 5. Code Style

Please keep your code consistent with the existing style:

- Python files use lowercase with underscores
- Class names use PascalCase
- Function names use lowercase with underscores
- API parameters keep underscore style
- CLI long parameters keep hyphen style
- For import order, module boundaries, and naming conventions, refer to `help/development-guide.md`

If you introduce non-obvious business logic, please add concise comments explaining *why* it is done that way.

## 6. Testing Requirements

Before submitting, please at least run the tests relevant to your changes.

Common commands:

```bash
# Unit tests
pytest tests/unit -v

# Run a specific test file
pytest tests/unit/test_upload.py -v

# Integration tests (requires API to be running first)
pytest tests/integration -v
```

If your changes affect any of the following, be especially careful to verify:

- Upload, parsing, generation, and other API flows
- CLI parameter compatibility
- Multilingual text
- File paths, output directories, and caching behavior
- LLM / TTS related fallback logic

## 7. Multi-Language Multi-Role TTS Voice Assignment

When the text contains multiple characters (speakers), the system automatically assigns distinct voices to each one. The resolution order is as follows.

### 7.1 Single-Role Mode

If only a single narrator or character is present, `TTS_VOICE` from the `.env` configuration is used throughout.

### 7.2 Multi-Role Mode

`TTS_VOICE` serves as the **ultimate fallback** only. The resolution chain is:

1. **Per-language voice preference** (`voice_preferences.by_language`)
   - Each character can define language-specific voices. If the current segment's language matches an entry (e.g. `zh`, `en`), that voice is used.

2. **Character profile & region hint**
   - If a character profile contains a `region_hint` (e.g. "british", "american", "cantonese"), the system refines the locale selection accordingly.
   - Voices are then drawn from the auto-built voice pool for that locale, gender-matched and cycled to distribute distinct voices across characters.

3. **Fallback to `TTS_VOICE`**
   - If none of the above rules match, a warning is logged and `TTS_VOICE` from the `.env` file is used as the fallback.

### 7.3 Locale Preferences

The system maps content languages to preferred locales in order of priority:

| Language | Preferred Locales |
|----------|------------------|
| `en`     | en-US, en-GB, en-AU, en-CA, en-IN |
| `zh`     | zh-CN, zh-TW, zh-HK |
| `ja`     | ja-JP |
| `de`     | de-DE, de-AT, de-CH |
| `fr`     | fr-FR, fr-CA, fr-CH |
| `es`     | es-ES, es-MX, es-US |
| `pt`     | pt-BR, pt-PT |
| `ru`     | ru-RU |
| `ko`     | ko-KR |
| `it`     | it-IT |

### 7.4 Region Hints

Region keywords in character profiles refine locale selection:

| Keyword(s)       | Locale  |
|------------------|---------|
| british, uk, england  | en-GB |
| american, usa, us     | en-US |
| canada                | en-CA |
| australia             | en-AU |
| india                 | en-IN |
| china, mandarin       | zh-CN |
| taiwan                | zh-TW |
| hong kong, cantonese  | zh-HK |
| japan, tokyo          | ja-JP |
| brazil                | pt-BR |
| portugal              | pt-PT |
| mexico                | es-MX |
| spain                 | es-ES |
| france                | fr-FR |
| germany               | de-DE |
| italy                 | it-IT |
| korea                 | ko-KR |

### 7.5 Voice Pool Auto-Building

When voice assignment falls through to the auto-pool path, the system:

1. Builds a voice catalog by querying the TTS engine (e.g. edge-tts) for available voices in the resolved locale.
2. Separates voices into `male` / `female` pools based on the TTS engine's gender metadata.
3. Selects a voice from the appropriate gender pool using round-robin rotation, ensuring different characters of the same gender get distinct voices when possible.

### 7.6 Character Template Format (Reference)

The character voice template used internally follows this structure:

```json
{
  "novel_id": "...",
  "novel_title": "...",
  "narrator": {
    "voice": "zh-CN-XiaoxiaoNeural",
    "voice_preferences": {
      "default": "zh-CN-XiaoxiaoNeural",
      "by_language": {
        "en": "en-US-JennyNeural",
        "ja": "ja-JP-NanamiNeural"
      }
    },
    "profile": {
      "personality": ["objective", "calm"]
    }
  },
  "characters": [
    {
      "name": "Alice",
      "gender": "female",
      "voice_preferences": {
        "by_language": {
          "en": "en-US-AriaNeural",
          "zh": "zh-CN-XiaoxiaoNeural"
        }
      },
      "profile": {
        "region_hint": "british",
        "personality": ["gentle", "kind"]
      }
    }
  ]
}
```

### 7.7 Key Environment Variables

| Variable | Description |
|----------|-------------|
| `TTS_VOICE` | Default / fallback voice (e.g. `zh-CN-YunxiNeural`) |
| `TTS_ENGINE` | TTS engine to use (currently `edge`) |
| `TTS_VOICE_CATALOG_CACHE` | Path to cached TTS voice catalog |

## 8. Pull Request Guidelines

PR descriptions should ideally include:

- Background of the change
- What was changed
- Why it was changed
- How it was tested
- Whether there are compatibility impacts

Small, focused PRs are preferred — they significantly reduce review cost.

## 9. Issue Reporting Guidelines

When filing an issue, please provide as much of the following as possible:

- Runtime environment (OS, Python version)
- Startup method (CLI / API)
- Input type (txt / pdf)
- Error logs or stack traces
- Minimal reproduction steps
- Expected vs. actual results

If the issue involves third-party services, please also specify:

- Whether using local LLM or API mode
- Which TTS engine is being used
- Whether there is a special network environment

## 10. Contribution Licensing

This project is open-sourced under the `Apache License 2.0`.

Unless you explicitly state otherwise and have a prior written agreement with the maintainer, any contribution you intentionally submit to this project with the intent of being included in the codebase will be licensed and distributed under `Apache-2.0` by default.

By submitting a contribution, you confirm:

- You have the right to submit the contribution
- The contribution does not infringe any third-party rights to your knowledge
- You agree that the contribution will be released under the `Apache-2.0` license as part of this project

If you are submitting code on behalf of a company or organization, please confirm that you have the proper authorization.

## 11. Future License Adjustments

The project maintainer may adjust release strategies, repository structure, commercialization approaches, or licensing arrangements for subsidiary projects in the future.

However, unless otherwise specified in a separate written agreement, code versions lawfully released under `Apache-2.0` will not have their existing license retroactively revoked.

If the project introduces a separate Contributor License Agreement (CLA) or Developer Certificate of Origin (DCO) in the future, it will be clearly documented in the repository.

## 12. Code of Conduct

Please maintain professional, respectful, and constructive communication. When discussing issues, design disagreements, and code reviews, focus on facts, reproduction, impact, and improvement plans.

---

**Author**: `adam`  
**Email**: `dev@ebf.hk`  
**Website**: <http://ebf.cc>  
**GitHub Source**: <https://github.com/tiger-sprite/ga-sprite-birds>  
**Last updated**: 2026-07-10

---

Thank you for your contribution.
