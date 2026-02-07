"""Pydantic schemas for Gemini AI structured outputs.

This module contains all Pydantic models used for Gemini AI structured
output generation, following the Gemini API documentation best practices.
These models ensure consistent, type-safe responses from the Gemini API.
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from enum import Enum


# =============================================================================
# Profile Extraction Models
# =============================================================================

class ExperienceItem(BaseModel):
    """Work experience entry."""
    company: Optional[str] = Field(default=None, description="Company name")
    title: Optional[str] = Field(default=None, description="Job title")
    duration: Optional[str] = Field(default=None, description="e.g., Jan 2020 - Present")
    start_date: Optional[str] = Field(default=None, description="ISO date or year if available")
    end_date: Optional[str] = Field(default=None, description="ISO date or 'Present'")
    description: Optional[str] = Field(default=None, description="Role description")
    highlights: Optional[List[str]] = Field(default=None, description="Key achievements or responsibilities")


class EducationItem(BaseModel):
    """Education history entry."""
    institution: Optional[str] = Field(default=None, description="School or university name")
    degree: Optional[str] = Field(default=None, description="Degree type")
    field: Optional[str] = Field(default=None, description="Field of study")
    duration: Optional[str] = Field(default=None, description="Duration period")
    start_date: Optional[str] = Field(default=None, description="Start date")
    end_date: Optional[str] = Field(default=None, description="End date")


class ProjectItem(BaseModel):
    """Project entry."""
    name: Optional[str] = Field(default=None, description="Project name")
    description: Optional[str] = Field(default=None, description="Project description")
    date: Optional[str] = Field(default=None, description="When the project was completed or active")
    technologies: Optional[List[str]] = Field(default=None, description="Technologies used")
    url: Optional[str] = Field(default=None, description="Project URL")
    impact: Optional[str] = Field(default=None, description="Measurable impact or outcome")


class AchievementItem(BaseModel):
    """Achievement or award entry."""
    title: Optional[str] = Field(default=None, description="Achievement or award name")
    date: Optional[str] = Field(default=None, description="When it was received")
    issuer: Optional[str] = Field(default=None, description="Who gave the award or recognition")
    description: Optional[str] = Field(default=None, description="Achievement description")


class CertificationItem(BaseModel):
    """Professional certification entry."""
    name: Optional[str] = Field(default=None, description="Certification name")
    issuer: Optional[str] = Field(default=None, description="Issuing organization")
    date: Optional[str] = Field(default=None, description="Date obtained")
    credential_id: Optional[str] = Field(default=None, description="Credential ID")


class RelatedLinkType(str, Enum):
    """Types of related links."""
    ARTICLE = "article"
    BLOG = "blog"
    PORTFOLIO = "portfolio"
    PROJECT = "project"
    SOCIAL = "social"
    MENTION = "mention"
    OTHER = "other"


class RelatedLinkItem(BaseModel):
    """Related link discovered about the person."""
    url: str = Field(..., description="Full URL of the related content")
    title: Optional[str] = Field(default=None, description="Title of the page or article")
    type: RelatedLinkType = Field(..., description="Type of content")
    description: Optional[str] = Field(default=None, description="Brief description of the content")
    source: Optional[str] = Field(default=None, description="Publisher or platform name")


class ProfileExtractionResult(BaseModel):
    """Complete profile extraction result from Gemini.
    
    This is the primary model for profile extraction structured output,
    used with response_json_schema in Gemini API calls.
    """
    name: str = Field(..., description="Full name of the person")
    passport: Optional[str] = Field(default=None, description="Passport photo or profile image URL")
    title: Optional[str] = Field(default=None, description="Current job title or professional role")
    location: Optional[str] = Field(default=None, description="Geographic location")
    bio: Optional[str] = Field(default=None, description="Professional bio or summary")
    
    experiences: Optional[List[ExperienceItem]] = Field(default=None, description="Work experience history")
    education: Optional[List[EducationItem]] = Field(default=None, description="Educational background")
    skills: Optional[List[str]] = Field(default=None, description="Technical, leadership, tools, and soft skills")
    projects: Optional[List[ProjectItem]] = Field(default=None, description="Notable projects")
    achievements: Optional[List[AchievementItem]] = Field(default=None, description="Professional achievements, awards, and recognitions")
    certifications: Optional[List[CertificationItem]] = Field(default=None, description="Professional certifications")
    
    email: Optional[str] = Field(default=None, description="Contact email")
    website: Optional[str] = Field(default=None, description="Personal website URL")
    linkedin: Optional[str] = Field(default=None, description="LinkedIn profile URL")
    github: Optional[str] = Field(default=None, description="GitHub profile URL")
    social_links: Optional[Dict[str, str]] = Field(default=None, description="Other social media links")
    related_links: Optional[List[RelatedLinkItem]] = Field(default=None, description="Related links discovered about the person")


# =============================================================================
# Journey Structure Models
# =============================================================================

class JourneySummary(BaseModel):
    """Summary section of the professional journey."""
    headline: str = Field(..., description="One-liner professional headline")
    narrative: str = Field(..., description="3-4 sentence journey summary")
    career_span: str = Field(..., description="e.g., '2015 - Present (9 years)'")
    key_themes: List[str] = Field(..., description="3-5 key themes of the career")


class MilestoneCategory(str, Enum):
    """Categories for career milestones."""
    CAREER = "career"
    EDUCATION = "education"
    ACHIEVEMENT = "achievement"
    PROJECT = "project"
    CERTIFICATION = "certification"


class MilestoneSignificance(str, Enum):
    """Significance levels for milestones."""
    MAJOR = "major"
    MODERATE = "moderate"
    MINOR = "minor"


class MilestoneItem(BaseModel):
    """Career milestone entry."""
    date: str = Field(..., description="Date of the milestone")
    title: str = Field(..., description="Milestone title")
    description: str = Field(..., description="Milestone description")
    category: MilestoneCategory = Field(..., description="Category of the milestone")
    significance: Optional[MilestoneSignificance] = Field(default=None, description="Significance level")
    impact_statement: Optional[str] = Field(default=None, description="Impact statement")


class CareerChapter(BaseModel):
    """Career chapter representing a phase of professional growth."""
    title: str = Field(..., description="Chapter title e.g., 'The Foundation Years'")
    period: str = Field(..., description="Time period of this chapter")
    narrative: str = Field(..., description="Narrative description of this chapter")


class SkillsEvolutionItem(BaseModel):
    """Skills evolution entry showing skill development over time."""
    period: str = Field(..., description="Time period (e.g., '2015-2017', 'Early Career')")
    stage: str = Field(..., description="Career stage name")
    description: str = Field(..., description="What was learned/achieved")
    skills_acquired: List[str] = Field(..., description="Specific skills gained during this period")
    milestone: Optional[str] = Field(default=None, description="Key milestone achieved")
    year: Optional[str] = Field(default=None, description="Alternative to period for single year")
    skill_level: Optional[str] = Field(default=None, description="Skill level progression")
    context: Optional[str] = Field(default=None, description="Context for skill development")


class ImpactMetrics(BaseModel):
    """Quantified impact metrics for the career."""
    years_experience: Optional[int] = Field(default=None, description="Total years of experience")
    companies_count: Optional[int] = Field(default=None, description="Number of companies worked at")
    projects_count: Optional[int] = Field(default=None, description="Number of notable projects")
    skills_count: Optional[int] = Field(default=None, description="Number of skills")


class JourneyStructureResult(BaseModel):
    """Complete journey structure result from Gemini.
    
    This model represents the structured professional journey
    generated from profile data.
    """
    summary: JourneySummary = Field(..., description="Career summary section")
    milestones: List[MilestoneItem] = Field(..., description="Chronologically ordered significant events")
    career_chapters: List[CareerChapter] = Field(..., description="Distinct career phases with narratives")
    skills_evolution: List[SkillsEvolutionItem] = Field(..., description="Skills development progression")
    impact_metrics: ImpactMetrics = Field(..., description="Quantified career statistics")


# =============================================================================
# Timeline Models
# =============================================================================

class TimelineMedia(BaseModel):
    """Media attachment for timeline events."""
    type: Optional[str] = Field(default=None, description="Media type")
    url: Optional[str] = Field(default=None, description="Media URL")
    caption: Optional[str] = Field(default=None, description="Media caption")


class TimelineEvent(BaseModel):
    """Single timeline event."""
    id: str = Field(..., description="Unique event identifier")
    date: str = Field(..., description="ISO date or year")
    title: str = Field(..., description="Event title")
    end_date: Optional[str] = Field(default=None, description="End date for ranges")
    subtitle: Optional[str] = Field(default=None, description="Event subtitle")
    description: Optional[str] = Field(default=None, description="Event description")
    category: Optional[str] = Field(default=None, description="Event category")
    icon: Optional[str] = Field(default=None, description="Icon identifier")
    color: Optional[str] = Field(default=None, description="Color code")
    media: Optional[TimelineMedia] = Field(default=None, description="Media attachment")
    tags: Optional[List[str]] = Field(default=None, description="Event tags")


class TimelineEra(BaseModel):
    """Career era for timeline visualization."""
    name: Optional[str] = Field(default=None, description="Era name")
    start_date: Optional[str] = Field(default=None, description="Era start date")
    end_date: Optional[str] = Field(default=None, description="Era end date")
    color: Optional[str] = Field(default=None, description="Era color")


class TimelineResult(BaseModel):
    """Complete timeline visualization result from Gemini."""
    events: List[TimelineEvent] = Field(default_factory=list, description="Timeline events")
    eras: Optional[List[TimelineEra]] = Field(default=None, description="Career era definitions")


# =============================================================================
# Documentary Models
# =============================================================================

class DocumentaryMood(str, Enum):
    """Mood types for documentary segments."""
    INSPIRATIONAL = "inspirational"
    PROFESSIONAL = "professional"
    DYNAMIC = "dynamic"
    REFLECTIVE = "reflective"
    TRIUMPHANT = "triumphant"


class DataVisualization(BaseModel):
    """Data visualization for documentary segments."""
    type: Optional[str] = Field(default=None, description="Visualization type")
    data_points: Optional[List[Any]] = Field(default=None, description="Data points")


class DocumentarySegment(BaseModel):
    """Documentary video segment."""
    id: str = Field(..., description="Segment identifier, e.g. segment_1")
    order: int = Field(..., description="Segment order starting from 1")
    title: str = Field(..., description="Segment title")
    duration_seconds: int = Field(default=8, description="Duration in seconds, default 8")
    visual_description: str = Field(..., description="Detailed description of what should be shown visually")
    narration: str = Field(..., description="Voiceover script, 10-15 words")
    mood: DocumentaryMood = Field(default=DocumentaryMood.PROFESSIONAL, description="Emotional tone of the segment")
    background_music_hint: Optional[str] = Field(default=None, description="Music suggestion")
    data_visualization: Optional[DataVisualization] = Field(default=None, description="Data visualization")


class DocumentaryResult(BaseModel):
    """Complete documentary narrative result from Gemini."""
    title: Optional[str] = Field(default=None, description="Documentary title")
    tagline: Optional[str] = Field(default=None, description="Catchy one-liner")
    duration_estimate: Optional[str] = Field(default=None, description="Estimated runtime")
    segments: List[DocumentarySegment] = Field(default_factory=list, description="Video segments")
    opening_hook: Optional[str] = Field(default=None, description="Compelling opening statement")
    closing_statement: Optional[str] = Field(default=None, description="Memorable conclusion")


# =============================================================================
# Profile Aggregation Models (for history merging)
# =============================================================================

class AggregationMetadata(BaseModel):
    """Metadata about the aggregation process."""
    sources_count: Optional[int] = Field(default=None, description="Number of data sources")
    scraped_articles_count: Optional[int] = Field(default=None, description="Number of scraped articles")
    date_range: Optional[str] = Field(default=None, description="Career date range")
    aggregation_timestamp: Optional[str] = Field(default=None, description="When aggregation occurred")


class ProfileAggregationResult(BaseModel):
    """Aggregated profile data from multiple sources.
    
    This model is used when merging current profile with historical
    data and scraped content.
    """
    name: str = Field(..., description="Full name")
    title: Optional[str] = Field(default=None, description="Current title")
    location: Optional[str] = Field(default=None, description="Location")
    bio: Optional[str] = Field(default=None, description="Professional bio")
    
    experiences: Optional[List[ExperienceItem]] = Field(default=None, description="All work experiences")
    education: Optional[List[EducationItem]] = Field(default=None, description="Education history")
    skills: Optional[List[str]] = Field(default=None, description="Complete skills list")
    projects: Optional[List[ProjectItem]] = Field(default=None, description="All projects")
    achievements: Optional[List[AchievementItem]] = Field(default=None, description="All achievements")
    certifications: Optional[List[CertificationItem]] = Field(default=None, description="Certifications")
    
    # Additional enrichment data
    publications: Optional[List[Dict[str, Any]]] = Field(default=None, description="Published works")
    speaking_engagements: Optional[List[Dict[str, Any]]] = Field(default=None, description="Speaking events")
    media_mentions: Optional[List[Dict[str, Any]]] = Field(default=None, description="Media mentions")
    
    # Contact info
    email: Optional[str] = Field(default=None, description="Contact email")
    website: Optional[str] = Field(default=None, description="Personal website")
    linkedin: Optional[str] = Field(default=None, description="LinkedIn URL")
    github: Optional[str] = Field(default=None, description="GitHub URL")
    social_links: Optional[Dict[str, str]] = Field(default=None, description="Social media links")
    
    # Career insights
    career_insights: Optional[List[str]] = Field(default=None, description="Career patterns identified")
    professional_recognition: Optional[List[str]] = Field(default=None, description="Community impact")
    
    # Metadata
    aggregation_metadata: Optional[AggregationMetadata] = Field(default=None, description="Aggregation details")


# =============================================================================
# Utility Functions for Schema Generation
# =============================================================================

def get_profile_extraction_schema() -> Dict[str, Any]:
    """Get JSON schema for profile extraction.
    
    Returns:
        JSON schema dictionary for Gemini API.
    """
    return ProfileExtractionResult.model_json_schema()


def get_journey_structure_schema() -> Dict[str, Any]:
    """Get JSON schema for journey structure.
    
    Returns:
        JSON schema dictionary for Gemini API.
    """
    return JourneyStructureResult.model_json_schema()


def get_timeline_schema() -> Dict[str, Any]:
    """Get JSON schema for timeline.
    
    Returns:
        JSON schema dictionary for Gemini API.
    """
    return TimelineResult.model_json_schema()


def get_documentary_schema() -> Dict[str, Any]:
    """Get JSON schema for documentary.
    
    Returns:
        JSON schema dictionary for Gemini API.
    """
    return DocumentaryResult.model_json_schema()


def get_profile_aggregation_schema() -> Dict[str, Any]:
    """Get JSON schema for profile aggregation.
    
    Returns:
        JSON schema dictionary for Gemini API.
    """
    return ProfileAggregationResult.model_json_schema()
