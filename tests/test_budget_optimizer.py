import unittest

from budget_optimizer import optimize_budget_plan
from planner import apply_additional_macro_targets, calc_food, plan_for


class BudgetOptimizerTests(unittest.TestCase):
    def test_whey_to_pea_swap_reduces_pack_cost_and_preserves_macros(self):
        for meals_per_day in (3, 4, 5):
            with self.subTest(meals_per_day=meals_per_day):
                original = plan_for(
                    2400, 180, 400, meals_per_day=meals_per_day, days=7,
                    use_whey=True,
                )
                optimized = optimize_budget_plan(original)

                self.assertTrue(optimized["budget_optimization"]["applied"])
                self.assertEqual(
                    optimized["budget_optimization"]["estimated_savings"], 130.0
                )
                self.assertLess(optimized["estimated_total"], original["estimated_total"])
                self.assertEqual(
                    optimized["budget_optimization"]["original_estimated_total"],
                    original["estimated_total"],
                )
                self.assertEqual(
                    optimized["budget_optimization"]["optimized_estimated_total"],
                    optimized["estimated_total"],
                )
                self.assertLessEqual(
                    abs(
                        optimized["daily_totals"]["calories"]
                        - original["daily_totals"]["calories"]
                    ) / original["daily_totals"]["calories"],
                    0.02,
                )
                self.assertAlmostEqual(
                    optimized["daily_totals"]["protein"],
                    original["daily_totals"]["protein"],
                    delta=0.5,
                )
                foods = {
                    item["food"]
                    for meal in optimized["daily"]
                    for item in meal["items"]
                }
                self.assertIn("Pea protein", foods)
                self.assertNotIn("Whey protein", foods)
                self.assertEqual(
                    optimized["budget_status"],
                    "WITHIN BUDGET"
                    if optimized["estimated_total"] <= optimized["budget_for_plan"]
                    else "OVER BUDGET",
                )

    def test_optimizer_is_a_noop_when_protein_powder_is_disabled(self):
        original = plan_for(2400, 180, 400, use_whey=False)
        optimized = optimize_budget_plan(original)

        self.assertFalse(optimized["budget_optimization"]["applied"])
        self.assertEqual(optimized["estimated_total"], original["estimated_total"])
        self.assertEqual(optimized["daily"], original["daily"])

    def test_optimizer_is_a_noop_for_vegan_plans_already_using_pea_protein(self):
        original = plan_for(2400, 180, 400, vegan=True, use_whey=True)
        optimized = optimize_budget_plan(original)

        self.assertFalse(optimized["budget_optimization"]["applied"])
        self.assertEqual(optimized["estimated_total"], original["estimated_total"])
        foods = {
            item["food"]
            for meal in optimized["daily"]
            for item in meal["items"]
        }
        self.assertNotIn("Whey protein", foods)

    def test_optimizer_does_not_mutate_original_and_is_idempotent(self):
        original = plan_for(2400, 180, 400)
        original_cost = original["estimated_total"]
        optimized = optimize_budget_plan(original)
        repeated = optimize_budget_plan(optimized)

        self.assertEqual(original["estimated_total"], original_cost)
        self.assertNotIn("budget_optimization", original)
        self.assertEqual(repeated, optimized)


    def test_optimizer_rejects_swap_that_materially_worsens_an_additional_macro_target(self):
        totals = calc_food([('chicken', 600), ('whey', 35)])
        plan = {
            "targets": {
                "calories": totals["calories"],
                "protein": totals["protein"],
            },
            "days": 7,
            "daily": [{
                "meal": "Snack",
                "name": "Chicken and whey",
                "items": [
                    {"food": "Chicken breast", "grams": 600},
                    {"food": "Whey protein", "grams": 35},
                ],
            }],
            "daily_totals": totals,
            "estimated_total": 1000,
            "budget_for_plan": 2000,
        }
        targeted = apply_additional_macro_targets(
            plan, {"carbs": totals["carbs"] + 0.1}
        )

        optimized = optimize_budget_plan(targeted)

        self.assertFalse(optimized["budget_optimization"]["applied"])
        self.assertIn("carbs target", optimized["budget_optimization"]["reason"])
        self.assertEqual(optimized["daily"], targeted["daily"])

    def test_optimizer_refreshes_all_available_target_comparisons(self):
        original = plan_for(2400, 180, 400, days=7)
        targeted = apply_additional_macro_targets(original, {
            "carbs": original["daily_totals"]["carbs"],
            "fat": original["daily_totals"]["fat"],
            "fibre": original["daily_totals"]["fibre"],
        })

        optimized = optimize_budget_plan(targeted)

        self.assertTrue(optimized["budget_optimization"]["applied"])
        for key in ("calories", "protein", "carbs", "fat", "fibre"):
            with self.subTest(nutrient=key):
                comparison = optimized["target_comparison"][key]
                actual = round(optimized["daily_totals"][key], 1)
                self.assertEqual(comparison["actual"], actual)
                self.assertEqual(
                    comparison["difference"],
                    round(actual - comparison["target"], 1),
                )


if __name__ == "__main__":
    unittest.main()
