"""Core task-domain constants and validation helpers."""

from __future__ import annotations

from typing import Final

TASK_STATUSES: Final = (
    "pending",
    "queued",
    "running",
    "paused",
    "succeeded",
    "failed",
    "canceled",
    "removed",
)

TERMINAL_STATUSES: Final = ("succeeded", "failed", "canceled", "removed")

# Contract transitions. Controlled reopen operations are exposed as explicit
# store methods instead of being accepted by update_status().
ALLOWED_TRANSITIONS: Final[dict[str, frozenset[str]]] = {
    "pending": frozenset({"queued", "removed"}),
    "queued": frozenset({"running", "removed"}),
    "running": frozenset({"succeeded", "failed", "canceled", "paused", "removed"}),
    "paused": frozenset({"queued", "removed"}),
    "failed": frozenset({"queued", "removed"}),
    "succeeded": frozenset({"removed"}),
    "canceled": frozenset({"removed"}),
    "removed": frozenset(),
}


class TaskNotFoundError(LookupError):
    def __init__(self, task_id: str) -> None:
        super().__init__(f"Task not found: {task_id}")
        self.task_id = task_id


class InvalidTransitionError(ValueError):
    def __init__(self, task_id: str, current: str, target: str) -> None:
        super().__init__(
            f"Invalid task transition for {task_id}: {current} -> {target}"
        )
        self.task_id = task_id
        self.current = current
        self.target = target


def ensure_transition(task_id: str, current: str, target: str) -> None:
    """Raise when a status transition is outside the task contract."""
    if target not in ALLOWED_TRANSITIONS.get(current, frozenset()):
        raise InvalidTransitionError(task_id, current, target)
