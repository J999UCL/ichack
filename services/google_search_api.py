"""
Google Custom Search API service for fetching search results
"""

import logging
import requests
from typing import Dict, List, Optional, Any
import re

from config import Config

logger = logging.getLogger(__name__)


class GoogleSearchAPI:
    """Handles Google Custom Search API interactions."""

    BASE_URL = "https://www.googleapis.com/customsearch/v1"

    def __init__(self):
        self.api_key = Config.GOOGLE_SEARCH_API_KEY
        self.search_engine_id = Config.GOOGLE_SEARCH_ENGINE_ID
        self.use_mock_data = (
                not self.api_key or
                self.api_key == 'your-google-search-api-key-here' or
                not self.search_engine_id or
                self.search_engine_id == 'your-search-engine-id-here'
        )

        if self.use_mock_data:
            logger.warning("Google Search API not configured, using mock data")
        else:
            logger.info("Google Search API configured successfully")

    def search_articles(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for articles using Google Custom Search API."""
        try:
            if self.use_mock_data:
                logger.info(f"Using mock data for search: {query}")
                raise ValueError("Search API Failed")

            # Add keywords to improve relevance
            enhanced_query = f"{query} (article OR news OR blog OR post OR guide OR tutorial)"

            params = {
                'key': self.api_key,
                'cx': self.search_engine_id,
                'q': enhanced_query,
                'num': min(limit, 10),  # Google API max is 10 per request
                'safe': 'active',
                'fields': 'items(title,link,snippet,pagemap(cse_image,metatags))'
            }

            logger.info(f"Searching Google for: {enhanced_query}")
            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            items = data.get('items', [])

            # Filter and format results
            articles = []
            for item in items:
                article = self._format_search_result(item)
                if self._is_relevant_article(article):
                    articles.append(article)

            logger.info(f"Found {len(articles)} relevant articles")
            return articles[:limit]

        except requests.RequestException as e:
            logger.error(f"Google Search API error: {e}")
            raise ValueError("Search API Failed")
        except Exception as e:
            logger.error(f"Unexpected error in search: {e}")
            raise ValueError("Search API Failed")

    def get_article_content(self, url: str) -> Optional[str]:
        """Fetch article content from URL (simplified version)."""
        try:
            # For now, we'll use the snippet from search results
            # In a full implementation, you might want to scrape the actual content
            logger.info(f"Getting content for: {url}")

            # Try to fetch the page
            response = requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (compatible; ArticleExplorer/1.0)'
            })
            response.raise_for_status()

            # Simple content extraction (you might want to use BeautifulSoup for better parsing)
            content = response.text

            # Extract text content (very basic)
            # Remove HTML tags
            clean_content = re.sub(r'<[^>]+>', ' ', content)
            # Clean up whitespace
            clean_content = re.sub(r'\s+', ' ', clean_content).strip()

            # Return first 2000 characters
            return clean_content[:2000] if clean_content else None

        except Exception as e:
            logger.error(f"Error fetching content from {url}: {e}")
            return f"Content from {url}. This article discusses various aspects of the topic."

    def _format_search_result(self, item: Dict) -> Dict[str, Any]:
        """Format a Google Search result item."""
        # Extract image from pagemap
        image_url = ""
        pagemap = item.get('pagemap', {})

        # Try to get image from various sources
        if 'cse_image' in pagemap and pagemap['cse_image']:
            image_url = pagemap['cse_image'][0].get('src', '')
        elif 'metatags' in pagemap and pagemap['metatags']:
            metatag = pagemap['metatags'][0]
            image_url = (
                    metatag.get('og:image', '') or
                    metatag.get('twitter:image', '') or
                    metatag.get('image', '')
            )

        return {
            'title': item.get('title', 'Untitled'),
            'url': item.get('link', ''),
            'snippet': item.get('snippet', 'No description available'),
            'image': image_url,
            'source': self._extract_domain(item.get('link', ''))
        }

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc.replace('www.', '')
        except:
            return 'Unknown'

    def _is_relevant_article(self, article: Dict) -> bool:
        """Check if the article is relevant based on keywords."""
        title = article.get('title', '').lower()
        snippet = article.get('snippet', '').lower()
        url = article.get('url', '').lower()

        # Check for relevant keywords
        keywords = Config.SEARCH_KEYWORDS
        text_to_check = f"{title} {snippet} {url}"

        # Must contain at least one keyword
        has_keyword = any(keyword in text_to_check for keyword in keywords)

        # Exclude certain domains/types
        excluded_domains = ['youtube.com', 'facebook.com', 'twitter.com', 'instagram.com']
        is_excluded = any(domain in url for domain in excluded_domains)

        return has_keyword and not is_excluded

    def is_available(self) -> bool:
        """Check if Google Search API is available."""
        return not self.use_mock_data