"""
gemini_service.py – minimal wrapper around the Google Gemini client.
"""

import logging
import re
import time
from typing import List, Optional

from google import genai

from config import Config
from utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self, rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter
        self.model = None
        self.use_mock_data = True

        try:
            if Config.GEMINI_API_KEY and Config.GEMINI_API_KEY != 'your-gemini-api-key-here':
                self.model = genai.Client(api_key=Config.GEMINI_API_KEY)
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
                raise ValueError("Gemini API Failed")

            prompt = f"""
            Based on this article title: "{article_title}"
            {f"And this content preview: {article_content[:500]}..." if article_content else ""}
            
            
            Summarize the text emphasizing clues of its historical and causal antecedents to aid in discovering prior related articles, papers, or posts.
            Write this analysis explicity then a delimiter then formulate {Config.MAX_ARTICLES_PER_LEVEL} hypotheses of search queries that should yield relevant predecessors
        
            Additional Requirements:
            - Make queries specific enough to find quality articles
            - Avoid duplicate or very similar queries
            - Your hypotheses should be detailed, more so than the examples given below 
            - You may use your memory to directly search articles/papers in your hypothesis
            - keep in mind your hypothesis will be searched on google 
            
            Return only the search queries, one per line, without numbers or formatting.
            
            Example format for a given text such as an article about "Why Jeff Bezos's Blue Origin Is So Reviled":
            
            **Analysis**
            [Whatever analysis you make]
            **
            Blue Origin NASA lawsuit contract dispute
            Criticism of private spaceflight economic inequality
            Jeff Bezos wealth inequality public perception
            """

            response = self.model.models.generate_content(
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
                clean_queries = queries[-Config.MAX_ARTICLES_PER_LEVEL:]

                special_chars = r'["~*+\-]'
                clean_queries = [re.sub(special_chars, '', s) for s in clean_queries]

                logger.info(f"Gemini suggested search queries: {clean_queries[:Config.MAX_ARTICLES_PER_LEVEL]}")
                self.rate_limiter.record_call()
                return clean_queries[:Config.MAX_ARTICLES_PER_LEVEL]
            else:
                logger.warning("Gemini returned empty response")
                raise RuntimeError("Gemini returned empty response")

        except Exception as e:
            logger.error(f"Error getting search queries from Gemini: {e}")
            raise RuntimeError("Error getting search queries from Gemini")

    def summarize_article(self, article_content: str) -> str:
        try:
            if not self.model or self.use_mock_data:
                raise ValueError("Gemini API not available")

            prompt = f"Summarize the following article content in a concise paragraph:\n\n{article_content[:2000]}"
            response = self.model.models.generate_content(
                model="gemini-2.0-flash",
                contents=[prompt]
            )

            summary = response.text.strip() if response.text else ""
            if not summary:
                logger.warning("Gemini returned empty summary")
                raise RuntimeError("Gemini returned empty summary")

            self.rate_limiter.record_call()
            return summary

        except Exception as e:
            logger.error(f"Error summarizing article with Gemini: {e}")
            raise RuntimeError("Error summarizing article with Gemini")

    def final_analysis(self, root_title: str, leaf_block, full_block) -> str:

        prompt =  f"""
    You are writing the closing analysis for a research-tree exploration of
    '{root_title}'.

    ------------------------------------------------------------
    PART A – Origins (foundational sources)
    Summarise the **core insights** from the earliest / leaf articles only.

    Leaf abstracts:
    {leaf_block}
    ------------------------------------------------------------
    PART B – Evolution (how the narrative shifted)
    Trace the progression through intermediate articles, noting any changes
    in framing, causality claims, or biases.

    Full-tree abstracts (root → intermediates → leaves):
    {full_block}
    ------------------------------------------------------------
    Write PART A first (concise), then PART B (≈2× PART A length).
    """.strip()

        try:
            if not self.model or self.use_mock_data:
                raise ValueError("Gemini API not available")

            response = self.model.models.generate_content(
                model="gemini-2.0-flash",
                contents=[prompt]
            )

            summary = response.text.strip() if response.text else ""
            if not summary:
                logger.warning("Gemini returned empty analysis")
                raise RuntimeError("Gemini returned empty analysis")

            self.rate_limiter.record_call()
            return summary

        except Exception as e:
            logger.error(f"Error analysing tree with Gemini: {e}")
            raise RuntimeError("Error analysing tree with Gemini")




    def is_available(self) -> bool:
        return self.model is not None and not self.use_mock_data

    def get_model_info(self) -> dict:
        return {
            'provider': 'Google Gemini',
            'model': Config.GEMINI_MODEL,
            'available': self.is_available(),
            'using_mock_data': self.use_mock_data
        }
