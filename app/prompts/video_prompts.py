"""Video generation prompts for Veo 3.1 AI.

This module contains all prompts and utilities related to Veo 3.1 video generation,
optimized for voiceover detection and visual continuity.
"""

import json
from typing import Dict, Any


def get_character_bible(
    name: str,
    headline: str = None,
    title: str = None,
    industry: str = None
) -> str:
    """Generate a character bible for consistent identity across video segments.
    
    Args:
        name: Full name of the person
        headline: Professional headline from journey summary
        title: Fallback title if no headline
        industry: Industry type to determine cinematographic style
        
    Returns:
        Character bible string for Veo prompt
    """
    # Determine demeanor from headline or title
    demeanor = "Confident, strategic, and visionary"
    if headline:
        demeanor_hint = headline
    elif title:
        demeanor_hint = title
    else:
        demeanor_hint = "professional and accomplished"
    
    # Determine cinematographic style based on industry
    visual_language = "Shallow depth of field (bokeh), professional lighting (cool blues for tech, warm ambers for leadership), and clean minimalist digital overlays"
    
    if industry:
        industry_lower = industry.lower()
        if "tech" in industry_lower or "software" in industry_lower or "engineering" in industry_lower:
            visual_language = "Shallow depth of field (bokeh), cool blue professional lighting, clean minimalist digital overlays with tech-inspired elements"
        elif "finance" in industry_lower or "banking" in industry_lower:
            visual_language = "Sharp focus, sophisticated warm lighting, elegant overlays with financial data visualizations"
        elif "healthcare" in industry_lower or "medical" in industry_lower:
            visual_language = "Clean composition, neutral balanced lighting, professional overlays with health metrics"
        elif "creative" in industry_lower or "design" in industry_lower or "art" in industry_lower:
            visual_language = "Dynamic depth of field, vibrant creative lighting, artistic overlays with bold visual elements"
        elif "education" in industry_lower or "academic" in industry_lower:
            visual_language = "Warm inviting lighting, thoughtful composition, educational overlays with knowledge-sharing elements"
    
    return f"""You are a professional cinematic director. Your task is to maintain strict visual and character continuity for '{name}' across a multi-segment video series.

CHARACTER ANCHORS:
- Identity: {name}
- Demeanor: {demeanor_hint}

CINEMATOGRAPHIC STYLE:
- Pacing: High-end corporate documentary style befitting a {industry or 'professional'}
- Visual Language: {visual_language}
- Continuity: Every segment must feel like it belongs to the same film. If a character is seen as a silhouette in one shot, their build and profile must match the next shot.

AUDIO RULES:
- If a 'Narrator' or 'Voiceover' line is provided in quotes, you must generate a high-quality, professional voiceover that speaks those exact words.
- The voiceover should maintain consistent tone and voice characteristics across all segments."""


