"""
Parameter manager
Unified handling of priority between command-line arguments, API arguments, and config file parameters
Priority: command-line / API arguments > config file parameters

Naming conventions:
- CLI arguments: kebab-case (e.g. --multi-voice)
- Config items: UPPER_SNAKE_CASE (e.g. ENABLE_MULTI_VOICE)
- Function arguments: snake_case (e.g. multi_voice)
"""

from typing import Optional, Any, Dict
import config


class ParamManager:
    """Parameter manager"""

    # Parameter mapping table: function argument name -> (config item name, type conversion function)
    PARAM_MAPPING = {
        # LLM related
        'enable_llm': ('ENABLE_LLM', bool),

        # TTS related
        'voice': ('TTS_VOICE', str),
        'rate': ('TTS_RATE', float),
        'volume': ('TTS_VOLUME', float),
        'pitch': ('TTS_PITCH', int),

        # Multi-character voice related
        'multi_voice': ('ENABLE_MULTI_VOICE', bool),
        'analysis_mode': ('CHARACTER_ANALYSIS_MODE', str),

        # Chapter related
        'chapter_intro_outro': ('CHAPTER_INTRO_OUTRO', bool),
        'chapter_intro_template': ('CHAPTER_INTRO_TEMPLATE', str),
        'chapter_outro_template': ('CHAPTER_OUTRO_TEMPLATE', str),
        'chapter_keep_title': ('CHAPTER_KEEP_TITLE', bool),

        # Output related
        'output_dir': ('OUTPUT_BASE_PATH', str),
        'output_strategy': ('OUTPUT_STRATEGY', str),
        'output_duplicate_handling': ('OUTPUT_DUPLICATE_HANDLING', str),

        # Other
        'log_level': ('LOG_LEVEL', str),
    }

    @staticmethod
    def _get_config_value(config_name: str, default: Any = None) -> Any:
        """
        Get a value from the configuration

        Args:
            config_name: config item name
            default: default value

        Returns:
            config value
        """
        return getattr(config, config_name, default)

    @staticmethod
    def _convert_value(value: Any, target_type: type) -> Any:
        """
        Convert the value type

        Args:
            value: original value
            target_type: target type

        Returns:
            converted value
        """
        if value is None:
            return None

        # Special handling for booleans
        if target_type == bool:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes')
            return bool(value)

        # Convert other types directly
        try:
            return target_type(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def merge_param(param_name: str, user_value: Optional[Any] = None) -> Any:
        """
        Merge a single parameter

        Args:
            param_name: parameter name (function argument name, snake_case)
            user_value: value provided by the user (CLI/API; None means unspecified)

        Returns:
            the final value used
        """
        # If the user provided a value, use it
        if user_value is not None:
            if param_name in ParamManager.PARAM_MAPPING:
                _, target_type = ParamManager.PARAM_MAPPING[param_name]
                return ParamManager._convert_value(user_value, target_type)
            return user_value

        # Otherwise use the config file value
        if param_name in ParamManager.PARAM_MAPPING:
            config_name, target_type = ParamManager.PARAM_MAPPING[param_name]
            config_value = ParamManager._get_config_value(config_name)
            return ParamManager._convert_value(config_value, target_type)

        # Unknown parameter, return None
        return None

    @staticmethod
    def merge_all_params(**user_params) -> Dict[str, Any]:
        """
        Merge all parameters at once

        Args:
            **user_params: parameters provided by the user (CLI/API)

        Returns:
            merged parameter dictionary
        """
        result = {}

        # Iterate over all known parameters
        for param_name in ParamManager.PARAM_MAPPING.keys():
            user_value = user_params.get(param_name)
            result[param_name] = ParamManager.merge_param(param_name, user_value)

        # Add parameters not in the mapping table (passed through directly)
        for param_name, user_value in user_params.items():
            if param_name not in result:
                result[param_name] = user_value

        return result

    # ========== Convenience methods ==========

    @staticmethod
    def merge_enable_llm(cli_value: Optional[bool]) -> bool:
        """Merge the LLM-enable parameter"""
        return ParamManager.merge_param('enable_llm', cli_value)

    @staticmethod
    def merge_multi_voice(cli_value: Optional[bool]) -> bool:
        """Merge the multi-character voice parameter"""
        return ParamManager.merge_param('multi_voice', cli_value)

    @staticmethod
    def merge_voice(cli_value: Optional[str]) -> str:
        """Merge the voice parameter"""
        return ParamManager.merge_param('voice', cli_value)

    @staticmethod
    def merge_rate(cli_value: Optional[float]) -> Optional[float]:
        """Merge the speech rate parameter"""
        return ParamManager.merge_param('rate', cli_value)

    @staticmethod
    def merge_output_dir(cli_value: Optional[str]) -> str:
        """Merge the output directory parameter"""
        return ParamManager.merge_param('output_dir', cli_value)

