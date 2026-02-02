"""Profile extraction and analysis service using Gemini 3.

This service orchestrates the profile extraction pipeline using the
Task Orchestrator for Chain of Thought (CoT) task management.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from google import genai
from google.genai import types
from fastapi import HTTPException
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update

from app.core.config import settings
from app.schemas.profile import ExtractedProfileData, ProfileStatus
from app.models.user import User, ProfileHistory
from app.services.task_orchestrator import task_orchestrator, TaskStatus
from app.prompts import get_profile_extraction_prompt, PROFILE_EXTRACTION_SCHEMA

# Configure logging
logger = logging.getLogger(__name__)

# In-memory storage for demo (replace with Redis in production)
profile_jobs: Dict[str, Dict[str, Any]] = {}


class ProfileExtractionService:
    """Service for extracting and analyzing profile data using Gemini 3."""
    
    def __init__(self):
        """Initialize the profile extraction service with Gemini 3 client."""
        self.genai_client = None
        
        if settings.ai_provider_api_key:
            try:
                self.genai_client = genai.Client(
                    api_key=settings.ai_provider_api_key,
                    http_options={'timeout': 600000}
                )
                logger.info("Gemini 3 AI client initialized successfully with extended timeout")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini 3 AI: {e}")
                self.genai_client = None
        else:
            logger.warning("AI provider API key not configured")
    
    async def start_profile_extraction(
        self, 
        url: str, 
        guest_user_id: str, 
        db: AsyncSession, 
        include_github: bool = False,
        use_orchestrator: bool = True
    ) -> str:
        """Start profile extraction process with CoT task planning.
        
        Args:
            url: Profile URL to extract data from
            guest_user_id: Unique guest user ID
            db: Database session
            include_github: Whether to include GitHub OAuth
            use_orchestrator: Whether to use the new task orchestrator
            
        Returns:
            Job ID for tracking the extraction process
        """
        # Ensure User exists
        result = await db.execute(select(User).where(User.guest_id == guest_user_id))
        user = result.scalars().first()
        
        if not user:
            user = User(guest_id=guest_user_id)
            db.add(user)
            await db.flush()

        # Generate Job ID
        job_id = f"prof_{uuid.uuid4().hex}"
        
        # Check if this is the first history for the user to set as default
        result = await db.execute(select(ProfileHistory).where(ProfileHistory.user_id == user.id))
        all_histories = result.scalars().all()
        existing_count = len(all_histories)
        
        # Determine if default (first one is default)
        is_default = (existing_count == 0)
        
        # Generate default title
        # Format: "Profile from [Domain] - [Date]" or just "Profile [N]"
        # Requirement says "default title for each profile created".
        # Let's simple "Profile N" or use domain.
        from urllib.parse import urlparse
        try:
            domain = urlparse(url).netloc.replace('www.', '').split('.')[0].capitalize()
            if not domain: domain = "Web"
        except:
            domain = "Profile"
            
        current_date = datetime.now().strftime("%b %d, %Y")
        default_title = f"{domain} Profile - {current_date}"
        if existing_count > 0:
             default_title += f" ({existing_count + 1})"

        # Create ProfileHistory record
        history = ProfileHistory(
            user_id=user.id,
            source_url=url,
            is_default=is_default,
            title=default_title,
            raw_data={"job_id": job_id}
        )
        db.add(history)
        await db.commit()
        
        # Create task plan using orchestrator
        if use_orchestrator:
            plan = task_orchestrator.create_plan(
                job_id=job_id,
                source_url=url,
                options={
                    "include_github": include_github,
                    "guest_user_id": guest_user_id,
                    "user_id": user.id,
                    "history_id": history.id
                }
            )
            
            # Store job with plan reference
            profile_jobs[job_id] = {
                "status": ProfileStatus.PROCESSING,
                "url": url,
                "include_github": include_github,
                "progress": 0,
                "message": "Task plan created, starting execution...",
                "created_at": datetime.utcnow(),
                "data": None,
                "error": None,
                "history_id": history.id,
                "plan_id": plan.plan_id,
                "use_orchestrator": True,
                "tasks": [t.to_dict() for t in plan.tasks]
            }
            
            # Start background execution with orchestrator
            asyncio.create_task(self._execute_with_orchestrator(job_id, history.id))
        else:
            # Legacy mode: direct extraction
            profile_jobs[job_id] = {
                "status": ProfileStatus.PENDING,
                "url": url,
                "include_github": include_github,
                "progress": 0,
                "message": "Profile extraction queued",
                "created_at": datetime.utcnow(),
                "data": None,
                "error": None,
                "history_id": history.id,
                "use_orchestrator": False
            }
            asyncio.create_task(self._extract_profile_data_legacy(job_id, url, history.id))
        
        logger.info(f"Started profile extraction job {job_id} for URL: {url} (Guest: {guest_user_id})")
        return job_id
    
    async def start_video_generation(
        self,
        history_id: str,
        settings: Dict[str, Any] = None
    ) -> str:
        """Start a video generation job for a specific profile history.
        
        Args:
            history_id: The profile history ID
            settings: Video generation settings
            
        Returns:
            job_id for the new job
        """
        job_id = f"job_video_{uuid.uuid4().hex[:8]}"
        
        # Create plan for video generation only
        plan = task_orchestrator.create_plan(
            job_id=job_id,
            source_url="internal", # Not used for video gen
            options={
                "history_id": history_id,
                "generate_video_only": True,
                "video_settings": settings or {}
            }
        )
        
        # Store job
        profile_jobs[job_id] = {
            "status": ProfileStatus.PROCESSING,
            "progress": 0,
            "message": "Video generation started...",
            "created_at": datetime.utcnow(),
            "history_id": history_id,
            "plan_id": plan.plan_id,
            "use_orchestrator": True,
            "tasks": [t.to_dict() for t in plan.tasks]
        }
        
        # Start execution
        asyncio.create_task(self._execute_with_orchestrator(job_id, history_id))
        
        logger.info(f"Started video generation job {job_id} for history {history_id}")
        return job_id

    async def _execute_with_orchestrator(self, job_id: str, history_id: str) -> None:
        """Execute profile extraction using the task orchestrator.
        
        Args:
            job_id: Job identifier
            history_id: ProfileHistory record ID
        """
        try:
            # Register callback for progress updates
            async def progress_callback(update: Dict[str, Any]):
                event = update.get("event", "")
                data = update.get("data", {})
                
                # Update job status based on events
                if event == "task_progress" or event == "task_started":
                    task_data = data.get("task", data) if isinstance(data, dict) else {}
                    profile_jobs[job_id].update({
                        "message": task_data.get("message", "Processing..."),
                        "current_task": task_data.get("name", ""),
                        "task_progress": task_data.get("progress", 0),
                    })
                    
                    # Update plan progress
                    plan = task_orchestrator.get_plan(job_id)
                    if plan:
                        profile_jobs[job_id]["progress"] = plan.progress
                        profile_jobs[job_id]["tasks"] = [t.to_dict() for t in plan.tasks]
                
                elif event == "task_completed":
                    task_data = data.get("task", data) if isinstance(data, dict) else {}
                    profile_jobs[job_id].update({
                        "message": f"Completed: {task_data.get('name', '')}",
                    })
                
                elif event == "plan_completed":
                    plan_data = data.get("plan", data) if isinstance(data, dict) else data
                    profile_jobs[job_id].update({
                        "status": ProfileStatus.COMPLETED,
                        "progress": 100,
                        "message": "Profile extraction completed successfully",
                        "completed_at": datetime.now().isoformat(),
                    })
                
                elif event == "plan_failed" or event == "task_failed":
                    profile_jobs[job_id].update({
                        "status": ProfileStatus.FAILED,
                        "error": data.get("error", "Unknown error"),
                        "failed_at": datetime.now().isoformat(),
                    })
            
            # Register callback
            task_orchestrator.register_callback(job_id, progress_callback)
            
            # Execute the plan
            await task_orchestrator.execute_plan(job_id)
            
            # Get results (even if plan failed, we want to save partial progress)
            plan = task_orchestrator.get_plan(job_id)
            if plan:
                # Extract results
                result_data = plan.result_data
                
                # Build profile data from results (look for best available data)
                profile_data = self._build_profile_from_results(result_data, plan.source_url)
                
                # Extract journey components
                journey_data = result_data.get("structure_journey", {})
                timeline_data = result_data.get("generate_timeline", {})
                documentary_data = result_data.get("generate_documentary", {})
                
                # Debug logging for journey components
                logger.info(f"Journey data extraction - job_id: {job_id}")
                logger.info(f"  - Journey data: {bool(journey_data)} ({len(journey_data) if journey_data else 0} keys)")
                logger.info(f"  - Timeline data: {bool(timeline_data)} ({len(timeline_data) if timeline_data else 0} keys)")
                logger.info(f"  - Documentary data: {bool(documentary_data)} ({len(documentary_data) if documentary_data else 0} keys)")
                logger.info(f"  - Available task results: {list(result_data.keys())}")
                
                # Check for error/warning indicators in the data
                for name, data in [("journey", journey_data), ("timeline", timeline_data), ("documentary", documentary_data)]:
                    if isinstance(data, dict) and ('error' in data or 'warning' in data):
                        logger.warning(f"{name.capitalize()} data contains issues: {data.get('error') or data.get('warning')}")
                
                # If plan completed normally, update job with full data
                if plan.status == TaskStatus.COMPLETED:
                    # Extract video URLs from task results if available
                    video_results = result_data.get("generate_video", {})
                    intro_video = video_results.get("intro_video") or profile_data.get("intro_video")
                    full_video = video_results.get("full_video") or profile_data.get("full_video")
                    
                    # Save comprehensive data to database with all task results and plan options
                    await self._save_comprehensive_data_to_database(
                        history_id, 
                        profile_data, 
                        journey_data, 
                        timeline_data, 
                        documentary_data,
                        {**result_data, **(plan.options or {})}  # Pass task results plus plan options
                    )
                    
                    profile_jobs[job_id].update({
                        "status": ProfileStatus.COMPLETED,
                        "progress": 100,
                        "message": "Profile extraction completed successfully",
                        "completed_at": datetime.now().isoformat(),
                        "data": profile_data,
                        "journey": journey_data,
                        "timeline": timeline_data,
                        "documentary": documentary_data,
                        "intro_video": intro_video,
                        "full_video": full_video,
                    })
                else:
                    # Plan failed or was partially completed
                    # Still save the profile data we have to database for consistency
                    if profile_data and (profile_data.get('name') or profile_data.get('experiences')):
                        await self._save_comprehensive_data_to_database(
                            history_id,
                            profile_data,
                            journey_data,
                            timeline_data,
                            documentary_data,
                            {**result_data, **(plan.options or {})}  # Pass task results plus plan options
                        )
                    
                    profile_jobs[job_id].update({
                        "status": ProfileStatus.FAILED,
                        "progress": plan.progress,
                        "error": profile_jobs[job_id].get("error", "Plan failed during execution"),
                        "data": profile_data, # Return partial data if available
                        "journey": journey_data,
                    })
                
                if profile_data:
                    self._log_extraction_results(job_id, profile_data)
            
            # Unregister callback
            task_orchestrator.unregister_callback(job_id, progress_callback)
            
        except Exception as e:
            logger.error(f"Orchestrated extraction failed for job {job_id}: {e}")
            profile_jobs[job_id].update({
                "status": ProfileStatus.FAILED,
                "error": str(e),
                "message": f"Extraction failed: {str(e)}",
            })
    
    def _build_profile_from_results(self, result_data: Dict[str, Any], source_url: str) -> Dict[str, Any]:
        """Build profile data from orchestrator results.
        
        Args:
            result_data: Results from task orchestrator
            source_url: Original source URL
            
        Returns:
            Structured profile data
        """
        # Get profile data from fetch or aggregate task
        # Use .get() without a default first to check if it's truthy
        profile = result_data.get("aggregate_history")
        if not profile or not isinstance(profile, dict):
            profile = result_data.get("enrich_profile")
        if not profile or not isinstance(profile, dict):
            profile = result_data.get("fetch_profile")
        
        # Ensure we have a dictionary
        if not profile or not isinstance(profile, dict):
            profile = self._get_empty_profile_data()
        else:
            # Create a copy to avoid modifying the original plan outputs
            profile = profile.copy()
        
        # Ensure required fields
        profile["source_url"] = source_url
        profile["extraction_timestamp"] = datetime.utcnow().isoformat()
        profile["raw_data"] = {
            "extraction_method": "gemini-3-flash-preview",
            "orchestrated": True,
            "tasks_completed": len([k for k in result_data.keys() if result_data.get(k)]),
        }
        
        return profile
    
    async def _save_to_database(self, history_id: str, profile_data: Dict[str, Any]) -> None:
        """Save extracted data to database.
        
        Args:
            history_id: ProfileHistory record ID
            profile_data: Extracted profile data
        """
        try:
            from app.db.session import async_session_maker
            if async_session_maker is not None:
                async with async_session_maker() as db:
                    await db.execute(
                        update(ProfileHistory)
                        .where(ProfileHistory.id == history_id)
                        .values(
                            raw_data=profile_data.get("raw_data", {}),
                            structured_data={
                                k: v for k, v in profile_data.items()
                                if k not in ['raw_data', 'source_url', 'extraction_timestamp']
                            },
                            intro_video=profile_data.get("intro_video"),
                            full_video=profile_data.get("full_video")
                        )
                    )
                    await db.commit()
                    logger.info(f"Saved extracted data to database for history_id: {history_id}")
            else:
                logger.warning("Database session maker not available")
        except Exception as db_error:
            logger.error(f"Failed to save to database: {db_error}")

    async def _save_comprehensive_data_to_database(
        self, 
        history_id: str, 
        profile_data: Dict[str, Any],
        journey_data: Dict[str, Any],
        timeline_data: Dict[str, Any],
        documentary_data: Dict[str, Any],
        all_task_results: Optional[Dict[str, Any]] = None
    ) -> None:
        """Save comprehensive data including journey components to database.
        
        Args:
            history_id: ProfileHistory record ID
            profile_data: Extracted profile data
            journey_data: Journey structure data
            timeline_data: Timeline data
            documentary_data: Documentary data
            all_task_results: Complete task execution results for raw_data tracking
        """
        try:
            from app.db.session import async_session_maker
            from app.models.user import ProfileHistory
            if async_session_maker is not None:
                async with async_session_maker() as db:
                    # Get existing record first if we need to preserve data
                    existing_history = await db.get(ProfileHistory, history_id)
                    
                    # Check if this is a video-only generation (don't overwrite structured_data)
                    is_video_only = all_task_results and all_task_results.get("generate_video_only") == True
                    
                    if is_video_only:
                        # For video-only generation, preserve existing structured_data and only update video fields
                        logger.info(f"Video-only generation detected for history_id: {history_id}, preserving existing structured_data")
                        
                        if existing_history and existing_history.structured_data:
                            comprehensive_data = existing_history.structured_data
                            logger.info(f"Preserved existing structured_data with keys: {list(comprehensive_data.keys())}")
                        else:
                            logger.warning(f"No existing structured_data found for history_id: {history_id}")
                            comprehensive_data = {}
                    else:
                        # Full profile generation - combine all data into structured_data
                        comprehensive_data = {
                            **{k: v for k, v in profile_data.items() 
                               if k not in ['raw_data', 'source_url', 'extraction_timestamp']},
                            "journey": journey_data if journey_data else {"status": "not_generated"},
                            "timeline": timeline_data if timeline_data else {"status": "not_generated"},
                            "documentary": documentary_data if documentary_data else {"status": "not_generated"},
                            "generated_at": datetime.utcnow().isoformat()
                        }
                    
                    # Add generation status metadata only for full profile generation
                    if not is_video_only:
                        comprehensive_data["generation_status"] = {
                            "journey_generated": bool(journey_data and not journey_data.get('error')),
                            "timeline_generated": bool(timeline_data and not timeline_data.get('error')),
                            "documentary_generated": bool(documentary_data and not documentary_data.get('error')),
                            "has_warnings": any(
                                data.get('warning') for data in [journey_data, timeline_data, documentary_data] 
                                if isinstance(data, dict)
                            )
                        }
                    
                    # Build comprehensive raw_data with all steps (only for full profile generation)
                    if not is_video_only:
                        raw_data_comprehensive = {
                            "profile_extraction": profile_data.get("raw_data", {}),
                            "all_task_results": all_task_results or {},
                            "processing_steps": {
                                "fetch_profile": all_task_results.get("fetch_profile", {}) if all_task_results else {},
                                "enrich_profile": all_task_results.get("enrich_profile", {}) if all_task_results else {},
                                "aggregate_history": all_task_results.get("aggregate_history", {}) if all_task_results else {},
                                "structure_journey": all_task_results.get("structure_journey", {}) if all_task_results else {},
                                "generate_timeline": all_task_results.get("generate_timeline", {}) if all_task_results else {},
                                "generate_documentary": all_task_results.get("generate_documentary", {}) if all_task_results else {}
                            },
                            "captured_at": datetime.utcnow().isoformat()
                        }
                    else:
                        # For video-only generation, preserve existing raw_data
                        raw_data_comprehensive = existing_history.raw_data if existing_history else {}
                        logger.info(f"Preserved existing raw_data for video-only generation")
                    
                    # Extract video URLs from task results or profile data
                    video_results = all_task_results.get("generate_video", {}) if all_task_results else {}
                    intro_video = video_results.get("intro_video") or profile_data.get("intro_video")
                    full_video = video_results.get("full_video") or profile_data.get("full_video")
                    
                    await db.execute(
                        update(ProfileHistory)
                        .where(ProfileHistory.id == history_id)
                        .values(
                            raw_data=raw_data_comprehensive,
                            structured_data=comprehensive_data,
                            intro_video=intro_video,
                            full_video=full_video
                        )
                    )
                    await db.commit()
                    logger.info(f"Saved comprehensive data to database for history_id: {history_id}")
                    logger.info(f"  - Profile data keys: {list(profile_data.keys()) if profile_data else 'None'}")
                    logger.info(f"  - Journey status: {'saved' if journey_data else 'empty'} - {len(journey_data) if journey_data else 0} keys")
                    logger.info(f"  - Timeline status: {'saved' if timeline_data else 'empty'} - {len(timeline_data) if timeline_data else 0} keys")
                    logger.info(f"  - Documentary status: {'saved' if documentary_data else 'empty'} - {len(documentary_data) if documentary_data else 0} keys")
            else:
                logger.warning("Database session maker not available")
        except Exception as db_error:
            logger.error(f"Failed to save comprehensive data to database: {db_error}")
    
    def _log_extraction_results(self, job_id: str, profile_data: Dict[str, Any]) -> None:
        """Log extraction results for debugging."""
        print("\n" + "="*80)
        print(f"EXTRACTED PROFILE DATA (Orchestrated) - Job ID: {job_id}")
        print("="*80)
        print(f"Name: {profile_data.get('name')}")
        print(f"Title: {profile_data.get('title')}")
        print(f"Location: {profile_data.get('location')}")
        print(f"Experiences: {len(profile_data.get('experiences', []))} found")
        print(f"Skills: {len(profile_data.get('skills', []))} found")
        print("="*80 + "\n")
    
    async def get_job_status(self, job_id: str, db: Optional[AsyncSession] = None) -> Dict[str, Any]:
        """Get the status of a profile extraction job.
        
        Args:
            job_id: Job identifier
            db: Optional database session for recovery
            
        Returns:
            Job status information including task details
        """
        if job_id not in profile_jobs:
            # Attempt to recover from database
            if db:
                try:
                    # Query ProfileHistory where raw_data->job_id matches target job_id
                    # This works for both MySQL and SQLite JSON columns in SQLAlchemy
                    query = select(ProfileHistory).where(ProfileHistory.raw_data["job_id"] == job_id)
                    result = await db.execute(query)
                    history = result.scalar_one_or_none()
                    
                    if history:
                        # Found in DB - if it has structured_data, it's completed
                        if history.structured_data:
                            # Reconstruct a "completed" job status
                            data = history.structured_data
                            return {
                                "status": ProfileStatus.COMPLETED,
                                "progress": 100,
                                "message": "Profile extraction recovered from history",
                                "data": {k: v for k, v in data.items() if k not in ["journey", "timeline", "documentary"]},
                                "journey": data.get("journey"),
                                "timeline": data.get("timeline"),
                                "documentary": data.get("documentary"),
                                "intro_video": history.intro_video,
                                "full_video": history.full_video,
                                "history_id": history.id,
                                "recovered": True
                            }
                        else:
                            # Found record but no data - likely failed/crashed
                            return {
                                "status": ProfileStatus.FAILED,
                                "progress": 0,
                                "message": "Generation session was interrupted and could not be completed.",
                                "error": "Session lost due to server restart",
                                "recovered": True
                            }
                except Exception as e:
                    logger.error(f"Error recovering job {job_id} from DB: {e}")
            
            raise HTTPException(
                status_code=404, 
                detail="Job session not found. This may be due to a server restart. Please start a new generation."
            )
        
        job_data = profile_jobs[job_id].copy()
        
        # If using orchestrator, get fresh task data
        if job_data.get("use_orchestrator"):
            plan = task_orchestrator.get_plan(job_id)
            if plan:
                job_data["tasks"] = [t.to_dict() for t in plan.tasks]
                job_data["progress"] = plan.progress
                job_data["plan_status"] = plan.status.value
        
        return job_data
    
    async def get_task_details(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed task information for a job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Task details including individual task statuses
        """
        plan = task_orchestrator.get_plan(job_id)
        if plan:
            return plan.to_dict()
        return None

    # Legacy extraction method (kept for backwards compatibility)
    async def _extract_profile_data_legacy(self, job_id: str, url: str, history_id: str) -> None:
        """Legacy profile extraction without orchestrator.
        
        Args:
            job_id: Job identifier
            url: Profile URL to extract from
            history_id: ProfileHistory record ID
        """
        try:
            profile_jobs[job_id].update({
                "status": ProfileStatus.PROCESSING,
                "progress": 10,
                "message": "Starting Gemini 3 profile analysis..."
            })
            
            extracted_data = await self._extract_with_gemini3(url)
            
            profile_data = ExtractedProfileData(
                **extracted_data,
                source_url=url,
                extraction_timestamp=datetime.utcnow(),
                raw_data={
                    "extraction_method": "gemini-3-flash-preview",
                    "orchestrated": False,
                }
            )
            
            await self._save_to_database(history_id, profile_data.dict())
            
            profile_jobs[job_id].update({
                "status": ProfileStatus.COMPLETED,
                "progress": 100,
                "message": "Profile extraction completed successfully",
                "data": profile_data.dict()
            })
            
        except Exception as e:
            logger.error(f"Legacy extraction failed for job {job_id}: {e}")
            profile_jobs[job_id].update({
                "status": ProfileStatus.FAILED,
                "error": str(e),
            })
    
    async def _extract_with_gemini3(self, url: str) -> Dict[str, Any]:
        """Extract profile data using Gemini 3.
        
        Args:
            url: Profile URL to analyze
            
        Returns:
            Extracted profile data
        """
        if not self.genai_client:
            return self._get_empty_profile_data()
        
        try:
            prompt = get_profile_extraction_prompt(url)
            
            response = await asyncio.to_thread(
                self.genai_client.models.generate_content,
                model="gemini-3-flash-preview",
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[{"url_context": {}}, {"google_search": {}}],
                    response_mime_type="application/json",
                    response_json_schema=PROFILE_EXTRACTION_SCHEMA,
                    thinking_config=types.ThinkingConfig(thinking_level="low")
                )
            )
            
            return self._parse_json_response(response.text)
            
        except Exception as e:
            logger.error(f"Gemini 3 extraction failed for {url}: {e}")
            raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")
    
    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Parse JSON response, handling code blocks."""
        text = text.strip()
        if text.startswith('```json'):
            text = text[7:]
        if text.startswith('```'):
            text = text[3:]
        if text.endswith('```'):
            text = text[:-3]
        
        try:
            data = json.loads(text.strip())
            return self._normalize_extracted_data(data)
        except json.JSONDecodeError:
            return self._get_empty_profile_data()
    
    def _normalize_extracted_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize extracted data to ensure all expected fields exist."""
        return {
            "name": data.get("name"),
            "title": data.get("title"),
            "location": data.get("location"),
            "bio": data.get("bio"),
            "experiences": data.get("experiences", []),
            "education": data.get("education", []),
            "skills": data.get("skills", []),
            "projects": data.get("projects", []),
            "achievements": data.get("achievements", []),
            "certifications": data.get("certifications", []),
            "email": data.get("email"),
            "website": data.get("website"),
            "linkedin": data.get("linkedin"),
            "github": data.get("github"),
            "social_links": data.get("social_links", {})
        }
    
    def _get_empty_profile_data(self) -> Dict[str, Any]:
        """Return empty profile data structure."""
        return {
            "name": None, "title": None, "location": None, "bio": None,
            "experiences": [], "education": [], "skills": [], "projects": [],
            "achievements": [], "certifications": [],
            "email": None, "website": None, "linkedin": None, "github": None,
            "social_links": {}
        }

    def cleanup_completed_jobs(self, max_age_minutes: int = 30) -> None:
        """Clean up completed jobs older than specified age to prevent memory leaks.
        
        Args:
            max_age_minutes: Maximum age in minutes for completed jobs to keep in memory
        """
        try:
            current_time = datetime.now()
            jobs_to_remove = []
            
            for job_id, job_data in profile_jobs.items():
                # Only clean up completed or failed jobs
                if job_data.get("status") in [ProfileStatus.COMPLETED, ProfileStatus.FAILED]:
                    # Check completion/failure timestamps first, fall back to created_at
                    job_end_time = (
                        job_data.get("completed_at") or 
                        job_data.get("failed_at") or 
                        job_data.get("created_at")
                    )
                    
                    if job_end_time:
                        # Parse timestamp if it's a string
                        if isinstance(job_end_time, str):
                            try:
                                job_end_time = datetime.fromisoformat(job_end_time.replace('Z', '+00:00'))
                            except:
                                # If parsing fails, remove the job as it's likely old
                                jobs_to_remove.append(job_id)
                                continue
                        
                        # Check if job is older than max_age
                        age_minutes = (current_time - job_end_time).total_seconds() / 60
                        if age_minutes > max_age_minutes:
                            jobs_to_remove.append(job_id)
            
            # Remove old jobs
            for job_id in jobs_to_remove:
                profile_jobs.pop(job_id, None)
                logger.info(f"Cleaned up old job: {job_id}")
                
        except Exception as e:
            logger.error(f"Error during job cleanup: {e}")

    def get_job_statistics(self) -> Dict[str, Any]:
        """Get statistics about current jobs in memory.
        
        Returns:
            Dictionary containing job statistics
        """
        try:
            total_jobs = len(profile_jobs)
            status_counts = {}
            
            for job_data in profile_jobs.values():
                status = job_data.get("status", "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1
            
            return {
                "total_jobs": total_jobs,
                "status_breakdown": status_counts,
                "job_ids": list(profile_jobs.keys())
            }
        except Exception as e:
            logger.error(f"Error getting job statistics: {e}")
            return {"error": str(e)}


# Global service instance
profile_service = ProfileExtractionService()
