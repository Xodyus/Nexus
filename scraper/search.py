"""Slug lookup by movie title.

Rotten Tomatoes doesn't publish a documented public search API, so this
tries RT's site-search endpoint first (best match, handles most titles) and
falls back to a deterministic slug guess (lowercase, spaces -> underscores,
strip punctuation) whenever the endpoint is unreachable, its response shape
has changed, or it returns nothing - never raises. The guess isn't always
right (RT sometimes disambiguates with a trailing release year), so callers
should present it as one candidate among others rather than assume it's
correct. If search_titles() is consistently returning [], RT's search
endpoint (SEARCH_URL below) is the first place to check.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional

import requests

from rt_scraper import HEADERS

SEARCH_URL = "https://www.rottentomatoes.com/napi/search/all"


def guess_slug(title: str, year: Optional[int] = None) -> str:
    normalized = unicodedata.normalize("NFKD", title)
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9\s]", "", normalized)
    slug = re.sub(r"\s+", "_", normalized).strip("_")
    if year:
        slug = f"{slug}_{year}"
    return slug


def search_titles(title: str, session: Optional[requests.Session] = None) -> list[dict]:
    """Return candidate {"slug", "title", "year"} dicts from RT's search
    endpoint, best match first. Returns [] (never raises) if the endpoint is
    unreachable or its response shape doesn't match what's expected here."""
    session = session or requests.Session()
    try:
        resp = session.get(
            SEARCH_URL, params={"query": title, "type": "movie"},
            headers=HEADERS, timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError):
        return []

    if not isinstance(data, dict):
        return []

    candidates = []
    for group in data.get("results", []):
        if not isinstance(group, dict) or group.get("type") != "movie":
            continue
        for item in group.get("items", []):
            url = item.get("url") or ""
            match = re.search(r"/m/([a-z0-9_]+)/?$", url)
            if not match:
                continue
            candidates.append({
                "slug": match.group(1),
                "title": item.get("name") or title,
                "year": item.get("releaseYear"),
            })
    return candidates


def search_slug(title: str, session: Optional[requests.Session] = None) -> list[dict]:
    """Best-effort candidate list for a title: RT search results first,
    falling back to a single deterministic guess if the search comes up
    empty."""
    candidates = search_titles(title, session=session)
    if candidates:
        return candidates
    return [{"slug": guess_slug(title), "title": title, "year": None}]
