"""Hybrid free-tier reasoning router.

Models are tried in a fixed priority order: the primary provider's chain, then the secondary's.
A rate-limited model cools down for the provider's retry hint, a model whose daily quota is spent is
marked exhausted until its reset, a rejected key disables the whole provider, and a bad answer just
moves on to the next model. Every call walks the order from the top again, so traffic returns to the
primary on its own as soon as it recovers."""

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass

import httpx

from app.config import Settings
from app.llm.client import LLMError, LLMResult
from app.llm.providers import FailureKind, GeminiProvider, GroqProvider, ProviderCallError
from app.observability.logging import redact

logger = logging.getLogger("surge.llm")

PROVIDERS = ("groq", "gemini")
Observer = Callable[[str | None, str, LLMResult], None]


@dataclass
class ModelSlot:
    provider: str
    model: str
    state: str = "ready"  # ready | cooling_down | exhausted | disabled
    cooldown_until: float = 0.0
    reason: str | None = None
    calls: int = 0
    successes: int = 0
    failures: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    last_error: str | None = None
    last_latency_ms: int | None = None

    @property
    def label(self) -> str:
        return f"{self.provider}/{self.model}"


def _is_type(value, expected: str) -> bool:
    return {
        "string": isinstance(value, str),
        "number": isinstance(value, int | float) and not isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "array": isinstance(value, list),
        "object": isinstance(value, dict),
        "null": value is None,
    }.get(expected, True)


def schema_problem(value, schema: dict, path: str = "$") -> str | None:
    """Minimal JSON Schema check (type, enum, required, properties, items). Returns the first problem."""
    expected = schema.get("type")
    if expected is not None:
        allowed = expected if isinstance(expected, list) else [expected]
        if not any(_is_type(value, t) for t in allowed):
            return f"{path} should be {'/'.join(allowed)}"
    if "enum" in schema and value not in schema["enum"]:
        return f"{path} is not an allowed value"
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                return f"{path}.{key} is missing"
        for key, sub in (schema.get("properties") or {}).items():
            if key in value and (problem := schema_problem(value[key], sub, f"{path}.{key}")):
                return problem
    if isinstance(value, list) and isinstance(schema.get("items"), dict):
        for index, item in enumerate(value):
            if problem := schema_problem(item, schema["items"], f"{path}[{index}]"):
                return problem
    return None


