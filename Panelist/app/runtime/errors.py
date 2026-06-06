from __future__ import annotations

# Common error codes (see PANELIST_SERVER.md section 16).
PROVIDER_AUTHENTICATION_ERROR = "provider_authentication_error"
PROVIDER_RATE_LIMIT = "provider_rate_limit"
PROVIDER_TIMEOUT = "provider_timeout"
PROVIDER_UNAVAILABLE = "provider_unavailable"
PROVIDER_INVALID_REQUEST = "provider_invalid_request"
PROVIDER_SAFETY_BLOCK = "provider_safety_block"
CONVERSATION_NOT_FOUND = "conversation_not_found"
CONVERSATION_STORE_ERROR = "conversation_store_error"
STREAM_INTERRUPTED = "stream_interrupted"
INTERNAL_ERROR = "internal_error"


class PanelistError(Exception):
    """Normalized error. Provider-specific exceptions are translated into this."""

    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable

    def to_payload(self) -> dict:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "retryable": self.retryable,
            }
        }


# Map error codes to HTTP status codes for the API layer.
ERROR_HTTP_STATUS: dict[str, int] = {
    PROVIDER_AUTHENTICATION_ERROR: 502,
    PROVIDER_RATE_LIMIT: 429,
    PROVIDER_TIMEOUT: 504,
    PROVIDER_UNAVAILABLE: 503,
    PROVIDER_INVALID_REQUEST: 400,
    PROVIDER_SAFETY_BLOCK: 422,
    CONVERSATION_NOT_FOUND: 404,
    CONVERSATION_STORE_ERROR: 500,
    STREAM_INTERRUPTED: 500,
    INTERNAL_ERROR: 500,
}


def http_status_for(code: str) -> int:
    return ERROR_HTTP_STATUS.get(code, 500)
