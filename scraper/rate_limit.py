"""Shared rate limiting and robots.txt etiquette for the RT scrapers.

REQUEST_DELAY_SECONDS in rt_scraper.py used to just be a sleep the caller
had to remember to do after each scrape. A token bucket enforces a hard cap
on request rate across the whole process instead, regardless of how many
call sites end up fetching pages - both rt_scraper.py and
reviews_scraper.py share the one bucket built in rt_scraper.py, since they
hit the same host.
"""

from __future__ import annotations

import threading
import time
import urllib.robotparser
from typing import Optional

ROBOTS_URL = "https://www.rottentomatoes.com/robots.txt"


class TokenBucket:
    """`rate` tokens refill per second, up to `capacity`. acquire() blocks
    (sleeps) until a token is available, then takes it."""

    def __init__(self, rate: float, capacity: float):
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.updated_at = time.monotonic()
        self.lock = threading.Lock()

    def acquire(self, tokens: float = 1.0) -> None:
        with self.lock:
            while True:
                now = time.monotonic()
                self.tokens = min(self.capacity, self.tokens + (now - self.updated_at) * self.rate)
                self.updated_at = now
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return
                time.sleep((tokens - self.tokens) / self.rate)


_robots_parser: Optional[urllib.robotparser.RobotFileParser] = None
_robots_checked = False
_robots_lock = threading.Lock()


def _load_robots() -> Optional[urllib.robotparser.RobotFileParser]:
    global _robots_parser, _robots_checked
    with _robots_lock:
        if not _robots_checked:
            _robots_checked = True
            parser = urllib.robotparser.RobotFileParser()
            parser.set_url(ROBOTS_URL)
            try:
                parser.read()
                _robots_parser = parser
            except OSError:
                # Can't reach robots.txt - fail open rather than blocking
                # every scrape on a network hiccup. The token bucket still
                # caps request volume regardless.
                _robots_parser = None
        return _robots_parser


def is_allowed(url: str, user_agent: str) -> bool:
    parser = _load_robots()
    if parser is None:
        return True
    return parser.can_fetch(user_agent, url)
