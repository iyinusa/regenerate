"""Profile Enrichment Handler.

Handles profile enrichment with web scraping and GitHub integration.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from app.services.orchestrator.handlers.base import BaseTaskHandler
from app.services.orchestrator.models import Task, TaskPlan, TaskType

logger = logging.getLogger(__name__)


class EnrichProfileHandler(BaseTaskHandler):
    """Handler for profile enrichment task."""
    
    async def execute(self, job_id: str, plan: TaskPlan, task: Task) -> Dict[str, Any]:
        """Handle profile enrichment task with web scraping."""
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
        task.message = f"Found {len(related_links)} related links to enrich"
        await self.update_progress(job_id, task)
        
        enriched_data = {**profile_data}
        scraped_content = []
        
        # Scrape content from related links using BeautifulSoup
        if related_links:
            task.progress = 30
            task.message = "Scraping content from related links..."
            await self.update_progress(job_id, task)
            
            from app.services.web_scraper import web_scraper
            
            # Extract URLs, excluding the primary source URL
            primary_url = profile_data.get('source_url', '')
            urls_to_scrape = [
                link['url'] for link in related_links 
                if link.get('url') and link['url'] != primary_url
            ]
            
            # Limit to top 20 links
            urls_to_scrape = urls_to_scrape[:20]
            
            logger.info(f"Scraping {len(urls_to_scrape)} URLs for enrichment")
            
            try:
                # Scrape all URLs concurrently with rate limiting
                scraped_results = await web_scraper.scrape_multiple_urls(
                    urls=urls_to_scrape,
                    max_concurrent=5
                )
                
                # Filter successful scrapes and format for Gemini
                for result in scraped_results:
                    if result.get('success'):
                        scraped_content.append({
                            'url': result['url'],
                            'title': result.get('title', ''),
                            'description': result.get('description', ''),
                            'content': result.get('content', '')[:3000],
                            'author': result.get('author', ''),
                            'publisher': result.get('publisher', ''),
                            'domain': result.get('domain', ''),
                            'published_date': result.get('published_date', result.get('publication_date', '')),
                            'featured_image': result.get('featured_image', ''),
                            'headings': result.get('headings', [])[:8],
                            'quality_score': result.get('quality_score', 5.0),
                        })
                
                # Sort scraped content by quality score (descending)
                scraped_content = sorted(scraped_content, key=lambda x: x.get('quality_score', 5.0), reverse=True)
                
                logger.info(f"Successfully scraped {len(scraped_content)} out of {len(urls_to_scrape)} URLs")
                if scraped_content:
                    avg_quality = sum(item.get('quality_score', 5.0) for item in scraped_content) / len(scraped_content)
                    logger.info(f"Average content quality score: {avg_quality:.2f}/10.0")
                
            except Exception as scrape_error:
                logger.error(f"Error during web scraping: {scrape_error}")
        
        task.progress = 60
        task.message = f"Scraped {len(scraped_content)} articles/pages"
        await self.update_progress(job_id, task)
        
        # Add scraped content to enriched data
        enriched_data['scraped_content'] = scraped_content
        enriched_data['enrichment_stats'] = {
            'related_links_found': len(related_links),
            'links_scraped': len(urls_to_scrape) if related_links else 0,
            'successful_scrapes': len(scraped_content),
        }
        
        # Check for GitHub OAuth enrichment
        guest_user_id = plan.options.get('guest_user_id')
        if guest_user_id:
            task.progress = 70
            task.message = "Checking GitHub integration..."
            await self.update_progress(job_id, task)
            
            github_enrichment = await self._enrich_with_github(guest_user_id, task, job_id)
            if github_enrichment:
                enriched_data['github_data'] = github_enrichment
                enriched_data['enrichment_stats']['github_enriched'] = True
        
        task.progress = 90
        task.message = "Enrichment complete"
        await self.update_progress(job_id, task)
        
        # Mark enrichment metadata
        enriched_data['enriched'] = True
        enriched_data['enrichment_timestamp'] = datetime.utcnow().isoformat()
        
        logger.info(f"Profile enrichment complete: {enriched_data.get('enrichment_stats')}")
        
        return enriched_data
    
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
