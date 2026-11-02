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


if __name__ == "__main__":
    unittest.main()
