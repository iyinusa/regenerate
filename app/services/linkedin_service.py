"""LinkedIn Scraping Service for profile data extraction.

This service handles LinkedIn profile data extraction using both:
1. Web scraping for unauthenticated access (with limitations)
2. LinkedIn OAuth API for authenticated access
"""

import asyncio
import logging
import re
from typing import Dict, Any, Optional
from datetime import datetime
import httpx
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class LinkedInScrapingService:
    """Service for scraping LinkedIn profile data."""
    
    # Common headers to mimic browser requests
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }
    
    # LinkedIn API endpoints
    LINKEDIN_API_BASE = "https://api.linkedin.com/v2"
    
    def __init__(self):
        """Initialize the LinkedIn scraping service."""
        self.http_client = None
    
    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create an async HTTP client."""
        if self.http_client is None:
            self.http_client = httpx.AsyncClient(
                headers=self.DEFAULT_HEADERS,
                follow_redirects=True,
                timeout=30.0
            )
        return self.http_client
    
    @staticmethod
    def is_linkedin_url(url: str) -> bool:
        """Check if a URL is a LinkedIn profile URL.
        
        Args:
            url: URL to check
            
        Returns:
            True if it's a LinkedIn URL
        """
        parsed = urlparse(url.lower())
        return "linkedin.com" in parsed.netloc
    
    @staticmethod
    def extract_linkedin_username(url: str) -> Optional[str]:
        """Extract LinkedIn username from URL.
        
        Args:
            url: LinkedIn profile URL
            
        Returns:
            Username or None
        """
        patterns = [
            r'linkedin\.com/in/([^/?]+)',
            r'linkedin\.com/pub/([^/?]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url.lower())
            if match:
                return match.group(1)
        return None
    
    async def scrape_public_profile(self, url: str) -> Dict[str, Any]:
        """Scrape public LinkedIn profile data.
        
        This method attempts to scrape publicly visible data from LinkedIn.
        Due to LinkedIn's anti-scraping measures, this may have limited success.
        
        Args:
            url: LinkedIn profile URL
            
        Returns:
            Dictionary with scraped data or error information
        """
        try:
            client = await self._get_http_client()
            
            # Attempt to fetch the profile page
            response = await client.get(url)
            
            if response.status_code == 999:
                # LinkedIn is blocking the request
                logger.warning("LinkedIn is blocking automated access")
                return {
                    "success": False,
                    "error": "linkedin_blocked",
                    "message": "LinkedIn is blocking automated access. Please use LinkedIn OAuth authentication.",
                    "raw_html": None
                }
            
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": "http_error",
                    "status_code": response.status_code,
                    "message": f"Failed to fetch profile: HTTP {response.status_code}"
                }
            
            html_content = response.text
            
            # Check if we got a login page instead
            if "authwall" in html_content.lower() or "login" in response.url.path.lower():
                logger.info("LinkedIn requires authentication for this profile")
                return {
                    "success": False,
                    "error": "auth_required",
                    "message": "LinkedIn requires authentication to view this profile. Please use LinkedIn OAuth.",
                    "raw_html": html_content[:5000]  # Store partial HTML for potential parsing
                }
            
            # Return the raw HTML for Gemini to process
            return {
                "success": True,
                "raw_html": html_content,
                "url": str(response.url),
                "scraped_at": datetime.utcnow().isoformat()
            }
            
        except httpx.TimeoutException:
            logger.error(f"Timeout while scraping LinkedIn profile: {url}")
            return {
                "success": False,
                "error": "timeout",
                "message": "Request timed out while fetching LinkedIn profile"
            }
        except Exception as e:
            logger.error(f"Error scraping LinkedIn profile: {e}")
            return {
                "success": False,
                "error": "exception",
                "message": str(e)
            }
    
    async def fetch_authenticated_profile(
        self, 
        access_token: str,
        include_positions: bool = True,
        include_education: bool = True,
        include_skills: bool = True
    ) -> Dict[str, Any]:
        """Fetch LinkedIn profile data using OAuth access token.
        
        Args:
            access_token: LinkedIn OAuth access token
            include_positions: Include work experience
            include_education: Include education history
            include_skills: Include skills
            
        Returns:
            Dictionary with profile data
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": "202401"
        }
        
        try:
            client = await self._get_http_client()
            profile_data = {}
            
            # Fetch basic profile
            me_response = await client.get(
                f"{self.LINKEDIN_API_BASE}/userinfo",
                headers=headers
            )
            
            if me_response.status_code == 401:
                return {
                    "success": False,
                    "error": "auth_expired",
                    "message": "LinkedIn access token has expired. Please re-authenticate."
                }
            
            if me_response.status_code != 200:
                return {
                    "success": False,
                    "error": "api_error",
                    "status_code": me_response.status_code,
                    "message": f"LinkedIn API error: {me_response.text}"
                }
            
            profile_data["basic_profile"] = me_response.json()
            
            # Fetch email (if scope allows)
            try:
                email_response = await client.get(
                    f"{self.LINKEDIN_API_BASE}/emailAddress?q=members&projection=(elements*(handle~))",
                    headers=headers
                )
                if email_response.status_code == 200:
                    email_data = email_response.json()
                    elements = email_data.get("elements", [])
                    if elements:
                        profile_data["email"] = elements[0].get("handle~", {}).get("emailAddress")
            except Exception as e:
                logger.warning(f"Failed to fetch email: {e}")
            
            # Fetch profile picture
            try:
                picture_response = await client.get(
                    f"{self.LINKEDIN_API_BASE}/userinfo?projection=(profilePicture(displayImage~:playableStreams))",
                    headers=headers
                )
                if picture_response.status_code == 200:
                    profile_data["profile_picture"] = picture_response.json()
            except Exception as e:
                logger.warning(f"Failed to fetch profile picture: {e}")
            
            return {
                "success": True,
                "data": profile_data,
                "fetched_at": datetime.utcnow().isoformat(),
                "authenticated": True,
                "linkedin_url": profile_data.get("basic_profile", {}).get("vanityName", None)  # Try to get profile URL
            }
            
        except Exception as e:
            logger.error(f"Error fetching authenticated LinkedIn profile: {e}")
            return {
                "success": False,
                "error": "exception",
                "message": str(e)
            }
    
    async def close(self):
        """Close the HTTP client."""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None


# Global instance
linkedin_service = LinkedInScrapingService()
