"""Utility Functions for Task Orchestrator.

Parsing, validation, and helper functions.
"""

import json
import logging
from typing import Dict, Any, Type

logger = logging.getLogger(__name__)


def parse_json_response(text: str) -> Dict[str, Any]:
    """Parse JSON response from Gemini, handling markdown code blocks.
    
    This is a basic JSON parser for legacy compatibility.
    For production use, prefer parse_and_validate_response with Pydantic models.
    """
    if not text or not isinstance(text, str):
        logger.warning("Empty or invalid text provided for JSON parsing")
        return {}
        
    text = text.strip()
    if text.startswith('```json'):
        text = text[7:]
    if text.startswith('```'):
        text = text[3:]
    if text.endswith('```'):
        text = text[:-3]
    text = text.strip()
    
    if not text:
        logger.warning("Text is empty after cleaning")
        return {}
    
    try:
        result = json.loads(text)
        logger.info(f"Successfully parsed JSON response with keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
        return result
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}")
        logger.error(f"Raw text: {text[:500]}...")
        return {}


def parse_and_validate_response(
    text: str, 
    model_class: Type,
    fallback_to_dict: bool = True
) -> Dict[str, Any]:
    """Parse and validate JSON response from Gemini using Pydantic models.
    
    This is the production-grade approach for Gemini structured output parsing.
    
    Args:
        text: Raw response text from Gemini API
        model_class: Pydantic model class for validation
        fallback_to_dict: If True, fall back to basic JSON parsing on validation error
        
    Returns:
        Validated data as dictionary, or empty dict on failure
    """
    if not text or not isinstance(text, str):
        logger.warning("Empty or invalid text provided for Pydantic parsing")
        return {}
    
    # Clean markdown code blocks
    text = text.strip()
    if text.startswith('```json'):
        text = text[7:]
    if text.startswith('```'):
        text = text[3:]
    if text.endswith('```'):
        text = text[:-3]
    text = text.strip()
    
    if not text:
        logger.warning("Text is empty after cleaning")
        return {}
    
    try:
        # Try Pydantic validation first
        validated_model = model_class.model_validate_json(text)
        
        # Convert to dictionary, excluding None values
        result = validated_model.model_dump(exclude_none=True)
        
        logger.info(
            f"Successfully validated {model_class.__name__} with keys: "
            f"{list(result.keys()) if isinstance(result, dict) else 'Not a dict'}"
        )
        return result
        
    except Exception as validation_error:
        logger.warning(
            f"Pydantic validation failed for {model_class.__name__}: {validation_error}"
        )
        
        if fallback_to_dict:
            logger.info("Falling back to basic JSON parsing...")
            try:
                result = json.loads(text)
                logger.info(
                    f"Fallback JSON parsing succeeded with keys: "
                    f"{list(result.keys()) if isinstance(result, dict) else 'Not a dict'}"
                )
                return result if isinstance(result, dict) else {}
            except json.JSONDecodeError as json_error:
                logger.error(f"Fallback JSON parsing also failed: {json_error}")
                logger.error(f"Raw text: {text[:500]}...")
                return {}
        else:
            logger.error(f"No fallback enabled, returning empty dict")
            return {}
