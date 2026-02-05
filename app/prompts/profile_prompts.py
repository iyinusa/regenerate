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
        "passport": {"type": "string", "description": "Passport photo or profile image URL"},
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
    "required": ["name", "title",  "bio", "education", "experiences", "skills"]
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
   - Article mentions (news, interviews, features, awards, publications)
   - Blog posts they are featured in
   - Speaking engagements or event appearances
   - Project showcases
   - Social media profiles
   - Portfolio pages
   - Awards or recognitions
   - Any public mentions or references

**URL TO ANALYZE:** {url}

**TWO-PHASE EXTRACTION:**

**Phase 1: Basic Profile Data & Link Discovery**
Extract the standard profile fields:
- name: Full name
- passport: URL to profile image or passport photo
- title: Current professional title or role
- location: Geographic location
- bio: Professional summary
- experiences: Work history (with start/end dates)
- education: Educational history (with dates)
- skills: Technical, leadership, tools, and soft skills
- projects: Notable projects (with dates)
- achievements: Awards and recognitions (with dates/year)
- certifications: Professional certifications
- publications: Published works (if any, with dates/year)
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
  - type: "article", "blog", "portfolio", "project", "research", "social", "mention", "other"
  - description: Brief description of the content
  - source: Publisher/platform name if identifiable
  
**EXCLUSION:** Do NOT include the primary source URL ({url}) in related_links - only additional discovered links.