def build_veo_segment_prompt(
    segment: Dict[str, Any],
    character_bible: str = None,
    include_character_bible: bool = True
) -> str:
    """Build a Veo 3.1 optimized prompt for a single segment.
    
    Key Rules for Veo 3.1 Voiceovers:
    - The Quote Rule: Always wrap narration in double quotes
    - The Speaker Label: Start with "Narrator:" or "Voiceover:"
    - Tone Cues: Mention voice quality in Audio section using mood
    - Word Count: Keep narration between 10-15 words for 8-second segments
    
    Args:
        segment: Documentary segment data
        character_bible: Character bible for continuity (optional)
        include_character_bible: Whether to include the character bible in prompt
        
    Returns:
        Formatted Veo prompt string
    """
    # Extract required fields (compulsory)
    narration = segment.get("narration", "")
    visual_description = segment.get("visual_description", "")
    
    # Skip segment if compulsory fields are missing
    if not narration or not visual_description:
        return None
    
    # Extract optional fields
    mood = segment.get("mood")
    data_viz = segment.get("data_visualization", {})
    background_music = segment.get("background_music_hint", "")
    
    # Build data visualization hint
    data_hint = ""
    if data_viz and isinstance(data_viz, dict):
        viz_type = data_viz.get("type")
        data_points = data_viz.get("data_points", [])
        if viz_type and data_points:
            data_hint = f"(Data: {', '.join(str(dp) for dp in data_points[:5])}). "
    
    # Determine voice style and pace from mood
    voice_style = "professional, clear"
    pace = "steady"
    if mood:
        mood_lower = mood.lower()
        if mood_lower == "inspirational":
            voice_style = "warm, uplifting"
            pace = "measured"
        elif mood_lower == "professional":
            voice_style = "clear, authoritative"
            pace = "steady"
        elif mood_lower == "dynamic":
            voice_style = "energetic, engaging"
            pace = "brisk"
        elif mood_lower == "reflective":
            voice_style = "thoughtful, contemplative"
            pace = "slow"
        elif mood_lower == "triumphant":
            voice_style = "confident, celebratory"
            pace = "measured"
    
    # Build visual description with data hint
    full_visual_description = visual_description
    if data_hint:
        full_visual_description = f"{visual_description} {data_hint}"
    
    # Determine motion complexity based on mood
    motion_complexity = "medium"
    if mood:
        mood_lower = mood.lower()
        if mood_lower in ["reflective", "professional"]:
            motion_complexity = "low"
        elif mood_lower in ["dynamic", "triumphant"]:
            motion_complexity = "high"
    
    # Build JSON-style segment prompt for Veo 3.1
    segment_data = {
        "id": segment.get("id", "segment_1"),
        "duration_seconds": segment.get("duration_seconds", 8),
        "priority": "narration",
        "narration": {
            "text": narration,
            "start_time_seconds": 0,
            "must_finish": True,
            "voice_style": voice_style,
            "pace": pace
        },
        "visuals": {
            "description": full_visual_description.strip(),
            "motion_complexity": motion_complexity
        },
        "audio": {
            "background_music": background_music if background_music else None
        },
        "lighting": "cool-toned, professional"
    }
    
    # Convert to JSON string with proper formatting
    segment_prompt = json.dumps(segment_data, indent=2)
    
    # Include character bible if provided and requested
    if include_character_bible and character_bible:
        return f"{character_bible}\n\n{segment_prompt}"
    
    return segment_prompt


def validate_segment_for_veo(segment: Dict[str, Any]) -> tuple[bool, str]:
    """Validate if a segment meets Veo requirements.
    
    Args:
        segment: Documentary segment data
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check compulsory fields
    narration = segment.get("narration", "")
    visual_description = segment.get("visual_description", "")
    
    if not narration:
        return False, "Narration is required"
    
    if not visual_description:
        return False, "Visual description is required"
    
    # Check word count (10-15 words recommended for 8-second segments)
    word_count = len(narration.split())
    if word_count > 15:
        return False, f"Narration exceeds 15 words (current: {word_count} words). Recommended: 10-15 words for 8-second segments."
    
    return True, ""


def get_veo_generation_guidelines() -> str:
    """Get comprehensive guidelines for Veo 3.1 video generation.
    
    Returns:
        Guidelines text for reference
    """
    return """
VEO 3.1 VIDEO GENERATION GUIDELINES
====================================

VOICEOVER REQUIREMENTS:
- Quote Rule: Always wrap narration in double quotes: "Spoken text here"
- Speaker Label: Start with "Narrator:" or "Voiceover:"
- Tone Cues: Mention voice quality in Audio section (e.g., "Deep authoritative voice", "Soft female whisper")
- Word Count: For 8-second segments, keep narration between 10-15 words

COMPULSORY SEGMENT FIELDS:
- narration: The voiceover text (required)
- visual_description: What viewers see (required)

OPTIONAL SEGMENT FIELDS:
- mood: Emotional tone (helps determine voice quality)
- data_visualization (type, data_points): Visual data elements
- background_music_hint: Music style suggestion

CHARACTER CONTINUITY:
- Use character bible for consistent identity across segments
- Include name, demeanor, and cinematographic style
- Maintain visual consistency (silhouettes, build, profile)
- Keep voice characteristics consistent

CINEMATOGRAPHIC STYLES BY INDUSTRY:
- Tech/Software: Cool blues, minimalist digital overlays
- Finance: Warm lighting, elegant financial visualizations
- Healthcare: Neutral lighting, professional health metrics
- Creative/Design: Vibrant lighting, bold artistic elements
- Education: Warm inviting lighting, knowledge-sharing elements

PROMPT FORMAT:
```
{character_bible}

CURRENT SEGMENT:
Visual: {visual_description} (Data: {data_points})
Narrator: "{narration}"
Audio: {voice_quality}; {background_music}
```

VALIDATION RULES:
- Skip segments without narration or visual_description
- Validate word count (max 15 words for 8-second segments)
- Ensure consistent character bible across all segments
- Optimize prompt length (max ~500 characters recommended)
"""
