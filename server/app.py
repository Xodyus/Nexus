"""Flask API that ties the Python scraper and C++ score engine together.

Flow for GET /api/movie/<slug>:
  1. Serve cached raw scrape from data/raw/<slug>.json if present, else
     scrape it fresh from Rotten Tomatoes.
  2. Normalize the raw payload into the engine's flat schema.
  3. Shell out to the compiled score_engine binary to compute the
     "realistic score".
  4. Return the combined result as JSON for the frontend to render.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, request, send_from_directory

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scraper"))

from rt_scraper import scrape, ScrapeError, DATA_DIR  # noqa: E402
from reviews_scraper import scrape_reviews  # noqa: E402
from normalize import normalize_file  # noqa: E402
from search import search_slug  # noqa: E402

FRONTEND_DIR = ROOT / "frontend"
NORMALIZED_DIR = ROOT / "data" / "normalized"
SCORES_DIR = ROOT / "data" / "scores"
ENGINE_BUILD_DIR = ROOT / "engine" / "build"

app = Flask(__name__, static_folder=None)


def find_engine_binary() -> Optional[Path]:
    """CMake's default generator on Windows (Visual Studio) nests the exe
    under build/Debug or build/Release, while single-config generators
    (Ninja, Makefiles) put it directly in build/ - search for either."""
    if not ENGINE_BUILD_DIR.exists():
        return None
    for name in ("score_engine.exe", "score_engine"):
        matches = list(ENGINE_BUILD_DIR.rglob(name))
        if matches:
            return matches[0]
    return None


@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(FRONTEND_DIR, filename)


@app.route("/api/movie/<slug>")
def movie_score(slug):
    raw_path = DATA_DIR / f"{slug}.json"
    if not raw_path.exists():
        try:
            scrape(slug)
        except ScrapeError as exc:
            return jsonify({"error": str(exc)}), 404

    reviews_path = DATA_DIR / f"{slug}_reviews.json"
    if not reviews_path.exists():
        try:
            scrape_reviews(slug)
        except ScrapeError:
            # Numeric critic scores are a nice-to-have, not required - the
            # realistic score just falls back to the raw tomatometer
            # (see normalize.py) if this page can't be scraped.
            pass

    normalized = normalize_file(raw_path)
    NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)
    SCORES_DIR.mkdir(parents=True, exist_ok=True)
    norm_path = NORMALIZED_DIR / f"{slug}.json"
    norm_path.write_text(json.dumps(normalized, indent=2), encoding="utf-8")
    score_path = SCORES_DIR / f"{slug}.json"

    engine_binary = find_engine_binary()
    if engine_binary is None:
        return jsonify({
            "error": "score engine not built yet. Run the CMake build in "
                     "engine/ first (see notes.txt).",
        }), 500

    result = subprocess.run(
        [str(engine_binary), str(norm_path), str(score_path)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return jsonify({"error": "score engine failed", "detail": result.stderr}), 500

    return jsonify(json.loads(score_path.read_text(encoding="utf-8")))


@app.route("/api/search")
def search():
    title = request.args.get("title", "").strip()
    if not title:
        return jsonify({"error": "missing 'title' query param"}), 400
    return jsonify({"candidates": search_slug(title)})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
