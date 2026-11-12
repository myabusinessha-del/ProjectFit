import unittest
from pathlib import Path

from api_errors import parse_json_object, respond_with_internal_error


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


class JsonObjectRequestBodyTests(unittest.TestCase):
    def test_accepts_object_and_empty_body(self):
        self.assertEqual(parse_json_object(b'{"days":7}'), {"days": 7})
        self.assertEqual(parse_json_object(b""), {})

    def test_rejects_non_object_json_payloads(self):
        for raw_body in (b"[]", b'""', b"123", b"true", b"null"):
            with self.subTest(raw_body=raw_body):
                with self.assertRaisesRegex(ValueError, "JSON object"):
                    parse_json_object(raw_body)

    def test_rejects_malformed_json(self):
        with self.assertRaises(ValueError):
            parse_json_object(b'{"incomplete":')

    def test_post_handler_uses_the_object_parser(self):
        repository_root = Path(__file__).resolve().parents[1]
        server = (repository_root / "server.py").read_text(encoding="utf-8")
        self.assertIn(
            "from api_errors import parse_json_object, respond_with_internal_error",
            server,
        )
        self.assertIn("return parse_json_object(self.rfile.read", server)


if __name__ == "__main__":
    unittest.main()
