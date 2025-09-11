from __future__ import annotations

from enum import Enum
from typing import Optional


class Status(Enum):
    """Standardized task status values."""

    TODO = "todo"
    IN_PROGRESS = "in-progress"
    UNDER_REVIEW = "under-review"
    BLOCKED = "blocked"
    DONE = "done"

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
            "todo": Status.TODO,
            "to-do": Status.TODO,
            "in-progress": Status.IN_PROGRESS,
            "inprogress": Status.IN_PROGRESS,
            "under-review": Status.UNDER_REVIEW,
            "review": Status.UNDER_REVIEW,
            "pending-review": Status.UNDER_REVIEW,
            "blocked": Status.BLOCKED,
            "done": Status.DONE,
            "complete": Status.DONE,
            "completed": Status.DONE,
        }

        return alias_map.get(normalized)


__all__ = ["Status"]


