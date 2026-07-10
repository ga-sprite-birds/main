"""
Test dialogue parser segment metadata normalization.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import config
from ga_birds.character_analyzer import DialogueParser


class StubLLMManager:
    def __init__(self, response: str):
        self.response = response

    def generate(self, prompt: str, **kwargs) -> str:
        return self.response


def test_dialogue_parser_fills_language_and_tts_metadata(monkeypatch):
    monkeypatch.setattr(config, "SEGMENT_ENABLE_LANGUAGE_ANALYSIS", True)
    monkeypatch.setattr(config, "SEGMENT_ENABLE_EMOTION_ANALYSIS", True)

    parser = DialogueParser(
        StubLLMManager(
            """
            {
              "segments": [
                {
                  "text": "I can see you.",
                  "speaker": "boss"
                }
              ]
            }
            """
        ),
        [{"name": "boss", "aliases": [], "gender": "male"}],
    )

    segments = parser.parse_chapter("I can see you.", 1)

    assert len(segments) == 1
    assert segments[0]["language"] == "en"
    assert segments[0]["emotion"] == "neutral"
    assert segments[0]["segment_type"] == "dialogue"
    assert "rate" in segments[0]["tts_params"]
    assert "pitch" in segments[0]["tts_params"]
    assert "volume" in segments[0]["tts_params"]
