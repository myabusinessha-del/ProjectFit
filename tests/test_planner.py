import unittest

from planner import (
    apply_ingredient_exclusions,
    calculate_targets,
    plan_for,
    validate_macro_target_payload,
    validate_plan_request_payload,
)



class PlannerApiPayloadValidationTests(unittest.TestCase):
    def test_planner_api_rejects_boolean_numeric_values_before_coercion(self):
        for field in ("calories", "protein", "budget"):
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, "valid number"):
                    validate_plan_request_payload({field: True})

    def test_planner_api_rejects_fractional_boolean_and_out_of_range_days(self):
        for days in (True, False, 0, 1.5, 15, float("inf"), float("nan"), "seven"):
            with self.subTest(days=days):
                with self.assertRaises(ValueError):
                    validate_plan_request_payload({"days": days})

    def test_planner_api_accepts_valid_values_and_omitted_defaults(self):
        validate_plan_request_payload({
            "calories": 2200,
            "protein": 150,
            "budget": 0,
            "days": "7",
        })
        validate_plan_request_payload({})

    def test_planner_api_rejects_invalid_meal_counts_before_service_fallback(self):
        for value in (True, False, 2, 6, 3.5, float('inf'), float('nan'), 'not-a-number', '2', '6'):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, 'Meals per day'):
                    validate_plan_request_payload({'meals_per_day': value})

    def test_planner_api_accepts_supported_meal_counts_and_omitted_defaults(self):
        for value in (3, 4, 5, 3.0, '4', '5'):
            with self.subTest(value=value):
                validate_plan_request_payload({'meals_per_day': value})
        validate_plan_request_payload({})
        validate_plan_request_payload({'meals_per_day': None})
        validate_plan_request_payload({'meals_per_day': ''})

    def test_planner_api_rejects_non_boolean_vegan_selection(self):
        for value in ("true", 1, None):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "Vegan selection"):
                    validate_plan_request_payload({"vegan": value})

    def test_planner_api_rejects_non_boolean_vegetarian_and_protein_powder_selections(self):
        for field, label in (
            ("vegetarian", "Vegetarian selection"),
            ("use_whey", "Protein powder selection"),
        ):
            for value in ("true", "false", 0, 1, None):
                with self.subTest(field=field, value=value):
                    with self.assertRaisesRegex(ValueError, label):
                        validate_plan_request_payload({field: value})

    def test_planner_api_accepts_boolean_dietary_and_protein_powder_selections(self):
        for vegetarian in (True, False):
            for vegan in (True, False):
                for use_whey in (True, False):
                    with self.subTest(vegetarian=vegetarian, vegan=vegan, use_whey=use_whey):
                        validate_plan_request_payload({
                            "vegetarian": vegetarian,
                            "vegan": vegan,
                            "use_whey": use_whey,
                        })

    def test_macro_api_rejects_invalid_age_height_and_weight_before_coercion(self):
        for field in ("age", "height_cm", "weight_kg"):
            for value in (True, False, 0, -1, float("inf"), float("nan"), "invalid"):
                with self.subTest(field=field, value=value):
                    with self.assertRaises(ValueError):
                        validate_macro_target_payload({field: value})

    def test_macro_api_allows_omitted_profile_values(self):
        validate_macro_target_payload({})
        validate_macro_target_payload({"age": None, "height_cm": "", "weight_kg": None})


    def test_planner_api_accepts_supported_ingredient_exclusions(self):
        validate_plan_request_payload({
            "excluded_allergens": ["peanut", "milk", "egg", "soy", "fish"]
        })

    def test_planner_api_rejects_malformed_or_unknown_ingredient_exclusions(self):
        for value in ("peanut", None, {}, ["unknown"], ["peanut", True]):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "Ingredient exclusions"):
                    validate_plan_request_payload({"excluded_allergens": value})


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


