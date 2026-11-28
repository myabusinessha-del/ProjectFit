import unittest

from planner import calculate_targets


class NutritionTargetCalculationTests(unittest.TestCase):
    def test_male_maintenance_targets_use_mifflin_st_jeor_and_moderate_activity(self):
        result = calculate_targets(
            age=30,
            height_cm=180,
            weight_kg=80,
            sex="Male",
            activity="moderate",
            goal="maintain",
        )

        self.assertEqual(result["bmr"], 1780)
        self.assertEqual(result["tdee"], 2759)
        self.assertEqual(result["calories"], 2750)
        self.assertEqual(result["protein"], 130)
        self.assertEqual(result["fat"], 75)
        self.assertEqual(result["carbs"], 390)
        self.assertEqual(result["method"], "Mifflin-St Jeor + activity/goal adjustment; planning estimate")

    def test_female_maintenance_targets_use_female_equation_constant(self):
        result = calculate_targets(
            age=30,
            height_cm=180,
            weight_kg=80,
            sex="Female",
            activity="moderate",
            goal="maintain",
        )

        self.assertEqual(result["bmr"], 1614)
        self.assertEqual(result["tdee"], 2502)
        self.assertEqual(result["calories"], 2500)
        self.assertEqual(result["protein"], 130)
        self.assertEqual(result["fat"], 70)
        self.assertEqual(result["carbs"], 340)

    def test_fat_loss_adjustment_changes_energy_target_without_changing_formula(self):
        result = calculate_targets(
            age=30,
            height_cm=180,
            weight_kg=80,
            sex="Male",
            activity="moderate",
            goal="lose",
        )

        self.assertEqual(result["bmr"], 1780)
        self.assertEqual(result["tdee"], 2759)
        self.assertEqual(result["calories"], 2200)
        self.assertEqual(result["protein"], 160)

    def test_target_macros_are_rounded_to_five_gram_increments(self):
        result = calculate_targets(
            age=27,
            height_cm=172,
            weight_kg=74,
            sex="Female",
            activity="light",
            goal="recomp",
        )

        for key in ("protein", "carbs", "fat"):
            with self.subTest(macro=key):
                self.assertEqual(result[key] % 5, 0)

    def test_fibre_reference_is_included(self):
        result = calculate_targets(
            age=30,
            height_cm=180,
            weight_kg=80,
            sex="Male",
            activity="moderate",
            goal="maintain",
        )

        self.assertEqual(result["fibre"], 30)


if __name__ == "__main__":
    unittest.main()
