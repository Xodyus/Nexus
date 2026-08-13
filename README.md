# Nexus

A "realistic score" engine for movies. It pulls a movie's Tomatometer and
Audience Score from Rotten Tomatoes, corrects for low review counts and
critic/audience controversy, and blends them into a single score meant to be
harder to game than the headline numbers alone.

The idea started from the observation that a small number of early reviews
(or a review-bombed audience score) can produce a misleading Tomatometer —
see [notes.txt](notes.txt) for the full writeup and roadmap.

## Architecture

```
Nexus/
  scraper/     Python: fetches and caches RT movie/review pages, normalizes
               them into the engine's input schema
  engine/      C++: reads the normalized JSON, computes the realistic score
               (score_engine.cpp), writes JSON output
  server/      Flask API (server/app.py) that ties the two together and
               serves the frontend
  frontend/    Static dashboard (index.html / style.css / app.js) — search
               a movie, see Tomatometer / Audience / Realistic score tiles
  data/        raw/, normalized/, scores/ — cached scrape and engine output
               (gitignored, regenerated on demand)
  tests/       Python tests (pytest) against the scraper and normalizer
```

Python handles the messy, change-often part (HTTP + HTML parsing); the C++
engine owns the scoring math as a small, fast, testable unit with a stable
JSON in/out contract.

### Scoring algorithm (v1)

1. **Bayesian shrinkage** — each raw score is pulled toward a neutral prior
   in proportion to how few reviews back it up.
2. **Controversy penalty** — the bigger the gap between the shrunk
   Tomatometer and Audience Score, the more points get deducted.
3. **Final blend** — a 50/50 weighted average of the two shrunk scores,
   minus the controversy penalty, clamped to `[0, 100]`.

## Getting started

```bash
# Python deps
pip install -r scraper/requirements.txt

# Build the C++ engine
cmake -S engine -B engine/build
cmake --build engine/build --config Release

# Run the server
python server/app.py
```

Open `http://localhost:5000`, search for a movie, and you should see three
score tiles.

A prebuilt `score_engine` binary is also attached to
[GitHub releases](../../releases).

## Tests

```bash
# Python
pytest

# C++ (after building engine/build with tests enabled)
ctest --test-dir engine/build
```

## Status

Early scaffold — see [notes.txt](notes.txt) for the current state of each
component and the prioritized next steps (numeric critic scores instead of
fresh/rotten, title search, caching freshness, etc).
