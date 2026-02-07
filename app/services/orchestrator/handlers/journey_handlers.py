"""Aggregate History, Journey, Timeline, and Documentary Handlers.

Consolidated handlers for journey-related tasks.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List

from google.genai import types

from app.services.orchestrator.handlers.base import BaseTaskHandler
from app.services.orchestrator.models import Task, TaskPlan, TaskType
from app.services.orchestrator.utils.parsing import parse_and_validate_response
from app.prompts import (
    get_journey_structuring_prompt,
    get_timeline_generation_prompt,
    get_documentary_narrative_prompt,
    JourneyStructureResult,
    TimelineResult,
    DocumentaryResult,
    ProfileAggregationResult,
)

logger = logging.getLogger(__name__)


class AggregateHistoryHandler(BaseTaskHandler):
    """Handler for aggregating profile history."""
    
    async def execute(self, job_id: str, plan: TaskPlan, task: Task) -> Dict[str, Any]:
        """Handle history aggregation task."""
        from app.db.session import get_db
        from app.models.user import User, ProfileHistory
        from sqlalchemy import select
        
        task.message = "Checking for existing profile history..."
        task.progress = 20
        await self.update_progress(job_id, task)
        
        # Get enriched profile data from previous task
        profile_data = plan.result_data.get(TaskType.ENRICH_PROFILE.value)
        if not profile_data or not isinstance(profile_data, dict):
            profile_data = plan.result_data.get(TaskType.FETCH_PROFILE.value)
            
        if not profile_data or not isinstance(profile_data, dict):
            profile_data = {}
        
        guest_user_id = plan.options.get('guest_user_id')
        current_history_id = plan.options.get('history_id')
        
        if not guest_user_id:
            task.message = "No identifier found, skipping history check"
            task.progress = 100
            await self.update_progress(job_id, task)
            return {**profile_data, "history_checked": True, "aggregated": False}
        
        task.progress = 40
        task.message = "Querying for existing records..."
        await self.update_progress(job_id, task)
        
        async for db in get_db():
            try:
                user_query = select(User).where(User.guest_id == guest_user_id)
                result = await db.execute(user_query)
                user = result.scalar_one_or_none()
                
                if not user:
                    task.message = "Record not found, skipping history check"
                    task.progress = 100
                    await self.update_progress(job_id, task)
                    return {**profile_data, "history_checked": True, "aggregated": False, "error": "Record not found"}
                
                task.progress = 60
                task.message = f"Loading profile history for record..."
                await self.update_progress(job_id, task)
                
                history_query = select(ProfileHistory).where(
                    ProfileHistory.user_id == user.id
                ).order_by(ProfileHistory.created_at.desc())
                result = await db.execute(history_query)
                all_histories = result.scalars().all()
                
                # Exclude the current history record
                histories = [h for h in all_histories if h.id != current_history_id]
                
                scraped_content = profile_data.get('scraped_content', [])
                
                if not histories or len(histories) == 0:
                    # No previous history - check for scraped content enrichment
                    if scraped_content and len(scraped_content) > 0:
                        task.progress = 70
                        task.message = f"Enriching first record with {len(scraped_content)} scraped sources..."
                        await self.update_progress(job_id, task)
                        
                        if not self.genai_client:
                            raise Exception("Gemini client not initialized")
                        
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
                                    response_json_schema=ProfileAggregationResult.model_json_schema()
                                )
                            )
                        except Exception as e:
                            logger.warning(f"Gemini call failed: {e}, retrying")
                            response = await asyncio.to_thread(
                                self.genai_client.models.generate_content,
                                model="gemini-3-flash-preview",
                                contents=enrichment_prompt,
                                config=types.GenerateContentConfig(
                                    response_mime_type="application/json",
                                    response_json_schema=ProfileAggregationResult.model_json_schema()
                                )
                            )
                        
                        enriched_profile = parse_and_validate_response(
                            response.text,
                            ProfileAggregationResult,
                            fallback_to_dict=True
                        )
                        
                        if current_history_id:
                            current_history = await db.get(ProfileHistory, current_history_id)
                            if current_history:
                                current_history.structured_data = enriched_profile
                                await db.commit()
                                logger.info(f"Saved enriched first record to history {current_history_id}")
                        
                        task.progress = 100
                        task.message = "First record enriched with scraped content"
                        await self.update_progress(job_id, task)
                        
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
                        
                        task.progress = 100
                        await self.update_progress(job_id, task)
                        return {**profile_data, "history_checked": True, "aggregated": False, "first_record": True}
                
                # Aggregate with Gemini
                task.progress = 70
                task.message = f"Aggregating {len(histories)} previous records..."
                await self.update_progress(job_id, task)
                
                if not self.genai_client:
                    raise Exception("Gemini client not initialized")
                
                previous_profiles = []
                for h in histories:
                    profile_entry = {
                        "source": h.source_url or "unknown",
                        "date": h.created_at.isoformat() if h.created_at else None
                    }
                    if h.structured_data and isinstance(h.structured_data, dict):
                        profile_entry["data"] = h.structured_data
                    else:
                        profile_entry["data"] = {}
                    previous_profiles.append(profile_entry)
                
                previous_profiles = [
                    p for p in previous_profiles 
                    if p.get("data") and any(p["data"].values())
                ]
                
                aggregation_prompt = self._create_aggregation_prompt(
                    current_profile=profile_data,
                    previous_profiles=previous_profiles,
                    scraped_content=scraped_content
                )
                
                task.progress = 80
                task.message = "Processing aggregation..."
                await self.update_progress(job_id, task)
                
                try:
                    response = await asyncio.to_thread(
                        self.genai_client.models.generate_content,
                        model="gemini-3-flash-preview",
                        contents=aggregation_prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_json_schema=ProfileAggregationResult.model_json_schema(),
                        )
                    )
                except Exception as e:
                    logger.warning(f"Aggregation failed: {e}, retrying")
                    response = await asyncio.to_thread(
                        self.genai_client.models.generate_content,
                        model="gemini-2.5-flash",
                        contents=aggregation_prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_json_schema=ProfileAggregationResult.model_json_schema()
                        )
                    )
                
                aggregated_data = parse_and_validate_response(
                    response.text,
                    ProfileAggregationResult,
                    fallback_to_dict=True
                )
                
                # Update the current history record
                if current_history_id:
                    current_history = await db.get(ProfileHistory, current_history_id)
                    if current_history:
                        current_history.structured_data = aggregated_data
                        current_history.raw_data = profile_data
                        await db.commit()
                
                task.progress = 100
                task.message = "Successfully aggregated profile history"
                await self.update_progress(job_id, task)
                
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
                return {**profile_data, "history_checked": True, "aggregated": False, "error": str(e)}
            finally:
                break
    
    def _create_aggregation_prompt(
        self, 
        current_profile: Dict[str, Any], 
        previous_profiles: List[Dict[str, Any]],
        scraped_content: List[Dict[str, Any]] = None
    ) -> str:
        """Create prompt for profile aggregation."""
        cleaned_profile = {
            k: v for k, v in current_profile.items() 
            if k not in ['scraped_content', 'enrichment_stats', 'github_data', 'enriched', 
                        'enrichment_timestamp', 'history_checked', 'aggregated']
            and v is not None
        }
        
        previous_section = ""
        if previous_profiles and len(previous_profiles) > 0:
            valid_previous = [
                p for p in previous_profiles 
                if p.get("data") and isinstance(p["data"], dict) and len(p["data"]) > 0
            ]
            if valid_previous:
                previous_section = f"""
