"""
Search tree models and data structures
"""

from datetime import datetime
from typing import Dict, List, Optional, Any

class SearchTreeNode:
    """Represents a node in the search tree."""

    def __init__(self, title: str, parent_id: Optional[str] = None):
        self.id = f"{title}_{datetime.now().timestamp()}"
        self.title = title
        self.parent_id = parent_id
        self.children: List[str] = []
        self.status = "searching"  # searching, completed, error, rate_limited
        self.timestamp = datetime.now().isoformat()
        self.error_message: Optional[str] = None

        # Additional fields for Google Search results
        self.url: Optional[str] = None
        self.snippet: Optional[str] = None
        self.image: Optional[str] = None
        self.source: Optional[str] = None
        self.search_query: Optional[str] = None

        # Gemini Summary
        self.summary: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'title': self.title,
            'parent_id': self.parent_id,
            'children': self.children,
            'status': self.status,
            'timestamp': self.timestamp,
            'error_message': self.error_message,
            'url': self.url,
            'snippet': self.snippet,
            'image': self.image,
            'source': self.source,
            'search_query': self.search_query
        }

    def add_child(self, child_id: str) -> None:
        """Add a child node ID."""
        if child_id not in self.children:
            self.children.append(child_id)

    def set_error(self, error_message: str) -> None:
        """Set node status to error with message."""
        self.status = "error"
        self.error_message = error_message

    def set_completed(self) -> None:
        """Set node status to completed."""
        self.status = "completed"
        self.error_message = None

    def set_rate_limited(self) -> None:
        """Set node status to rate limited."""
        self.status = "rate_limited"
