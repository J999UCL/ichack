"""
Main Flask routes for the application
"""

import logging
from flask import Blueprint, render_template, jsonify, request

from services.wikipedia_api import WikipediaAPI

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Render main page with trending articles."""
    return render_template('index.html')

@main_bp.route('/tree/<article_title>')
def tree_view(article_title):
    """Render tree visualization page."""
    logger.info(f"🌳 Tree view requested for article: {article_title}")
    return render_template('tree.html', article_title=article_title)

@main_bp.route('/debug')
def debug():
    """Debug page for testing Socket.IO connection."""
    return render_template('debug.html')

@main_bp.route('/api/trending')
def get_trending():
    """API endpoint for trending articles."""
    try:
        articles = WikipediaAPI.get_trending_articles()
        return jsonify({
            'success': True,
            'articles': articles
        })
    except Exception as e:
        logger.error(f"Error in trending endpoint: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@main_bp.route('/api/rate-limit-status')
def rate_limit_status():
    """Get current rate limit status."""
    from app import rate_limiter  # Import here to avoid circular imports

    return jsonify(rate_limiter.get_status())

@main_bp.route('/api/ai-status')
def ai_status():
    """Get current AI service status."""
    from app import gemini_service  # Import here to avoid circular imports

    return jsonify(gemini_service.get_model_info())

@main_bp.route('/api/health')
def health_check():
    """Health check endpoint."""
    from app import gemini_service

    return jsonify({
        'status': 'healthy',
        'service': 'Wikipedia Explorer',
        'ai_provider': 'Google Gemini',
        'ai_available': gemini_service.is_available()
    })

@main_bp.route('/api/test-search', methods=['POST'])
def test_search():
    """Test endpoint for search functionality."""
    try:
        data = request.get_json()
        article_title = data.get('article_title', 'Artificial Intelligence')

        logger.info(f"🧪 Test search requested for: {article_title}")

        from app import gemini_service

        # Test the Gemini service directly
        mock_content = f"This is a test article about {article_title}. It covers various aspects of the topic including its history, applications, and future prospects."

        related_articles = gemini_service.get_related_articles_with_retry(
            mock_content, article_title, max_retries=1
        )

        return jsonify({
            'success': True,
            'article_title': article_title,
            'related_articles': related_articles,
            'gemini_available': gemini_service.is_available()
        })

    except Exception as e:
        logger.error(f"❌ Test search failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
