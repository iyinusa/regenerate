"""Profile API routes."""

import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
import time

from fastapi import APIRouter, HTTPException, status, Depends, File, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.profile import (
    ProfileGenerateRequest,
    ProfileGenerateResponse, 
    ProfileStatusResponse,
    ProfileStatus,
    TaskInfo,
    ProfileHistoryResponse,
    ProfileHistoryUpdate,
    VideoGenerateRequest
)
import time
from app.services.profile_service import profile_service
from app.services.task_orchestrator import task_orchestrator
from app.services.storage_service import gcs_storage
from app.db.session import get_db
from app.core.dependencies import get_current_user_required
from app.core.config import settings
from app.models.user import User, ProfileHistory

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/profile", tags=["profile"])

# Track active video generation requests to prevent duplicates
# Format: {history_id: (job_id, timestamp)}
_active_video_generations: Dict[str, tuple] = {}
VIDEO_GENERATION_COOLDOWN = 30  # seconds before allowing another request for same history


@router.post(
    "/passport/upload",
    response_model=Dict[str, str],
    summary="Upload Passport Image",
    description="Upload a passport image to GCS and return the public URL."
)
async def upload_passport(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user_required)
):
    """
    Upload a passport image to GCS and return the public URL.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Generate unique filename
    extension = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    filename = f"passport_{int(time.time())}.{extension}"
    
    try:
        url = await gcs_storage.upload_file_object(
            file.file,
            str(current_user.id),
            filename,
            file.content_type,
            folder="passports"
        )
        return {"url": url}
    except Exception as e:
        logger.error(f"Failed to upload passport: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/passport/{history_id}",
    response_model=Dict[str, Any],
    summary="Update Passport URL",
    description="Update the passport URL in the profile history structured data."
)
async def update_passport(
    history_id: str,
    data: Dict[str, str],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_required)
):
    """Update profile passport URL."""
    # Check if history exists and belongs to user
    history = await db.get(ProfileHistory, history_id)
    if not history:
        raise HTTPException(status_code=404, detail="Profile history not found")
        
    if history.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if "passport" not in data:
        raise HTTPException(status_code=400, detail="Passport URL required")
        
    # Update structured data - save passport at ROOT level (not under profile)
    structured_data = history.structured_data if history.structured_data else {}
    # Make a copy to avoid mutation issues
    structured_data = dict(structured_data)
    structured_data["passport"] = data["passport"]
    
    # Log for debugging
    logger.info(f"Updating passport for history {history_id}: {data['passport']}")
    logger.info(f"Structured data keys after update: {list(structured_data.keys())}")
    
    history.structured_data = structured_data
    await db.commit()
    await db.refresh(history)
    
    logger.info(f"Passport saved successfully. Returning: {structured_data.get('passport')}")
    return {"passport": structured_data["passport"]}


@router.post(
    "/resume/upload",
    response_model=Dict[str, str],
    summary="Upload Resume PDF",
    description="Upload a resume PDF to GCS and return the public URL for profile extraction."
)
async def upload_resume(
    file: UploadFile = File(...),
):
    """
    Upload a resume PDF to GCS and return the public URL.
    This endpoint is accessible to guests (no auth required) for initial profile creation.
    """
    # Validate file type
    if not file.content_type or file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400, 
            detail="File must be a PDF document"
        )
    
    # Validate file size (max 10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="File size exceeds maximum limit of 10MB"
        )
    
    # Reset file pointer for upload
    await file.seek(0)
    
    # Generate unique filename
    from io import BytesIO
    import uuid
    file_id = uuid.uuid4().hex[:12]
    filename = f"resume_{file_id}_{int(time.time())}.pdf"
    
    try:
        # Upload to GCS in resumes folder
        # Use a generic folder for guest uploads
        url = await gcs_storage.upload_file_object(
            BytesIO(content),
            "uploads",  # Generic folder for guest resume uploads
            filename,
            "application/pdf",
            folder="resumes"
        )
        logger.info(f"Resume uploaded successfully: {url}")
        return {"url": url, "filename": filename}
    except Exception as e:
        logger.error(f"Failed to upload resume: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload resume: {str(e)}")


@router.post(
    "/generate",
    response_model=ProfileGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start Profile Generation",
    description="Initiate the profile data extraction and analysis process from a URL or uploaded resume PDF with CoT task planning."
)
async def generate_profile(
    request: ProfileGenerateRequest,
    db: AsyncSession = Depends(get_db)
) -> ProfileGenerateResponse:
    """Generate profile from URL or Resume PDF with Chain of Thought task planning.
    
    This endpoint supports two source types:
    1. URL: LinkedIn, Portfolio, GitHub, or other professional profile URLs
    2. Resume: Uploaded PDF resume (use /resume/upload first to get the file URL)
    
    The endpoint:
    1. Creates a task plan using CoT reasoning
    2. Starts background execution of tasks
    3. Returns job ID for tracking progress via polling or WebSocket
    
    Connect to WebSocket at /api/v1/ws/tasks/{job_id} for real-time updates.
    
    Args:
        request: Profile generation request with URL/resume and options
        db: Database session
        
    Returns:
        Response with job ID and initial status
    """
    from app.schemas.profile import ProfileSourceType
    
    try:
        # Validate request based on source type
        source_type = request.source_type
        
        if source_type == ProfileSourceType.URL:
            if not request.url:
                raise HTTPException(
                    status_code=400,
                    detail="URL is required when source_type is 'url'"
                )
            source_identifier = request.url
            logger.info(f"Starting profile generation from URL: {request.url}")
        elif source_type == ProfileSourceType.RESUME:
            if not request.resume_file_url:
                raise HTTPException(
                    status_code=400,
                    detail="resume_file_url is required when source_type is 'resume'"
                )
            source_identifier = request.resume_file_url
            logger.info(f"Starting profile generation from Resume: {request.resume_file_url}")
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid source_type: {source_type}"
            )
        
        # Start the extraction process with orchestrator
        job_id = await profile_service.start_profile_extraction(
            url=source_identifier,
            guest_user_id=request.guest_user_id,
            db=db,
            include_github=request.include_github,
            use_orchestrator=True,
            source_type=source_type.value  # Pass source type to service
        )
        
        return ProfileGenerateResponse(
            job_id=job_id,
            status=ProfileStatus.PROCESSING,
            message="Task plan created. Connect to WebSocket for real-time updates."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start profile generation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start profile generation: {str(e)}"
        )


@router.post(
    "/{history_id}/generate-video",
    response_model=ProfileGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start Video Generation",
    description="Initiate the video generation process for a profile history in the background."
)
async def generate_video(
    history_id: str,
    request: VideoGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_required)
) -> Dict[str, Any]:
    """Generate video documentary for a profile history.
    
    This endpoint starts a background video generation task that continues
    even if the user disconnects. The task will:
    
    1. Generate video segments (first only or all based on generate_full)
    2. Upload each segment to GCS as it's generated
    3. Update database after each segment
    4. Merge all segments into final video (if generate_full=True)
    5. Clean up segment videos (keeping first segment as intro)
    
    Args:
        history_id: ID of the profile history
        request: Video generation settings (generate_full flag)
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Response with task ID for tracking progress
    """
    try:
        # Check if history exists and belongs to user
        history = await db.get(ProfileHistory, history_id)
        if not history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Profile history not found: {history_id}"
            )
        
        # Verify ownership
        if current_user and history.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to generate video for this profile"
            )
        
        # Check if documentary data exists
        if not history.structured_data or not history.structured_data.get("documentary"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No documentary data found. Generate profile first."
            )
        
        documentary = history.structured_data.get("documentary", {})
        segments = documentary.get("segments", [])
        
        if not segments:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No video segments found in documentary data"
            )
        
        # Check for duplicate/rapid requests for the same history_id
        current_time = time.time()
        if history_id in _active_video_generations:
            existing_job_id, request_time = _active_video_generations[history_id]
            elapsed = current_time - request_time
            
            # Check if the existing job is still running
            existing_plan = task_orchestrator.get_plan(existing_job_id)
            if existing_plan and existing_plan.status.value in ['pending', 'running']:
                logger.warning(
                    f"Duplicate video generation request for history {history_id} "
                    f"(existing job: {existing_job_id}, elapsed: {elapsed:.1f}s)"
                )
                # Return the existing job info instead of creating a new one
                return {
                    "job_id": existing_job_id,
                    "status": "already_processing",
                    "message": "Video generation already in progress",
                    "total_segments": 1 if request.first_segment_only else len(segments),
                    "estimate_minutes": 1 if request.first_segment_only else len(segments)
                }
            
            # If within cooldown period but job completed/failed, allow new request
            if elapsed < VIDEO_GENERATION_COOLDOWN:
                logger.warning(
                    f"Video generation request within cooldown for history {history_id} "
                    f"(elapsed: {elapsed:.1f}s, cooldown: {VIDEO_GENERATION_COOLDOWN}s)"
                )
        
        logger.info(f"Starting video generation for history: {history_id}")
        logger.info(f"First segment only: {request.first_segment_only}, Total segments: {len(segments)}")
        
        # Create task orchestrator plan for video generation
        import uuid
        job_id = f"video_{uuid.uuid4().hex[:8]}"
        
        # Use task orchestrator for video generation (runs async in background)
        plan = task_orchestrator.create_plan(
            job_id=job_id,
            source_url=f"history:{history_id}",
            options={
                "generate_video_only": True,
                "history_id": history_id,
                "user_id": history.user_id,
                "video_settings": {
                    "first_segment_only": request.first_segment_only,
                    "resolution": request.export_format,
                    "aspect_ratio": request.aspect_ratio
                }
            }
        )
        
        # Execute plan in background (non-blocking)
        import asyncio
        asyncio.create_task(task_orchestrator.execute_plan(job_id))
        
        # Track this video generation request
        _active_video_generations[history_id] = (job_id, time.time())
        
        segment_count = 1 if request.first_segment_only else len(segments)
        
        return {
            "job_id": job_id,
            "status": "processing",
            "message": "Video generation started",
            "total_segments": segment_count,
            "estimate_minutes": segment_count  # ~1 min per segment
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start video generation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start video generation: {str(e)}"
        )


# Track active documentary generation requests to prevent duplicates
_active_documentary_generations: Dict[str, tuple] = {}
DOCUMENTARY_GENERATION_COOLDOWN = 30  # seconds before allowing another request


@router.post(
    "/{history_id}/compute-documentary",
    response_model=Dict[str, Any],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Compute Documentary Content",
    description="Trigger the Task Orchestrator to compute documentary content (narrative and segments) for a profile."
)
async def compute_documentary(
    history_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_required)
) -> Dict[str, Any]:
    """Compute documentary content for a profile history.
    
    This endpoint triggers the GENERATE_DOCUMENTARY task in the Task Orchestrator
    to create the documentary narrative and video segments script based on the
    existing profile and journey data.
    
    This is useful when the documentary wasn't computed during the initial profile
    generation, or when the user wants to regenerate the documentary content.
    
    Args:
        history_id: ID of the profile history
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Response with task ID for tracking progress
    """
    try:
        # Check if history exists and belongs to user
        history = await db.get(ProfileHistory, history_id)
        if not history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Profile history not found: {history_id}"
            )
        
        # Verify ownership
        if current_user and history.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to generate documentary for this profile"
            )
        
        # Check if profile data exists
        if not history.structured_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No profile data found. Generate profile first."
            )
        
        # Check for duplicate/rapid requests
        current_time = time.time()
        if history_id in _active_documentary_generations:
            existing_job_id, request_time = _active_documentary_generations[history_id]
            elapsed = current_time - request_time
            
            existing_plan = task_orchestrator.get_plan(existing_job_id)
            if existing_plan and existing_plan.status.value in ['pending', 'running']:
                logger.warning(
                    f"Duplicate documentary generation request for history {history_id} "
                    f"(existing job: {existing_job_id}, elapsed: {elapsed:.1f}s)"
                )
                return {
                    "job_id": existing_job_id,
                    "status": "already_processing",
                    "message": "Documentary computation already in progress"
                }
            
            if elapsed < DOCUMENTARY_GENERATION_COOLDOWN:
                logger.warning(
                    f"Documentary generation request within cooldown for history {history_id}"
                )
        
        logger.info(f"Starting documentary computation for history: {history_id}")
        
        # Create task orchestrator plan for documentary generation only
        import uuid
        job_id = f"doc_{uuid.uuid4().hex[:8]}"
        
        plan = task_orchestrator.create_plan(
            job_id=job_id,
            source_url=f"history:{history_id}",
            options={
                "compute_documentary_only": True,
                "history_id": history_id,
                "user_id": history.user_id,
            }
        )
        
        # Execute plan in background
        import asyncio
        asyncio.create_task(task_orchestrator.execute_plan(job_id))
        
        # Track this documentary generation request
        _active_documentary_generations[history_id] = (job_id, time.time())
        
        return {
            "job_id": job_id,
            "status": "processing",
            "message": "Documentary computation started"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start documentary computation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start documentary computation: {str(e)}"
        )


@router.get(
    "/status/{job_id}",
    response_model=ProfileStatusResponse,
    summary="Get Profile Generation Status",
    description="Check the status and progress of a profile generation job including task details."
)
async def get_profile_status(
    job_id: str,
    db: AsyncSession = Depends(get_db)
) -> ProfileStatusResponse:
    """Get profile generation status with task details.
    
    Returns the current status of all tasks in the execution pipeline,
    including individual task progress and any extracted data.
    
    For real-time updates, connect to WebSocket at /api/v1/ws/tasks/{job_id}
    
    Args:
        job_id: The job identifier returned from the generate endpoint
        db: Database session for recovery
        
    Returns:
        Current job status with task details and extracted data
    """
    try:
        job_data = await profile_service.get_job_status(job_id, db=db)
        
        # Convert task dictionaries to TaskInfo objects
        tasks = None
        if job_data.get("tasks"):
            tasks = [TaskInfo(**t) for t in job_data["tasks"]]
        
        return ProfileStatusResponse(
            job_id=job_id,
            status=job_data["status"],
            progress=job_data["progress"],
            message=job_data["message"],
            current_task=job_data.get("current_task"),
            tasks=tasks,
            data=job_data.get("data"),
            journey=job_data.get("journey"),
            timeline=job_data.get("timeline"),
            documentary=job_data.get("documentary"),
            error=job_data.get("error")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get profile status for job {job_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get profile status: {str(e)}"
        )


@router.get(
    "/tasks/{job_id}",
    summary="Get Task Details",
    description="Get detailed information about all tasks in the execution plan."
)
async def get_task_details(job_id: str) -> Dict[str, Any]:
    """Get detailed task information for a job.
    
    Returns the complete task plan with detailed status for each task,
    including timing information and outputs.
    
    Args:
        job_id: The job identifier
        
    Returns:
        Detailed task plan information
    """
    try:
        plan_status = task_orchestrator.get_plan_status(job_id)
        
        if not plan_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task plan not found"
            )
        
        return plan_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task details for job {job_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task details: {str(e)}"
        )


@router.get(
    "/video-status/{job_id}",
    summary="Get Video Generation Status",
    description="Check the status of a video generation job."
)
async def get_video_status(job_id: str) -> Dict[str, Any]:
    """Get video generation task status.
    
    Returns current progress, segment URLs, and final video URL when complete.
    
    Args:
        job_id: Video generation job ID from generate-video endpoint
        
    Returns:
        Task status with progress and video URLs
    """
    try:
        # Get status from task orchestrator
        plan = task_orchestrator.get_plan(job_id)
        
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video generation job not found"
            )
        
        # Get video result data from the plan
        video_result = plan.result_data.get("generate_video", {})
        
        return {
            "job_id": job_id,
            "status": plan.status.value,
            "progress": plan.progress,
            "message": plan.tasks[0].message if plan.tasks else "Processing...",
            "full_video_url": video_result.get("full_video_url"),
            "intro_video_url": video_result.get("intro_video_url"),
            "segment_urls": video_result.get("segment_urls", []),
            "segments_generated": video_result.get("segments_generated", 0),
            "generated_first_only": video_result.get("generated_first_only", True)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get video status for task {job_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get video status: {str(e)}"
        )


@router.get(
    "/history",
    response_model=List[ProfileHistoryResponse],
    summary="Get Profile History",
    description="List all profile histories/versions for the current user."
)
async def get_profile_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_required)
) -> List[ProfileHistoryResponse]:
    query = select(ProfileHistory).where(ProfileHistory.user_id == current_user.id).order_by(ProfileHistory.created_at.desc())
    result = await db.execute(query)
    histories = result.scalars().all()
    return histories


@router.get(
    "/{profile_id}",
    summary="Get Profile Data", 
    description="Retrieve the complete extracted profile data by profile ID."
)
async def get_profile(
    profile_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get profile data by ID.
    
    Returns the complete profile data including journey, timeline,
    and documentary narrative if generation is complete.
    
    Args:
        profile_id: Profile identifier (job_id)
        db: Database session for recovery
        
    Returns:
        Complete profile data
    """
    try:
        job_data = await profile_service.get_job_status(profile_id, db=db)
        
        if job_data["status"] != ProfileStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not ready or not found"
            )
        
        return {
            "profile": job_data.get("data", {}),
            "journey": job_data.get("journey", {}),
            "timeline": job_data.get("timeline", {}),
            "documentary": job_data.get("documentary", {}),
            "intro_video": job_data.get("intro_video"),
            "full_video": job_data.get("full_video"),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get profile {profile_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get profile: {str(e)}"
        )


@router.get(
    "/journey/{guest_id}",
    summary="Get Journey Data by Guest ID",
    description="Retrieve the journey data for a guest user. Prioritizes specific history ID, then default profile, then most recent."
)
async def get_journey_by_guest_id(
    guest_id: str,
    history_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get journey data by guest ID.
    
    This endpoint loads the profile history for the given guest_id.
    Logic: requested history_id -> default history -> most recent history.
    
    Args:
        guest_id: The guest user identifier
        history_id: Optional specific history version to load
        db: Database session
        
    Returns:
        Complete journey data with profile, timeline, and documentary
    """
    try:
        from app.models.user import User, ProfileHistory
        from sqlalchemy import select
        
        logger.info(f"Looking for journey data for guest_id: {guest_id}, history_id: {history_id}")
        
        # Find user by guest_id
        user_query = select(User).where(User.guest_id == guest_id)
        result = await db.execute(user_query)
        user = result.scalar_one_or_none()
        
        if not user:
            logger.warning(f"No user found with guest_id: {guest_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No user found with guest_id: {guest_id}"
            )
        
        logger.info(f"Found user {user.id} for guest_id: {guest_id}")
        
        latest_history = None
        
        # 1. Try to fetch specific history if requested
        if history_id:
             h_query = select(ProfileHistory).where(
                 ProfileHistory.id == history_id,
                 ProfileHistory.user_id == user.id
             )
             res = await db.execute(h_query)
             latest_history = res.scalar_one_or_none()
        
        # 2. If not found or not requested, try default
        if not latest_history:
            d_query = select(ProfileHistory).where(
                ProfileHistory.user_id == user.id,
                ProfileHistory.is_default == True
            )
            res = await db.execute(d_query)
            latest_history = res.scalar_one_or_none()
            
        # 3. Fallback to most recent
        if not latest_history:
            history_query = select(ProfileHistory).where(
                ProfileHistory.user_id == user.id
            ).order_by(ProfileHistory.created_at.desc())
            result = await db.execute(history_query)
            latest_history = result.scalars().first()
        
        if not latest_history:
            logger.warning(f"No profile history found for user {user.id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No profile history found for guest_id: {guest_id}"
            )
        
        logger.info(f"Found profile history {latest_history.id} (Default: {latest_history.is_default}), structured_data exists: {latest_history.structured_data is not None}, raw_data exists: {latest_history.raw_data is not None}")
        
        
        # Get structured data, provide fallback if empty
        structured_data = latest_history.structured_data or {}
        raw_data = latest_history.raw_data or {}
        
        # Determine profile data part (excluding journey components)
        profile_content = {
            k: v for k, v in structured_data.items() 
            if k not in ["journey", "timeline", "documentary", "generated_at"]
        } if structured_data else raw_data
        
        # If still no meaningful data, return error
        if not profile_content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No profile data available for guest_id: {guest_id}. Profile generation may still be in progress."
            )
        
        # Return the comprehensive journey data
        return {
            "guest_id": guest_id,
            "profile": profile_content,
            "passport": structured_data.get("passport"),
            "journey": structured_data.get("journey", {}),
            "timeline": structured_data.get("timeline", {}),
            "documentary": structured_data.get("documentary", {}),
            "intro_video": latest_history.intro_video,
            "full_video": latest_history.full_video,
            "source_url": latest_history.source_url,
            "created_at": latest_history.created_at.isoformat(),
            "generated_at": structured_data.get("generated_at"),
            "history_id": latest_history.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get journey for guest_id {guest_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get journey data: {str(e)}"
        )


@router.put(
    "/timeline/{history_id}",
    summary="Update Timeline Events",
    description="Update timeline events data for a specific profile history."
)
async def update_timeline_events(
    history_id: str,
    timeline_events: List[Dict[str, Any]],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_required)
) -> Dict[str, Any]:
    """Update timeline events for a specific profile history.
    
    This endpoint allows updating the timeline.events section of the structured_data,
    enabling inline editing of the Chronicles section.
    
    Args:
        history_id: The profile history identifier
        timeline_events: Updated list of timeline events
        db: Database session
        current_user: The authenticated user
        
    Returns:
        Updated timeline data
    """
    try:
        from app.models.user import ProfileHistory
        from sqlalchemy import select
        
        logger.info(f"Updating timeline events for history_id: {history_id}")
        
        # Find the profile history record
        query = select(ProfileHistory).where(ProfileHistory.id == history_id)
        result = await db.execute(query)
        history = result.scalar_one_or_none()
        
        if not history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Profile history not found: {history_id}"
            )

        # Check ownership
        if history.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this journey"
            )
        
        # Get existing structured data or create new
        structured_data = history.structured_data or {}
        
        # Update timeline events while preserving other timeline data
        if 'timeline' not in structured_data:
            structured_data['timeline'] = {}
        
        structured_data['timeline']['events'] = timeline_events
        structured_data['updated_at'] = datetime.utcnow().isoformat()
        
        # Save updated data - ensure proper JSON serialization
        from sqlalchemy.orm.attributes import flag_modified
        history.structured_data = structured_data
        flag_modified(history, 'structured_data')  # Mark JSON field as modified
        await db.commit()
        await db.refresh(history)
        
        logger.info(f"Successfully updated timeline events for history {history_id}")
        
        return {
            "success": True,
            "message": "Timeline events updated successfully",
            "timeline": structured_data.get('timeline', {}),
            "updated_at": structured_data['updated_at']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update timeline events for history {history_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update timeline events: {str(e)}"
        )


@router.post(
    "/timeline/{history_id}/events",
    summary="Add Timeline Event",
    description="Add a new event to the timeline."
)
async def add_timeline_event(
    history_id: str,
    event_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_required)
) -> Dict[str, Any]:
    """Add a new timeline event.
    
    Args:
        history_id: The profile history identifier
        event_data: New event data to add
        db: Database session
        current_user: The authenticated user
        
    Returns:
        Success response with updated timeline
    """
    try:
        from app.models.user import ProfileHistory
        from sqlalchemy import select
        import uuid
        
        logger.info(f"Adding new timeline event for history_id: {history_id}")
        
        # Find the profile history record
        query = select(ProfileHistory).where(ProfileHistory.id == history_id)
        result = await db.execute(query)
        history = result.scalar_one_or_none()
        
        if not history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Profile history not found: {history_id}"
            )

        # Check ownership
        if history.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this journey"
            )
        
        # Get existing structured data or create new
        structured_data = history.structured_data or {}
        
        # Ensure timeline and events exist
        if 'timeline' not in structured_data:
            structured_data['timeline'] = {}
        if 'events' not in structured_data['timeline']:
            structured_data['timeline']['events'] = []
        
        # Add unique ID if not provided
        if 'id' not in event_data:
            event_data['id'] = str(uuid.uuid4())
        
        # Add the new event
        structured_data['timeline']['events'].append(event_data)
        structured_data['updated_at'] = datetime.utcnow().isoformat()
        
        # Save updated data
        history.structured_data = structured_data
        await db.commit()
        
        logger.info(f"Successfully added timeline event for history {history_id}")
        
        return {
            "success": True,
            "message": "Timeline event added successfully",
            "event": event_data,
            "timeline": structured_data.get('timeline', {}),
            "updated_at": structured_data['updated_at']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add timeline event for history {history_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add timeline event: {str(e)}"
        )


@router.delete(
    "/timeline/{history_id}/events/{event_id}",
    summary="Delete Timeline Event",
    description="Delete a specific timeline event."
)
async def delete_timeline_event(
    history_id: str,
    event_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_required)
) -> Dict[str, Any]:
    """Delete a timeline event.
    
    Args:
        history_id: The profile history identifier
        event_id: The event identifier to delete
        db: Database session
        current_user: The authenticated user
        
    Returns:
        Success response with updated timeline
    """
    try:
        from app.models.user import ProfileHistory
        from sqlalchemy import select
        
        logger.info(f"Deleting timeline event {event_id} for history_id: {history_id}")
        
        # Find the profile history record
        query = select(ProfileHistory).where(ProfileHistory.id == history_id)
        result = await db.execute(query)
        history = result.scalar_one_or_none()
        
        if not history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Profile history not found: {history_id}"
            )
            
        # Check ownership
        if history.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this journey"
            )
        
        # Get existing structured data
        structured_data = history.structured_data or {}
        
        if 'timeline' not in structured_data or 'events' not in structured_data['timeline']:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Timeline events not found"
            )
        
        # Find and remove the event
        events = structured_data['timeline']['events']
        original_count = len(events)
        structured_data['timeline']['events'] = [e for e in events if e.get('id') != event_id]
        
        if len(structured_data['timeline']['events']) == original_count:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Timeline event not found: {event_id}"
            )
        
        structured_data['updated_at'] = datetime.utcnow().isoformat()
        
        # Save updated data
        history.structured_data = structured_data
        await db.commit()
        
        logger.info(f"Successfully deleted timeline event {event_id} for history {history_id}")
        
        return {
            "success": True,
            "message": "Timeline event deleted successfully",
            "timeline": structured_data.get('timeline', {}),
            "updated_at": structured_data['updated_at']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete timeline event {event_id} for history {history_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete timeline event: {str(e)}"
        )


# =====================================================================
# Professional Experience CRUD Endpoints
# =====================================================================

@router.put(
    "/experiences/{history_id}",
    summary="Update Professional Experiences",
    description="Update professional experiences data for a specific profile history."
)
async def update_experiences(
    history_id: str,
    experiences: List[Dict[str, Any]],
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Update professional experiences for a specific profile history.
    
    This endpoint allows updating the experiences section of the structured_data,
    enabling inline editing of the Professional Experience section.
    
    Args:
        history_id: The profile history identifier
        experiences: Updated list of professional experiences
        db: Database session
        
    Returns:
        Updated experiences data
    """
    try:
        from app.models.user import ProfileHistory
        from sqlalchemy import select
        
        logger.info(f"Updating experiences for history_id: {history_id}")
        
        # Find the profile history record
        query = select(ProfileHistory).where(ProfileHistory.id == history_id)
        result = await db.execute(query)
        history = result.scalar_one_or_none()
        
        if not history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Profile history not found: {history_id}"
            )
        
        # Get existing structured data or create new
        structured_data = history.structured_data or {}
        
        # Update experiences
        structured_data['experiences'] = experiences
        structured_data['updated_at'] = datetime.utcnow().isoformat()
        
        # Save updated data - ensure proper JSON serialization
        from sqlalchemy.orm.attributes import flag_modified
        history.structured_data = structured_data
        flag_modified(history, 'structured_data')  # Mark JSON field as modified
        await db.commit()
        await db.refresh(history)
        
        logger.info(f"Successfully updated experiences for history {history_id}")
        
        return {
            "success": True,
            "message": "Professional experiences updated successfully",
            "experiences": structured_data.get('experiences', []),
            "updated_at": structured_data['updated_at']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update experiences for history {history_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update experiences: {str(e)}"
        )


@router.post(
    "/experiences/{history_id}/items",
    summary="Add Professional Experience",
    description="Add a new professional experience to the profile."
)
async def add_experience(
    history_id: str,
    experience_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_required)
) -> Dict[str, Any]:
    """Add a new professional experience.
    
    Args:
        history_id: The profile history identifier
        experience_data: New experience data to add
        db: Database session
        current_user: The authenticated user
        
    Returns:
        Success response with updated experiences
    """
    try:
        from app.models.user import ProfileHistory
        from sqlalchemy import select
        import uuid
        
        logger.info(f"Adding new experience for history_id: {history_id}")
        
        # Find the profile history record
        query = select(ProfileHistory).where(ProfileHistory.id == history_id)
        result = await db.execute(query)
        history = result.scalar_one_or_none()
        
        if not history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Profile history not found: {history_id}"
            )
            
        # Check ownership
        if history.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this journey"
            )
        
        # Get existing structured data or create new
        structured_data = history.structured_data or {}
        
        # Ensure experiences list exists
        if 'experiences' not in structured_data:
            structured_data['experiences'] = []
        
        # Add unique ID if not provided
        if 'id' not in experience_data:
            experience_data['id'] = str(uuid.uuid4())
        
        # Add the new experience
        structured_data['experiences'].append(experience_data)
        structured_data['updated_at'] = datetime.utcnow().isoformat()
        
        # Save updated data
        history.structured_data = structured_data
        await db.commit()
        
        logger.info(f"Successfully added experience for history {history_id}")
        
        return {
            "success": True,
            "message": "Professional experience added successfully",
            "experience": experience_data,
            "experiences": structured_data.get('experiences', []),
            "updated_at": structured_data['updated_at']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add experience for history {history_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add experience: {str(e)}"
        )


@router.delete(
    "/experiences/{history_id}/items/{experience_id}",
    summary="Delete Professional Experience",
    description="Delete a specific professional experience."
)
async def delete_experience(
    history_id: str,
    experience_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_required)
) -> Dict[str, Any]:
    """Delete a professional experience.
    
    Args:
        history_id: The profile history identifier
        experience_id: The experience identifier to delete
        db: Database session
        current_user: The authenticated user
        
    Returns:
        Success response with updated experiences
    """
    try:
        from app.models.user import ProfileHistory
        from sqlalchemy import select
        
        logger.info(f"Deleting experience {experience_id} for history_id: {history_id}")
        
        # Find the profile history record
        query = select(ProfileHistory).where(ProfileHistory.id == history_id)
        result = await db.execute(query)
        history = result.scalar_one_or_none()
        
        if not history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Profile history not found: {history_id}"
            )
            
        # Check ownership
        if history.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this journey"
            )
        
        # Get existing structured data
        structured_data = history.structured_data or {}
        
        if 'experiences' not in structured_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Professional experiences not found"
            )
        
        # Find and remove the experience
        experiences = structured_data['experiences']
        original_count = len(experiences)
        structured_data['experiences'] = [e for e in experiences if e.get('id') != experience_id]
        
        if len(structured_data['experiences']) == original_count:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Professional experience not found: {experience_id}"
            )
        
        structured_data['updated_at'] = datetime.utcnow().isoformat()
        
        # Save updated data
        history.structured_data = structured_data
        await db.commit()
        
        logger.info(f"Successfully deleted experience {experience_id} for history {history_id}")
        
        return {
            "success": True,
            "message": "Professional experience deleted successfully",
            "experiences": structured_data.get('experiences', []),
            "updated_at": structured_data['updated_at']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete experience {experience_id} for history {history_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete experience: {str(e)}"
        )


# =====================================================================
# Projects CRUD Endpoints
# =====================================================================

@router.put(
    "/projects/{history_id}",
    summary="Update Projects",
    description="Update projects data for a specific profile history."
)
async def update_projects(
    history_id: str,
    projects: List[Dict[str, Any]],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_required)
) -> Dict[str, Any]:
    """Update projects for a specific profile history.
    
    This endpoint allows updating the projects section of the structured_data,
    enabling inline editing of the Projects section.
    
    Args:
        history_id: The profile history identifier
        projects: Updated list of projects
        db: Database session
        current_user: The authenticated user
        
    Returns:
        Updated projects data
    """
    try:
        from app.models.user import ProfileHistory
        from sqlalchemy import select
        
        logger.info(f"Updating projects for history_id: {history_id}")
        
        # Find the profile history record
        query = select(ProfileHistory).where(ProfileHistory.id == history_id)
        result = await db.execute(query)
        history = result.scalar_one_or_none()
        
        if not history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Profile history not found: {history_id}"
            )
            
        # Check ownership
        if history.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this journey"
            )
        
        # Get existing structured data or create new
        structured_data = history.structured_data or {}
        
        # Update projects
        structured_data['projects'] = projects
        structured_data['updated_at'] = datetime.utcnow().isoformat()
        
        # Save updated data - ensure proper JSON serialization
        from sqlalchemy.orm.attributes import flag_modified
        history.structured_data = structured_data
        flag_modified(history, 'structured_data')  # Mark JSON field as modified
        await db.commit()
        await db.refresh(history)
        
        logger.info(f"Successfully updated projects for history {history_id}")
        
        return {
            "success": True,
            "message": "Projects updated successfully",
            "projects": structured_data.get('projects', []),
            "updated_at": structured_data['updated_at']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update projects for history {history_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update projects: {str(e)}"
        )


@router.post(
    "/projects/{history_id}/items",
    summary="Add Project",
    description="Add a new project to the profile."
)
async def add_project(
    history_id: str,
    project_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_required)
) -> Dict[str, Any]:
    """Add a new project.
    
    Args:
        history_id: The profile history identifier
        project_data: New project data to add
        db: Database session
        current_user: The authenticated user
        
    Returns:
        Success response with updated projects
    """
    try:
        from app.models.user import ProfileHistory
        from sqlalchemy import select
        import uuid
        
        logger.info(f"Adding new project for history_id: {history_id}")
        
        # Find the profile history record
        query = select(ProfileHistory).where(ProfileHistory.id == history_id)
        result = await db.execute(query)
        history = result.scalar_one_or_none()
        
        if not history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Profile history not found: {history_id}"
            )
            
        # Check ownership
        if history.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this journey"
            )
        
        # Get existing structured data or create new
        structured_data = history.structured_data or {}
        
        # Ensure projects list exists
        if 'projects' not in structured_data:
            structured_data['projects'] = []
        
        # Add unique ID if not provided
        if 'id' not in project_data:
            project_data['id'] = str(uuid.uuid4())
        
        # Add the new project
        structured_data['projects'].append(project_data)
        structured_data['updated_at'] = datetime.utcnow().isoformat()
        
        # Save updated data
        history.structured_data = structured_data
        await db.commit()
        
        logger.info(f"Successfully added project for history {history_id}")
        
        return {
            "success": True,
            "message": "Project added successfully",
            "project": project_data,
            "projects": structured_data.get('projects', []),
            "updated_at": structured_data['updated_at']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add project for history {history_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add project: {str(e)}"
        )


@router.delete(
    "/projects/{history_id}/items/{project_id}",
    summary="Delete Project",
    description="Delete a specific project."
)
async def delete_project(
    history_id: str,
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_required)
) -> Dict[str, Any]:
    """Delete a project.
    
    Args:
        history_id: The profile history identifier
        project_id: The project identifier to delete
        db: Database session
        current_user: The authenticated user
        
    Returns:
        Success response with updated projects
    """
    try:
        from app.models.user import ProfileHistory
        from sqlalchemy import select
        
        logger.info(f"Deleting project {project_id} for history_id: {history_id}")
        
        # Find the profile history record
        query = select(ProfileHistory).where(ProfileHistory.id == history_id)
        result = await db.execute(query)
        history = result.scalar_one_or_none()
        
        if not history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Profile history not found: {history_id}"
            )
            
        # Check ownership
        if history.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this journey"
            )
        
        # Get existing structured data
        structured_data = history.structured_data or {}
        
        if 'projects' not in structured_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Projects not found"
            )
        
        # Find and remove the project
        projects = structured_data['projects']
        original_count = len(projects)
        structured_data['projects'] = [p for p in projects if p.get('id') != project_id]
        
        if len(structured_data['projects']) == original_count:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project not found: {project_id}"
            )
        
        structured_data['updated_at'] = datetime.utcnow().isoformat()
        
        # Save updated data
        history.structured_data = structured_data
        await db.commit()
        
        logger.info(f"Successfully deleted project {project_id} for history {history_id}")
        
        return {
            "success": True,
            "message": "Project deleted successfully",
            "projects": structured_data.get('projects', []),
            "updated_at": structured_data['updated_at']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete project {project_id} for history {history_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {str(e)}"
        )


# =====================================================================
# Education CRUD Endpoints
# =====================================================================

@router.put(
    "/education/{history_id}",
    summary="Update Education",
    description="Update education data for a specific profile history."
)
async def update_education(
    history_id: str,
    education: List[Dict[str, Any]],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_required)
) -> Dict[str, Any]:
    """Update education for a specific profile history.
    
    Args:
        history_id: The profile history identifier
        education: Updated list of education items
        db: Database session
        current_user: The authenticated user
        
    Returns:
        Updated education data
    """
    try:
        from app.models.user import ProfileHistory
        from sqlalchemy import select
        from sqlalchemy.orm.attributes import flag_modified
        
        logger.info(f"Updating education for history_id: {history_id}")
        
        query = select(ProfileHistory).where(ProfileHistory.id == history_id)
        result = await db.execute(query)
        history = result.scalar_one_or_none()
        
        if not history:
            raise HTTPException(status_code=404, detail=f"History not found: {history_id}")
            
        if history.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        structured_data = history.structured_data or {}
        structured_data['education'] = education
        structured_data['updated_at'] = datetime.utcnow().isoformat()
        
        history.structured_data = structured_data
        flag_modified(history, 'structured_data')
        await db.commit()
        
        return {
            "success": True,
            "education": structured_data.get('education', []),
            "updated_at": structured_data['updated_at']
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update education: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/education/{history_id}/items",
    summary="Add Education Item",
    description="Add a new education item to the profile."
)
async def add_education(
    history_id: str,
    education_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_required)
) -> Dict[str, Any]:
    try:
        from app.models.user import ProfileHistory
        from sqlalchemy import select
        from sqlalchemy.orm.attributes import flag_modified
        import uuid
        
        query = select(ProfileHistory).where(ProfileHistory.id == history_id)
        result = await db.execute(query)
        history = result.scalar_one_or_none()
        
        if not history:
            raise HTTPException(status_code=404, detail="History not found")
        if history.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
            
        structured_data = history.structured_data or {}
        if 'education' not in structured_data:
            structured_data['education'] = []
            
        if 'id' not in education_data:
            education_data['id'] = str(uuid.uuid4())
            
        structured_data['education'].append(education_data)
        structured_data['updated_at'] = datetime.utcnow().isoformat()
        
        history.structured_data = structured_data
        flag_modified(history, 'structured_data')
        await db.commit()
        
        return {
            "success": True,
            "education": structured_data.get('education', []),
            "item": education_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete(
    "/education/{history_id}/items/{item_id}",
    summary="Delete Education Item",
    description="Delete a specific education item."
)
async def delete_education(
    history_id: str,
    item_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_required)
) -> Dict[str, Any]:
    try:
        from app.models.user import ProfileHistory
        from sqlalchemy import select
        from sqlalchemy.orm.attributes import flag_modified
        
        query = select(ProfileHistory).where(ProfileHistory.id == history_id)
        result = await db.execute(query)
        history = result.scalar_one_or_none()
        
        if not history:
            raise HTTPException(status_code=404, detail="History not found")
        if history.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
            
        structured_data = history.structured_data or {}
        if 'education' not in structured_data:
            raise HTTPException(status_code=404, detail="Education section not found")
            
        items = structured_data['education']
        structured_data['education'] = [i for i in items if i.get('id') != item_id]
        
        history.structured_data = structured_data
        flag_modified(history, 'structured_data')
        await db.commit()
        
        return {
            "success": True,
            "education": structured_data.get('education', [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================================
# Certifications CRUD Endpoints
# =====================================================================

@router.put(
    "/certifications/{history_id}",
    summary="Update Certifications",
    description="Update certifications data for a specific profile history."
)
async def update_certifications(
    history_id: str,
    certifications: List[Dict[str, Any]],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_required)
) -> Dict[str, Any]:
    try:
        from app.models.user import ProfileHistory
        from sqlalchemy import select
        from sqlalchemy.orm.attributes import flag_modified
        
        logger.info(f"Updating certifications for history_id: {history_id}")
        
        query = select(ProfileHistory).where(ProfileHistory.id == history_id)
        result = await db.execute(query)
        history = result.scalar_one_or_none()
        
        if not history:
            raise HTTPException(status_code=404, detail=f"History not found: {history_id}")
            
        if history.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        
        structured_data = history.structured_data or {}
        structured_data['certifications'] = certifications
        structured_data['updated_at'] = datetime.utcnow().isoformat()
        
        history.structured_data = structured_data
        flag_modified(history, 'structured_data')
        await db.commit()
        
        return {
            "success": True,
            "certifications": structured_data.get('certifications', []),
            "updated_at": structured_data['updated_at']
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update certifications: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/certifications/{history_id}/items",
    summary="Add Certification Item",
    description="Add a new certification item to the profile."
)
async def add_certification(
    history_id: str,
    certification_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_required)
) -> Dict[str, Any]:
    try:
        from app.models.user import ProfileHistory
        from sqlalchemy import select
        from sqlalchemy.orm.attributes import flag_modified
        import uuid
        
        query = select(ProfileHistory).where(ProfileHistory.id == history_id)
        result = await db.execute(query)
        history = result.scalar_one_or_none()
        
        if not history:
            raise HTTPException(status_code=404, detail="History not found")
        if history.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
            
        structured_data = history.structured_data or {}
        if 'certifications' not in structured_data:
            structured_data['certifications'] = []
            
        if 'id' not in certification_data:
            certification_data['id'] = str(uuid.uuid4())
            
        structured_data['certifications'].append(certification_data)
        structured_data['updated_at'] = datetime.utcnow().isoformat()
        
        history.structured_data = structured_data
        flag_modified(history, 'structured_data')
        await db.commit()
        
        return {
            "success": True,
            "certifications": structured_data.get('certifications', []),
            "item": certification_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete(
    "/certifications/{history_id}/items/{item_id}",
    summary="Delete Certification Item",
    description="Delete a specific certification item."
)
async def delete_certification(
    history_id: str,
    item_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_required)
) -> Dict[str, Any]:
    try:
        from app.models.user import ProfileHistory
        from sqlalchemy import select
        from sqlalchemy.orm.attributes import flag_modified
        
        query = select(ProfileHistory).where(ProfileHistory.id == history_id)
        result = await db.execute(query)
        history = result.scalar_one_or_none()
        
        if not history:
            raise HTTPException(status_code=404, detail="History not found")
        if history.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
            
        structured_data = history.structured_data or {}
        if 'certifications' not in structured_data:
            raise HTTPException(status_code=404, detail="Certifications section not found")
            
        items = structured_data['certifications']
        structured_data['certifications'] = [i for i in items if i.get('id') != item_id]
        
        history.structured_data = structured_data
        flag_modified(history, 'structured_data')
        await db.commit()
        
        return {
            "success": True,
            "certifications": structured_data.get('certifications', [])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================================
# Documentary CRUD Endpoints
# =====================================================================

@router.put(
    "/documentary/{history_id}",
    summary="Update Documentary",
    description="Update documentary data for a specific profile history."
)
async def update_documentary(
    history_id: str,
    documentary: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_required)
) -> Dict[str, Any]:
    """Update documentary for a specific profile history.
    
    This endpoint allows updating the documentary section of the structured_data,
    enabling inline editing of the Documentary section.
    
    Args:
        history_id: The profile history identifier
        documentary: Updated documentary data
        db: Database session
        current_user: The authenticated user
        
    Returns:
        Updated documentary data
        
    Raises:
        HTTPException: If history not found or update fails
    """
    try:
        logger.info(f"Updating documentary for history_id: {history_id}")
        logger.debug(f"Documentary data received: {documentary}")
        
        # Get the profile history record
        from app.models.user import ProfileHistory
        from sqlalchemy import select
        
        result = await db.execute(
            select(ProfileHistory).where(ProfileHistory.id == history_id)
        )
        history = result.scalar_one_or_none()
        
        if not history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Profile history not found: {history_id}"
            )

        # Check ownership
        if history.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this journey"
            )
        
        # Update the documentary data
        structured_data = history.structured_data or {}
        structured_data['documentary'] = documentary
        structured_data['updated_at'] = datetime.utcnow().isoformat()
        
        # Save to database
        from sqlalchemy.orm.attributes import flag_modified
        history.structured_data = structured_data
        flag_modified(history, 'structured_data')
        await db.commit()
        await db.refresh(history)
        
        logger.info(f"Successfully updated documentary for history {history_id}")
        
        return {
            "success": True,
            "message": "Documentary updated successfully",
            "documentary": structured_data.get('documentary', {}),
            "updated_at": structured_data['updated_at']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update documentary for history {history_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update documentary: {str(e)}"
        )

@router.put(
    "/history/{history_id}",
    response_model=ProfileHistoryResponse,
    summary="Update Profile History",
    description="Update title or set as default."
)
async def update_profile_history(
    history_id: str,
    update_data: ProfileHistoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_required)
) -> ProfileHistoryResponse:
    # Check if history exists and belongs to user
    query = select(ProfileHistory).where(
        ProfileHistory.id == history_id,
        ProfileHistory.user_id == current_user.id
    )
    result = await db.execute(query)
    history = result.scalar_one_or_none()
    
    if not history:
        raise HTTPException(status_code=404, detail="Profile history not found")
    
    if update_data.title is not None:
        history.title = update_data.title
    
    if update_data.is_default:
        # Unset other defaults
        await db.execute(
            update(ProfileHistory)
            .where(ProfileHistory.user_id == current_user.id)
            .where(ProfileHistory.id != history_id)
            .values(is_default=False)
        )
        history.is_default = True
    
    await db.commit()
    await db.refresh(history)
    return history

@router.delete(
    "/history/{history_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Profile History",
    description="Delete a profile history."
)
async def delete_profile_history(
    history_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_required)
):
    # Check if history exists and belongs to user
    query = select(ProfileHistory).where(
        ProfileHistory.id == history_id,
        ProfileHistory.user_id == current_user.id
    )
    result = await db.execute(query)
    history = result.scalar_one_or_none()
    
    if not history:
        raise HTTPException(status_code=404, detail="Profile history not found")
    
    # Optional logic: if default is deleted, should we warn? Frontend handles warning.
    
    await db.delete(history)
    await db.commit()
    return None

@router.get(
    "/history/{history_id}",
    summary="Get Specific Profile History",
    description="Get full details (including structured data) of a profile history."
)
async def get_profile_history_details(
    history_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_required)
):
    query = select(ProfileHistory).where(
        ProfileHistory.id == history_id,
        ProfileHistory.user_id == current_user.id
    )
    result = await db.execute(query)
    history = result.scalar_one_or_none()
    
    if not history:
        raise HTTPException(status_code=404, detail="Profile history not found")
    
    return history

