"""Video Generation Handler.

Handles video generation using Veo 3.1.
"""

import logging
from typing import Dict, Any

from app.services.orchestrator.handlers.base import BaseTaskHandler
from app.services.orchestrator.models import Task, TaskPlan, TaskType, TaskStatus
from app.prompts.video_prompts import (
    get_character_bible,
    build_veo_segment_prompt,
    validate_segment_for_veo,
)

logger = logging.getLogger(__name__)


class GenerateVideoHandler(BaseTaskHandler):
    """Handler for video generation using Veo 3.1."""
    
    async def execute(self, job_id: str, plan: TaskPlan, task: Task) -> Dict[str, Any]:
        """Handle video generation task using Veo 3.1."""
        from app.services.video_generator import video_generator
        from app.db.session import get_db
        from app.models.user import ProfileHistory
        
        task.message = "Preparing video documentary..."
        task.progress = 10
        await self.update_progress(job_id, task)
        
        documentary_data = plan.result_data.get(TaskType.GENERATE_DOCUMENTARY.value, {})
        
        # If running in isolation, fetch documentary data from DB
        current_history_id = plan.options.get('history_id')
        if not documentary_data and current_history_id:
            try:
                async for db in get_db():
                    current_history = await db.get(ProfileHistory, current_history_id)
                    if current_history and current_history.structured_data:
                        documentary_data = current_history.structured_data.get('documentary', {})
                        logger.info(f"Loaded documentary from history {current_history_id}")
                    break
            except Exception as db_error:
                logger.error(f"Failed to load history for video gen: {db_error}")

        segments = documentary_data.get("segments", [])
        logger.info(f"Found {len(segments)} segments for video generation")

        if not segments:
            task.message = "No segments found for video generation"
            task.status = TaskStatus.SKIPPED
            return {"status": "skipped", "reason": "no segments"}
        
        # Check if we should generate only first segment or full segments
        video_settings = plan.options.get('video_settings', {})
        generate_first_only = video_settings.get('first_segment_only', True)
        
        if generate_first_only:
            segments = segments[:1]
            logger.info("Generating first segment only as requested")
        else:
            logger.info(f"Generating all {len(segments)} segments")
        
        # Get journey and profile data for character bible
        journey_data = await self._load_journey_data(plan, current_history_id)
        profile_data = await self._load_profile_data(plan, current_history_id)
        
        # Build character bible
        character_bible = self._build_character_bible(profile_data, journey_data)
        logger.info(f"Generated character bible for {profile_data.get('name', 'subject')}")
        
        # Process segments
        generated_segments = []
        segment_filenames = []
        video_files = []
        valid_segments = 0
        skipped_segments = 0
        
        for i, seg in enumerate(segments):
            logger.info(f"Segment {i}: {seg}")
            
            # Validate segment
            is_valid, error_msg = validate_segment_for_veo(seg)
            if not is_valid:
                logger.warning(f"Skipping segment {i}: {error_msg}")
                skipped_segments += 1
                continue
            
            # Build prompt
            prompt = build_veo_segment_prompt(
                segment=seg,
                character_bible=character_bible,
                include_character_bible=False
            )
            
            if not prompt:
                logger.warning(f"Skipping segment {i}: Unable to build valid prompt")
                skipped_segments += 1
                continue
            
            valid_segments += 1
            seg_id = seg.get("id", f"seg_{i+1:02d}")
            
            task.message = f"Generating video segment {valid_segments}..."
            await self.update_progress(job_id, task)
            
            try:
                video_ref = video_files[-1] if valid_segments > 1 and video_files else None
                
                filename, video_object = await video_generator.generate_segment(
                    self.genai_client,
                    prompt=prompt,
                    duration_seconds=8,
                    video_reference=video_ref
                )
                
                segment_url = video_generator.get_url(filename)
                segment_filenames.append(filename)
                video_files.append(video_object)
                
                generated_segments.append({
                    "segment_index": i,
                    "segment_id": seg_id,
                    "url": segment_url,
                    "filename": filename
                })
                
                # Save to database
                if current_history_id:
                    await self._save_segment_to_db(current_history_id, segment_url, valid_segments)
                
                task.progress = 10 + int(valid_segments * 70)
                await self.update_progress(job_id, task)
                
            except Exception as e:
                logger.error(f"Failed to generate segment {i} ({seg_id}): {e}")
        
        logger.info(f"Video generation: {valid_segments} generated, {skipped_segments} skipped")
        
        if not generated_segments:
            raise Exception(f"Video generation failed for all segments.")

        # Merge segments if needed
        task.message = "Merging video segments..."
        task.progress = 85
        await self.update_progress(job_id, task)
        
        final_video_url = None
        try:
            if len(generated_segments) > 1:
                stitched_filename = await video_generator.stitch_videos(segment_filenames)
                final_video_url = video_generator.get_url(stitched_filename)
            elif len(generated_segments) == 1:
                final_video_url = generated_segments[0]["url"]
        except Exception as e:
            logger.error(f"Merging failed: {e}")
            if generated_segments:
                final_video_url = generated_segments[0]["url"]

        # Save final video
        if current_history_id and final_video_url:
            await self._save_final_video_to_db(current_history_id, final_video_url)
        
        return {
            "video_ready": True,
            "segments_generated": len(generated_segments),
            "full_video_url": final_video_url,
            "segment_urls": [seg["url"] for seg in generated_segments],
            "generated_first_only": generate_first_only
        }
    
    async def _load_journey_data(self, plan: TaskPlan, current_history_id: str) -> Dict[str, Any]:
        """Load journey data from plan or database."""
        journey_data = plan.result_data.get(TaskType.STRUCTURE_JOURNEY.value, {})
        if not journey_data and current_history_id:
            try:
                from app.db.session import get_db
                from app.models.user import ProfileHistory
                
                async for db in get_db():
                    current_history = await db.get(ProfileHistory, current_history_id)
                    if current_history and current_history.structured_data:
                        journey_data = current_history.structured_data.get('journey', {})
                    break
            except Exception as e:
                logger.error(f"Failed to load journey data: {e}")
        return journey_data
    
    async def _load_profile_data(self, plan: TaskPlan, current_history_id: str) -> Dict[str, Any]:
        """Load profile data from plan or database."""
        profile_data = plan.result_data.get(TaskType.ENRICH_PROFILE.value, {})
        if not profile_data and current_history_id:
            try:
                from app.db.session import get_db
                from app.models.user import ProfileHistory
                
                async for db in get_db():
                    current_history = await db.get(ProfileHistory, current_history_id)
                    if current_history and current_history.structured_data:
                        profile_data = current_history.structured_data or {}
                    break
            except Exception as e:
                logger.error(f"Failed to load profile data: {e}")
        return profile_data
    
    def _build_character_bible(self, profile_data: Dict[str, Any], journey_data: Dict[str, Any]) -> str:
        """Build character bible for consistent identity."""
        name = profile_data.get('name', 'the subject')
        summary = journey_data.get('summary') or {}
        headline = summary.get('headline') if isinstance(summary, dict) else None
        title = headline or profile_data.get('title')
        
        # Infer industry from experiences
        industry = None
        experiences = profile_data.get('experiences', [])
        if experiences and len(experiences) > 0:
            recent_exp = experiences[0]
            if isinstance(recent_exp, dict):
                exp_title = recent_exp.get('title', '').lower()
                if any(word in exp_title for word in ['engineer', 'developer', 'software', 'tech']):
                    industry = 'Technology'
                elif any(word in exp_title for word in ['finance', 'bank', 'investment']):
                    industry = 'Finance'
                elif any(word in exp_title for word in ['healthcare', 'medical', 'doctor', 'nurse']):
                    industry = 'Healthcare'
                elif any(word in exp_title for word in ['design', 'creative', 'artist']):
                    industry = 'Creative'
                elif any(word in exp_title for word in ['teacher', 'professor', 'education']):
                    industry = 'Education'
        
        return get_character_bible(
            name=name,
            headline=headline,
            title=title,
            industry=industry
        )
    
    async def _save_segment_to_db(self, history_id: str, segment_url: str, segment_num: int) -> None:
        """Save segment URL to database."""
        try:
            from app.db.session import get_db
            from app.models.user import ProfileHistory
            
            async for db in get_db():
                current_history = await db.get(ProfileHistory, history_id)
                if current_history:
                    if current_history.segment_videos is None:
                        current_history.segment_videos = []
                    current_history.segment_videos.append(segment_url)
                    await db.commit()
                    logger.info(f"Saved segment {segment_num} URL to database")
                break
        except Exception as e:
            logger.error(f"Failed to save segment to DB: {e}")
    
    async def _save_final_video_to_db(self, history_id: str, final_video_url: str) -> None:
        """Save final video URL to database."""
        try:
            from app.db.session import get_db
            from app.models.user import ProfileHistory
            
            async for db in get_db():
                current_history = await db.get(ProfileHistory, history_id)
                if current_history:
                    current_history.full_video = final_video_url
                    await db.commit()
                    logger.info(f"Saved full video URL to history {history_id}")
                break
        except Exception as e:
            logger.error(f"Failed to save final video URL to DB: {e}")
