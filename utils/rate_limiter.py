"""
Rate limiting utilities for API calls
"""

import time
import logging
from typing import List

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple rate limiter for API calls."""

    def __init__(self, max_calls_per_minute: int = 3):
        self.max_calls_per_minute = max_calls_per_minute
        self.calls: List[float] = []

    def can_make_call(self) -> bool:
        """Check if we can make an API call."""
        now = time.time()
        # Remove calls older than 1 minute
        self.calls = [call_time for call_time in self.calls if now - call_time < 60]

        return len(self.calls) < self.max_calls_per_minute

    def record_call(self) -> None:
        """Record that we made an API call."""
        self.calls.append(time.time())

    def wait_time(self) -> float:
        """Get how long to wait before next call."""
        if not self.calls:
            return 0

        oldest_call = min(self.calls)
        wait_time = 60 - (time.time() - oldest_call)
        return max(0, wait_time)

    def get_status(self) -> dict:
        """Get current rate limiter status."""
        return {
            'can_make_call': self.can_make_call(),
            'wait_time': self.wait_time(),
            'recent_calls': len(self.calls),
            'max_calls_per_minute': self.max_calls_per_minute
        }
