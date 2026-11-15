"""Sync GUI config i18n modules from the backend language files.

The backend returns i18n keys (`config.section.*` / `config.item.*`) in the
`GET /system-config` payload, so the GUI needs the matching translations. The
backend `ga_birds/Langues/*.json` files stay the single source of truth; this
script regenerates the GUI modules from them.

Usage:
    python scripts/sync_config_i18n.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

PAIRS = {
    "zh_CN": PROJECT_ROOT / "ga_birds" / "Langues" / "zh_CN.json",
    "en_US": PROJECT_ROOT / "ga_birds" / "Langues" / "en_US.json",
}

OUTPUT_DIR = PROJECT_ROOT / "gui" / "src" / "i18n" / "lang"

TEMPLATE = """/**
 * 配置项 i18n（{locale}）。
 *
 * 单一事实来源：{source} 中的 config 块。
 * 修改配置项文案时请先改后端 Langues 文件，再执行同步脚本覆盖本文件：
 *   python scripts/sync_config_i18n.py
 */
export default {{
    config: {body},
}};
"""


def render(locale: str, source: Path) -> str:
    payload = json.loads(source.read_text(encoding="utf-8"))
    block = payload.get("config")
    if not isinstance(block, dict):
        raise SystemExit(f"{source} 缺少 config 块")
    body = json.dumps(block, ensure_ascii=False, indent=4).replace("\n", "\n    ")
    # JSON 会强制给 key 加引号；标识符形式的 key 去掉引号，保持 JS 风格一致。
    body = re.sub(r'^(\s*)"([A-Za-z_$][\w$]*)":', r"\1\2:", body, flags=re.MULTILINE)
    relative = source.relative_to(PROJECT_ROOT).as_posix()
    return TEMPLATE.format(locale=locale, source=relative, body=body)


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for locale, source in PAIRS.items():
        target = OUTPUT_DIR / f"config_{locale}.js"
        target.write_text(render(locale, source), encoding="utf-8")
        print(f"written {target.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
