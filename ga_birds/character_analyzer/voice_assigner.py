"""
Character voice assigner
Automatically assigns voices based on character gender
"""

import asyncio
import json
import threading
from pathlib import Path
from typing import Dict, List, Optional

import edge_tts
from loguru import logger
from ga_birds.Common.i18n import t
import config
from .segment_utils import SegmentUtils


def _run_async_safely(coro):
    """Run a coroutine even when a event loop is already running on this thread."""
    try:
        asyncio.get_running_loop()
        loop_is_running = True
    except RuntimeError:
        loop_is_running = False

    if not loop_is_running:
        return asyncio.run(coro)

    result: Dict = {}

    def _runner():
        try:
            result["value"] = asyncio.run(coro)
        except Exception as e:  # noqa: BLE001
            result["error"] = e

    worker = threading.Thread(target=_runner)
    worker.start()
    worker.join()

    if "error" in result:
        raise result["error"]
    return result.get("value")


class VoiceAssigner:
    """Character voice assigner"""

    LANGUAGE_LOCALE_PREFERENCES = {
        "en": ["en-US", "en-GB", "en-AU", "en-CA", "en-IN"],
        "zh": ["zh-CN", "zh-TW", "zh-HK"],
        "ja": ["ja-JP"],
        "de": ["de-DE", "de-AT", "de-CH"],
        "fr": ["fr-FR", "fr-CA", "fr-CH"],
        "es": ["es-ES", "es-MX", "es-US"],
        "it": ["it-IT"],
        "pt": ["pt-BR", "pt-PT"],
        "ru": ["ru-RU"],
        "ko": ["ko-KR"],
    }

    REGION_LOCALE_HINTS = {
        "british": ["en-GB"],
        "uk": ["en-GB"],
        "england": ["en-GB"],
        "american": ["en-US"],
        "usa": ["en-US"],
        "us": ["en-US"],
        "canada": ["en-CA"],
        "australia": ["en-AU"],
        "india": ["en-IN"],
        "china": ["zh-CN"],
        "mandarin": ["zh-CN"],
        "taiwan": ["zh-TW"],
        "hong kong": ["zh-HK"],
        "cantonese": ["zh-HK"],
        "japan": ["ja-JP"],
        "tokyo": ["ja-JP"],
        "brazil": ["pt-BR"],
        "portugal": ["pt-PT"],
        "mexico": ["es-MX"],
        "spain": ["es-ES"],
        "france": ["fr-FR"],
        "germany": ["de-DE"],
        "italy": ["it-IT"],
        "korea": ["ko-KR"],
    }

    @staticmethod
    def _get_narrator_metadata() -> Dict:
        language = str(config.LANGUAGE).lower()
        if language.startswith("en"):
            return {
                "name": "narrator",
                "personality": ["objective", "calm"]
            }
        if language.startswith("ja"):
            return {
                "name": "ナレーター",
                "personality": ["客観的", "落ち着いた"]
            }
        return {
            "name": "旁白",
            "personality": ["客观", "平静"]
        }

    def __init__(self, source_text: str = "", content_language: Optional[str] = None):
        """Initialize the voice assigner"""
        self.male_index = 0
        self.female_index = 0
        self.source_text = source_text or ""
        self.fallback_voice = config.TTS_VOICE
        self.fallback_locale = self._extract_locale_from_voice(self.fallback_voice)
        self.content_language = self._resolve_content_language(content_language, self.source_text)
        self.voice_catalog_path = Path(config.TTS_VOICE_CATALOG_CACHE)
        self.voice_catalog = self._load_or_fetch_voice_catalog()
        self.voice_pool_cache: Dict[str, Dict[str, List[str]]] = {}
        self.locale_voice_indices: Dict[str, Dict[str, int]] = {}
        self.target_locale = self._resolve_target_locale()
        self.MALE_VOICES, self.FEMALE_VOICES = self._build_voice_pools()
        self.narrator_voice = self._select_narrator_voice()
        logger.info(t("character.voice_assigner_initialized"))

    @staticmethod
    def _extract_locale_from_voice(voice_name: str) -> str:
        return SegmentUtils.extract_locale_from_voice(voice_name)

    @staticmethod
    def _extract_language_from_locale(locale: str) -> str:
        return SegmentUtils.extract_language_from_locale(locale)

    def _resolve_content_language(self, content_language: Optional[str], source_text: str) -> str:
        if content_language:
            language = SegmentUtils.normalize_language_code(
                content_language,
                fallback=self._extract_language_from_locale(self.fallback_voice) or "en",
            )
            logger.info(t("character.content_language_forced", language=language))
            return language

        language = SegmentUtils.detect_language(
            source_text,
            fallback_language=self._extract_language_from_locale(self.fallback_locale) or "en",
        )
        logger.info(t("character.content_language_detected", language=language))
        return language

    def _load_or_fetch_voice_catalog(self) -> List[Dict]:
        if self.voice_catalog_path.exists():
            try:
                with open(self.voice_catalog_path, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                voices = cached.get("voices", cached) if isinstance(cached, dict) else cached
                if isinstance(voices, list) and voices:
                    logger.info(
                        t("character.voice_catalog_loaded", path=self.voice_catalog_path, count=len(voices))
                    )
                    return voices
            except Exception as e:
                logger.warning(t("character.voice_catalog_load_failed", path=self.voice_catalog_path, error=e))

        logger.info(t("character.voice_catalog_missing", path=self.voice_catalog_path))
        return self._fetch_and_cache_voice_catalog()

    def _fetch_and_cache_voice_catalog(self) -> List[Dict]:
        try:
            logger.info(t("character.voice_catalog_fetching"))
            voices = _run_async_safely(edge_tts.list_voices())

            self.voice_catalog_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.voice_catalog_path, "w", encoding="utf-8") as f:
                json.dump({"voices": voices}, f, ensure_ascii=False, indent=2)

            logger.info(t("character.voice_catalog_saved", path=self.voice_catalog_path, count=len(voices)))
            return voices
        except Exception as e:
            logger.warning(t("character.voice_catalog_fetch_failed", error=e))
            logger.warning(t("character.voice_catalog_fallback_builtin"))
            return []

    def _resolve_target_locale(self) -> str:
        locale = self._resolve_language_locale(self.content_language)
        if locale:
            logger.info(t("character.voice_target_locale_selected", language=self.content_language, locale=locale))
            return locale

        logger.warning(
            t(
                "character.voice_target_locale_missing",
                language=self.content_language,
                fallback=self.fallback_voice,
            )
        )
        return ""

    def _get_available_locales(self) -> List[str]:
        return [
            voice.get("Locale", "")
            for voice in self.voice_catalog
            if voice.get("Locale")
        ]

    def _resolve_language_locale(
        self,
        language: str,
        preferred_locales: Optional[List[str]] = None,
    ) -> str:
        if not self.voice_catalog:
            return ""

        normalized_language = SegmentUtils.normalize_language_code(language, fallback=self.content_language)
        available_locales = self._get_available_locales()
        candidate_locales = list(preferred_locales or [])
        candidate_locales.extend(self.LANGUAGE_LOCALE_PREFERENCES.get(normalized_language, []))

        for locale in candidate_locales:
            if locale in available_locales:
                return locale

        language_prefix = f"{normalized_language.lower()}-"
        dynamic_locales = sorted({
            locale for locale in available_locales
            if locale.lower().startswith(language_prefix)
        })
        return dynamic_locales[0] if dynamic_locales else ""

    def _build_voice_pools(self) -> tuple[List[str], List[str]]:
        pools = self._build_voice_pools_for_locale(self.target_locale)
        return pools["male"], pools["female"]

    def _build_voice_pools_for_locale(self, locale: str) -> Dict[str, List[str]]:
        if not self.voice_catalog or not locale:
            return {"male": [], "female": []}

        if locale in self.voice_pool_cache:
            return self.voice_pool_cache[locale]

        male_voices = [
            voice.get("ShortName")
            for voice in self.voice_catalog
            if voice.get("Locale") == locale and voice.get("Gender") == "Male"
        ]
        female_voices = [
            voice.get("ShortName")
            for voice in self.voice_catalog
            if voice.get("Locale") == locale and voice.get("Gender") == "Female"
        ]

        pools = {
            "male": [voice for voice in male_voices if voice],
            "female": [voice for voice in female_voices if voice],
        }
        self.voice_pool_cache[locale] = pools

        if pools["male"] or pools["female"]:
            logger.info(
                t(
                    "character.voice_catalog_pool_ready",
                    locale=locale,
                    male=len(pools["male"]),
                    female=len(pools["female"]),
                )
            )
        else:
            logger.warning(
                t(
                    "character.voice_catalog_locale_missing",
                    locale=locale,
                    fallback=self.fallback_voice,
                )
            )
        return pools

    def _select_narrator_voice(self) -> str:
        if self.FEMALE_VOICES:
            return self.FEMALE_VOICES[0]
        if self.MALE_VOICES:
            return self.MALE_VOICES[0]
        logger.warning(t("character.voice_fallback_narrator", voice=self.fallback_voice))
        return self.fallback_voice

    def _resolve_region_locales(self, region_hint: str, language: str) -> List[str]:
        if not config.VOICE_PREFER_REGION_MATCH:
            return []

        lowered = str(region_hint or "").lower()
        if not lowered or lowered == "unknown":
            return []

        for key, locales in self.REGION_LOCALE_HINTS.items():
            if key in lowered:
                return [
                    locale
                    for locale in locales
                    if self._extract_language_from_locale(locale) == language
                ]
        return []

    def _get_character_profile(self, character: Dict) -> Dict:
        return character.get("profile", {}) if isinstance(character.get("profile"), dict) else {}

    def _next_voice_from_pool(self, locale: str, gender: str) -> Optional[str]:
        pools = self._build_voice_pools_for_locale(locale)
        pool_gender = gender if gender in ("male", "female") else ("female" if pools["female"] else "male")
        pool = pools.get(pool_gender, [])
        if not pool:
            alternate = "male" if pool_gender == "female" else "female"
            pool = pools.get(alternate, [])
            pool_gender = alternate
        if not pool:
            return None

        indices = self.locale_voice_indices.setdefault(locale, {"male": 0, "female": 0})
        index = indices.get(pool_gender, 0)
        voice = pool[index % len(pool)]
        indices[pool_gender] = index + 1
        return voice

    def _resolve_segment_locale(self, segment_language: str, character: Optional[Dict] = None) -> str:
        normalized_language = SegmentUtils.normalize_language_code(
            segment_language,
            fallback=self.content_language,
        )
        preferred_locales: List[str] = []
        if character:
            profile = self._get_character_profile(character)
            preferred_locales.extend(
                self._resolve_region_locales(profile.get("region_hint", "unknown"), normalized_language)
            )

        return self._resolve_language_locale(normalized_language, preferred_locales=preferred_locales)

    def _find_character_entry(self, speaker: str, character_template: Dict) -> Optional[Dict]:
        for char in character_template.get("characters", []):
            if speaker == char.get("name"):
                return char
        return None

    def resolve_character_voice(
        self,
        character: Dict,
        preferred_language: Optional[str] = None,
        fallback_voice: Optional[str] = None,
    ) -> str:
        voice_preferences = character.get("voice_preferences", {})
        by_language = voice_preferences.get("by_language", {}) if isinstance(voice_preferences, dict) else {}
        language = SegmentUtils.normalize_language_code(
            preferred_language,
            fallback=self.content_language,
        )

        if isinstance(by_language, dict) and by_language.get(language):
            return str(by_language[language]).strip()

        explicit_voice = str(character.get("voice", "")).strip()
        if explicit_voice and self._extract_language_from_locale(self._extract_locale_from_voice(explicit_voice)) == language:
            return explicit_voice

        locale = self._resolve_segment_locale(language, character)
        if locale:
            selected = self._next_voice_from_pool(locale, character.get("gender", "unknown"))
            if selected:
                return selected

        voice_fallback = fallback_voice or explicit_voice or self.fallback_voice
        logger.warning(
            t(
                "character.voice_fallback_gender",
                name=character.get("name", "unknown"),
                gender=character.get("gender", "unknown"),
                voice=voice_fallback,
            )
        )
        return voice_fallback

    def assign_voices(self, characters: List[Dict]) -> List[Dict]:
        """
        Assign voices to the character list

        Args:
            characters: character list (generated from CharacterAnalyzer)

        Returns:
            character list with the voice field added
        """
        for char in characters:
            gender = char.get('gender', 'unknown')

            # If the voice field already exists (manually set by user), skip
            if 'voice' in char and char['voice']:
                logger.info(t("character.voice_already_set", name=char['name'], voice=char['voice']))
                continue

            char['voice'] = self.resolve_character_voice(char, preferred_language=self.content_language)
            if gender == 'male':
                logger.info(t("character.voice_assigned_male", name=char['name'], voice=char['voice']))
            elif gender == 'female':
                logger.info(t("character.voice_assigned_female", name=char['name'], voice=char['voice']))
            else:
                logger.info(t("character.voice_assigned_unknown", name=char['name'], voice=char['voice']))

        return characters

    def _get_male_voice(self, character_name: str) -> str:
        """Get the next male voice (cycling)"""
        if self.MALE_VOICES:
            voice = self.MALE_VOICES[self.male_index % len(self.MALE_VOICES)]
            self.male_index += 1
            return voice

        logger.warning(t("character.voice_fallback_gender", name=character_name, gender="male", voice=self.fallback_voice))
        return self.fallback_voice

    def get_voice_for_segment(self, segment: Dict, character_template: Dict) -> str:
        voice_override = str(segment.get("voice_override", "")).strip()
        if voice_override:
            return voice_override

        if segment.get("segment_type") in ("intro", "outro"):
            return config.TTS_VOICE

        speaker = str(segment.get("speaker", "narrator")).strip() or "narrator"
        segment_language = SegmentUtils.normalize_language_code(
            segment.get("language"),
            fallback=self.content_language,
        )

        if speaker == "narrator":
            narrator_voice = character_template.get("narrator", {}).get("voice", self.fallback_voice)
            narrator_language = self._extract_language_from_locale(self._extract_locale_from_voice(narrator_voice))
            if narrator_voice and narrator_language == segment_language:
                return narrator_voice
            narrator_entry = {
                "name": "narrator",
                "gender": "unknown",
                "voice": narrator_voice,
                "profile": character_template.get("narrator", {}).get("profile", {}),
                "voice_preferences": character_template.get("narrator", {}).get("voice_preferences", {}),
            }
            return self.resolve_character_voice(
                narrator_entry,
                preferred_language=segment_language,
                fallback_voice=narrator_voice,
            )

        character = self._find_character_entry(speaker, character_template)
        if not character:
            logger.warning(t("character.voice_not_found", speaker=speaker))
            return character_template.get('narrator', {}).get('voice', config.TTS_VOICE)

        return self.resolve_character_voice(
            character,
            preferred_language=segment_language,
            fallback_voice=character.get("voice") or self.fallback_voice,
        )

    def _get_female_voice(self, character_name: str) -> str:
        """Get the next female voice (cycling)"""
        if self.FEMALE_VOICES:
            voice = self.FEMALE_VOICES[self.female_index % len(self.FEMALE_VOICES)]
            self.female_index += 1
            return voice

        logger.warning(t("character.voice_fallback_gender", name=character_name, gender="female", voice=self.fallback_voice))
        return self.fallback_voice

    def _get_unknown_voice(self, character_name: str) -> str:
        if self.MALE_VOICES:
            return self._get_male_voice(character_name)
        if self.FEMALE_VOICES:
            return self._get_female_voice(character_name)
        logger.warning(
            t("character.voice_fallback_gender", name=character_name, gender="unknown", voice=self.fallback_voice)
        )
        return self.fallback_voice

    @staticmethod
    def create_character_template(
        characters: List[Dict],
        novel_id: str,
        novel_title: str,
        narrator_voice: Optional[str] = None
    ) -> Dict:
        """
        Create the character voice cast template

        Args:
            characters: character list (voices already assigned)
            novel_id: novel ID
            novel_title: novel title

        Returns:
            character voice cast template (JSON format)
        """
        narrator = VoiceAssigner._get_narrator_metadata()

        return {
            "novel_id": novel_id,
            "novel_title": novel_title,
            "total_characters": len(characters),
            "characters": [
                {
                    "name": char['name'],
                    "aliases": char.get('aliases', []),
                    "gender": char.get('gender', 'unknown'),
                    "voice": char.get('voice', config.TTS_VOICE),
                    "description": char.get('description', ''),
                    "personality": char.get('personality', []),
                    "profile": char.get('profile', {
                        "age_group": "unknown",
                        "occupation": "unknown",
                        "region_hint": "unknown",
                        "accent_preference": "unknown",
                        "speech_style": [],
                    }),
                    "voice_preferences": char.get('voice_preferences', {
                        "default": char.get('voice', config.TTS_VOICE),
                        "by_language": {},
                    }),
                    "appearance_count": char.get('appearance_count', 0),
                    "first_chapter": char.get('first_chapter', 0),
                    "last_chapter": char.get('last_chapter', 0)
                }
                for char in characters
            ],
            "narrator": {
                "name": narrator["name"],
                "voice": narrator_voice or config.TTS_VOICE,
                "personality": narrator["personality"],
                "profile": {
                    "age_group": "unknown",
                    "occupation": "narrator",
                    "region_hint": "unknown",
                    "accent_preference": "standard",
                    "speech_style": ["narration", "clear"],
                },
                "voice_preferences": {
                    "default": narrator_voice or config.TTS_VOICE,
                    "by_language": {},
                },
            }
        }
    
    @staticmethod
    def get_voice_for_speaker(speaker: str, character_template: Dict) -> str:
        """
        Get the voice for a speaker

        Args:
            speaker: speaker name (or "narrator")
            character_template: character voice cast template

        Returns:
            voice name
        """
        if speaker == "narrator":
            return character_template.get('narrator', {}).get('voice', config.TTS_VOICE)

        # Look up the character
        for char in character_template.get('characters', []):
            if speaker == char['name']:
                return char.get('voice', config.TTS_VOICE)

        # Not found, use the narrator voice
        logger.warning(t("character.voice_not_found", speaker=speaker))
        return character_template.get('narrator', {}).get('voice', config.TTS_VOICE)

