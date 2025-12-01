"""
多语言支持（可选接入项目多语言）

使用方式：
1. 独立运行：使用本地翻译文件（utils/try_tts/langues/）
2. 项目集成：自动检测并使用项目多语言（ga_birds/Langues/）
3. 保底方案：硬编码默认翻译

优先级：项目多语言 > 本地翻译文件 > 硬编码默认翻译
"""

import sys
import json
from pathlib import Path
from typing import Optional


class UtilsI18n:
    def __init__(self, locale: str = "en_US"):
        self.locale = locale
        self.translations = {}
        self._use_project = False
        self._load_translations()

    def _load_translations(self):
        """加载翻译（优先级：本地 > 项目 > 硬编码）"""
        # 优先使用本地翻译文件（工具自己的翻译）
        if self._try_load_from_local():
            return
        # 其次尝试项目多语言（如果工具被集成到项目中）
        if self._try_load_from_project():
            return
        # 最后使用硬编码默认翻译
        self._load_hardcoded()

    def _try_load_from_project(self) -> bool:
        """尝试从项目多语言加载"""
        try:
            project_root = Path(__file__).parent.parent.parent
            sys.path.insert(0, str(project_root))

            from ga_birds.Common.i18n import get_i18n

            self._project_i18n = get_i18n(self.locale)
            self._use_project = True
            return True
        except (ImportError, FileNotFoundError):
            self._use_project = False
            return False

    def _try_load_from_local(self) -> bool:
        """从本地 JSON 文件加载"""
        local_file = Path(__file__).parent / "langues" / f"{self.locale}.json"

        if local_file.exists():
            with open(local_file, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
            return True
        return False

    def _load_hardcoded(self):
        """硬编码默认翻译（保底方案）"""
        if self.locale == "zh_CN":
            self.translations = {
                "fetching_voices": "正在获取音色列表...",
                "voices_fetched": "获取成功，共 {count} 个音色",
                "filter_condition": "筛选条件: 语言={language}, 性别={gender}",
                "voice_count": "音色数量: {count}",
                "generating": "正在生成",
                "saved": "已保存",
                "failed": "生成失败",
                "retry": "首次失败，等待3秒后重试...",
                "retry_success": "重试成功",
                "all_success": "全部生成成功",
                "partial_success": "部分生成成功，{success} 个成功，{failed} 个失败",
                "all_failed": "全部生成失败",
                "batch_generate": "批量生成试听音频",
                "batch_complete": "批量生成完成",
                "single_generate": "生成单个音色试听: {voice}",
                "audio_generated": "试听音频已生成: {file}",
                "no_voices": "错误: 未找到匹配的音色",
                "list_exported": "音色列表已导出: {file}",
                "saving_doc": "正在保存文档...",
                "all": "全部",
                "help": {
                    "description": "Edge TTS 配音试听工具",
                    "action": "操作类型: list(列出音色), generate(生成试听音频)",
                }
            }
        else:
            self.translations = {
                "fetching_voices": "Fetching voice list...",
                "voices_fetched": "Fetched successfully, {count} voices available",
                "filter_condition": "Filter: Language={language}, Gender={gender}",
                "voice_count": "Voice count: {count}",
                "generating": "Generating",
                "saved": "Saved",
                "failed": "Failed to generate",
                "retry": "First attempt failed, retrying in 3 seconds...",
                "retry_success": "Retry succeeded",
                "all_success": "All generated successfully",
                "partial_success": "Partially succeeded, {success} succeeded, {failed} failed",
                "all_failed": "All failed",
                "batch_generate": "Batch generating audio samples",
                "batch_complete": "Batch generation complete",
                "single_generate": "Generating single voice sample: {voice}",
                "audio_generated": "Audio generated: {file}",
                "no_voices": "Error: No matching voices found",
                "list_exported": "Voice list exported: {file}",
                "saving_doc": "Saving document...",
                "all": "All",
                "help": {
                    "description": "Edge TTS Voice Testing Tool",
                    "action": "Action type: list (list voices), generate (generate audio samples)",
                }
            }

    def t(self, key: str, **kwargs) -> str:
        """翻译函数"""
        if self._use_project:
            # 如果键不是以 tts. 开头，则添加前缀
            project_key = key if key.startswith('tts.') else f"tts.{key}"
            return self._project_i18n.t(project_key, **kwargs)

        # 支持点号分隔的嵌套键
        keys = key.split('.')
        text = self.translations
        for k in keys:
            if isinstance(text, dict):
                text = text.get(k, key)
            else:
                text = key
                break

        if isinstance(text, str):
            return text.format(**kwargs) if kwargs else text
        return str(text)


_i18n = None


def get_i18n(locale: str = None) -> UtilsI18n:
    """获取或创建 i18n 实例

    Args:
        locale: 语言代码。如果为 None，返回现有实例或创建默认实例
    """
    global _i18n
    if locale is not None:
        # 如果指定了语言，重新创建实例
        _i18n = UtilsI18n(locale)
    elif _i18n is None:
        # 如果没有指定语言且实例不存在，创建默认实例
        _i18n = UtilsI18n("en_US")
    return _i18n


def t(key: str, **kwargs) -> str:
    return get_i18n().t(key, **kwargs)

