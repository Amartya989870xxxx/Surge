import hashlib
from dataclasses import dataclass
from datetime import datetime

from app.db.models import IdempotencyRecord
from app.db.session import Database

ACTION_VERSION = "v1"


def normalize_target(target: str) -> str:
    return " ".join(target.strip().lower().split())


def idempotency_key(investigation_id: str, action_type: str, target: str, version: str = ACTION_VERSION) -> str:
    raw = f"{investigation_id}|{action_type}|{normalize_target(target)}|{version}"
    return hashlib.sha256(raw.encode()).hexdigest()


def action_marker(key: str) -> str:
    return f"surge-action:{key[:16]}"


def incident_fingerprint(metric: str, hypothesis_kind: str, onset: datetime) -> str:
    return hashlib.sha1(f"{metric}|{hypothesis_kind}|{onset:%Y-%m-%d}".encode()).hexdigest()[:12]


def incident_marker(fingerprint: str) -> str:
    return f"surge-incident:{fingerprint}"


@dataclass
class LedgerEntry:
    key: str
    action_id: str
    status: str  # IN_PROGRESS | SUCCEEDED | FAILED | UNKNOWN
    external_result_id: str | None
    external_url: str | None
    attempts: int


class IdempotencyLedger:
    def __init__(self, db: Database):
        self.db = db

    def get(self, key: str) -> LedgerEntry | None:
        with self.db.session() as s:
            row = s.get(IdempotencyRecord, key)
            if row is None:
                return None
            return LedgerEntry(row.key, row.action_id, row.status, row.external_result_id, row.external_url, row.attempts)

    def begin(self, key: str, action_id: str) -> int:
        with self.db.session() as s:
            row = s.get(IdempotencyRecord, key)
            if row is None:
                row = IdempotencyRecord(key=key, action_id=action_id, status="IN_PROGRESS", attempts=0)
                s.add(row)
            row.status = "IN_PROGRESS"
            row.attempts = (row.attempts or 0) + 1
            return row.attempts

    def resolve(self, key: str, status: str, *, external_result_id: str | None = None, external_url: str | None = None) -> None:
        with self.db.session() as s:
            row = s.get(IdempotencyRecord, key)
            row.status = status
            if external_result_id is not None:
                row.external_result_id = external_result_id
            if external_url is not None:
                row.external_url = external_url

    # --- async twins, for callers migrated to AsyncSession ---

    async def aget(self, key: str) -> LedgerEntry | None:
        async with self.db.async_session() as s:
            row = await s.get(IdempotencyRecord, key)
            if row is None:
                return None
            return LedgerEntry(row.key, row.action_id, row.status, row.external_result_id, row.external_url, row.attempts)

    async def abegin(self, key: str, action_id: str) -> int:
        async with self.db.async_session() as s:
            row = await s.get(IdempotencyRecord, key)
            if row is None:
                row = IdempotencyRecord(key=key, action_id=action_id, status="IN_PROGRESS", attempts=0)
                s.add(row)
            row.status = "IN_PROGRESS"
            row.attempts = (row.attempts or 0) + 1
            return row.attempts

    async def aresolve(
        self, key: str, status: str, *, external_result_id: str | None = None, external_url: str | None = None
    ) -> None:
        async with self.db.async_session() as s:
            row = await s.get(IdempotencyRecord, key)
            row.status = status
            if external_result_id is not None:
                row.external_result_id = external_result_id
            if external_url is not None:
                row.external_url = external_url
