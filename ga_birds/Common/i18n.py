import json
from pathlib import Path
from typing import Dict, Any, Optional


class I18n:
    """多语言管理器"""

    def __init__(self, locale: str = "en_US"):
        self.locale = locale
        self.translations: Dict[str, Any] = {}
        self.load_translations()

    def load_translations(self):
        """加载翻译文件"""
        langues_dir = Path(__file__).parent.parent / "Langues"
        locale_file = langues_dir / f"{self.locale}.json"

        if locale_file.exists():
            with open(locale_file, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
        else:
            fallback_file = langues_dir / "en_US.json"
            if fallback_file.exists():
                with open(fallback_file, 'r', encoding='utf-8') as f:
                    self.translations = json.load(f)
            else:
                self.translations = {}

    def t(self, key: str, **kwargs) -> str:
        """
        翻译函数

        Args:
            key: 翻译键（支持点号分隔，如 "video.processing"）
            **kwargs: 占位符参数

        Returns:
            翻译后的文本

        Examples:
            >>> i18n.t("common.success")
            "Success"
            >>> i18n.t("video.processing", path="/videos/ep01.mp4")
            "Processing: /videos/ep01.mp4"
        """
        keys = key.split('.')
        value = self.translations

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return key
            else:
                return key

        if not isinstance(value, str):
            return key

        if kwargs:
            try:
                return value.format(**kwargs)
            except (KeyError, ValueError):
                return value

        return value

    def change_locale(self, locale: str):
        """
        切换语言

        Args:
            locale: 新的语言代码
        """
        self.locale = locale
        self.load_translations()


_i18n_instance: Optional[I18n] = None


def get_i18n(locale: str = None) -> I18n:
    """
    获取 i18n 实例（单例模式）

    Args:
        locale: 语言代码（可选）

    Returns:
        I18n 实例
    """
    global _i18n_instance

    if _i18n_instance is None:
        _i18n_instance = I18n(locale or "en_US")
    elif locale and _i18n_instance.locale != locale:
        _i18n_instance.change_locale(locale)

    return _i18n_instance


def t(key: str, **kwargs) -> str:
    """
    快捷翻译函数

    Args:
        key: 翻译键
        **kwargs: 占位符参数

    Returns:
        翻译后的文本

    Examples:
        >>> from ga_birds.Common.i18n import t
        >>> t("common.success")
        "Success"
    """
    return get_i18n().t(key, **kwargs)


def set_locale(locale: str):
    """
    设置全局语言

    Args:
        locale: 语言代码（en_US / zh_CN / ja_JP）
    """
    get_i18n(locale)

