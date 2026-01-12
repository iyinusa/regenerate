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
        
        # Create ProfileHistory record
        history = ProfileHistory(
            user_id=user.id,
            source_url=url
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
                    })
                
                elif event == "plan_failed" or event == "task_failed":
                    profile_jobs[job_id].update({
                        "status": ProfileStatus.FAILED,
                        "error": data.get("error", "Unknown error"),
                    })
            
            # Register callback
            task_orchestrator.register_callback(job_id, progress_callback)
            
            # Execute the plan
            await task_orchestrator.execute_plan(job_id)
            
            # Get final results
            plan = task_orchestrator.get_plan(job_id)
            if plan and plan.status == TaskStatus.COMPLETED:
                # Extract final data
                result_data = plan.result_data
                
                # Build profile data from results
                profile_data = self._build_profile_from_results(result_data, plan.source_url)
                
                # Save to database
                await self._save_to_database(history_id, profile_data)
                
                # Update job with final data
                profile_jobs[job_id].update({
                    "status": ProfileStatus.COMPLETED,
                    "progress": 100,
                    "message": "Profile extraction completed successfully",
                    "data": profile_data,
                    "journey": result_data.get("structure_journey", {}),
                    "timeline": result_data.get("generate_timeline", {}),
                    "documentary": result_data.get("generate_documentary", {}),
                })
                
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
        profile = result_data.get("aggregate_history", {})
        if not profile:
            profile = result_data.get("enrich_profile", {})
        if not profile:
            profile = result_data.get("fetch_profile", {})
        
        # Ensure required fields
        profile["source_url"] = source_url
        profile["extraction_timestamp"] = datetime.utcnow().isoformat()
        profile["raw_data"] = {
            "extraction_method": "gemini-3-pro-preview",
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
                            }
                        )
                    )
                    await db.commit()
                    logger.info(f"Saved extracted data to database for history_id: {history_id}")
            else:
                logger.warning("Database session maker not available")
        except Exception as db_error:
            logger.error(f"Failed to save to database: {db_error}")
    
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
    
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get the status of a profile extraction job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job status information including task details
        """
        if job_id not in profile_jobs:
            raise HTTPException(status_code=404, detail="Job not found")
        
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
                    "extraction_method": "gemini-3-pro-preview",
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
                model="gemini-3-pro-preview",
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[{"url_context": {}}, {"google_search": {}}],
                    response_mime_type="application/json",
                    response_json_schema=PROFILE_EXTRACTION_SCHEMA,
                    thinking_config=types.ThinkingConfig(thinking_level="high")
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


# Global service instance
profile_service = ProfileExtractionService()
