import logging


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
