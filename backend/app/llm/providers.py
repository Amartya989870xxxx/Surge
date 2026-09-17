"""Free-tier LLM providers over plain HTTP: Groq (OpenAI-compatible) and Google Gemini.

Each provider turns every failure into a classified ProviderCallError so the router can decide
whether a model should cool down, is exhausted for the day, or the whole provider is unusable."""

import json
import re
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import quote

import httpx

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class FailureKind(StrEnum):
    RATE_LIMITED = "rate_limited"
    QUOTA_EXHAUSTED = "quota_exhausted"
    AUTH = "auth_failed"
    MODEL_UNAVAILABLE = "model_unavailable"
    BAD_REQUEST = "bad_request"
    SERVER = "server_error"
    TIMEOUT = "timeout"
    INVALID_OUTPUT = "invalid_output"
    BLOCKED = "blocked"


class ProviderCallError(Exception):
    def __init__(self, kind: FailureKind, message: str, *, status: int | None = None, retry_after_s: float | None = None):
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.status = status
        self.retry_after_s = retry_after_s


@dataclass
class ProviderResponse:
    data: dict
    input_tokens: int | None = None
    output_tokens: int | None = None


_DURATION_PART = re.compile(r"(\d+(?:\.\d+)?)(ms|h|m|s)")


def parse_duration(text: str | None) -> float | None:
    """Parses provider retry hints such as '12', '37s', '7m26.4s', '1h2m' or '340ms' into seconds."""
    if not text:
        return None
    text = str(text).strip()
    try:
        return float(text)
    except ValueError:
        pass
    parts = _DURATION_PART.findall(text)
    if not parts:
        return None
    scale = {"h": 3600.0, "m": 60.0, "s": 1.0, "ms": 0.001}
    return round(sum(float(value) * scale[unit] for value, unit in parts), 3)


def extract_json(text: str) -> dict:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            raise ProviderCallError(FailureKind.INVALID_OUTPUT, "response was not JSON") from None
        try:
            data = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            raise ProviderCallError(FailureKind.INVALID_OUTPUT, "response contained malformed JSON") from None
    if not isinstance(data, dict):
        raise ProviderCallError(FailureKind.INVALID_OUTPUT, "response JSON was not an object")
    return data


def _without_additional_properties(schema):
    if isinstance(schema, dict):
        return {k: _without_additional_properties(v) for k, v in schema.items() if k != "additionalProperties"}
    if isinstance(schema, list):
        return [_without_additional_properties(v) for v in schema]
    return schema


async def _post(http: httpx.AsyncClient, provider: str, url: str, *, headers: dict, body: dict, timeout_s: float) -> httpx.Response:
    try:
        return await http.post(url, json=body, headers=headers, timeout=timeout_s)
    except httpx.TimeoutException as exc:
        raise ProviderCallError(FailureKind.TIMEOUT, f"{provider} request timed out after {timeout_s:.0f}s") from exc
    except httpx.TransportError as exc:
        raise ProviderCallError(FailureKind.SERVER, f"{provider} unreachable ({type(exc).__name__})") from exc


@dataclass(frozen=True)
class GroqModelProfile:
    schema_mode: str  # strict | json_object
    reasoning: dict


def groq_profile(model: str, effort: str) -> GroqModelProfile:
    if model.startswith("openai/gpt-oss") and "safeguard" not in model:
        return GroqModelProfile("strict", {"reasoning_effort": effort, "include_reasoning": False})
    if model.startswith("qwen/qwen3.8"):
        return GroqModelProfile("strict", {"reasoning_effort": effort, "reasoning_format": "hidden"})
    if model.startswith("qwen/"):
        # qwen3.6 fails Groq's JSON validation when it reasons first; with thinking off it answers reliably.
        return GroqModelProfile("json_object", {"reasoning_effort": "none", "reasoning_format": "hidden"})
    return GroqModelProfile("json_object", {})


