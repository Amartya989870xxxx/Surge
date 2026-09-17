import asyncio

from tests.conftest import TERMINAL, TERMINAL_OR_WAITING, start, wait_for_status


async def test_primary_flow_end_to_end(client):
    inv_id = await start(client)
    detail = await wait_for_status(client, inv_id, TERMINAL_OR_WAITING)
    assert detail["status"] == "AWAITING_APPROVAL", detail
    assert detail["outcome"] == "diagnosis"
    assert detail["strongest_hypothesis"]["kind"] == "checkout_regression"
    assert detail["confidence"] >= 0.85
    assert detail["connector_mode"] == "DEMO" and detail["reasoning_mode"] == "heuristic"

    hypotheses = (await client.get(f"/api/investigations/{inv_id}/hypotheses")).json()
    assert len(hypotheses) == 4
    assert hypotheses[0]["kind"] == "checkout_regression" and hypotheses[0]["status"] == "supported"
    assert all(h["status"] in ("rejected", "insufficient_evidence") for h in hypotheses[1:])
    assert len(hypotheses[0]["independent_sources"]) >= 2

    evidence = (await client.get(f"/api/investigations/{inv_id}/evidence")).json()
    evidence_ids = {e["id"] for e in evidence}
    for h in hypotheses:
        assert set(h["supporting_evidence_ids"]) | set(h["contradicting_evidence_ids"]) <= evidence_ids
    assert any(e["source_type"] == "metric_anomaly" for e in evidence)
    assert all(e["connector_mode"] == "DEMO" for e in evidence)

    claims = (await client.get(f"/api/investigations/{inv_id}/claims")).json()
    assert claims and all(c["grounded"] for c in claims)
    assert {"FACT", "INFERENCE", "HYPOTHESIS", "RECOMMENDATION"} <= {c["claim_type"] for c in claims}
    for c in claims:
        assert set(c["evidence_ids"]) <= evidence_ids

    events = (await client.get(f"/api/investigations/{inv_id}/events")).json()
    types = [e["event_type"] for e in events]
    for expected in ("ANOMALY", "HYPOTHESES_GENERATED", "HYPOTHESIS_UPDATED", "SUFFICIENCY_CHECK", "SYNTHESIS", "APPROVAL_REQUIRED"):
        assert expected in types
    assert [e["sequence"] for e in events] == list(range(1, len(events) + 1))
    assert not any(e["tool_name"] in ("github.create_issue", "github.create_comment") for e in events)
    probes = [e["data"].get("probe_id") for e in events if e["event_type"] == "PLAN"]
    assert probes[0] == "establish_anomaly" and len(set(probes)) >= 4

    action = (await client.get(f"/api/investigations/{inv_id}/actions")).json()[0]
    assert action["approval_status"] == "PENDING" and action["risk_level"] == "MEDIUM"
    assert "## Surge incident report" in action["preview"]["body"]
    response = await client.post(f"/api/investigations/{inv_id}/approve", json={"action_id": action["id"], "approved": True})
    assert response.status_code == 200, response.text

    detail = await wait_for_status(client, inv_id, TERMINAL)
    assert detail["status"] == "COMPLETED" and detail["verified"]
    action = (await client.get(f"/api/investigations/{inv_id}/actions")).json()[0]
    assert action["execution_status"] == "SUCCEEDED" and action["verification_status"] == "VERIFIED"
    assert action["verification"] and all(check["passed"] for check in action["verification"]["checks"])
    assert action["external_result_id"].startswith("acme/storefront#")
    assert [stage["done"] for stage in action["lifecycle"]] == [True, True, True, True]

    stream = await client.get(f"/api/investigations/{inv_id}/stream")
    assert stream.headers["content-type"].startswith("text/event-stream")
    all_events = (await client.get(f"/api/investigations/{inv_id}/events")).json()
    assert sum(1 for line in stream.text.splitlines() if line.startswith("id: ")) == len(all_events)
    assert "event: end" in stream.text


