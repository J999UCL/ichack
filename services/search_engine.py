"""
Recursive search engine for building article trees using Google Search
"""

import logging
import time
import random
from typing import Dict, Optional

from config import Config
from models.search_tree import SearchTreeNode
from services.google_search_api import GoogleSearchAPI
from services.gemini_service import GeminiService

logger = logging.getLogger(__name__)

class RecursiveSearchEngine:
    """Handles recursive article search with real-time tree updates using Google Search."""

    def __init__(self, socketio_instance, gemini_service: GeminiService):
        self.socketio = socketio_instance
        self.gemini_service = gemini_service
        self.google_search = GoogleSearchAPI()
        self.search_tree: Dict[str, SearchTreeNode] = {}

    def start_search(self, initial_article_data: Dict, session_id: str) -> None:
        """Start recursive search and emit tree updates."""
        article_title = initial_article_data.get('title', 'Unknown Article')
        article_url = initial_article_data.get('url', '')

        logger.info(f"🚀 Starting recursive search for: '{article_title}' (session: {session_id})")

        try:
            # Clear previous search tree
            self.search_tree = {}

            # Create root node with article data
            root_node = SearchTreeNode(article_title)
            root_node.url = article_url
            root_node.snippet = initial_article_data.get('snippet', '')
            root_node.image = initial_article_data.get('image', '')
            root_node.source = initial_article_data.get('source', '')

            self.search_tree[root_node.id] = root_node

            logger.info(f"🌱 Created root node: {root_node.id}")

            # Emit search started event
            self.socketio.emit('search_started', {
                'article': article_title,
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

            logger.info(f"✅ Search completed for '{article_title}' with {len(self.search_tree)} nodes")

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

            # Get article content if we have a URL (use snippet as fallback)
            article_content = ""
            if hasattr(current_node, 'snippet') and current_node.snippet:
                article_content = current_node.snippet

            # If we have a URL, try to get more content
            if hasattr(current_node, 'url') and current_node.url:
                try:
                    full_content = self.google_search.get_article_content(current_node.url)
                    if full_content and len(full_content) > len(article_content):
                        article_content = full_content[:1000]  # Limit content length
                except Exception as e:
                    logger.warning(f"Could not fetch full content from {current_node.url}: {e}")

            # Use Gemini to find related search queries
            logger.info(f"🤖 Getting related search queries from Gemini for: {current_node.title}")
            search_queries = self.gemini_service.get_related_search_queries(
                current_node.title, article_content
            )

            if not search_queries:
                logger.warning(f"❌ No search queries found for: {current_node.title}")
                current_node.set_error("Could not generate related search queries")
                self._emit_tree_update(session_id)
                return

            logger.info(f"✅ Found {len(search_queries)} search queries: {search_queries}")

            # Search for articles using each query and create child nodes
            children_created = 0
            for i, query in enumerate(search_queries[:Config.MAX_ARTICLES_PER_LEVEL]):
                logger.info(f"🔍 Searching Google for query {i+1}/{len(search_queries)}: '{query}'")

                try:
                    # Search Google for articles using this query
                    search_results = self.google_search.search_articles(query, limit=3)

                    if search_results:
                        # Take the best result (first one)
                        best_result = search_results[0]

                        # Create child node with the actual website data
                        child_node = SearchTreeNode(best_result['title'], node_id)
                        child_node.url = best_result['url']
                        child_node.snippet = best_result['snippet']
                        child_node.image = best_result['image']
                        child_node.source = best_result['source']
                        child_node.search_query = query  # Store the query that found this result

                        self.search_tree[child_node.id] = child_node
                        current_node.add_child(child_node.id)
                        children_created += 1

                        logger.info(f"🌿 Created child node: '{best_result['title']}' from '{best_result['source']}'")
                        logger.info(f"   📄 URL: {best_result['url']}")
                        logger.info(f"   🔍 Found via query: '{query}'")

                        # Emit tree update to show the new node
                        self._emit_tree_update(session_id)

                        # Add small delay between creating nodes for better UX
                        if i < len(search_queries) - 1:
                            time.sleep(0.8)

                        # Continue recursive search for this child node
                        if depth < Config.MAX_SEARCH_DEPTH - 1:
                            logger.info(f"🔄 Continuing recursive search for: '{best_result['title']}'")
                            self._recursive_search(child_node.id, depth + 1, session_id)
                        else:
                            logger.info(f"📏 Max depth reached, marking '{best_result['title']}' as completed")
                            child_node.set_completed()
                            self._emit_tree_update(session_id)
                    else:
                        logger.warning(f"❌ No search results found for query: '{query}'")

                except Exception as e:
                    logger.error(f"❌ Error searching for query '{query}': {e}")
                    continue

            # Mark current node as completed
            if children_created > 0:
                logger.info(f"✅ Successfully created {children_created} child nodes for: {current_node.title}")
                current_node.set_completed()
            else:
                logger.warning(f"⚠️ No child nodes created for: {current_node.title}")
                current_node.set_error("No related articles found")

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

        # Log some details about the nodes for debugging
        for node_id, node_data in tree_data.items():
            logger.debug(f"  Node: {node_data['title']} | Status: {node_data['status']} | URL: {node_data.get('url', 'N/A')}")

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
