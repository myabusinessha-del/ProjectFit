import unittest

from cloud_service import CloudAccountService
from cloud_sync import table_rows
from db import DB


class FakeCloud:
    def __init__(self, records):
        self.records = [dict(record, version=record.get("version", 3)) for record in records]
        self.upsert_calls = []
        self.delete_calls = []

    def pull(self, user_id, token):
        return list(self.records)

    def upsert(self, user_id, token, record, base_version):
        self.upsert_calls.append((record, base_version))
        return {"id": record["id"], "version": 4}, None

    def _req(self, path, method="GET", body=None, token=None, prefer="return=representation"):
        if method == "DELETE":
            self.delete_calls.append(path)
            record_id = path.split("id=eq.", 1)[1].split("&", 1)[0]
            self.records = [record for record in self.records if record["id"] != record_id]
        return {}


class TestableCloudAccountService(CloudAccountService):
    def token_from_cookie(self, cookie):
        return {"user_id": "user-123"}

    def access(self, cookie):
        return "test-access-token"


class FreshDeviceSyncSafetyTests(unittest.TestCase):
    def setUp(self):
        self.local = DB(":memory:")
        self.remote = DB(":memory:")
        self._seed_user(self.local, "Local bootstrap profile", 2400, 180)
        self._seed_user(self.remote, "Saved cloud profile", 2150, 155)

        records = table_rows(self.remote, "user-123")
        for record in records:
            record["version"] = 3

        self.cloud = FakeCloud(records)
        self.service = TestableCloudAccountService.__new__(TestableCloudAccountService)
        self.service.db = self.local
        self.service.cloud = self.cloud

    def tearDown(self):
        self.local.close()
        self.remote.close()

    @staticmethod
    def _seed_user(db, display_name, calories, protein):
        now = "2026-11-06T00:00:00+00:00"
        db.q(
            "INSERT INTO users(id, display_name, age, height_cm, sex, timezone, created_at) "
            "VALUES(?,?,?,?,?,?,?)",
            ("user-123", display_name, 32, 178, "Male", "Africa/Johannesburg", now),
        )
        db.q(
            "INSERT INTO goals(user_id, objective, target_weight, target_body_fat, "
            "training_frequency, calorie_target, protein_target) VALUES(?,?,?,?,?,?,?)",
            ("user-123", "lose", 78, 18, 4, calories, protein),
        )
        db.q(
            "INSERT INTO privacy_settings(user_id, consent, sharing_enabled, "
            "deletion_requested, updated_at) VALUES(?,?,?,?,?)",
            ("user-123", 1, 0, 0, now),
        )
        db.commit()

    def test_fresh_device_adopts_existing_cloud_records_without_uploading_defaults(self):
        result = self.service.sync("test-cookie")

        self.assertTrue(result["ok"])
        self.assertEqual(result["uploaded"], 0)
        self.assertEqual(self.cloud.upsert_calls, [])

        profile = self.local.q(
            "SELECT display_name, age, height_cm FROM users WHERE id=?",
            ("user-123",),
        ).fetchone()
        goal = self.local.q(
            "SELECT calorie_target, protein_target FROM goals WHERE user_id=?",
            ("user-123",),
        ).fetchone()

        self.assertEqual(profile["display_name"], "Saved cloud profile")
        self.assertEqual(profile["age"], 32)
        self.assertEqual(profile["height_cm"], 178)
        self.assertEqual(goal["calorie_target"], 2150)
        self.assertEqual(goal["protein_target"], 155)

    def test_adopted_cloud_versions_are_recorded_for_future_conflict_checks(self):
        self.service.sync("test-cookie")

        rows = self.local.q(
            "SELECT server_version FROM cloud_record_state"
        ).fetchall()

        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row["server_version"] == 3 for row in rows))


if __name__ == "__main__":
    unittest.main()
