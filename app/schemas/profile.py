"""Profile-related Pydantic schemas."""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime
from enum import Enum


class ProfileStatus(str, Enum):
    """Profile generation status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProfileGenerateRequest(BaseModel):
    """Request schema for profile generation."""
    url: str = Field(..., description="Profile URL to analyze (LinkedIn, website, etc.)")
    include_github: bool = Field(default=False, description="Whether to include GitHub OAuth data")
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://linkedin.com/in/johndoe",
                "include_github": False
            }
        }


class ProfileGenerateResponse(BaseModel):
    """Response schema for profile generation initiation."""
    job_id: str = Field(..., description="Unique job identifier for tracking")
    status: ProfileStatus = Field(..., description="Current processing status")
    message: str = Field(..., description="Status message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "prof_1234567890abcdef",
                "status": "processing",
                "message": "Profile extraction started successfully"
            }
        }


class ExtractedProfileData(BaseModel):
    """Schema for structured profile data extracted from URLs."""
    
    # Basic Information
    name: Optional[str] = None
    title: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    
    # Professional Experience
    experiences: List[Dict[str, Any]] = Field(default_factory=list)
    education: List[Dict[str, Any]] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    
    # Projects and Achievements
    projects: List[Dict[str, Any]] = Field(default_factory=list)
    achievements: List[str] = Field(default_factory=list)
    certifications: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Contact and Links
    email: Optional[str] = None
    website: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    social_links: Dict[str, str] = Field(default_factory=dict)
    
    # Metadata
    source_url: str
    extraction_timestamp: datetime
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "title": "Senior Software Engineer",
                "location": "San Francisco, CA",
                "bio": "Passionate full-stack developer with 5+ years of experience...",
                "experiences": [
                    {
                        "company": "Tech Corp",
                        "title": "Senior Software Engineer",
                        "duration": "2020 - Present",
                        "description": "Led development of microservices..."
                    }
                ],
                "skills": ["Python", "JavaScript", "React", "FastAPI"],
                "source_url": "https://linkedin.com/in/johndoe",
                "extraction_timestamp": "2024-01-10T12:00:00Z"
            }
        }


class ProfileStatusResponse(BaseModel):
    """Response schema for profile status check."""
    job_id: str
    status: ProfileStatus
    progress: int = Field(..., ge=0, le=100, description="Progress percentage")
    message: str
    data: Optional[ExtractedProfileData] = None
    error: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "prof_1234567890abcdef",
                "status": "completed",
                "progress": 100,
                "message": "Profile extraction completed successfully",
                "data": {
                    "name": "John Doe",
                    "title": "Senior Software Engineer"
                }
            }
        }