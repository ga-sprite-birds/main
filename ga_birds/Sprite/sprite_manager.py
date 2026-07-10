"""
GA Sprite Birds - Character manager
Manages voice configuration for different characters (simplified V1 implementation; V2 extends to multi-character)

Version: v1.0
Dev team: Tiger
"""

from dataclasses import dataclass
from typing import Optional, Dict

from loguru import logger


@dataclass
class Sprite:
    """Character data class"""
    name: str  # character name
    voice: str  # voice identifier
    emotion: str = "neutral"  # emotion
    description: Optional[str] = None  # character description


class SpriteManager:
    """Character manager"""

    def __init__(self):
        """Initialize the character manager"""
        self.sprites: Dict[str, Sprite] = {}

        # Add the default character
        self.add_sprite(Sprite(
            name="default",
            voice="zh-CN-XiaoxiaoNeural",
            emotion="neutral",
            description="默认女声"
        ))
        
        logger.info("角色管理器初始化完成")
    
    def add_sprite(self, sprite: Sprite) -> None:
        """
        Add a character

        Args:
            sprite: character object
        """
        self.sprites[sprite.name] = sprite
        logger.info(f"添加角色: {sprite.name}, 音色: {sprite.voice}")

    def get_sprite(self, name: str) -> Optional[Sprite]:
        """
        Get a character

        Args:
            name: character name

        Returns:
            character object, or None if it does not exist
        """
        return self.sprites.get(name)

    def get_default_sprite(self) -> Sprite:
        """
        Get the default character

        Returns:
            default character object
        """
        return self.sprites.get("default")

    def list_sprites(self) -> list[Sprite]:
        """
        List all characters

        Returns:
            character list
        """
        return list(self.sprites.values())

    def remove_sprite(self, name: str) -> bool:
        """
        Remove a character

        Args:
            name: character name

        Returns:
            whether removal succeeded
        """
        if name in self.sprites:
            del self.sprites[name]
            logger.info(f"移除角色: {name}")
            return True
        return False

