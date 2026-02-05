"""Journey structuring, timeline, and documentary prompts for Gemini AI.

This module contains all prompts related to journey structuring,
timeline generation, and documentary narrative creation.
"""

from typing import Dict, Any


# JSON Schema for journey structure
JOURNEY_STRUCTURE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {
            "type": "object",
            "properties": {
                "headline": {"type": "string", "description": "One-liner professional headline"},
                "narrative": {"type": "string", "description": "3-4 sentence journey summary"},
                "career_span": {"type": "string", "description": "e.g., '2015 - Present (9 years)'"},
                "key_themes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "3-5 key themes of the career"
                }
            },
            "required": ["headline", "narrative", "career_span", "key_themes"]
        },
        "milestones": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": ["career", "education", "achievement", "project", "certification"]
                    },
                    "significance": {
                        "type": "string",
                        "enum": ["major", "moderate", "minor"]
                    },
                    "impact_statement": {"type": "string"}
                },
                "required": ["date", "title", "description", "category"]
            }
        },
        "career_chapters": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Chapter title e.g., 'The Foundation Years'"},
                    "period": {"type": "string"},
                    "narrative": {"type": "string"},
                    "key_learnings": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "3-5 key learnings from this chapter"
                    }
                },
                "required": ["title", "period", "narrative", "key_learnings"]
            }
        },
        "skills_evolution": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "period": {"type": "string", "description": "Time period (e.g., '2015-2017', 'Early Career')"},
                    "stage": {"type": "string", "description": "Career stage name"},
                    "milestone": {"type": "string", "description": "Key milestone achieved"},
                    "year": {"type": "string", "description": "Alternative to period for single year"},
                    "description": {"type": "string", "description": "What was learned/achieved"},
                    "skills_acquired": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific skills gained during this period"
                    }
                },
                "required": ["period", "stage", "description", "skills_acquired"]
            }
        },
        "impact_metrics": {
            "type": "object",
            "properties": {
                "years_experience": {"type": "number"},
                "companies_count": {"type": "number"},
                "projects_count": {"type": "number"},
                "skills_count": {"type": "number"}
            }
        }
    },
    "required": ["summary", "milestones", "career_chapters", "skills_evolution", "impact_metrics"]
}


# JSON Schema for timeline data
TIMELINE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "date": {"type": "string", "description": "ISO date or year"},
                    "end_date": {"type": "string", "description": "For ranges"},
                    "title": {"type": "string"},
                    "subtitle": {"type": "string"},
                    "description": {"type": "string"},
                    "category": {"type": "string"},
                    "icon": {"type": "string"},
                    "color": {"type": "string"},
                    "media": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "url": {"type": "string"},
                            "caption": {"type": "string"}
                        }
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["id", "date", "title"]
            }
        },
        "eras": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                    "color": {"type": "string"}
                }
            }
        },
        "required": ["events"]
    }
}


# JSON Schema for documentary narrative
DOCUMENTARY_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "Documentary title"},
        "tagline": {"type": "string", "description": "Catchy one-liner"},
        "duration_estimate": {"type": "string", "description": "Estimated runtime"},
        "segments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "order": {"type": "number"},
                    "title": {"type": "string"},
                    "duration_seconds": {"type": "number", "description": "8-30 seconds"},
                    "visual_description": {"type": "string", "description": "What should be shown"},
                    "narration": {"type": "string", "description": "Voiceover script"},
                    "mood": {
                        "type": "string",
                        "enum": ["inspirational", "professional", "dynamic", "reflective", "triumphant"]
                    },
                    "background_music_hint": {"type": "string"},
                    "data_visualization": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "data_points": {"type": "array"}
                        }
                    }
                }
            }
        },
        "opening_hook": {"type": "string", "description": "Compelling opening statement"},
        "closing_statement": {"type": "string", "description": "Memorable conclusion"},
        "required": ["title", "tagline", "opening_hook", "segments"]
    }
}


