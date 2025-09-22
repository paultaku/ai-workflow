from __future__ import annotations

from enum import Enum
from typing import Optional


class Status(Enum):
    """Standardized task status values."""

    PENDING = "pending"
    WORK_IN_PROGRESS = "work-in-progress"
    DONE = "done"
    FAILED = "failed"
    # Legacy status values for backward compatibility
    TODO = "todo"
    UNDER_REVIEW = "under-review"
    BLOCKED = "blocked"

    @staticmethod
    def parse(value: Optional[str]) -> Optional["Status"]:
        """Parse various textual representations into a Status enum.

        Accepts common aliases and different separators/cases. Returns None if
        the input is empty or unrecognized.
        """
        if not value:
            return None
        normalized = value.strip().lower().replace("_", "-").replace(" ", "-")

        alias_map = {
            # New primary status values
            "pending": Status.PENDING,
            
            "done": Status.DONE,
            "complete": Status.DONE,
            "completed": Status.DONE,
            "failed": Status.FAILED,
            "error": Status.FAILED,
            "failure": Status.FAILED,
            # Legacy status values for backward compatibility
            "todo": Status.TODO,
            "to-do": Status.TODO,
            "work-in-progress": Status.WORK_IN_PROGRESS,
            "workinprogress": Status.WORK_IN_PROGRESS,
            "wip": Status.WORK_IN_PROGRESS,
            "in-progress": Status.WORK_IN_PROGRESS,
            "inprogress": Status.WORK_IN_PROGRESS,
            "under-review": Status.UNDER_REVIEW,
            "review": Status.UNDER_REVIEW,
            "pending-review": Status.UNDER_REVIEW,
            "blocked": Status.BLOCKED,
        }

        return alias_map.get(normalized)


__all__ = ["Status"]


