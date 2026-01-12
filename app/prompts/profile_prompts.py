"""Profile extraction and enrichment prompts for Gemini AI.

This module contains all prompts related to profile data extraction
and enrichment using Gemini 3 Pro.
"""

from typing import Dict, Any


# JSON Schema for profile extraction response
PROFILE_EXTRACTION_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Full name of the person"},
        "title": {"type": "string", "description": "Current job title or professional role"},
        "location": {"type": "string", "description": "Geographic location"},
        "bio": {"type": "string", "description": "Professional bio or summary"},
        "experiences": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "company": {"type": "string"},
                    "title": {"type": "string"},
                    "duration": {"type": "string", "description": "e.g., Jan 2020 - Present"},
                    "start_date": {"type": "string", "description": "ISO date or year if available"},
                    "end_date": {"type": "string", "description": "ISO date or 'Present'"},
                    "description": {"type": "string"},
                    "highlights": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Key achievements or responsibilities"
                    }
                }
            },
            "description": "Work experience history"
        },
        "education": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "institution": {"type": "string"},
                    "degree": {"type": "string"},
                    "field": {"type": "string"},
                    "duration": {"type": "string"},
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"}
                }
            },
            "description": "Educational background"
        },
        "skills": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Technical and soft skills"
        },
        "projects": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "date": {"type": "string", "description": "When the project was completed or active"},
                    "technologies": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "url": {"type": "string"},
                    "impact": {"type": "string", "description": "Measurable impact or outcome"}
                }
            },
            "description": "Notable projects"
        },
        "achievements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Achievement or award name"},
                    "date": {"type": "string", "description": "When it was received"},
                    "issuer": {"type": "string", "description": "Who gave the award or recognition"},
                    "description": {"type": "string"}
                }
            },
            "description": "Professional achievements, awards, and recognitions"
        },
        "certifications": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "issuer": {"type": "string"},
                    "date": {"type": "string"},
                    "credential_id": {"type": "string"}
                }
            },
            "description": "Professional certifications"
        },
        "email": {"type": "string", "description": "Contact email"},
        "website": {"type": "string", "description": "Personal website URL"},
        "linkedin": {"type": "string", "description": "LinkedIn profile URL"},
        "github": {"type": "string", "description": "GitHub profile URL"},
        "social_links": {
            "type": "object",
            "description": "Other social media links",
            "additionalProperties": {"type": "string"}
        }
    },
    "required": ["name"]
}


def get_profile_extraction_prompt(url: str) -> str:
    """Generate the profile extraction prompt for Gemini 3.
    
    Args:
        url: The profile URL to extract data from
        
    Returns:
        Formatted prompt string for Gemini 3
    """
    return f"""You are a precise data extraction assistant using Gemini 3. Your goal is to build a COMPREHENSIVE profile for the person identified by the URL.

**CORE DIRECTIVE: DEEP SEARCH & AGGREGATE**
The provided URL is just the starting point. You MUST use Google Search to find and aggregate data from other public sources (Personal Website, GitHub, Twitter/X, Articles, Interviews, Event Speaking) to build a complete profile.

**CRITICAL DATA INTEGRITY RULES (STRICT):**
1. **IDENTITY ANCHOR:** The person is defined ONLY by the URL provided: {url}
2. **PRIMARY SOURCE:** First, use the URL Context tool to read the page content.
3. **ACTIVE SEARCH:**
   - **MANDATORY:** Use `google_search` to find external sources. Search for "[Name] personal website", "[Name] github", "[Name] blog", "[Name] projects".
   - **AGGREGATION:** If you find a verified personal website or portfolio, extract details (Bio, Projects, Skills) from verified search snippets to enrich the profile.
4. **STRICT VERIFICATION (ANTI-HALLUCINATION):**
   - **USERNAME TRAP:** If URL has username 'iyinusa' and search finds 'iaboyeji', **DO NOT MERGE** unless you find a "Bridge Link" (e.g., a website linking to BOTH).
   - **NAME COLLISIONS:** Verify identity using (Company + Title + Location). If they don't match, DISCARD the extra source.
   - **ZERO TRUST:** If you are not 100% sure a result belongs to THIS person, ignore it.

**URL TO ANALYZE:** {url}

**EXTRACTION TASK (Enrich with Search Results):**
- name: Full name (from Anchor URL)
- title: Current professional title (Verify via Search if outdated)
- location: Geographic location
- bio: Comprehensive professional summary (Combine Anchor URL bio + Search results from interviews/personal site).
- experiences: Work history. (MANDATORY: Capture start/end dates for timeline reconstruction).
- education: Educational history. (Capture dates of study).
- skills: Commercial and technical skills (Aggregate from all verified sources).
- projects: Notable public projects (MANDATORY: Capture dates to place on professional timeline).
- achievements: Publicly verifiable awards and recognitions (MANDATORY: Capture dates/year for chronological storytelling).
- certifications: Professional certifications.
- email: Professional contact email (Only if publicly visible).
- website: Personal website/Portfolio (PRIORITY: Search for this).
- linkedin: The correct LinkedIn URL.
- github: GitHub URL (Verify identity match carefully).
- social_links: Twitter/X, Medium, Substack (Verify identity).

**TIMELINE FOCUS:** 
The primary goal is to "retell the story" via a visual timeline and documentary video. For EVERY experience, achievement, and project, you MUST strive to find associated dates (Month/Year or just Year). A journey cannot be told without a chronological anchor.

**VERIFICATION:**
Before adding any field, ask: "Is this definitely the same person?"

Return a JSON object. Use null for missing string fields and empty arrays [] for missing list fields."""


def get_profile_enrichment_prompt(existing_data: Dict[str, Any], additional_urls: list) -> str:
    """Generate prompt to enrich existing profile with additional sources.
    
    Args:
        existing_data: Already extracted profile data
        additional_urls: List of additional URLs to analyze
        
    Returns:
        Formatted prompt string for enrichment
    """
    urls_str = "\n".join(f"- {url}" for url in additional_urls)
    
    return f"""You are enriching an existing professional profile with additional data sources.

**EXISTING PROFILE DATA:**
Name: {existing_data.get('name', 'Unknown')}
Current Title: {existing_data.get('title', 'Unknown')}
Location: {existing_data.get('location', 'Unknown')}

**ADDITIONAL SOURCES TO ANALYZE:**
{urls_str}

**TASK:**
1. Analyze each additional URL using URL Context tool
2. Extract NEW information not already in the profile
3. Merge and deduplicate experiences, skills, projects
4. Update timeline with any new dates discovered
5. Validate all information belongs to the SAME person

**CRITICAL RULES:**
- Do NOT replace existing data unless the new source is more authoritative
- ADD to lists (experiences, skills, projects) - don't replace
- Maintain chronological ordering for experiences
- Flag any potential identity mismatches

Return a JSON object with the enriched profile data."""