**LINK DISCOVERY STRATEGY:**
1. For LinkedIn URLs: Use ONLY Google Search (not url_context) to find mentions
2. For other URLs: Use BOTH url_context AND google_search
3. SMART SEARCH QUERIES (use person's name + company if known):
   - "[Person Name] [Company] awards"
   - "[Person Name] [Company] interview"
   - "[Person Name] [Company] published article blog"
   - "[Person Name] [Company] research paper"
   - "[Person Name] [Company] speaking conference presentation"
   - "[Person Name] [Company] portfolio projects work"
   - "[Person Name] [Company] featured mentioned press"
   - "[Person Name] [Company] github repository code"
   - "[Person Name] [Company] linkedin profile about"
   - "[Person Name] [Title/Role] industry insights"
   - "[Person Name] [Title/Role] expert opinion"

**LINK INTELLIGENCE REQUIREMENTS:**
- Return DIRECT links to specific pages that mention the person (not homepage/base URLs)
- Example: Return "https://techblog.com/interview-with-kennedy-yinusa-2024" NOT "https://techblog.com"
- Prioritize content-rich pages: awards, interviews, publications, research, articles, project showcases, conference talks, events
- Include publication dates in descriptions when visible
- Focus on recent content (last 3-5 years) but include significant older achievements
- Target 10-20 high-quality specific links rather than 5 general ones
- Links MUST be accessible and publicly available.

**CRITICAL DATA INTEGRITY RULES:**
1. **IDENTITY ANCHOR:** The person is defined ONLY by the URL: {url}
2. **STRICT VERIFICATION:** Verify identity using (Name and/or Company), can also consider Title
3. **NO HALLUCINATION:** If unsure a link mention or belongs to THIS person, exclude it
4. **TIMELINE FOCUS:** Capture dates for ALL awards, experiences, publication, achievements, projects, etc

**VERIFICATION:**
Before adding any field or link, ask: "Is this definitely the same person?" (VERY IMPORTANT)

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

def get_resume_extraction_prompt() -> str:
    """Generate the resume PDF extraction prompt for Gemini 3.
    
    This prompt is used when extracting profile data from an uploaded PDF resume.
    It leverages Gemini 3's native PDF processing capabilities.
    
    Returns:
        Formatted prompt string for Gemini 3 resume extraction
    """
    return """You are a precise data extraction assistant using Gemini 3. Your goal is to extract comprehensive profile information from the provided resume PDF document.

**CORE DIRECTIVE: COMPREHENSIVE EXTRACTION FROM PDF**
Extract ALL relevant professional information from the resume document. Be thorough and accurate.

**EXTRACTION FIELDS:**

1. **Basic Information:**
   - name: Full name of the person
   - passport: Profile photo if visible in the PDF (otherwise null)
   - title: Current or most recent job title/professional role
   - location: Geographic location if mentioned
   - bio: Professional summary/objective statement if present

2. **Professional Experience:**
   For each position, extract:
   - company: Company/organization name
   - title: Job title held
   - duration: Human-readable duration (e.g., "Jan 2020 - Present")
   - start_date: Start date (ISO format if possible)
   - end_date: End date or "Present"
   - description: Job description and responsibilities
   - highlights: Key achievements and accomplishments

3. **Education:**
   For each educational entry:
   - institution: School/university name
   - degree: Degree type (BS, MS, PhD, etc.)
   - field: Field of study/major
   - duration: Time period
   - start_date/end_date: Dates if available

4. **Skills:**
   - Extract ALL mentioned skills (technical, soft skills, tools, languages)
   - Include skill categories if grouped in the resume

5. **Projects:**
   For each project mentioned:
   - name: Project name
   - description: What the project does
   - technologies: Tech stack used
   - impact: Measurable outcomes if mentioned
   - date: When it was done

6. **Achievements & Certifications:**
   - Awards, recognitions, publications
   - Professional certifications with dates and issuers

7. **Contact & Links:**
   - email: Contact email if present
   - website: Personal website/portfolio URL
   - linkedin: LinkedIn profile URL if mentioned
   - github: GitHub profile URL if mentioned
   - social_links: Other social/professional links

8. **Related Links:**
   - Extract any URLs mentioned in the resume for enrichment
   - Include portfolio links, project URLs, publication links

**EXTRACTION RULES:**
1. Extract EXACTLY what is in the document - do not fabricate data
2. If a field is not present, return null for strings or empty arrays []
3. Preserve original formatting for dates when possible
4. Capture ALL experiences, not just recent ones
5. Extract quantifiable achievements (numbers, percentages, metrics)
6. Include any publications, patents, or research mentioned

**OUTPUT FORMAT:**
Return a valid JSON object matching the ProfileExtractionResult schema.
Ensure all dates are extracted to enable timeline generation.

Return the complete extracted profile data in JSON format."""


def get_deep_research_enrichment_prompt(profile_data: Dict[str, Any], related_links: list) -> str:
    """Generate prompt for deep research enrichment using Gemini 3.
    
    This prompt leverages Gemini 3's url_context and google_search tools
    to perform comprehensive research on related links instead of web scraping.
    
    Args:
        profile_data: Existing profile data from fetch stage
        related_links: List of related link objects with url, title, type
        
    Returns:
        Formatted prompt string for Gemini 3 deep research
    """
    name = profile_data.get('name', 'Unknown')
    title = profile_data.get('title', 'Unknown')
    company = None
    
    # Try to get current company from experiences
    experiences = profile_data.get('experiences', [])
    if experiences and len(experiences) > 0:
        company = experiences[0].get('company', '')
    
    # Format related links for the prompt
    links_formatted = []
    for link in related_links[:20]:  # Limit to top 20 links
        if isinstance(link, dict) and link.get('url'):
            link_str = f"- URL: {link['url']}"
            if link.get('title'):
                link_str += f"\n  Title: {link['title']}"
            if link.get('type'):
                link_str += f"\n  Type: {link['type']}"
            if link.get('description'):
                link_str += f"\n  Description: {link['description']}"
            links_formatted.append(link_str)
    
    links_str = "\n".join(links_formatted) if links_formatted else "No specific links provided"
    
    return f"""You are a professional research assistant using Gemini 3's advanced capabilities. Your task is to perform deep research to enrich a professional profile.

**SUBJECT PROFILE:**
Name: {name}
Current Title: {title}
{f"Company: {company}" if company else ""}

**RELATED LINKS TO INVESTIGATE:**
{links_str}

**RESEARCH DIRECTIVE:**
Use url_context tool to analyze each of the related links above and extract relevant information about this person.
Additionally, use google_search to find any other relevant mentions, articles, or achievements.

**EXTRACTION GOALS:**

1. **Article Content:**
   For each link, extract:
   - Main content/article text relevant to the person
   - Publication date if available
   - Author if applicable
   - Key quotes or mentions about the person
   - Context of why this person is mentioned

2. **Additional Achievements:**
   - Awards or recognitions mentioned
   - Speaking engagements or conferences
   - Publications or research papers
   - Interviews or features

3. **Project Details:**
   - Project descriptions from portfolio links
   - Technical details and impact metrics
   - Technologies and methodologies used

4. **Professional Insights:**
   - Industry expertise demonstrated
   - Thought leadership content
   - Community involvement

5. **New Links Discovered:**
   - Any additional relevant links found during research
   - Social profiles not already captured

**VERIFICATION RULES:**
1. ONLY include information that is DEFINITELY about the same person
2. Verify identity using name, title, and company matches
3. DO NOT include information about different people with similar names
4. If uncertain about identity match, exclude the content

**OUTPUT FORMAT:**
Return a JSON object with:
{{
    "enriched_content": [
        {{
            "url": "source URL",
            "title": "page/article title",
            "content_summary": "relevant content about the person",
            "key_points": ["point1", "point2"],
            "publication_date": "date if found",
            "relevance_score": 1-10
        }}
    ],
    "additional_achievements": [
        {{
            "title": "achievement name",
            "date": "when received",
            "description": "details",
            "source": "where found"
        }}
    ],
    "additional_projects": [
        {{
            "name": "project name",
            "description": "what it does",
            "technologies": ["tech1", "tech2"],
            "impact": "measurable outcomes",
            "url": "project URL if any"
        }}
    ],
    "additional_skills": ["skill1", "skill2"],
    "new_links_discovered": [
        {{
            "url": "new URL",
            "title": "page title",
            "type": "article/project/social/etc",
            "description": "why relevant"
        }}
    ],
    "profile_updates": {{
        "bio_additions": "new bio content to add",
        "title_refinement": "more accurate title if found"
    }}
}}

Ensure thorough investigation of each link while maintaining strict identity verification."""