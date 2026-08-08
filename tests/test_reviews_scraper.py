"""Tests for reviews_scraper.py against a saved HTML fixture - no network
access. See reviews_scraper.py's module docstring on why the fixture is
synthetic rather than a captured live page."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scraper"))

from reviews_scraper import ScrapeError, _score_to_100, extract_reviews  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class ScoreTo100Tests(unittest.TestCase):
    def test_fraction(self):
        self.assertEqual(_score_to_100("4/5"), 80.0)

    def test_letter_grade(self):
        self.assertEqual(_score_to_100("B+"), 87.0)

    def test_unparseable_returns_none(self):
        self.assertIsNone(_score_to_100("three stars"))


class ExtractReviewsTests(unittest.TestCase):
    def test_averages_scored_reviews_only(self):
        html = (FIXTURES / "reviews_page.html").read_text(encoding="utf-8")
        data = extract_reviews(html, "test_movie")

        self.assertEqual(data["scored_review_count"], 3)
        self.assertAlmostEqual(data["average_critic_score"], (80 + 67 + 60) / 3)

    def test_raises_when_no_scores_found(self):
        with self.assertRaises(ScrapeError):
            extract_reviews("<html><body>no reviews here</body></html>", "test_movie")


if __name__ == "__main__":
    unittest.main()
