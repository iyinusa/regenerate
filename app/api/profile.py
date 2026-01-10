"""Profile API routes."""

import logging
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from app.schemas.profile import (
    ProfileGenerateRequest,
    ProfileGenerateResponse, 
    ProfileStatusResponse,
    ProfileStatus
)
from app.services.profile_service import profile_service

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/profile", tags=["profile"])


@router.post(
    "/generate",
    response_model=ProfileGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start Profile Generation",
    description="Initiate the profile data extraction and analysis process from a given URL."
)
async def generate_profile(request: ProfileGenerateRequest) -> ProfileGenerateResponse:
    """Generate profile from URL.
    
    This endpoint starts the profile extraction process:
    1. Validates the input URL
    2. Initiates web scraping
    3. Uses AI (Gemini) to analyze and structure the data
    4. Returns a job ID for tracking progress
    
    Args:
        request: Profile generation request with URL and options
        
    Returns:
        Response with job ID and initial status
    """
    try:
        logger.info(f"Starting profile generation for URL: {request.url}")
        
        # Start the extraction process
        job_id = await profile_service.start_profile_extraction(
            url=request.url,
            include_github=request.include_github
        )
        
        return ProfileGenerateResponse(
            job_id=job_id,
            status=ProfileStatus.PROCESSING,
            message="Profile extraction started successfully"
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
    description="Check the status and progress of a profile generation job."
)
async def get_profile_status(job_id: str) -> ProfileStatusResponse:
    """Get profile generation status.
    
    Args:
        job_id: The job identifier returned from the generate endpoint
        
    Returns:
        Current job status with progress and extracted data (if completed)
    """
    try:
        job_data = await profile_service.get_job_status(job_id)
        
        return ProfileStatusResponse(
            job_id=job_id,
            status=job_data["status"],
            progress=job_data["progress"],
            message=job_data["message"],
            data=job_data.get("data"),
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
    "/{profile_id}",
    summary="Get Profile Data", 
    description="Retrieve the complete extracted profile data by profile ID."
)
async def get_profile(profile_id: str) -> Dict[str, Any]:
    """Get profile data by ID.
    
    Note: This is a placeholder endpoint for future implementation
    when we add persistent storage.
    
    Args:
        profile_id: Profile identifier
        
    Returns:
        Profile data
    """
    # For now, treat profile_id as job_id
    try:
        job_data = await profile_service.get_job_status(profile_id)
        
        if job_data["status"] != ProfileStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not ready or not found"
            )
        
        return job_data.get("data", {})
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get profile {profile_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get profile: {str(e)}"
        )