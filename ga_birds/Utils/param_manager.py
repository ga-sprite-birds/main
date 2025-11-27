"""
参数管理器
统一处理命令行参数、API 参数和配置文件参数的优先级
优先级：命令行/API 参数 > 配置文件参数

命名规范：
- CLI 参数：kebab-case（如 --multi-voice）
- 配置项：UPPER_SNAKE_CASE（如 ENABLE_MULTI_VOICE）
- 函数参数：snake_case（如 multi_voice）
"""

from typing import Optional, Any, Dict
import config


class ParamManager:
    """参数管理器"""

    # 参数映射表：函数参数名 -> (配置项名, 类型转换函数)
    PARAM_MAPPING = {
        # LLM 相关
        'enable_llm': ('ENABLE_LLM', bool),

        # TTS 相关
        'voice': ('TTS_VOICE', str),
        'rate': ('TTS_RATE', float),
        'volume': ('TTS_VOLUME', float),
        'pitch': ('TTS_PITCH', int),

        # 多角色配音相关
        'multi_voice': ('ENABLE_MULTI_VOICE', bool),
        'analysis_mode': ('CHARACTER_ANALYSIS_MODE', str),

        # 章节相关
        'chapter_intro_outro': ('CHAPTER_INTRO_OUTRO', bool),
        'chapter_intro_template': ('CHAPTER_INTRO_TEMPLATE', str),
        'chapter_outro_template': ('CHAPTER_OUTRO_TEMPLATE', str),
        'chapter_keep_title': ('CHAPTER_KEEP_TITLE', bool),

        # 输出相关
        'output_dir': ('OUTPUT_BASE_PATH', str),
        'output_strategy': ('OUTPUT_STRATEGY', str),
        'output_duplicate_handling': ('OUTPUT_DUPLICATE_HANDLING', str),

        # 其他
        'log_level': ('LOG_LEVEL', str),
    }

    @staticmethod
    def _get_config_value(config_name: str, default: Any = None) -> Any:
        """
        从配置中获取值

        Args:
            config_name: 配置项名称
            default: 默认值

        Returns:
            配置值
        """
        return getattr(config, config_name, default)

    @staticmethod
    def _convert_value(value: Any, target_type: type) -> Any:
        """
        转换值类型

        Args:
            value: 原始值
            target_type: 目标类型

        Returns:
            转换后的值
        """
        if value is None:
            return None

        # 布尔值特殊处理
        if target_type == bool:
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes')
            return bool(value)

        # 其他类型直接转换
        try:
            return target_type(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def merge_param(param_name: str, user_value: Optional[Any] = None) -> Any:
        """
        合并单个参数

        Args:
            param_name: 参数名（函数参数名，snake_case）
            user_value: 用户提供的值（CLI/API，None 表示未指定）

        Returns:
            最终使用的值
        """
        # 如果用户提供了值，使用用户值
        if user_value is not None:
            if param_name in ParamManager.PARAM_MAPPING:
                _, target_type = ParamManager.PARAM_MAPPING[param_name]
                return ParamManager._convert_value(user_value, target_type)
            return user_value

        # 否则使用配置文件的值
        if param_name in ParamManager.PARAM_MAPPING:
            config_name, target_type = ParamManager.PARAM_MAPPING[param_name]
            config_value = ParamManager._get_config_value(config_name)
            return ParamManager._convert_value(config_value, target_type)

        # 未知参数，返回 None
        return None

    @staticmethod
    def merge_all_params(**user_params) -> Dict[str, Any]:
        """
        一次性合并所有参数

        Args:
            **user_params: 用户提供的参数（CLI/API）

        Returns:
            合并后的参数字典
        """
        result = {}

        # 遍历所有已知参数
        for param_name in ParamManager.PARAM_MAPPING.keys():
            user_value = user_params.get(param_name)
            result[param_name] = ParamManager.merge_param(param_name, user_value)

        # 添加未在映射表中的参数（直接传递）
        for param_name, user_value in user_params.items():
            if param_name not in result:
                result[param_name] = user_value

        return result

    # ========== 向后兼容的方法 ==========

    @staticmethod
    def merge_enable_llm(cli_value: Optional[bool]) -> bool:
        """合并 LLM 启用参数（向后兼容）"""
        return ParamManager.merge_param('enable_llm', cli_value)

    @staticmethod
    def merge_multi_voice(cli_value: Optional[bool]) -> bool:
        """合并多角色配音参数（向后兼容）"""
        return ParamManager.merge_param('multi_voice', cli_value)

    @staticmethod
    def merge_voice(cli_value: Optional[str]) -> str:
        """合并音色参数（向后兼容）"""
        return ParamManager.merge_param('voice', cli_value)

    @staticmethod
    def merge_rate(cli_value: Optional[float]) -> Optional[float]:
        """合并语速参数（向后兼容）"""
        return ParamManager.merge_param('rate', cli_value)

    @staticmethod
    def merge_output_dir(cli_value: Optional[str]) -> str:
        """合并输出目录参数（向后兼容）"""
        return ParamManager.merge_param('output_dir', cli_value)

