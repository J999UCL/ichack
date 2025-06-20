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

    logger.info("🚀 Creating Flask application...")

    # Initialize SocketIO with proper configuration
    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        logger=Config.DEBUG,
        engineio_logger=Config.DEBUG,
        async_mode='threading'  # Use threading for better compatibility
    )

    logger.info("✅ SocketIO initialized")

    # Initialize services
    logger.info("🔧 Initializing services...")
    rate_limiter = RateLimiter(max_calls_per_minute=Config.MAX_CALLS_PER_MINUTE)
    gemini_service = GeminiService(rate_limiter)
    search_engine = RecursiveSearchEngine(socketio, gemini_service)

    logger.info("✅ Services initialized")

    # Register blueprints
    app.register_blueprint(main_bp)
    logger.info("✅ Blueprints registered")

    # Register socket handlers
    register_socket_handlers(socketio, search_engine, rate_limiter)
    logger.info("✅ Socket handlers registered")

    # Store services in app context for access in routes
    app.rate_limiter = rate_limiter
    app.gemini_service = gemini_service
    app.search_engine = search_engine

    # Log configuration
    logger.info("📊 Application Configuration:")
    logger.info(f"  - Gemini service available: {gemini_service.is_available()}")
    logger.info(f"  - Model info: {gemini_service.get_model_info()}")
    logger.info(f"  - Rate limiting: {Config.MAX_CALLS_PER_MINUTE} calls per minute")
    logger.info(f"  - Max search depth: {Config.MAX_SEARCH_DEPTH}")
    logger.info(f"  - Max articles per level: {Config.MAX_ARTICLES_PER_LEVEL}")
    logger.info(f"  - Debug mode: {Config.DEBUG}")

    logger.info("✅ Wikipedia Explorer application created successfully")

    return app, socketio

# Create the application
app, socketio = create_app()

# Make services available for imports (for backward compatibility)
rate_limiter = app.rate_limiter
gemini_service = app.gemini_service
search_engine = app.search_engine

if __name__ == '__main__':
    logger.info("🌟 Starting Wikipedia Explorer with Google Gemini...")
    logger.info(f"🌐 Server will be available at: http://{Config.HOST}:{Config.PORT}")
    logger.info(f"🔧 Debug page: http://{Config.HOST}:{Config.PORT}/debug")

    socketio.run(
        app,
        debug=Config.DEBUG,
        host=Config.HOST,
        port=Config.PORT,
        allow_unsafe_werkzeug=True  # For development
    )
