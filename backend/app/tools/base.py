from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from app.enums import App, RiskLevel


class ToolAccess(StrEnum):
    READ = "read"
    WRITE = "write"


class ToolError(BaseModel):
    code: str
    message: str
    retryable: bool
    ambiguous: bool = False


class ToolResult(BaseModel):
    success: bool
    tool: str
    app: str
    operation: str
    mode: str
    items: list[dict] = Field(default_factory=list)
    data: dict = Field(default_factory=dict)
    error: ToolError | None = None
    latency_ms: int = 0
    attempts: int = 1
    warnings: list[str] = Field(default_factory=list)
    next_cursor: str | None = None
    event_sequence: int | None = None


Handler = Callable[[BaseModel, Any], Awaitable[dict]]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    app: App
    operation: str
    description: str
    access: ToolAccess
    risk: RiskLevel
    args_model: type[BaseModel]
    handler: Handler
    timeout_s: float | None = None
    demo_safe: bool = True
    verification: str | None = None

    def describe(self) -> dict:
        return {
            "name": self.name,
            "app": self.app.value,
            "operation": self.operation,
            "description": self.description,
            "access": self.access.value,
            "risk_level": self.risk.value,
            "argument_schema": self.args_model.model_json_schema(),
            "timeout_s": self.timeout_s,
            "demo_safe": self.demo_safe,
            "verification_strategy": self.verification,
        }


@dataclass
class ToolContext:
    investigation_id: str
    connectors: Any  # ConnectorSet
    approved_action_id: str | None = None
