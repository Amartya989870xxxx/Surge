"""Deterministic guardrails. The LLM never enforces these; the backend does."""

import re

from pydantic import BaseModel, ValidationError

from app.enums import ApprovalMode, ConnectorMode, RiskLevel
from app.errors import ErrorCode
from app.tools.base import ToolAccess, ToolContext, ToolSpec


class PolicyViolation(Exception):
    def __init__(self, code: ErrorCode, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


ACTION_RISK: dict[str, RiskLevel] = {
    "create_github_issue": RiskLevel.MEDIUM,
    "comment_github_issue": RiskLevel.MEDIUM,
    "send_slack_message": RiskLevel.MEDIUM,
    "create_internal_draft": RiskLevel.LOW,
    "send_external_email": RiskLevel.HIGH,
}

_AUTO_REQUEST = re.compile(
    r"(without (asking|approval|waiting|confirmation)|don'?t (ask|wait)|no need to (ask|confirm)|"
    r"automatically|auto[- ]?(create|execute|approve)|just (do|go ahead|create|file|open))",
    re.IGNORECASE,
)


def validate_tool_call(spec: ToolSpec, arguments: dict, ctx: ToolContext) -> BaseModel:
    mode = ctx.connectors.mode(spec.app)
    if mode == ConnectorMode.DISABLED:
        raise PolicyViolation(ErrorCode.CONNECTOR_DISABLED, f"{spec.app.value} connector is disabled")
    if spec.access == ToolAccess.WRITE and not ctx.approved_action_id:
        raise PolicyViolation(
            ErrorCode.POLICY_VIOLATION,
            f"{spec.name} is a mutation and may only run for an approved action",
        )
    try:
        return spec.args_model.model_validate(arguments)
    except ValidationError as exc:
        fields = ", ".join(".".join(str(p) for p in e["loc"]) or "arguments" for e in exc.errors()[:5])
        raise PolicyViolation(ErrorCode.INVALID_ARGUMENTS, f"Invalid arguments for {spec.name}: {fields}") from exc


def risk_for(action_type: str) -> RiskLevel:
    return ACTION_RISK.get(action_type, RiskLevel.HIGH)


def approval_required(risk: RiskLevel, approval_mode: ApprovalMode | str) -> bool:
    return not (risk == RiskLevel.LOW and ApprovalMode(approval_mode) == ApprovalMode.AUTO_LOW_RISK)


def requests_autonomous_action(text: str) -> bool:
    return bool(_AUTO_REQUEST.search(text or ""))
