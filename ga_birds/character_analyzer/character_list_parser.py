"""
Character list parser
Parses the user-provided character list file
"""

from typing import List, Dict
from pathlib import Path
from loguru import logger
from ga_birds.Common.i18n import t


class CharacterListParser:
    """Character list parser"""
    
    @staticmethod
    def parse_file(file_path: str) -> List[Dict]:
        """
        Parse the character list file

        Supported formats:
        1. Simple format: one character name per line
            陈洪德
            老爸
            爷爷

        2. Gender format: <character_name> <gender>
            陈洪德 male
            老爸 male
            王婶 female

        3. Comments supported: lines starting with #
           # 主要角色
            陈洪德 male
            # 配角
            老爸 male

        Args:
            file_path: path to the character list file

        Returns:
            character list: [{"name": "陈洪德", "gender": "male"}, ...]
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.error(t("character.list_parser_file_not_found", path=file_path))
            return []
        
        characters = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    # Strip leading/trailing whitespace
                    line = line.strip()

                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue

                    # Parse the character
                    parts = line.split()

                    if len(parts) == 1:
                        # Simple format: only the character name
                        characters.append({
                            "name": parts[0],
                            "gender": "unknown"
                        })
                    elif len(parts) == 2:
                        # Gender format: <character_name> <gender>
                        name, gender = parts

                        # Validate gender
                        if gender.lower() not in ['male', 'female', 'unknown', 'narrator']:
                            logger.warning(t("character.list_parser_invalid_gender", line=line_num, gender=gender))
                            gender = 'unknown'
                        
                        characters.append({
                            "name": name,
                            "gender": gender.lower()
                        })
                    else:
                        logger.warning(t("character.list_parser_format_error", line=line_num, text=line))
                        continue
            
            logger.info(t("character.list_parser_read_success", count=len(characters)))
            return characters
            
        except Exception as e:
            logger.error(t("character.list_parser_read_failed", error=e))
            return []
    
    @staticmethod
    def validate_characters(characters: List[Dict]) -> bool:
        """
        Validate the character list

        Args:
            characters: character list

        Returns:
            whether valid
        """
        if not characters:
            logger.error(t("character.list_parser_empty"))
            return False

        # Check for duplicate characters
        names = [char['name'] for char in characters]
        duplicates = [name for name in names if names.count(name) > 1]
        
        if duplicates:
            logger.warning(t("character.list_parser_duplicates", names=", ".join(set(duplicates))))
            return False
        
        return True
    
    @staticmethod
    def create_example_file(output_path: str):
        """
        Create an example character list file

        Args:
            output_path: output file path
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
        
        logger.info(t("character.list_parser_example_created", path=output_path))

