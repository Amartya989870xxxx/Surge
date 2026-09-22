from __future__ import annotations

import hashlib
import math
from datetime import datetime

from sqlalchemy import select

from app.agent.types import EvidenceDraft
from app.db.models import EvidenceItem, EvidenceLink, new_id
from app.db.session import Database
from app.enums import Strength

_SOURCE_WEIGHT = {
    "metric_anomaly": 1.0,
    "metric_stability": 0.9,
    "funnel_analysis": 0.9,
    "error_rate_analysis": 0.9,
    "tracking_consistency": 0.9,
    "traffic_mix": 0.9,
    "code_change": 0.85,
    "deployment": 0.7,
    "deployment_absence": 0.6,
    "message": 0.55,
}
_DIRECTNESS = {Strength.STRONG: 1.0, Strength.MODERATE: 0.7, Strength.WEAK: 0.4}


def dedupe_key(app: str, source_type: str, record_id: str) -> str:
    return hashlib.sha256(f"{app}|{source_type}|{record_id}".encode()).hexdigest()[:32]


def relevance(draft: EvidenceDraft, onset: datetime | None) -> float:
    """Transparent ranking heuristic (directness, temporal proximity, source type). It orders
    evidence for display and citation; it does not establish causality."""
    temporal = 0.5
    if onset and draft.observed_at:
        hours = abs((draft.observed_at - onset).total_seconds()) / 3600
        temporal = math.exp(-hours / 6)
    score = (
        0.4 * _DIRECTNESS[Strength(draft.strength)]
        + 0.35 * temporal
        + 0.25 * _SOURCE_WEIGHT.get(draft.source_type, 0.5)
    )
    return round(score, 3)


class EvidenceStore:
    def __init__(self, db: Database):
        self.db = db

    def add(self, investigation_id: str, draft: EvidenceDraft, *, mode: str, probe_id: str, onset: datetime | None) -> tuple[str, bool]:
        key = dedupe_key(draft.source_app, draft.source_type, draft.source_record_id)
        with self.db.session() as s:
            existing = s.scalar(
                select(EvidenceItem).where(
                    EvidenceItem.investigation_id == investigation_id, EvidenceItem.dedupe_key == key
                )
            )
            if existing:
                return existing.id, False
            eid = new_id("ev")
            s.add(
                EvidenceItem(
                    id=eid,
                    investigation_id=investigation_id,
                    source_app=draft.source_app,
                    source_type=draft.source_type,
                    source_record_id=draft.source_record_id,
                    title=draft.title[:300],
                    normalized_content=draft.content,
                    observed_at=draft.observed_at,
                    url=draft.url,
                    source_metadata=_jsonable(draft.metadata),
                    derived_from=draft.derived_from,
                    relevance_score=relevance(draft, onset),
                    evidence_strength=Strength(draft.strength).value,
                    dedupe_key=key,
                    connector_mode=mode,
                    probe_id=probe_id,
                )
            )
            return eid, True

    def list(self, investigation_id: str) -> list[EvidenceItem]:
        with self.db.session() as s:
            return list(
                s.scalars(
                    select(EvidenceItem)
                    .where(EvidenceItem.investigation_id == investigation_id)
                    .order_by(EvidenceItem.relevance_score.desc())
                ).all()
            )

    def links(self, investigation_id: str) -> list[EvidenceLink]:
        with self.db.session() as s:
            return list(s.scalars(select(EvidenceLink).where(EvidenceLink.investigation_id == investigation_id)).all())

    def existing_ids(self, investigation_id: str) -> set[str]:
        with self.db.session() as s:
            return set(s.scalars(select(EvidenceItem.id).where(EvidenceItem.investigation_id == investigation_id)).all())

    # --- async twins, for callers migrated to AsyncSession ---

    async def aadd(
        self, investigation_id: str, draft: EvidenceDraft, *, mode: str, probe_id: str, onset: datetime | None
    ) -> tuple[str, bool]:
        key = dedupe_key(draft.source_app, draft.source_type, draft.source_record_id)
        async with self.db.async_session() as s:
            existing = await s.scalar(
                select(EvidenceItem).where(
                    EvidenceItem.investigation_id == investigation_id, EvidenceItem.dedupe_key == key
                )
            )
            if existing:
                return existing.id, False
            eid = new_id("ev")
            s.add(
                EvidenceItem(
                    id=eid,
                    investigation_id=investigation_id,
                    source_app=draft.source_app,
                    source_type=draft.source_type,
                    source_record_id=draft.source_record_id,
                    title=draft.title[:300],
                    normalized_content=draft.content,
                    observed_at=draft.observed_at,
                    url=draft.url,
                    source_metadata=_jsonable(draft.metadata),
                    derived_from=draft.derived_from,
                    relevance_score=relevance(draft, onset),
                    evidence_strength=Strength(draft.strength).value,
                    dedupe_key=key,
                    connector_mode=mode,
                    probe_id=probe_id,
                )
            )
            return eid, True

    async def alist(self, investigation_id: str) -> list[EvidenceItem]:
        async with self.db.async_session() as s:
            result = await s.scalars(
                select(EvidenceItem)
                .where(EvidenceItem.investigation_id == investigation_id)
                .order_by(EvidenceItem.relevance_score.desc())
            )
            return list(result.all())

    async def alinks(self, investigation_id: str) -> list[EvidenceLink]:
        async with self.db.async_session() as s:
            result = await s.scalars(select(EvidenceLink).where(EvidenceLink.investigation_id == investigation_id))
            return list(result.all())

    async def aexisting_ids(self, investigation_id: str) -> set[str]:
        async with self.db.async_session() as s:
            result = await s.scalars(select(EvidenceItem.id).where(EvidenceItem.investigation_id == investigation_id))
            return set(result.all())


def _jsonable(value):
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(v) for v in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value
