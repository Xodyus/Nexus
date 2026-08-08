import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scraper"))

from normalize import _to_number, normalize  # noqa: E402


class ToNumberTests(unittest.TestCase):
    def test_strips_percent_sign(self):
        self.assertEqual(_to_number("88%"), 88.0)

    def test_handles_none(self):
        self.assertEqual(_to_number(None), 0.0)

    def test_handles_int(self):
        self.assertEqual(_to_number(250), 250.0)

    def test_falls_back_on_garbage(self):
        self.assertEqual(_to_number("n/a", default=-1.0), -1.0)


class NormalizeTests(unittest.TestCase):
    def _raw(self):
        return {
            "slug": "test_movie",
            "score_board": {
                "tomatometerscore": "88",
                "audiencescore": "91",
                "tomatometercount": 250,
                "audiencecount": 5000,
            },
        }

    def test_falls_back_to_tomatometer_without_reviews(self):
        result = normalize(self._raw(), reviews=None)
        self.assertEqual(result["average_critic_score"], 88.0)

    def test_falls_back_when_reviews_have_no_average(self):
        result = normalize(self._raw(), reviews={"average_critic_score": None})
        self.assertEqual(result["average_critic_score"], 88.0)

    def test_uses_average_critic_score_when_present(self):
        result = normalize(self._raw(), reviews={"average_critic_score": 71.5})
        self.assertEqual(result["average_critic_score"], 71.5)
        # tomatometer_score in the output stays the raw RT figure regardless.
        self.assertEqual(result["tomatometer_score"], 88.0)


if __name__ == "__main__":
    unittest.main()
