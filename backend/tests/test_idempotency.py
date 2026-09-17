import asyncio

from app.actions.idempotency import idempotency_key
from app.db.models import Investigation
from tests.conftest import TERMINAL, start, wait_for_status

WORLD_KEY, SCENARIO = "demo:checkout_regression_01", "checkout_regression_01"


def surge_issues(client) -> list[dict]:
    world = client.services.worlds.get(WORLD_KEY, SCENARIO)
    return [i for i in world.github["issues"] if "surge-action:" in (i.get("body") or "")]


async def approve_first_action(client, inv_id) -> dict:
    await wait_for_status(client, inv_id, {"AWAITING_APPROVAL"})
    action = (await client.get(f"/api/investigations/{inv_id}/actions")).json()[0]
    response = await client.post(f"/api/investigations/{inv_id}/approve", json={"action_id": action["id"]})
    assert response.status_code == 200, response.text
    return action


def test_key_is_stable_and_normalized():
    a = idempotency_key("inv_1", "create_github_issue", " Acme/Storefront ")
    assert a == idempotency_key("inv_1", "create_github_issue", "acme/storefront")
    assert a != idempotency_key("inv_2", "create_github_issue", "acme/storefront")
    assert a != idempotency_key("inv_1", "comment_github_issue", "acme/storefront")
    assert a != idempotency_key("inv_1", "create_github_issue", "acme/storefront", version="v2")


async def test_ambiguous_timeout_is_resolved_without_a_duplicate(client):
    inv_id = await start(client, inject_failures=["github_issue_timeout"])
    await approve_first_action(client, inv_id)
    detail = await wait_for_status(client, inv_id, TERMINAL)
    assert detail["status"] == "COMPLETED"
    events = (await client.get(f"/api/investigations/{inv_id}/events")).json()
    assert any(e["event_type"] == "ACTION_AMBIGUOUS" for e in events)
    assert sum(1 for e in events if e["event_type"] == "TOOL_CALL_STARTED" and e["tool_name"] == "github.create_issue") == 1
    assert len(surge_issues(client)) == 1
    action = (await client.get(f"/api/investigations/{inv_id}/actions")).json()[0]
    assert action["verification_status"] == "VERIFIED"


async def test_concurrent_double_approval_executes_once(client):
    inv_id = await start(client)
    await wait_for_status(client, inv_id, {"AWAITING_APPROVAL"})
    action = (await client.get(f"/api/investigations/{inv_id}/actions")).json()[0]
    url = f"/api/investigations/{inv_id}/approve"
    first, second = await asyncio.gather(
        client.post(url, json={"action_id": action["id"]}), client.post(url, json={"action_id": action["id"]})
    )
    assert sorted([first.status_code, second.status_code]) == [200, 409]
    assert (await wait_for_status(client, inv_id, TERMINAL))["status"] == "COMPLETED"
    assert len(surge_issues(client)) == 1


async def test_re_executing_a_completed_action_is_an_idempotent_replay(client):
    inv_id = await start(client)
    action = await approve_first_action(client, inv_id)
    await wait_for_status(client, inv_id, TERMINAL)
    s = client.services
    with s.db.session() as db:
        inv = db.get(Investigation, inv_id)
        db.expunge(inv)
    await s.executor.execute(inv_id, action["id"], s.runtime.connectors_for(inv))
    events = (await client.get(f"/api/investigations/{inv_id}/events")).json()
    assert any(e["event_type"] == "IDEMPOTENT_REPLAY" for e in events)
    assert sum(1 for e in events if e["tool_name"] == "github.create_issue" and e["event_type"] == "TOOL_CALL_STARTED") == 1
    assert len(surge_issues(client)) == 1


async def test_second_investigation_updates_the_existing_incident(client):
    first = await start(client)
    await approve_first_action(client, first)
    await wait_for_status(client, first, TERMINAL)
    second = await start(client)
    await wait_for_status(client, second, {"AWAITING_APPROVAL"})
    action = (await client.get(f"/api/investigations/{second}/actions")).json()[0]
    assert action["action_type"] == "comment_github_issue"
    await client.post(f"/api/investigations/{second}/approve", json={"action_id": action["id"]})
    assert (await wait_for_status(client, second, TERMINAL))["status"] == "COMPLETED"
    assert len(surge_issues(client)) == 1
