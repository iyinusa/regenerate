"""Centralized Gemini AI Prompts Module.

This module contains all prompts used for Gemini AI interactions,
following separation of concerns for clean architecture.
"""

from app.prompts.profile_prompts import (
    get_profile_extraction_prompt,
    get_profile_enrichment_prompt,
    PROFILE_EXTRACTION_SCHEMA,
)

from app.prompts.journey_prompts import (
    get_journey_structuring_prompt,
    get_timeline_generation_prompt,
    get_documentary_narrative_prompt,
    JOURNEY_STRUCTURE_SCHEMA,
    TIMELINE_SCHEMA,
    DOCUMENTARY_SCHEMA,
)

from app.prompts.task_prompts import (
    get_task_planning_prompt,
    TASK_PLAN_SCHEMA,
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
]
