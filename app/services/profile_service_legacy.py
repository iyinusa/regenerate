"""Profile extraction and analysis service using Gemini 3.

This service uses Google Gemini 3 Pro with URL Context tool to directly
fetch and extract structured professional data from web profiles.
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
                # Initialize Gemini 3 client using the new google-genai SDK
                # Increase timeout to 10 minutes (600,000ms) to allow for Deep Search & High Thinking
                # Note: http_options timeout is in milliseconds for some versions of the SDK
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
    
    async def start_profile_extraction(self, url: str, guest_user_id: str, db: AsyncSession, include_github: bool = False) -> str:
        """Start profile extraction process.
        
        Args:
            url: Profile URL to extract data from
            guest_user_id: Unique guest user ID
            db: Database session
            include_github: Whether to include GitHub OAuth (not implemented yet)
            
        Returns:
            Job ID for tracking the extraction process
        """
        # Ensure User exists
        result = await db.execute(select(User).where(User.guest_id == guest_user_id))
        user = result.scalars().first()
        
        if not user:
            user = User(guest_id=guest_user_id)
            db.add(user)
            await db.flush() # Populate user.id

        # Generate Job ID (we'll use this as history ID if compatible, or just link them)
        # Using simple UUID for job_id for now to match existing pattern, but storing a record in DB
        job_id = f"prof_{uuid.uuid4().hex}"
        
        # Create ProfileHistory record
        history = ProfileHistory(
            user_id=user.id,
            source_url=url
        )
        db.add(history)
        await db.commit()
        
        # Store job in memory (replace with Redis in production)
        profile_jobs[job_id] = {
            "status": ProfileStatus.PENDING,
            "url": url,
            "include_github": include_github,
            "progress": 0,
            "message": "Profile extraction queued",
            "created_at": datetime.utcnow(),
            "data": None,
            "error": None,
            "history_id": history.id # Link to DB record
        }
        
        # Start background task with database session
        asyncio.create_task(self._extract_profile_data(job_id, url, history.id))
        
        logger.info(f"Started profile extraction job {job_id} for URL: {url} (Guest: {guest_user_id})")
        return job_id
    
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get the status of a profile extraction job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job status information
        """
        if job_id not in profile_jobs:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return profile_jobs[job_id]
    
    async def _extract_profile_data(self, job_id: str, url: str, history_id: str) -> None:
        """Extract profile data from the given URL using Gemini 3.
        
        Uses Gemini 3 Pro with URL Context tool to directly fetch and analyze
        the profile page, extracting structured professional data.
        
        Args:
            job_id: Job identifier
            url: Profile URL to extract data from
            history_id: ProfileHistory record ID to update with extracted data
        """
        try:
            # Update job status
            profile_jobs[job_id].update({
                "status": ProfileStatus.PROCESSING,
                "progress": 10,
                "message": "Starting Gemini 3 profile analysis..."
            })
            
            logger.info(f"Starting Gemini 3 profile extraction for job {job_id}")
            
            # Step 1: Use Gemini 3 with URL Context to extract structured data
            profile_jobs[job_id].update({
                "progress": 30,
                "message": "Fetching and analyzing profile with Gemini 3..."
            })
            
            extracted_data = await self._extract_with_gemini3(url)
            
            profile_jobs[job_id].update({
                "progress": 80,
                "message": "Structuring extracted data..."
            })
            
            # Step 2: Structure and validate data
            profile_data = ExtractedProfileData(
                **extracted_data,
                source_url=url,
                extraction_timestamp=datetime.utcnow(),
                raw_data={
                    "extraction_method": "gemini-3-pro-preview",
                    "url_context_tool": True,
                    "google_search_tool": True,
                    "thinking_level": "high",
                    "data_integrity_validated": True,
                    "source_url_verified": url
                }
            )
            
            # Console log extracted data as requested in Task 2
            print("\n" + "="*80)
            print(f"EXTRACTED PROFILE DATA (Gemini 3) - Job ID: {job_id}")
            print("="*80)
            print(f"Source URL: {url}")
            print(f"Extraction Time: {profile_data.extraction_timestamp}")
            print("\nStructured Data:")
            print("-"*40)
            print(f"Name: {profile_data.name}")
            print(f"Title: {profile_data.title}")
            print(f"Location: {profile_data.location}")
            print(f"Bio: {profile_data.bio[:200]}..." if profile_data.bio and len(profile_data.bio) > 200 else f"Bio: {profile_data.bio}")
            print(f"Skills: {profile_data.skills}")
            print(f"Experiences: {len(profile_data.experiences)} found")
            for i, exp in enumerate(profile_data.experiences[:3], 1):
                print(f"  {i}. {exp.get('title', 'N/A')} at {exp.get('company', 'N/A')} ({exp.get('duration', 'N/A')})")
            if len(profile_data.experiences) > 3:
                print(f"  ... and {len(profile_data.experiences) - 3} more")
            print(f"Education: {len(profile_data.education)} found")
            for i, edu in enumerate(profile_data.education[:2], 1):
                print(f"  {i}. {edu.get('degree', 'N/A')} from {edu.get('institution', 'N/A')}")
            print(f"Projects: {len(profile_data.projects)} found")
            for i, proj in enumerate(profile_data.projects[:2], 1):
                print(f"  {i}. {proj.get('name', 'N/A')} ({proj.get('date', 'N/A')})")
            print(f"Achievements: {len(profile_data.achievements)} found")
            for i, ach in enumerate(profile_data.achievements[:2], 1):
                print(f"  {i}. {ach.get('title', 'N/A')} ({ach.get('date', 'N/A')})")
            print(f"Certifications: {len(profile_data.certifications)} found")
            print(f"Contact Email: {profile_data.email}")
            print(f"LinkedIn: {profile_data.linkedin}")
            print(f"GitHub: {profile_data.github}")
            print(f"Website: {profile_data.website}")
            print(f"Social Links: {profile_data.social_links}")
            print("\nExtraction Method: Gemini 3 Pro with URL Context Tool")
            print("="*80 + "\n")
            
            # Save extracted data to database
            try:
                # Create a new database session for this background task
                from app.db.session import async_session_maker
                if async_session_maker is not None:
                    async with async_session_maker() as db:
                        # Update ProfileHistory record with extracted data
                        profile_dict = profile_data.dict()
                        await db.execute(
                            update(ProfileHistory)
                            .where(ProfileHistory.id == history_id)
                            .values(
                                raw_data=profile_data.raw_data,
                                structured_data={
                                    k: v for k, v in profile_dict.items() 
                                    if k not in ['raw_data', 'source_url', 'extraction_timestamp']
                                }
                            )
                        )
                        await db.commit()
                        logger.info(f"Successfully saved extracted data to database for history_id: {history_id}")
                else:
                    logger.warning("Database session maker not available, skipping database save")
            except Exception as db_error:
                logger.error(f"Failed to save extracted data to database for history_id {history_id}: {str(db_error)}")
                # Continue with in-memory storage even if DB save fails
            
            # Update job with completion
            profile_jobs[job_id].update({
                "status": ProfileStatus.COMPLETED,
                "progress": 100,
                "message": "Profile extraction completed successfully using Gemini 3",
                "data": profile_data.dict()
            })
            
            logger.info(f"Gemini 3 profile extraction completed for job {job_id}")
            
        except Exception as e:
            logger.error(f"Gemini 3 profile extraction failed for job {job_id}: {str(e)}")
            profile_jobs[job_id].update({
                "status": ProfileStatus.FAILED,
                "progress": 0,
                "message": f"Extraction failed: {str(e)}",
                "error": str(e)
            })
    
    async def _extract_with_gemini3(self, url: str) -> Dict[str, Any]:
        """Extract structured profile data using Gemini 3 with URL Context tool.
        
        This method leverages Gemini 3's native URL Context capability to fetch
        and analyze web pages directly, eliminating the need for separate scraping.
        
        Args:
            url: Profile URL to analyze
            
        Returns:
            Structured profile data dictionary
        """
        if not self.genai_client:
            logger.warning("Gemini 3 client not available, returning empty data")
            return self._get_empty_profile_data()
        
        try:
            # Define the structured output schema for profile extraction
            profile_schema = {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Full name of the person"},
                    "title": {"type": "string", "description": "Current job title or professional role"},
                    "location": {"type": "string", "description": "Geographic location"},
                    "bio": {"type": "string", "description": "Professional bio or summary"},
                    "experiences": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "company": {"type": "string"},
                                "title": {"type": "string"},
                                "duration": {"type": "string", "description": "e.g., Jan 2020 - Present"},
                                "start_date": {"type": "string", "description": "ISO date or year if available"},
                                "end_date": {"type": "string", "description": "ISO date or 'Present'"},
                                "description": {"type": "string"}
                            }
                        },
                        "description": "Work experience history"
                    },
                    "education": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "institution": {"type": "string"},
                                "degree": {"type": "string"},
                                "field": {"type": "string"},
                                "duration": {"type": "string"},
                                "start_date": {"type": "string"},
                                "end_date": {"type": "string"}
                            }
                        },
                        "description": "Educational background"
                    },
                    "skills": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Technical and soft skills"
                    },
                    "projects": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "description": {"type": "string"},
                                "date": {"type": "string", "description": "When the project was completed or active"},
                                "technologies": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                },
                                "url": {"type": "string"}
                            }
                        },
                        "description": "Notable projects"
                    },
                    "achievements": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string", "description": "Achievement or award name"},
                                "date": {"type": "string", "description": "When it was received"},
                                "issuer": {"type": "string", "description": "Who gave the award or recognition"}
                            }
                        },
                        "description": "Professional achievements, awards, and recognitions"
                    },
                    "certifications": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "issuer": {"type": "string"},
                                "date": {"type": "string"}
                            }
                        },
                        "description": "Professional certifications"
                    },
                    "email": {"type": "string", "description": "Contact email"},
                    "website": {"type": "string", "description": "Personal website URL"},
                    "linkedin": {"type": "string", "description": "LinkedIn profile URL"},
                    "github": {"type": "string", "description": "GitHub profile URL"},
                    "social_links": {
                        "type": "object",
                        "description": "Other social media links",
                        "additionalProperties": {"type": "string"}
                    }
                },
                "required": ["name"]
            }
            
            # Prompt for Gemini 3 to extract structured profile data with STRICT accuracy constraints
            extraction_prompt = f"""You are a precise data extraction assistant using Gemini 3. Your goal is to build a COMPREHENSIVE profile for the person identified by the URL.

**CORE DIRECTIVE: DEEP SEARCH & AGGREGATE**
The provided URL is just the starting point. You MUST use Google Search to find and aggregate data from other public sources (Personal Website, GitHub, Twitter/X, Articles, Interviews) to build a complete profile.

**CRITICAL DATA INTEGRITY RULES (STRICT):**
1. **IDENTITY ANCHOR:** The person is defined ONLY by the URL provided: {url}
2. **PRIMARY SOURCE:** First, use the URL Context tool to read the page content.
3. **ACTIVE SEARCH:**
   - **MANDATORY:** Use `google_search` to find external sources. Search for "[Name] personal website", "[Name] github", "[Name] blog", "[Name] projects".
   - **AGGREGATION:** If you find a verified personal website or portfolio, extract details (Bio, Projects, Skills) from verified search snippets to enrich the profile.
4. **STRICT VERIFICATION (ANTI-HALLUCINATION):**
   - **USERNAME TRAP:** If URL has username 'iyinusa' and search finds 'iaboyeji', **DO NOT MERGE** unless you find a "Bridge Link" (e.g., a website linking to BOTH).
   - **NAME COLLISIONS:** Verify identity using (Company + Title + Location). If they don't match, DISCARD the extra source.
   - **ZERO TRUST:** If you are not 100% sure a result belongs to THIS person, ignore it.

**URL TO ANALYZE:** {url}

**EXTRACTION TASK (Enrich with Search Results):**
- name: Full name (from Anchor URL)
- title: Current professional title (Verify via Search if outdated)
- location: Geographic location
- bio: Comprehensive professional summary (Combine Anchor URL bio + Search results from interviews/personal site).
- experiences: Work history. (MANDATORY: Capture start/end dates for timeline reconstruction).
- education: Educational history. (Capture dates of study).
- skills: Commercial and technical skills (Aggregate from all verified sources).
- projects: Notable public projects (MANDATORY: Capture dates to place on professional timeline).
- achievements: Publicly verifiable awards and recognitions (MANDATORY: Capture dates/year for chronological storytelling).
- certifications: Professional certifications.
- email: Professional contact email (Only if publicly visible).
- website: Personal website/Portfolio (PRIORITY: Search for this).
- linkedin: The correct LinkedIn URL.
- github: GitHub URL (Verify identity match carefully).
- social_links: Twitter/X, Medium, Substack (Verify identity).

**TIMELINE FOCUS:** 
The primary goal is to "retell the story" via a visual timeline and documentary video. For EVERY experience, achievement, and project, you MUST strive to find associated dates (Month/Year or just Year). A journey cannot be told without a chronological anchor.

**VERIFICATION:**
Before adding any field, ask: "Is this definitely the same person?"

Return a JSON object. Use null for missing string fields and empty arrays [] for missing list fields."""

            # Use Gemini 3 Pro with Search and URL Context
            # Using thinking_level="high" for better reasoning and data verification
            start_time = datetime.utcnow()
            logger.info(f"Sending prompt to Gemini 3 (thinking_level=high, deep_search=enabled)...")
            
            response = await asyncio.to_thread(
                self.genai_client.models.generate_content,
                model="gemini-3-pro-preview",
                contents=extraction_prompt,
                config=types.GenerateContentConfig(
                    tools=[{"url_context": {}}, {"google_search": {}}],  # Enable URL Context and Google Search
                    response_mime_type="application/json",
                    response_json_schema=profile_schema,
                    # Use high thinking level for reasoning and data aggregation
                    thinking_config=types.ThinkingConfig(thinking_level="high")
                )
            )
            
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"Gemini 3 response received in {elapsed:.2f} seconds")
            
            # Parse the response
            response_text = response.text.strip()
            
            # Clean up JSON if needed
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            try:
                extracted_data = json.loads(response_text)
                logger.info(f"Successfully extracted profile data from {url} using Gemini 3")
                
                # Validate and sanitize extracted data
                validated_data = self._validate_extracted_data(extracted_data, url)
                
                # Ensure all expected fields exist
                return self._normalize_extracted_data(validated_data)
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Gemini 3 response as JSON: {e}")
                logger.debug(f"Response text: {response_text[:500]}...")
                return self._get_empty_profile_data()
                
        except Exception as e:
            logger.error(f"Gemini 3 extraction failed for {url}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Gemini 3 extraction failed: {str(e)}"
            )
    
    def _validate_extracted_data(self, data: Dict[str, Any], source_url: str) -> Dict[str, Any]:
        """Validate extracted data for integrity and remove potentially hallucinated content.
        
        This method performs sanity checks to ensure data integrity:
        1. Removes entries that appear to be from different profiles
        2. Validates URL consistency
        3. Removes suspiciously generic or templated data
        
        Args:
            data: Raw extracted data from Gemini 3
            source_url: The original URL that was analyzed
            
        Returns:
            Validated and sanitized data dictionary
        """
        validated = data.copy()
        source_url_lower = source_url.lower()
        
        # Check if this is a LinkedIn URL and validate linkedin field
        if 'linkedin.com/in/' in source_url_lower:
            # Extract the profile identifier from the source URL
            try:
                profile_id = source_url_lower.split('linkedin.com/in/')[-1].split('/')[0].split('?')[0]
                # If we extracted a different LinkedIn URL, it might be wrong
                if validated.get('linkedin'):
                    extracted_linkedin = validated['linkedin'].lower()
                    if 'linkedin.com/in/' in extracted_linkedin:
                        extracted_id = extracted_linkedin.split('linkedin.com/in/')[-1].split('/')[0].split('?')[0]
                        if extracted_id != profile_id:
                            logger.warning(f"LinkedIn mismatch: source={profile_id}, extracted={extracted_id}")
                            validated['linkedin'] = source_url  # Use the source URL instead
                    else:
                        validated['linkedin'] = source_url
                else:
                    validated['linkedin'] = source_url
            except Exception:
                validated['linkedin'] = source_url
        
        # Check if this is a GitHub URL and validate github field
        if 'github.com/' in source_url_lower and '/github.com/' not in source_url_lower:
            try:
                # Extract username from GitHub URL
                parts = source_url_lower.replace('https://', '').replace('http://', '').split('/')
                if len(parts) >= 2 and parts[0] == 'github.com':
                    github_username = parts[1].split('?')[0]
                    if validated.get('github'):
                        extracted_github = validated['github'].lower()
                        if 'github.com/' in extracted_github:
                            extracted_parts = extracted_github.replace('https://', '').replace('http://', '').split('/')
                            if len(extracted_parts) >= 2:
                                extracted_username = extracted_parts[1].split('?')[0]
                                if extracted_username != github_username:
                                    logger.warning(f"GitHub mismatch: source={github_username}, extracted={extracted_username}")
                                    validated['github'] = source_url
                        else:
                            validated['github'] = source_url
                    else:
                        validated['github'] = source_url
            except Exception:
                pass
        
        # Validate experiences - remove entries with suspicious patterns
        if validated.get('experiences'):
            clean_experiences = []
            for exp in validated['experiences']:
                # Skip entries that look like templates or placeholders
                company = exp.get('company', '').lower()
                title = exp.get('title', '').lower()
                
                suspicious_patterns = [
                    'company name', 'your company', 'example', 'sample',
                    'lorem ipsum', 'placeholder', '[company]', '{company}'
                ]
                
                is_suspicious = any(pattern in company or pattern in title for pattern in suspicious_patterns)
                
                if not is_suspicious and (company or title):
                    clean_experiences.append(exp)
            
            validated['experiences'] = clean_experiences
        
        # Validate education - remove suspicious entries
        if validated.get('education'):
            clean_education = []
            for edu in validated['education']:
                institution = edu.get('institution', '').lower()
                degree = edu.get('degree', '').lower()
                
                suspicious_patterns = [
                    'university name', 'your university', 'example', 'sample',
                    'lorem ipsum', 'placeholder', '[university]', '{institution}'
                ]
                
                is_suspicious = any(pattern in institution or pattern in degree for pattern in suspicious_patterns)
                
                if not is_suspicious and (institution or degree):
                    clean_education.append(edu)
            
            validated['education'] = clean_education
        
        # Remove common hallucinated/generic skills if they seem out of place
        if validated.get('skills'):
            # Keep skills as-is but log for monitoring
            logger.debug(f"Extracted {len(validated['skills'])} skills from {source_url}")
        
        # Validate name is not suspiciously generic
        if validated.get('name'):
            name_lower = validated['name'].lower()
            generic_names = ['john doe', 'jane doe', 'user name', 'your name', 'full name', 'name here']
            if name_lower in generic_names:
                logger.warning(f"Suspicious generic name detected: {validated['name']}")
                validated['name'] = None
        
        return validated
    
    def _normalize_extracted_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize extracted data to ensure all expected fields exist.
        
        Args:
            data: Raw extracted data from Gemini 3
            
        Returns:
            Normalized data dictionary with all expected fields
        """
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
        """Return empty profile data structure.
        
        Returns:
            Empty profile data dictionary
        """
        return {
            "name": None,
            "title": None,
            "location": None,
            "bio": None,
            "experiences": [],
            "education": [],
            "skills": [],
            "projects": [],
            "achievements": [],
            "certifications": [],
            "email": None,
            "website": None,
            "linkedin": None,
            "github": None,
            "social_links": {}
        }


# Global service instance
profile_service = ProfileExtractionService()