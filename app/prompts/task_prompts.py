"""Task planning and Chain of Thought prompts for Gemini AI.

This module contains prompts for generating task plans using
Chain of Thought reasoning for the profile-to-journey pipeline.
"""

from typing import Dict, Any, List


# JSON Schema for task planning
TASK_PLAN_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "plan_id": {"type": "string"},
        "total_tasks": {"type": "number"},
        "estimated_duration_seconds": {"type": "number"},
        "tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "order": {"type": "number"},
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "estimated_seconds": {"type": "number"},
                    "dependencies": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Task IDs this task depends on"
                    },
                    "retry_strategy": {
                        "type": "object",
                        "properties": {
                            "max_retries": {"type": "number"},
                            "backoff_seconds": {"type": "number"}
                        }
                    },
                    "critical": {"type": "boolean", "description": "If true, failure stops pipeline"},
                    "outputs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "What this task produces"
                    }
                },
                "required": ["task_id", "order", "name", "description"]
            }
        },
        "reasoning": {"type": "string", "description": "Chain of Thought reasoning for the plan"}
    }
}


def get_task_planning_prompt(source_url: str, options: Dict[str, Any]) -> str:
    """Generate Chain of Thought task planning prompt.
    
    Args:
        source_url: The source URL to process
        options: Processing options (include_github, etc.)
        
    Returns:
        Formatted CoT planning prompt
    """
    include_github = options.get('include_github', False)
    
    return f"""You are a task planning AI that uses Chain of Thought reasoning to create optimal execution plans.

**SOURCE TO PROCESS:**
URL: {source_url}
Include GitHub OAuth: {include_github}

**CHAIN OF THOUGHT REASONING:**

Let me think through this step by step...

1. **Source Analysis:**
   - What type of URL is this? (LinkedIn, GitHub, personal website, etc.)
   - What data can we expect to extract?
   - Are there related sources to discover?

2. **Data Dependencies:**
   - Profile extraction must complete before journey structuring
   - Timeline requires structured journey data
   - Documentary needs both journey and timeline data

3. **Optimization Considerations:**
   - Can any tasks run in parallel?
   - What's the critical path?
   - Where might failures occur?

4. **Task Breakdown:**
   Based on the source type and requirements, generate the optimal task sequence.

**AVAILABLE TASK TYPES:**
- `fetch_profile`: Extract profile data from URL using Gemini 3
- `enrich_profile`: Aggregate data from discovered sources
- `aggregate_history`: Merge with existing profile history (if any)
- `structure_journey`: Transform profile into structured journey
- `generate_timeline`: Create timeline visualization data
- `generate_documentary`: Create documentary narrative and segments
- `generate_video`: Create video segments using Veo 3.1 (optional, expensive)

**TASK PLAN REQUIREMENTS:**
- Each task must have unique ID (e.g., "task_001")
- Order must be sequential where dependencies exist
- Estimate realistic durations (profile extraction: 30-60s, journey: 15-30s, etc.)
- Mark critical tasks that would fail the entire pipeline
- Define clear outputs for each task

**OUTPUT:**
Generate a JSON task plan with:
- plan_id: Unique identifier for this execution plan
- total_tasks: Number of tasks
- estimated_duration_seconds: Total estimated time
- tasks: Array of task definitions
- reasoning: Your Chain of Thought reasoning explaining the plan

Think carefully about the optimal execution order and parallelization opportunities."""


def get_task_coordination_prompt(
    current_task: Dict[str, Any],
    completed_tasks: List[Dict[str, Any]],
    pending_tasks: List[Dict[str, Any]]
) -> str:
    """Generate prompt for coordinating between tasks.
    
    Args:
        current_task: The task currently executing
        completed_tasks: Tasks that have completed
        pending_tasks: Tasks still to execute
        
    Returns:
        Formatted coordination prompt
    """
    completed_summary = "\n".join([
        f"- [{t['task_id']}] {t['name']}: {t.get('status', 'completed')}"
        for t in completed_tasks
    ]) or "None"
    
    pending_summary = "\n".join([
        f"- [{t['task_id']}] {t['name']} (depends on: {', '.join(t.get('dependencies', []))})"
        for t in pending_tasks
    ]) or "None"
    
    return f"""You are coordinating task execution in a pipeline.

**CURRENT TASK:**
ID: {current_task['task_id']}
Name: {current_task['name']}
Description: {current_task['description']}

**COMPLETED TASKS:**
{completed_summary}

**PENDING TASKS:**
{pending_summary}

**COORDINATION CHECK:**
1. Are all dependencies for the current task satisfied?
2. What data should be passed from completed tasks?
3. Are there any warnings or issues to flag?
4. Can any pending tasks be parallelized after this completes?

Provide coordination guidance as JSON with:
- can_proceed: boolean
- input_data_mapping: which outputs from completed tasks to use
- warnings: any issues detected
- parallelizable_next: task IDs that can run in parallel next"""
