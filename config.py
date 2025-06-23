"""
Configuration settings for Wikipedia Explorer
"""

import os

from flask import Flask

app = Flask(__name__)

class Config:
    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

    # Google Custom Search API settings
    GOOGLE_SEARCH_API_KEY = os.environ["GOOGLE_SEARCH_API_KEY"]
    GOOGLE_SEARCH_ENGINE_ID = os.environ['GOOGLE_SEARCH_ENGINE_ID']

    SEARCH_RESULTS_LIMIT = int(os.getenv('SEARCH_RESULTS_LIMIT', '10'))
    SEARCH_KEYWORDS = ['article', 'news', 'blog', 'post', 'guide', 'tutorial', 'review', 'analysis']

    # Google Gemini settings
    GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
    MAX_TOKENS = int(os.getenv('MAX_TOKENS', '100'))
    TEMPERATURE = float(os.getenv('TEMPERATURE', '0.7'))

    # Rate limiting settings (Gemini has different limits)
    MAX_CALLS_PER_MINUTE = int(os.getenv('MAX_CALLS_PER_MINUTE', '15'))  # Gemini allows more requests

    # Search settings
    MAX_SEARCH_DEPTH = int(os.getenv('MAX_SEARCH_DEPTH', '2'))
    MAX_ARTICLES_PER_LEVEL = int(os.getenv('MAX_ARTICLES_PER_LEVEL', '3'))  # Can handle more with Gemini

    # Timing settings (in seconds) - can be faster with Gemini
    MIN_DELAY_BETWEEN_REQUESTS = float(os.getenv('MIN_DELAY_BETWEEN_REQUESTS', '1'))
    MAX_DELAY_BETWEEN_REQUESTS = float(os.getenv('MAX_DELAY_BETWEEN_REQUESTS', '2'))

    # Fallback settings
    USE_MOCK_DATA_ON_ERROR = os.getenv('USE_MOCK_DATA_ON_ERROR', 'True').lower() == 'true'

    # Server settings
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', '5000'))

    # Logging settings
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
