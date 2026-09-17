from app.tools.base import ToolContext

SINCE, UNTIL = "2026-09-11T14:00:00+00:00", "2026-09-12T16:00:00+00:00"
DEMO = {"sheets": "DEMO", "github": "DEMO", "slack": "DEMO"}


def connectors(services, faults=None):
    world = services.library.build_world(services.library.get("checkout_regression_01"))
    return services.connectors.build(DEMO, world=world, faults=faults), world


async def test_transient_5xx_is_retried_with_backoff_then_succeeds(services):
    cs, _ = connectors(services, [{"target": "github.list_deployments", "type": "error_500", "times": 2}])
    result = await services.runner.call(ToolContext("inv_t", cs), "github.list_deployments", {"since": SINCE, "until": UNTIL})
    assert result.success and result.attempts == 3
    retries = [e for e in services.bus.history("inv_t") if e["event_type"] == "TOOL_RETRY"]
    assert len(retries) == 2


async def test_auth_failure_is_not_retried(services):
    cs, _ = connectors(services, [{"target": "github", "type": "auth_failure"}])
    result = await services.runner.call(ToolContext("inv_t", cs), "github.list_deployments", {"since": SINCE, "until": UNTIL})
    assert not result.success and result.attempts == 1 and result.error.code == "AUTH_FAILED"


async def test_persistent_timeout_is_bounded(services):
    cs, _ = connectors(services, [{"target": "slack.search_messages", "type": "timeout"}])
    result = await services.runner.call(
        ToolContext("inv_t", cs), "slack.search_messages", {"terms": ["checkout"], "since": SINCE, "until": UNTIL}
    )
    assert not result.success and result.error.code == "TIMEOUT"
    assert result.attempts == services.settings.tool_max_retries + 1


async def test_malformed_payload_becomes_structured_failure(services):
    cs, _ = connectors(services, [{"target": "slack.search_messages", "type": "malformed"}])
    result = await services.runner.call(
        ToolContext("inv_t", cs), "slack.search_messages", {"terms": ["checkout"], "since": SINCE, "until": UNTIL}
    )
    assert not result.success and result.error.code == "MALFORMED_RESPONSE" and result.items == []


async def test_unavailable_connector_returns_failure_instead_of_raising(services):
    cs, _ = connectors(services, [{"target": "sheets", "type": "unavailable"}])
    result = await services.runner.call(ToolContext("inv_t", cs), "sheets.get_metadata", {})
    assert not result.success and result.error.code == "CONNECTOR_UNAVAILABLE"


async def test_write_timeout_is_ambiguous_and_never_retried_by_runner(services):
    cs, world = connectors(services, [{"target": "github.create_issue", "type": "timeout_after_commit", "times": 1}])
    result = await services.runner.call(
        ToolContext("inv_t", cs, approved_action_id="act_000000000001"),
        "github.create_issue",
        {"title": "Incident report", "body": "body", "labels": []},
    )
    assert not result.success and result.error.ambiguous and result.attempts == 1
    assert len(world.github["issues"]) == 1


async def test_unknown_tool_is_rejected_and_logged(services):
    cs, _ = connectors(services)
    result = await services.runner.call(ToolContext("inv_t", cs), "http.request", {"url": "http://example.com"})
    assert not result.success and result.error.code == "UNSUPPORTED_OPERATION"
