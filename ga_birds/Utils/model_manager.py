"""
GA Sprite Birds - 模型管理器
负责模型检测、下载、缓存目录管理和设备选择

版本: v1.0
开发团队: Tiger
"""

import os
import sys
from pathlib import Path
from typing import Optional, Tuple

import ollama
from loguru import logger

import ga_birds.config as config


class ModelManager:
    """模型管理器"""

    def __init__(self):
        """初始化模型管理器"""
        self.cache_dir = Path(config.MODEL_CACHE_DIR)
        
    def ensure_cache_dir(self) -> bool:
        """
        确保缓存目录存在
        
        Returns:
            bool: 成功返回 True，失败返回 False
        """
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"✓ 缓存目录已就绪: {self.cache_dir.absolute()}")
            return True
        except PermissionError:
            logger.error(f"❌ 无法创建缓存目录（权限不足）: {self.cache_dir.absolute()}")
            logger.error("请检查目录权限或更改 config.yaml 中的 model_download.cache_dir 配置")
            return False
        except Exception as e:
            logger.error(f"❌ 创建缓存目录失败: {e}")
            logger.error(f"路径: {self.cache_dir.absolute()}")
            return False
    
    def check_ollama_model(self, model_name: str) -> bool:
        """
        检查 Ollama 模型是否存在

        Args:
            model_name: 模型名称

        Returns:
            bool: 模型存在返回 True，否则返回 False
        """
        try:
            # 获取已安装的模型列表
            models = ollama.list()

            # 处理不同的返回格式
            if hasattr(models, 'models'):
                # 新版 ollama 返回对象
                model_list = models.models
            else:
                # 旧版返回字典
                model_list = models.get('models', [])

            # 检查模型是否存在
            for model in model_list:
                # 尝试获取模型名称（支持不同的字段名）
                current_model_name = None
                if hasattr(model, 'model'):
                    current_model_name = model.model
                elif isinstance(model, dict):
                    current_model_name = model.get('model') or model.get('name')

                if current_model_name and current_model_name.startswith(model_name):
                    logger.info(f"✓ 找到 Ollama 模型: {current_model_name}")
                    return True

            logger.warning(f"⚠ Ollama 模型不存在: {model_name}")
            return False

        except Exception as e:
            logger.error(f"❌ 检查 Ollama 模型失败: {e}")
            logger.error("请确保 Ollama 服务正在运行: ollama serve")
            return False
    
    def download_ollama_model(self, model_name: str) -> bool:
        """
        下载 Ollama 模型
        
        Args:
            model_name: 模型名称
            
        Returns:
            bool: 下载成功返回 True，否则返回 False
        """
        try:
            logger.info(f"正在下载 Ollama 模型: {model_name}")
            logger.info("这可能需要几分钟到几小时，取决于模型大小和网络速度...")
            
            # 使用 ollama.pull() 下载模型
            # 这会显示下载进度
            for progress in ollama.pull(model_name, stream=True):
                status = progress.get('status', '')
                if 'total' in progress and 'completed' in progress:
                    total = progress['total']
                    completed = progress['completed']
                    percent = (completed / total * 100) if total > 0 else 0
                    logger.info(f"下载进度: {percent:.1f}% ({completed}/{total} bytes)")
                else:
                    logger.info(f"状态: {status}")
            
            logger.info(f"✓ 模型下载完成: {model_name}")
            return True
            
        except KeyboardInterrupt:
            logger.warning("⚠ 用户中断下载")
            return False
        except Exception as e:
            logger.error(f"❌ 下载 Ollama 模型失败: {e}")
            logger.error(f"请手动下载: ollama pull {model_name}")
            return False
    
    def ensure_ollama_model(self, model_name: str) -> bool:
        """
        确保 Ollama 模型可用（检测 + 下载）
        
        Args:
            model_name: 模型名称
            
        Returns:
            bool: 模型可用返回 True，否则返回 False
        """
        # 1. 检查模型是否存在
        if self.check_ollama_model(model_name):
            return True
        
        # 2. 模型不存在，尝试下载
        logger.info(f"本地未找到模型 {model_name}，准备下载...")
        
        # 询问用户是否下载（如果是交互式环境）
        if sys.stdin.isatty():
            response = input(f"是否下载模型 {model_name}? (y/n): ").strip().lower()
            if response != 'y':
                logger.warning("用户取消下载")
                return False
        
        # 3. 下载模型
        return self.download_ollama_model(model_name)
    
    def get_device(self, prefer_gpu: bool = True) -> Tuple[str, str]:
        """
        获取可用的计算设备
        
        Args:
            prefer_gpu: 是否优先使用 GPU
            
        Returns:
            Tuple[str, str]: (设备类型, 设备描述)
                设备类型: 'cuda', 'mps', 'cpu'
                设备描述: 详细的设备信息
        """
        # 检查 CUDA (NVIDIA GPU)
        if prefer_gpu:
            try:
                import torch
                if torch.cuda.is_available():
                    device_name = torch.cuda.get_device_name(0)
                    device_count = torch.cuda.device_count()
                    logger.info(f"✓ 检测到 CUDA 设备: {device_name} (共 {device_count} 个)")
                    return 'cuda', f"CUDA - {device_name}"
            except ImportError:
                logger.debug("PyTorch 未安装，跳过 CUDA 检测")
            except Exception as e:
                logger.debug(f"CUDA 检测失败: {e}")
        
        # 检查 MPS (Apple Silicon GPU)
        if prefer_gpu and sys.platform == 'darwin':
            try:
                import torch
                if torch.backends.mps.is_available():
                    logger.info("✓ 检测到 MPS 设备 (Apple Silicon GPU)")
                    return 'mps', "MPS - Apple Silicon GPU"
            except ImportError:
                logger.debug("PyTorch 未安装，跳过 MPS 检测")
            except Exception as e:
                logger.debug(f"MPS 检测失败: {e}")
        
        # 默认使用 CPU
        import platform
        cpu_info = f"{platform.processor()} ({platform.machine()})"
        logger.info(f"✓ 使用 CPU 设备: {cpu_info}")
        return 'cpu', f"CPU - {cpu_info}"
    
    def check_ollama_service(self, host: str = "http://localhost:11434") -> bool:
        """
        检查 Ollama 服务是否运行
        
        Args:
            host: Ollama 服务地址
            
        Returns:
            bool: 服务运行返回 True，否则返回 False
        """
        try:
            import httpx
            response = httpx.get(f"{host}/api/tags", timeout=5.0)
            if response.status_code == 200:
                logger.info(f"✓ Ollama 服务正在运行: {host}")
                return True
            else:
                logger.error(f"❌ Ollama 服务响应异常: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ 无法连接到 Ollama 服务: {e}")
            logger.error(f"请确保 Ollama 服务正在运行:")
            logger.error(f"  1. 启动服务: ollama serve")
            logger.error(f"  2. 检查地址: {host}")
            return False
    
    def validate_local_llm_setup(self) -> bool:
        """
        验证本地 LLM 设置
        
        Returns:
            bool: 设置有效返回 True，否则返回 False
        """
        if config.LLM_MODE != "local":
            return True

        logger.info("正在验证本地 LLM 设置...")

        # 1. 检查 Ollama 服务
        if not self.check_ollama_service(config.LLM_LOCAL_HOST):
            return False

        # 2. 检查并下载模型
        model_name = config.LLM_LOCAL_MODEL
        if not self.ensure_ollama_model(model_name):
            logger.error(f"❌ 模型 {model_name} 不可用")
            return False

        logger.info("✓ 本地 LLM 设置验证通过")
        return True
    
    def validate_local_tts_setup(self) -> bool:
        """
        验证本地 TTS 设置
        
        Returns:
            bool: 设置有效返回 True，否则返回 False
        """
        if config.TTS_MODE != "local":
            return True

        logger.info("正在验证本地 TTS 设置...")

        # 1. 检查模型路径
        model_path = Path(config.TTS_LOCAL_MODEL_PATH)
        if not model_path.exists():
            logger.warning(f"⚠ TTS 模型路径不存在: {model_path.absolute()}")
            logger.info("首次运行时会自动下载模型")

        # 2. 检查设备
        device_type, device_desc = self.get_device(
            prefer_gpu=(config.TTS_LOCAL_DEVICE != 'cpu')
        )

        # 如果配置要求 GPU 但只有 CPU 可用，给出警告
        if config.TTS_LOCAL_DEVICE == 'cuda' and device_type == 'cpu':
            logger.warning("⚠ 配置要求使用 CUDA，但未检测到 GPU，将使用 CPU")
            logger.warning("这可能会导致性能下降")

        logger.info(f"✓ TTS 设备: {device_desc}")
        logger.info("✓ 本地 TTS 设置验证通过")
        return True

