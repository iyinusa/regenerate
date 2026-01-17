"""Centralized Gemini AI Prompts Module.

This module contains all prompts used for Gemini AI interactions,
following separation of concerns for clean architecture.

Uses Pydantic models for structured output schemas (production-grade approach).
"""

from app.prompts.profile_prompts import (
    get_profile_extraction_prompt,
    get_profile_enrichment_prompt,
    PROFILE_EXTRACTION_SCHEMA,  # Kept for backwards compatibility
)

from app.prompts.journey_prompts import (
    get_journey_structuring_prompt,
    get_timeline_generation_prompt,
    get_documentary_narrative_prompt,
    JOURNEY_STRUCTURE_SCHEMA,  # Kept for backwards compatibility
    TIMELINE_SCHEMA,  # Kept for backwards compatibility
    DOCUMENTARY_SCHEMA,  # Kept for backwards compatibility
)

from app.prompts.task_prompts import (
    get_task_planning_prompt,
    TASK_PLAN_SCHEMA,
)

# Import Pydantic-based schemas for Gemini structured output (recommended approach)
from app.schemas.gemini_schemas import (
    # Pydantic Models
    ProfileExtractionResult,
    JourneyStructureResult,
    TimelineResult,
    DocumentaryResult,
    ProfileAggregationResult,
    # Schema generator functions
    get_profile_extraction_schema,
    get_journey_structure_schema,
    get_timeline_schema,
    get_documentary_schema,
    get_profile_aggregation_schema,
)

__all__ = [
    # Profile Prompts
    "get_profile_extraction_prompt",
    "get_profile_enrichment_prompt",
    "PROFILE_EXTRACTION_SCHEMA",
    # Journey Prompts
    "get_journey_structuring_prompt",
    "get_timeline_generation_prompt",
    "get_documentary_narrative_prompt",
    "JOURNEY_STRUCTURE_SCHEMA",
    "TIMELINE_SCHEMA",
    "DOCUMENTARY_SCHEMA",
    # Task Prompts
    "get_task_planning_prompt",
    "TASK_PLAN_SCHEMA",
    # Pydantic Models (Production-grade)
    "ProfileExtractionResult",
    "JourneyStructureResult",
    "TimelineResult",
    "DocumentaryResult",
    "ProfileAggregationResult",
    # Pydantic Schema Generators
    "get_profile_extraction_schema",
    "get_journey_structure_schema",
    "get_timeline_schema",
    "get_documentary_schema",
    "get_profile_aggregation_schema",
]