**Previous Profile Records ({len(valid_previous)} records):**
```json
{json.dumps(valid_previous, indent=2, default=str)}
```
"""
        
        scraped_section = ""
        if scraped_content and len(scraped_content) > 0:
            scraped_section = f"""
**Enrichment Data from Web Scraping ({len(scraped_content)} sources):**
```json
{json.dumps(scraped_content, indent=2, default=str)}
```
"""
        
        return f"""You are an expert at aggregating professional profile data.

**Current Profile Data:**
```json
{json.dumps(cleaned_profile, indent=2, default=str)}
```
{previous_section}
{scraped_section}

**Task:**
Aggregate and merge all profile data to create a comprehensive professional profile following these guidelines:
1. Chronological Integration
2. Scraped Content Integration
3. Skill Evolution
4. Career Progression
5. Completeness
6. Deduplication

Return a comprehensive JSON object with the aggregated profile.
"""


class StructureJourneyHandler(BaseTaskHandler):
    """Handler for structuring journey."""
    
    async def execute(self, job_id: str, plan: TaskPlan, task: Task) -> Dict[str, Any]:
        """Handle journey structuring task."""
        task.message = "Creating narrative structure..."
        task.progress = 20
        await self.update_progress(job_id, task)

        if not self.genai_client:
            raise Exception("Gemini client not initialized")

        profile_data = plan.result_data.get(TaskType.AGGREGATE_HISTORY.value)
        if not profile_data:
            profile_data = plan.result_data.get(TaskType.ENRICH_PROFILE.value)
        if not profile_data:
            profile_data = plan.result_data.get(TaskType.FETCH_PROFILE.value)

        task.progress = 50
        task.message = "Generating journey chapters..."
        await self.update_progress(job_id, task)
        
        prompt = get_journey_structuring_prompt(profile_data)

        try:
            response = await asyncio.to_thread(
                self.genai_client.models.generate_content,
                model="gemini-3-flash-preview",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_json_schema=JourneyStructureResult.model_json_schema(),
                )
            )
        except Exception as e:
            logger.error(f"Journey structuring failed: {e}")
            return self._create_fallback_journey(profile_data)

        task.progress = 80
        task.message = "Finalising journey structure..."
        await self.update_progress(job_id, task)

        result = parse_and_validate_response(
            response.text,
            JourneyStructureResult,
            fallback_to_dict=True
        )
        
        # Save to database
        current_history_id = plan.options.get('history_id')
        if current_history_id:
            try:
                from app.db.session import get_db
                from app.models.user import ProfileHistory
                
                async for db in get_db():
                    current_history = await db.get(ProfileHistory, current_history_id)
                    if current_history:
                        if isinstance(current_history.structured_data, dict):
                            updated_data = current_history.structured_data.copy()
                        else:
                            updated_data = {}
                        updated_data['journey'] = result
                        current_history.structured_data = updated_data
                        
                        await db.commit()
                        logger.info(f"Saved journey data to history {current_history_id}")
                    break
            except Exception as db_error:
                logger.error(f"Failed to save journey data: {db_error}")
        
        return result
    
    def _create_fallback_journey(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a fallback journey structure when AI fails."""
        return {
            "summary": {
                "headline": profile_data.get('name', 'Professional') + " Journey",
                "narrative": "Unable to generate journey narrative",
                "career_span": "Unknown",
                "key_themes": profile_data.get('skills', [])[:3] if profile_data.get('skills') else []
            },
            "milestones": [],
            "career_chapters": [],
            "skills_evolution": [],
            "impact_metrics": {},
            "error": "AI processing failed"
        }


