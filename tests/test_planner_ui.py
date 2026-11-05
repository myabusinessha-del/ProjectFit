import unittest
from pathlib import Path


class PlannerUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        repository_root = Path(__file__).resolve().parents[1]
        cls.html = (repository_root / "index.html").read_text(encoding="utf-8")

    def test_vegetarian_meal_option_is_visible(self):
        self.assertIn('id="plvegetarian"', self.html)
        self.assertIn("Vegetarian meals", self.html)

    def test_planner_request_sends_vegetarian_selection(self):
        self.assertIn('vegetarian:$("plvegetarian").checked', self.html)


if __name__ == "__main__":
    unittest.main()
