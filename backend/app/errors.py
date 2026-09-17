from enum import StrEnum


class ErrorCode(StrEnum):
    CONNECTOR_UNAVAILABLE = "CONNECTOR_UNAVAILABLE"
    CONNECTOR_DISABLED = "CONNECTOR_DISABLED"
    TIMEOUT = "TIMEOUT"
    PROVIDER_5XX = "PROVIDER_5XX"
    RATE_LIMITED = "RATE_LIMITED"
    AUTH_FAILED = "AUTH_FAILED"
    INVALID_REQUEST = "INVALID_REQUEST"
    NOT_FOUND = "NOT_FOUND"
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"
    UNSUPPORTED_OPERATION = "UNSUPPORTED_OPERATION"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    INVALID_ARGUMENTS = "INVALID_ARGUMENTS"
    INVALID_STATE = "INVALID_STATE"
    INTERNAL = "INTERNAL"


RETRYABLE_CODES = frozenset({ErrorCode.TIMEOUT, ErrorCode.PROVIDER_5XX, ErrorCode.RATE_LIMITED})

# Failures that mean the whole connector is unusable for this run, not just one call.
CONNECTOR_LEVEL_CODES = frozenset(
    {ErrorCode.CONNECTOR_UNAVAILABLE, ErrorCode.CONNECTOR_DISABLED, ErrorCode.AUTH_FAILED}
)


def is_retryable(code: ErrorCode | str) -> bool:
    return ErrorCode(code) in RETRYABLE_CODES


class ProviderError(Exception):
    """A classified failure from an external provider (real or demo)."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        status_code: int | None = None,
        ambiguous: bool = False,
    ):
        super().__init__(message)
        self.code = ErrorCode(code)
        self.message = message
        self.status_code = status_code
        # True when a write may have been applied by the provider despite the error.
        self.ambiguous = ambiguous

    @property
    def retryable(self) -> bool:
        return is_retryable(self.code)

    def to_dict(self) -> dict:
        return {
            "code": self.code.value,
            "message": self.message,
            "retryable": self.retryable,
            "ambiguous": self.ambiguous,
        }


def classify_http_status(status: int) -> ErrorCode:
    if status in (401,):
        return ErrorCode.AUTH_FAILED
    if status == 403:
        return ErrorCode.AUTH_FAILED
    if status == 404:
        return ErrorCode.NOT_FOUND
    if status == 429:
        return ErrorCode.RATE_LIMITED
    if status >= 500:
        return ErrorCode.PROVIDER_5XX
    return ErrorCode.INVALID_REQUEST


class SurgeAPIError(Exception):
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        http_status: int = 400,
        retryable: bool = False,
        investigation_id: str | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.retryable = retryable
        self.investigation_id = investigation_id

    def to_dict(self) -> dict:
        body = {"code": self.code.value, "message": self.message, "retryable": self.retryable}
        if self.investigation_id:
            body["investigation_id"] = self.investigation_id
        return {"error": body}
