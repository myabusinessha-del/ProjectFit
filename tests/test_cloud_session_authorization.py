import unittest
from datetime import datetime, timedelta, timezone

from cloud_service import CloudAccountService
from db import DB


class FakeAuth:
    def __init__(self, refresh_result=None, error=None):
        self.refresh_result = refresh_result
        self.error = error
        self.refresh_calls = []

    def refresh(self, refresh_token):
        self.refresh_calls.append(refresh_token)
        if self.error:
            raise self.error
        return self.refresh_result


class CloudSessionAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.db = DB(":memory:")
        self.service = CloudAccountService.__new__(CloudAccountService)
        self.service.db = self.db
        self.service.auth = FakeAuth()

    def tearDown(self):
        self.db.close()

    def add_session(self, expires_at, refresh_token=None):
        cookie = "test-session-cookie"
        self.db.q(
            "INSERT INTO cloud_sessions(token_hash,user_id,access_token,refresh_token,created_at,expires_at) "
            "VALUES(?,?,?,?,?,?)",
            (
                self.service._hash(cookie),
                "user-123",
                "old-access-token",
                refresh_token,
                datetime.now(timezone.utc).isoformat(),
                expires_at.isoformat() if expires_at else None,
            ),
        )
        self.db.commit()
        return cookie

    def test_active_session_authenticates(self):
        cookie = self.add_session(datetime.now(timezone.utc) + timedelta(minutes=10))

        self.assertEqual(self.service.user_id(cookie), "user-123")
        self.assertEqual(self.service.access(cookie), "old-access-token")

    def test_expired_session_without_refresh_token_is_rejected(self):
        cookie = self.add_session(datetime.now(timezone.utc) - timedelta(minutes=1))

        self.assertIsNone(self.service.user_id(cookie))

    def test_expired_session_refreshes_before_authenticating(self):
        cookie = self.add_session(
            datetime.now(timezone.utc) - timedelta(minutes=1),
            refresh_token="valid-refresh-token",
        )
        self.service.auth = FakeAuth(
            refresh_result={
                "access_token": "new-access-token",
                "refresh_token": "rotated-refresh-token",
                "expires_in": 3600,
            }
        )

        self.assertEqual(self.service.user_id(cookie), "user-123")
        self.assertEqual(self.service.auth.refresh_calls, ["valid-refresh-token"])
        row = self.service.token_from_cookie(cookie)
        self.assertEqual(row["access_token"], "new-access-token")
        self.assertEqual(row["refresh_token"], "rotated-refresh-token")

    def test_expired_session_with_failed_refresh_is_rejected(self):
        cookie = self.add_session(
            datetime.now(timezone.utc) - timedelta(minutes=1),
            refresh_token="revoked-refresh-token",
        )
        self.service.auth = FakeAuth(error=ValueError("refresh rejected"))

        self.assertIsNone(self.service.user_id(cookie))


if __name__ == "__main__":
    unittest.main()
