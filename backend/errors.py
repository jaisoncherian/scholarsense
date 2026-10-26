"""Uniform error envelope: {"error": {"code", "message", "details"}}."""
import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

log = logging.getLogger("scholarsense")

_HTTP_CODES = {
    400: "bad_request",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    415: "unsupported_media_type",
    422: "unprocessable",
    500: "internal_error",
}


class ApiError(Exception):
    def __init__(self, status, code, message, details=None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details


def error_response(status, code, message, details=None):
    resp = jsonify({"error": {"code": code, "message": message, "details": details}})
    resp.status_code = status
    return resp


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def _api_error(err):
        return error_response(err.status, err.code, err.message, err.details)

    @app.errorhandler(HTTPException)
    def _http_error(err):
        status = err.code or 500
        if status == 413:
            limit = app.config.get("MAX_UPLOAD_MB")
            return error_response(
                413, "file_too_large", f"The uploaded file exceeds the {limit} MB limit.",
                {"max_mb": limit},
            )
        return error_response(status, _HTTP_CODES.get(status, "http_error"), err.description or err.name)

    @app.errorhandler(Exception)
    def _unhandled(err):
        # Log the exception type and traceback only; never row contents.
        log.exception("Unhandled error: %s", type(err).__name__)
        return error_response(500, "internal_error", "An unexpected server error occurred.")
