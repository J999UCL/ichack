"""
Main Flask routes for the application
"""

import logging
import json
from urllib.parse import unquote
from flask import Blueprint, render_template, jsonify, request

from services.google_search_api import GoogleSearchAPI

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)

# Initialize Google Search API
google_search = GoogleSearchAPI()

@main_bp.route('/')
def index():
    """Render main page with search functionality."""
    return render_template('index.html')

@main_bp.route('/tree')
def tree_view():
    """Render tree visualization page."""
    # Get article data from query parameter
    data_param = request.args.get('data')

    if not data_param:
        # Fallback for old URL format
        article_title = request.args.get('title', 'Unknown Article')
        article_data = {'title': article_title}
    else:
        try:
            article_data = json.loads(unquote(data_param))
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error parsing article data: {e}")
            article_data = {'title': 'Unknown Article'}

    logger.info(f"🌳 Tree view requested for article: {article_data.get('title')}")
    return render_template('tree.html', article_data=article_data)

@main_bp.route('/debug')
def debug():
    """Debug page for testing Socket.IO connection."""
    return render_template('debug.html')

@main_bp.route('/api/search', methods=['POST'])
def search_articles():
    """API endpoint for searching articles."""
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400

        query = data.get('query', '').strip()
        limit = data.get('limit', 10)

        if not query:
            return jsonify({
                'success': False,
                'error': 'Search query is required'
            }), 400

        if len(query) < 2:
            return jsonify({
                'success': False,
                'error': 'Search query must be at least 2 characters'
            }), 400

        logger.info(f"Search request: '{query}' (limit: {limit})")

        # Search for articles
        results = google_search.search_articles(query, limit)

        logger.info(f"Found {len(results)} results for '{query}'")

        return jsonify({
            'success': True,
            'query': query,
            'results': results,
            'count': len(results)
        })

    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@main_bp.route('/api/health')
def health_check():
    """Health check endpoint."""
    from app import gemini_service

    return jsonify({
        'status': 'healthy',
        'service': 'Article Explorer',
        'ai_provider': 'Google Gemini',
        'ai_available': gemini_service.is_available(),
        'search_available': google_search.is_available(),
        'server_running': True
    })

@main_bp.route('/api/ai-status')
def ai_status():
    """Get current AI service status."""
    from app import gemini_service
    return jsonify(gemini_service.get_model_info())

@main_bp.route('/api/search-status')
def search_status():
    """Get current search service status."""
    return jsonify({
        'provider': 'Google Custom Search',
        'available': google_search.is_available()
    })
