"""Generate a lead-in (导读) chapter for a task.

Used at generation time so the per-task ``chapter_lead_in_enabled`` option can
decide it. If the source already contains front matter (导读/前言), it is kept
as-is and no new chapter is generated.
"""

from __future__ import annotations

import asyncio
from typing import Any

LEAD_IN_TITLE = "导读篇"
LEAD_IN_SAMPLE_CHARS = 6000


def has_front_matter(chapters: list[dict[str, Any]]) -> bool:
    from ga_birds.Audio.audio_exporter import AudioExporter

    return any(
        AudioExporter.front_matter_marker(chapter.get("title") or "")
        for chapter in chapters
    )


async def generate_lead_in(
    chapters: list[dict[str, Any]],
    language: str = "zh_CN",
) -> str | None:
    """Return lead-in text, or None when unnecessary/unavailable."""
    if has_front_matter(chapters):
        return None

    from ga_birds.LLM import LLMManager

    total_chars = sum(len(chapter.get("content") or "") for chapter in chapters)
    target_chars = min(500, max(80, total_chars // 300))
    sample = "\n\n".join(
        chapter.get("content") or "" for chapter in chapters
    )[:LEAD_IN_SAMPLE_CHARS]
    if not sample.strip():
        return None

    llm = LLMManager()
    if str(language).lower().startswith("en"):
        system_prompt = "You are an audiobook editor who writes engaging lead-ins."
        prompt = f"""Write an English lead-in of about {target_chars} words for the book below.
Requirements:
1. Summarize the theme, core ideas, or story arc.
2. Highlight what makes it worth reading, without spoiling the ending.
3. Natural tone, suitable to open an audiobook.
4. Output only the lead-in text - no title, no bullet points, no explanation.

Book excerpt:
{sample}
"""
    else:
        system_prompt = "你是有声书编辑，擅长撰写吸引人的导读。"
        prompt = f"""请根据下面的书籍内容，写一段约 {target_chars} 字的中文导读。
要求：
1. 概括全书主题、核心观点或故事梗概；
2. 点出主要看点，但不要剧透结局；
3. 语气自然，适合作为有声书的开篇朗读；
4. 直接输出导读正文，不要标题、不要分点、不要任何说明。

书籍内容节选：
{sample}
"""

    result = await asyncio.to_thread(llm.generate, prompt, system_prompt)
    text = (result or "").strip()
    return text or None
