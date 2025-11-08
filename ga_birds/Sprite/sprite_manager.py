"""
GA Sprite Birds - 角色管理器
管理不同角色的音色配置（V1 版本简化实现，V2 扩展多角色）

版本: v1.0
开发团队: Tiger
"""

from dataclasses import dataclass
from typing import Optional, Dict

from loguru import logger


@dataclass
class Sprite:
    """角色数据类"""
    name: str  # 角色名称
    voice: str  # 音色标识
    emotion: str = "neutral"  # 情绪
    description: Optional[str] = None  # 角色描述


class SpriteManager:
    """角色管理器"""
    
    def __init__(self):
        """初始化角色管理器"""
        self.sprites: Dict[str, Sprite] = {}
        
        # 添加默认角色
        self.add_sprite(Sprite(
            name="default",
            voice="zh-CN-XiaoxiaoNeural",
            emotion="neutral",
            description="默认女声"
        ))
        
        logger.info("角色管理器初始化完成")
    
    def add_sprite(self, sprite: Sprite) -> None:
        """
        添加角色
        
        Args:
            sprite: 角色对象
        """
        self.sprites[sprite.name] = sprite
        logger.info(f"添加角色: {sprite.name}, 音色: {sprite.voice}")
    
    def get_sprite(self, name: str) -> Optional[Sprite]:
        """
        获取角色
        
        Args:
            name: 角色名称
            
        Returns:
            角色对象，如果不存在则返回 None
        """
        return self.sprites.get(name)
    
    def get_default_sprite(self) -> Sprite:
        """
        获取默认角色
        
        Returns:
            默认角色对象
        """
        return self.sprites.get("default")
    
    def list_sprites(self) -> list[Sprite]:
        """
        列出所有角色
        
        Returns:
            角色列表
        """
        return list(self.sprites.values())
    
    def remove_sprite(self, name: str) -> bool:
        """
        移除角色
        
        Args:
            name: 角色名称
            
        Returns:
            是否成功移除
        """
        if name in self.sprites:
            del self.sprites[name]
            logger.info(f"移除角色: {name}")
            return True
        return False