class HybridLLMRouter:
    def __init__(
        self,
        settings: Settings,
        http: httpx.AsyncClient,
        *,
        providers: dict | None = None,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.settings = settings
        self._clock = clock
        self.providers = providers if providers is not None else self._default_providers(settings, http)
        self.primary = settings.llm_primary if settings.llm_primary in PROVIDERS else "groq"
        order = [self.primary] + [p for p in PROVIDERS if p != self.primary]
        chains = {"groq": settings.groq_model_list, "gemini": settings.gemini_model_list}
        self.slots = [ModelSlot(p, m) for p in order if p in self.providers for m in chains[p]]
        self._observer: Observer | None = None

    @staticmethod
    def _default_providers(settings: Settings, http: httpx.AsyncClient) -> dict:
        providers = {}
        if settings.groq_api_key:
            providers["groq"] = GroqProvider(
                http, settings.groq_api_key, timeout_s=settings.llm_timeout_s, reasoning_effort=settings.llm_reasoning_effort
            )
        if settings.gemini_api_key:
            providers["gemini"] = GeminiProvider(
                http, settings.gemini_api_key, timeout_s=settings.llm_timeout_s, thinking_level=settings.llm_reasoning_effort
            )
        return providers

    def set_observer(self, observer: Observer) -> None:
        self._observer = observer

    def _effective_state(self, slot: ModelSlot, now: float) -> str:
        if slot.state == "disabled":
            return "disabled"
        return slot.state if slot.cooldown_until > now else "ready"

    @property
    def available(self) -> bool:
        return any(s.state != "disabled" for s in self.slots)

    @property
    def model(self) -> str:
        now = self._clock()
        ready = next((s for s in self.slots if self._effective_state(s, now) == "ready"), None)
        fallback = next((s for s in self.slots if s.state != "disabled"), None)
        return (ready or fallback).label if (ready or fallback) else "none"

    @property
    def description(self) -> str:
        return "hybrid router: " + " → ".join(s.label for s in self.slots)

    def status(self) -> dict:
        now = self._clock()
        return {
            "configured_providers": [p for p in PROVIDERS if p in self.providers],
            "primary": self.primary,
            "active_model": self.model if self.available else None,
            "order": [s.label for s in self.slots],
            "models": [
                {
                    "provider": s.provider,
                    "model": s.model,
                    "label": s.label,
                    "state": self._effective_state(s, now),
                    "available_in_s": round(max(0.0, s.cooldown_until - now), 1) if s.state != "disabled" else None,
                    "reason": s.reason if self._effective_state(s, now) != "ready" else None,
                    "calls": s.calls,
                    "successes": s.successes,
                    "failures": s.failures,
                    "input_tokens": s.input_tokens,
                    "output_tokens": s.output_tokens,
                    "last_error": s.last_error,
                    "last_latency_ms": s.last_latency_ms,
                }
                for s in self.slots
            ],
        }

    async def complete_json(
        self,
        *,
        purpose: str,
        system: str,
        prompt: str,
        schema: dict,
        max_tokens: int = 2048,
        trace_id: str | None = None,
    ) -> LLMResult:
        if not self.available:
            raise LLMError("No reasoning model is available (no Groq or Gemini key configured, or all disabled)")
        attempts: list[dict] = []
        for round_index in range(2):
            result = await self._try_all(purpose, system, prompt, schema, max_tokens, attempts, record_cooling=round_index == 0)
            if result is not None:
                if self._observer is not None:
                    self._observer(trace_id, purpose, result)
                return result
            wait = self._soonest_recovery()
            if round_index == 0 and wait is not None and wait <= self.settings.llm_max_wait_s:
                await asyncio.sleep(max(wait, 0.05))
                continue
            break
        summary = "; ".join(f"{a['model']} {a['outcome']}" for a in attempts) or "no usable models"
        raise LLMError(f"All reasoning models are unavailable ({summary})", attempts)

    async def _try_all(self, purpose, system, prompt, schema, max_tokens, attempts: list[dict], *, record_cooling: bool) -> LLMResult | None:
        for slot in self.slots:
            if slot.state == "disabled":
                continue
            remaining = slot.cooldown_until - self._clock()
            if remaining > 0:
                if record_cooling:
                    attempts.append(
                        {"model": slot.label, "outcome": slot.state, "detail": f"{slot.reason}; available again in {remaining:.0f}s"}
                    )
                continue
            slot.calls += 1
            started = self._clock()
            try:
                response = await self.providers[slot.provider].generate(
                    slot.model, system=system, prompt=prompt, schema=schema, max_tokens=max_tokens
                )
                problem = schema_problem(response.data, schema)
                if problem:
                    raise ProviderCallError(FailureKind.INVALID_OUTPUT, f"output did not match the schema ({problem})")
            except ProviderCallError as exc:
                self._penalize(slot, exc)
                attempts.append({"model": slot.label, "outcome": exc.kind.value, "detail": redact(exc.message)[:200]})
                logger.warning("llm purpose=%s model=%s failed: %s %s", purpose, slot.label, exc.kind.value, exc.message[:160])
                continue
            except Exception as exc:  # a provider bug must degrade to the next model, never crash a run
                logger.exception("Unexpected LLM provider failure on %s", slot.label)
                self._penalize(slot, ProviderCallError(FailureKind.SERVER, f"unexpected {type(exc).__name__}"))
                attempts.append({"model": slot.label, "outcome": FailureKind.SERVER.value, "detail": type(exc).__name__})
                continue
            latency = int((self._clock() - started) * 1000)
            slot.successes += 1
            slot.state, slot.reason, slot.cooldown_until, slot.last_latency_ms = "ready", None, 0.0, latency
            slot.input_tokens += response.input_tokens or 0
            slot.output_tokens += response.output_tokens or 0
            logger.info("llm purpose=%s served_by=%s latency_ms=%d skipped=%d", purpose, slot.label, latency, len(attempts))
            return LLMResult(response.data, slot.provider, slot.model, latency, list(attempts))
        return None

    def _penalize(self, slot: ModelSlot, exc: ProviderCallError) -> None:
        slot.failures += 1
        slot.last_error = f"{exc.kind.value}: {redact(exc.message)[:160]}"
        s = self.settings
        if exc.kind == FailureKind.RATE_LIMITED:
            self._cool(slot, "cooling_down", exc.retry_after_s or s.llm_rate_limit_cooldown_s, "rate limited")
        elif exc.kind == FailureKind.QUOTA_EXHAUSTED:
            self._cool(slot, "exhausted", exc.retry_after_s or s.llm_quota_cooldown_s, "daily quota exhausted")
        elif exc.kind in (FailureKind.SERVER, FailureKind.TIMEOUT):
            self._cool(slot, "cooling_down", exc.retry_after_s or s.llm_error_cooldown_s, exc.kind.value.replace("_", " "))
        elif exc.kind == FailureKind.AUTH:
            for other in self.slots:
                if other.provider == slot.provider:
                    other.state, other.reason = "disabled", f"{slot.provider} rejected the API key"
        elif exc.kind == FailureKind.MODEL_UNAVAILABLE:
            slot.state, slot.reason = "disabled", "model unavailable"

    def _cool(self, slot: ModelSlot, state: str, seconds: float, reason: str) -> None:
        slot.state, slot.reason = state, reason
        slot.cooldown_until = self._clock() + seconds

    def _soonest_recovery(self) -> float | None:
        now = self._clock()
        waits = [s.cooldown_until - now for s in self.slots if s.state != "disabled" and s.cooldown_until > now]
        return min(waits) if waits else None
