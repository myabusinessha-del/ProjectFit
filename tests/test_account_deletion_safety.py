import unittest

from cloud_service import CloudAccountService
from db import DB


class FakeCloud:
    def __init__(self):
        self.delete_calls = []

    def delete_all(self, user_id, token):
        self.delete_calls.append((user_id, token))


class TestableCloudAccountService(CloudAccountService):
    def token_from_cookie(self, cookie):
        return {"user_id": "user-123"}

    def access(self, cookie):
        return "valid-access-token"


class AccountDeletionSafetyTests(unittest.TestCase):
    def setUp(self):
        self.db = DB(":memory:")
        self.db.q(
            "INSERT INTO users(id, display_name, timezone, created_at) VALUES(?,?,?,?)",
            ("user-123", "Saved profile", "Africa/Johannesburg", "2026-11-06T00:00:00+00:00"),
        )
        self.db.commit()
        self.cloud = FakeCloud()
        self.service = TestableCloudAccountService.__new__(TestableCloudAccountService)
        self.service.db = self.db
        self.service.cloud = self.cloud

    def tearDown(self):
        self.db.close()

    def test_incomplete_account_deletion_fails_before_any_data_is_removed(self):
        with self.assertRaisesRegex(ValueError, "No account data has been changed"):
            self.service.delete_account("test-cookie")

        self.assertEqual(self.cloud.delete_calls, [])
        row = self.db.q(
            "SELECT display_name FROM users WHERE id=?",
            ("user-123",),
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["display_name"], "Saved profile")


if __name__ == "__main__":
    unittest.main()
