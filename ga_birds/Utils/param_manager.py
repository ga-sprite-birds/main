"""
参数管理器
统一处理命令行参数、API 参数和配置文件参数的优先级
优先级：命令行/API 参数 > 配置文件参数
"""

from typing import Optional
import config


class ParamManager:
    """参数管理器"""
    
    @staticmethod
    def merge_enable_llm(cli_value: Optional[bool]) -> bool:
        """
        合并 LLM 启用参数
        
        Args:
            cli_value: 命令行/API 参数值（None 表示未指定）
            
        Returns:
            最终使用的值
        """
        if cli_value is not None:
            return cli_value
        return config.ENABLE_LLM
    
    @staticmethod
    def merge_multi_voice(cli_value: Optional[bool]) -> bool:
        """
        合并多角色配音参数
        
        Args:
            cli_value: 命令行/API 参数值（None 表示未指定）
            
        Returns:
            最终使用的值
        """
        if cli_value is not None:
            return cli_value
        return config.ENABLE_MULTI_VOICE
    
    @staticmethod
    def merge_voice(cli_value: Optional[str]) -> str:
        """
        合并音色参数
        
        Args:
            cli_value: 命令行/API 参数值（None 表示未指定）
            
        Returns:
            最终使用的值
        """
        if cli_value is not None:
            return cli_value
        return config.TTS_VOICE
    
    @staticmethod
    def merge_rate(cli_value: Optional[float]) -> Optional[float]:
        """
        合并语速参数
        
        Args:
            cli_value: 命令行/API 参数值（None 表示未指定）
            
        Returns:
            最终使用的值
        """
        if cli_value is not None:
            return cli_value
        return config.TTS_RATE if hasattr(config, 'TTS_RATE') else None
    
    @staticmethod
    def merge_output_dir(cli_value: Optional[str]) -> str:
        """
        合并输出目录参数
        
        Args:
            cli_value: 命令行/API 参数值（None 表示未指定）
            
        Returns:
            最终使用的值
        """
        if cli_value is not None:
            return cli_value
        return config.OUTPUT_DIR
    
    @staticmethod
    def merge_all_params(
        enable_llm: Optional[bool] = None,
        multi_voice: Optional[bool] = None,
        voice: Optional[str] = None,
        rate: Optional[float] = None,
        output_dir: Optional[str] = None
    ) -> dict:
        """
        一次性合并所有参数
        
        Args:
            enable_llm: LLM 启用参数
            multi_voice: 多角色配音参数
            voice: 音色参数
            rate: 语速参数
            output_dir: 输出目录参数
            
        Returns:
            合并后的参数字典
        """
        return {
            'enable_llm': ParamManager.merge_enable_llm(enable_llm),
            'multi_voice': ParamManager.merge_multi_voice(multi_voice),
            'voice': ParamManager.merge_voice(voice),
            'rate': ParamManager.merge_rate(rate),
            'output_dir': ParamManager.merge_output_dir(output_dir)
        }

