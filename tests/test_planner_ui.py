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


    def test_planner_uses_profile_based_macro_targets_before_generating_meals(self):
        macro_request = self.html.index('api("/api/macro-targets"')
        planner_request = self.html.index('api("/api/planner"', macro_request)
        self.assertLess(macro_request, planner_request)
        self.assertIn("weight_kg:weight", self.html)
        self.assertIn("goal:goal", self.html)
        self.assertIn("activity:activity", self.html)
        self.assertIn("calories:targets.calories", self.html)
        self.assertIn("protein:targets.protein", self.html)

    def test_profile_allows_sex_selection_for_calorie_calculation(self):
        self.assertIn('id="psex"', self.html)
        self.assertIn('sex:$("psex").value', self.html)

    def test_planner_requires_current_weight_and_profile_demographics(self):
        self.assertIn('id="plweight"', self.html)
        self.assertIn("Enter your current weight", self.html)
        self.assertIn("Complete your age, height and sex in Profile", self.html)


if __name__ == "__main__":
    unittest.main()
