from datetime import UTC, datetime

from app.db.models import Investigation
from app.db.session import Database
from app.enums import TERMINAL_STATUSES, Actor, EventType, InvestigationStatus
from app.observability.events import EventBus

S = InvestigationStatus
_ESCAPES = {S.FAILED, S.CANCELLED, S.TIMED_OUT}

TRANSITIONS: dict[InvestigationStatus, set[InvestigationStatus]] = {
    S.CREATED: {S.PLANNING} | _ESCAPES,
    S.PLANNING: {S.INVESTIGATING} | _ESCAPES,
    S.INVESTIGATING: {S.SYNTHESIZING, S.PARTIAL} | _ESCAPES,
    S.SYNTHESIZING: {S.AWAITING_APPROVAL, S.EXECUTING, S.COMPLETED, S.PARTIAL} | _ESCAPES,
    S.AWAITING_APPROVAL: {S.EXECUTING, S.COMPLETED} | _ESCAPES,
    S.EXECUTING: {S.VERIFYING, S.PARTIAL} | _ESCAPES,
    S.VERIFYING: {S.COMPLETED, S.PARTIAL} | _ESCAPES,
}


class InvalidTransition(Exception):
    pass


def can_transition(current: InvestigationStatus | str, target: InvestigationStatus | str) -> bool:
    return InvestigationStatus(target) in TRANSITIONS.get(InvestigationStatus(current), set())


class Lifecycle:
    """Persisted investigation state machine. Every transition is validated and emitted."""

    def __init__(self, db: Database, bus: EventBus):
        self.db = db
        self.bus = bus

    def status(self, investigation_id: str) -> InvestigationStatus:
        with self.db.session() as s:
            return InvestigationStatus(s.get(Investigation, investigation_id).status)

    def transition(self, investigation_id: str, target: InvestigationStatus, *, reason: str | None = None, **fields) -> InvestigationStatus:
        with self.db.session() as s:
            inv = s.get(Investigation, investigation_id)
            current = InvestigationStatus(inv.status)
            if current == target:
                for k, v in fields.items():
                    setattr(inv, k, v)
                return current
            if not can_transition(current, target):
                raise InvalidTransition(f"{current} → {target} is not allowed")
            inv.status = target.value
            now = datetime.now(UTC)
            if target == S.PLANNING and inv.started_at is None:
                inv.started_at = now
            if target in TERMINAL_STATUSES:
                inv.completed_at = now
                if inv.started_at:
                    inv.duration_ms = int((now - inv.started_at).total_seconds() * 1000)
            for k, v in fields.items():
                setattr(inv, k, v)
        self.bus.publish(
            investigation_id,
            EventType.STATUS_CHANGED,
            f"{current.value} → {target.value}",
            actor=Actor.SYSTEM,
            status=target.value,
            summary=reason,
            data={"from": current.value, "to": target.value},
        )
        return current

    def update(self, investigation_id: str, **fields) -> None:
        with self.db.session() as s:
            inv = s.get(Investigation, investigation_id)
            for k, v in fields.items():
                setattr(inv, k, v)
