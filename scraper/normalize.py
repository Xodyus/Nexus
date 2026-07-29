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


def normalize(raw: dict) -> dict:
    board = raw.get("score_board", {})
    return {
        "slug": raw.get("slug", ""),
        "tomatometer_score": _to_number(board.get("tomatometerscore")),
        "audience_score": _to_number(board.get("audiencescore")),
        "critic_review_count": _to_number(board.get("tomatometercount")),
        "audience_review_count": _to_number(board.get("audiencecount")),
    }


def normalize_file(raw_path: Path) -> dict:
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    return normalize(raw)
