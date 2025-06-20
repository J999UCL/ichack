"""
OpenAI service for ChatGPT integration
"""

import logging
import time
import random
from typing import List, Optional
import openai
from openai import OpenAI

from config import Config
from utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class OpenAIService:
    """Handles OpenAI ChatGPT interactions."""

    def __init__(self, rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter
        self.client: Optional[OpenAI] = None
        self.use_mock_data = True

        try:
            if Config.OPENAI_API_KEY and Config.OPENAI_API_KEY != 'your-openai-api-key-here':
                self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
                self.use_mock_data = False
                logger.info("OpenAI client initialized successfully")
            else:
                logger.warning("OpenAI API key not configured, using mock data")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")

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

            except openai.RateLimitError as e:
                logger.warning(f"OpenAI rate limit error (attempt {attempt + 1}): {e}")
                wait_time = (2 ** attempt) * 10  # Exponential backoff: 10, 20, 40 seconds
                time.sleep(wait_time)

            except Exception as e:
                logger.error(f"Error getting related articles (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    break
                time.sleep(2 ** attempt)  # Exponential backoff

        # If all retries failed, return mock data
        logger.warning(f"All retries failed for {current_title}, using mock data")
        return self._get_mock_related_articles(current_title)

    def _get_related_articles(self, content: str, current_title: str) -> List[str]:
        """Use ChatGPT to find related articles."""
        try:
            if not self.client or self.use_mock_data:
                logger.info("Using mock data instead of OpenAI API")
                return self._get_mock_related_articles(current_title)

            prompt = f"""
            Based on this Wikipedia article about "{current_title}":

            {content[:1000]}...

            Please suggest {Config.MAX_ARTICLES_PER_LEVEL} related Wikipedia article titles that would be interesting to explore next.
            Return only the article titles, one per line, without any additional text or formatting.
            Make sure the titles are actual Wikipedia article names.
            """

            response = self.client.chat.completions.create(
                model=Config.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that suggests related Wikipedia articles. Only return article titles, one per line."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=Config.MAX_TOKENS,
                temperature=Config.TEMPERATURE
            )

            articles = [
                line.strip()
                for line in response.choices[0].message.content.strip().split('\n')
                if line.strip()
            ]

            logger.info(f"ChatGPT suggested articles: {articles}")
            return articles[:Config.MAX_ARTICLES_PER_LEVEL]

        except openai.RateLimitError:
            raise  # Re-raise rate limit errors to be handled by retry logic
        except Exception as e:
            logger.error(f"Error getting related articles: {e}")
            return self._get_mock_related_articles(current_title)

    def _get_mock_related_articles(self, current_title: str) -> List[str]:
        """Get mock related articles when API is unavailable."""
        mock_articles = {
            'Artificial Intelligence': ['Machine Learning', 'Neural Networks'],
            'Machine Learning': ['Deep Learning', 'Data Science'],
            'Neural Networks': ['Artificial Neural Network', 'Convolutional Neural Network'],
            'Climate Change': ['Global Warming', 'Greenhouse Effect'],
            'Global Warming': ['Carbon Dioxide', 'Climate Science'],
            'Space Exploration': ['NASA', 'Mars Exploration'],
            'NASA': ['Space Shuttle', 'International Space Station'],
            'Quantum Computing': ['Quantum Physics', 'Quantum Entanglement'],
            'Quantum Physics': ['Quantum Mechanics', 'Particle Physics'],
            'Renewable Energy': ['Solar Power', 'Wind Energy'],
            'Solar Power': ['Photovoltaic System', 'Solar Panel'],
            'Deep Learning': ['Convolutional Neural Network', 'Recurrent Neural Network'],
            'Data Science': ['Big Data', 'Data Mining'],
            'Blockchain': ['Cryptocurrency', 'Bitcoin'],
            'Virtual Reality': ['Augmented Reality', 'Mixed Reality']
        }

        # Generate related articles based on the title
        if current_title in mock_articles:
            return mock_articles[current_title]
        else:
            # Generate generic related topics
            return [f"Related to {current_title} - Topic A", f"Related to {current_title} - Topic B"]

    def is_available(self) -> bool:
        """Check if OpenAI service is available."""
        return self.client is not None and not self.use_mock_data
