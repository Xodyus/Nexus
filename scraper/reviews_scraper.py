"""Rotten Tomatoes critic-reviews scraper.

The tomatometer is a binary fresh/rotten percentage - a pile of lukewarm
6/10 "fresh" reviews reads the same as a pile of 9/10 raves. This module
scrapes RT's /m/<slug>/reviews page, pulls each critic's explicit numeric
score where they published one (e.g. "3.5/5", "8/10", "B+"), normalizes it
to a 0-100 scale, and averages across the reviews that had one. That average
is the "real" downscaling signal the C++ engine uses instead of the raw
tomatometer (see normalize.py and score_engine.cpp).

NOTE: like rt_scraper.py, this scrapes public page markup, not an official
API - RT can change this without notice. Critic review cards on RT have
long carried a visible "Original Score:" label regardless of the underlying
component markup, so that text label (rather than a CSS class or custom
element name) is the primary extraction anchor here - it's the part most
likely to survive a markup change. If extraction starts returning nothing,
inspect a saved page and check ORIGINAL_SCORE_RE and FRESH_ICON_RE below
first.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

from rate_limit import is_allowed
from rt_scraper import HEADERS, ScrapeError, throttle

BASE_URL = "https://www.rottentomatoes.com/m/{slug}/reviews"
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

# Visible on each critic review card regardless of markup churn.
ORIGINAL_SCORE_RE = re.compile(r"Original Score:\s*([A-Fa-f][+-]?|[\d.]+\s*/\s*[\d.]+)")

# Letter-grade -> numeric (out of 100) mapping. RT critics occasionally
# publish a letter grade instead of a fraction (e.g. Original Score: B+).
LETTER_GRADES = {
    "A+": 100, "A": 95, "A-": 90,
    "B+": 87, "B": 83, "B-": 80,
    "C+": 77, "C": 73, "C-": 70,
    "D+": 67, "D": 63, "D-": 60,
    "F": 40,
}


def fetch_reviews_html(slug: str, session: Optional[requests.Session] = None) -> str:
    session = session or requests.Session()
    url = BASE_URL.format(slug=slug)
    if not is_allowed(url, HEADERS["User-Agent"]):
        raise ScrapeError(f"robots.txt disallows fetching {url}")
    throttle()
    resp = session.get(url, headers=HEADERS, timeout=15)
    if resp.status_code == 404:
        raise ScrapeError(f"No reviews page found for slug '{slug}' ({url})")
    resp.raise_for_status()
    return resp.text


def _score_to_100(score_text: str) -> Optional[float]:
    """Normalize an "Original Score" value to 0-100, or None if it can't
    be parsed (unusual formats, e.g. "3 stars", are skipped rather than
    guessed at)."""
    text = score_text.strip()

    grade = LETTER_GRADES.get(text.upper())
    if grade is not None:
        return float(grade)

    match = re.match(r"^([\d.]+)\s*/\s*([\d.]+)$", text)
    if match:
        numerator, denominator = float(match.group(1)), float(match.group(2))
        if denominator <= 0:
            return None
        return max(0.0, min(100.0, (numerator / denominator) * 100.0))

    return None


def _is_fresh(card_text: str) -> Optional[bool]:
    lowered = card_text.lower()
    if "rotten" in lowered and "fresh" not in lowered:
        return False
    if "fresh" in lowered:
        return True
    return None


def extract_reviews(html: str, slug: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    # Each review lives in its own card; RT has used a handful of custom
    # element / class names for this over time (review-row, media-review-card,
    # etc), so cast a wide net and filter by whether "Original Score:"
    # actually appears in the card's text rather than betting on one name.
    candidates = soup.select(
        "media-review-card-critic, div[class*='review-row'], "
        "div[class*='media-review-card'], div[data-qa='review-item']"
    )
    if not candidates:
        # Fall back to scanning the whole page in fixed-size chunks - still
        # lets us find "Original Score:" occurrences even if RT drops every
        # class/element name above.
        candidates = [soup]

    reviews = []
    seen_text = set()
    for card in candidates:
        text = card.get_text(" ", strip=True)
        for match in ORIGINAL_SCORE_RE.finditer(text):
            score_text = match.group(1)
            key = (score_text, text[:80])
            if key in seen_text:
                continue
            seen_text.add(key)
            score_100 = _score_to_100(score_text)
            reviews.append({
                "score_text": score_text,
                "score_100": score_100,
                "fresh": _is_fresh(text),
            })

    if not reviews and candidates == [soup] and "Original Score:" not in soup.get_text():
        raise ScrapeError(
            "Could not find any 'Original Score:' text on the reviews page. "
            "Rotten Tomatoes likely changed its markup or this movie has no "
            "critic reviews with explicit scores - check "
            "reviews_scraper.py's ORIGINAL_SCORE_RE and the card selectors "
            "in extract_reviews()."
        )

    scored = [r["score_100"] for r in reviews if r["score_100"] is not None]
    average = sum(scored) / len(scored) if scored else None

    return {
        "slug": slug,
        "scraped_at": time.time(),
        "reviews": reviews,
        "average_critic_score": average,
        "scored_review_count": len(scored),
    }


def save_reviews(slug: str, data: dict) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"{slug}_reviews.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


def scrape_reviews(slug: str) -> Path:
    """Fetch + extract + cache numeric critic scores for one movie slug."""
    html = fetch_reviews_html(slug)
    data = extract_reviews(html, slug)
    return save_reviews(slug, data)


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape numeric critic scores for a movie")
    parser.add_argument("slug", help="RT movie slug, e.g. 'dune_part_two'")
    args = parser.parse_args()
    try:
        path = scrape_reviews(args.slug)
    except ScrapeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"saved reviews data -> {path}")


if __name__ == "__main__":
    main()
