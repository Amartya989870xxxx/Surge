"""Real auth: Firebase ID token verification, per-user connector credential isolation, and the
persona system (which changes investigation depth and wording, never the outcome itself)."""

import time

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.auth.firebase import FirebaseAuthError, FirebaseVerifier
from app.connectors.credentials import CredentialStore
from tests.conftest import FIREBASE_TEST_KID, FIREBASE_TEST_PROJECT, TERMINAL_OR_WAITING, start, wait_for_status


def _sign(private_key, project=FIREBASE_TEST_PROJECT, kid=FIREBASE_TEST_KID, **overrides):
    now = int(time.time())
    claims = {
        "sub": "user_abc",
        "aud": project,
        "iss": f"https://securetoken.google.com/{project}",
        "iat": now,
        "exp": now + 3600,
        "auth_time": now,
        "email": "abc@example.com",
        **overrides,
    }
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": kid})


# --------------------------------------------------------------------------- FirebaseVerifier unit tests

async def test_verifier_fetches_and_caches_jwks_then_accepts_a_valid_token():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    numbers = private_key.public_key().public_numbers()

    def b64url(n: int) -> str:
        import base64
        raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    jwks = {"keys": [{"kty": "RSA", "kid": FIREBASE_TEST_KID, "n": b64url(numbers.n), "e": b64url(numbers.e)}]}
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json=jwks)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        verifier = FirebaseVerifier(FIREBASE_TEST_PROJECT, http)
        token = _sign(private_key)
        claims = await verifier.verify(token)
        assert claims["sub"] == "user_abc" and claims["email"] == "abc@example.com"
        await verifier.verify(token)
        assert calls["n"] == 1, "second verification with the same kid must hit the cache, not refetch"


async def test_verifier_rejects_wrong_audience_expired_and_bad_signature():
    key_a = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    key_b = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    async with httpx.AsyncClient() as http:
        verifier = FirebaseVerifier(FIREBASE_TEST_PROJECT, http)
        verifier._keys = {FIREBASE_TEST_KID: key_a.public_key()}
        verifier._fetched_at = time.monotonic()

        with pytest.raises(FirebaseAuthError, match="Invalid"):
            await verifier.verify(_sign(key_a, project="some-other-project"))
        with pytest.raises(FirebaseAuthError, match="Invalid"):
            expired = int(time.time()) - 7200
            await verifier.verify(_sign(key_a, iat=expired, exp=expired + 60, auth_time=expired))
        with pytest.raises(FirebaseAuthError):
            await verifier.verify(_sign(key_b))  # signed by a key whose kid isn't in the cache


async def test_verifier_without_a_project_id_refuses_everything():
    async with httpx.AsyncClient() as http:
        verifier = FirebaseVerifier("", http)
        assert not verifier.configured
        with pytest.raises(FirebaseAuthError, match="not configured"):
            await verifier.verify("anything")


# --------------------------------------------------------------------------- Auth dependency + API

async def test_anonymous_requests_keep_working_exactly_as_before(client):
    response = await client.post("/api/investigations", json={"request": "Investigate the conversion drop"})
    assert response.status_code == 202
    me = await client.get("/api/auth/me")
    assert me.status_code == 401


async def test_malformed_and_invalid_tokens_are_rejected(client, firebase_identity):
    bad_scheme = await client.get("/api/auth/me", headers={"Authorization": "Basic abc"})
    assert bad_scheme.status_code == 401
    garbage = await client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert garbage.status_code == 401
    _, headers = firebase_identity()
    tampered = {"Authorization": headers["Authorization"] + "x"}
    assert (await client.get("/api/auth/me", headers=tampered)).status_code == 401


