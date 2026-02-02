"""Profile Fetching Handler.

Handles profile fetching from various sources including LinkedIn and standard URLs.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

from google.genai import types

from app.services.orchestrator.handlers.base import BaseTaskHandler
from app.services.orchestrator.models import Task, TaskPlan, TaskType
from app.prompts import get_profile_extraction_prompt, ProfileExtractionResult

logger = logging.getLogger(__name__)


class FetchProfileHandler(BaseTaskHandler):
    """Handler for profile fetching task."""
    
    async def execute(self, job_id: str, plan: TaskPlan, task: Task) -> Dict[str, Any]:
        """Handle profile fetching task with LinkedIn-aware extraction."""
        from app.services.linkedin_service import linkedin_service
        
        task.message = "Analysing profile source..."
        task.progress = 10
        await self.update_progress(job_id, task)
        
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
        """Handle LinkedIn profile extraction."""
        from app.services.linkedin_service import linkedin_service
        from app.db.session import get_db
        from app.models.user import User
        from sqlalchemy import select
        
        task.message = "Detected LinkedIn profile, checking authentication..."
        task.progress = 10
        await self.update_progress(job_id, task)
        
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
                        if not user.linkedin_token_expires_at or user.linkedin_token_expires_at > datetime.utcnow():
                            linkedin_access_token = user.linkedin_access_token
                            logger.info(f"Using authenticated LinkedIn access for user {user.id}")
                except Exception as e:
                    logger.error(f"Error checking LinkedIn auth: {e}")
                finally:
                    break
        
        task.progress = 20
        task.message = "Preparing profile fetch..."
        await self.update_progress(job_id, task)
        
        if linkedin_access_token:
            return await self._handle_linkedin_authenticated(job_id, task, source_url, linkedin_access_token)
        else:
            return await self._handle_linkedin_unauthenticated(job_id, task, source_url)
    
    async def _handle_linkedin_authenticated(
        self,
        job_id: str,
        task: Task,
        source_url: str,
        access_token: str
    ) -> Dict[str, Any]:
        """Handle LinkedIn profile with OAuth authentication."""
        from app.services.linkedin_service import linkedin_service
        from app.services.orchestrator.utils.parsing import parse_and_validate_response
        
        task.message = "Fetching LinkedIn OAuth data..."
        task.progress = 30
        await self.update_progress(job_id, task)
        
        # Fetch limited profile data using OAuth
        linkedin_data = await linkedin_service.fetch_authenticated_profile(
            access_token=access_token,
            include_positions=False,
            include_education=False,
            include_skills=False
        )
        
        if not linkedin_data.get("success"):
            logger.warning(f"LinkedIn OAuth failed: {linkedin_data.get('error')}, falling back to search")
            return await self._handle_linkedin_unauthenticated(job_id, task, source_url)
        
        task.progress = 50
        task.message = "Enriching with Google Search..."
        await self.update_progress(job_id, task)
        
        oauth_basic = linkedin_data.get('data', {}).get('basic_profile', {})
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
                    tools=[{"google_search": {}}],
                    response_mime_type="application/json",
                    response_json_schema=ProfileExtractionResult.model_json_schema(),
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
                    response_json_schema=ProfileExtractionResult.model_json_schema(),
                )
            )
        
        task.progress = 80
        task.message = "Processing response..."
        await self.update_progress(job_id, task)
        
        result = parse_and_validate_response(
            response.text, 
            ProfileExtractionResult,
            fallback_to_dict=True
        )
        
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
        """Handle LinkedIn profile without OAuth (using Google Search only)."""
        from app.services.linkedin_service import linkedin_service
        from app.services.orchestrator.utils.parsing import parse_and_validate_response
        
        task.message = "Analysing LinkedIn profile via Search..."
        task.progress = 40
        await self.update_progress(job_id, task)
        
        username = linkedin_service.extract_linkedin_username(source_url)
        prompt = get_profile_extraction_prompt(url=source_url, is_linkedin_oauth=False)
        
        task.progress = 60
        task.message = "Searching for profile information..."
        await self.update_progress(job_id, task)
        
        try:
            response = await asyncio.to_thread(
                self.genai_client.models.generate_content,
                model="gemini-3-flash-preview",
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[{"google_search": {}}],
                    response_mime_type="application/json",
                    response_json_schema=ProfileExtractionResult.model_json_schema(),
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
                    response_json_schema=ProfileExtractionResult.model_json_schema(),
                )
            )
        
        task.progress = 80
        task.message = "Processing response..."
        await self.update_progress(job_id, task)
        
        from app.services.orchestrator.utils.parsing import parse_and_validate_response
        result = parse_and_validate_response(
            response.text,
            ProfileExtractionResult,
            fallback_to_dict=True
        )
        result['source_url'] = source_url
        result['extraction_timestamp'] = datetime.utcnow().isoformat()
        result['extraction_method'] = 'linkedin_search'
        result['linkedin'] = source_url
        result['linkedin_auth_recommended'] = True
        
        return result
    
    async def _handle_standard_profile(
        self,
        job_id: str,
        plan: TaskPlan,
        task: Task,
        source_url: str
    ) -> Dict[str, Any]:
        """Handle non-LinkedIn profile extraction using both url_context and google_search."""
        from app.services.orchestrator.utils.parsing import parse_and_validate_response
        
        task.message = "Extracting profile data..."
        task.progress = 40
        await self.update_progress(job_id, task)
        
        prompt = get_profile_extraction_prompt(url=source_url, is_linkedin_oauth=False)
        
        try:
            response = await asyncio.to_thread(
                self.genai_client.models.generate_content,
                model="gemini-3-flash-preview",
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[{"url_context": {}}, {"google_search": {}}],
                    response_mime_type="application/json",
                    response_json_schema=ProfileExtractionResult.model_json_schema()
                )
            )
        except Exception as e:
            if "thinking level" in str(e).lower() or "thinking" in str(e).lower():
                logger.warning(f"Thinking config not supported: {str(e)}, retrying without")
                response = await asyncio.to_thread(
                    self.genai_client.models.generate_content,
                    model="gemini-3-flash-preview",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        tools=[{"url_context": {}}, {"google_search": {}}],
                        response_mime_type="application/json",
                        response_json_schema=ProfileExtractionResult.model_json_schema()
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
                        response_json_schema=ProfileExtractionResult.model_json_schema()
                    )
                )
            else:
                raise
        
        task.progress = 80
        task.message = "Processing response..."
        await self.update_progress(job_id, task)
        
        result = parse_and_validate_response(
            response.text,
            ProfileExtractionResult,
            fallback_to_dict=True
        )
        result['source_url'] = plan.source_url
        result['extraction_timestamp'] = datetime.utcnow().isoformat()
        result['extraction_method'] = 'standard_with_search'
        
        return result
