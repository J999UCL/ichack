"""
Google Gemini service for AI integration
"""

import logging
import time
from typing import List

from google import genai

from config import Config
from utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

class GeminiService:
    """Handles Google Gemini AI interactions."""

    def __init__(self, rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter
        self.model = None
        self.use_mock_data = True

        try:
            if Config.GEMINI_API_KEY and Config.GEMINI_API_KEY != 'your-gemini-api-key-here':
                self.gemini_client = genai.Client(api_key=Config.GEMINI_API_KEY)
                self.use_mock_data = False
                logger.info(f"Gemini client initialized successfully with model: {Config.GEMINI_MODEL}")
            else:
                logger.warning("Gemini API key not configured, using mock data")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")

    def get_related_search_queries(self, article_title: str, article_content: str = "") -> List[str]:
        """Get related search queries for finding more articles."""
        try:
            # Check rate limit
            if not self.rate_limiter.can_make_call():
                wait_time = self.rate_limiter.wait_time()
                logger.warning(f"Rate limited. Waiting {wait_time:.1f} seconds...")
                time.sleep(wait_time + 1)

            if not self.model or self.use_mock_data:
                logger.info("Using mock data instead of Gemini API")
                return self._get_mock_search_queries(article_title)

            prompt = f"""
            Based on this article title: "{article_title}"
            {f"And this content preview: {article_content[:500]}..." if article_content else ""}
            
            
            Summarize the text emphasizing clues of its historical and causal antecedents to aid in discovering prior related articles, papers, or posts.
            Write this analysis explicity then a delimiter then formulate {Config.MAX_ARTICLES_PER_LEVEL} hypotheses of search queries that should yield relevant predecessors
        
            Additional Requirements:
            - Make queries specific enough to find quality articles
            - Avoid duplicate or very similar queries
            
            Return only the search queries, one per line, without numbers or formatting.
            
            Example format:
            Hypothesis1
            Hypothesis2
            Hypothesis3
            """

            response = self.gemini_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[prompt]
            )

            if response.text:
                queries = [
                    line.strip()
                    for line in response.text.strip().split('\n')
                    if line.strip() and len(line.strip()) > 3
                ]

                # Clean up queries
                clean_queries = []
                for query in queries:
                    # Remove common prefixes and formatting
                    cleaned = query.strip()
                    for prefix in ['1. ', '2. ', '3. ', '4. ', '5. ', '• ', '- ', '* ', '→ ', '> ']:
                        if cleaned.startswith(prefix):
                            cleaned = cleaned[len(prefix):].strip()

                    # Remove quotes
                    cleaned = cleaned.strip('"\'')

                    if cleaned and len(cleaned) > 3:
                        clean_queries.append(cleaned)

                logger.info(f"Gemini suggested search queries: {clean_queries[:Config.MAX_ARTICLES_PER_LEVEL]}")
                self.rate_limiter.record_call()
                return clean_queries[:Config.MAX_ARTICLES_PER_LEVEL]
            else:
                logger.warning("Gemini returned empty response")
                raise ValueError("Invalid value provided")

        except Exception as e:
            logger.error(f"Error getting search queries from Gemini: {e}")
            raise ValueError("Invalid value provided")

    def _get_mock_search_queries(self, article_title: str) -> List[str]:
        """Generate mock search queries when API is unavailable."""
        title_lower = article_title.lower()

        # Generate contextual queries based on the article title
        mock_queries = []

        # Add specific queries based on common topics
        if any(word in title_lower for word in ['ai', 'artificial intelligence', 'machine learning']):
            mock_queries = ['deep learning applications', 'neural network architectures', 'AI ethics and safety']
        elif any(word in title_lower for word in ['climate', 'environment', 'sustainability']):
            mock_queries = ['renewable energy solutions', 'carbon footprint reduction', 'sustainable technology']
        elif any(word in title_lower for word in ['technology', 'tech', 'digital']):
            mock_queries = ['emerging technologies', 'digital transformation', 'tech innovation trends']
        elif any(word in title_lower for word in ['health', 'medical', 'healthcare']):
            mock_queries = ['medical technology advances', 'healthcare innovation', 'digital health solutions']
        elif any(word in title_lower for word in ['business', 'startup', 'entrepreneur']):
            mock_queries = ['startup growth strategies', 'business model innovation', 'entrepreneurship trends']
        elif any(word in title_lower for word in ['science', 'research', 'study']):
            mock_queries = ['scientific breakthroughs', 'research methodology', 'scientific innovation']
        else:
            # Generic related queries
            words = article_title.split()
            if len(words) >= 2:
                mock_queries = [
                    f"{words[0]} applications",
                    f"{words[-1]} trends",
                    f"future of {words[0]}"
                ]
            else:
                mock_queries = [
                    f"{article_title} applications",
                    f"{article_title} trends",
                    f"future of {article_title}"
                ]

        return mock_queries[:Config.MAX_ARTICLES_PER_LEVEL]

    def is_available(self) -> bool:
        """Check if Gemini service is available."""
        return self.gemini_client is not None and not self.use_mock_data

    def get_model_info(self) -> dict:
        """Get information about the current model."""
        return {
            'provider': 'Google Gemini',
            'model': Config.GEMINI_MODEL,
            'available': self.is_available(),
            'using_mock_data': self.use_mock_data
        }