class VeganMealPlanTests(unittest.TestCase):
    def test_vegan_plans_exclude_animal_derived_foods_for_all_meal_counts(self):
        animal_foods = {
            "Eggs", "Chicken breast", "Lean beef mince", "Tuna",
            "Low-fat milk", "Whey protein",
        }
        for count in (3, 4, 5):
            for use_powder in (False, True):
                with self.subTest(count=count, use_powder=use_powder):
                    result = plan_for(
                        2400, 150, 1000, meals_per_day=count, days=7,
                        vegetarian=True, use_whey=use_powder, vegan=True,
                    )
                    foods = {
                        item["food"]
                        for meal in result["daily"]
                        for item in meal["items"]
                    }
                    self.assertFalse(animal_foods.intersection(foods))
                    self.assertIn("Firm tofu", foods)
                    self.assertIn("Dry lentils", foods)
                    self.assertIn("Soy milk", foods)
                    self.assertEqual(len(result["daily"]), count)
                    if use_powder:
                        self.assertIn("Pea protein", foods)

    def test_vegan_five_meal_plan_uses_chickpeas_when_powder_is_disabled(self):
        result = plan_for(
            2200, 100, 500, meals_per_day=5, days=5,
            use_whey=False, vegan=True,
        )
        self.assertEqual(result["daily"][2]["name"], "Roasted chickpea snack")
        foods = {
            item["food"]
            for meal in result["daily"]
            for item in meal["items"]
        }
        self.assertIn("Dry chickpeas", foods)
        self.assertNotIn("Whey protein", foods)


class PlannerInputValidationTests(unittest.TestCase):
    def test_rejects_days_outside_supported_range(self):
        for days in (0, -1, 15):
            with self.subTest(days=days):
                with self.assertRaisesRegex(ValueError, "between 1 and 14"):
                    plan_for(2200, 100, 500, days=days)

    def test_rejects_non_integer_days(self):
        for days in (None, "seven", 1.5, 7.25, True, False, float("inf"), float("nan")):
            with self.subTest(days=days):
                with self.assertRaisesRegex(ValueError, "whole number"):
                    plan_for(2200, 100, 500, days=days)

    def test_accepts_whole_number_days_as_integer_float_or_numeric_string(self):
        for days in (1, 7.0, "14"):
            with self.subTest(days=days):
                result = plan_for(2200, 100, 500, days=days)
                self.assertEqual(result["days"], int(days))

    def test_rejects_invalid_meal_counts_in_core_planner(self):
        invalid_counts = (
            0, 1, 2, 6, "four", 3.5, 4.5, True, False,
            None, float("inf"), float("nan"),
        )
        for count in invalid_counts:
            with self.subTest(count=count):
                with self.assertRaisesRegex(ValueError, "Meals per day must be 3, 4 or 5"):
                    plan_for(2200, 100, 500, meals_per_day=count)

    def test_accepts_only_supported_meal_counts_in_core_planner(self):
        for count in (3, 4, 5, 3.0, "4", "5"):
            with self.subTest(count=count):
                result = plan_for(2200, 100, 500, meals_per_day=count)
                self.assertEqual(len(result["daily"]), int(count))
                self.assertEqual(result["meals_per_day"], int(count))

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

    def test_rejects_non_positive_or_non_finite_calorie_targets(self):
        for calories in (0, -1, float("inf"), float("nan"), "invalid", None):
            with self.subTest(calories=calories):
                with self.assertRaisesRegex(ValueError, "Calorie target"):
                    plan_for(calories, 100, 500)

    def test_rejects_negative_or_non_finite_protein_targets(self):
        for protein in (-1, float("inf"), float("nan"), "invalid", None):
            with self.subTest(protein=protein):
                with self.assertRaisesRegex(ValueError, "Protein target"):
                    plan_for(2200, protein, 500)

    def test_rejects_boolean_calorie_protein_and_budget_inputs(self):
        for calories, protein, budget in (
            (True, 100, 500),
            (2200, True, 500),
            (2200, 100, True),
        ):
            with self.subTest(calories=calories, protein=protein, budget=budget):
                with self.assertRaises(ValueError):
                    plan_for(calories, protein, budget)


