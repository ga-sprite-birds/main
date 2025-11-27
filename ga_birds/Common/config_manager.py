"""
GA Sprite Birds - 配置管理器
封装 config 模块，提供类型安全的配置访问接口

版本: v1.0
开发团队: Tiger
"""

from typing import List
import config


class ConfigManager:
    """配置管理器 - 封装配置访问"""

    # ========== 章节配置 ==========

    @staticmethod
    def is_chapter_intro_outro_enabled() -> bool:
        """是否启用片头片尾"""
        return config.CHAPTER_INTRO_OUTRO

    @staticmethod
    def get_chapter_intro_template() -> str:
        """获取片头模板"""
        return config.CHAPTER_INTRO_TEMPLATE

    @staticmethod
    def get_chapter_outro_template() -> str:
        """获取片尾模板"""
        return config.CHAPTER_OUTRO_TEMPLATE

    @staticmethod
    def get_chapter_regex_patterns() -> List[str]:
        """获取章节识别正则表达式列表"""
        return config.CHAPTER_REGEX_PATTERNS

    @staticmethod
    def get_chapter_min_length() -> int:
        """获取最小章节长度"""
        return config.CHAPTER_MIN_LENGTH

    @staticmethod
    def is_chapter_keep_title() -> bool:
        """是否保留章节标题"""
        return config.CHAPTER_KEEP_TITLE

    # ========== 输出配置 ==========

    @staticmethod
    def is_save_chapter_text_enabled() -> bool:
        """是否保存章节文本"""
        return config.OUTPUT_SAVE_CHAPTER_TEXT

    @staticmethod
    def get_chapter_text_encoding() -> str:
        """获取章节文本编码"""
        return config.OUTPUT_CHAPTER_TEXT_ENCODING

    @staticmethod
    def get_output_base_path() -> str:
        """获取输出基础路径"""
        return config.OUTPUT_BASE_PATH

    @staticmethod
    def get_output_duplicate_handling() -> str:
        """获取文件重复处理方式"""
        return config.OUTPUT_DUPLICATE_HANDLING

    @staticmethod
    def get_output_format() -> str:
        """获取输出音频格式"""
        return config.OUTPUT_FORMAT

    @staticmethod
    def is_keep_temp_files() -> bool:
        """是否保留临时文件"""
        return config.OUTPUT_KEEP_TEMP_FILES

    # ========== 角色分析配置 ==========

    @staticmethod
    def is_multi_voice_enabled() -> bool:
        """是否启用多角色配音"""
        return config.ENABLE_MULTI_VOICE

    @staticmethod
    def get_character_analysis_mode() -> str:
        """获取角色分析模式"""
        return config.CHARACTER_ANALYSIS_MODE

    @staticmethod
    def get_character_cache_dir() -> str:
        """获取角色缓存目录"""
        return config.CHARACTER_CACHE_DIR

    # ========== LLM 配置 ==========

    @staticmethod
    def is_llm_enabled() -> bool:
        """是否启用 LLM"""
        return config.ENABLE_LLM

    @staticmethod
    def get_llm_mode() -> str:
        """获取 LLM 模式"""
        return config.LLM_MODE

    # ========== TTS 配置 ==========

    @staticmethod
    def get_tts_mode() -> str:
        """获取 TTS 模式"""
        return config.TTS_MODE

    @staticmethod
    def get_tts_engine() -> str:
        """获取 TTS 引擎"""
        return config.TTS_ENGINE

    @staticmethod
    def get_tts_voice() -> str:
        """获取默认音色"""
        return config.TTS_VOICE

    @staticmethod
    def get_tts_rate() -> float:
        """获取语速倍数"""
        return config.TTS_RATE

    # ========== 文本预处理配置 ==========

    @staticmethod
    def is_text_preprocessing_enabled() -> bool:
        """是否启用文本预处理"""
        return config.TEXT_PREPROCESSING_ENABLED

