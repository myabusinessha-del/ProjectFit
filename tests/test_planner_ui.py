import base64
import gzip
import unittest
from pathlib import Path


class PlannerUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        repository_root = Path(__file__).resolve().parents[1]
        cls.html = (repository_root / "index.html").read_text(encoding="utf-8")
        cls.server = (repository_root / "server.py").read_text(encoding="utf-8")
        encoded_service = (repository_root / "service_min.py.gz.b64").read_text(encoding="utf-8")
        cls.service = gzip.decompress(base64.b64decode(encoded_service)).decode("utf-8")


    def test_api_validates_raw_planner_and_macro_inputs_before_service_coercion(self):
        self.assertIn("validate_plan_request_payload(p)", self.server)
        self.assertIn("validate_macro_target_payload(p)", self.server)
        self.assertLess(
            self.server.index("validate_plan_request_payload(p)"),
            self.server.index("routes[path](uid,p)"),
        )
        self.assertLess(
            self.server.index("validate_macro_target_payload(p)"),
            self.server.index("routes[path](uid,p)"),
        )

    def test_vegetarian_meal_option_is_visible(self):
        self.assertIn('id="plvegetarian"', self.html)
        self.assertIn("Vegetarian meals", self.html)

    def test_planner_request_sends_vegetarian_selection(self):
        self.assertIn('vegetarian:$("plvegetarian").checked', self.html)

    def test_vegan_meal_option_and_plant_protein_label_are_visible(self):
        self.assertIn('id="plvegan"', self.html)
        self.assertIn("Vegan meals (overrides vegetarian)", self.html)
        self.assertIn("pea for vegan plans", self.html)

    def test_planner_request_sends_vegan_selection(self):
        self.assertIn("vegan:vegan", self.html)

    def test_service_forwards_vegan_selection_to_planner(self):
        self.assertIn("bool(p.get('vegan'))", self.service)


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


    def test_planner_can_keep_saved_manual_targets(self):
        self.assertIn('id="plcalculate" type="checkbox" checked', self.html)
        self.assertIn("if(!useCalculated)", self.html)
        self.assertIn("saved.calorie_target", self.html)
        self.assertIn("saved.protein_target", self.html)


if __name__ == "__main__":
    unittest.main()
