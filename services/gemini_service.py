"""
Google Gemini service for AI integration
"""

import logging
import time
import random
from typing import List, Optional
from google import genai

from config import Config
from utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class GeminiService:
    """Handles Google Gemini AI interactions."""

    def __init__(self, rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter
        self.gemini_client = None
        self.use_mock_data = True

        try:
            if Config.GEMINI_API_KEY and Config.GEMINI_API_KEY != 'your-gemini-api-key-here':
                self.gemini_client = genai.Client(api_key=Config.GEMINI_API_KEY)
                self.use_mock_data = False
            else:
                logger.warning("Gemini API key not configured, using mock data")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")

    def get_related_articles_with_retry(self, content: str, current_title: str, max_retries: int = 3) -> List[str]:
        """Get related articles with retry logic for rate limiting."""

        for attempt in range(max_retries):
            try:
                # Check rate limit
                if not self.rate_limiter.can_make_call():
                    wait_time = self.rate_limiter.wait_time()
                    logger.warning(f"Rate limited. Waiting {wait_time:.1f} seconds...")
                    time.sleep(wait_time + 1)  # Add extra second for safety

                # Try to get related articles
                articles = self._get_related_articles(content, current_title)

                if articles:
                    self.rate_limiter.record_call()
                    return articles

            except Exception as e:
                error_message = str(e).lower()

                # Handle different types of Gemini errors
                if 'quota' in error_message or 'rate' in error_message:
                    logger.warning(f"Gemini rate limit error (attempt {attempt + 1}): {e}")
                    wait_time = (2 ** attempt) * 5  # Exponential backoff: 5, 10, 20 seconds
                    time.sleep(wait_time)
                elif 'safety' in error_message:
                    logger.warning(f"Gemini safety filter triggered for {current_title}: {e}")
                    # Return mock data for safety-filtered content
                    raise ValueError("Invalid value provided")
                else:
                    logger.error(f"Error getting related articles (attempt {attempt + 1}): {e}")
                    if attempt == max_retries - 1:
                        break
                    time.sleep(2 ** attempt)  # Exponential backoff

        # If all retries failed, return mock data
        logger.warning(f"All retries failed for {current_title}, using mock data")
        raise ValueError("Invalid value provided")

    def _get_related_articles(self, content: str, current_title: str) -> List[str]:
        """Use Gemini to find related articles."""
        try:
            if not self.gemini_client or self.use_mock_data:
                logger.info("Using mock data instead of Gemini API")
                raise ValueError("Invalid value provided")

            prompt = f"""
            Based on this Wikipedia article about "{current_title}":

            {content[:1500]}...

            Please suggest {Config.MAX_ARTICLES_PER_LEVEL} related Wikipedia article titles that would be interesting to explore next.

            Requirements:
            - Return only the article titles, one per line
            - No additional text, formatting, or explanations
            - Make sure the titles are actual Wikipedia article names
            - Focus on closely related topics that would create meaningful connections

            Example format:
            Machine Learning
            Neural Networks
            Deep Learning
            """

            response = self.gemini_client.models.generate_content(
                model = "gemini-2.0-flash",
                contents = [prompt]
            )

            if response.text:
                articles = [
                    line.strip()
                    for line in response.text.strip().split('\n')
                    if line.strip() and not line.strip().startswith('-') and not line.strip().startswith('*')
                ]

                # Filter out any remaining formatting or numbers
                clean_articles = []
                for article in articles:
                    # Remove leading numbers or bullets
                    cleaned = article.strip()
                    if cleaned and len(cleaned) > 3:  # Minimum length check
                        # Remove common prefixes
                        for prefix in ['1. ', '2. ', '3. ', '• ', '- ', '* ']:
                            if cleaned.startswith(prefix):
                                cleaned = cleaned[len(prefix):].strip()
                        clean_articles.append(cleaned)

                logger.info(f"Gemini suggested articles: {clean_articles[:Config.MAX_ARTICLES_PER_LEVEL]}")
                return clean_articles[:Config.MAX_ARTICLES_PER_LEVEL]
            else:
                logger.warning("Gemini returned empty response")
                raise ValueError("Invalid value provided")

        except Exception as e:
            logger.error(f"Error getting related articles from Gemini: {e}")
            raise ValueError("Invalid value provided")

    def _get_mock_related_articles(self, current_title: str) -> List[str]:
        """Get mock related articles when API is unavailable."""
        mock_articles = {
            'Artificial Intelligence': ['Machine Learning', 'Neural Networks', 'Deep Learning'],
            'Machine Learning': ['Deep Learning', 'Data Science', 'Pattern Recognition'],
            'Neural Networks': ['Artificial Neural Network', 'Convolutional Neural Network',
                                'Recurrent Neural Network'],
            'Deep Learning': ['Convolutional Neural Network', 'Transformer Architecture', 'Generative AI'],
            'Climate Change': ['Global Warming', 'Greenhouse Effect', 'Carbon Footprint'],
            'Global Warming': ['Carbon Dioxide', 'Climate Science', 'Renewable Energy'],
            'Space Exploration': ['NASA', 'Mars Exploration', 'International Space Station'],
            'NASA': ['Space Shuttle', 'Apollo Program', 'James Webb Space Telescope'],
            'Quantum Computing': ['Quantum Physics', 'Quantum Entanglement', 'Quantum Algorithms'],
            'Quantum Physics': ['Quantum Mechanics', 'Particle Physics', 'Quantum Field Theory'],
            'Renewable Energy': ['Solar Power', 'Wind Energy', 'Hydroelectric Power'],
            'Solar Power': ['Photovoltaic System', 'Solar Panel', 'Solar Energy'],
            'Data Science': ['Big Data', 'Data Mining', 'Statistical Analysis'],
            'Blockchain': ['Cryptocurrency', 'Bitcoin', 'Distributed Ledger'],
            'Virtual Reality': ['Augmented Reality', 'Mixed Reality', 'Computer Graphics'],
            'Cybersecurity': ['Computer Security', 'Cryptography', 'Network Security'],
            'Biotechnology': ['Genetic Engineering', 'CRISPR', 'Synthetic Biology']
        }

        # Generate related articles based on the title
        if current_title in mock_articles:
            return mock_articles[current_title]
        else:
            # Generate generic related topics
            return [
                f"Advanced {current_title}",
                f"{current_title} Applications",
                f"{current_title} Research"
            ]

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
