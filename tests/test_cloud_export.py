import unittest

from cloud_service import CloudAccountService


class FakeCloud:
    def __init__(self, records):
        self.records = records
        self.pull_calls = []

    def pull(self, user_id, token):
        self.pull_calls.append((user_id, token))
        return self.records


class TestableCloudAccountService(CloudAccountService):
    def token_from_cookie(self, cookie):
        return {"user_id": "user-123"}

    def access(self, cookie):
        return "fresh-access-token"


class CloudExportTests(unittest.TestCase):
    def test_export_reads_the_authenticated_cloud_source_of_truth(self):
        records = [
            {"id": "record-1", "entity": "goals", "payload": {"calorie_target": 2200}, "version": 4}
        ]
        service = TestableCloudAccountService.__new__(TestableCloudAccountService)
        service.cloud = FakeCloud(records)

        exported = service.export_cloud("session-cookie")

        self.assertEqual(exported["user_id"], "user-123")
        self.assertEqual(exported["records"], records)
        self.assertEqual(service.cloud.pull_calls, [("user-123", "fresh-access-token")])


if __name__ == "__main__":
    unittest.main()
