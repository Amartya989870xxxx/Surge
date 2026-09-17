import asyncio
import logging
import time

from pydantic import BaseModel, ValidationError

from app.agent.policy import PolicyViolation, validate_tool_call
from app.config import Settings
from app.enums import Actor, EventType
from app.errors import ErrorCode, ProviderError
from app.observability.events import EventBus
from app.tools.base import ToolAccess, ToolContext, ToolError, ToolResult
from app.tools.registry import ToolRegistry

logger = logging.getLogger("surge.tools")


def summarize_args(args: BaseModel) -> str:
    parts = []
    for key, value in args.model_dump().items():
        if value is None:
            continue
        if key == "body":
            parts.append(f"body=<{len(value)} chars>")
            continue
        if hasattr(value, "isoformat"):
            value = value.strftime("%Y-%m-%d %H:%M")
        text = str(value)
        parts.append(f"{key}={text[:60]}{'…' if len(text) > 60 else ''}")
    return ", ".join(parts)


class ToolRunner:
    """Executes allowlisted tools with validation, timeouts, bounded retries and full observability."""

    def __init__(self, registry: ToolRegistry, bus: EventBus, settings: Settings):
        self.registry = registry
        self.bus = bus
        self.settings = settings

    async def call(
        self,
        ctx: ToolContext,
        tool_name: str,
        arguments: dict,
        *,
        purpose: str | None = None,
    ) -> ToolResult:
        spec = self.registry.get(tool_name)
        inv = ctx.investigation_id
        if spec is None:
            self.bus.publish(
                inv, EventType.TOOL_CALL_FAILED, f"Rejected unknown tool '{tool_name}'",
                actor=Actor.SYSTEM, status="rejected", tool_name=tool_name,
                error_code=ErrorCode.UNSUPPORTED_OPERATION.value,
            )
            return ToolResult(
                success=False, tool=tool_name, app="unknown", operation="unknown", mode="n/a",
                error=ToolError(code=ErrorCode.UNSUPPORTED_OPERATION.value, message="Tool not allowlisted", retryable=False),
            )

        app = spec.app.value
        mode = ctx.connectors.mode(spec.app).value
        try:
            args = validate_tool_call(spec, arguments, ctx)
        except PolicyViolation as violation:
            self.bus.publish(
                inv, EventType.TOOL_CALL_FAILED, f"Policy blocked {spec.name}",
                actor=Actor.SYSTEM, status="rejected", tool_name=spec.name, external_app=app,
                summary=violation.message, error_code=violation.code.value, data={"mode": mode},
            )
            return ToolResult(
                success=False, tool=spec.name, app=app, operation=spec.operation, mode=mode,
                error=ToolError(code=violation.code.value, message=violation.message, retryable=False),
            )

        input_summary = summarize_args(args)
        self.bus.publish(
            inv, EventType.TOOL_CALL_STARTED, purpose or spec.description,
            actor=Actor.TOOL, status="running", tool_name=spec.name, external_app=app,
            input_summary=input_summary, data={"mode": mode, "access": spec.access.value},
        )

        timeout = spec.timeout_s or self.settings.tool_timeout_s
        delay = self.settings.retry_base_delay_s
        attempts = 0
        started = time.perf_counter()
        while True:
            attempts += 1
            try:
                client = ctx.connectors.client(spec.app)
                payload = await asyncio.wait_for(spec.handler(args, client), timeout=timeout)
                latency = int((time.perf_counter() - started) * 1000)
                items = payload.get("items", [])
                event = self.bus.publish(
                    inv, EventType.TOOL_CALL_SUCCEEDED, purpose or spec.description,
                    actor=Actor.TOOL, status="succeeded", tool_name=spec.name, external_app=app,
                    duration_ms=latency, input_summary=input_summary,
                    output_summary=payload.get("summary") or f"{len(items)} item(s)",
                    data={"mode": mode, "attempts": attempts, "warnings": payload.get("warnings", [])},
                )
                return ToolResult(
                    success=True, tool=spec.name, app=app, operation=spec.operation, mode=mode,
                    items=items, data=payload.get("data", {}), latency_ms=latency, attempts=attempts,
                    warnings=payload.get("warnings", []), event_sequence=event["sequence"],
                )
            except TimeoutError:
                error = ProviderError(
                    ErrorCode.TIMEOUT, f"{spec.name} exceeded {timeout:.0f}s", ambiguous=spec.access == ToolAccess.WRITE
                )
            except ProviderError as exc:
                error = exc
            except ValidationError:
                error = ProviderError(ErrorCode.MALFORMED_RESPONSE, f"{spec.name} returned an unexpected shape")
            except asyncio.CancelledError:
                raise
            except Exception:  # a tool bug must never take down the investigation
                logger.exception("Unexpected failure in %s", spec.name)
                error = ProviderError(ErrorCode.INTERNAL, f"{spec.name} failed unexpectedly")

            if spec.access == ToolAccess.WRITE and error.code == ErrorCode.TIMEOUT:
                error.ambiguous = True
            can_retry = (
                spec.access == ToolAccess.READ
                and error.retryable
                and attempts <= self.settings.tool_max_retries
            )
            if not can_retry:
                break
            self.bus.publish(
                inv, EventType.TOOL_RETRY, f"Retrying {spec.name} after {error.code.value}",
                actor=Actor.SYSTEM, status="retrying", tool_name=spec.name, external_app=app,
                summary=f"{error.message}. Backing off {delay:.2f}s (attempt {attempts + 1} of {self.settings.tool_max_retries + 1}).",
                error_code=error.code.value, data={"attempt": attempts, "delay_s": round(delay, 3)},
            )
            await asyncio.sleep(delay)
            delay *= 2

        latency = int((time.perf_counter() - started) * 1000)
        event = self.bus.publish(
            inv, EventType.TOOL_CALL_FAILED, purpose or spec.description,
            actor=Actor.TOOL, status="failed", tool_name=spec.name, external_app=app,
            duration_ms=latency, input_summary=input_summary, summary=error.message,
            error_code=error.code.value,
            data={"mode": mode, "attempts": attempts, "retryable": error.retryable, "ambiguous": error.ambiguous},
        )
        return ToolResult(
            success=False, tool=spec.name, app=app, operation=spec.operation, mode=mode,
            error=ToolError(code=error.code.value, message=error.message, retryable=error.retryable, ambiguous=error.ambiguous),
            latency_ms=latency, attempts=attempts, event_sequence=event["sequence"],
        )
