from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
from core.enum.status import Status




@dataclass(slots=True)
class Task:
    """Task entity.

    This entity is compatible with task fields in features/demo.yaml:
    - UUID -> uuid
    - Name -> name
    - Prompt -> description
    - DockerImage -> docker_image
    - CommitID -> commit_id
    - DependencyTaskID -> dependency_task_id
    - Status -> status

    Provides from_dict/to_dict to convert between the original YAML schema and
    the internal naming, ensuring zero breakage.
    """

    uuid: str
    name: str
    description: Optional[str] = None
    docker_image: Optional[str] = None
    commit_id: Optional[str] = None
    dependency_task_id: Optional[str] = None
    status: Optional[Status] = None

    @staticmethod
    def from_dict(raw: Dict[str, Any]) -> "Task":
        """Construct a Task from a dict that uses the original YAML keys."""
        return Task(
            uuid=str(raw.get("uuid") or raw.get("UUID") or ""),
            name=str(raw.get("Name") or raw.get("name") or ""),
            description=raw.get("Prompt") or raw.get("Description") or raw.get("description"),
            docker_image=raw.get("DockerImage") or raw.get("docker_image"),
            commit_id=raw.get("CommitID") or raw.get("commit_id"),
            dependency_task_id=raw.get("DependencyTaskID") or raw.get("dependency_task_id"),
            status=Status.parse(raw.get("Status") or raw.get("status")),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Export to a dict compatible with the YAML consumed by main.py."""
        return {
            "uuid": self.uuid,
            "Name": self.name,
            "Prompt": self.description,
            "DockerImage": self.docker_image,
            "CommitID": self.commit_id,
            "DependencyTaskID": self.dependency_task_id,
            "Status": self.status.value if self.status else None,
        }


__all__ = ["Task", "Status"]


