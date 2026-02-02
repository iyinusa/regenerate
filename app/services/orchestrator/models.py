"""Task Orchestrator Models.

Data models for task orchestration including Task, TaskPlan, and status enums.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskType(str, Enum):
    """Types of tasks in the pipeline."""
    FETCH_PROFILE = "fetch_profile"
    ENRICH_PROFILE = "enrich_profile"
    AGGREGATE_HISTORY = "aggregate_history"
    STRUCTURE_JOURNEY = "structure_journey"
    GENERATE_TIMELINE = "generate_timeline"
    GENERATE_DOCUMENTARY = "generate_documentary"
    GENERATE_VIDEO = "generate_video"


@dataclass
class Task:
    """Represents a single task in the execution pipeline."""
    task_id: str
    task_type: TaskType
    name: str
    description: str
    order: int
    status: TaskStatus = TaskStatus.PENDING
    progress: int = 0
    message: str = ""
    dependencies: List[str] = field(default_factory=list)
    outputs: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_seconds: int = 30
    critical: bool = True
    retry_count: int = 0
    max_retries: int = 2

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for JSON serialization."""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "name": self.name,
            "description": self.description,
            "order": self.order,
            "status": self.status.value,
            "progress": self.progress,
            "message": self.message,
            "dependencies": self.dependencies,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "estimated_seconds": self.estimated_seconds,
            "critical": self.critical,
        }


@dataclass
class TaskPlan:
    """Represents an execution plan containing multiple tasks."""
    plan_id: str
    job_id: str
    source_url: str
    tasks: List[Task]
    options: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    progress: int = 0
    current_task_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    result_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert plan to dictionary for JSON serialization."""
        return {
            "plan_id": self.plan_id,
            "job_id": self.job_id,
            "source_url": self.source_url,
            "status": self.status.value,
            "progress": self.progress,
            "current_task_id": self.current_task_id,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "tasks": [task.to_dict() for task in self.tasks],
            "total_tasks": len(self.tasks),
            "completed_tasks": sum(1 for t in self.tasks if t.status == TaskStatus.COMPLETED),
        }