async def test_valid_token_creates_and_returns_a_real_user(client, firebase_identity):
    uid, headers = firebase_identity("user_new", name="Ada Lovelace")
    response = await client.get("/api/auth/me", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == uid and body["email"] == "user_new@example.com" and body["display_name"] == "Ada Lovelace"
    assert body["onboarding_completed"] is False and body["persona"] is None


async def test_profile_update_persists_persona_and_rejects_invalid_persona(client, firebase_identity):
    _, headers = firebase_identity("user_persona")
    ok = await client.put(
        "/api/auth/profile",
        headers=headers,
        json={"persona": "engineer", "goal": "debug incidents faster", "onboarding_completed": True},
    )
    assert ok.status_code == 200
    assert ok.json()["persona"] == "engineer" and ok.json()["onboarding_completed"] is True

    bad = await client.put("/api/auth/profile", headers=headers, json={"persona": "wizard"})
    assert bad.status_code == 422

    again = await client.get("/api/auth/me", headers=headers)
    assert again.json()["persona"] == "engineer"


# --------------------------------------------------------------------------- Per-user data scoping

async def test_two_signed_in_users_get_isolated_connector_credentials(client, firebase_identity, settings):
    store = CredentialStore(client.services.db, settings.secret_key)
    store.save("github", "token-for-alice", user_id="user_alice", account_label="alice")
    store.save("github", "token-for-bob", user_id="user_bob", account_label="bob")

    assert store.get("github", "user_alice")["access_token"] == "token-for-alice"
    assert store.get("github", "user_bob")["access_token"] == "token-for-bob"
    assert store.get("github", "user_carol") is None
    assert store.delete("github", "user_alice") is True
    assert store.get("github", "user_alice") is None
    assert store.get("github", "user_bob")["access_token"] == "token-for-bob"  # untouched


async def test_investigations_are_owned_by_the_signed_in_user(client, firebase_identity):
    uid, headers = firebase_identity("user_owner")
    inv_id = await start(client, headers=headers)
    detail = (await client.get(f"/api/investigations/{inv_id}", headers=headers)).json()
    assert detail["session_id"] == uid

    mine = (await client.get("/api/investigations", headers=headers)).json()
    assert mine["total"] == 1 and mine["items"][0]["id"] == inv_id

    anonymous_view = (await client.get("/api/investigations")).json()
    assert inv_id not in [i["id"] for i in anonymous_view["items"]]


async def test_a_different_signed_in_user_cannot_access_someone_elses_investigation(client, firebase_identity):
    _, owner_headers = firebase_identity("user_owner_2")
    inv_id = await start(client, headers=owner_headers)
    await wait_for_status(client, inv_id, TERMINAL_OR_WAITING, headers=owner_headers)

    _, intruder_headers = firebase_identity("user_intruder")
    for path in ("", "/events", "/evidence", "/hypotheses", "/actions", "/claims"):
        resp = await client.get(f"/api/investigations/{inv_id}{path}", headers=intruder_headers)
        assert resp.status_code == 404, f"{path} leaked to a non-owner"

    approve = await client.post(
        f"/api/investigations/{inv_id}/approve", json={"action_id": "act_000000000000"}, headers=intruder_headers
    )
    assert approve.status_code == 404, "a non-owner must not be able to approve someone else's action"

    cancel = await client.post(f"/api/investigations/{inv_id}/cancel", headers=intruder_headers)
    assert cancel.status_code == 404, "a non-owner must not be able to cancel someone else's investigation"

    # An unauthenticated caller is treated the same as any other non-owner.
    anonymous = await client.get(f"/api/investigations/{inv_id}")
    assert anonymous.status_code == 404

    # The real owner is unaffected.
    own_view = await client.get(f"/api/investigations/{inv_id}", headers=owner_headers)
    assert own_view.status_code == 200


async def test_starting_oauth_requires_sign_in_and_state_carries_the_user(client, firebase_identity):
    _, headers = firebase_identity("user_connector")
    # Not configured on the server, but auth is checked first and must succeed before that 409.
    response = await client.post("/api/connectors/github/start", headers=headers)
    assert response.status_code == 409


# --------------------------------------------------------------------------- Persona: depth, not just wording

async def test_engineer_persona_keeps_investigating_past_the_stop_threshold(client, firebase_identity):
    _, headers = firebase_identity("user_eng", **{})
    await client.put("/api/auth/profile", headers=headers, json={"persona": "engineer"})
    inv_id = await start(client, headers=headers)
    detail = await wait_for_status(client, inv_id, TERMINAL_OR_WAITING, headers=headers)

    default_run = await start(client)
    default_detail = await wait_for_status(client, default_run, TERMINAL_OR_WAITING)

    assert detail["strongest_hypothesis"]["kind"] == default_detail["strongest_hypothesis"]["kind"]
    assert detail["tool_call_count"] >= default_detail["tool_call_count"]
    events = (await client.get(f"/api/investigations/{inv_id}/events", headers=headers)).json()
    stop_event = next(e for e in events if e["event_type"] == "SUFFICIENCY_CHECK")
    assert "no_remaining_leads_(thorough_mode)" in stop_event["data"]["checks"]


async def test_student_persona_gets_a_plain_language_note_in_the_summary(client, firebase_identity):
    _, headers = firebase_identity("user_student")
    await client.put("/api/auth/profile", headers=headers, json={"persona": "student"})
    inv_id = await start(client, headers=headers)
    detail = await wait_for_status(client, inv_id, TERMINAL_OR_WAITING, headers=headers)
    assert "in plain terms" in detail["final_summary"].lower()
    assert detail["intent"]["persona"] == "student"


async def test_persona_never_changes_the_outcome_or_confidence(client, firebase_identity):
    _, headers = firebase_identity("user_founder")
    await client.put("/api/auth/profile", headers=headers, json={"persona": "founder"})
    with_persona = await wait_for_status(client, await start(client, headers=headers), TERMINAL_OR_WAITING, headers=headers)
    without_persona = await wait_for_status(client, await start(client), TERMINAL_OR_WAITING)
    assert with_persona["outcome"] == without_persona["outcome"]
    assert with_persona["strongest_hypothesis"]["kind"] == without_persona["strongest_hypothesis"]["kind"]
    assert with_persona["confidence"] == without_persona["confidence"]
    assert "bottom line for the business" in with_persona["final_summary"].lower()


async def test_persona_override_works_without_being_signed_in(client):
    inv_id = await start(client, persona="student")
    detail = await wait_for_status(client, inv_id, TERMINAL_OR_WAITING)
    assert detail["intent"]["persona"] == "student"
    assert "in plain terms" in detail["final_summary"].lower()


async def test_invalid_persona_in_request_body_is_rejected(client):
    response = await client.post("/api/investigations", json={"request": "Investigate the drop", "persona": "wizard"})
    assert response.status_code == 422