async def test_live_stream_delivers_every_event_in_order(client):
    inv_id = await start(client)
    stream_task = asyncio.create_task(client.get(f"/api/investigations/{inv_id}/stream"))
    await wait_for_status(client, inv_id, {"AWAITING_APPROVAL"})
    action = (await client.get(f"/api/investigations/{inv_id}/actions")).json()[0]
    rejected = await client.post(
        f"/api/investigations/{inv_id}/approve", json={"action_id": action["id"], "approved": False}
    )
    assert rejected.json()["approval_status"] == "REJECTED"
    response = await asyncio.wait_for(stream_task, timeout=30)
    streamed = [int(line[4:]) for line in response.text.splitlines() if line.startswith("id: ")]
    events = (await client.get(f"/api/investigations/{inv_id}/events")).json()
    assert streamed == [e["sequence"] for e in events]
    assert (await client.get(f"/api/investigations/{inv_id}")).json()["status"] == "COMPLETED"


async def test_slack_outage_is_survived_and_disclosed(client):
    inv_id = await start(client, inject_failures=["slack_unavailable"])
    detail = await wait_for_status(client, inv_id, TERMINAL_OR_WAITING)
    assert detail["status"] == "AWAITING_APPROVAL"
    assert detail["degraded"] and detail["missing_sources"] == ["slack"]
    assert detail["strongest_hypothesis"]["kind"] == "checkout_regression"
    breakdown = detail["confidence_breakdown"]
    assert breakdown["coverage_factor"] < 1 and detail["confidence"] < breakdown["posterior"]
    assert detail["fault_injection"][0]["target"] == "slack"
    events = (await client.get(f"/api/investigations/{inv_id}/events")).json()
    degraded = [e for e in events if e["event_type"] == "DEGRADED"]
    assert degraded and "injected" in degraded[0]["summary"]
    assert any(e["event_type"] == "POLICY" and e["title"].startswith("Confidence adjusted") for e in events)
    assert any(u.startswith("Slack was unavailable") for u in detail["synthesis"]["uncertainties"])


async def test_disabled_github_never_mutates(client):
    inv_id = await start(client, disabled_apps=["github"])
    detail = await wait_for_status(client, inv_id, TERMINAL_OR_WAITING)
    assert detail["status"] in ("PARTIAL", "COMPLETED")
    assert "github" in detail["missing_sources"]
    events = (await client.get(f"/api/investigations/{inv_id}/events")).json()
    assert not any((e["tool_name"] or "").startswith("github.create") for e in events)
    actions = (await client.get(f"/api/investigations/{inv_id}/actions")).json()
    assert all(a["execution_status"] in ("BLOCKED",) for a in actions)


async def test_cancel_while_waiting_for_approval(client):
    inv_id = await start(client)
    await wait_for_status(client, inv_id, {"AWAITING_APPROVAL"})
    response = await client.post(f"/api/investigations/{inv_id}/cancel")
    assert response.json()["status"] == "CANCELLED"
    action = (await client.get(f"/api/investigations/{inv_id}/actions")).json()[0]
    assert action["approval_status"] == "REJECTED"
    again = await client.post(f"/api/investigations/{inv_id}/cancel")
    assert again.status_code == 409 and again.json()["error"]["code"] == "INVALID_STATE"


async def test_live_stream_delivers_cancellation_without_client_polling(client):
    """A client with an open SSE connection must see CANCELLED and the stream close on its own —
    the frontend should never need to poll the REST endpoint to learn a run was cancelled."""
    inv_id = await start(client)
    stream_task = asyncio.create_task(client.get(f"/api/investigations/{inv_id}/stream"))
    await wait_for_status(client, inv_id, {"AWAITING_APPROVAL"})

    cancelled = await client.post(f"/api/investigations/{inv_id}/cancel")
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "CANCELLED"

    response = await asyncio.wait_for(stream_task, timeout=10)
    event_types = [line[7:] for line in response.text.splitlines() if line.startswith("event: ")]
    assert event_types[-2:] == ["CANCELLED", "end"]


