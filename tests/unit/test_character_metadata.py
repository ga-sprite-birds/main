"""
Test character metadata normalization and localization.
"""

import sys
from pathlib import Path

# Add the project root directory to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import config
from ga_birds.character_analyzer import CharacterAnalyzer, VoiceAssigner


class StubLLMManager:
    def __init__(self, response: str):
        self.response = response

    def generate(self, prompt: str, **kwargs) -> str:
        return self.response


def test_analyzer_keeps_source_language_metadata(monkeypatch):
    monkeypatch.setattr(config, "LANGUAGE", "en_US")

    llm_response = """
    {
      "characters": [
        {
          "name": "老板",
          "aliases": ["boss", "老板", "女同事A"],
          "gender": "male",
          "personality": ["严厉", "直接", "领导"]
        }
      ]
    }
    """
    analyzer = CharacterAnalyzer(StubLLMManager(llm_response))
    chapter_content = (
        "One day, someone kindly warned them: "
        "\"Be careful, the boss might catch you.\""
    )

    characters = analyzer.analyze_chapter(chapter_content, 1)

    assert len(characters) == 1
    assert characters[0]["name"] == "boss"
    assert characters[0]["aliases"] == []
    assert characters[0]["personality"] == ["strict", "direct", "leader"]


def test_voice_assigner_localizes_narrator_metadata(monkeypatch):
    monkeypatch.setattr(config, "LANGUAGE", "en_US")

    template = VoiceAssigner.create_character_template(
        [
            {
                "name": "boss",
                "aliases": [],
                "gender": "male",
                "voice": "zh-CN-YunxiNeural",
                "description": "",
                "personality": ["strict"],
                "appearance_count": 1,
                "first_chapter": 1,
                "last_chapter": 1,
            }
        ],
        "en",
        "en",
    )

    assert template["narrator"]["name"] == "narrator"
    assert template["narrator"]["personality"] == ["objective", "calm"]