def get_journey_structuring_prompt(profile_data: Dict[str, Any]) -> str:
    """Generate prompt for structuring the professional journey.
    
    Args:
        profile_data: Extracted profile data
        
    Returns:
        Formatted prompt for journey structuring
    """
    return f"""You are a professional story architect. Transform raw profile data into a compelling professional journey narrative.

**PROFILE DATA:**
{_format_profile_for_prompt(profile_data)}

**TASK: Structure the Professional Journey**

Create a structured journey that:
1. **Identifies Key Milestones** - Career pivots, achievements, major projects
2. **Groups into Career Chapters** - Logical phases of professional growth
3. **Tracks Skills Evolution** - How expertise developed over time
4. **Quantifies Impact** - Numbers and metrics where possible

**NARRATIVE GUIDELINES:**
- Write in third person, professional tone
- Focus on growth, challenges overcome, and impact made
- Create compelling chapter titles (e.g., "The Foundation Years", "Rising Through the Ranks")
- Highlight transitions and pivotal moments
- Make it inspirational yet authentic

**OUTPUT REQUIREMENTS:**
- summary: Headline, narrative, career span, key themes
- milestones: Chronologically ordered significant events
- career_chapters: 3-5 distinct career phases with narratives and key learnings
- skills_evolution: CRITICAL - Detailed progression showing skills acquired over time with periods, stages, milestones, descriptions, and context
- impact_metrics: Quantified career statistics

**CRITICAL: Skills Evolution Structure**
The skills_evolution array MUST capture the complete skill development journey:
- Each entry should represent a distinct period/stage in skill development
- Include specific skills acquired during that period
- Provide context for why skills were developed (job requirements, projects, interests)
- Show progression from beginner to expert levels
- Connect skills to career milestones and projects

Example structure:
```json
"skills_evolution": [
  {{
    "period": "2015-2017",
    "stage": "Foundation Years",
    "milestone": "Starting Programming Career", 
    "description": "Built fundamental programming skills through education and first projects",
    "skills_acquired": ["Python", "JavaScript", "HTML/CSS", "Git"],
    "skill_level": "Beginner to Intermediate",
    "context": "University coursework and first internships"
  }},
  {{
    "period": "2018-2020", 
    "stage": "Professional Growth",
    "milestone": "First Full-Stack Developer Role",
    "description": "Expanded to full-stack development and learned modern frameworks",
    "skills_acquired": ["React", "Node.js", "MongoDB", "AWS"],
    "skill_level": "Intermediate to Advanced",
    "context": "Industry demands and project requirements"
  }}
]
```

Return a JSON object following the journey structure schema."""


def get_timeline_generation_prompt(journey_data: Dict[str, Any]) -> str:
    """Generate prompt for creating timeline visualization data.
    
    Args:
        journey_data: Structured journey data
        
    Returns:
        Formatted prompt for timeline generation
    """
    return f"""You are a data visualization specialist. Transform journey data into timeline visualization format.

**JOURNEY DATA:**
{_format_journey_for_prompt(journey_data)}

**TASK: Generate Timeline Data**

Create timeline events that:
1. Are chronologically ordered
2. Have appropriate icons and colors per category
3. Include media references where applicable
4. Define career eras for background visualization

**CATEGORY COLOR SCHEME:**
- career: #0066FF (blue)
- education: #00CC66 (green)
- achievement: #FFD700 (gold)
- project: #9933FF (purple)
- certification: #FF6633 (orange)

**ICON MAPPING:**
- career: briefcase
- education: graduation-cap
- achievement: trophy
- project: code
- certification: certificate

**OUTPUT:**
Return JSON with:
- events: Array of timeline events
- eras: Career era definitions for background bands

Ensure dates are in ISO format (YYYY-MM-DD) or at minimum YYYY for display."""


