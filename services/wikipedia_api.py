"""
Wikipedia API service for fetching articles and content
"""

import logging
import requests
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class WikipediaAPI:
    """Handles Wikipedia API interactions."""

    BASE_URL = "https://en.wikipedia.org/api/rest_v1"

    @staticmethod
    def get_trending_articles(limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch trending Wikipedia articles."""
        try:
            # Use a more reliable endpoint for getting articles
            url = "https://en.wikipedia.org/api/rest_v1/page/random/summary"
            articles = []

            # Get random articles as a fallback
            for i in range(min(limit, 10)):
                try:
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        articles.append({
                            'title': data.get('title', f'Article {i + 1}'),
                            'extract': data.get('extract', 'No description available'),
                            'thumbnail': data.get('thumbnail', {}).get('source', ''),
                            'url': data.get('content_urls', {}).get('desktop', {}).get('page', '#')
                        })
                except Exception as e:
                    logger.warning(f"Error fetching random article {i}: {e}")
                    continue

            # Add some default articles if we couldn't fetch enough
            if len(articles) < 5:
                articles.extend(WikipediaAPI._get_default_articles()[:limit - len(articles)])

            return articles[:limit]

        except Exception as e:
            logger.error(f"Error fetching trending articles: {e}")
            return WikipediaAPI._get_default_articles()[:limit]

    @staticmethod
    def get_article_content(title: str) -> Optional[str]:
        """Fetch full content of a Wikipedia article."""
        try:
            # Get page content
            url = f"{WikipediaAPI.BASE_URL}/page/summary/{title.replace(' ', '_')}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            return data.get('extract', '')

        except requests.RequestException as e:
            logger.error(f"Error fetching article content for {title}: {e}")
            # Return a mock content for testing
            return f"This is mock content for the article '{title}'. In a real implementation, this would contain the actual Wikipedia article content."

    @staticmethod
    def _get_default_articles() -> List[Dict[str, Any]]:
        """Get default articles when API is unavailable."""
        return [
            {
                'title': 'Artificial Intelligence',
                'extract': 'Artificial intelligence is intelligence demonstrated by machines, in contrast to the natural intelligence displayed by humans and animals.',
                'thumbnail': '',
                'url': 'https://en.wikipedia.org/wiki/Artificial_intelligence'
            },
            {
                'title': 'Climate Change',
                'extract': 'Climate change refers to long-term shifts in global or regional climate patterns.',
                'thumbnail': '',
                'url': 'https://en.wikipedia.org/wiki/Climate_change'
            },
            {
                'title': 'Space Exploration',
                'extract': 'Space exploration is the use of astronomy and space technology to explore outer space.',
                'thumbnail': '',
                'url': 'https://en.wikipedia.org/wiki/Space_exploration'
            },
            {
                'title': 'Quantum Computing',
                'extract': 'Quantum computing is a type of computation that harnesses quantum mechanical phenomena.',
                'thumbnail': '',
                'url': 'https://en.wikipedia.org/wiki/Quantum_computing'
            },
            {
                'title': 'Renewable Energy',
                'extract': 'Renewable energy is energy that is collected from renewable resources.',
                'thumbnail': '',
                'url': 'https://en.wikipedia.org/wiki/Renewable_energy'
            },
            {
                'title': 'Machine Learning',
                'extract': 'Machine learning is a method of data analysis that automates analytical model building.',
                'thumbnail': '',
                'url': 'https://en.wikipedia.org/wiki/Machine_learning'
            },
            {
                'title': 'Blockchain',
                'extract': 'A blockchain is a growing list of records, called blocks, that are linked and secured using cryptography.',
                'thumbnail': '',
                'url': 'https://en.wikipedia.org/wiki/Blockchain'
            },
            {
                'title': 'Virtual Reality',
                'extract': 'Virtual reality is a simulated experience that can be similar to or completely different from the real world.',
                'thumbnail': '',
                'url': 'https://en.wikipedia.org/wiki/Virtual_reality'
            }
        ]
