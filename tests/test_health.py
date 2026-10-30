import unittest

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


if __name__ == "__main__":
    unittest.main()