class GroqProvider:
    name = "groq"

    def __init__(self, http: httpx.AsyncClient, api_key: str, *, timeout_s: float, reasoning_effort: str):
        self.http = http
        self._key = api_key
        self.timeout_s = timeout_s
        self.effort = reasoning_effort

    async def generate(self, model: str, *, system: str, prompt: str, schema: dict, max_tokens: int) -> ProviderResponse:
        profile = groq_profile(model, self.effort)
        if profile.schema_mode == "json_object":
            system = f"{system}\n\nRespond with a single JSON object that conforms to this JSON Schema:\n{json.dumps(schema)}"
            response_format = {"type": "json_object"}
        else:
            response_format = {
                "type": "json_schema",
                "json_schema": {"name": "surge_output", "strict": True, "schema": schema},
            }
        body = {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            "response_format": response_format,
            "max_completion_tokens": max_tokens,
            "temperature": 0.2,
            **profile.reasoning,
        }
        try:
            return await self._send(body)
        except ProviderCallError as exc:
            if exc.kind == FailureKind.BAD_REQUEST and profile.reasoning and "reason" in exc.message.lower():
                return await self._send({k: v for k, v in body.items() if k not in profile.reasoning})
            raise

    async def _send(self, body: dict) -> ProviderResponse:
        resp = await _post(
            self.http, "Groq", GROQ_URL, headers={"Authorization": f"Bearer {self._key}"}, body=body, timeout_s=self.timeout_s
        )
        if resp.status_code != 200:
            raise self.classify(resp)
        try:
            payload = resp.json()
        except ValueError:
            raise ProviderCallError(FailureKind.INVALID_OUTPUT, "Groq returned a non-JSON body") from None
        choice = (payload.get("choices") or [{}])[0]
        if choice.get("finish_reason") == "length":
            raise ProviderCallError(FailureKind.INVALID_OUTPUT, "output truncated at max_completion_tokens")
        content = (choice.get("message") or {}).get("content")
        if not content:
            raise ProviderCallError(FailureKind.INVALID_OUTPUT, "Groq returned an empty message")
        usage = payload.get("usage") or {}
        return ProviderResponse(extract_json(content), usage.get("prompt_tokens"), usage.get("completion_tokens"))

    @staticmethod
    def classify(resp: httpx.Response) -> ProviderCallError:
        try:
            error = (resp.json() or {}).get("error") or {}
        except ValueError:
            error = {}
        message = str(error.get("message") or resp.text[:300] or f"HTTP {resp.status_code}")
        code = str(error.get("code") or "")
        status = resp.status_code
        retry = parse_duration(resp.headers.get("retry-after"))
        if retry is None and (hint := re.search(r"try again in ([\d.hms]+)", message)):
            retry = parse_duration(hint.group(1))
        lowered = message.lower()
        if status == 429:
            daily = "per day" in lowered or "(tpd)" in lowered or "(rpd)" in lowered
            kind = FailureKind.QUOTA_EXHAUSTED if daily else FailureKind.RATE_LIMITED
            return ProviderCallError(kind, message, status=status, retry_after_s=retry)
        if status in (401, 403):
            return ProviderCallError(FailureKind.AUTH, message, status=status)
        if status == 404 or code in ("model_not_found", "model_decommissioned"):
            return ProviderCallError(FailureKind.MODEL_UNAVAILABLE, message, status=status)
        if code == "json_validate_failed":
            return ProviderCallError(FailureKind.INVALID_OUTPUT, message, status=status)
        if status >= 500 or status == 498:
            return ProviderCallError(FailureKind.SERVER, message, status=status, retry_after_s=retry)
        return ProviderCallError(FailureKind.BAD_REQUEST, message, status=status)


_BLOCKED_FINISH = {"SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII", "RECITATION", "IMAGE_SAFETY"}


