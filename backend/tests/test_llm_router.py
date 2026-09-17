"""Hybrid Groq → Gemini routing against a scripted fake provider server (no network)."""

import json

import httpx
import pytest

from app.config import Settings
from app.llm.client import LLMError
from app.llm.providers import parse_duration
from app.llm.router import HybridLLMRouter, schema_problem
from tests.conftest import TERMINAL_OR_WAITING, _client_for, start, wait_for_status

SCHEMA = {
    "type": "object",
    "properties": {"probe_id": {"type": "string", "enum": ["a", "b"]}, "reason": {"type": "string"}},
    "required": ["probe_id", "reason"],
    "additionalProperties": False,
}
GOOD = {"probe_id": "a", "reason": "because"}
GROQ_CHAIN = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b", "qwen/qwen3.6-27b"]
GEMINI_CHAIN = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash"]


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def make_settings(**overrides) -> Settings:
    base = dict(
        _env_file=None, groq_api_key="gsk_test", gemini_api_key="gm_test", llm_max_wait_s=0,
        llm_rate_limit_cooldown_s=20, llm_quota_cooldown_s=3600, llm_error_cooldown_s=15,
    )
    return Settings(**{**base, **overrides})


def groq_ok(data=GOOD, fenced=False):
    content = json.dumps(data)
    if fenced:
        content = f"```json\n{content}\n```"
    return lambda: httpx.Response(
        200, json={"choices": [{"message": {"content": content}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 12, "completion_tokens": 6}}
    )


def gemini_ok(data=GOOD, thought=True):
    parts = ([{"text": "private reasoning", "thought": True}] if thought else []) + [{"text": json.dumps(data)}]
    return lambda: httpx.Response(
        200, json={"candidates": [{"content": {"parts": parts}, "finishReason": "STOP"}], "usageMetadata": {"promptTokenCount": 9}}
    )


def groq_limit(message, retry_after=None):
    headers = {"retry-after": retry_after} if retry_after else {}
    return lambda: httpx.Response(429, headers=headers, json={"error": {"message": message, "type": "tokens", "code": "rate_limit_exceeded"}})


def status(code, body):
    return lambda: httpx.Response(code, json=body)


GEMINI_DAILY = status(429, {"error": {
    "code": 429, "status": "RESOURCE_EXHAUSTED", "message": "You exceeded your current quota.",
    "details": [
        {"@type": "type.googleapis.com/google.rpc.QuotaFailure",
         "violations": [{"quotaMetric": "generativelanguage.googleapis.com/generate_content_free_tier_requests",
                         "quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}]},
        {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "37s"},
    ],
}})
TPD = groq_limit(
    "Rate limit reached for model `x` on tokens per day (TPD): Limit 200000, Used 199850, Requested 900. Please try again in 7m26.4s."
)


class Server:
    def __init__(self, script: dict):
        self.script = {model: list(responses) for model, responses in script.items()}
        self.requests: list[tuple[str, httpx.Request, dict]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        model = body["model"] if "groq.com" in request.url.host else request.url.path.split("/models/")[1].split(":")[0]
        self.requests.append((model, request, body))
        queue = self.script.get(model)
        if not queue:
            return httpx.Response(404, json={"error": {"message": f"model {model} not found", "status": "NOT_FOUND", "code": "model_not_found"}})
        factory = queue.pop(0) if len(queue) > 1 else queue[0]
        return factory()


def build(script, clock=None, **overrides):
    server = Server(script)
    http = httpx.AsyncClient(transport=httpx.MockTransport(server))
    return HybridLLMRouter(make_settings(**overrides), http, clock=clock or Clock()), server


async def call(router, trace_id=None):
    return await router.complete_json(purpose="plan_next_step", system="sys", prompt="p", schema=SCHEMA, trace_id=trace_id)


def slot(router, label):
    return next(m for m in router.status()["models"] if m["label"] == label)


async def test_groq_primary_uses_strict_schema_and_hidden_reasoning():
    router, server = build({"openai/gpt-oss-120b": [groq_ok()]})
    result = await call(router)
    assert result.route == "groq/openai/gpt-oss-120b" and result.data == GOOD and result.attempts == []
    _, request, body = server.requests[0]
    assert request.headers["authorization"] == "Bearer gsk_test"
    assert body["response_format"]["type"] == "json_schema" and body["response_format"]["json_schema"]["strict"] is True
    assert body["include_reasoning"] is False and body["reasoning_effort"] == "low"
    assert router.status()["order"] == [f"groq/{m}" for m in GROQ_CHAIN] + [f"gemini/{m}" for m in GEMINI_CHAIN]


async def test_minute_limit_moves_to_next_model_then_primary_recovers_on_its_own():
    clock = Clock()
    limited = groq_limit("Rate limit reached on tokens per minute (TPM): Limit 8000. Please try again in 11.5s.", retry_after="12")
    router, server = build({"openai/gpt-oss-120b": [limited, groq_ok()], "openai/gpt-oss-20b": [groq_ok()]}, clock)
    seen = []
    router.set_observer(lambda trace, purpose, result: seen.append((trace, result.route)))

    first = await call(router, trace_id="inv_1")
    assert first.route == "groq/openai/gpt-oss-20b" and first.attempts[0]["outcome"] == "rate_limited"
    assert seen == [("inv_1", "groq/openai/gpt-oss-20b")]
    assert slot(router, "groq/openai/gpt-oss-120b")["state"] == "cooling_down"
    assert slot(router, "groq/openai/gpt-oss-120b")["available_in_s"] == 12

    second = await call(router)
    assert second.route == "groq/openai/gpt-oss-20b" and second.attempts[0]["outcome"] == "cooling_down"
    assert sum(1 for m, _, _ in server.requests if m == "openai/gpt-oss-120b") == 1

    clock.now += 13
    third = await call(router)
    assert third.route == "groq/openai/gpt-oss-120b" and third.attempts == []


async def test_daily_quota_marks_model_exhausted_until_reset():
    router, _ = build({"openai/gpt-oss-120b": [TPD], "openai/gpt-oss-20b": [groq_ok()]})
    result = await call(router)
    assert result.attempts[0]["outcome"] == "quota_exhausted"
    primary = slot(router, "groq/openai/gpt-oss-120b")
    assert primary["state"] == "exhausted" and primary["available_in_s"] == pytest.approx(446.4)


async def test_exhausted_groq_falls_through_the_gemini_chain():
    script = {m: [TPD] for m in GROQ_CHAIN}
    script.update({"gemini-3.8-flash": [GEMINI_DAILY], "gemini-3.7-flash": [gemini_ok()]})
    router, server = build(script)
    result = await call(router)
    assert result.route == "gemini/gemini-3.7-flash" and result.data == GOOD
    assert [a["outcome"] for a in result.attempts] == ["quota_exhausted"] * 5
    assert slot(router, "gemini/gemini-3.8-flash")["state"] == "exhausted"
    assert slot(router, "gemini/gemini-3.8-flash")["available_in_s"] == 37

    model, request, body = server.requests[-1]
    assert model == "gemini-3.7-flash" and request.headers["x-goog-api-key"] == "gm_test"
    config = body["generationConfig"]
    assert config["responseMimeType"] == "application/json" and config["responseJsonSchema"] == SCHEMA
    assert config["thinkingConfig"] == {"thinkingLevel": "low"}
    assert body["systemInstruction"]["parts"][0]["text"] == "sys"


async def test_primary_can_be_gemini():
    router, _ = build({"gemini-3.8-flash": [gemini_ok()]}, llm_primary="gemini")
    assert router.status()["order"][0] == "gemini/gemini-3.8-flash"
    assert (await call(router)).route == "gemini/gemini-3.8-flash"


async def test_gemini_rejected_thinking_parameter_is_retried_without_it():
    rejected = status(400, {"error": {"code": 400, "status": "INVALID_ARGUMENT", "message": "Thinking level is not supported for this model."}})
    router, server = build({"gemini-3.8-flash": [rejected, gemini_ok()]}, groq_api_key="")
    assert (await call(router)).route == "gemini/gemini-3.8-flash"
    assert "thinkingConfig" in server.requests[0][2]["generationConfig"]
    assert "thinkingConfig" not in server.requests[1][2]["generationConfig"]


async def test_off_schema_output_moves_on_without_penalizing_the_model():
    router, _ = build({"openai/gpt-oss-120b": [groq_ok({"probe_id": "invented", "reason": "x"})], "openai/gpt-oss-20b": [groq_ok()]})
    result = await call(router)
    assert result.route == "groq/openai/gpt-oss-20b" and result.attempts[0]["outcome"] == "invalid_output"
    assert slot(router, "groq/openai/gpt-oss-120b")["state"] == "ready"


async def test_json_object_mode_for_models_without_strict_schema_support():
    router, server = build({"qwen/qwen3.6-27b": [groq_ok(fenced=True)]}, groq_models="qwen/qwen3.6-27b", gemini_api_key="")
    assert (await call(router)).data == GOOD
    body = server.requests[0][2]
    assert body["response_format"] == {"type": "json_object"} and body["reasoning_format"] == "hidden"
    assert body["reasoning_effort"] == "none"
    assert "JSON Schema" in body["messages"][0]["content"]


async def test_rejected_key_disables_the_whole_provider():
    unauthorized = status(401, {"error": {"message": "Invalid API Key", "type": "invalid_request_error", "code": "invalid_api_key"}})
    router, server = build({"openai/gpt-oss-120b": [unauthorized], "gemini-3.8-flash": [gemini_ok()]})
    assert (await call(router)).route == "gemini/gemini-3.8-flash"
    assert all(slot(router, f"groq/{m}")["state"] == "disabled" for m in GROQ_CHAIN)
    before = len(server.requests)
    await call(router)
    assert all(m.startswith("gemini") for m, _, _ in server.requests[before:])


async def test_blocked_and_truncated_outputs_are_skipped():
    safety = status(200, {"candidates": [{"content": {"parts": []}, "finishReason": "SAFETY"}]})
    blocked = status(200, {"promptFeedback": {"blockReason": "OTHER"}})
    truncated = status(200, {"choices": [{"message": {"content": "{\"probe_id\": \"a\""}, "finish_reason": "length"}]})
    router, _ = build({
        "openai/gpt-oss-120b": [truncated], "gemini-3.8-flash": [safety], "gemini-3.7-flash": [blocked], "gemini-3.6-flash": [gemini_ok()],
    }, groq_models="openai/gpt-oss-120b")
    result = await call(router)
    assert result.route == "gemini/gemini-3.6-flash"
    assert [a["outcome"] for a in result.attempts] == ["invalid_output", "blocked", "blocked"]


async def test_everything_down_raises_with_the_full_attempt_trail():
    groq_down = status(503, {"error": {"message": "Service Unavailable", "type": "internal_server_error"}})
    gemini_down = status(503, {"error": {"code": 503, "status": "UNAVAILABLE", "message": "The model is overloaded."}})
    script = {m: [groq_down] for m in GROQ_CHAIN} | {m: [gemini_down] for m in GEMINI_CHAIN}
    router, _ = build(script)
    with pytest.raises(LLMError) as exc:
        await call(router)
    assert len(exc.value.attempts) == 7 and {a["outcome"] for a in exc.value.attempts} == {"server_error"}


async def test_no_keys_means_no_llm_and_heuristic_default():
    settings = make_settings(groq_api_key="", gemini_api_key="")
    router = HybridLLMRouter(settings, httpx.AsyncClient())
    assert not router.available and settings.resolved_reasoning_mode() == "heuristic"
    with pytest.raises(LLMError):
        await call(router)


def test_parse_duration():
    assert parse_duration("7m26.4s") == pytest.approx(446.4)
    assert parse_duration("37s") == 37 and parse_duration("12") == 12
    assert parse_duration("340ms") == pytest.approx(0.34) and parse_duration("1h2m") == 3720
    assert parse_duration(None) is None and parse_duration("soon") is None


def test_schema_problem_checks_nested_enums_and_required_fields():
    nested = {"type": "object", "properties": {"items": {"type": "array", "items": SCHEMA}}, "required": ["items"]}
    assert schema_problem({"items": [GOOD]}, nested) is None
    assert "missing" in schema_problem({"items": [{"probe_id": "a"}]}, nested)
    assert "allowed" in schema_problem({"items": [{"probe_id": "z", "reason": "r"}]}, nested)


def _answer(schema: dict) -> dict:
    props = schema.get("properties", {})
    if "probe_id" in props:
        return {"probe_id": props["probe_id"]["enum"][0], "reason": "Model-chosen step.", "expected_information": ["x"]}
    if "assessments" in props:
        return {"assessments": []}
    return {"summary": "Model-written summary.", "key_findings": []}


async def test_investigation_discloses_reroute_and_records_serving_model(settings):
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        calls["count"] += 1
        if body["model"] == "openai/gpt-oss-120b":
            return httpx.Response(429, headers={"retry-after": "600"}, json={"error": {"message": "tokens per minute (TPM) limit", "code": "rate_limit_exceeded"}})
        schema = body["response_format"]["json_schema"]["schema"]
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(_answer(schema))}, "finish_reason": "stop"}]})

    llm_settings = settings.model_copy(update={"groq_api_key": "gsk_test", "llm_max_wait_s": 0})
    router = HybridLLMRouter(llm_settings, httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    async for client in _client_for(llm_settings, llm=router):
        inv_id = await start(client, reasoning="llm")
        detail = await wait_for_status(client, inv_id, TERMINAL_OR_WAITING)
        events = (await client.get(f"/api/investigations/{inv_id}/events")).json()
        reroutes = [e for e in events if e["event_type"] == "LLM_FALLBACK" and e["data"].get("fallback_to") == "model"]
        assert len(reroutes) == 1 and reroutes[0]["data"]["served_by"] == "groq/openai/gpt-oss-20b"
        plans = [e for e in events if e["event_type"] == "PLAN" and e["data"].get("decided_by") == "llm"]
        assert plans and all(e["data"]["model"] == "groq/openai/gpt-oss-20b" for e in plans)
        assert detail["synthesis"]["llm_model"] == "groq/openai/gpt-oss-20b"
        llm = (await client.get("/api/llm/status")).json()
        primary = next(m for m in llm["models"] if m["label"] == "groq/openai/gpt-oss-120b")
        assert llm["available"] and primary["state"] == "cooling_down" and primary["calls"] == 1
