"""
Wikipedia Article Explorer with Real-time Search Tree
A Flask application that allows users to explore Wikipedia articles and visualize
Google Gemini's recursive search process in real-time.
"""

import logging
from flask import Flask
from flask_socketio import SocketIO

from config import Config
from utils.rate_limiter import RateLimiter
from services.gemini_service import GeminiService
from services.search_engine import RecursiveSearchEngine
from routes.main_routes import main_bp
from routes.socket_handlers import register_socket_handlers

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*", logger=Config.DEBUG, engineio_logger=Config.DEBUG)

    # Initialize services
    rate_limiter = RateLimiter(max_calls_per_minute=Config.MAX_CALLS_PER_MINUTE)
    gemini_service = GeminiService(rate_limiter)
    search_engine = RecursiveSearchEngine(socketio, gemini_service)

    # Register blueprints
    app.register_blueprint(main_bp)

    # Register socket handlers
    register_socket_handlers(socketio, search_engine, rate_limiter)

    # Store services in app context for access in routes
    app.rate_limiter = rate_limiter
    app.gemini_service = gemini_service
    app.search_engine = search_engine

    logger.info("Wikipedia Explorer application created successfully")
    logger.info(f"Gemini service available: {gemini_service.is_available()}")
    logger.info(f"Model info: {gemini_service.get_model_info()}")
    logger.info(f"Rate limiting: {Config.MAX_CALLS_PER_MINUTE} calls per minute")

    return app, socketio

# Create the application
app, socketio = create_app()

# Make services available for imports (for backward compatibility)
rate_limiter = app.rate_limiter
gemini_service = app.gemini_service
search_engine = app.search_engine

if __name__ == '__main__':
    logger.info("Starting Wikipedia Explorer with Google Gemini...")
    socketio.run(app, debug=Config.DEBUG, host=Config.HOST, port=Config.PORT)
