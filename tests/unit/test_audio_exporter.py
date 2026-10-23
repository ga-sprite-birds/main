"""
Tests for source-based output directory naming.
"""

import sys
from pathlib import Path

import pytest

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import config  # noqa: E402
from ga_birds.Audio import AudioExporter  # noqa: E402


@pytest.mark.unit
def test_source_stem_removes_extension_and_upload_prefix():
    assert AudioExporter.get_source_stem("example_book.md") == "example_book"
    assert AudioExporter.get_source_stem(
        "0123456789abcdef0123456789abcdef_example_book.md"
    ) == "example_book"
    assert AudioExporter.get_source_stem("plain_name") == "plain_name"
    assert AudioExporter.get_source_stem("../../evil.md") == "evil"
    assert AudioExporter.get_source_stem("") is None


@pytest.mark.unit
def test_front_matter_uses_zero_prefix_and_normalized_title(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_FRONT_MATTER_MARKERS", ["导读", "前言"])
    exporter = AudioExporter()
    exporter.strategy = "by_role"

    for title, expected in (
        ("第0章 导读篇", "000-导读篇.mp3"),
        ("前言", "000-前言篇.mp3"),
    ):
        output = exporter.get_output_path(
            index=1,
            title=title,
            role="default",
            custom_base_path=str(tmp_path),
            source_name="book.md",
        )
        assert output.name == expected

    # A normal chapter keeps its existing sequence and title.
    normal = exporter.get_output_path(
        index=2,
        title="第1章 示例章节",
        role="default",
        custom_base_path=str(tmp_path),
        source_name="book.md",
    )
    assert normal.name.startswith("002-第1章")

    # A chapter that merely mentions 导读 is not front matter.
    assert AudioExporter.get_filename_parts(
        1, "第1章 开篇导读示例"
    ) == (1, "第1章 开篇导读示例")


@pytest.mark.unit
def test_single_voice_output_is_inside_source_directory(tmp_path):
    exporter = AudioExporter()
    exporter.strategy = "by_role"

    output = exporter.get_output_path(
        index=1,
        title="第一章",
        role="default",
        custom_base_path=str(tmp_path),
        source_name="0123456789abcdef0123456789abcdef_example_book.md",
    )

    assert output.parent == tmp_path / "example_book"
    assert output.name.startswith("001-")


@pytest.mark.unit
def test_multi_voice_output_keeps_role_directory(tmp_path):
    exporter = AudioExporter()
    exporter.strategy = "by_role"

    output = exporter.get_output_path(
        index=1,
        title="第一章",
        role="multi",
        custom_base_path=str(tmp_path),
        source_name="example_book.md",
    )

    assert output.parent == tmp_path / "example_book" / "multi"
    assert output.name.startswith("001-")


@pytest.mark.unit
def test_front_matter_markers_are_configurable(monkeypatch):
    monkeypatch.setattr(config, "OUTPUT_FRONT_MATTER_MARKERS", ["序言"])

    assert AudioExporter.get_filename_parts(1, "序言") == (0, "序言篇")
    assert AudioExporter.get_filename_parts(2, "第1章 示例章节") == (
        2,
        "第1章 示例章节",
    )
