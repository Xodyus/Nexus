"""Tests for rt_scraper.py's extract_raw_data() against saved HTML
fixtures - no network access. These check the parsing contract against a
known input shape, not RT's actual current live markup (which can't be
verified from this environment - see rt_scraper.py's module docstring)."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scraper"))

from rt_scraper import ScrapeError, extract_raw_data  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class ExtractRawDataTests(unittest.TestCase):
    def test_parses_media_scorecard_json(self):
        html = (FIXTURES / "media_scorecard.html").read_text(encoding="utf-8")
        data = extract_raw_data(html, "test_movie")

        board = data["score_board"]
        self.assertEqual(board["tomatometerscore"], 88)
        self.assertEqual(board["audiencescore"], 91)
        self.assertEqual(board["tomatometercount"], 250)
        self.assertEqual(board["audiencecount"], 5000)
        self.assertTrue(board["certified"])
        self.assertEqual(data["next_data"]["name"], "Test Movie")

    def test_raises_when_markup_missing(self):
        html = (FIXTURES / "no_score_data.html").read_text(encoding="utf-8")
        with self.assertRaises(ScrapeError):
            extract_raw_data(html, "test_movie")


if __name__ == "__main__":
    unittest.main()
