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


    def test_planner_displays_daily_carbohydrate_fat_and_fibre_totals(self):
        for label in ("Daily carbohydrates", "Daily fat", "Daily fibre"):
            with self.subTest(label=label):
                self.assertIn(label, self.html)
        for field in ("daily.carbs", "daily.fat", "daily.fibre"):
            with self.subTest(field=field):
                self.assertIn(field, self.html)


    def test_planner_displays_exact_budget_gap_or_remaining_amount(self):
        self.assertIn("function budgetDelta()", self.html)
        self.assertIn("budget_for_plan==null?d.budget:d.budget_for_plan", self.html)
        self.assertIn("Budget comparison unavailable", self.html)
        self.assertIn("over budget", self.html)
        self.assertIn("remaining", self.html)
        self.assertIn("Exactly on budget", self.html)


    def test_planner_displays_pack_purchase_cost_per_day_and_planned_meal(self):
        for label in ("Shopping spend per day", "Shopping spend per planned meal"):
            with self.subTest(label=label):
                self.assertIn(label, self.html)
        self.assertIn("estimatedCost/planDays", self.html)
        self.assertIn("estimatedCost/(planDays*planMeals)", self.html)
        self.assertIn("costBreakdownValid", self.html)
        self.assertIn("not the cost of ingredients consumed only", self.html)


    def test_budget_swap_is_opt_in_and_wired_through_the_api(self):
        self.assertIn("Try lower-cost protein swap", self.html)
        self.assertIn("optimize_budget:optimizeBudget===true", self.html)
        self.assertIn("optimize_budget", self.server)
        self.assertIn("optimize_budget') is True", self.server)
        self.assertIn("optimize_budget', 'Budget optimisation selection", (Path(__file__).resolve().parents[1] / "planner.py").read_text(encoding="utf-8"))

    def test_budget_swap_result_explains_savings_and_allergen_check(self):
        self.assertIn("budgetOpt.estimated_savings", self.html)
        self.assertIn("allergen information before use", self.html)


    def test_budget_swap_shows_before_and_after_full_pack_costs(self):
        self.assertIn("budgetOpt.original_estimated_total", self.html)
        self.assertIn("budgetOpt.optimized_estimated_total", self.html)
        self.assertIn("Before R", self.html)
        self.assertIn("after R", self.html)


    def test_ingredient_exclusion_controls_are_wired_to_planner_api(self):
        for element_id in (
            "plallergenPeanut", "plallergenMilk", "plallergenEgg",
            "plallergenSoy", "plallergenFish",
        ):
            with self.subTest(element_id=element_id):
                self.assertIn('id="' + element_id + '"', self.html)
        self.assertIn("excluded_allergens:excludedAllergens", self.html)
        self.assertIn("apply_ingredient_exclusions(result", self.server)
        self.assertLess(
            self.server.index("apply_ingredient_exclusions(result"),
            self.server.index("optimize_budget_plan(result)"),
        )
        self.assertIn("not an allergy safety guarantee", self.html)
        self.assertIn("Verify product labels and cross-contact", self.html)


    def test_planner_can_download_a_safe_csv_shopping_list(self):
        self.assertIn("function downloadShoppingList()", self.html)
        self.assertIn('onclick="downloadShoppingList()"', self.html)
        self.assertIn('"Required (g)"', self.html)
        self.assertIn('"Estimated pack cost (ZAR)"', self.html)
        self.assertIn("text/csv;charset=utf-8", self.html)
        self.assertIn("plannerShoppingExport=null;", self.html)
        self.assertIn("items:Array.isArray(shop)", self.html)
        self.assertIn(r"if(/^[\s]*[=+\-@]/.test(cell))", self.html)
        self.assertIn('cell.replace(/"/g,\'""\')', self.html)
        self.assertIn('if(value==null||value==="")return ""', self.html)


if __name__ == "__main__":
    unittest.main()
