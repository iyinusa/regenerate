"""Base Task Handler.

Base class for all task handlers with common functionality.
"""

import logging
from typing import Dict, Any
from abc import ABC, abstractmethod

from app.services.orchestrator.models import Task, TaskPlan

logger = logging.getLogger(__name__)


class BaseTaskHandler(ABC):
    """Base class for task handlers."""
    
    def __init__(self, genai_client, broadcast_callback):
        """Initialize the handler.
        
        Args:
            genai_client: Gemini API client
            broadcast_callback: Callback function for broadcasting updates
        """
        self.genai_client = genai_client
        self.broadcast_callback = broadcast_callback
    
    @abstractmethod
    async def execute(self, job_id: str, plan: TaskPlan, task: Task) -> Dict[str, Any]:
        """Execute the task.
        
        Args:
            job_id: The job ID
            plan: The task plan
            task: The task to execute
            
        Returns:
            Task execution result
        """
        pass
    
    async def update_progress(self, job_id: str, task: Task) -> None:
        """Update task progress.
        
        Args:
            job_id: The job ID
            task: The task being updated
        """
        await self.broadcast_callback(job_id, "task_progress", task.to_dict())
