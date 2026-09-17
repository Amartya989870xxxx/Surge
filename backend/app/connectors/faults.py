from typing import Literal

from pydantic import BaseModel

from app.errors import ErrorCode, ProviderError

FaultType = Literal[
    "unavailable",
    "error_500",
    "timeout",
    "rate_limit",
    "auth_failure",
    "malformed",
    "timeout_after_commit",
]

FAULT_PRESETS: dict[str, dict] = {
    "slack_unavailable": {
        "description": "Slack API is unreachable for the whole investigation.",
        "faults": [{"target": "slack", "type": "unavailable"}],
    },
    "github_unavailable": {
        "description": "GitHub API is unreachable for the whole investigation.",
        "faults": [{"target": "github", "type": "unavailable"}],
    },
    "sheets_unavailable": {
        "description": "Google Sheets API is unreachable.",
        "faults": [{"target": "sheets", "type": "unavailable"}],
    },
    "github_issue_timeout": {
        "description": "GitHub issue creation times out after GitHub has already created the issue.",
        "faults": [{"target": "github.create_issue", "type": "timeout_after_commit", "times": 1}],
    },
    "github_transient_500": {
        "description": "GitHub deployment listing returns HTTP 503 twice, then recovers.",
        "faults": [{"target": "github.list_deployments", "type": "error_500", "times": 2}],
    },
    "slack_malformed": {
        "description": "Slack search returns a malformed payload.",
        "faults": [{"target": "slack.search_messages", "type": "malformed"}],
    },
}


class Fault(BaseModel):
    target: str
    type: FaultType
    times: int = -1  # -1 = every call


def expand_faults(presets: list[str] | None, explicit: list[dict] | None) -> list[dict]:
    faults: list[dict] = []
    for name in presets or []:
        if name not in FAULT_PRESETS:
            raise ValueError(f"Unknown fault preset '{name}'")
        faults.extend(FAULT_PRESETS[name]["faults"])
    for fault in explicit or []:
        faults.append(Fault.model_validate(fault).model_dump())
    return faults


class FaultInjector:
    """Deterministic, disclosed failure injection for demo connectors."""

    def __init__(self, faults: list[dict] | None = None):
        self._faults = [Fault.model_validate(f) for f in faults or []]

    @property
    def active(self) -> list[dict]:
        return [f.model_dump() for f in self._faults]

    def take(self, app: str, operation: str) -> Fault | None:
        for fault in self._faults:
            if fault.target not in (app, f"{app}.{operation}"):
                continue
            if fault.times == 0:
                continue
            if fault.times > 0:
                fault.times -= 1
            return fault
        return None

    def raise_for(self, fault: Fault, app: str, operation: str) -> None:
        label = f"{app}.{operation}"
        match fault.type:
            case "unavailable":
                raise ProviderError(
                    ErrorCode.CONNECTOR_UNAVAILABLE,
                    f"{app} API unreachable (injected fault)",
                    status_code=503,
                )
            case "error_500":
                raise ProviderError(
                    ErrorCode.PROVIDER_5XX, f"{label} returned HTTP 503 (injected fault)", status_code=503
                )
            case "timeout":
                raise ProviderError(ErrorCode.TIMEOUT, f"{label} timed out (injected fault)")
            case "rate_limit":
                raise ProviderError(
                    ErrorCode.RATE_LIMITED, f"{label} rate limited (injected fault)", status_code=429
                )
            case "auth_failure":
                raise ProviderError(
                    ErrorCode.AUTH_FAILED, f"{app} credentials rejected (injected fault)", status_code=401
                )