def get_documentary_narrative_prompt(journey_data: Dict[str, Any], profile_data: Dict[str, Any]) -> str:
    """Generate prompt for documentary video narrative creation.
    
    Args:
        journey_data: Structured journey data
        profile_data: Original profile data
        
    Returns:
        Formatted prompt for documentary narrative
    """
    name = profile_data.get('name', 'the subject')
    
    return f"""You are a documentary filmmaker and scriptwriter. Create a compelling video documentary narrative for {name}'s professional journey.

**JOURNEY DATA:**
{_format_journey_for_prompt(journey_data)}

**DOCUMENTARY REQUIREMENTS:**
- Total duration: 8-40 seconds (broken into 8 seconds segments)
- Segments: 1-5 distinct video segments
- Tone: Inspirational, professional, and authentic
- Visual style: Modern, clean, data-driven with emotional moments

**SEGMENT STRUCTURE:**
Each segment needs:
1. **Title** - Segment name
2. **Duration** - 8 seconds (fixed)
3. **Visual Description** - What viewers see (REQUIRED for Veo 3.1 generation)
4. **Narration** - Voiceover script (REQUIRED, 10-15 words max for 8-second segments)
5. **Mood** - Emotional tone (inspirational, professional, dynamic, reflective, triumphant)
6. **Background Music Hint** - Music style suggestion
7. **Data Visualization** - Any charts/graphs to show (type and data_points)

**CRITICAL VEO 3.1 REQUIREMENTS:**
- Narration MUST be between 10-15 words for 8-second segments
- Narration MUST be provided (segments without narration will be skipped)
- Visual Description MUST be provided (segments without visuals will be skipped)
- Mood helps determine voice quality (warm/uplifting, clear/authoritative, energetic, thoughtful, confident)

**DOCUMENTARY FLOW:**
1. Opening Hook - Grab attention immediately (120 characters max)
2. Origin Story - Where it all began
3. Journey Highlights - Key milestones and achievements
4. Challenges & Growth - Obstacles overcome
5. Impact & Legacy - What they've accomplished
6. Future Vision - What's next (optional)
7. Closing Statement - Memorable conclusion (100 characters max)

**VISUAL DESCRIPTIONS FOR VEO:**
Be specific about:
- Camera angles and movements (e.g., "Medium close-up tracking shot", "Wide establishing shot")
- Color palettes and lighting (e.g., "Cool blue professional lighting", "Warm amber tones")
- Subject positioning and framing (e.g., "Professional in modern office, centered frame")
- Data visualizations to render (e.g., "Rising bar chart showing growth metrics")
- Transitions between segments (e.g., "Fade to black", "Cross-dissolve to next scene")

**NARRATION GUIDELINES:**
- Keep it concise: 10-15 words maximum per 8-second segment
- Make every word count - avoid filler
- Use strong, active voice
- Create emotional connection
- Build narrative momentum

**EXAMPLE NARRATION (22 words):**
"In 2015, Kennedy took his first step into software engineering. What started as curiosity became a career defined by innovation and impact."

Return a JSON object with the complete documentary structure."""


def _format_profile_for_prompt(profile_data: Dict[str, Any]) -> str:
    """Format profile data for inclusion in prompts."""
    if not profile_data or not isinstance(profile_data, dict):
        return "No profile data available"
    
    sections = []
    
    if profile_data.get('name'):
        sections.append(f"Name: {profile_data['name']}")
    if profile_data.get('title'):
        sections.append(f"Title: {profile_data['title']}")
    if profile_data.get('location'):
        sections.append(f"Location: {profile_data['location']}")
    if profile_data.get('bio'):
        sections.append(f"Bio: {profile_data['bio'][:500]}")
    
    if profile_data.get('experiences') and isinstance(profile_data['experiences'], list):
        exp_list = []
        for exp in profile_data['experiences'][:5]:
            if isinstance(exp, dict):
                exp_str = f"- {exp.get('title', 'N/A')} at {exp.get('company', 'N/A')} ({exp.get('duration', 'N/A')})"
                exp_list.append(exp_str)
        if exp_list:
            sections.append(f"Experiences:\n" + "\n".join(exp_list))
    
    if profile_data.get('skills') and isinstance(profile_data['skills'], list):
        sections.append(f"Skills: {', '.join(str(s) for s in profile_data['skills'][:15])}")
    
    if profile_data.get('achievements') and isinstance(profile_data['achievements'], list):
        ach_list = []
        for a in profile_data['achievements'][:3]:
            if isinstance(a, dict):
                ach_list.append(f"- {a.get('title', 'N/A')} ({a.get('date', 'N/A')})")
        if ach_list:
            sections.append(f"Achievements:\n" + "\n".join(ach_list))
    
    return "\n\n".join(sections) if sections else "Limited profile data available"


def _format_journey_for_prompt(journey_data: Dict[str, Any]) -> str:
    """Format journey data for inclusion in prompts."""
    sections = []
    
    if journey_data.get('summary'):
        summary = journey_data['summary']
        sections.append(f"Headline: {summary.get('headline', 'N/A')}")
        sections.append(f"Career Span: {summary.get('career_span', 'N/A')}")
    
    if journey_data.get('milestones'):
        milestone_list = [f"- [{m.get('date', 'N/A')}] {m.get('title', 'N/A')}" 
                         for m in journey_data['milestones'][:10]]
        sections.append(f"Key Milestones:\n" + "\n".join(milestone_list))
    
    if journey_data.get('career_chapters'):
        chapter_list = [f"- {c.get('title', 'N/A')} ({c.get('period', 'N/A')})" 
                       for c in journey_data['career_chapters']]
        sections.append(f"Career Chapters:\n" + "\n".join(chapter_list))
    
    return "\n\n".join(sections)
