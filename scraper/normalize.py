"""Flatten raw RT scrape output into the small schema the C++ score engine
reads (see engine/src/score_engine.cpp)."""

from __future__ import annotations

import json
from pathlib import Path


def _to_number(value, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(str(value).rstrip("%"))
    except ValueError:
        return default


def normalize(raw: dict, reviews: dict | None = None) -> dict:
    board = raw.get("score_board", {})
    tomatometer_score = _to_number(board.get("tomatometerscore"))

    # average_critic_score is the "real" downscaling signal (see
    # reviews_scraper.py) - fall back to the raw tomatometer when the
    # reviews page wasn't scraped, or none of its reviews had an explicit
    # numeric score.
    average_critic_score = tomatometer_score
    if reviews and reviews.get("average_critic_score") is not None:
        average_critic_score = float(reviews["average_critic_score"])

    return {
        "slug": raw.get("slug", ""),
        "tomatometer_score": tomatometer_score,
        "average_critic_score": average_critic_score,
        "audience_score": _to_number(board.get("audiencescore")),
        "critic_review_count": _to_number(board.get("tomatometercount")),
        "audience_review_count": _to_number(board.get("audiencecount")),
    }


def normalize_file(raw_path: Path) -> dict:
    raw = json.loads(raw_path.read_text(encoding="utf-8"))

    reviews = None
    reviews_path = raw_path.parent / f"{raw_path.stem}_reviews.json"
    if reviews_path.exists():
        reviews = json.loads(reviews_path.read_text(encoding="utf-8"))

    return normalize(raw, reviews)
