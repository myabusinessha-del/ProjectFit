import unittest

from planner import plan_for


class MealCountTests(unittest.TestCase):
    def test_three_four_five_meal_options_return_requested_count(self):
        for count in (3, 4, 5):
            with self.subTest(count=count):
                result = plan_for(2400, 150, 400, meals_per_day=count, days=7)
                self.assertEqual(result["meals_per_day"], count)
                self.assertEqual(len(result["daily"]), count)

    def test_three_and_five_meals_preserve_daily_nutrition_and_shopping(self):
        four = plan_for(2400, 220, 400, meals_per_day=4, days=7)
        expected_shopping = {
            item["food"]: item["required_g"] for item in four["shopping"]
        }

        for count in (3, 5):
            result = plan_for(2400, 220, 400, meals_per_day=count, days=7)
            for macro in ("calories", "protein", "carbs", "fat", "fibre"):
                with self.subTest(count=count, macro=macro):
                    self.assertAlmostEqual(
                        result["daily_totals"][macro],
                        four["daily_totals"][macro],
                        places=6,
                    )
            self.assertEqual(
                {item["food"]: item["required_g"] for item in result["shopping"]},
                expected_shopping,
            )

    def test_five_meals_split_snack_without_whey_for_vegetarian_plan(self):
        result = plan_for(
            2200, 100, 500, meals_per_day=5, days=5,
            vegetarian=True, use_whey=False,
        )
        self.assertEqual(len(result["daily"]), 5)
        self.assertEqual(result["daily"][2]["name"], "Egg and peanut snack")
        self.assertEqual(result["daily"][3]["name"], "Banana snack")

    def test_invalid_meal_count_falls_back_to_four(self):
        for value in (None, 2, 6, "not-a-number"):
            with self.subTest(value=value):
                result = plan_for(2200, 100, 500, meals_per_day=value)
                self.assertEqual(result["meals_per_day"], 4)

    def test_vegetarian_lunch_and_dinner_use_their_own_meal_categories(self):
        for count in (3, 4, 5):
            for use_whey in (False, True):
                with self.subTest(count=count, use_whey=use_whey):
                    result = plan_for(
                        2400, 150, 1000, meals_per_day=count,
                        vegetarian=True, use_whey=use_whey,
                    )
                    self.assertEqual(result["daily"][1]["meal"], "Lunch")
                    self.assertEqual(result["daily"][1]["name"], "Egg rice bowl")
                    self.assertEqual(result["daily"][-1]["meal"], "Dinner")
                    self.assertEqual(result["daily"][-1]["name"], "Egg and potato bowl")

    def test_vegetarian_protein_adjustment_never_adds_meat_or_fish(self):
        for count in (3, 4, 5):
            for use_whey in (False, True):
                with self.subTest(count=count, use_whey=use_whey):
                    result = plan_for(
                        2400, 220, 1000, meals_per_day=count,
                        vegetarian=True, use_whey=use_whey,
                    )
                    foods = {
                        item["food"]
                        for meal in result["daily"]
                        for item in meal["items"]
                    }
                    self.assertNotIn("Chicken breast", foods)
                    self.assertNotIn("Lean beef mince", foods)
                    self.assertNotIn("Tuna", foods)
                    self.assertIn("Eggs", foods)


class PlannerInputValidationTests(unittest.TestCase):
    def test_rejects_days_outside_supported_range(self):
        for days in (0, -1, 15):
            with self.subTest(days=days):
                with self.assertRaisesRegex(ValueError, "between 1 and 14"):
                    plan_for(2200, 100, 500, days=days)

    def test_rejects_non_integer_days(self):
        for days in (None, "seven"):
            with self.subTest(days=days):
                with self.assertRaisesRegex(ValueError, "whole number"):
                    plan_for(2200, 100, 500, days=days)

    def test_rejects_negative_or_non_finite_budget(self):
        for budget in (-1, float("inf"), float("nan")):
            with self.subTest(budget=budget):
                with self.assertRaisesRegex(ValueError, "non-negative"):
                    plan_for(2200, 100, budget)

    def test_accepts_zero_budget_and_supported_day_boundaries(self):
        for days in (1, 14):
            with self.subTest(days=days):
                result = plan_for(2200, 100, 0, days=days)
                self.assertEqual(result["days"], days)
                self.assertEqual(result["budget"], 0.0)


if __name__ == "__main__":
    unittest.main()