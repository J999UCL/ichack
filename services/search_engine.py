"""
Recursive search engine for building article trees
"""

import logging
import time
import random
from typing import Dict, Optional

from config import Config
from models.search_tree import SearchTreeNode
from services.wikipedia_api import WikipediaAPI
from services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

class RecursiveSearchEngine:
    """Handles recursive article search with real-time tree updates."""

    def __init__(self, socketio_instance, gemini_service: GeminiService):
        self.socketio = socketio_instance
        self.gemini_service = gemini_service
        self.search_tree: Dict[str, SearchTreeNode] = {}

    def start_search(self, initial_article: str, session_id: str) -> None:
        """Start recursive search and emit tree updates."""
        logger.info(f"🚀 Starting recursive search for: '{initial_article}' (session: {session_id})")

        try:
            # Clear previous search tree
            self.search_tree = {}

            # Create root node
            root_node = SearchTreeNode(initial_article)
            self.search_tree[root_node.id] = root_node

            logger.info(f"🌱 Created root node: {root_node.id}")

            # Emit search started event
            self.socketio.emit('search_started', {
                'article': initial_article,
                'ai_provider': 'Google Gemini',
                'session_id': session_id
            }, room=session_id)

            # Emit initial tree state
            self._emit_tree_update(session_id)

            # Start recursive search
            self._recursive_search(root_node.id, 0, session_id)

            # Emit search complete event
            self.socketio.emit('search_complete', {
                'message': 'Search completed successfully',
                'total_nodes': len(self.search_tree),
                'session_id': session_id
            }, room=session_id)

            logger.info(f"✅ Search completed for '{initial_article}' with {len(self.search_tree)} nodes")

        except Exception as e:
            logger.error(f"❌ Error in start_search: {e}", exc_info=True)
            self.socketio.emit('error', {
                'message': f'Search failed: {str(e)}',
                'session_id': session_id
            }, room=session_id)

    def _recursive_search(self, node_id: str, depth: int, session_id: str) -> None:
        """Perform recursive search with real-time updates."""
        try:
            if depth >= Config.MAX_SEARCH_DEPTH:
                logger.info(f"📏 Reached max depth {depth} for node {node_id}")
                return

            current_node = self.search_tree[node_id]
            logger.info(f"🔍 Processing node: '{current_node.title}' at depth {depth}")

            # Add delay between requests to avoid rate limiting
            delay = random.uniform(Config.MIN_DELAY_BETWEEN_REQUESTS, Config.MAX_DELAY_BETWEEN_REQUESTS)
            logger.info(f"⏳ Waiting {delay:.1f} seconds to avoid rate limits...")
            time.sleep(delay)

            # Fetch article content
            logger.info(f"📖 Fetching content for: {current_node.title}")
            article_content = WikipediaAPI.get_article_content(current_node.title)

            if not article_content:
                logger.warning(f"❌ Could not fetch content for: {current_node.title}")
                current_node.set_error("Could not fetch article content")
                self._emit_tree_update(session_id)
                return

            logger.info(f"✅ Fetched {len(article_content)} characters of content")

            # Use Gemini to find related articles (with rate limiting)
            logger.info(f"🤖 Getting related articles from Gemini for: {current_node.title}")
            related_articles = self.gemini_service.get_related_articles_with_retry(
                article_content, current_node.title
            )

            if not related_articles:
                logger.warning(f"❌ No related articles found for: {current_node.title}")
                current_node.set_error("Could not find related articles")
                self._emit_tree_update(session_id)
                return

            logger.info(f"✅ Found {len(related_articles)} related articles: {related_articles}")

            # Create child nodes
            for i, article_title in enumerate(related_articles[:Config.MAX_ARTICLES_PER_LEVEL]):
                logger.info(f"🌿 Creating child node {i+1}/{len(related_articles)}: {article_title}")

                child_node = SearchTreeNode(article_title, node_id)
                self.search_tree[child_node.id] = child_node
                current_node.add_child(child_node.id)

                # Emit tree update
                self._emit_tree_update(session_id)

                # Add delay between creating nodes
                if i < len(related_articles) - 1:
                    time.sleep(0.5)

                # Continue recursive search
                if depth < Config.MAX_SEARCH_DEPTH - 1:
                    logger.info(f"🔄 Continuing recursive search for: {article_title}")
                    self._recursive_search(child_node.id, depth + 1, session_id)
                else:
                    logger.info(f"📏 Max depth reached, marking {article_title} as completed")
                    child_node.set_completed()
                    self._emit_tree_update(session_id)

            # Mark current node as completed
            logger.info(f"✅ Marking node as completed: {current_node.title}")
            current_node.set_completed()
            self._emit_tree_update(session_id)

        except Exception as e:
            logger.error(f"❌ Error in _recursive_search for node {node_id}: {e}", exc_info=True)
            if node_id in self.search_tree:
                self.search_tree[node_id].set_error(str(e))
                self._emit_tree_update(session_id)

    def _emit_tree_update(self, session_id: str) -> None:
        """Emit tree update to client."""
        tree_data = {
            node_id: node.to_dict()
            for node_id, node in self.search_tree.items()
        }

        logger.info(f"📡 Emitting tree update to {session_id}: {len(tree_data)} nodes")
        logger.debug(f"Tree data: {list(tree_data.keys())}")

        self.socketio.emit('tree_update', tree_data, room=session_id)

    def get_tree_status(self) -> Dict[str, int]:
        """Get current tree status statistics."""
        status_counts = {}
        for node in self.search_tree.values():
            status_counts[node.status] = status_counts.get(node.status, 0) + 1

        return {
            'total_nodes': len(self.search_tree),
            'status_counts': status_counts
        }
