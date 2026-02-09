"""Pydantic schemas for reGen API.

This module exports all schemas including Gemini AI structured output schemas.
"""

from app.schemas.profile import (
    ProfileStatus,
    ProfileSourceType,
    TaskStatus,
    TaskInfo,
    ProfileGenerateRequest,
    ProfileGenerateResponse,
    ExtractedProfileData,
    ProfileStatusResponse,
    JourneyData,
    TimelineData,
    DocumentaryData,
    FullProfileResponse,
)

from app.schemas.gemini_schemas import (
    # Profile Extraction Models
    ExperienceItem,
    EducationItem,
    ProjectItem,
    AchievementItem,
    CertificationItem,
    RelatedLinkType,
    RelatedLinkItem,
    ProfileExtractionResult,
    # Journey Structure Models
    JourneySummary,
    MilestoneCategory,
    MilestoneSignificance,
    MilestoneItem,
    CareerChapter,
    SkillsEvolutionItem,
    ImpactMetrics,
    JourneyStructureResult,
    # Timeline Models
    TimelineMedia,
    TimelineEvent,
    TimelineEra,
    TimelineResult,
    # Documentary Models
    DocumentaryMood,
    DataVisualization,
    DocumentarySegment,
    DocumentaryResult,
    # Aggregation Models
    AggregationMetadata,
    ProfileAggregationResult,
    # Schema Generators
    get_profile_extraction_schema,
    get_journey_structure_schema,
    get_timeline_schema,
    get_documentary_schema,
    get_profile_aggregation_schema,
)

__all__ = [
    # Profile Schemas
    "ProfileStatus",
    "TaskStatus",
    "TaskInfo",
    "ProfileGenerateRequest",
    "ProfileGenerateResponse",
    "ExtractedProfileData",
    "ProfileStatusResponse",
    "JourneyData",
    "TimelineData",
    "DocumentaryData",
    "FullProfileResponse",
    # Gemini AI Structured Output Models
    "ExperienceItem",
    "EducationItem",
    "ProjectItem",
    "AchievementItem",
    "CertificationItem",
    "RelatedLinkType",
    "RelatedLinkItem",
    "ProfileExtractionResult",
    "JourneySummary",
    "MilestoneCategory",
    "MilestoneSignificance",
    "MilestoneItem",
    "CareerChapter",
    "SkillsEvolutionItem",
    "ImpactMetrics",
    "JourneyStructureResult",
    "TimelineMedia",
    "TimelineEvent",
    "TimelineEra",
    "TimelineResult",
    "DocumentaryMood",
    "DataVisualization",
    "DocumentarySegment",
    "DocumentaryResult",
    "AggregationMetadata",
    "ProfileAggregationResult",
    # Schema Generators
    "get_profile_extraction_schema",
    "get_journey_structure_schema",
    "get_timeline_schema",
    "get_documentary_schema",
    "get_profile_aggregation_schema",
]