class NutritionTargetValidationTests(unittest.TestCase):
    def test_rejects_invalid_age_height_and_weight(self):
        valid = {
            "age": 30,
            "height_cm": 180,
            "weight_kg": 80,
            "sex": "Male",
            "activity": "moderate",
            "goal": "maintain",
        }
        invalid_values = (0, -1, True, False, float("inf"), float("nan"), "invalid", None)
        expected_labels = {"age": "Age", "height_cm": "Height", "weight_kg": "Weight"}
        for field in ("age", "height_cm", "weight_kg"):
            for value in invalid_values:
                with self.subTest(field=field, value=value):
                    inputs = dict(valid)
                    inputs[field] = value
                    with self.assertRaisesRegex(ValueError, expected_labels[field]):
                        calculate_targets(**inputs)

    def test_rejects_unknown_sex_activity_and_goal_instead_of_guessing(self):
        valid = {
            "age": 30,
            "height_cm": 180,
            "weight_kg": 80,
            "sex": "Male",
            "activity": "moderate",
            "goal": "maintain",
        }
        invalid_values = (
            ("sex", "unspecified"),
            ("activity", "extreme"),
            ("goal", "bulk"),
        )
        for field, value in invalid_values:
            with self.subTest(field=field, value=value):
                inputs = dict(valid)
                inputs[field] = value
                with self.assertRaises(ValueError):
                    calculate_targets(**inputs)

    def test_accepts_numeric_strings_and_short_sex_codes(self):
        result = calculate_targets(
            age="30",
            height_cm="180",
            weight_kg="80",
            sex="M",
            activity="moderate",
            goal="maintain",
        )
        self.assertEqual(result["bmr"], 1780)


class PlannerBudgetPeriodTests(unittest.TestCase):
    def test_weekly_budget_is_prorated_to_selected_plan_duration(self):
        for days, expected in ((1, 100.0), (7, 700.0), (14, 1400.0)):
            with self.subTest(days=days):
                result = plan_for(2200, 100, 700, days=days)
                self.assertEqual(result["budget_for_plan"], expected)

    def test_budget_status_uses_the_prorated_plan_budget(self):
        baseline = plan_for(2200, 100, 0, days=14)
        weekly_budget = baseline["estimated_total"] / 2

        at_budget = plan_for(2200, 100, weekly_budget, days=14)
        self.assertEqual(at_budget["budget_for_plan"], baseline["estimated_total"])
        self.assertEqual(at_budget["budget_status"], "WITHIN BUDGET")

        below_budget = plan_for(2200, 100, weekly_budget - 0.01, days=14)
        self.assertEqual(below_budget["budget_status"], "OVER BUDGET")


class PlannerTargetComparisonTests(unittest.TestCase):
    def test_target_comparison_reports_signed_calorie_and_protein_differences(self):
        above = plan_for(1000, 30, 500)
        below = plan_for(4000, 250, 500)

        for result in (above, below):
            comparison = result["target_comparison"]
            for key in ("calories", "protein"):
                with self.subTest(result=result, key=key):
                    target = result["targets"][key]
                    actual = round(result["daily_totals"][key], 1)
                    self.assertEqual(comparison[key]["target"], round(target, 1))
                    self.assertEqual(comparison[key]["actual"], actual)
                    self.assertEqual(
                        comparison[key]["difference"],
                        round(actual - round(target, 1), 1),
                    )

        self.assertGreater(above["target_comparison"]["calories"]["difference"], 0)
        self.assertGreater(above["target_comparison"]["protein"]["difference"], 0)
        self.assertLess(below["target_comparison"]["calories"]["difference"], 0)
        self.assertLess(below["target_comparison"]["protein"]["difference"], 0)


