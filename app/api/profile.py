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
async def get_profile_status(job_id: str) -> ProfileStatusResponse:
    """Get profile generation status with task details.
    
    Returns the current status of all tasks in the execution pipeline,
    including individual task progress and any extracted data.
    
    For real-time updates, connect to WebSocket at /api/v1/ws/tasks/{job_id}
    
    Args:
        job_id: The job identifier returned from the generate endpoint
        
    Returns:
        Current job status with task details and extracted data
    """
    try:
        job_data = await profile_service.get_job_status(job_id)
        
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
async def get_profile(profile_id: str) -> Dict[str, Any]:
    """Get profile data by ID.
    
    Returns the complete profile data including journey, timeline,
    and documentary narrative if generation is complete.
    
    Args:
        profile_id: Profile identifier (job_id)
        
    Returns:
        Complete profile data
    """
    try:
        job_data = await profile_service.get_job_status(profile_id)
        
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