async def test_investigations_can_be_filtered_by_session(client):
    mine = await start(client, session_id="judge-session-1")
    await start(client, session_id="judge-session-2")
    await wait_for_status(client, mine, TERMINAL_OR_WAITING)

    filtered = (await client.get("/api/investigations", params={"session_id": "judge-session-1"})).json()
    assert filtered["total"] == 1
    assert filtered["items"][0]["id"] == mine
    assert filtered["items"][0]["session_id"] == "judge-session-1"

    # An unfiltered, unauthenticated call must NOT return every custom session's investigations —
    # it only ever sees the shared "anonymous" bucket, so one tenant's data can't leak to another.
    everything = (await client.get("/api/investigations")).json()
    assert everything["total"] == 0

    both_explicitly = (await client.get("/api/investigations", params={"session_id": "judge-session-2"})).json()
    assert both_explicitly["total"] == 1 and both_explicitly["items"][0]["session_id"] == "judge-session-2"


async def test_approving_unknown_action_is_404(client):
    inv_id = await start(client)
    await wait_for_status(client, inv_id, {"AWAITING_APPROVAL"})
    response = await client.post(f"/api/investigations/{inv_id}/approve", json={"action_id": "act_000000000000"})
    assert response.status_code == 404


async def test_validation_errors_are_structured(client):
    too_short = await client.post("/api/investigations", json={"request": "hi"})
    assert too_short.status_code == 422 and too_short.json()["error"]["code"] == "INVALID_REQUEST"
    bad_fault = await client.post("/api/investigations", json={"request": "Investigate the drop", "inject_failures": ["nope"]})
    assert bad_fault.status_code == 422
    extra = await client.post("/api/investigations", json={"request": "Investigate the drop", "url": "http://x"})
    assert extra.status_code == 422
    missing = await client.get("/api/investigations/inv_doesnotexist")
    assert missing.status_code == 404 and missing.json()["error"]["code"] == "NOT_FOUND"


async def test_llm_mode_without_key_is_refused_honestly(client):
    response = await client.post("/api/investigations", json={"request": "Investigate the drop", "reasoning": "llm"})
    assert response.status_code == 409


async def test_oauth_state_is_validated(client):
    response = await client.get("/api/connectors/github/callback", params={"code": "abc", "state": "forged"})
    assert response.status_code == 400
    anonymous = await client.post("/api/connectors/github/start")
    assert anonymous.status_code == 401, "connecting a real account requires being signed in"


async def test_connectors_system_and_tools_endpoints(client):
    connectors = (await client.get("/api/connectors")).json()
    assert {c["app"] for c in connectors["connectors"]} == {"sheets", "github", "slack"}
    assert all(c["mode"] == "DEMO" and c["status"] == "demo" for c in connectors["connectors"])
    assert "access_token" not in str(connectors)
    assert "slack_unavailable" in connectors["fault_presets"]
    system = (await client.get("/api/system")).json()
    assert system["reasoning"]["default_mode"] == "heuristic" and len(system["hypothesis_catalog"]) == 4
    tools = (await client.get("/api/tools")).json()
    assert {t["name"] for t in tools} >= {"github.create_issue", "sheets.read_rows", "slack.search_messages"}
    assert (await client.get("/api/health")).json()["status"] == "ok"
    assert (await client.get("/openapi.json")).status_code == 200


async def test_list_and_rerun_without_faults(client):
    inv_id = await start(client, inject_failures=["slack_unavailable"])
    await wait_for_status(client, inv_id, TERMINAL_OR_WAITING)
    listing = (await client.get("/api/investigations")).json()
    assert listing["total"] == 1 and listing["items"][0]["id"] == inv_id
    rerun = await client.post(f"/api/investigations/{inv_id}/rerun", json={"clear_faults": True})
    assert rerun.status_code == 202 and rerun.json()["injected_faults"] == []
    detail = await wait_for_status(client, rerun.json()["id"], TERMINAL_OR_WAITING)
    assert not detail["degraded"]


async def test_false_alarm_does_not_invent_an_incident(client):
    response = await client.post(
        "/api/investigations",
        json={"request": "Conversion feels lower than usual this week. Is something actually wrong?", "scenario_id": "false_alarm_01"},
    )
    detail = await wait_for_status(client, response.json()["id"], TERMINAL_OR_WAITING)
    assert detail["status"] == "COMPLETED" and detail["outcome"] == "no_anomaly"
    assert (await client.get(f"/api/investigations/{detail['id']}/hypotheses")).json() == []
    assert (await client.get(f"/api/investigations/{detail['id']}/actions")).json() == []