class GeminiProvider:
    name = "gemini"

    def __init__(self, http: httpx.AsyncClient, api_key: str, *, timeout_s: float, thinking_level: str):
        self.http = http
        self._key = api_key
        self.timeout_s = timeout_s
        self.thinking_level = thinking_level

    async def generate(self, model: str, *, system: str, prompt: str, schema: dict, max_tokens: int) -> ProviderResponse:
        config = {
            "responseMimeType": "application/json",
            "responseJsonSchema": schema,
            "maxOutputTokens": max_tokens * 2,
            "temperature": 0.2,
            "thinkingConfig": {"thinkingLevel": self.thinking_level},
        }
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": config,
        }
        try:
            return await self._send(model, body)
        except ProviderCallError as exc:
            if exc.kind != FailureKind.BAD_REQUEST:
                raise
            lowered = exc.message.lower()
            if "thinking" in lowered:
                config.pop("thinkingConfig", None)
            elif "schema" in lowered and "responseJsonSchema" in config:
                config["responseSchema"] = _without_additional_properties(config.pop("responseJsonSchema"))
            else:
                raise
            return await self._send(model, body)

    async def _send(self, model: str, body: dict) -> ProviderResponse:
        resp = await _post(
            self.http, "Gemini", GEMINI_URL.format(model=quote(model, safe="")),
            headers={"x-goog-api-key": self._key}, body=body, timeout_s=self.timeout_s,
        )
        if resp.status_code != 200:
            raise self.classify(resp)
        try:
            payload = resp.json()
        except ValueError:
            raise ProviderCallError(FailureKind.INVALID_OUTPUT, "Gemini returned a non-JSON body") from None
        block = (payload.get("promptFeedback") or {}).get("blockReason")
        if block:
            raise ProviderCallError(FailureKind.BLOCKED, f"prompt blocked ({block})")
        candidates = payload.get("candidates") or []
        if not candidates:
            raise ProviderCallError(FailureKind.INVALID_OUTPUT, "Gemini returned no candidates")
        candidate = candidates[0]
        finish = candidate.get("finishReason")
        if finish in _BLOCKED_FINISH:
            raise ProviderCallError(FailureKind.BLOCKED, f"generation stopped ({finish})")
        parts = (candidate.get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
        if not text:
            detail = "output truncated at maxOutputTokens" if finish == "MAX_TOKENS" else "Gemini returned no text"
            raise ProviderCallError(FailureKind.INVALID_OUTPUT, detail)
        usage = payload.get("usageMetadata") or {}
        return ProviderResponse(extract_json(text), usage.get("promptTokenCount"), usage.get("candidatesTokenCount"))

    @staticmethod
    def classify(resp: httpx.Response) -> ProviderCallError:
        try:
            error = (resp.json() or {}).get("error") or {}
        except ValueError:
            error = {}
        message = str(error.get("message") or resp.text[:300] or f"HTTP {resp.status_code}")
        status_text = str(error.get("status") or "")
        retry, quota_ids = None, []
        for detail in error.get("details") or []:
            kind = str(detail.get("@type", ""))
            if kind.endswith("RetryInfo"):
                retry = parse_duration(detail.get("retryDelay"))
            elif kind.endswith("QuotaFailure"):
                quota_ids += [f"{v.get('quotaId', '')} {v.get('quotaMetric', '')}" for v in detail.get("violations") or []]
        text = f"{message} {' '.join(quota_ids)} {error.get('code', '')}".lower()
        status = resp.status_code
        if status == 429 or status_text == "RESOURCE_EXHAUSTED":
            daily = "perday" in text or "per day" in text or "daily" in text or "quota_exceeded" in text
            kind = FailureKind.QUOTA_EXHAUSTED if daily else FailureKind.RATE_LIMITED
            return ProviderCallError(kind, message, status=status, retry_after_s=retry)
        if status in (401, 403) or status_text in ("PERMISSION_DENIED", "UNAUTHENTICATED", "FAILED_PRECONDITION") or "api key not valid" in text:
            return ProviderCallError(FailureKind.AUTH, message, status=status)
        if status == 404 or status_text == "NOT_FOUND":
            return ProviderCallError(FailureKind.MODEL_UNAVAILABLE, message, status=status)
        if status >= 500 or status_text in ("UNAVAILABLE", "INTERNAL", "DEADLINE_EXCEEDED"):
            return ProviderCallError(FailureKind.SERVER, message, status=status, retry_after_s=retry)
        return ProviderCallError(FailureKind.BAD_REQUEST, message, status=status)
