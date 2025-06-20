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
        logger.info(f"Starting recursive search for: {initial_article} (session: {session_id})")

        try:
            # Clear previous search tree
            self.search_tree = {}

            # Create root node
            root_node = SearchTreeNode(initial_article)
            self.search_tree[root_node.id] = root_node

            # Emit search started event
            self.socketio.emit('search_started', {
                'article': initial_article,
                'ai_provider': 'Google Gemini'
            }, room=session_id)

            # Emit initial tree state
            self._emit_tree_update(session_id)

            # Start recursive search
            self._recursive_search(root_node.id, 0, session_id)

            # Emit search complete event
            self.socketio.emit('search_complete', {
                'message': 'Search completed',
                'total_nodes': len(self.search_tree)
            }, room=session_id)

        except Exception as e:
            logger.error(f"Error in start_search: {e}")
            self.socketio.emit('error', {'message': f'Search failed: {str(e)}'}, room=session_id)

    def _recursive_search(self, node_id: str, depth: int, session_id: str) -> None:
        """Perform recursive search with real-time updates."""
        try:
            if depth >= Config.MAX_SEARCH_DEPTH:
                logger.info(f"Reached max depth {depth} for node {node_id}")
                return

            current_node = self.search_tree[node_id]
            logger.info(f"Processing node: {current_node.title} at depth {depth}")

            # Add delay between requests to avoid rate limiting
            delay = random.uniform(Config.MIN_DELAY_BETWEEN_REQUESTS, Config.MAX_DELAY_BETWEEN_REQUESTS)
            logger.info(f"Waiting {delay:.1f} seconds to avoid rate limits...")
            time.sleep(delay)

            # Fetch article content
            article_content = WikipediaAPI.get_article_content(current_node.title)

            if not article_content:
                current_node.set_error("Could not fetch article content")
                self._emit_tree_update(session_id)
                return

            # Use Gemini to find related articles (with rate limiting)
            related_articles = self.gemini_service.get_related_articles_with_retry(
                article_content, current_node.title
            )

            if not related_articles:
                current_node.set_error("Could not find related articles")
                self._emit_tree_update(session_id)
                return

            logger.info(f"Found {len(related_articles)} related articles for {current_node.title}")

            # Create child nodes
            for i, article_title in enumerate(related_articles[:Config.MAX_ARTICLES_PER_LEVEL]):
                child_node = SearchTreeNode(article_title, node_id)
                self.search_tree[child_node.id] = child_node
                current_node.add_child(child_node.id)

                # Emit tree update
                self._emit_tree_update(session_id)

                # Add delay between creating nodes
                if i < len(related_articles) - 1:
                    time.sleep(0.5)  # Shorter delay since Gemini is faster

                # Continue recursive search
                if depth < Config.MAX_SEARCH_DEPTH - 1:
                    self._recursive_search(child_node.id, depth + 1, session_id)

            # Mark current node as completed
            current_node.set_completed()
            self._emit_tree_update(session_id)

        except Exception as e:
            logger.error(f"Error in _recursive_search: {e}")
            if node_id in self.search_tree:
                self.search_tree[node_id].set_error(str(e))
                self._emit_tree_update(session_id)

    def _emit_tree_update(self, session_id: str) -> None:
        """Emit tree update to client."""
        tree_data = {
            node_id: node.to_dict()
            for node_id, node in self.search_tree.items()
        }

        logger.debug(f"Emitting tree update to {session_id}: {len(tree_data)} nodes")
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