class GenerateTimelineHandler(BaseTaskHandler):
    """Handler for generating timeline."""
    
    async def execute(self, job_id: str, plan: TaskPlan, task: Task) -> Dict[str, Any]:
        """Handle timeline generation task."""
        task.message = "Building interactive timeline..."
        task.progress = 30
        await self.update_progress(job_id, task)
        
        if not self.genai_client:
            raise Exception("Gemini client not initialized")
        
        journey_data = plan.result_data.get(TaskType.STRUCTURE_JOURNEY.value, {})
        prompt = get_timeline_generation_prompt(journey_data)
        
        task.progress = 60
        task.message = "Generating timeline events..."
        await self.update_progress(job_id, task)
        
        try:
            response = await asyncio.to_thread(
                self.genai_client.models.generate_content,
                model="gemini-3-flash-preview",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_json_schema=TimelineResult.model_json_schema(),
                )
            )
        except Exception as e:
            logger.error(f"Timeline generation failed: {e}")
            raise
        
        result = parse_and_validate_response(
            response.text,
            TimelineResult,
            fallback_to_dict=True
        )
        
        # Save to database
        current_history_id = plan.options.get('history_id')
        if current_history_id:
            try:
                from app.db.session import get_db
                from app.models.user import ProfileHistory
                
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
                    break
            except Exception as db_error:
                logger.error(f"Failed to save timeline data: {db_error}")

        return result


