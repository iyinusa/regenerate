"""Main Task Orchestrator.

Coordinates task execution with Chain of Thought planning.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable, Set

from google import genai

from app.core.config import settings
from app.services.orchestrator.models import Task, TaskPlan, TaskStatus, TaskType
from app.services.orchestrator.handlers.fetch_profile import FetchProfileHandler
from app.services.orchestrator.handlers.enrich_profile import EnrichProfileHandler
from app.services.orchestrator.handlers.journey_handlers import (
    AggregateHistoryHandler,
    StructureJourneyHandler,
    GenerateTimelineHandler,
    GenerateDocumentaryHandler,
)
from app.services.orchestrator.handlers.video import GenerateVideoHandler

logger = logging.getLogger(__name__)


class TaskOrchestrator:
    """Orchestrates task execution with Chain of Thought planning."""
    
    # Class-level storage for active plans
    _active_plans: Dict[str, TaskPlan] = {}
    _update_callbacks: Dict[str, Set[Callable]] = {}
    # Track plans that are currently executing to prevent duplicate execution
    _executing_plans: Set[str] = set()
    
    def __init__(self):
        """Initialize the task orchestrator."""
        self.genai_client = None
        
        if settings.ai_provider_api_key:
            try:
                self.genai_client = genai.Client(
                    api_key=settings.ai_provider_api_key,
                    http_options={'timeout': 600000}
                )
                logger.info("Task Orchestrator: Gemini client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
        
        # Initialize handlers
        self._init_handlers()
    
    def _init_handlers(self):
        """Initialize task handlers."""
        self.handlers = {
            TaskType.FETCH_PROFILE: FetchProfileHandler(self.genai_client, self._broadcast_update),
            TaskType.ENRICH_PROFILE: EnrichProfileHandler(self.genai_client, self._broadcast_update),
            TaskType.AGGREGATE_HISTORY: AggregateHistoryHandler(self.genai_client, self._broadcast_update),
            TaskType.STRUCTURE_JOURNEY: StructureJourneyHandler(self.genai_client, self._broadcast_update),
            TaskType.GENERATE_TIMELINE: GenerateTimelineHandler(self.genai_client, self._broadcast_update),
            TaskType.GENERATE_DOCUMENTARY: GenerateDocumentaryHandler(self.genai_client, self._broadcast_update),
            TaskType.GENERATE_VIDEO: GenerateVideoHandler(self.genai_client, self._broadcast_update),
        }
    
    def create_plan(self, job_id: str, source_url: str, options: Dict[str, Any] = None) -> TaskPlan:
        """Create an execution plan for the given source.
        
        Uses Chain of Thought reasoning to determine optimal task sequence.
        
        Args:
            job_id: Unique job identifier
            source_url: The source URL to process
            options: Processing options
            
        Returns:
            TaskPlan with ordered tasks
        """
        options = options or {}
        plan_id = f"plan_{uuid.uuid4().hex[:12]}"
        
        # Determine source type and create appropriate task chain
        tasks = self._create_task_chain(source_url, options)
        
        plan = TaskPlan(
            plan_id=plan_id,
            job_id=job_id,
            source_url=source_url,
            tasks=tasks,
            options=options,
        )
        
        # Store the plan
        self._active_plans[job_id] = plan
        
        logger.info(f"Created task plan {plan_id} with {len(tasks)} tasks for job {job_id}")
        return plan
    
    def _create_task_chain(self, source_url: str, options: Dict[str, Any]) -> List[Task]:
        """Create the chain of tasks based on source and options.
        
        Uses Chain of Thought reasoning to determine optimal task sequence.
        """
        tasks = []
        
        # Check if this is a specialized plan
        if options.get("generate_video_only"):
            tasks.append(Task(
                task_id="task_video_gen",
                task_type=TaskType.GENERATE_VIDEO,
                name="Generating Video Documentary",
                description="Generating video segments and stitching full documentary",
                order=1,
                estimated_seconds=120,
                critical=True,
                dependencies=[], 
            ))
            return tasks
        
        # Standard Profile Generation Flow
        
        # Task 1: Fetch Profile
        tasks.append(Task(
            task_id="task_001",
            task_type=TaskType.FETCH_PROFILE,
            name="Extracting Profile Data",
            description="Using Gemini 3 to fetch and analyze profile data",
            order=1,
            estimated_seconds=60,
            critical=True,
            dependencies=[],
        ))
        
        # Task 2: Enrich Profile
        tasks.append(Task(
            task_id="task_002",
            task_type=TaskType.ENRICH_PROFILE,
            name="Enriching Profile",
            description="Discovering and aggregating data from related sources",
            order=2,
            estimated_seconds=30,
            critical=False,
            dependencies=["task_001"],
        ))
        
        # Task 3: Aggregate History
        tasks.append(Task(
            task_id="task_003",
            task_type=TaskType.AGGREGATE_HISTORY,
            name="Aggregating History",
            description="Merging with existing profile history",
            order=3,
            estimated_seconds=25,
            critical=False,
            dependencies=["task_002"],
        ))
        
        # Task 4: Structure Journey
        tasks.append(Task(
            task_id="task_004",
            task_type=TaskType.STRUCTURE_JOURNEY,
            name="Structuring Journey",
            description="Transforming profile into compelling narrative",
            order=4,
            estimated_seconds=20,
            critical=False,
            dependencies=["task_003"],
        ))
        
        # Task 5: Generate Timeline
        tasks.append(Task(
            task_id="task_005",
            task_type=TaskType.GENERATE_TIMELINE,
            name="Generating Timeline",
            description="Creating interactive timeline visualization",
            order=5,
            estimated_seconds=20,
            critical=False,
            dependencies=["task_001", "task_004"], 
        ))
        
        # Task 6: Generate Documentary
        tasks.append(Task(
            task_id="task_006",
            task_type=TaskType.GENERATE_DOCUMENTARY,
            name="Creating Documentary",
            description="Crafting documentary narrative and video segments",
            order=6,
            estimated_seconds=20,
            critical=False,
            dependencies=["task_001", "task_004"], 
        ))
        
        return tasks
    
    async def execute_plan(self, job_id: str) -> None:
        """Execute the task plan for a job.
        
        Runs tasks in order, respecting dependencies, and broadcasts progress updates.
        Guards against duplicate execution of the same plan.
        """
        # Guard against duplicate execution
        if job_id in self._executing_plans:
            logger.warning(f"Plan {job_id} is already executing, skipping duplicate execution request")
            return
        
        plan = self._active_plans.get(job_id)
        if not plan:
            logger.error(f"No plan found for job {job_id}")
            return
        
        # Check if plan has already been executed
        if plan.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            logger.warning(f"Plan {job_id} has already been executed (status: {plan.status}), skipping")
            return
        
        # Mark plan as executing
        self._executing_plans.add(job_id)
        logger.info(f"Starting execution of plan {job_id}")
        
        plan.status = TaskStatus.RUNNING
        await self._broadcast_update(job_id, "plan_started", plan.to_dict())
        
        try:
            # Execute tasks in order
            for task in sorted(plan.tasks, key=lambda t: t.order):
                # Check dependencies
                if not self._dependencies_satisfied(plan, task):
                    logger.warning(f"Dependencies not met for task {task.task_id}, skipping")
                    task.status = TaskStatus.SKIPPED
                    continue
                
                # Execute the task
                plan.current_task_id = task.task_id
                await self._execute_task(job_id, plan, task)
                
                # Update overall progress
                completed = sum(1 for t in plan.tasks if t.status == TaskStatus.COMPLETED)
                plan.progress = int((completed / len(plan.tasks)) * 100)
                
                # Check for critical failure
                if task.status == TaskStatus.FAILED and task.critical:
                    logger.error(f"Critical task {task.task_id} failed, aborting plan")
                    plan.status = TaskStatus.FAILED
                    break
                elif task.status == TaskStatus.FAILED and not task.critical:
                    logger.warning(f"Non-critical task {task.task_id} failed, continuing")
            
            # Mark plan as completed if no critical failures
            if plan.status != TaskStatus.FAILED:
                plan.status = TaskStatus.COMPLETED
                plan.progress = 100
                plan.completed_at = datetime.utcnow()
            
            await self._broadcast_update(job_id, "plan_completed", plan.to_dict())
            
        except Exception as e:
            logger.error(f"Plan execution failed for job {job_id}: {e}")
            plan.status = TaskStatus.FAILED
            await self._broadcast_update(job_id, "plan_failed", {
                "error": str(e),
                "plan": plan.to_dict()
            })
        finally:
            # Always remove from executing set when done
            self._executing_plans.discard(job_id)
            logger.info(f"Finished execution of plan {job_id} (status: {plan.status})")
    
    async def _execute_task(self, job_id: str, plan: TaskPlan, task: Task) -> None:
        """Execute a single task."""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        task.message = "Starting..."
        
        await self._broadcast_update(job_id, "task_started", {
            "task": task.to_dict(),
            "plan_progress": plan.progress
        })
        
        try:
            # Get handler for task type
            handler = self.handlers.get(task.task_type)
            if not handler:
                raise Exception(f"No handler for task type: {task.task_type}")
            
            # Execute handler
            result = await handler.execute(job_id, plan, task)
            
            task.outputs = result
            task.status = TaskStatus.COMPLETED
            task.progress = 100
            task.completed_at = datetime.utcnow()
            task.message = "Completed successfully"
            
            # Store result in plan
            plan.result_data[task.task_type.value] = result
            
            logger.info(f"Task {task.task_id} completed successfully")
            
            await self._broadcast_update(job_id, "task_completed", {
                "task": task.to_dict(),
                "plan_progress": plan.progress
            })
            
        except Exception as e:
            logger.error(f"Task {task.task_id} failed: {e}")
            
            # Retry logic
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.message = f"Retrying ({task.retry_count}/{task.max_retries})..."
                await self._broadcast_update(job_id, "task_retrying", {
                    "task": task.to_dict(),
                    "plan_progress": plan.progress
                })
                await asyncio.sleep(2 ** task.retry_count)  # Exponential backoff
                await self._execute_task(job_id, plan, task)
            else:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                task.message = f"Failed: {str(e)}"
                await self._broadcast_update(job_id, "task_failed", {
                    "task": task.to_dict(),
                    "plan_progress": plan.progress
                })
    
    def _dependencies_satisfied(self, plan: TaskPlan, task: Task) -> bool:
        """Check if all dependencies for a task are satisfied."""
        for dep_id in task.dependencies:
            dep_task = next((t for t in plan.tasks if t.task_id == dep_id), None)
            if dep_task and dep_task.status not in [TaskStatus.COMPLETED, TaskStatus.SKIPPED]:
                return False
        return True
    
    # Update Broadcasting
    def register_callback(self, job_id: str, callback: Callable) -> None:
        """Register a callback for task updates."""
        if job_id not in self._update_callbacks:
            self._update_callbacks[job_id] = set()
        self._update_callbacks[job_id].add(callback)
    
    def unregister_callback(self, job_id: str, callback: Callable) -> None:
        """Unregister a callback."""
        if job_id in self._update_callbacks:
            self._update_callbacks[job_id].discard(callback)
    
    async def _broadcast_update(self, job_id: str, event_type: str, data: Any) -> None:
        """Broadcast update to all registered callbacks."""
        callbacks = self._update_callbacks.get(job_id, set())
        
        update = {
            "event": event_type,
            "job_id": job_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(update)
                else:
                    callback(update)
            except Exception as e:
                logger.error(f"Callback error for job {job_id}: {e}")
    
    # Plan Status
    def get_plan(self, job_id: str) -> Optional[TaskPlan]:
        """Get the plan for a job."""
        return self._active_plans.get(job_id)
    
    def get_plan_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a plan."""
        plan = self._active_plans.get(job_id)
        if plan:
            return plan.to_dict()
        return None


# Global orchestrator instance
task_orchestrator = TaskOrchestrator()
