import asyncio
import time

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.config import Settings
from app.main import create_app
from app.services import build_services

PRIMARY_REQUEST = (
    "Something changed after yesterday's release. Our conversion rate dropped. "
    "Investigate the cause and coordinate the response."
)
TERMINAL_OR_WAITING = {"AWAITING_APPROVAL", "COMPLETED", "PARTIAL", "FAILED", "CANCELLED", "TIMED_OUT"}
TERMINAL = {"COMPLETED", "PARTIAL", "FAILED", "CANCELLED", "TIMED_OUT"}

FIREBASE_TEST_PROJECT = "surge-test-project"
FIREBASE_TEST_KID = "test-kid-1"


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        _env_file=None,
        database_url=f"sqlite:///{tmp_path / 'surge-test.db'}",
        reasoning_mode="heuristic",
        groq_api_key="",
        gemini_api_key="",
        demo_latency_ms=0,
        retry_base_delay_s=0.01,
        secret_key="test-secret",
        reports_dir=tmp_path / "reports",
    )


@pytest.fixture
async def services(settings):
    s = build_services(settings)
    yield s
    await s.aclose()


async def _client_for(settings, llm=None):
    app = create_app(settings, llm=llm)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
            c.services = app.state.services
            yield c


@pytest.fixture
async def client(settings):
    async for c in _client_for(settings):
        yield c


async def wait_for_status(client, investigation_id: str, statuses: set[str], timeout: float = 30.0) -> dict:
    deadline = time.monotonic() + timeout
    while True:
        body = (await client.get(f"/api/investigations/{investigation_id}")).json()
        if body["status"] in statuses:
            return body
        if time.monotonic() > deadline:
            raise AssertionError(f"Timed out waiting for {statuses}; last status {body['status']}")
        await asyncio.sleep(0.05)


async def start(client, headers: dict | None = None, **extra) -> str:
    response = await client.post("/api/investigations", json={"request": PRIMARY_REQUEST, **extra}, headers=headers)
    assert response.status_code == 202, response.text
    return response.json()["id"]


@pytest.fixture
def firebase_identity(client):
    """Configures the running app's FirebaseVerifier with a locally-generated RSA keypair (no
    network) and returns a factory for (uid, auth_headers) with a valid signed ID token."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    client.services.firebase.project_id = FIREBASE_TEST_PROJECT
    client.services.firebase._keys = {FIREBASE_TEST_KID: private_key.public_key()}
    client.services.firebase._fetched_at = time.monotonic()

    def make(uid: str = "user_test_1", **claim_overrides) -> tuple[str, dict]:
        now = int(time.time())
        claims = {
            "sub": uid,
            "aud": FIREBASE_TEST_PROJECT,
            "iss": f"https://securetoken.google.com/{FIREBASE_TEST_PROJECT}",
            "iat": now,
            "exp": now + 3600,
            "auth_time": now,
            "email": f"{uid}@example.com",
            "name": "Test User",
            **claim_overrides,
        }
        token = jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": FIREBASE_TEST_KID})
        return uid, {"Authorization": f"Bearer {token}"}

    return make
