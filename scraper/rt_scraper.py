"""Rotten Tomatoes raw data scraper.

Fetches a movie page from Rotten Tomatoes and extracts the JSON/attribute
data RT ships to the browser (tomatometer, audience score, review counts,
etc). Saves the raw payload to data/raw/<slug>.json so the rest of the
pipeline (normalize -> score engine) can work from a local cache instead of
re-hitting RT on every run.

NOTE: this scrapes public page markup, not an official API. Rotten
Tomatoes can and does change its HTML/JSON structure without notice - if
extraction starts failing, the selectors below are the first place to look.
Keep request volume low and cache aggressively (see REQUEST_DELAY_SECONDS
and the data/raw/ cache) to be a good citizen of someone else's site. All
requests to rottentomatoes.com (from this module and reviews_scraper.py)
go through throttle() and a robots.txt check - see rate_limit.py.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

from rate_limit import TokenBucket, is_allowed

BASE_URL = "https://www.rottentomatoes.com/m/{slug}"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
REQUEST_DELAY_SECONDS = 1.5  # minimum courtesy delay between requests

# Shared by every scraper module in this package (rt_scraper.py,
# reviews_scraper.py) - a hard cap on request rate to rottentomatoes.com
# regardless of how many call sites end up fetching pages. Allows a small
# burst (e.g. a movie page + its reviews page back to back) but settles to
# one request per REQUEST_DELAY_SECONDS.
_bucket = TokenBucket(rate=1 / REQUEST_DELAY_SECONDS, capacity=2)


class ScrapeError(RuntimeError):
    """Raised when a movie page can't be fetched or parsed."""


def throttle() -> None:
    """Block until it's polite to make another request to Rotten Tomatoes."""
    _bucket.acquire()


def fetch_movie_html(slug: str, session: Optional[requests.Session] = None) -> str:
    session = session or requests.Session()
    url = BASE_URL.format(slug=slug)
    if not is_allowed(url, HEADERS["User-Agent"]):
        raise ScrapeError(f"robots.txt disallows fetching {url}")
    throttle()
    resp = session.get(url, headers=HEADERS, timeout=15)
    if resp.status_code == 404:
        raise ScrapeError(f"No movie found for slug '{slug}' ({url})")
    resp.raise_for_status()
    return resp.text

##
def _extract_score_board(soup: BeautifulSoup) -> dict:
    """RT now ships headline scores as JSON in a
    <script id="media-scorecard-json"> tag (the old <score-board> custom
    element with score attributes was replaced by <media-scorecard>, which
    no longer carries the scores itself). This is the primary, most stable
    source."""
    tag = soup.find("script", id="media-scorecard-json")
    if tag is None or not tag.string:
        return {}
    try:
        data = json.loads(tag.string)
    except json.JSONDecodeError:
        return {}

    critics = data.get("criticsScore") or {}
    audience = data.get("audienceScore") or {}
    board = {
        "tomatometerscore": critics.get("score"),
        "tomatometerstate": critics.get("sentiment"),
        "tomatometercount": critics.get("reviewCount"),
        "audiencescore": audience.get("score"),
        "audiencestate": audience.get("sentiment"),
        "audiencecount": audience.get("reviewCount"),
        "certified": critics.get("certified"),
    }
    return {k: v for k, v in board.items() if v is not None}

##
def _extract_next_data(soup: BeautifulSoup) -> dict:
    """Fallback: RT embeds a schema.org Movie block as
    <script type="application/ld+json"> (this replaced the old Next.js
    __NEXT_DATA__ blob). Useful when score-board data is absent or when
    richer fields (cast, genre, content rating) are needed later."""
    tag = soup.find("script", type="application/ld+json")
    if tag is None or not tag.string:
        return {}
    try:
        return json.loads(tag.string)
    except json.JSONDecodeError:
        return {}


def extract_raw_data(html: str, slug: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    score_board = _extract_score_board(soup)
    next_data = _extract_next_data(soup)

    if not score_board and not next_data:
        raise ScrapeError(
            "Could not find media-scorecard-json or the ld+json Movie block "
            "on the page. Rotten Tomatoes likely changed its markup - update "
            "the extraction functions in rt_scraper.py."
        )

    for count_key in ("tomatometercount", "audiencecount"):
        if score_board.get(count_key, 0) == 0:
            print(
                f"warning: '{slug}' has a 0 (or missing) {count_key} - the "
                "shrinkage math in score_engine.cpp will silently fall back "
                "to the prior for this score",
                file=sys.stderr,
            )

    return {
        "slug": slug,
        "scraped_at": time.time(),
        "score_board": score_board,
        "next_data": next_data,
    }


def save_raw(slug: str, data: dict) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"{slug}.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def scrape(slug: str) -> Path:
    """Fetch + extract + cache the raw data for one movie slug."""
    html = fetch_movie_html(slug)
    data = extract_raw_data(html, slug)
    return save_raw(slug, data)


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape raw RT data for a movie")
    parser.add_argument("slug", help="RT movie slug, e.g. 'dune_part_two'")
    args = parser.parse_args()
    try:
        path = scrape(args.slug)
    except ScrapeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"saved raw data -> {path}")


if __name__ == "__main__":
    main()
