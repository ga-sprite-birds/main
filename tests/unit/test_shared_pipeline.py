"""
Tests for the shared chapter loader and duplicate-file handling.
"""

import sys
from pathlib import Path

import pytest

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import config
from ga_birds.Audio.chapter_generator import resolve_output_path
from ga_birds.Common.chapter_loader import load_chapters


@pytest.mark.unit
def test_load_chapters_reads_markdown(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CHAPTER_NORMALIZE_ENABLED", True)
    monkeypatch.setattr(config, "CHAPTER_MIN_LENGTH", 10)

    source = tmp_path / "book.md"
    source.write_text(
        "# 第一章 开始\n\n" + "这是第一章的正文。" * 20,
        encoding="utf-8"
    )

    chapters = load_chapters(str(source))
    assert len(chapters) == 1
    assert chapters[0].title.startswith("第一章")


@pytest.mark.unit
def test_resolve_output_path_skip_keeps_existing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_DUPLICATE_HANDLING", "skip")
    existing = tmp_path / "chapter.mp3"
    existing.write_bytes(b"audio")

    assert resolve_output_path(existing) is None
    assert existing.read_bytes() == b"audio"


@pytest.mark.unit
def test_resolve_output_path_rename_returns_new_name(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_DUPLICATE_HANDLING", "rename")
    existing = tmp_path / "chapter.mp3"
    existing.write_bytes(b"audio")

    resolved = resolve_output_path(existing)
    assert resolved != existing
    assert resolved.name == "chapter (1).mp3"


@pytest.mark.unit
def test_resolve_output_path_overwrites_empty_file(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_DUPLICATE_HANDLING", "overwrite")
    empty = tmp_path / "chapter.mp3"
    empty.write_bytes(b"")

    resolved = resolve_output_path(empty)
    assert resolved == empty
    assert not empty.exists()
