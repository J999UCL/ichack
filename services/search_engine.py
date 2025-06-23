"""
Recursive search engine for building article trees using Google Search
"""

import logging
import time
import random
from typing import Dict, Optional, List

from flask_socketio import rooms

from config import Config
from models.search_tree import SearchTreeNode
from services.google_search_api import GoogleSearchAPI
from services.gemini_service import GeminiService

logger = logging.getLogger(__name__)


class RecursiveSearchEngine:
    """Handles recursive article search with real-time tree updates using Google Search."""

    # ────────────────────────────────  init / public  ──────────────────────────────── #

    def __init__(self, socketio_instance, gemini_service: GeminiService):
        self.socketio = socketio_instance
        self.gemini_service = gemini_service
        self.google_search = GoogleSearchAPI()
        self.search_tree: Dict[str, SearchTreeNode] = {}


    def start_search(self, initial_article_data: Dict, session_id: str) -> None:
        """Start recursive search and emit tree updates."""
        article_title = initial_article_data.get("title", "Unknown Article")
        article_url = initial_article_data.get("url", "")

        logger.info(
            "Starting recursive search for: '%s' (session: %s)",
            article_title,
            session_id,
        )

        try:
            self.search_tree = {}  # clear any previous tree
            root_node = self._create_root_node(initial_article_data)
            self.search_tree[root_node.id] = root_node

            self._emit_search_started(article_title, session_id)
            self._emit_tree_update(session_id)

            # begin the recursion
            self._recursive_search(root_node.id, 0, session_id)

            self._emit_final_analysis(self._final_analysis(article_title), session_id)

            self._emit_search_complete(session_id)
            logger.info(
                "Search completed for '%s' with %d nodes",
                article_title,
                len(self.search_tree),
            )

        except Exception as e:
            logger.error("Error in start_search: %s", e, exc_info=True)
            self._emit_error(f"Search failed: {e}", session_id)

    # ────────────────────────────────  recursion  ──────────────────────────────── #

    def _recursive_search(self, node_id: str, depth: int, session_id: str) -> None:
        """Perform recursive search with real-time updates."""
        try:
            if depth >= Config.MAX_SEARCH_DEPTH:
                logger.info("Reached max depth %d for node %s", depth, node_id)
                return

            current_node = self.search_tree[node_id]
            logger.info("Processing node: '%s' at depth %d", current_node.title, depth)

            self._delay_between_requests()

            article_content = self._fetch_article_content(current_node)

            current_node.summary = self.gemini_service.summarize_article(article_content)
            search_queries = self._get_related_search_queries(
                current_node.title, article_content, current_node, session_id
            )

            if not search_queries:
                return

            children_created = 0
            for i, query in enumerate(search_queries[: Config.MAX_ARTICLES_PER_LEVEL]):
                if self._process_query(
                    current_node,
                    query,
                    i,
                    len(search_queries),
                    depth,
                    session_id,
                ):
                    children_created += 1

            # mark current node status
            if children_created > 0:
                logger.info(
                    "Successfully created %d child nodes for: %s",
                    children_created,
                    current_node.title,
                )
                current_node.set_completed()
            else:
                logger.warning("No child nodes created for: %s", current_node.title)
                current_node.set_error("No related articles found")

            self._emit_tree_update(session_id)

        except Exception as e:
            logger.error(
                "Error in _recursive_search for node %s: %s", node_id, e, exc_info=True
            )
            if node_id in self.search_tree:
                self.search_tree[node_id].set_error(str(e))
                self._emit_tree_update(session_id)

    # ────────────────────────────────  helpers (search)  ──────────────────────────────── #

    def _delay_between_requests(self) -> None:
        delay = random.uniform(
            Config.MIN_DELAY_BETWEEN_REQUESTS, Config.MAX_DELAY_BETWEEN_REQUESTS
        )
        logger.info("Waiting %.1f seconds to avoid rate limits...", delay)
        time.sleep(delay)

    def _fetch_article_content(self, node: SearchTreeNode) -> str:
        """Return the best available text snippet for *node*."""
        content = getattr(node, "snippet", "") or ""
        if getattr(node, "url", ""):
            try:
                full = self.google_search.get_article_content(node.url)
                if full and len(full) > len(content):
                    content = full[:1000]  # trim long bodies
            except Exception as e:
                logger.warning("Could not fetch full content from %s: %s", node.url, e)
        return content

    def _get_related_search_queries(
        self,
        title: str,
        content: str,
        node: SearchTreeNode,
        session_id: str,
    ) -> List[str]:
        logger.info("Getting related search queries from Gemini for: %s", title)
        try:
            queries = self.gemini_service.get_related_search_queries(title, content)
            if not queries:
                logger.warning("No search queries found for: %s", title)
                node.set_error("Could not generate related search queries")
                self._emit_tree_update(session_id)
            else:
                logger.info("Found %d search queries: %s", len(queries), queries)
            return queries
        except Exception as e:
            logger.error("Gemini failed for %s: %s", title, e)
            node.set_error("Gemini failed")
            self._emit_tree_update(session_id)
            return []

    def _collect_abstract_blocks(self) -> tuple[str, str]:
        """
        Return two newline-joined blocks:

        * leaf_block – only the abstracts of leaf nodes
        * full_block – every node in the tree

        Each block entry looks like:

            TITLE: ...
            SOURCE: ...
            SUMMARY: ...
            ---

        The function never re-queries the network; it just reads `node.summary`.
        """
        leaf_lines: list[str] = []
        full_lines: list[str] = []

        for node in self.search_tree.values():
            summary = getattr(node, "summary", "") or ""
            blob = (
                f"TITLE: {node.title}\n"
                f"SOURCE: {getattr(node, 'source', 'Unknown')}\n"
                f"SUMMARY: {summary}\n---"
            )
            full_lines.append(blob)

            # A leaf has no children or an empty list
            if not getattr(node, "children", []):
                leaf_lines.append(blob)

        return "\n".join(leaf_lines), "\n".join(full_lines)

    def _final_analysis(self, root_title):
        leaf_block, full_block = self._collect_abstract_blocks()
        return self.gemini_service.final_analysis(root_title, leaf_block, full_block)

    def _find_unique_result(self, results: List[Dict[str, str]]) -> Optional[Dict[str, str]]:
        """
        Return the first search result whose URL does **not** already appear
        anywhere in the tree.  If every result is a duplicate, return ``None``.
        """
        seen_urls = {
            n.url.lower()
            for n in self.search_tree.values()
            if getattr(n, "url", "")
        }
        for res in results:
            url = res.get("url", "").lower()
            if url and url not in seen_urls:
                return res
        return None

    def _process_query(
        self,
        parent_node: SearchTreeNode,
        query: str,
        index: int,
        total: int,
        depth: int,
        session_id: str,
    ) -> bool:
        """Handle one search query; returns True if a child node was created."""
        logger.info("Searching Google for query %d/%d: '%s'", index + 1, total, query)

        try:
            results = self.google_search.search_articles(query, limit=10)
            if not results:
                logger.warning("No search results found for query: '%s'", query)
                return False

            best = self._find_unique_result(results)
            if not best:
                logger.info("All top results for '%s' were duplicates — skipping", query)
                return False

            child = self._create_child_node(parent_node.id, best, query)

            self.search_tree[child.id] = child
            parent_node.add_child(child.id)

            logger.info(
                "Created child node: '%s' from '%s'",
                best["title"],
                best["source"],
            )
            logger.info("URL: %s", best["url"])
            logger.info("Found via query: '%s'", query)

            self._emit_tree_update(session_id)
            if index < total - 1:
                time.sleep(0.8)  # UX: stagger nodes in UI

            # depth-first dive
            if depth < Config.MAX_SEARCH_DEPTH - 1:
                logger.info("Continuing recursive search for: '%s'", best["title"])
                self._recursive_search(child.id, depth + 1, session_id)
            else:
                logger.info("Max depth reached, marking '%s' as completed", best["title"])
                child.set_completed()
                self._emit_tree_update(session_id)

            return True

        except Exception as e:
            logger.error("Error searching for query '%s': %s", query, e)
            return False

    # ────────────────────────────────  helpers (node / socket)  ──────────────────────────────── #

    def _create_root_node(self, data: Dict) -> SearchTreeNode:
        node = SearchTreeNode(data.get("title", "Unknown Article"))
        node.url = data.get("url", "")
        node.snippet = data.get("snippet", "")
        node.image = data.get("image", "")
        node.source = data.get("source", "")
        logger.info("Created root node: %s", node.id)
        return node

    @staticmethod
    def _create_child_node(
        parent_id: str, result: Dict[str, str], query: str
    ) -> SearchTreeNode:
        child = SearchTreeNode(result["title"], parent_id)
        child.url = result["url"]
        child.snippet = result["snippet"]
        child.image = result["image"]
        child.source = result["source"]
        child.search_query = query
        return child

    # ────────────────────────────────  helpers (socket events)  ──────────────────────────────── #

    def _emit_search_started(self, article: str, session_id: str) -> None:
        self.socketio.emit(
            "search_started",
            {
                "article": article,
                "ai_provider": "Google Gemini",
                "session_id": session_id,
            },
            room=session_id,
        )

    def _emit_search_complete(self, session_id: str) -> None:
        self.socketio.emit(
            "search_complete",
            {
                "message": "Search completed successfully",
                "total_nodes": len(self.search_tree),
                "session_id": session_id,
            },
            room=session_id,
        )

    def _emit_final_analysis(self, message: str, session_id: str) -> None:
        self.socketio.emit(
            "History Analysis Completed",
                {
                    "message": message, "session_id": session_id
                },
            room=session_id
            )

    def _emit_error(self, message: str, session_id: str) -> None:
        self.socketio.emit("error", {"message": message, "session_id": session_id}, room=session_id)

    def _emit_tree_update(self, session_id: str) -> None:
        tree_data = {nid: n.to_dict() for nid, n in self.search_tree.items()}
        logger.info("Emitting tree update to %s: %d nodes", session_id, len(tree_data))

        for node in tree_data.values():
            logger.debug(
                "  Node: %s | Status: %s | URL: %s",
                node["title"],
                node["status"],
                node.get("url", "N/A"),
            )

        self.socketio.emit("tree_update", tree_data, room=session_id)