class GenerateDocumentaryHandler(BaseTaskHandler):
    """Handler for generating documentary."""
    
    async def execute(self, job_id: str, plan: TaskPlan, task: Task) -> Dict[str, Any]:
        """Handle documentary narrative generation task."""
        task.message = "Crafting documentary narrative..."
        task.progress = 20
        await self.update_progress(job_id, task)
        
        if not self.genai_client:
            raise Exception("Gemini client not initialized")
        
        # Check if running in standalone mode (compute_documentary_only)
        is_standalone = plan.options.get("compute_documentary_only", False)
        current_history_id = plan.options.get('history_id')
        
        if is_standalone and current_history_id:
            # Load profile and journey data from database
            task.message = "Loading profile data..."
            task.progress = 25
            await self.update_progress(job_id, task)
            
            journey_data = {}
            profile_data = {}
            
            try:
                from app.db.session import get_db
                from app.models.user import ProfileHistory
                
                async for db in get_db():
                    current_history = await db.get(ProfileHistory, current_history_id)
                    if current_history and current_history.structured_data:
                        structured = current_history.structured_data
                        journey_data = structured.get('journey', {})
                        # Profile data is at the root level of structured_data
                        profile_data = {k: v for k, v in structured.items() 
                                       if k not in ['journey', 'timeline', 'documentary', 'generated_at', 'generation_status']}
                    break
            except Exception as db_error:
                logger.error(f"Failed to load profile data: {db_error}")
                raise Exception(f"Failed to load profile data: {str(db_error)}")
            
            if not profile_data.get('name'):
                raise Exception("No profile data found. Please generate a profile first.")
        else:
            # Get data from previous tasks in the pipeline
            journey_data = plan.result_data.get(TaskType.STRUCTURE_JOURNEY.value, {})
            profile_data = (
                plan.result_data.get(TaskType.AGGREGATE_HISTORY.value) or 
                plan.result_data.get(TaskType.ENRICH_PROFILE.value) or 
                plan.result_data.get(TaskType.FETCH_PROFILE.value) or 
                {}
            )
        
        prompt = get_documentary_narrative_prompt(journey_data, profile_data)
        
        task.progress = 50
        task.message = "Writing documentary segments..."
        await self.update_progress(job_id, task)
        
        try:
            response = await asyncio.to_thread(
                self.genai_client.models.generate_content,
                model="gemini-3-flash-preview",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_json_schema=DocumentaryResult.model_json_schema()
                )
            )
        except Exception as e:
            logger.error(f"Documentary generation failed: {e}")
            return {
                "title": "Professional Journey",
                "tagline": "A professional story",
                "duration_estimate": "32 seconds", 
                "segments": [],
                "opening_hook": "Welcome to my professional journey.",
                "closing_statement": "Thank you for watching.",
                "error": f"Generation failed: {str(e)}"
            }
        
        task.progress = 80
        task.message = "Finalising documentary structure..."
        await self.update_progress(job_id, task)
        
        result = parse_and_validate_response(
            response.text,
            DocumentaryResult,
            fallback_to_dict=True
        )
        
        # Validate that segments were generated
        segments = result.get('segments', [])
        if not segments or len(segments) == 0:
            logger.error("Documentary generation returned no segments")
            raise Exception("Documentary generation failed: No video segments were generated. Please try again.")
        
        # Validate each segment has required fields
        valid_segments = []
        for seg in segments:
            if isinstance(seg, dict) and seg.get('visual_description') and seg.get('narration'):
                valid_segments.append(seg)
            else:
                logger.warning(f"Skipping invalid segment: {seg}")
        
        if not valid_segments:
            logger.error("All segments were invalid")
            raise Exception("Documentary generation failed: No valid video segments with narration and visuals were generated.")
        
        result['segments'] = valid_segments
        logger.info(f"Documentary generated with {len(valid_segments)} valid segments")
        
        task.progress = 90
        task.message = f"Saving documentary ({len(valid_segments)} segments)..."
        await self.update_progress(job_id, task)
        
        # Save to database
        current_history_id = plan.options.get('history_id')
        if current_history_id:
            try:
                from app.db.session import get_db
                from app.models.user import ProfileHistory
                from sqlalchemy.orm.attributes import flag_modified
                
                async for db in get_db():
                    current_history = await db.get(ProfileHistory, current_history_id)
                    if current_history:
                        if isinstance(current_history.structured_data, dict):
                            updated_data = current_history.structured_data.copy()
                        else:
                            updated_data = {}
                        updated_data['documentary'] = result
                        current_history.structured_data = updated_data
                        
                        # Mark the JSON column as modified so SQLAlchemy detects the change
                        flag_modified(current_history, 'structured_data')
                        
                        await db.commit()
                        logger.info(f"Documentary saved to database for history {current_history_id}")
                    break
            except Exception as db_error:
                logger.error(f"Failed to save documentary data: {db_error}")
                raise Exception(f"Failed to save documentary: {str(db_error)}")
        
        task.progress = 100
        task.message = "Documentary complete!"
        await self.update_progress(job_id, task)

        return result
