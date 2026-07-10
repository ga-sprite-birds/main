"""
GA Sprite Birds - Model manager
Responsible for model detection, download, cache directory management, and device selection

Version: v1.0
Dev team: Tiger
"""

import os
import sys
from pathlib import Path
from typing import Optional, Tuple

import ollama
from loguru import logger

from ga_birds.Common.i18n import t

import config


class ModelManager:
    """Model manager"""

    def __init__(self):
        """Initialize the model manager"""
        self.cache_dir = Path(config.MODEL_CACHE_DIR)
        
    def ensure_cache_dir(self) -> bool:
        """
        Ensure the cache directory exists

        Returns:
            bool: True on success, False on failure
        """
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(t("model.cache_dir_ready", path=str(self.cache_dir.absolute())))
            return True
        except PermissionError:
            logger.error(t("model.cache_dir_permission_error", path=str(self.cache_dir.absolute())))
            logger.error(t("model.cache_dir_permission_hint"))
            return False
        except Exception as e:
            logger.error(t("model.cache_dir_create_failed", error=e))
            logger.error(t("model.cache_dir_path", path=str(self.cache_dir.absolute())))
            return False

    def check_ollama_model(self, model_name: str) -> bool:
        """
        Check whether the Ollama model exists

        Args:
            model_name: model name

        Returns:
            bool: True if the model exists, otherwise False
        """
        try:
            # Get the list of installed models
            models = ollama.list()

            # Handle different return formats
            if hasattr(models, 'models'):
                # Newer ollama returns an object
                model_list = models.models
            else:
                # Older version returns a dict
                model_list = models.get('models', [])

            # Check whether the model exists
            for model in model_list:
                # Try to get the model name (supports different field names)
                current_model_name = None
                if hasattr(model, 'model'):
                    current_model_name = model.model
                elif isinstance(model, dict):
                    current_model_name = model.get('model') or model.get('name')

                if current_model_name and current_model_name.startswith(model_name):
                    logger.info(t("model.ollama_model_found", model=current_model_name))
                    return True

            logger.warning(t("model.ollama_model_not_found", model=model_name))
            return False

        except Exception as e:
            logger.error(t("model.ollama_check_failed", error=e))
            logger.error(t("model.ollama_service_hint"))
            return False
    
    def download_ollama_model(self, model_name: str) -> bool:
        """
        Download the Ollama model

        Args:
            model_name: model name

        Returns:
            bool: True if download succeeded, otherwise False
        """
        try:
            logger.info(t("model.downloading_model", model=model_name))
            logger.info(t("model.download_may_take_long"))

            # Use ollama.pull() to download the model
            # This shows download progress
            for progress in ollama.pull(model_name, stream=True):
                status = progress.get('status', '')
                if 'total' in progress and 'completed' in progress:
                    total = progress['total']
                    completed = progress['completed']
                    percent = (completed / total * 100) if total > 0 else 0
                    logger.info(t("model.download_progress", percent=percent, completed=completed, total=total))
                else:
                    logger.info(t("model.download_status", status=status))

            logger.info(t("model.download_complete", model=model_name))
            return True

        except KeyboardInterrupt:
            logger.warning(t("model.download_interrupted"))
            return False
        except Exception as e:
            logger.error(t("model.download_failed", error=e))
            logger.error(t("model.manual_download_hint", model=model_name))
            return False

    def ensure_ollama_model(self, model_name: str) -> bool:
        """
        Ensure the Ollama model is available (detect + download)

        Args:
            model_name: model name

        Returns:
            bool: True if the model is available, otherwise False
        """
        # 1. Check whether the model exists
        if self.check_ollama_model(model_name):
            return True

        # 2. Model does not exist, try to download
        logger.info(t("model.model_not_found_locally", model=model_name))

        # Ask the user whether to download (if in an interactive environment)
        if sys.stdin.isatty():
            response = input(f"是否下载模型 {model_name}? (y/n): ").strip().lower()
            if response != 'y':
                logger.warning(t("model.user_cancelled"))
                return False

        # 3. Download the model
        return self.download_ollama_model(model_name)
    
    def get_device(self, prefer_gpu: bool = True) -> Tuple[str, str]:
        """
        Get an available compute device

        Args:
            prefer_gpu: whether to prefer GPU

        Returns:
            Tuple[str, str]: (device type, device description)
                device type: 'cuda', 'mps', 'cpu'
                device description: detailed device information
        """
        # Check CUDA (NVIDIA GPU)
        if prefer_gpu:
            try:
                import torch
                if torch.cuda.is_available():
                    device_name = torch.cuda.get_device_name(0)
                    device_count = torch.cuda.device_count()
                    logger.info(t("model.cuda_detected", name=device_name, count=device_count))
                    return 'cuda', f"CUDA - {device_name}"
            except ImportError:
                logger.debug(t("model.pytorch_not_installed"))
            except Exception as e:
                logger.debug(t("model.cuda_check_failed", error=e))

        # Check MPS (Apple Silicon GPU)
        if prefer_gpu and sys.platform == 'darwin':
            try:
                import torch
                if torch.backends.mps.is_available():
                    logger.info(t("model.mps_detected"))
                    return 'mps', "MPS - Apple Silicon GPU"
            except ImportError:
                logger.debug(t("model.pytorch_not_installed"))
            except Exception as e:
                logger.debug(t("model.mps_check_failed", error=e))

        # Default to CPU
        import platform
        cpu_info = f"{platform.processor()} ({platform.machine()})"
        logger.info(t("model.using_cpu", info=cpu_info))
        return 'cpu', f"CPU - {cpu_info}"
    
    def check_ollama_service(self, host: str = "http://localhost:11434") -> bool:
        """
        Check whether the Ollama service is running

        Args:
            host: Ollama service address

        Returns:
            bool: True if the service is running, otherwise False
        """
        try:
            import httpx
            response = httpx.get(f"{host}/api/tags", timeout=5.0)
            if response.status_code == 200:
                logger.info(t("model.ollama_service_running", host=host))
                return True
            else:
                logger.error(t("model.ollama_service_error", code=response.status_code))
                return False
        except Exception as e:
            logger.error(t("model.ollama_service_unreachable", error=e))
            logger.error(t("model.ollama_service_start_hint"))
            logger.error(t("model.ollama_service_step1"))
            logger.error(t("model.ollama_service_step2", host=host))
            return False
    
    def validate_local_llm_setup(self) -> bool:
        """
        Validate the local LLM setup

        Returns:
            bool: True if the setup is valid, otherwise False
        """
        if config.LLM_MODE != "local":
            return True

        logger.info(t("model.validating_llm_setup"))

        # 1. Check the Ollama service
        if not self.check_ollama_service(config.LLM_LOCAL_HOST):
            return False

        # 2. Check and download the model
        model_name = config.LLM_LOCAL_MODEL
        if not self.ensure_ollama_model(model_name):
            logger.error(t("model.model_unavailable", model=model_name))
            return False

        logger.info(t("model.llm_setup_valid"))
        return True

    def validate_local_tts_setup(self) -> bool:
        """
        Validate the local TTS setup

        Returns:
            bool: True if the setup is valid, otherwise False
        """
        if config.TTS_MODE != "local":
            return True

        logger.info(t("model.validating_tts_setup"))

        # 1. Check the model path
        model_path = Path(config.TTS_LOCAL_MODEL_PATH)
        if not model_path.exists():
            logger.warning(t("model.tts_model_path_missing", path=str(model_path.absolute())))
            logger.info(t("model.first_run_auto_download"))

        # 2. Check the device
        device_type, device_desc = self.get_device(
            prefer_gpu=(config.TTS_LOCAL_DEVICE != 'cpu')
        )

        # If GPU is required by config but only CPU is available, warn
        if config.TTS_LOCAL_DEVICE == 'cuda' and device_type == 'cpu':
            logger.warning(t("model.gpu_required_but_cpu"))
            logger.warning(t("model.cpu_may_be_slower"))

        logger.info(t("model.tts_device_ready", desc=device_desc))
        logger.info(t("model.tts_setup_valid"))
        return True

