import pytest

from app.agent.policy import PolicyViolation, approval_required, requests_autonomous_action, risk_for, validate_tool_call
from app.connectors.manager import ConnectorHandle, ConnectorSet
from app.enums import App, ApprovalMode, ConnectorMode, RiskLevel
from app.tools.base import ToolContext
from app.tools.registry import build_registry

REGISTRY = build_registry()


def ctx(approved_action_id=None, **modes) -> ToolContext:
    handles = {
        app: ConnectorHandle(app, ConnectorMode(modes.get(app.value, "DEMO")), object(), "demo") for app in App
    }
    return ToolContext("inv_test", ConnectorSet(handles=handles), approved_action_id=approved_action_id)


def test_mutation_without_approved_action_is_blocked():
    spec = REGISTRY.get("github.create_issue")
    with pytest.raises(PolicyViolation) as exc:
        validate_tool_call(spec, {"title": "x" * 10, "body": "y"}, ctx())
    assert exc.value.code == "POLICY_VIOLATION"


def test_mutation_with_approved_action_is_allowed():
    spec = REGISTRY.get("github.create_issue")
    args = validate_tool_call(spec, {"title": "Incident report", "body": "y"}, ctx(approved_action_id="act_1"))
    assert args.title == "Incident report"


@pytest.mark.parametrize(
    "tool,arguments",
    [
        ("sheets.read_rows", {"tab": "../../etc/passwd"}),
        ("sheets.read_rows", {"tab": "metrics", "url": "http://evil.example"}),
        ("slack.search_messages", {"terms": ["<script>"], "since": "2026-09-12T00:00:00Z", "until": "2026-09-13T00:00:00Z"}),
        ("github.list_deployments", {"since": "2026-09-01T00:00:00Z", "until": "2026-09-30T00:00:00Z"}),
        ("github.get_issue", {"number": 0}),
    ],
)
def test_invalid_or_unbounded_arguments_are_rejected(tool, arguments):
    with pytest.raises(PolicyViolation) as exc:
        validate_tool_call(REGISTRY.get(tool), arguments, ctx())
    assert exc.value.code == "INVALID_ARGUMENTS"


def test_disabled_connector_is_rejected():
    with pytest.raises(PolicyViolation) as exc:
        validate_tool_call(REGISTRY.get("slack.search_messages"), {}, ctx(slack="DISABLED"))
    assert exc.value.code == "CONNECTOR_DISABLED"


def test_only_allowlisted_operations_exist():
    names = {spec.name for spec in REGISTRY.list()}
    assert "http.request" not in names
    assert all(name.split(".")[0] in {"sheets", "github", "slack"} for name in names)


def test_approval_rules():
    assert approval_required(RiskLevel.MEDIUM, ApprovalMode.AUTO_LOW_RISK)
    assert approval_required(RiskLevel.HIGH, ApprovalMode.AUTO_LOW_RISK)
    assert approval_required(RiskLevel.LOW, ApprovalMode.REQUIRED)
    assert not approval_required(RiskLevel.LOW, ApprovalMode.AUTO_LOW_RISK)
    assert risk_for("create_github_issue") == RiskLevel.MEDIUM
    assert risk_for("something_unknown") == RiskLevel.HIGH


def test_detects_requests_to_skip_approval():
    assert requests_autonomous_action("just go ahead and create the issue automatically, don't wait for my approval")
    assert not requests_autonomous_action("Investigate the conversion drop and coordinate the response")
