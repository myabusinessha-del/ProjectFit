import unittest

from api_errors import respond_with_internal_error


class InternalApiErrorTests(unittest.TestCase):
    def test_internal_details_are_logged_but_not_returned(self):
        response = {}

        def json_response(payload, status):
            response["payload"] = payload
            response["status"] = status
            return status

        try:
            raise RuntimeError("private database host and connection details")
        except RuntimeError as error:
            with self.assertLogs(level="ERROR") as captured:
                result = respond_with_internal_error(json_response, error)

        self.assertEqual(result, 500)
        self.assertEqual(response["status"], 500)
        self.assertEqual(
            response["payload"]["error"],
            "An unexpected server error occurred. Please try again.",
        )
        self.assertNotIn("private database host", str(response["payload"]))
        self.assertIn("private database host", "\n".join(captured.output))


if __name__ == "__main__":
    unittest.main()
