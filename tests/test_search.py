import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scraper"))

from search import guess_slug  # noqa: E402


class GuessSlugTests(unittest.TestCase):
    def test_lowercases_and_joins_with_underscores(self):
        self.assertEqual(guess_slug("Dune: Part Two"), "dune_part_two")

    def test_strips_punctuation(self):
        self.assertEqual(guess_slug("Spider-Man: No Way Home!"), "spiderman_no_way_home")

    def test_appends_year_on_request(self):
        self.assertEqual(guess_slug("Dune", year=2021), "dune_2021")


if __name__ == "__main__":
    unittest.main()
