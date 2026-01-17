"""Professional web scraping service using BeautifulSoup for profile enrichment.

This service captures information from article mentions, portfolio pages, and other
web content to enrich profile data with rich digital footprint.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from urllib.parse import urlparse, urljoin
import re

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class WebScraperService:
    """Professional web scraping service for enriching profile data."""
    
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
    
    # Domains that should be skipped (block scraping or require authentication)
    BLOCKED_DOMAINS: Set[str] = {
        "linkedin.com", "www.linkedin.com",
        "facebook.com", "www.facebook.com",
        "instagram.com", "www.instagram.com",
        "twitter.com", "www.twitter.com", "x.com", "www.x.com",
        "tiktok.com", "www.tiktok.com",
        "api.github.com",  # GitHub API requires auth, but github.com pages are OK
    }
    
    # Rate limiting configuration
    REQUEST_DELAY = 1.0  # seconds between requests
    MAX_CONCURRENT_REQUESTS = 5
    MAX_RETRIES = 2
    RETRY_DELAY = 2.0
    
    def __init__(self):
        """Initialize the web scraper service."""
        self._http_client: Optional[httpx.AsyncClient] = None
        self._lock = asyncio.Lock()
        self._last_request_time: float = 0.0
    
    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create an async HTTP client with thread-safe initialization."""
        if self._http_client is None:
            async with self._lock:
                # Double-check after acquiring lock
                if self._http_client is None:
                    self._http_client = httpx.AsyncClient(
                        headers=self.DEFAULT_HEADERS,
                        follow_redirects=True,
                        timeout=httpx.Timeout(30.0, connect=10.0)
                    )
        return self._http_client
    
    async def _rate_limit(self):
        """Implement rate limiting between requests."""
        async with self._lock:
            current_time = asyncio.get_event_loop().time()
            time_since_last_request = current_time - self._last_request_time
            
            if time_since_last_request < self.REQUEST_DELAY:
                await asyncio.sleep(self.REQUEST_DELAY - time_since_last_request)
            
            self._last_request_time = asyncio.get_event_loop().time()
    
    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format and check if it's scrapable."""
        if not url or not isinstance(url, str):
            return False
        
        try:
            parsed = urlparse(url)
            
            # Must have valid scheme
            if parsed.scheme not in ('http', 'https'):
                return False
            
            # Must have netloc (domain)
            if not parsed.netloc:
                return False
            
            # Check if domain is blocked
            domain = parsed.netloc.lower()
            for blocked in self.BLOCKED_DOMAINS:
                if domain == blocked or domain.endswith(f".{blocked}"):
                    logger.info(f"Skipping blocked domain: {domain}")
                    return False
            
            return True
            
        except Exception:
            return False
    
    async def scrape_url(self, url: str, retry_count: int = 0) -> Dict[str, Any]:
        """Scrape a single URL and extract relevant information.
        
        Args:
            url: URL to scrape
            retry_count: Current retry attempt (internal use)
            
        Returns:
            Dictionary with scraped data including publisher info, content, date, images
        """
        # Validate URL first
        if not self._is_valid_url(url):
            logger.warning(f"Invalid or blocked URL: {url}")
            return {
                "url": url,
                "success": False,
                "error": "invalid_or_blocked_url",
                "scraped_at": datetime.utcnow().isoformat()
            }
        
        try:
            # Rate limiting
            await self._rate_limit()
            
            client = await self._get_http_client()
            
            logger.info(f"Scraping URL: {url}")
            response = await client.get(url)
            
            # Handle non-success status codes
            if response.status_code == 429:  # Too Many Requests
                if retry_count < self.MAX_RETRIES:
                    logger.warning(f"Rate limited on {url}, retrying after delay...")
                    await asyncio.sleep(self.RETRY_DELAY * (retry_count + 1))
                    return await self.scrape_url(url, retry_count + 1)
                    
            if response.status_code >= 400:
                logger.warning(f"Failed to fetch {url}: HTTP {response.status_code}")
                return {
                    "url": url,
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "scraped_at": datetime.utcnow().isoformat()
                }
            
            # Check content type - only process HTML
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' not in content_type and 'application/xhtml' not in content_type:
                logger.info(f"Skipping non-HTML content: {content_type} for {url}")
                return {
                    "url": url,
                    "success": False,
                    "error": f"non_html_content: {content_type}",
                    "scraped_at": datetime.utcnow().isoformat()
                }
            
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract data
            result = {
                "url": url,
                "success": True,
                "scraped_at": datetime.utcnow().isoformat(),
                **self._extract_metadata(soup, url),
                **self._extract_content(soup),
                **self._extract_publisher_info(soup, url),
                **self._extract_images(soup, url),
                **self._extract_date(soup),
            }
            
            return result
            
        except httpx.TimeoutException:
            logger.error(f"Timeout while scraping {url}")
            if retry_count < self.MAX_RETRIES:
                logger.info(f"Retrying {url} after timeout...")
                await asyncio.sleep(self.RETRY_DELAY)
                return await self.scrape_url(url, retry_count + 1)
            return {
                "url": url,
                "success": False,
                "error": "timeout",
                "scraped_at": datetime.utcnow().isoformat()
            }
        except httpx.ConnectError as e:
            logger.error(f"Connection error for {url}: {e}")
            return {
                "url": url,
                "success": False,
                "error": f"connection_error: {str(e)}",
                "scraped_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return {
                "url": url,
                "success": False,
                "error": str(e),
                "scraped_at": datetime.utcnow().isoformat()
            }
    
    def _extract_metadata(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract metadata from page (title, description, keywords)."""
        metadata = {}
        
        # Page title
        title_tag = soup.find('title')
        if title_tag:
            metadata['title'] = title_tag.get_text(strip=True)
        
        # Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'}) or \
                   soup.find('meta', attrs={'property': 'og:description'})
        if meta_desc:
            metadata['description'] = meta_desc.get('content', '').strip()
        
        # Meta keywords
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords:
            keywords = meta_keywords.get('content', '').strip()
            metadata['keywords'] = [k.strip() for k in keywords.split(',') if k.strip()]
        
        # Open Graph title
        og_title = soup.find('meta', attrs={'property': 'og:title'})
        if og_title:
            metadata['og_title'] = og_title.get('content', '').strip()
        
        # Open Graph type
        og_type = soup.find('meta', attrs={'property': 'og:type'})
        if og_type:
            metadata['og_type'] = og_type.get('content', '').strip()
        
        # Twitter card
        twitter_card = soup.find('meta', attrs={'name': 'twitter:card'})
        if twitter_card:
            metadata['twitter_card'] = twitter_card.get('content', '').strip()
        
        return metadata
    
    def _extract_content(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract main content from the page."""
        content_data = {}
        
        # Try to find main content area
        main_content = (
            soup.find('article') or
            soup.find('main') or
            soup.find('div', class_=re.compile(r'(content|article|post|entry)', re.I)) or
            soup.find('div', id=re.compile(r'(content|article|post|entry)', re.I))
        )
        
        if main_content:
            # Extract text content
            text_content = main_content.get_text(separator=' ', strip=True)
            # Limit to first 8000 characters for more comprehensive content
            content_data['content'] = text_content[:8000]
            content_data['content_length'] = len(text_content)
            
            # Calculate content quality score
            content_data['quality_score'] = self._calculate_content_quality(text_content, soup)
            
            # Extract headings
            headings = []
            for heading_tag in main_content.find_all(['h1', 'h2', 'h3']):
                heading_text = heading_tag.get_text(strip=True)
                if heading_text:
                    headings.append({
                        'level': heading_tag.name,
                        'text': heading_text
                    })
            content_data['headings'] = headings
            
            # Extract publication date if visible
            pub_date = self._extract_publication_date(soup)
            if pub_date:
                content_data['publication_date'] = pub_date
            
            # Extract author information
            author = self._extract_author(soup)
            if author:
                content_data['author'] = author
                
            # Extract links within content
            links = []
            for link_tag in main_content.find_all('a', href=True):
                link_text = link_tag.get_text(strip=True)
                link_href = link_tag.get('href')
                if link_text and link_href:
                    links.append({
                        'text': link_text,
                        'url': link_href
                    })
            content_data['internal_links'] = links[:25]  # Increased link limit
        else:
            # Fallback to body text
            body = soup.find('body')
            if body:
                text_content = body.get_text(separator=' ', strip=True)
                content_data['content'] = text_content[:8000]
                content_data['content_length'] = len(text_content)
                content_data['quality_score'] = self._calculate_content_quality(text_content, soup)
        
        return content_data
    
    def _calculate_content_quality(self, text_content: str, soup: BeautifulSoup) -> float:
        """Calculate content quality score based on multiple factors (0.0-10.0)."""
        score = 5.0  # Base score
        
        # Content length scoring (optimal: 1000-5000 chars)
        length = len(text_content)
        if 1000 <= length <= 5000:
            score += 1.5
        elif 500 <= length < 1000:
            score += 1.0
        elif length < 200:
            score -= 2.0
        elif length > 8000:
            score -= 0.5
        
        # Professional keywords scoring
        professional_keywords = [
            'interview', 'article', 'published', 'featured', 'speaking',
            'conference', 'presentation', 'award', 'recognition', 'project',
            'developer', 'engineer', 'manager', 'director', 'ceo', 'founder',
            'startup', 'company', 'technology', 'software', 'innovation'
        ]
        keyword_count = sum(1 for word in professional_keywords if word.lower() in text_content.lower())
        score += min(keyword_count * 0.3, 2.0)  # Max +2.0
        
        # Structure quality (headings, paragraphs)
        headings = soup.find_all(['h1', 'h2', 'h3'])
        if len(headings) >= 2:
            score += 1.0
        
        # Date presence (recent content preferred)
        if self._extract_publication_date(soup):
            score += 0.5
        
        # Author information present
        if self._extract_author(soup):
            score += 0.5
        
        # Avoid low-quality indicators
        low_quality_indicators = ['lorem ipsum', 'coming soon', 'under construction', 'page not found']
        if any(indicator in text_content.lower() for indicator in low_quality_indicators):
            score -= 3.0
        
        return max(0.0, min(10.0, score))  # Clamp between 0.0-10.0
    
    def _extract_publication_date(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract publication date from various meta tags."""
        date_selectors = [
            ('meta', {'property': 'article:published_time'}),
            ('meta', {'name': 'date'}),
            ('meta', {'name': 'publish-date'}),
            ('meta', {'property': 'og:publish_date'}),
            ('time', {'datetime': True}),
        ]
        
        for tag_name, attrs in date_selectors:
            element = soup.find(tag_name, attrs)
            if element:
                date_str = element.get('content') or element.get('datetime') or element.get_text()
                if date_str:
                    return date_str.strip()
        return None
    
    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract author information from various sources."""
        author_selectors = [
            ('meta', {'name': 'author'}),
            ('meta', {'property': 'article:author'}),
            ('meta', {'name': 'twitter:creator'}),
            ('span', {'class': re.compile(r'author', re.I)}),
            ('a', {'rel': 'author'}),
            ('div', {'class': re.compile(r'author', re.I)}),
        ]
        
        for tag_name, attrs in author_selectors:
            element = soup.find(tag_name, attrs)
            if element:
                author = element.get('content') or element.get_text()
                if author:
                    return author.strip()
        return None
    
    def _extract_publisher_info(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract publisher/author information."""
        publisher_data = {}
        
        # Domain name
        parsed_url = urlparse(url)
        publisher_data['domain'] = parsed_url.netloc
        
        # Author
        author_meta = (
            soup.find('meta', attrs={'name': 'author'}) or
            soup.find('meta', attrs={'property': 'article:author'}) or
            soup.find('meta', attrs={'name': 'twitter:creator'})
        )
        if author_meta:
            publisher_data['author'] = author_meta.get('content', '').strip()
        
        # Also check for author in structured data
        author_tag = (
            soup.find('span', class_=re.compile(r'author', re.I)) or
            soup.find('a', rel='author') or
            soup.find('div', class_=re.compile(r'author', re.I))
        )
        if author_tag and not publisher_data.get('author'):
            publisher_data['author'] = author_tag.get_text(strip=True)
        
        # Publisher name
        publisher_meta = soup.find('meta', attrs={'property': 'og:site_name'})
        if publisher_meta:
            publisher_data['publisher'] = publisher_meta.get('content', '').strip()
        
        # Publication/Section
        section_meta = soup.find('meta', attrs={'property': 'article:section'})
        if section_meta:
            publisher_data['section'] = section_meta.get('content', '').strip()
        
        return publisher_data
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> Dict[str, Any]:
        """Extract images from the page."""
        image_data = {}
        images = []
        
        # Open Graph image
        og_image = soup.find('meta', attrs={'property': 'og:image'})
        if og_image:
            image_url = og_image.get('content', '').strip()
            if image_url:
                image_data['featured_image'] = self._normalize_url(image_url, base_url)
        
        # Twitter image
        if not image_data.get('featured_image'):
            twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
            if twitter_image:
                image_url = twitter_image.get('content', '').strip()
                if image_url:
                    image_data['featured_image'] = self._normalize_url(image_url, base_url)
        
        # Find all images in content
        for img_tag in soup.find_all('img')[:10]:  # Limit to 10 images
            img_src = img_tag.get('src')
            if img_src:
                images.append({
                    'url': self._normalize_url(img_src, base_url),
                    'alt': img_tag.get('alt', '').strip(),
                    'width': img_tag.get('width'),
                    'height': img_tag.get('height')
                })
        
        if images:
            image_data['images'] = images
        
        return image_data
    
    def _extract_date(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract publication date from the page."""
        date_data = {}
        
        # Try Open Graph published_time
        og_published = soup.find('meta', attrs={'property': 'article:published_time'})
        if og_published:
            date_str = og_published.get('content', '').strip()
            if date_str:
                date_data['published_date'] = date_str
                return date_data
        
        # Try meta tag for datePublished
        date_meta = soup.find('meta', attrs={'itemprop': 'datePublished'})
        if date_meta:
            date_str = date_meta.get('content', '').strip()
            if date_str:
                date_data['published_date'] = date_str
                return date_data
        
        # Try time tag with datetime attribute
        time_tag = soup.find('time', datetime=True)
        if time_tag:
            date_data['published_date'] = time_tag.get('datetime', '').strip()
            return date_data
        
        # Try to find date in text using regex
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2})',  # ISO format
            r'(\d{1,2}/\d{1,2}/\d{4})',  # MM/DD/YYYY
            r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4})',  # Month DD, YYYY
        ]
        
        text_content = soup.get_text()
        for pattern in date_patterns:
            match = re.search(pattern, text_content)
            if match:
                date_data['published_date_text'] = match.group(1)
                break
        
        return date_data
    
    def _normalize_url(self, url: str, base_url: str) -> str:
        """Normalize relative URLs to absolute URLs."""
        if url.startswith('http://') or url.startswith('https://'):
            return url
        return urljoin(base_url, url)
    
    async def scrape_multiple_urls(
        self, 
        urls: List[str],
        max_concurrent: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Scrape multiple URLs with concurrency control.
        
        Args:
            urls: List of URLs to scrape
            max_concurrent: Maximum concurrent requests (default: MAX_CONCURRENT_REQUESTS)
            
        Returns:
            List of scraped data dictionaries
        """
        if not urls:
            return []
        
        # Filter and deduplicate URLs
        valid_urls = []
        seen_urls = set()
        for url in urls:
            normalized_url = url.strip().rstrip('/')
            if normalized_url and normalized_url not in seen_urls:
                if self._is_valid_url(normalized_url):
                    valid_urls.append(normalized_url)
                    seen_urls.add(normalized_url)
                else:
                    logger.info(f"Filtered out invalid/blocked URL: {url}")
        
        if not valid_urls:
            logger.warning("No valid URLs to scrape after filtering")
            return []
        
        logger.info(f"Scraping {len(valid_urls)} valid URLs (filtered from {len(urls)} original)")
        
        if max_concurrent is None:
            max_concurrent = self.MAX_CONCURRENT_REQUESTS
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def scrape_with_semaphore(url: str) -> Dict[str, Any]:
            async with semaphore:
                return await self.scrape_url(url)
        
        tasks = [scrape_with_semaphore(url) for url in valid_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error scraping {valid_urls[i]}: {result}")
                processed_results.append({
                    "url": valid_urls[i],
                    "success": False,
                    "error": str(result),
                    "scraped_at": datetime.utcnow().isoformat()
                })
            else:
                processed_results.append(result)
        
        successful = sum(1 for r in processed_results if r.get('success'))
        logger.info(f"Scraping complete: {successful}/{len(valid_urls)} successful")
        
        return processed_results
    
    async def close(self):
        """Close the HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


# Global instance
web_scraper = WebScraperService()
