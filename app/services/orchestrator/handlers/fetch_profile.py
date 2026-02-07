"""Profile Fetching Handler.

Handles profile fetching from various sources including LinkedIn, standard URLs, and Resume PDFs.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

import httpx
from google.genai import types

from app.services.orchestrator.handlers.base import BaseTaskHandler
from app.services.orchestrator.models import Task, TaskPlan, TaskType
from app.prompts import get_profile_extraction_prompt, get_resume_extraction_prompt, ProfileExtractionResult

logger = logging.getLogger(__name__)


class FetchProfileHandler(BaseTaskHandler):
    """Handler for profile fetching task."""
    
    def _is_valid_profile(self, data: Dict[str, Any]) -> bool:
        """
        Validate that the extracted data looks like a professional profile.
        
        A valid profile must have at least:
        - A name (required)
        - Either a title/role OR at least one experience entry
        
        Args:
            data: The extracted profile data
            
        Returns:
            True if the data appears to be a valid profile, False otherwise
        """
        if not data:
            return False
        
        # Name is required
        name = data.get('name', '').strip()
        if not name or len(name) < 2:
            return False
        
        # Check for title/role
        title = data.get('title', '').strip()
        has_title = bool(title and len(title) >= 3)
        
        # Check for experiences
        experiences = data.get('experiences', [])
        has_experiences = isinstance(experiences, list) and len(experiences) > 0
        
        # Check for education
        education = data.get('education', [])
        has_education = isinstance(education, list) and len(education) > 0
        
        # Check for skills
        skills = data.get('skills', [])
        has_skills = isinstance(skills, list) and len(skills) > 0
        
        # A valid profile needs name AND at least one of: title, experiences, education, or skills
        if has_title or has_experiences or has_education or has_skills:
            return True
        
        return False
    
    async def execute(self, job_id: str, plan: TaskPlan, task: Task) -> Dict[str, Any]:
        """Handle profile fetching task with LinkedIn-aware extraction and resume PDF support."""
        from app.services.linkedin_service import linkedin_service
        
        task.message = "Analysing profile source..."
        task.progress = 10
        await self.update_progress(job_id, task)
        
        if not self.genai_client:
            raise Exception("Gemini client not initialized")
        
        source_url = plan.source_url
        guest_user_id = plan.options.get('guest_user_id')
        source_type = plan.options.get('source_type', 'url')
        
        # Check if this is a resume PDF source
        if source_type == 'resume':
            return await self._handle_resume_extraction(job_id, plan, task, source_url)
        
        # Detect if this is a LinkedIn URL
        is_linkedin = linkedin_service.is_linkedin_url(source_url)
        
        if is_linkedin:
            return await self._handle_linkedin_profile(job_id, plan, task, source_url, guest_user_id)
        else:
            return await self._handle_standard_profile(job_id, plan, task, source_url)
    
    async def _handle_resume_extraction(
        self,
        job_id: str,
        plan: TaskPlan,
        task: Task,
        resume_url: str
    ) -> Dict[str, Any]:
        """Handle resume PDF extraction using Gemini 3's native PDF processing.
        
        This method downloads the PDF from GCS and passes it directly to Gemini 3
        for comprehensive data extraction.
        """
        from app.services.orchestrator.utils.parsing import parse_and_validate_response
        
        task.message = "Downloading resume PDF..."
        task.progress = 20
        await self.update_progress(job_id, task)
        
        try:
            # Download PDF from GCS URL
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(resume_url)
                response.raise_for_status()
                pdf_data = response.content
            
            logger.info(f"Downloaded resume PDF: {len(pdf_data)} bytes")
            
            task.message = "Extracting profile from resume..."
            task.progress = 40
            await self.update_progress(job_id, task)
            
            # Get the resume extraction prompt
            prompt = get_resume_extraction_prompt()
            
            # Use Gemini 3's PDF processing capability
            try:
                response = await asyncio.to_thread(
                    self.genai_client.models.generate_content,
                    model="gemini-3-flash-preview",
                    contents=[
                        types.Part.from_bytes(
                            data=pdf_data,
                            mime_type="application/pdf"
                        ),
                        prompt
                    ],
                    config=types.GenerateContentConfig(
                        tools=[{"google_search": {}}],  # Enable search for enrichment
                        response_mime_type="application/json",
                        response_json_schema=ProfileExtractionResult.model_json_schema()
                    )
                )
            except Exception as e:
                logger.warning(f"Gemini PDF extraction failed with search, retrying without: {e}")
                # Retry without google_search if it fails
                response = await asyncio.to_thread(
                    self.genai_client.models.generate_content,
                    model="gemini-3-flash-preview",
                    contents=[
                        types.Part.from_bytes(
                            data=pdf_data,
                            mime_type="application/pdf"
                        ),
                        prompt
                    ],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_json_schema=ProfileExtractionResult.model_json_schema()
                    )
                )
            
            task.progress = 70
            task.message = "Processing extracted data..."
            await self.update_progress(job_id, task)
            
            result = parse_and_validate_response(
                response.text,
                ProfileExtractionResult,
                fallback_to_dict=True
            )
            
            # Add metadata
            result['source_url'] = resume_url
            result['extraction_timestamp'] = datetime.utcnow().isoformat()
            result['extraction_method'] = 'resume_pdf'
            result['source_type'] = 'resume'
            
            # Perform additional search enrichment if we have a name
            if result.get('name'):
                task.progress = 80
                task.message = "Searching for additional profile links..."
                await self.update_progress(job_id, task)
                
                # Use Google Search to find related links for this person
                search_result = await self._search_for_related_links(result)
                if search_result:
                    # Merge any discovered links
                    existing_links = result.get('related_links', []) or []
                    new_links = search_result.get('related_links', []) or []
                    result['related_links'] = existing_links + new_links
                    
                    # Update social links if found
                    for field in ['linkedin', 'github', 'website']:
                        if not result.get(field) and search_result.get(field):
                            result[field] = search_result[field]
            
            # Validate that the extracted data looks like a profile
            if not self._is_valid_profile(result):
                logger.warning(f"Extracted data does not look like a profile: {result}")
                raise Exception("The uploaded document does not appear to be a resume or profile. Please upload a valid resume or professional profile.")
            
            # Delete resume from GCS after successful extraction
            task.progress = 90
            task.message = "Cleaning up temporary files..."
            await self.update_progress(job_id, task)
            
            try:
                from app.services.storage_service import gcs_storage
                deleted = await gcs_storage.delete_file_by_url(resume_url)
                if deleted:
                    logger.info(f"Resume file deleted from GCS: {resume_url}")
                else:
                    logger.warning(f"Failed to delete resume file from GCS: {resume_url}")
            except Exception as del_error:
                logger.warning(f"Error deleting resume from GCS (non-critical): {del_error}")
            
            logger.info(f"Resume extraction complete: {result.get('name', 'Unknown')}")
            return result
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to download resume PDF: {e}")
            raise Exception(f"Failed to download resume: {str(e)}")
        except Exception as e:
            logger.error(f"Resume extraction failed: {e}")
            raise
    
    async def _search_for_related_links(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Search for related links based on extracted profile data."""
        name = profile_data.get('name', '')
        title = profile_data.get('title', '')
        
        if not name:
            return {}
        
        # Build search query
        search_parts = [name]
        if title:
            search_parts.append(title)
        
        # Get company from experiences if available
        experiences = profile_data.get('experiences', [])
        if experiences and len(experiences) > 0:
            company = experiences[0].get('company', '')
            if company:
                search_parts.append(company)
        
        search_query = ' '.join(search_parts)
        
        prompt = f"""Use Google Search to find professional links and mentions for this person:
        
Name: {name}
Title: {title}
Search Query: "{search_query}"

Find and return:
1. LinkedIn profile URL if exists
2. GitHub profile URL if exists  
3. Personal website or portfolio
4. Related articles, interviews, or mentions
5. Any other professional profiles

Return a JSON object with:
- linkedin: LinkedIn URL or null
- github: GitHub URL or null
- website: Personal website or null
- related_links: Array of discovered links with url, title, type, description"""

        try:
            response = await asyncio.to_thread(
                self.genai_client.models.generate_content,
                model="gemini-3-flash-preview",
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[{"google_search": {}}],
                    response_mime_type="application/json"
                )
            )
            
            import json
            return json.loads(response.text)
        except Exception as e:
            logger.warning(f"Related links search failed: {e}")
            return {}
    
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
                    response_json_schema=ProfileExtractionResult.model_json_schema()
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
                    response_json_schema=ProfileExtractionResult.model_json_schema()
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
        
        # Validate that the extracted data looks like a profile
        if not self._is_valid_profile(result):
            logger.warning(f"Extracted data does not look like a profile: {result}")
            raise Exception("Unable to extract profile information from this LinkedIn URL. Please ensure it's a valid LinkedIn profile page.")
        
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
                    response_json_schema=ProfileExtractionResult.model_json_schema()
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
        
        # Validate that the extracted data looks like a profile
        if not self._is_valid_profile(result):
            logger.warning(f"Extracted data does not look like a profile: {result}")
            raise Exception("Unable to extract profile information from this LinkedIn URL. Please ensure it's a valid LinkedIn profile page.")
        
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
        
        # Validate that the extracted data looks like a profile
        if not self._is_valid_profile(result):
            logger.warning(f"Extracted data does not look like a profile: {result}")
            raise Exception("The provided URL does not appear to contain profile data. Please provide a valid professional profile URL (LinkedIn, portfolio, or personal website).")
        
        return result
