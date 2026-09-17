"""Structured-output contract shared by every reasoning component.

Model output is always a proposal: providers constrain it to a JSON schema, the router re-checks the
schema, and each caller validates it against backend state (candidate probes, evidence IDs, catalog)."""

from dataclasses import dataclass, field
from typing import Protocol


class LLMError(Exception):
    def __init__(self, message: str, attempts: list[dict] | None = None):
        super().__init__(message)
        self.attempts = attempts or []


@dataclass
class LLMResult:
    data: dict
    provider: str
    model: str
    latency_ms: int
    attempts: list[dict] = field(default_factory=list)

    @property
    def route(self) -> str:
        return f"{self.provider}/{self.model}"


class StructuredLLM(Protocol):
    @property
    def available(self) -> bool: ...

    @property
    def model(self) -> str: ...

    async def complete_json(
        self,
        *,
        purpose: str,
        system: str,
        prompt: str,
        schema: dict,
        max_tokens: int = 2048,
        trace_id: str | None = None,
    ) -> LLMResult: ...
