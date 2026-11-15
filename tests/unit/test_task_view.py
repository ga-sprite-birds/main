"""task_view 的进度口径：只生成勾选章节时按本次目标计算。"""

from __future__ import annotations

import pytest

from models.task import task_view


def _task(**overrides):
    task = {
        "task_id": "t-1",
        "type": "audio",
        "status": "running",
        "phase": "generating",
        "total_chapters": 31,
        "completed_chapters": 3,
        "params": {},
    }
    task.update(overrides)
    return task


def _chapter(index: int, status: str = "pending"):
    return {
        "chapter_index": index,
        "title": f"第{index}章",
        "status": status,
        "audio_path": None,
        "error": None,
        "started_at": None,
        "finished_at": None,
    }


@pytest.mark.unit
def test_full_generation_keeps_book_wide_progress():
    chapters = [_chapter(i, "succeeded" if i <= 3 else "pending") for i in range(1, 32)]
    view = task_view(_task(), chapters)

    assert view["total_chapters"] == 31
    assert view["target_chapters"] == 31
    assert view["target_completed_chapters"] == 3
    assert view["progress"] == pytest.approx(3 / 31)


@pytest.mark.unit
def test_selected_generation_progress_uses_target_not_book_total():
    """勾选 23 章生成时，分母必须是 23 而不是全书 31。"""
    selected = list(range(1, 24))
    task = _task(params={"generation": {"chapter_indexes": selected}})
    chapters = [_chapter(i, "succeeded" if i in (1, 2, 3) else "pending") for i in range(1, 32)]

    view = task_view(task, chapters)

    assert view["total_chapters"] == 31
    assert view["completed_chapters"] == 3
    assert view["target_chapters"] == 23
    assert view["target_completed_chapters"] == 3
    assert view["progress"] == pytest.approx(3 / 23)


@pytest.mark.unit
def test_selected_generation_completed_subset_reaches_full_progress():
    """只生成第 9、10 章且都成功后，进度应是 2/2 = 100%。"""
    task = _task(
        params={"generation": {"chapter_indexes": [9, 10]}},
        completed_chapters=2,
    )
    chapters = [_chapter(i, "succeeded" if i in (9, 10) else "pending") for i in range(1, 32)]

    view = task_view(task, chapters)

    assert view["target_chapters"] == 2
    assert view["target_completed_chapters"] == 2
    assert view["progress"] == 1


@pytest.mark.unit
def test_completed_outside_selection_does_not_inflate_target_progress():
    """之前生成的其它章节不计入本次目标的分子。"""
    task = _task(
        params={"generation": {"chapter_indexes": [2, 3]}},
        completed_chapters=2,  # 第 1、2 章成功，但只有第 2 章在本次选集里
    )
    chapters = [_chapter(i, "succeeded" if i in (1, 2) else "pending") for i in range(1, 32)]

    view = task_view(task, chapters)

    assert view["target_chapters"] == 2
    assert view["target_completed_chapters"] == 1
    assert view["progress"] == 0.5


@pytest.mark.unit
def test_list_view_without_chapters_keeps_book_wide_progress():
    """列表视图没有章节明细，progress 仍按全书口径，避免分子分母混用。"""
    task = _task(params={"generation": {"chapter_indexes": [1, 2, 3]}})

    view = task_view(task, None)

    assert view["progress"] == pytest.approx(3 / 31)
    assert view["target_chapters"] == 3
