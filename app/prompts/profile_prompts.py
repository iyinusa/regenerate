"""Profile extraction and enrichment prompts for Gemini AI.

This module contains all prompts related to profile data extraction
and enrichment using Gemini 3 Pro.
"""

import json
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
        },
        "related_links": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Full URL of the related content"},
                    "title": {"type": "string", "description": "Title of the page or article"},
                    "type": {"type": "string", "enum": ["article", "blog", "portfolio", "project", "social", "mention", "other"], "description": "Type of content"},
                    "description": {"type": "string", "description": "Brief description of the content"},
                    "source": {"type": "string", "description": "Publisher or platform name"}
                },
                "required": ["url", "type"]
            },
            "description": "Related links discovered about the person (articles, mentions, portfolio pages, etc.)"
        }
    },
    "required": ["name"]
}


def get_profile_extraction_prompt(url: str, is_linkedin_oauth: bool = False, oauth_data: Dict[str, Any] = None) -> str:
    """Generate the profile extraction prompt for Gemini 3.
    
    Args:
        url: The profile URL to extract data from
        is_linkedin_oauth: Whether LinkedIn OAuth data is available
        oauth_data: LinkedIn OAuth data if available
        
    Returns:
        Formatted prompt string for Gemini 3
    """
    # Build the base prompt with LinkedIn-specific handling
    if is_linkedin_oauth and oauth_data:
        oauth_info = f"""
**LINKEDIN OAUTH DATA AVAILABLE:**
You have limited LinkedIn OAuth data:
{json.dumps(oauth_data, indent=2)}

This provides: firstname, lastname, picture, member ID, and email.
You MUST supplement this with Google Search to build a rich profile.
"""
    else:
        oauth_info = ""
    
    return f"""You are a precise data extraction assistant using Gemini 3. Your goal is to build a COMPREHENSIVE profile for the person identified by the URL.

{oauth_info}

**CORE DIRECTIVE: DEEP SEARCH & LINK DISCOVERY**
The provided URL is just the starting point. You MUST use Google Search (and URL Context for non-LinkedIn URLs) to:
1. Find and aggregate data from public sources (Personal Website, GitHub, Twitter/X, Portfolio, Blog)
2. **CRITICAL:** Discover and extract ALL relevant links about this person including:
   - Article mentions (news, interviews, features)
   - Blog posts they wrote or are featured in
   - Speaking engagements or event appearances
   - Project showcases
   - Social media profiles
   - Portfolio pages
   - Any public mentions or references

**URL TO ANALYZE:** {url}

**TWO-PHASE EXTRACTION:**

**Phase 1: Basic Profile Data & Link Discovery**
Extract the standard profile fields:
- name: Full name
- title: Current professional title
- location: Geographic location
- bio: Professional summary
- experiences: Work history (with start/end dates)
- education: Educational history (with dates)
- skills: Technical and soft skills
- projects: Notable projects (with dates)
- achievements: Awards and recognitions (with dates/year)
- certifications: Professional certifications
- email: Contact email (if publicly visible)
- website: Personal website/Portfolio
- linkedin: LinkedIn URL
- github: GitHub URL
- social_links: Other social profiles (Twitter/X, Medium, etc.)

**Phase 2: LINK EXTRACTION (CRITICAL FOR ENRICHMENT)**
You MUST also extract a comprehensive list of related links:
- related_links: Array of objects with:
  - url: The full URL
  - title: Page/article title
  - type: "article", "blog", "portfolio", "project", "social", "mention", "other"
  - description: Brief description of the content
  - source: Publisher/platform name if identifiable
  
**EXCLUSION:** Do NOT include the primary source URL ({url}) in related_links - only additional discovered links.

**LINK DISCOVERY STRATEGY:**
1. For LinkedIn URLs: Use ONLY Google Search (not url_context) to find mentions
2. For other URLs: Use BOTH url_context AND google_search
3. SMART SEARCH QUERIES (use person's name + company if known):
   - "[Person Name] [Company] awards recognition"
   - "[Person Name] [Company] interview podcast"
   - "[Person Name] [Company] published article blog"
   - "[Person Name] [Company] speaking conference presentation"
   - "[Person Name] [Company] portfolio projects work"
   - "[Person Name] [Company] featured mentioned press"
   - "[Person Name] [Company] github repository code"
   - "[Person Name] [Company] linkedin profile about"
   - "[Person Name] [Title/Role] industry insights"
   - "[Person Name] [Title/Role] expert opinion"

**LINK INTELLIGENCE REQUIREMENTS:**
- Return DIRECT links to specific pages that mention the person (not homepage/base URLs)
- Example: Return "https://techblog.com/interview-with-john-doe-2024" NOT "https://techblog.com"
- Prioritize content-rich pages: awards, interviews, publications, articles, project showcases, conference talks
- Include publication dates in descriptions when visible
- Focus on recent content (last 3-5 years) but include significant older achievements
- Target 10-20 high-quality specific links rather than 5 general ones

**CRITICAL DATA INTEGRITY RULES:**
1. **IDENTITY ANCHOR:** The person is defined ONLY by the URL: {url}
2. **STRICT VERIFICATION:** Verify identity using (Name and/or Company), can also consider Title (but not too strict)
3. **NO HALLUCINATION:** If unsure a link belongs to THIS person, exclude it
4. **TIMELINE FOCUS:** Capture dates for ALL awards, experiences, publication, achievements, projects, etc

**VERIFICATION:**
Before adding any field or link, ask: "Is this definitely the same person?"

Return a JSON object. Use null for missing string fields and empty arrays [] for missing list fields.
Include the "related_links" array with all discovered links for enrichment."""


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
