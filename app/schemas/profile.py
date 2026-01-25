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


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskInfo(BaseModel):
    """Information about a single task in the execution pipeline."""
    task_id: str
    task_type: str
    name: str
    description: str
    order: int
    status: TaskStatus = TaskStatus.PENDING
    progress: int = Field(default=0, ge=0, le=100)
    message: str = ""
    dependencies: List[str] = Field(default_factory=list)
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_seconds: int = 30
    critical: bool = True


class ProfileGenerateRequest(BaseModel):
    """Request schema for profile generation."""
    url: str = Field(..., description="Profile URL to analyze (LinkedIn, website, etc.)")
    include_github: bool = Field(default=False, description="Whether to include GitHub OAuth data")
    guest_user_id: str = Field(..., description="Unique guest user ID from frontend")
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://linkedin.com/in/iyinusa",
                "include_github": False,
                "guest_user_id": "550e8400-e29b-41d4-a716-446655440000"
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
    achievements: List[Dict[str, Any]] = Field(default_factory=list)
    certifications: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Contact and Links
    email: Optional[str] = None
    website: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None


class ProfileHistoryResponse(BaseModel):
    """Schema for profile history/version."""
    id: str
    title: Optional[str] = None
    source_url: str
    is_default: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class ProfileHistoryUpdate(BaseModel):
    """Schema for updating profile history."""
    title: Optional[str] = None
    is_default: Optional[bool] = None
    
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
                "source_url": "https://linkedin.com/in/iyinusa",
                "extraction_timestamp": "2024-01-10T12:00:00Z"
            }
        }


class ProfileStatusResponse(BaseModel):
    """Response schema for profile status check with task details."""
    job_id: str
    status: ProfileStatus
    progress: int = Field(..., ge=0, le=100, description="Progress percentage")
    message: str
    current_task: Optional[str] = Field(None, description="Name of currently running task")
    tasks: Optional[List[TaskInfo]] = Field(None, description="List of tasks in the pipeline")
    data: Optional[ExtractedProfileData] = None
    journey: Optional[Dict[str, Any]] = Field(None, description="Structured journey data")
    timeline: Optional[Dict[str, Any]] = Field(None, description="Timeline visualization data")
    documentary: Optional[Dict[str, Any]] = Field(None, description="Documentary narrative data")
    error: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "prof_1234567890abcdef",
                "status": "processing",
                "progress": 45,
                "message": "Structuring Journey",
                "current_task": "structure_journey",
                "tasks": [
                    {
                        "task_id": "task_001",
                        "name": "Extracting Profile Data",
                        "status": "completed",
                        "progress": 100
                    }
                ],
                "data": {
                    "name": "John Doe",
                    "title": "Senior Software Engineer"
                }
            }
        }


class JourneyData(BaseModel):
    """Schema for structured journey data."""
    summary: Optional[Dict[str, Any]] = None
    milestones: List[Dict[str, Any]] = Field(default_factory=list)
    career_chapters: List[Dict[str, Any]] = Field(default_factory=list)
    skills_evolution: List[Dict[str, Any]] = Field(default_factory=list)
    impact_metrics: Optional[Dict[str, Any]] = None


class TimelineData(BaseModel):
    """Schema for timeline visualization data."""
    events: List[Dict[str, Any]] = Field(default_factory=list)
    eras: List[Dict[str, Any]] = Field(default_factory=list)


class DocumentaryData(BaseModel):
    """Schema for documentary narrative data."""
    title: Optional[str] = None
    tagline: Optional[str] = None
    duration_estimate: Optional[str] = None
    segments: List[Dict[str, Any]] = Field(default_factory=list)
    opening_hook: Optional[str] = None
    closing_statement: Optional[str] = None


class FullProfileResponse(BaseModel):
    """Complete response with profile, journey, timeline, and documentary."""
    job_id: str
    status: ProfileStatus
    profile: Optional[ExtractedProfileData] = None
    journey: Optional[JourneyData] = None
    timeline: Optional[TimelineData] = None
    documentary: Optional[DocumentaryData] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    