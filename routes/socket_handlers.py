"""
WebSocket event handlers for real-time communication
"""

import logging
from flask import request
from flask_socketio import emit

logger = logging.getLogger(__name__)

def register_socket_handlers(socketio, search_engine, rate_limiter):
    """Register all socket event handlers."""

    @socketio.on('connect')
    def handle_connect():
        """Handle client connection."""
        logger.info(f"✅ Client connected: {request.sid}")
        emit('connected', {
            'message': 'Connected to server successfully',
            'session_id': request.sid,
            'ai_provider': 'Google Gemini',
            'timestamp': str(request.sid)
        })

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection."""
        logger.info(f"❌ Client disconnected: {request.sid}")

    @socketio.on('start_search')
    def handle_start_search(data):
        """Handle WebSocket request to start recursive search."""
        session_id = request.sid

        logger.info(f"🔍 Received start_search request from session {session_id}")
        logger.info(f"📊 Request data: {data}")

        # Validate request data
        if not data:
            logger.error("❌ No data provided in start_search request")
            emit('error', {'message': 'No data provided'})
            return

        article_title = data.get('article_title')
        if not article_title:
            logger.error("❌ No article title provided")
            emit('error', {'message': 'Article title is required'})
            return

        # Clean up the article title
        article_title = article_title.strip()
        if not article_title:
            logger.error("❌ Empty article title provided")
            emit('error', {'message': 'Article title cannot be empty'})
            return

        logger.info(f"📖 Article title: '{article_title}'")

        # Check rate limit before starting
        if not rate_limiter.can_make_call():
            wait_time = rate_limiter.wait_time()
            logger.warning(f"⏳ Rate limited. Wait time: {wait_time:.0f} seconds")
            emit('rate_limit_warning', {
                'message': f'Rate limited. Please wait {wait_time:.0f} seconds before starting a new search.',
                'wait_time': wait_time
            })
            return

        logger.info(f"🚀 Starting search for '{article_title}' (session: {session_id})")

        # Start search in background
        try:
            def run_search():
                try:
                    search_engine.start_search(article_title, session_id)
                except Exception as e:
                    logger.error(f"❌ Search engine error: {e}", exc_info=True)
                    socketio.emit('error', {
                        'message': f'Search engine error: {str(e)}',
                        'session_id': session_id
                    }, room=session_id)

            socketio.start_background_task(run_search)
            logger.info("✅ Background search task started successfully")

        except Exception as e:
            logger.error(f"❌ Failed to start background task: {e}", exc_info=True)
            emit('error', {'message': f'Failed to start search: {str(e)}'})

    @socketio.on('test')
    def handle_test(data):
        """Handle test message."""
        logger.info(f"🧪 Test message received from {request.sid}: {data}")
        emit('connected', {
            'message': 'Test successful! Connection is working.',
            'echo': data,
            'session_id': request.sid,
            'timestamp': str(request.sid)
        })

    @socketio.on('ping')
    def handle_ping():
        """Handle ping for connection testing."""
        logger.debug(f"🏓 Ping received from {request.sid}")
        emit('pong', {
            'timestamp': str(request.sid),
            'session_id': request.sid
        })

    @socketio.on('get_rate_limit_status')
    def handle_get_rate_limit_status():
        """Handle request for rate limit status."""
        status = rate_limiter.get_status()
        logger.info(f"📊 Rate limit status requested: {status}")
        emit('rate_limit_status', status)

    # Error handler
    @socketio.on_error_default
    def default_error_handler(e):
        logger.error(f"❌ Socket.IO error: {e}", exc_info=True)
        emit('error', {'message': f'Server error: {str(e)}'})
