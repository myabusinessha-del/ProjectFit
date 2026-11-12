import json
import logging


def parse_json_object(raw_body):
    """Parse an API body and reject valid JSON values that are not objects."""
    payload = json.loads(raw_body or b"{}")
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object.")
    return payload


def respond_with_internal_error(json_response, error):
    """Log an unexpected API failure without exposing its details to clients."""
    logging.error(
        "Unhandled ProjectFit API error",
        exc_info=(type(error), error, error.__traceback__),
    )
    return json_response(
        {"error": "An unexpected server error occurred. Please try again."},
        500,
    )
