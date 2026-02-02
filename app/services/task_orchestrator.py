"""Task Orchestrator Service for Chain of Thought (CoT) Task Management.

DEPRECATED: This file is maintained for backward compatibility only.
All new code should import from app.services.orchestrator instead.

The orchestrator has been refactored into a professional separation of concerns structure:
- app.services.orchestrator.models: Data models (Task, TaskPlan, TaskStatus, TaskType)
- app.services.orchestrator.handlers: Task execution handlers
- app.services.orchestrator.utils: Helper functions (parsing, validation)
- app.services.orchestrator.orchestrator: Main TaskOrchestrator class
"""

# Re-export from new structure for backward compatibility
from app.services.orchestrator.models import Task, TaskPlan, TaskStatus, TaskType
from app.services.orchestrator.orchestrator import TaskOrchestrator, task_orchestrator

__all__ = [
    'Task',
    'TaskPlan',
    'TaskStatus',
    'TaskType',
    'TaskOrchestrator',
    'task_orchestrator',
]
