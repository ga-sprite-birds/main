"""
角色列表解析器
解析用户提供的角色列表文件
"""

from typing import List, Dict
from pathlib import Path
from loguru import logger


class CharacterListParser:
    """角色列表解析器"""
    
    @staticmethod
    def parse_file(file_path: str) -> List[Dict]:
        """
        解析角色列表文件
        
        支持格式：
        1. 简单格式：每行一个角色名
           陈洪德
           老爸
           爷爷
        
        2. 带性别格式：角色名 性别
           陈洪德 male
           老爸 male
           王婶 female
        
        3. 支持注释：# 开头的行
           # 主要角色
           陈洪德 male
           # 配角
           老爸 male
        
        Args:
            file_path: 角色列表文件路径
            
        Returns:
            角色列表：[{"name": "陈洪德", "gender": "male"}, ...]
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.error(f"角色列表文件不存在: {file_path}")
            return []
        
        characters = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    # 去除首尾空白
                    line = line.strip()
                    
                    # 跳过空行和注释
                    if not line or line.startswith('#'):
                        continue
                    
                    # 解析角色
                    parts = line.split()
                    
                    if len(parts) == 1:
                        # 简单格式：只有角色名
                        characters.append({
                            "name": parts[0],
                            "gender": "unknown"
                        })
                    elif len(parts) == 2:
                        # 带性别格式：角色名 性别
                        name, gender = parts
                        
                        # 验证性别
                        if gender.lower() not in ['male', 'female', 'unknown', 'narrator']:
                            logger.warning(f"第 {line_num} 行：性别 '{gender}' 无效，使用 'unknown'")
                            gender = 'unknown'
                        
                        characters.append({
                            "name": name,
                            "gender": gender.lower()
                        })
                    else:
                        logger.warning(f"第 {line_num} 行：格式错误，跳过: {line}")
                        continue
            
            logger.info(f"✓ 从角色列表文件读取 {len(characters)} 个角色")
            return characters
            
        except Exception as e:
            logger.error(f"读取角色列表文件失败: {e}")
            return []
    
    @staticmethod
    def validate_characters(characters: List[Dict]) -> bool:
        """
        验证角色列表
        
        Args:
            characters: 角色列表
            
        Returns:
            是否有效
        """
        if not characters:
            logger.error("角色列表为空")
            return False
        
        # 检查重复角色
        names = [char['name'] for char in characters]
        duplicates = [name for name in names if names.count(name) > 1]
        
        if duplicates:
            logger.warning(f"检测到重复角色: {', '.join(set(duplicates))}")
            return False
        
        return True
    
    @staticmethod
    def create_example_file(output_path: str):
        """
        创建示例角色列表文件
        
        Args:
            output_path: 输出文件路径
        """
        example_content = """# 角色列表示例
# 格式：角色名 [性别]
# 性别可选值：male, female, unknown, narrator
# 性别可省略，默认为 unknown

# 主要角色
陈洪德 male
老爸 male
爷爷 male

# 配角
王婶 female
二叔 male

# 特殊角色
旁白 narrator
其他 unknown
"""
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(example_content)
        
        logger.info(f"✓ 示例角色列表文件已创建: {output_path}")

