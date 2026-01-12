"""Profile API routes."""

import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.profile import (
    ProfileGenerateRequest,
    ProfileGenerateResponse, 
    ProfileStatusResponse,
    ProfileStatus,
    TaskInfo,
)
from app.services.profile_service import profile_service
from app.services.task_orchestrator import task_orchestrator
from app.db.session import get_db

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/profile", tags=["profile"])


@router.post(
    "/generate",
    response_model=ProfileGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start Profile Generation",
    description="Initiate the profile data extraction and analysis process from a given URL with CoT task planning."
)
async def generate_profile(
    request: ProfileGenerateRequest,
    db: AsyncSession = Depends(get_db)
) -> ProfileGenerateResponse:
    """Generate profile from URL with Chain of Thought task planning.
    
    This endpoint:
    1. Creates a task plan using CoT reasoning
    2. Starts background execution of tasks
    3. Returns job ID for tracking progress via polling or WebSocket
    
    Connect to WebSocket at /api/v1/ws/tasks/{job_id} for real-time updates.
    
    Args:
        request: Profile generation request with URL and options
        db: Database session
        
    Returns:
        Response with job ID and initial status
    """
    try:
        logger.info(f"Starting profile generation for URL: {request.url}")
        
        # Start the extraction process with orchestrator
        job_id = await profile_service.start_profile_extraction(
            url=request.url,
            guest_user_id=request.guest_user_id,
            db=db,
            include_github=request.include_github,
            use_orchestrator=True  # Enable CoT task orchestration
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
    description="Retrieve the most recent journey data for a guest user."
)
async def get_journey_by_guest_id(
    guest_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get the most recent journey data by guest ID.
    
    This endpoint loads the latest profile history for the given guest_id,
    enabling consistent journey experiences and supporting future username conversion.
    
    Args:
        guest_id: The guest user identifier
        db: Database session
        
    Returns:
        Complete journey data with profile, timeline, and documentary
    """
    try:
        from app.models.user import User, ProfileHistory
        from sqlalchemy import select
        
        logger.info(f"Looking for journey data for guest_id: {guest_id}")
        
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
        
        # Get the most recent profile history
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
        
        logger.info(f"Found profile history {latest_history.id}, structured_data exists: {latest_history.structured_data is not None}, raw_data exists: {latest_history.raw_data is not None}")
        
        if not latest_history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No profile history found for guest_id: {guest_id}"
            )
        
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
            "journey": structured_data.get("journey", {}),
            "timeline": structured_data.get("timeline", {}),
            "documentary": structured_data.get("documentary", {}),
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