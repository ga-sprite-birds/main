"""
GA Sprite Birds - Audio Exporter
Responsible for saving audio files and path management

Version: v1.0
Dev team: Tiger
"""

import re
from pathlib import Path
from typing import Optional
from datetime import datetime

from pydub import AudioSegment
from loguru import logger

import config
from ga_birds.Common.i18n import t
from system.config import PROJECT_ROOT
from system.paths import PathSafetyError, ensure_under, safe_filename


class AudioExporter:
    """Audio exporter"""

    def __init__(self):
        """Initialize the audio exporter"""
        self.base_path = Path(config.OUTPUT_BASE_PATH)
        self.strategy = config.OUTPUT_STRATEGY
        self.format = config.OUTPUT_FORMAT
        self.bitrate = config.OUTPUT_BITRATE
        self.filename_template = config.OUTPUT_FILENAME_TEMPLATE

        # Ensure the output directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)

        logger.info(t("audio.exporter_initialized", path=self.base_path, strategy=self.strategy))

    def get_output_path(
        self,
        index: int,
        title: str,
        role: Optional[str] = None,
        custom_base_path: Optional[str] = None,
        source_name: Optional[str] = None
    ) -> Path:
        """
        Get the output file path

        Args:
            index: chapter number
            title: chapter title
            role: character name
            custom_base_path: custom base path (overridden by API parameter)
            source_name: uploaded or specified source filename; its stem becomes
                         a subdirectory under the output base

        Returns:
            output file path
        """
        # Use custom path or default path. Per-task overrides must stay under
        # the configured output root; resolve symlinks before comparing.
        output_root = self.base_path.expanduser().resolve(strict=False)
        if custom_base_path:
            base = Path(custom_base_path).expanduser()
            if not base.is_absolute():
                base = PROJECT_ROOT / base
        else:
            base = output_root
        base = base.resolve(strict=False)
        try:
            base.relative_to(output_root)
        except ValueError as exc:
            raise PathSafetyError(
                f"Output path is outside OUTPUT_BASE_PATH: {base}"
            ) from exc

        # Keep each book in its own directory, even when the user supplies a
        # custom output base such as "abc".
        source_stem = self.get_source_stem(source_name)
        if source_stem:
            source_stem = self._sanitize_filename(source_stem)
            safe_filename(source_stem)
            base = base / source_stem

        # Determine subdirectory based on strategy. Single-voice output does
        # not need the redundant "default" directory.
        if self.strategy == "by_role":
            subdir = base / safe_filename(role) if role and role != "default" else base
        elif self.strategy == "by_model":
            subdir = base / "edge-tts"
        elif self.strategy == "by_date":
            date_str = datetime.now().strftime("%Y%m%d")
            subdir = base / date_str
        else:
            subdir = base

        # Generate filename. Front matter uses 000, but later chapter numbers
        # keep their existing sequence.
        filename_index, filename_title = self.get_filename_parts(index, title)
        filename = self.filename_template.format(
            index=filename_index,
            title=self._sanitize_filename(filename_title),
            role=role or "default",
            date=datetime.now().strftime("%Y%m%d"),
            format=self.format
        )
        safe_filename(filename)

        output_path = (subdir / filename).resolve(strict=False)
        ensure_under(output_root, output_path)

        # Ensure subdirectory exists only after the path is validated.
        subdir.mkdir(parents=True, exist_ok=True)
        logger.debug(t("audio.output_path_generated", path=output_path))

        return output_path

    @staticmethod
    def _strip_chapter_prefix(title: str) -> str:
        return re.sub(
            r"^第[0-9零一二三四五六七八九十百千]+章[\s:：、,，.．-]*",
            "",
            (title or "").strip(),
        )

    @classmethod
    def front_matter_marker(cls, title: str) -> Optional[str]:
        """Return the matched front-matter marker for a title, if any."""
        clean = cls._strip_chapter_prefix(title)
        for marker in config.OUTPUT_FRONT_MATTER_MARKERS:
            if marker and clean.startswith(marker):
                return marker
        return None

    @classmethod
    def get_filename_parts(cls, index: int, title: str):
        """Return the numeric prefix and title used in the output filename."""
        marker = cls.front_matter_marker(title)
        if marker is not None:
            canonical = marker if marker.endswith("篇") else f"{marker}篇"
            return 0, canonical
        return index, title

    @classmethod
    def display_index_map(cls, chapters) -> dict:
        """Map task chapter_index -> display index for filenames and intros.

        Front matter (导读/前言/...) is 0; the remaining chapters are numbered
        1..N in reading order, so 导读 = 000, first chapter = 001, and so on.
        The task's own chapter_index is left untouched.
        """
        mapping: dict[int, int] = {}
        counter = 0
        for chapter in chapters:
            index = int(chapter["chapter_index"])
            title = chapter.get("title") or ""
            if cls.front_matter_marker(title) is not None:
                mapping[index] = 0
            else:
                counter += 1
                mapping[index] = counter
        return mapping

    @staticmethod
    def get_source_stem(source_name: Optional[str]) -> Optional[str]:
        """Return a safe book directory name from a source filename."""
        if not source_name:
            return None

        name = Path(str(source_name).replace("\\", "/")).name
        # Uploaded files are stored as "<uuid-hex>_<original name>".
        name = re.sub(r"^[0-9a-fA-F]{32}_", "", name)
        stem = Path(name).stem.strip().rstrip(". ")
        if not stem or stem in {".", ".."}:
            return None

        stem = AudioExporter._sanitize_filename(stem).strip().rstrip(". ")
        return stem or None

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """
        Sanitize the filename by removing illegal characters

        Args:
            filename: original filename

        Returns:
            sanitized filename
        """
        # Remove or replace illegal characters
        illegal_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in illegal_chars:
            filename = filename.replace(char, '_')
        # Remove control characters (including newlines) that could break logs
        # or generated ffmpeg concat lists.
        filename = re.sub(r"[\x00-\x1f\x7f]", "_", filename)

        # Limit length
        max_length = 100
        if len(filename) > max_length:
            filename = filename[:max_length]

        return filename

    def convert_format(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        target_format: Optional[str] = None,
        bitrate: Optional[int] = None
    ) -> str:
        """
        Convert audio format

        Args:
            input_path: input file path
            output_path: output file path (auto-generated if None)
            target_format: target format (uses configured format if None)
            bitrate: bitrate (uses configured bitrate if None)

        Returns:
            output file path
        """
        target_format = target_format or self.format
        bitrate = bitrate or self.bitrate

        # Auto-generate output path if not specified
        if output_path is None:
            input_file = Path(input_path)
            output_path = str(input_file.with_suffix(f".{target_format}"))

        logger.info(t("audio.converting_format", input=input_path, output=output_path))

        try:
            # Load audio
            audio = AudioSegment.from_file(input_path)

            # Export to target format
            audio.export(
                output_path,
                format=target_format,
                bitrate=f"{bitrate}k"
            )

            logger.info(t("audio.conversion_complete", path=output_path))
            return output_path
        except Exception as e:
            logger.error(t("audio.conversion_failed", error=e))
            raise

    def merge_audio_files(
        self,
        input_paths: list[str],
        output_path: str,
        crossfade: int = 0
    ) -> str:
        """
        Merge multiple audio files

        Args:
            input_paths: list of input file paths
            output_path: output file path
            crossfade: crossfade duration in milliseconds

        Returns:
            output file path
        """
        logger.info(t("audio.merge_start", count=len(input_paths)))

        try:
            # Load the first audio
            combined = AudioSegment.from_file(input_paths[0])

            # Merge the remaining audio files in sequence
            for path in input_paths[1:]:
                audio = AudioSegment.from_file(path)
                if crossfade > 0:
                    combined = combined.append(audio, crossfade=crossfade)
                else:
                    combined = combined + audio

            # Export the merged audio
            combined.export(
                output_path,
                format=self.format,
                bitrate=f"{self.bitrate}k"
            )

            logger.info(t("audio.merge_complete", path=output_path))
            return output_path
        except Exception as e:
            logger.error(t("audio.merge_failed", error=e))
            raise

