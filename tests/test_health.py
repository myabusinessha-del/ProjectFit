import os
import sqlite3
import unittest
from unittest.mock import patch

from health import health_status


class Cursor:
    def fetchone(self):
        return (1,)


class HealthyDatabase:
    def __init__(self):
        self.query = None

    def q(self, sql):
        self.query = sql
        return Cursor()


class UnavailableDatabase:
    def q(self, sql):
        raise RuntimeError("internal connection detail must not be exposed")


class SQLiteDatabase:
    """Small adapter matching the application's DB.q interface."""

    def __init__(self):
        self.connection = sqlite3.connect(":memory:")

    def q(self, sql):
        return self.connection.execute(sql)

    def close(self):
        self.connection.close()


class HealthStatusTests(unittest.TestCase):
    def test_reports_ready_when_database_query_succeeds(self):
        database = HealthyDatabase()
        payload, status = health_status(database)

        self.assertEqual(database.query, "SELECT 1")
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["database"], "ok")
        self.assertEqual(payload["service"], "ProjectFit")

    def test_reports_unavailable_without_leaking_database_error(self):
        payload, status = health_status(UnavailableDatabase())

        self.assertEqual(status, 503)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["database"], "unavailable")
        self.assertNotIn("internal connection detail", str(payload))

    def test_reports_ready_and_unavailable_with_real_sqlite(self):
        database = SQLiteDatabase()
        payload, status = health_status(database)
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["database"], "ok")

        database.close()
        payload, status = health_status(database)
        self.assertEqual(status, 503)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["database"], "unavailable")

    def test_includes_render_revision_branch_and_service_name(self):
        render_environment = {
            "RENDER_GIT_COMMIT": "38bbacc290a24ee47df66a2cb24ae997f4b7e90f",
            "RENDER_GIT_BRANCH": "main",
            "RENDER_SERVICE_NAME": "projectfit-live",
        }
        with patch.dict(os.environ, render_environment, clear=True):
            payload, status = health_status(HealthyDatabase())

        self.assertEqual(status, 200)
        self.assertEqual(
            payload["deployment"],
            {
                "revision": "38bbacc290a24ee47df66a2cb24ae997f4b7e90f",
                "branch": "main",
                "service_name": "projectfit-live",
            },
        )

    def test_omits_invalid_revision_and_empty_deployment_metadata(self):
        with patch.dict(
            os.environ,
            {
                "RENDER_GIT_COMMIT": "not-a-commit",
                "RENDER_GIT_BRANCH": "",
                "RENDER_SERVICE_NAME": "",
            },
            clear=True,
        ):
            payload, status = health_status(HealthyDatabase())

        self.assertEqual(status, 200)
        self.assertNotIn("deployment", payload)


if __name__ == "__main__":
    unittest.main()
