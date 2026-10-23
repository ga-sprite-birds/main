"""
GA Sprite Birds - Configuration manager
Wraps the config module and provides type-safe configuration access interfaces

Version: v1.0
Dev team: Tiger
"""

from typing import List
import config


class ConfigManager:
    """Configuration manager - wraps configuration access"""

    # ========== Chapter configuration ==========

    @staticmethod
    def is_chapter_intro_outro_enabled() -> bool:
        """Whether intro/outro is enabled"""
        return config.CHAPTER_INTRO_OUTRO

    @staticmethod
    def get_chapter_intro_template() -> str:
        """Get the intro template"""
        return config.CHAPTER_INTRO_TEMPLATE

    @staticmethod
    def get_chapter_outro_template() -> str:
        """Get the outro template"""
        return config.CHAPTER_OUTRO_TEMPLATE

    @staticmethod
    def get_chapter_regex_patterns() -> List[str]:
        """Get the chapter detection regex patterns"""
        return config.CHAPTER_REGEX_PATTERNS

    @staticmethod
    def get_chapter_min_length() -> int:
        """Get the minimum chapter length"""
        return config.CHAPTER_MIN_LENGTH

    @staticmethod
    def is_chapter_keep_title() -> bool:
        """Whether to keep the chapter title"""
        return config.CHAPTER_KEEP_TITLE

    # ========== Output configuration ==========

    @staticmethod
    def is_save_chapter_text_enabled() -> bool:
        """Whether to save chapter text"""
        return config.OUTPUT_SAVE_CHAPTER_TEXT

    @staticmethod
    def get_chapter_text_encoding() -> str:
        """Get the chapter text encoding"""
        return config.OUTPUT_CHAPTER_TEXT_ENCODING

    @staticmethod
    def get_output_base_path() -> str:
        """Get the output base path"""
        return config.OUTPUT_BASE_PATH

    @staticmethod
    def get_output_duplicate_handling() -> str:
        """Get the file duplicate handling mode"""
        return config.OUTPUT_DUPLICATE_HANDLING

    @staticmethod
    def get_output_format() -> str:
        """Get the output audio format"""
        return config.OUTPUT_FORMAT

    @staticmethod
    def is_keep_temp_files() -> bool:
        """Whether to keep temporary files"""
        return config.OUTPUT_KEEP_TEMP_FILES

    # ========== Character analysis configuration ==========

    @staticmethod
    def is_multi_voice_enabled() -> bool:
        """Whether multi-character voice is enabled"""
        return config.ENABLE_MULTI_VOICE

    @staticmethod
    def get_character_analysis_mode() -> str:
        """Get the character analysis mode"""
        return config.CHARACTER_ANALYSIS_MODE

    @staticmethod
    def get_character_cache_dir() -> str:
        """Get the character cache directory"""
        return config.CHARACTER_CACHE_DIR

    # ========== LLM configuration ==========

    @staticmethod
    def is_llm_enabled() -> bool:
        """Whether LLM is enabled"""
        return config.ENABLE_LLM

    @staticmethod
    def get_llm_mode() -> str:
        """Get the LLM mode"""
        return config.LLM_MODE

    # ========== TTS configuration ==========

    @staticmethod
    def get_tts_engine() -> str:
        """Get the TTS engine"""
        return config.TTS_ENGINE

    @staticmethod
    def get_tts_voice() -> str:
        """Get the default voice"""
        return config.TTS_VOICE

    @staticmethod
    def get_tts_rate() -> float:
        """Get the speech rate multiplier"""
        return config.TTS_RATE

    # ========== Text preprocessing configuration ==========

    @staticmethod
    def is_text_preprocessing_enabled() -> bool:
        """Whether text preprocessing is enabled"""
        return config.TEXT_PREPROCESSING_ENABLED

