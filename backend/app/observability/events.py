import asyncio
import logging
import threading
from collections import defaultdict

from sqlalchemy import func, select

from app.db.models import InvestigationEvent
from app.db.session import Database
from app.enums import Actor, EventType
from app.observability.logging import redact

logger = logging.getLogger("surge.events")

_APP_CATEGORY = {"sheets": "SHEETS", "github": "GITHUB", "slack": "SLACK"}
_TYPE_CATEGORY = {
    EventType.PLAN: "PLAN",
    EventType.EVIDENCE: "EVIDENCE",
    EventType.ANOMALY: "EVIDENCE",
    EventType.NOT_APPLICABLE: "EVIDENCE",
    EventType.HYPOTHESES_GENERATED: "HYPOTHESIS",
    EventType.HYPOTHESIS_UPDATED: "HYPOTHESIS",
    EventType.SUFFICIENCY_CHECK: "HYPOTHESIS",
    EventType.SYNTHESIS: "SYNTHESIS",
    EventType.DEGRADED: "DEGRADED",
    EventType.POLICY: "POLICY",
    EventType.VERIFICATION: "VERIFICATION",
    EventType.LLM_FALLBACK: "SYSTEM",
    EventType.STATUS_CHANGED: "SYSTEM",
    EventType.INVESTIGATION_CREATED: "SYSTEM",
    EventType.COMPLETED: "SYSTEM",
    EventType.FAILED: "SYSTEM",
    EventType.CANCELLED: "SYSTEM",
}


def display_category(event_type: str, external_app: str | None) -> str:
    if event_type.startswith("TOOL_") and external_app:
        return _APP_CATEGORY.get(external_app, "TOOL")
    if event_type.startswith("ACTION_") or event_type in (
        EventType.APPROVAL_REQUIRED,
        EventType.IDEMPOTENT_REPLAY,
    ):
        return "ACTION"
    return _TYPE_CATEGORY.get(EventType(event_type), "SYSTEM")


def serialize_event(row: InvestigationEvent) -> dict:
    return {
        "id": row.id,
        "investigation_id": row.investigation_id,
        "sequence": row.sequence,
        "timestamp": row.timestamp.isoformat(),
        "event_type": row.event_type,
        "category": display_category(row.event_type, row.external_app),
        "actor": row.actor,
        "status": row.status,
        "title": row.title,
        "summary": row.summary,
        "tool_name": row.tool_name,
        "external_app": row.external_app,
        "duration_ms": row.duration_ms,
        "input_summary": row.input_summary,
        "output_summary": row.output_summary,
        "error_code": row.error_code,
        "evidence_ids": row.evidence_ids or [],
        "hypothesis_ids": row.hypothesis_ids or [],
        "action_id": row.action_id,
        "data": row.data or {},
    }


class EventBus:
    """Append-only investigation event log with live fan-out for SSE subscribers."""

    def __init__(self, db: Database):
        self.db = db
        self._subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)
        self._sequences: dict[str, int] = {}
        self._lock = threading.Lock()

    def _next_sequence(self, investigation_id: str) -> int:
        if investigation_id not in self._sequences:
            with self.db.session() as s:
                current = s.scalar(
                    select(func.max(InvestigationEvent.sequence)).where(
                        InvestigationEvent.investigation_id == investigation_id
                    )
                )
            self._sequences[investigation_id] = current or 0
        self._sequences[investigation_id] += 1
        return self._sequences[investigation_id]

    def publish(
        self,
        investigation_id: str,
        event_type: EventType,
        title: str,
        *,
        actor: Actor = Actor.AGENT,
        summary: str | None = None,
        status: str | None = None,
        tool_name: str | None = None,
        external_app: str | None = None,
        duration_ms: int | None = None,
        input_summary: str | None = None,
        output_summary: str | None = None,
        error_code: str | None = None,
        evidence_ids: list[str] | None = None,
        hypothesis_ids: list[str] | None = None,
        action_id: str | None = None,
        data: dict | None = None,
    ) -> dict:
        with self._lock:
            sequence = self._next_sequence(investigation_id)
            row = InvestigationEvent(
                investigation_id=investigation_id,
                sequence=sequence,
                event_type=EventType(event_type).value,
                actor=Actor(actor).value,
                status=status,
                title=redact(title)[:300],
                summary=redact(summary),
                tool_name=tool_name,
                external_app=external_app,
                duration_ms=duration_ms,
                input_summary=redact(input_summary),
                output_summary=redact(output_summary),
                error_code=error_code,
                evidence_ids=evidence_ids or [],
                hypothesis_ids=hypothesis_ids or [],
                action_id=action_id,
                data=data or {},
            )
            with self.db.session() as s:
                s.add(row)
                s.flush()
            payload = serialize_event(row)
        for queue in list(self._subscribers.get(investigation_id, ())):
            queue.put_nowait(payload)
        logger.info(
            "inv=%s seq=%s type=%s app=%s status=%s %s",
            investigation_id,
            sequence,
            payload["event_type"],
            external_app or "-",
            status or "-",
            payload["title"],
        )
        return payload

    def subscribe(self, investigation_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers[investigation_id].add(queue)
        return queue

    def unsubscribe(self, investigation_id: str, queue: asyncio.Queue) -> None:
        self._subscribers.get(investigation_id, set()).discard(queue)

    def history(self, investigation_id: str, after_sequence: int = 0) -> list[dict]:
        with self.db.session() as s:
            rows = s.scalars(
                select(InvestigationEvent)
                .where(
                    InvestigationEvent.investigation_id == investigation_id,
                    InvestigationEvent.sequence > after_sequence,
                )
                .order_by(InvestigationEvent.sequence)
            ).all()
            return [serialize_event(r) for r in rows]