class BudgetOptimizationPayloadValidationTests(unittest.TestCase):
    def test_planner_api_requires_boolean_budget_optimization_flag(self):
        for value in ("true", "false", 0, 1, None):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "Budget optimisation selection"):
                    validate_plan_request_payload({"optimize_budget": value})

    def test_planner_api_accepts_boolean_budget_optimization_flag(self):
        validate_plan_request_payload({"optimize_budget": True})
        validate_plan_request_payload({"optimize_budget": False})
        validate_plan_request_payload({})



class IngredientExclusionTests(unittest.TestCase):
    def test_peanut_exclusion_removes_catalogue_ingredient_and_recalculates_totals(self):
        original = plan_for(2400, 180, 400, meals_per_day=4, days=7)
        original_totals = dict(original["daily_totals"])
        filtered = apply_ingredient_exclusions(original, ["peanut"])

        foods = {
            item["food"]
            for meal in filtered["daily"]
            for item in meal["items"]
        }
        shopping_foods = {item["food"] for item in filtered["shopping"]}
        self.assertNotIn("Peanut butter", foods)
        self.assertNotIn("Peanut butter", shopping_foods)
        self.assertEqual(filtered["excluded_allergens"], ["peanut"])
        self.assertEqual(
            filtered["estimated_total"],
            sum(item["estimated_cost"] for item in filtered["shopping"]),
        )
        for macro in ("calories", "protein", "carbs", "fat", "fibre"):
            with self.subTest(macro=macro):
                self.assertAlmostEqual(
                    filtered["daily_totals"][macro],
                    sum(meal[macro] for meal in filtered["daily"]),
                    places=6,
                )
        self.assertEqual(original["daily_totals"], original_totals)
        self.assertNotIn("excluded_allergens", original)

    def test_milk_exclusion_removes_both_milk_and_whey(self):
        original = plan_for(2400, 180, 400, use_whey=True)
        filtered = apply_ingredient_exclusions(original, ["milk"])
        foods = {
            item["food"]
            for meal in filtered["daily"]
            for item in meal["items"]
        }
        self.assertNotIn("Low-fat milk", foods)
        self.assertNotIn("Whey protein", foods)
        self.assertNotIn("Low-fat milk", {item["food"] for item in filtered["shopping"]})
        self.assertNotIn("Whey protein", {item["food"] for item in filtered["shopping"]})

    def test_soy_exclusion_removes_soy_milk_and_tofu_from_vegan_plan(self):
        original = plan_for(2400, 150, 1000, vegan=True)
        filtered = apply_ingredient_exclusions(original, ["soy"])
        foods = {
            item["food"]
            for meal in filtered["daily"]
            for item in meal["items"]
        }
        self.assertNotIn("Soy milk", foods)
        self.assertNotIn("Firm tofu", foods)
        self.assertEqual(len(filtered["daily"]), len(original["daily"]))

    def test_optimizer_does_not_reintroduce_dairy_after_milk_exclusion(self):
        from budget_optimizer import optimize_budget_plan

        original = plan_for(2400, 180, 400, use_whey=True)
        filtered = apply_ingredient_exclusions(original, ["milk"])
        optimized = optimize_budget_plan(filtered)
        foods = {
            item["food"]
            for meal in optimized["daily"]
            for item in meal["items"]
        }
        self.assertNotIn("Low-fat milk", foods)
        self.assertNotIn("Whey protein", foods)
        self.assertFalse(optimized["budget_optimization"]["applied"])

    def test_unknown_catalogue_items_fail_closed(self):
        from copy import deepcopy

        plan = deepcopy(plan_for(2400, 180, 400))
        plan["daily"][0]["items"][0]["food"] = "Unlisted ingredient"
        with self.assertRaisesRegex(ValueError, "outside the current food catalogue"):
            apply_ingredient_exclusions(plan, ["peanut"])

    def test_unknown_allergen_selection_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "supported ingredient exclusions"):
            apply_ingredient_exclusions(plan_for(2400, 180, 400), ["tree_nut"])


if __name__ == "__main__":
    unittest.main()
