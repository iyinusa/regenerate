"""Task Orchestrator Service for Chain of Thought (CoT) Task Management.

This service coordinates the execution of planned tasks for profile-to-journey
transformation, providing real-time updates via WebSocket connections.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, field, asdict

from google import genai
from google.genai import types

from app.core.config import settings
from app.prompts import (
    get_profile_extraction_prompt,
    get_journey_structuring_prompt,
    get_timeline_generation_prompt,
    get_documentary_narrative_prompt,
    PROFILE_EXTRACTION_SCHEMA,
    JOURNEY_STRUCTURE_SCHEMA,
    TIMELINE_SCHEMA,
    DOCUMENTARY_SCHEMA,
)

logger = logging.getLogger(__name__)


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


class TaskOrchestrator:
    """Orchestrates task execution with Chain of Thought planning."""
    
    # Class-level storage for active plans (replace with Redis in production)
    _active_plans: Dict[str, TaskPlan] = {}
    _update_callbacks: Dict[str, Set[Callable]] = {}
    
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
    
    def create_plan(self, job_id: str, source_url: str, options: Dict[str, Any] = None) -> TaskPlan:
        """Create an execution plan for the given source.
        
        This uses Chain of Thought reasoning to determine the optimal
        task sequence based on the source type and options.
        
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
        
        Args:
            source_url: Source URL to analyze
            options: Processing options
            
        Returns:
            List of Task objects in execution order
        """
        tasks = []
        
        # Task 1: Fetch Profile (always first)
        tasks.append(Task(
            task_id="task_001",
            task_type=TaskType.FETCH_PROFILE,
            name="Extracting Profile Data",
            description="Using Gemini 3 to fetch and analyze profile data from the source URL",
            order=1,
            estimated_seconds=60,
            critical=True,
            dependencies=[],
        ))
        
        # Task 2: Enrich Profile (discover and aggregate additional sources)
        tasks.append(Task(
            task_id="task_002",
            task_type=TaskType.ENRICH_PROFILE,
            name="Enriching Profile",
            description="Discovering and aggregating data from related sources",
            order=2,
            estimated_seconds=30,
            critical=False,  # Can continue without enrichment
            dependencies=["task_001"],
        ))
        
        # Task 3: Aggregate History (if user has existing data)
        tasks.append(Task(
            task_id="task_003",
            task_type=TaskType.AGGREGATE_HISTORY,
            name="Aggregating History",
            description="Merging with existing profile history for comprehensive view",
            order=3,
            estimated_seconds=25,
            critical=False,
            dependencies=["task_002"],
        ))
        
        # Task 4: Structure Journey (main transformation)
        tasks.append(Task(
            task_id="task_004",
            task_type=TaskType.STRUCTURE_JOURNEY,
            name="Structuring Journey",
            description="Transforming profile data into a compelling narrative structure",
            order=4,
            estimated_seconds=20,
            critical=False,  # Non-critical: enhancement feature
            dependencies=["task_003"],
        ))
        
        # Task 5: Generate Timeline
        tasks.append(Task(
            task_id="task_005",
            task_type=TaskType.GENERATE_TIMELINE,
            name="Generating Timeline",
            description="Creating interactive timeline visualization data",
            order=5,
            estimated_seconds=20,
            critical=False,  # Non-critical: enhancement feature
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
            critical=False,  # Non-critical: enhancement feature
            dependencies=["task_001", "task_004"], 
        ))
        
        return tasks
    
    async def execute_plan(self, job_id: str) -> None:
        """Execute the task plan for a job.
        
        Runs tasks in order, respecting dependencies, and broadcasts
        progress updates via registered callbacks.
        
        Args:
            job_id: The job ID to execute
        """
        plan = self._active_plans.get(job_id)
        if not plan:
            logger.error(f"No plan found for job {job_id}")
            return
        
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
                    logger.error(f"Critical task {task.task_id} ({task.task_type.value}) failed, aborting plan")
                    plan.status = TaskStatus.FAILED
                    break
                elif task.status == TaskStatus.FAILED and not task.critical:
                    logger.warning(f"Non-critical task {task.task_id} ({task.task_type.value}) failed, continuing with plan")
                    # Continue execution for non-critical failures
            
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
    
    async def _execute_task(self, job_id: str, plan: TaskPlan, task: Task) -> None:
        """Execute a single task.
        
        Args:
            job_id: The job ID
            plan: The task plan
            task: The task to execute
        """
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        task.message = "Starting..."
        
        await self._broadcast_update(job_id, "task_started", {
            "task": task.to_dict(),
            "plan_progress": plan.progress
        })
        
        try:
            # Route to appropriate handler based on task type
            handler = self._get_task_handler(task.task_type)
            result = await handler(job_id, plan, task)
            
            task.outputs = result
            task.status = TaskStatus.COMPLETED
            task.progress = 100
            task.completed_at = datetime.utcnow()
            task.message = "Completed successfully"
            
            # Store result in plan (even if it contains errors/warnings)
            plan.result_data[task.task_type.value] = result
            
            # Log result for debugging
            if isinstance(result, dict) and ('error' in result or 'warning' in result):
                logger.warning(f"Task {task.task_id} completed with issues: {result.get('error') or result.get('warning')}")
            else:
                logger.info(f"Task {task.task_id} completed successfully with result keys: {list(result.keys()) if isinstance(result, dict) else 'non-dict result'}")
            
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
                await self._broadcast_update(job_id, "task_retrying", task.to_dict())
                await asyncio.sleep(2 ** task.retry_count)  # Exponential backoff
                await self._execute_task(job_id, plan, task)
            else:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                task.message = f"Failed: {str(e)}"
                await self._broadcast_update(job_id, "task_failed", task.to_dict())
    
    def _get_task_handler(self, task_type: TaskType) -> Callable:
        """Get the handler function for a task type."""
        handlers = {
            TaskType.FETCH_PROFILE: self._handle_fetch_profile,
            TaskType.ENRICH_PROFILE: self._handle_enrich_profile,
            TaskType.AGGREGATE_HISTORY: self._handle_aggregate_history,
            TaskType.STRUCTURE_JOURNEY: self._handle_structure_journey,
            TaskType.GENERATE_TIMELINE: self._handle_generate_timeline,
            TaskType.GENERATE_DOCUMENTARY: self._handle_generate_documentary,
            TaskType.GENERATE_VIDEO: self._handle_generate_video,
        }
        return handlers.get(task_type, self._handle_unknown)
    
    def _dependencies_satisfied(self, plan: TaskPlan, task: Task) -> bool:
        """Check if all dependencies for a task are satisfied."""
        for dep_id in task.dependencies:
            dep_task = next((t for t in plan.tasks if t.task_id == dep_id), None)
            if dep_task and dep_task.status not in [TaskStatus.COMPLETED, TaskStatus.SKIPPED]:
                return False
        return True
    
    # Task Handlers
    async def _handle_fetch_profile(self, job_id: str, plan: TaskPlan, task: Task) -> Dict[str, Any]:
        """Handle profile fetching task with LinkedIn-aware extraction.
        
        This method detects the source type and uses the appropriate extraction method:
        - LinkedIn (unauthenticated): Scrape HTML and pass to Gemini
        - LinkedIn (authenticated): Use OAuth API and pass to Gemini  
        - Other URLs: Use url_context tool directly
        """
        from app.services.linkedin_service import linkedin_service
        
        task.message = "Analysing profile source..."
        task.progress = 10
        await self._broadcast_update(job_id, "task_progress", task.to_dict())
        
        if not self.genai_client:
            raise Exception("Gemini client not initialized")
        
        source_url = plan.source_url
        guest_user_id = plan.options.get('guest_user_id')
        
        # Detect if this is a LinkedIn URL
        is_linkedin = linkedin_service.is_linkedin_url(source_url)
        
        if is_linkedin:
            return await self._handle_linkedin_profile(job_id, plan, task, source_url, guest_user_id)
        else:
            return await self._handle_standard_profile(job_id, plan, task, source_url)
    
    async def _handle_linkedin_profile(
        self, 
        job_id: str, 
        plan: TaskPlan, 
        task: Task, 
        source_url: str,
        guest_user_id: str
    ) -> Dict[str, Any]:
        """Handle LinkedIn profile extraction.
        
        Uses different strategies based on authentication status:
        1. Authenticated: Use LinkedIn OAuth API
        2. Unauthenticated: Scrape public HTML and pass to Gemini
        """
        from app.services.linkedin_service import linkedin_service
        from app.db.session import get_db
        from app.models.user import User
        from sqlalchemy import select
        
        task.message = "Detected LinkedIn profile, checking authentication..."
        task.progress = 10
        await self._broadcast_update(job_id, "task_progress", task.to_dict())
        
        linkedin_access_token = None
        
        # Check if user has LinkedIn OAuth credentials
        if guest_user_id:
            async for db in get_db():
                try:
                    result = await db.execute(
                        select(User).where(User.guest_id == guest_user_id)
                    )
                    user = result.scalar_one_or_none()
                    
                    if user and user.linkedin_access_token:
                        # Check if token is not expired
                        from datetime import datetime
                        if not user.linkedin_token_expires_at or user.linkedin_token_expires_at > datetime.utcnow():
                            linkedin_access_token = user.linkedin_access_token
                            logger.info(f"Using authenticated LinkedIn access for user {user.id}")
                except Exception as e:
                    logger.error(f"Error checking LinkedIn auth: {e}")
                finally:
                    break
        
        task.progress = 20
        task.message = "Preparing profile fetch..."
        await self._broadcast_update(job_id, "task_progress", task.to_dict())
        
        if linkedin_access_token:
            # Use authenticated LinkedIn API
            return await self._handle_linkedin_authenticated(
                job_id, task, source_url, linkedin_access_token
            )
        else:
            # Use unauthenticated scraping
            return await self._handle_linkedin_unauthenticated(
                job_id, task, source_url
            )
    
    async def _handle_linkedin_authenticated(
        self,
        job_id: str,
        task: Task,
        source_url: str,
        access_token: str
    ) -> Dict[str, Any]:
        """Handle LinkedIn profile with OAuth authentication.
        
        New Flow: Combine limited OAuth data with Google Search for rich profile.
        LinkedIn OAuth only provides: firstname, lastname, picture, member ID, email.
        """
        from app.services.linkedin_service import linkedin_service
        
        task.message = "Fetching LinkedIn OAuth data..."
        task.progress = 30
        await self._broadcast_update(job_id, "task_progress", task.to_dict())
        
        # Fetch limited profile data using OAuth
        linkedin_data = await linkedin_service.fetch_authenticated_profile(
            access_token=access_token,
            include_positions=False,  # Not available in limited API
            include_education=False,  # Not available in limited API
            include_skills=False  # Not available in limited API
        )
        
        if not linkedin_data.get("success"):
            # Fall back to unauthenticated if OAuth fails
            logger.warning(f"LinkedIn OAuth failed: {linkedin_data.get('error')}, falling back to search")
            return await self._handle_linkedin_unauthenticated(job_id, task, source_url)
        
        task.progress = 50
        task.message = "Enriching with Google Search..."
        await self._broadcast_update(job_id, "task_progress", task.to_dict())
        
        # Extract basic info from OAuth
        oauth_basic = linkedin_data.get('data', {}).get('basic_profile', {})
        
        # Use Gemini with Google Search ONLY to build rich profile
        # Combine the limited OAuth data with comprehensive search results
        from app.prompts import get_profile_extraction_prompt
        prompt = get_profile_extraction_prompt(
            url=source_url,
            is_linkedin_oauth=True,
            oauth_data=oauth_basic
        )

        try:
            response = await asyncio.to_thread(
                self.genai_client.models.generate_content,
                model="gemini-3-flash-preview",
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[{"google_search": {}}],  # ONLY google_search for LinkedIn OAuth
                    response_mime_type="application/json",
                    response_json_schema=PROFILE_EXTRACTION_SCHEMA,
                    temperature=0.0,
                    top_p=1.0,
                    top_k=1.0,
                    thinking_config=types.ThinkingConfig(thinking_level="high")
                )
            )
        except Exception as e:
            logger.warning(f"Gemini extraction failed: {e}, trying without thinking config")
            response = await asyncio.to_thread(
                self.genai_client.models.generate_content,
                model="gemini-3-flash-preview",
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[{"google_search": {}}],
                    response_mime_type="application/json",
                    response_json_schema=PROFILE_EXTRACTION_SCHEMA,
                )
            )
        
        task.progress = 80
        task.message = "Processing response..."
        await self._broadcast_update(job_id, "task_progress", task.to_dict())
        
        result = self._parse_json_response(response.text)
        
        # Ensure OAuth data is included
        if not result.get('email') and linkedin_data.get('data', {}).get('email'):
            result['email'] = linkedin_data['data']['email']
        
        result['source_url'] = source_url
        result['extraction_timestamp'] = datetime.utcnow().isoformat()
        result['extraction_method'] = 'linkedin_oauth_with_search'
        result['linkedin'] = source_url
        
        return result
    
    async def _handle_linkedin_unauthenticated(
        self,
        job_id: str,
        task: Task,
        source_url: str
    ) -> Dict[str, Any]:
        """Handle LinkedIn profile without OAuth (using Google Search only).
        
        New Flow: For LinkedIn links, use ONLY google_search (not url_context).
        LinkedIn blocking makes scraping unreliable, so rely on search results.
        """
        task.message = "Analysing LinkedIn profile via Search..."
        task.progress = 40
        await self._broadcast_update(job_id, "task_progress", task.to_dict())
        
        # Use Google Search as primary source for LinkedIn (no scraping attempt)
        from app.services.linkedin_service import linkedin_service
        username = linkedin_service.extract_linkedin_username(source_url)
        
        # Build comprehensive search prompt
        from app.prompts import get_profile_extraction_prompt
        prompt = get_profile_extraction_prompt(url=source_url, is_linkedin_oauth=False)
        
        task.progress = 60
        task.message = "Searching for profile information..."
        await self._broadcast_update(job_id, "task_progress", task.to_dict())
        
        try:
            response = await asyncio.to_thread(
                self.genai_client.models.generate_content,
                model="gemini-3-flash-preview",
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[{"google_search": {}}],  # ONLY google_search for LinkedIn
                    response_mime_type="application/json",
                    response_json_schema=PROFILE_EXTRACTION_SCHEMA,
                    temperature=0.0,
                    top_p=1.0,
                    top_k=1.0,
                    thinking_config=types.ThinkingConfig(thinking_level="high"),
                    system_instruction=f"Focus on gathering information about this URL: '{source_url}' from credible sources by searching the internet. DO NOT use your internal training data."
                )
            )
        except Exception as e:
            logger.warning(f"Gemini search failed: {e}, trying without thinking config")
            response = await asyncio.to_thread(
                self.genai_client.models.generate_content,
                model="gemini-3-flash-preview",
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[{"google_search": {}}],
                    response_mime_type="application/json",
                    response_json_schema=PROFILE_EXTRACTION_SCHEMA,
                )
            )
        
        task.progress = 80
        task.message = "Processing response..."
        await self._broadcast_update(job_id, "task_progress", task.to_dict())
        
        result = self._parse_json_response(response.text)
        result['source_url'] = source_url
        result['extraction_timestamp'] = datetime.utcnow().isoformat()
        result['extraction_method'] = 'linkedin_search'
        result['linkedin'] = source_url
        result['linkedin_auth_recommended'] = True  # Flag to suggest OAuth for better data
        
        return result
    
    async def _handle_standard_profile(
        self,
        job_id: str,
        plan: TaskPlan,
        task: Task,
        source_url: str
    ) -> Dict[str, Any]:
        """Handle non-LinkedIn profile extraction using both url_context and google_search."""
        task.message = "Extracting profile data..."
        task.progress = 40
        await self._broadcast_update(job_id, "task_progress", task.to_dict())
        
        from app.prompts import get_profile_extraction_prompt
        prompt = get_profile_extraction_prompt(url=source_url, is_linkedin_oauth=False)
        
        # Try with thinking config first, fall back without if not supported
        try:
            response = await asyncio.to_thread(
                self.genai_client.models.generate_content,
                model="gemini-3-flash-preview",
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[{"url_context": {}}, {"google_search": {}}],  # Both tools for non-LinkedIn
                    response_mime_type="application/json",
                    response_json_schema=PROFILE_EXTRACTION_SCHEMA
                )
            )
        except Exception as e:
            if "thinking level" in str(e).lower() or "thinking" in str(e).lower():
                logger.warning(f"Thinking config not supported for profile extraction: {str(e)}, retrying without thinking config")
                response = await asyncio.to_thread(
                    self.genai_client.models.generate_content,
                    model="gemini-3-flash-preview",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        tools=[{"url_context": {}}, {"google_search": {}}],
                        response_mime_type="application/json",
                        response_json_schema=PROFILE_EXTRACTION_SCHEMA
                    )
                )
            elif "model" in str(e).lower() and "not found" in str(e).lower():
                logger.warning(f"Model not found, falling back to gemini-2.5-flash: {str(e)}")
                response = await asyncio.to_thread(
                    self.genai_client.models.generate_content,
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        tools=[{"url_context": {}}, {"google_search": {}}],
                        response_mime_type="application/json",
                        response_json_schema=PROFILE_EXTRACTION_SCHEMA
                    )
                )
            else:
                raise
        
        task.progress = 80
        task.message = "Processing response..."
        await self._broadcast_update(job_id, "task_progress", task.to_dict())
        
        result = self._parse_json_response(response.text)
        result['source_url'] = plan.source_url
        result['extraction_timestamp'] = datetime.utcnow().isoformat()
        result['extraction_method'] = 'standard_with_search'
        
        return result
    
    async def _handle_enrich_profile(self, job_id: str, plan: TaskPlan, task: Task) -> Dict[str, Any]:
        """Handle profile enrichment task with web scraping.
        
        New Flow:
        1. Get profile data from FETCH_PROFILE (includes related_links)
        2. Use BeautifulSoup scraper to extract rich content from all related links
        3. Combine scraped data with profile for next stage (AGGREGATE_HISTORY will use this)
        """
        task.message = "Starting enrichment process..."
        task.progress = 10
        await self._broadcast_update(job_id, "task_progress", task.to_dict())
        
        # Get profile data from previous task
        profile_data = plan.result_data.get(TaskType.FETCH_PROFILE.value)
        if not profile_data or not isinstance(profile_data, dict):
            profile_data = {}
        
        # Extract related links discovered by Gemini
        related_links = profile_data.get('related_links', [])
        
        task.progress = 20
        task.message = f"Found {len(related_links)} related links to enrich"
        await self._broadcast_update(job_id, "task_progress", task.to_dict())
        
        enriched_data = {**profile_data}
        scraped_content = []
        
        # Scrape content from related links using BeautifulSoup
        if related_links:
            task.progress = 30
            task.message = "Scraping content from related links..."
            await self._broadcast_update(job_id, "task_progress", task.to_dict())
            
            from app.services.web_scraper import web_scraper
            
            # Extract URLs, excluding the primary source URL
            primary_url = profile_data.get('source_url', '')
            urls_to_scrape = [
                link['url'] for link in related_links 
                if link.get('url') and link['url'] != primary_url
            ]
            
            # Limit to top 20 links to allow more comprehensive enrichment
            urls_to_scrape = urls_to_scrape[:20]
            
            logger.info(f"Scraping {len(urls_to_scrape)} URLs for enrichment")
            
            try:
                # Scrape all URLs concurrently with rate limiting
                scraped_results = await web_scraper.scrape_multiple_urls(
                    urls=urls_to_scrape,
                    max_concurrent=5  # Increased concurrency for better throughput
                )
                
                # Filter successful scrapes and format for Gemini
                for result in scraped_results:
                    if result.get('success'):
                        scraped_content.append({
                            'url': result['url'],
                            'title': result.get('title', ''),
                            'description': result.get('description', ''),
                            'content': result.get('content', '')[:3000],  # Increased content limit for richer context
                            'author': result.get('author', ''),
                            'publisher': result.get('publisher', ''),
                            'domain': result.get('domain', ''),
                            'published_date': result.get('published_date', result.get('publication_date', '')),
                            'featured_image': result.get('featured_image', ''),
                            'headings': result.get('headings', [])[:8],  # More headings for better context
                            'quality_score': result.get('quality_score', 5.0),  # Quality score for prioritization
                        })
                
                # Sort scraped content by quality score (descending) to prioritize best content
                scraped_content = sorted(scraped_content, key=lambda x: x.get('quality_score', 5.0), reverse=True)
                
                logger.info(f"Successfully scraped {len(scraped_content)} out of {len(urls_to_scrape)} URLs (sorted by quality)")
                if scraped_content:
                    avg_quality = sum(item.get('quality_score', 5.0) for item in scraped_content) / len(scraped_content)
                    logger.info(f"Average content quality score: {avg_quality:.2f}/10.0")
                
            except Exception as scrape_error:
                logger.error(f"Error during web scraping: {scrape_error}")
                # Continue without scraped data
        
        task.progress = 60
        task.message = f"Scraped {len(scraped_content)} articles/pages"
        await self._broadcast_update(job_id, "task_progress", task.to_dict())
        
        # Add scraped content to enriched data
        enriched_data['scraped_content'] = scraped_content
        enriched_data['enrichment_stats'] = {
            'related_links_found': len(related_links),
            'links_scraped': len(urls_to_scrape) if related_links else 0,
            'successful_scrapes': len(scraped_content),
        }
        
        # Check for GitHub OAuth enrichment
        guest_user_id = plan.options.get('guest_user_id')
        if guest_user_id:
            task.progress = 70
            task.message = "Checking GitHub integration..."
            await self._broadcast_update(job_id, "task_progress", task.to_dict())
            
            github_enrichment = await self._enrich_with_github(guest_user_id, task, job_id)
            if github_enrichment:
                enriched_data['github_data'] = github_enrichment
                enriched_data['enrichment_stats']['github_enriched'] = True
        
        task.progress = 90
        task.message = "Enrichment complete"
        await self._broadcast_update(job_id, "task_progress", task.to_dict())
        
        # Mark enrichment metadata
        enriched_data['enriched'] = True
        enriched_data['enrichment_timestamp'] = datetime.utcnow().isoformat()
        
        logger.info(f"Profile enrichment complete: {enriched_data.get('enrichment_stats')}")
        
        return enriched_data
    
    async def _enrich_with_github(
        self, 
        guest_user_id: str, 
        task: Task, 
        job_id: str
    ) -> Optional[Dict[str, Any]]:
        """Enrich profile with GitHub data if OAuth is available.
        
        Args:
            guest_user_id: Guest user identifier
            task: Current task for progress updates
            job_id: Job ID for broadcasting
            
        Returns:
            GitHub enrichment data or None
        """
        from app.db.session import get_db
        from app.models.user import User
        from sqlalchemy import select
        import httpx
        
        async for db in get_db():
            try:
                result = await db.execute(
                    select(User).where(User.guest_id == guest_user_id)
                )
                user = result.scalar_one_or_none()
                
                if not user or not user.github_access_token:
                    return None
                
                task.message = "Enriching with GitHub data..."
                await self._broadcast_update(job_id, "task_progress", task.to_dict())
                
                github_data = {
                    'username': user.github_username,
                    'authenticated': True,
                    'repositories': [],
                    'contributions': {},
                    'languages': {},
                    'significant_projects': []
                }
                
                headers = {
                    "Authorization": f"Bearer {user.github_access_token}",
                    "Accept": "application/vnd.github+json"
                }
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    # Fetch user's repositories
                    repos_response = await client.get(
                        f"https://api.github.com/users/{user.github_username}/repos",
                        headers=headers,
                        params={"sort": "updated", "per_page": 30}
                    )
                    
                    if repos_response.status_code == 200:
                        repos = repos_response.json()
                        
                        # Process repositories for significant projects
                        significant_repos = []
                        language_stats = {}
                        
                        for repo in repos:
                            # Track languages
                            if repo.get('language'):
                                lang = repo['language']
                                language_stats[lang] = language_stats.get(lang, 0) + 1
                            
                            # Identify significant projects (stars, forks, or has description)
                            stars = repo.get('stargazers_count', 0)
                            forks = repo.get('forks_count', 0)
                            
                            if stars >= 1 or forks >= 1 or repo.get('description'):
                                significant_repos.append({
                                    'name': repo['name'],
                                    'description': repo.get('description', ''),
                                    'url': repo['html_url'],
                                    'stars': stars,
                                    'forks': forks,
                                    'language': repo.get('language'),
                                    'updated_at': repo.get('updated_at'),
                                    'topics': repo.get('topics', [])
                                })
                        
                        # Sort by significance (stars + forks)
                        significant_repos.sort(
                            key=lambda x: x['stars'] + x['forks'], 
                            reverse=True
                        )
                        
                        github_data['repositories'] = repos[:10]  # Top 10 recent
                        github_data['significant_projects'] = significant_repos[:10]
                        github_data['languages'] = language_stats
                        github_data['total_repos'] = len(repos)
                    
                    # Fetch contribution stats
                    events_response = await client.get(
                        f"https://api.github.com/users/{user.github_username}/events",
                        headers=headers,
                        params={"per_page": 100}
                    )
                    
                    if events_response.status_code == 200:
                        events = events_response.json()
                        
                        # Count event types
                        event_counts = {}
                        for event in events:
                            event_type = event.get('type', 'Unknown')
                            event_counts[event_type] = event_counts.get(event_type, 0) + 1
                        
                        github_data['contributions'] = {
                            'recent_events': len(events),
                            'event_types': event_counts,
                            'push_events': event_counts.get('PushEvent', 0),
                            'pr_events': event_counts.get('PullRequestEvent', 0),
                            'issue_events': event_counts.get('IssuesEvent', 0),
                        }
                
                logger.info(f"GitHub enrichment completed for user {user.id}")
                return github_data
                
            except Exception as e:
                logger.error(f"GitHub enrichment failed: {e}")
                return None
            finally:
                break
        
        return None
    
    async def _handle_aggregate_history(self, job_id: str, plan: TaskPlan, task: Task) -> Dict[str, Any]:
        """Handle history aggregation task.
        
        Checks for existing profile history using guest_id and aggregates with Gemini 3 if found.
        """
        from app.db.session import get_db
        from app.models.user import User, ProfileHistory
        from sqlalchemy import select
        
        task.message = "Checking for existing profile history..."
        task.progress = 20
        await self._broadcast_update(job_id, "task_progress", task.to_dict())
        
        # Get enriched profile data from previous task
        profile_data = plan.result_data.get(TaskType.ENRICH_PROFILE.value)
        if not profile_data or not isinstance(profile_data, dict):
            profile_data = plan.result_data.get(TaskType.FETCH_PROFILE.value)
            
        if not profile_data or not isinstance(profile_data, dict):
            profile_data = {}
        
        # Get guest_user_id and current history_id from plan options
        guest_user_id = plan.options.get('guest_user_id')
        current_history_id = plan.options.get('history_id')
        user_id = plan.options.get('user_id')
        
        if not guest_user_id:
            task.message = "No identifier found, skipping history check"
            task.progress = 100
            await self._broadcast_update(job_id, "task_progress", task.to_dict())
            return {**profile_data, "history_checked": True, "aggregated": False}
        
        task.progress = 40
        task.message = "Querying for existing records..."
        await self._broadcast_update(job_id, "task_progress", task.to_dict())
        
        # Query database for existing history
        async for db in get_db():
            try:
                # Find user by guest_id (more reliable than email)
                user_query = select(User).where(User.guest_id == guest_user_id)
                result = await db.execute(user_query)
                user = result.scalar_one_or_none()
                
                if not user:
                    # This shouldn't happen as user is created in profile_service
                    # But handle gracefully
                    task.message = "Record not found, skipping history check"
                    task.progress = 100
                    await self._broadcast_update(job_id, "task_progress", task.to_dict())
                    return {**profile_data, "history_checked": True, "aggregated": False, "error": "Record not found"}
                
                # Fetch all profile histories for this user EXCEPT the current one
                task.progress = 60
                task.message = f"Loading profile history for record..."
                await self._broadcast_update(job_id, "task_progress", task.to_dict())
                
                history_query = select(ProfileHistory).where(
                    ProfileHistory.user_id == user.id
                ).order_by(ProfileHistory.created_at.desc())
                result = await db.execute(history_query)
                all_histories = result.scalars().all()
                
                # Exclude the current history record (just created in profile_service)
                histories = [h for h in all_histories if h.id != current_history_id]
                
                if not histories or len(histories) == 0:
                    # No previous history found, this is the first record
                    # But we still want to integrate scraped content if available
                    scraped_content = profile_data.get('scraped_content', [])
                    
                    if scraped_content and len(scraped_content) > 0:
                        # First record but has scraped content - enrich with Gemini
                        task.progress = 70
                        task.message = f"Enriching first record with {len(scraped_content)} scraped sources..."
                        await self._broadcast_update(job_id, "task_progress", task.to_dict())
                        
                        if not self.genai_client:
                            raise Exception("Gemini client not initialized")
                        
                        # Create enrichment prompt
                        enrichment_prompt = self._create_aggregation_prompt(
                            current_profile=profile_data,
                            previous_profiles=[],
                            scraped_content=scraped_content
                        )
                        
                        try:
                            response = await asyncio.to_thread(
                                self.genai_client.models.generate_content,
                                model="gemini-3-flash-preview",
                                contents=enrichment_prompt,
                                config=types.GenerateContentConfig(
                                    response_mime_type="application/json",
                                    # thinking_config=types.ThinkingConfig(thinking_level="low")
                                )
                            )
                        except Exception as e:
                            if "thinking level" in str(e).lower() or "thinking" in str(e).lower():
                                logger.warning(f"Thinking config not supported: {str(e)}, retrying without")
                                response = await asyncio.to_thread(
                                    self.genai_client.models.generate_content,
                                    model="gemini-3-flash-preview",
                                    contents=enrichment_prompt,
                                    config=types.GenerateContentConfig(
                                        response_mime_type="application/json"
                                    )
                                )
                            else:
                                raise
                        
                        enriched_profile = self._parse_json_response(response.text)
                        
                        # Save enriched profile
                        if current_history_id:
                            current_history = await db.get(ProfileHistory, current_history_id)
                            if current_history:
                                current_history.structured_data = enriched_profile
                                await db.commit()
                                logger.info(f"Saved enriched first record to history {current_history_id}")
                        
                        task.progress = 100
                        task.message = "First record enriched with scraped content"
                        await self._broadcast_update(job_id, "task_progress", task.to_dict())
                        
                        return {
                            **enriched_profile,
                            "history_checked": True,
                            "aggregated": False,
                            "enriched_with_scraping": True,
                            "first_record": True
                        }
                    else:
                        # First record without scraped content
                        task.message = "First profile record"
                        
                        if current_history_id:
                            current_history = await db.get(ProfileHistory, current_history_id)
                            if current_history:
                                current_history.structured_data = profile_data
                                await db.commit()
                                logger.info(f"Saved initial profile data to history record {current_history_id}")
                        
                        task.progress = 100
                        await self._broadcast_update(job_id, "task_progress", task.to_dict())
                        return {**profile_data, "history_checked": True, "aggregated": False, "first_record": True}
                
                # Aggregate with Gemini 3
                task.progress = 70
                task.message = f"Aggregating {len(histories)} previous records..."
                await self._broadcast_update(job_id, "task_progress", task.to_dict())
                
                if not self.genai_client:
                    raise Exception("Gemini client not initialized")
                
                # Prepare aggregation prompt with scraped content
                previous_profiles = []
                for h in histories:
                    # Safely extract structured_data, handling None cases
                    profile_entry = {
                        "source": h.source_url or "unknown",
                        "date": h.created_at.isoformat() if h.created_at else None
                    }
                    # Only include data if structured_data exists and has content
                    if h.structured_data and isinstance(h.structured_data, dict):
                        profile_entry["data"] = h.structured_data
                    else:
                        profile_entry["data"] = {}
                    previous_profiles.append(profile_entry)
                
                # Filter out entries with empty data to avoid noise in the prompt
                previous_profiles = [
                    p for p in previous_profiles 
                    if p.get("data") and any(p["data"].values())
                ]
                
                # Extract scraped content for enrichment
                scraped_content = profile_data.get('scraped_content', [])
                
                aggregation_prompt = self._create_aggregation_prompt(
                    current_profile=profile_data,
                    previous_profiles=previous_profiles,
                    scraped_content=scraped_content
                )
                
                task.progress = 80
                task.message = "Processing aggregation..."
                await self._broadcast_update(job_id, "task_progress", task.to_dict())
                
                # Try with thinking config first, fall back without if failed
                try:
                    response = await asyncio.to_thread(
                        self.genai_client.models.generate_content,
                        model="gemini-3-flash-preview",
                        contents=aggregation_prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            # thinking_config=types.ThinkingConfig(thinking_level="low")
                        )
                    )
                except Exception as e:
                    if "thinking level" in str(e).lower() or "thinking" in str(e).lower():
                        logger.warning(f"Thinking config not supported for aggregation: {str(e)}, retrying without thinking config")
                        response = await asyncio.to_thread(
                            self.genai_client.models.generate_content,
                            model="gemini-3-flash-preview",
                            contents=aggregation_prompt,
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json"
                            )
                        )
                    elif "model" in str(e).lower() and "not found" in str(e).lower():
                        logger.warning(f"Model not found, falling back to gemini-2.5-flash: {str(e)}")
                        response = await asyncio.to_thread(
                            self.genai_client.models.generate_content,
                            model="gemini-2.5-flash",
                            contents=aggregation_prompt,
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json"
                            )
                        )
                    else:
                        raise
                
                aggregated_data = self._parse_json_response(response.text)
                
                # Update the current history record with aggregated data
                if current_history_id:
                    current_history = await db.get(ProfileHistory, current_history_id)
                    if current_history:
                        current_history.structured_data = aggregated_data
                        current_history.raw_data = profile_data
                        await db.commit()
                
                task.progress = 100
                task.message = "Successfully aggregated profile history"
                await self._broadcast_update(job_id, "task_progress", task.to_dict())
                
                return {
                    **aggregated_data,
                    "history_checked": True,
                    "aggregated": True,
                    "previous_records": len(histories),
                    "aggregation_timestamp": datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error aggregating history: {e}")
                await db.rollback()
                # Return profile data without aggregation on error
                return {**profile_data, "history_checked": True, "aggregated": False, "error": str(e)}
            finally:
                break  # Exit after first iteration
    
    async def _handle_structure_journey(self, job_id: str, plan: TaskPlan, task: Task) -> Dict[str, Any]:
        """Handle journey structuring task."""
        task.message = "Creating narrative structure..."
        task.progress = 20
        await self._broadcast_update(job_id, "task_progress", task.to_dict())

        if not self.genai_client:
            raise Exception("Gemini client not initialized")

        # Get profile data from aggregate_history, enrich_profile, or fetch_profile tasks
        profile_data = plan.result_data.get(TaskType.AGGREGATE_HISTORY.value)
        if not profile_data:
            profile_data = plan.result_data.get(TaskType.ENRICH_PROFILE.value)
        if not profile_data:
            profile_data = plan.result_data.get(TaskType.FETCH_PROFILE.value)

        task.progress = 50
        task.message = "Generating journey chapters..."
        await self._broadcast_update(job_id, "task_progress", task.to_dict())
        
        prompt = get_journey_structuring_prompt(profile_data)

        # Try with thinking config first, fall back without if not supported
        try:
            logger.info("Calling Gemini for journey structuring with thinking config...")
            response = await asyncio.to_thread(
                self.genai_client.models.generate_content,
                model="gemini-3-flash-preview",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_json_schema=JOURNEY_STRUCTURE_SCHEMA,
                    # thinking_config=types.ThinkingConfig(thinking_level="low")
                )
            )
            logger.info(f"Gemini response received, length: {len(response.text) if response and response.text else 0}")
        except Exception as e:
            logger.error(f"Journey structuring Gemini call failed with thinking config: {str(e)}")
            if "thinking level" in str(e).lower() or "thinking" in str(e).lower():
                logger.warning("Thinking config not supported, retrying without thinking config")
                try:
                    response = await asyncio.to_thread(
                        self.genai_client.models.generate_content,
                        model="gemini-3-flash-preview",
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_json_schema=JOURNEY_STRUCTURE_SCHEMA
                        )
                    )
                    logger.info(f"Gemini response received (retry), length: {len(response.text) if response and response.text else 0}")
                except Exception as retry_error:
                    logger.error(f"Journey structuring retry also failed: {str(retry_error)}")
                    # Try with a different model as final fallback
                    logger.info("Attempting final fallback with gemini-2.5-flash model...")
                    try:
                        response = await asyncio.to_thread(
                            self.genai_client.models.generate_content,
                            model="gemini-2.5-flash",
                            contents=prompt,
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json"
                                # Note: Removed schema to be more lenient
                            )
                        )
                        logger.info(f"Fallback model response received, length: {len(response.text) if response and response.text else 0}")
                    except Exception as final_error:
                        logger.error(f"All journey structuring attempts failed: {str(final_error)}")
                        # Return detailed error structure instead of failing
                        return {
                            "summary": {
                                "headline": profile_data.get('name', 'Professional') + " Journey",
                                "narrative": "Unable to generate journey narrative - all AI models failed",
                                "career_span": "Unknown",
                                "key_themes": profile_data.get('skills', [])[:3] if profile_data.get('skills') else []
                            },
                            "milestones": [],
                            "career_chapters": [],
                            "skills_evolution": [],
                            "impact_metrics": {},
                            "error": f"All models failed: {str(final_error)}"
                        }
            else:
                logger.error(f"Non-thinking config related error: {str(e)}")
                return {
                    "summary": {
                        "headline": profile_data.get('name', 'Professional') + " Journey",
                        "narrative": "Unable to generate journey narrative due to processing error",
                        "career_span": "Unknown", 
                        "key_themes": profile_data.get('skills', [])[:3] if profile_data.get('skills') else []
                    },
                    "milestones": [],
                    "career_chapters": [],
                    "skills_evolution": [],
                    "impact_metrics": {},
                    "error": f"Processing error: {str(e)}"
                }

        task.progress = 80
        task.message = "Finalising journey structure..."
        await self._broadcast_update(job_id, "task_progress", task.to_dict())

        # Enhanced JSON parsing with specific logging for journey
        try:
            if not response or not response.text:
                logger.error("No response or empty response text from Gemini for journey structuring")
                return {
                    "summary": {
                        "headline": profile_data.get('name', 'Professional') + " Journey",
                        "narrative": "Empty response from AI processing",
                        "career_span": "Unknown",
                        "key_themes": []
                    },
                    "milestones": [],
                    "career_chapters": [],
                    "skills_evolution": [],
                    "impact_metrics": {},
                    "error": "Empty response from Gemini API"
                }

            logger.info(f"Parsing journey response: {response.text[:200]}...")
            result = self._parse_json_response(response.text)

            if not result:
                logger.error("JSON parsing returned empty result for journey structuring")
                return {
                    "summary": {
                        "headline": profile_data.get('name', 'Professional') + " Journey",
                        "narrative": "Failed to parse AI response",
                        "career_span": "Unknown",
                        "key_themes": []
                    },
                    "milestones": [],
                    "career_chapters": [],
                    "skills_evolution": [],
                    "impact_metrics": {},
                    "error": "JSON parsing failed"
                }

            logger.info(f"Successfully processed journey data with keys: {list(result.keys())}")
            
            # Save journey data to database
            from app.db.session import get_db
            from app.models.user import ProfileHistory
            
            current_history_id = plan.options.get('history_id')
            if current_history_id:
                try:
                    async for db in get_db():
                        current_history = await db.get(ProfileHistory, current_history_id)
                        if current_history:
                            # Update structured_data with journey
                            # Ensure we don't overwrite existing data (like raw profile data)
                            if isinstance(current_history.structured_data, dict):
                                updated_data = current_history.structured_data.copy()
                            else:
                                updated_data = {}
                            updated_data['journey'] = result
                            current_history.structured_data = updated_data
                            
                            await db.commit()
                            logger.info(f"Saved journey data to history record {current_history_id}")
                        break
                except Exception as db_error:
                    logger.error(f"Failed to save journey data to DB: {db_error}")
            
            return result

        except Exception as parse_error:
            logger.error(f"Error processing journey response: {str(parse_error)}")
            return {
                "summary": {
                    "headline": profile_data.get('name', 'Professional') + " Journey",
                    "narrative": "Error processing AI response",
                    "career_span": "Unknown",
                    "key_themes": []
                },
                "milestones": [],
                "career_chapters": [],
                "skills_evolution": [],
                "impact_metrics": {},
                "error": f"Response processing error: {str(parse_error)}"
            }
    
    async def _handle_generate_timeline(self, job_id: str, plan: TaskPlan, task: Task) -> Dict[str, Any]:
        """Handle timeline generation task."""
        task.message = "Building interactive timeline..."
        task.progress = 30
        await self._broadcast_update(job_id, "task_progress", task.to_dict())
        
        if not self.genai_client:
            raise Exception("Gemini client not initialized")
        
        journey_data = plan.result_data.get(TaskType.STRUCTURE_JOURNEY.value, {})
        if not journey_data:
            logger.warning("No journey data available for timeline generation, using profile data directly")
            # Fallback to profile data for timeline generation
            profile_data = plan.result_data.get(TaskType.AGGREGATE_HISTORY.value) or plan.result_data.get(TaskType.ENRICH_PROFILE.value) or plan.result_data.get(TaskType.FETCH_PROFILE.value, {})
            journey_data = {
                "summary": {
                    "headline": profile_data.get('name', 'Professional') + " Timeline",
                    "narrative": profile_data.get('bio', ''),
                    "key_themes": profile_data.get('skills', [])[:3] if profile_data.get('skills') else []
                },
                "milestones": profile_data.get('experiences', [])[:5] if profile_data.get('experiences') else []
            }
        
        prompt = get_timeline_generation_prompt(journey_data)
        
        task.progress = 60
        task.message = "Generating timeline events..."
        await self._broadcast_update(job_id, "task_progress", task.to_dict())
        
        # Try with thinking config first, fall back without if not supported
        try:
            response = await asyncio.to_thread(
                self.genai_client.models.generate_content,
                model="gemini-3-flash-preview",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_json_schema=TIMELINE_SCHEMA,
                    # thinking_config=types.ThinkingConfig(thinking_level="low")
                )
            )
        except Exception as e:
            if "thinking level" in str(e).lower():
                logger.warning("Thinking config not supported for timeline, retrying without thinking config")
                response = await asyncio.to_thread(
                    self.genai_client.models.generate_content,
                    model="gemini-3-flash-preview",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_json_schema=TIMELINE_SCHEMA
                    )
                )
            else:
                raise
        
        result = self._parse_json_response(response.text)
        
        # Save timeline data to database
        from app.db.session import get_db
        from app.models.user import ProfileHistory
        
        current_history_id = plan.options.get('history_id')
        if current_history_id:
            try:
                async for db in get_db():
                    current_history = await db.get(ProfileHistory, current_history_id)
                    if current_history:
                        if isinstance(current_history.structured_data, dict):
                            updated_data = current_history.structured_data.copy()
                        else:
                            updated_data = {}
                        updated_data['timeline'] = result
                        current_history.structured_data = updated_data
                        
                        await db.commit()
                        logger.info(f"Saved timeline data to history record {current_history_id}")
                    break
            except Exception as db_error:
                logger.error(f"Failed to save timeline data to DB: {db_error}")

        return result
    
    async def _handle_generate_documentary(self, job_id: str, plan: TaskPlan, task: Task) -> Dict[str, Any]:
        """Handle documentary narrative generation task."""
        task.message = "Crafting documentary narrative..."
        task.progress = 20
        await self._broadcast_update(job_id, "task_progress", task.to_dict())
        
        if not self.genai_client:
            raise Exception("Gemini client not initialized")
        
        journey_data = plan.result_data.get(TaskType.STRUCTURE_JOURNEY.value, {})
        profile_data = (
            plan.result_data.get(TaskType.AGGREGATE_HISTORY.value) or 
            plan.result_data.get(TaskType.ENRICH_PROFILE.value) or 
            plan.result_data.get(TaskType.FETCH_PROFILE.value) or 
            {}
        )
        
        # Handle missing data gracefully
        if not journey_data:
            logger.warning("No journey data available for documentary, using profile data directly")
            # Create minimal journey structure from profile data
            base_profile = profile_data
            journey_data = {
                "summary": {
                    "headline": base_profile.get('name', 'Professional') + " Story",
                    "narrative": base_profile.get('bio', ''),
                    "key_themes": base_profile.get('skills', [])[:3] if base_profile.get('skills') else []
                },
                "milestones": base_profile.get('experiences', [])[:3] if base_profile.get('experiences') else []
            }
            
        if not profile_data:
            logger.warning("No profile data available for documentary - all sources empty")
        
        prompt = get_documentary_narrative_prompt(journey_data, profile_data)
        
        task.progress = 50
        task.message = "Writing documentary segments..."
        await self._broadcast_update(job_id, "task_progress", task.to_dict())
        
        # Try with thinking config first, fall back without if not supported or on other errors
        try:
            logger.info("Calling Gemini for documentary generation...")
            response = await asyncio.to_thread(
                self.genai_client.models.generate_content,
                model="gemini-3-flash-preview",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_json_schema=DOCUMENTARY_SCHEMA
                )
            )
        except Exception as e:
            logger.warning(f"Initial documentary generation failed: {e}")
            try:
                logger.info("Retrying documentary generation without strict schema...")
                # Fallback without schema to be more lenient
                response = await asyncio.to_thread(
                    self.genai_client.models.generate_content,
                    model="gemini-3-flash-preview",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
            except Exception as retry_error:
                logger.error(f"Documentary generation failed after retry: {retry_error}")
                # Return a minimal valid structure with error info instead of failing the task
                return {
                    "title": journey_data.get("summary", {}).get("headline", "Professional Journey"),
                    "tagline": "A professional story",
                    "duration_estimate": "32 seconds", 
                    "segments": [],
                    "opening_hook": "Welcome to my professional journey.",
                    "closing_statement": "Thank you for watching.",
                    "error": f"Generation failed: {str(retry_error)}"
                }
        
        task.progress = 80
        task.message = "Finalising documentary structure..."
        await self._broadcast_update(job_id, "task_progress", task.to_dict())
        
        result = self._parse_json_response(response.text)
        
        # Save documentary data to database
        from app.db.session import get_db
        from app.models.user import ProfileHistory
        
        current_history_id = plan.options.get('history_id')
        if current_history_id:
            try:
                async for db in get_db():
                    current_history = await db.get(ProfileHistory, current_history_id)
                    if current_history:
                        if isinstance(current_history.structured_data, dict):
                            updated_data = current_history.structured_data.copy()
                        else:
                            updated_data = {}
                        updated_data['documentary'] = result
                        current_history.structured_data = updated_data
                        
                        await db.commit()
                        logger.info(f"Saved documentary data to history record {current_history_id}")
                    break
            except Exception as db_error:
                logger.error(f"Failed to save documentary data to DB: {db_error}")

        return result
    
    async def _handle_generate_video(self, job_id: str, plan: TaskPlan, task: Task) -> Dict[str, Any]:
        """Handle video generation task using Veo 3.1."""
        task.message = "Preparing video documentary..."
        task.progress = 30
        await self._broadcast_update(job_id, "task_progress", task.to_dict())
        
        # Video generation would use Veo 3.1 API
        # For now, return placeholder indicating video is ready for generation
        documentary_data = plan.result_data.get(TaskType.GENERATE_DOCUMENTARY.value, {})
        
        return {
            "video_ready": False,
            "segments_prepared": len(documentary_data.get("segments", [])),
            "estimated_duration": documentary_data.get("duration_estimate", "8-40 seconds"),
            "status": "Video generation queued"
        }
    
    async def _handle_unknown(self, job_id: str, plan: TaskPlan, task: Task) -> Dict[str, Any]:
        """Handle unknown task types."""
        logger.warning(f"Unknown task type: {task.task_type}")
        return {"warning": "Unknown task type"}
    
    def _create_aggregation_prompt(
        self, 
        current_profile: Dict[str, Any], 
        previous_profiles: List[Dict[str, Any]],
        scraped_content: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Create prompt for profile aggregation with Gemini 3, including scraped content.
        
        New Flow: Combines profile data with rich scraped content from related links.
        """
        # Clean the current profile - remove internal fields not needed for aggregation
        cleaned_profile = {
            k: v for k, v in current_profile.items() 
            if k not in ['scraped_content', 'enrichment_stats', 'github_data', 'enriched', 
                        'enrichment_timestamp', 'history_checked', 'aggregated']
            and v is not None
        }
        
        # Prepare previous profiles section - only if we have meaningful data
        previous_section = ""
        if previous_profiles and len(previous_profiles) > 0:
            # Filter to only include profiles with actual data
            valid_previous = [
                p for p in previous_profiles 
                if p.get("data") and isinstance(p["data"], dict) and len(p["data"]) > 0
            ]
            if valid_previous:
                previous_section = f"""
**Previous Profile Records ({len(valid_previous)} records with data):**
These are historical records from the same person's previous profile generations.
Use them to identify career progression, new skills, and historical context.

```json
{json.dumps(valid_previous, indent=2, default=str)}
```
"""
            else:
                previous_section = "\n**Previous Profile Records:** None with usable data.\n"
        else:
            previous_section = "\n**Previous Profile Records:** This is the first profile record.\n"
        
        # Prepare scraped content section
        scraped_section = ""
        if scraped_content and len(scraped_content) > 0:
            # Content is already filtered and sorted by quality score
            valid_scrapes = [
                s for s in scraped_content 
                if s.get('content') or s.get('title')
            ]
            if valid_scrapes:
                # Calculate quality stats
                total_score = sum(s.get('quality_score', 5.0) for s in valid_scrapes)
                avg_quality = total_score / len(valid_scrapes)
                high_quality_count = sum(1 for s in valid_scrapes if s.get('quality_score', 5.0) >= 7.0)
                
                scraped_section = f"""
**Enrichment Data from Web Scraping ({len(valid_scrapes)} sources, avg quality: {avg_quality:.1f}/10.0):**
Content is sorted by quality score (highest first). {high_quality_count} sources have high quality scores (7.0+).
Use this rich content to dramatically enhance the profile with verified achievements, media mentions, professional activities, etc.

```json
{json.dumps(valid_scrapes, indent=2, default=str)}
```

**How to Use Quality-Scored Scraped Content:**
- PRIORITIZE higher quality_score sources (7.0+ are premium content)
- Extract verified achievements, awards, and recognition from quality sources
- Identify speaking engagements, publications, interviews, or media features
- Capture precise dates and contexts from articles to build accurate timelines
- Add professional insights, quotes, and thought leadership examples
- Cross-reference multiple sources for accuracy validation
- Use author/publisher information to assess credibility
- Add professional recognition and community impact
- Verify and cross-reference information with existing profile data
"""
        
        return f"""You are an expert at aggregating and enriching professional profile data.

**Current Profile Data:**
```json
{json.dumps(cleaned_profile, indent=2, default=str)}
```
{previous_section}
{scraped_section}

**Task:**
Aggregate and merge all profile data (including scraped enrichment content) to create the most comprehensive and accurate professional profile. Follow these guidelines:

1. **Chronological Integration**: Merge experiences, projects, and achievements chronologically
2. **Scraped Content Integration**: Extract valuable information from scraped articles/pages:
   - Speaking engagements or conference appearances
   - Articles written by or featuring the person
   - Project launches or product releases
   - Awards, recognitions, or media mentions
   - Professional insights and contributions
3. **Skill Evolution**: Track skill development and new technologies learned over time
4. **Career Progression**: Identify career growth patterns and trajectory
5. **Digital Footprint**: Capture the person's professional presence across the web
6. **Completeness**: Fill gaps using information from all sources
7. **Accuracy**: Prefer most recent data for current information, but preserve historical context
8. **Deduplication**: Remove duplicate entries while preserving unique details
9. **Verification**: Cross-reference scraped content with profile data for accuracy

**Output Requirements:**
Return a JSON object with the aggregated profile containing:
- name, title, location, bio (core identity fields)
- All unique experiences (with date ranges)
- Complete skills list (with evolution timeline if possible)
- All projects and achievements (including those found in scraped content)
- Publications, articles, or media mentions (from scraped content)
- Speaking engagements or events (from scraped content)
- Complete education history
- Comprehensive contact information (email, website, linkedin, github, social_links)
- Professional recognition and community impact
- Career insights and patterns identified
- Metadata about the aggregation (sources count, scraped articles count, date range, etc.)

Ensure the output is comprehensive, accurate, and provides a complete picture of the professional journey with rich digital footprint data.
"""
    
    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Parse JSON response from Gemini, handling markdown code blocks."""
        if not text or not isinstance(text, str):
            logger.warning("Empty or invalid text provided for JSON parsing")
            return {}
            
        text = text.strip()
        if text.startswith('```json'):
            text = text[7:]
        if text.startswith('```'):
            text = text[3:]
        if text.endswith('```'):
            text = text[:-3]
        text = text.strip()
        
        if not text:
            logger.warning("Text is empty after cleaning")
            return {}
        
        try:
            result = json.loads(text)
            logger.info(f"Successfully parsed JSON response with keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.error(f"Raw text: {text[:500]}...")
            return {}
    
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
