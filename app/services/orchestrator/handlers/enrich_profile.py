"""Profile Enrichment Handler.

Handles profile enrichment using Gemini 3 Deep Research and GitHub integration.
Uses Gemini's url_context and google_search tools instead of traditional web scraping.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from google.genai import types

from app.services.orchestrator.handlers.base import BaseTaskHandler
from app.services.orchestrator.models import Task, TaskPlan, TaskType
from app.prompts import get_deep_research_enrichment_prompt, ProfileExtractionResult

logger = logging.getLogger(__name__)


class EnrichProfileHandler(BaseTaskHandler):
    """Handler for profile enrichment task using Gemini 3 Deep Research."""
    
    async def execute(self, job_id: str, plan: TaskPlan, task: Task) -> Dict[str, Any]:
        """Handle profile enrichment task with Gemini 3 Deep Research."""
        task.message = "Starting enrichment process..."
        task.progress = 10
        await self.update_progress(job_id, task)
        
        # Get profile data from previous task
        profile_data = plan.result_data.get(TaskType.FETCH_PROFILE.value)
        if not profile_data or not isinstance(profile_data, dict):
            profile_data = {}
        
        # Extract related links discovered by Gemini
        related_links = profile_data.get('related_links', [])
        
        task.progress = 20
        task.message = f"Found {len(related_links)} related links to research"
        await self.update_progress(job_id, task)
        
        enriched_data = {**profile_data}
        deep_research_content = []
        
        # Use Gemini 3 Deep Research for related links instead of web scraping
        if related_links and self.genai_client:
            task.progress = 30
            task.message = "Performing deep research on related links..."
            await self.update_progress(job_id, task)
            
            try:
                research_result = await self._perform_deep_research(
                    profile_data, 
                    related_links, 
                    job_id, 
                    task
                )
                
                if research_result:
                    deep_research_content = research_result.get('enriched_content', [])
                    
                    # Merge additional achievements
                    additional_achievements = research_result.get('additional_achievements', [])
                    if additional_achievements:
                        existing_achievements = enriched_data.get('achievements', []) or []
                        enriched_data['achievements'] = existing_achievements + additional_achievements
                    
                    # Merge additional projects
                    additional_projects = research_result.get('additional_projects', [])
                    if additional_projects:
                        existing_projects = enriched_data.get('projects', []) or []
                        enriched_data['projects'] = existing_projects + additional_projects
                    
                    # Merge additional skills
                    additional_skills = research_result.get('additional_skills', [])
                    if additional_skills:
                        existing_skills = enriched_data.get('skills', []) or []
                        # Deduplicate skills
                        all_skills = list(set(existing_skills + additional_skills))
                        enriched_data['skills'] = all_skills
                    
                    # Add new discovered links
                    new_links = research_result.get('new_links_discovered', [])
                    if new_links:
                        existing_links = enriched_data.get('related_links', []) or []
                        enriched_data['related_links'] = existing_links + new_links
                    
                    # Apply profile updates
                    profile_updates = research_result.get('profile_updates', {})
                    if profile_updates.get('bio_additions'):
                        current_bio = enriched_data.get('bio', '') or ''
                        enriched_data['bio'] = current_bio + '\n\n' + profile_updates['bio_additions']
                    
                    logger.info(f"Deep research enriched: {len(deep_research_content)} content items, "
                               f"{len(additional_achievements)} achievements, "
                               f"{len(additional_projects)} projects")
                
            except Exception as research_error:
                logger.error(f"Error during deep research: {research_error}")
                # Fall back to basic link info without scraping
                deep_research_content = [
                    {
                        'url': link.get('url', ''),
                        'title': link.get('title', ''),
                        'type': link.get('type', 'unknown'),
                        'description': link.get('description', ''),
                        'content_summary': 'Research pending'
                    }
                    for link in related_links[:10] if link.get('url')
                ]
        
        task.progress = 60
        task.message = f"Researched {len(deep_research_content)} sources"
        await self.update_progress(job_id, task)
        
        # Add research content to enriched data (replaces scraped_content)
        enriched_data['deep_research_content'] = deep_research_content
        enriched_data['enrichment_stats'] = {
            'related_links_found': len(related_links),
            'links_researched': min(len(related_links), 20),
            'successful_research': len(deep_research_content),
            'enrichment_method': 'gemini_deep_research'
        }
        
        # Check for GitHub OAuth enrichment (RETAINED - important for profile)
        guest_user_id = plan.options.get('guest_user_id')
        if guest_user_id:
            task.progress = 70
            task.message = "Checking GitHub integration..."
            await self.update_progress(job_id, task)
            
            github_enrichment = await self._enrich_with_github(guest_user_id, task, job_id)
            if github_enrichment:
                enriched_data['github_data'] = github_enrichment
                enriched_data['enrichment_stats']['github_enriched'] = True
                logger.info(f"GitHub enrichment added: {github_enrichment.get('total_repos', 0)} repos")
        
        task.progress = 90
        task.message = "Enrichment complete"
        await self.update_progress(job_id, task)
        
        # Mark enrichment metadata
        enriched_data['enriched'] = True
        enriched_data['enrichment_timestamp'] = datetime.utcnow().isoformat()
        
        logger.info(f"Profile enrichment complete: {enriched_data.get('enrichment_stats')}")
        
        return enriched_data
    
    async def _perform_deep_research(
        self,
        profile_data: Dict[str, Any],
        related_links: List[Dict[str, Any]],
        job_id: str,
        task: Task
    ) -> Optional[Dict[str, Any]]:
        """Perform deep research using Gemini 3's url_context and google_search tools.
        
        This replaces the traditional web scraping approach with AI-powered research.
        """
        if not self.genai_client:
            logger.warning("Gemini client not available for deep research")
            return None
        
        # Filter to valid URLs only
        valid_links = [
            link for link in related_links 
            if isinstance(link, dict) and link.get('url')
        ][:20]  # Limit to 20 links
        
        if not valid_links:
            logger.info("No valid links to research")
            return None
        
        task.message = f"Deep researching {len(valid_links)} links..."
        await self.update_progress(job_id, task)
        
        # Get the deep research prompt
        prompt = get_deep_research_enrichment_prompt(profile_data, valid_links)
        
        try:
            # Use Gemini 3 with url_context and google_search for comprehensive research
            response = await asyncio.to_thread(
                self.genai_client.models.generate_content,
                model="gemini-3-flash-preview",
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[{"url_context": {}}, {"google_search": {}}],
                    response_mime_type="application/json"
                )
            )
            
            result = json.loads(response.text)
            
            # Sort enriched content by relevance score if available
            if 'enriched_content' in result:
                result['enriched_content'] = sorted(
                    result['enriched_content'],
                    key=lambda x: x.get('relevance_score', 5),
                    reverse=True
                )
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse deep research response: {e}")
            # Try to extract partial data
            try:
                # Attempt to clean and parse
                text = response.text.strip()
                if text.startswith('```json'):
                    text = text[7:]
                if text.endswith('```'):
                    text = text[:-3]
                return json.loads(text)
            except:
                return None
        except Exception as e:
            logger.error(f"Deep research failed: {e}")
            # Try without url_context if it fails
            try:
                response = await asyncio.to_thread(
                    self.genai_client.models.generate_content,
                    model="gemini-3-flash-preview",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        tools=[{"google_search": {}}],
                        response_mime_type="application/json"
                    )
                )
                return json.loads(response.text)
            except Exception as fallback_error:
                logger.error(f"Deep research fallback also failed: {fallback_error}")
                return None
    
    async def _enrich_with_github(
        self, 
        guest_user_id: str, 
        task: Task, 
        job_id: str
    ) -> Optional[Dict[str, Any]]:
        """Enrich profile with GitHub data if OAuth is available."""
        from app.db.session import get_db
        from app.models.user import User
        from sqlalchemy import select
        import httpx
        
        async for db in get_db():
            try:
                result = await db.execute(
                    select(User).where(User.guest_id == guest_user_id)
                )
                user = result.scalar_one_or_none()
                
                if not user or not user.github_access_token:
                    return None
                
                task.message = "Enriching with GitHub data..."
                await self.update_progress(job_id, task)
                
                github_data = {
                    'username': user.github_username,
                    'authenticated': True,
                    'repositories': [],
                    'contributions': {},
                    'languages': {},
                    'significant_projects': []
                }
                
                headers = {
                    "Authorization": f"Bearer {user.github_access_token}",
                    "Accept": "application/vnd.github+json"
                }
                
                async with httpx.AsyncClient(timeout=30.0) as client:
                    # Fetch user's repositories
                    repos_response = await client.get(
                        f"https://api.github.com/users/{user.github_username}/repos",
                        headers=headers,
                        params={"sort": "updated", "per_page": 30}
                    )
                    
                    if repos_response.status_code == 200:
                        repos = repos_response.json()
                        
                        significant_repos = []
                        language_stats = {}
                        
                        for repo in repos:
                            if repo.get('language'):
                                lang = repo['language']
                                language_stats[lang] = language_stats.get(lang, 0) + 1
                            
                            stars = repo.get('stargazers_count', 0)
                            forks = repo.get('forks_count', 0)
                            
                            if stars >= 1 or forks >= 1 or repo.get('description'):
                                significant_repos.append({
                                    'name': repo['name'],
                                    'description': repo.get('description', ''),
                                    'url': repo['html_url'],
                                    'stars': stars,
                                    'forks': forks,
                                    'language': repo.get('language'),
                                    'updated_at': repo.get('updated_at'),
                                    'topics': repo.get('topics', [])
                                })
                        
                        significant_repos.sort(
                            key=lambda x: x['stars'] + x['forks'], 
                            reverse=True
                        )
                        
                        github_data['repositories'] = repos[:10]
                        github_data['significant_projects'] = significant_repos[:10]
                        github_data['languages'] = language_stats
                        github_data['total_repos'] = len(repos)
                    
                    # Fetch contribution stats
                    events_response = await client.get(
                        f"https://api.github.com/users/{user.github_username}/events",
                        headers=headers,
                        params={"per_page": 100}
                    )
                    
                    if events_response.status_code == 200:
                        events = events_response.json()
                        
                        event_counts = {}
                        for event in events:
                            event_type = event.get('type', 'Unknown')
                            event_counts[event_type] = event_counts.get(event_type, 0) + 1
                        
                        github_data['contributions'] = {
                            'recent_events': len(events),
                            'event_types': event_counts,
                            'push_events': event_counts.get('PushEvent', 0),
                            'pr_events': event_counts.get('PullRequestEvent', 0),
                            'issue_events': event_counts.get('IssuesEvent', 0),
                        }
                
                logger.info(f"GitHub enrichment completed for user {user.id}")
                return github_data
                
            except Exception as e:
                logger.error(f"GitHub enrichment failed: {e}")
                return None
            finally:
                break
        
        return None
