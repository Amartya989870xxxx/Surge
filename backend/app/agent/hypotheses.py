"""Hypothesis catalog and transparent confidence aggregation.

Confidence is a log-odds belief update, not a probability of causal truth: each evidence link
adds a fixed weight by strength, repeated links from the same app get diminishing weight (so
ten Slack messages cannot outvote a metric), and the result is squashed back to [0, 1].
"""

import math
from collections import Counter, defaultdict
from dataclasses import dataclass

from sqlalchemy import select

from app.agent.types import Assessment, HypothesisView, LinkView
from app.db.models import EvidenceItem, EvidenceLink, Hypothesis, new_id
from app.db.session import Database
from app.enums import HypothesisStatus, Relation, Strength

STRENGTH_WEIGHT = {Strength.WEAK: 0.35, Strength.MODERATE: 0.8, Strength.STRONG: 1.4}
STRENGTH_RANK = {Strength.WEAK: 1, Strength.MODERATE: 2, Strength.STRONG: 3}
DIMINISHING = 0.5
SUPPORTED_THRESHOLD = 0.75
STOP_THRESHOLD = 0.85
REJECT_THRESHOLD = 0.12
MIN_MARGIN = 0.25
MIN_INDEPENDENT_SOURCES = 2
SOURCE_SUPPORT_MIN_WEIGHT = 0.5


@dataclass(frozen=True)
class HypothesisTemplate:
    kind: str
    label: str
    statement: str
    prior: float
    team: str
    keywords: tuple[str, ...]


CATALOG: dict[str, HypothesisTemplate] = {
    t.kind: t
    for t in [
        HypothesisTemplate(
            "checkout_regression",
            "Checkout regression",
            "A recent change to the checkout flow introduced a regression that prevents customers from completing purchases.",
            0.2,
            "checkout",
            ("checkout",),
        ),
        HypothesisTemplate(
            "payment_provider_issue",
            "Payment provider issue",
            "An external payment provider problem is causing payment attempts to fail.",
            0.2,
            "payments",
            ("payment", "stripe", "provider"),
        ),
        HypothesisTemplate(
            "marketing_traffic_quality",
            "Traffic-quality shift",
            "A change in traffic mix (for example a new campaign) brought lower-intent visitors and diluted the conversion rate.",
            0.2,
            "growth",
            ("campaign", "traffic"),
        ),
        HypothesisTemplate(
            "tracking_failure",
            "Analytics tracking failure",
            "Conversion tracking broke, so real purchases are under-reported and the drop is a measurement artifact.",
            0.2,
            "analytics",
            ("tracking", "analytics"),
        ),
    ]
}


def _logit(p: float) -> float:
    return math.log(p / (1 - p))


def _sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def aggregate(prior: float, links: list[tuple[str, str, str]]) -> tuple[float, list[str]]:
    """links: (app, relation, strength). Returns (confidence, independent supporting apps)."""
    groups: dict[tuple[str, str], list[float]] = defaultdict(list)
    for app, relation, strength in links:
        if relation == Relation.NEUTRAL:
            continue
        groups[(app, relation)].append(STRENGTH_WEIGHT[Strength(strength)])
    total = _logit(prior)
    support_apps = []
    for (app, relation), weights in groups.items():
        contribution = sum(w * DIMINISHING**i for i, w in enumerate(sorted(weights, reverse=True)))
        if relation == Relation.SUPPORTS:
            total += contribution
            if contribution >= SOURCE_SUPPORT_MIN_WEIGHT:
                support_apps.append(app)
        else:
            total -= contribution
    return round(_sigmoid(total), 4), sorted(support_apps)


def provisional_status(confidence: float, support_apps: list[str], has_contradiction: bool) -> HypothesisStatus:
    if confidence >= SUPPORTED_THRESHOLD and len(support_apps) >= MIN_INDEPENDENT_SOURCES:
        return HypothesisStatus.SUPPORTED
    if confidence <= REJECT_THRESHOLD and has_contradiction:
        return HypothesisStatus.REJECTED
    return HypothesisStatus.CANDIDATE


class HypothesisEngine:
    def __init__(self, db: Database):
        self.db = db

    def generate(self, investigation_id: str) -> dict[str, str]:
        ids = {}
        with self.db.session() as s:
            for rank, template in enumerate(CATALOG.values()):
                hid = new_id("hyp")
                ids[template.kind] = hid
                s.add(
                    Hypothesis(
                        id=hid,
                        investigation_id=investigation_id,
                        kind=template.kind,
                        label=template.label,
                        statement=template.statement,
                        prior=template.prior,
                        confidence=template.prior,
                        status=HypothesisStatus.CANDIDATE.value,
                        rationale="Generated after the anomaly was established; not yet tested.",
                        rank=rank,
                    )
                )
        return ids

    def apply(self, investigation_id: str, assessments: list[Assessment], hypothesis_ids: dict[str, str], evidence_ids: dict[str, str]) -> int:
        applied = 0
        with self.db.session() as s:
            for a in assessments:
                hid = hypothesis_ids.get(a.hypothesis_kind)
                eid = evidence_ids.get(a.evidence_key, a.evidence_key)
                if hid is None or a.relation == Relation.NEUTRAL or s.get(EvidenceItem, eid) is None:
                    continue
                existing = s.scalar(
                    select(EvidenceLink).where(EvidenceLink.evidence_id == eid, EvidenceLink.hypothesis_id == hid)
                )
                if existing:
                    replace = a.assessed_by == "llm" and existing.assessed_by != "llm"
                    replace = replace or STRENGTH_RANK[Strength(a.strength)] > STRENGTH_RANK[Strength(existing.strength)]
                    if not replace:
                        continue
                    existing.relation, existing.strength = a.relation.value, Strength(a.strength).value
                    existing.rationale, existing.assessed_by = a.rationale, a.assessed_by
                else:
                    s.add(
                        EvidenceLink(
                            investigation_id=investigation_id,
                            evidence_id=eid,
                            hypothesis_id=hid,
                            relation=a.relation.value,
                            strength=Strength(a.strength).value,
                            rationale=a.rationale[:1000],
                            assessed_by=a.assessed_by,
                        )
                    )
                applied += 1
        return applied

    def views(self, investigation_id: str) -> list[HypothesisView]:
        with self.db.session() as s:
            hyps = s.scalars(
                select(Hypothesis).where(Hypothesis.investigation_id == investigation_id).order_by(Hypothesis.rank)
            ).all()
            links = s.scalars(select(EvidenceLink).where(EvidenceLink.investigation_id == investigation_id)).all()
            evidence = {
                e.id: e
                for e in s.scalars(select(EvidenceItem).where(EvidenceItem.investigation_id == investigation_id)).all()
            }
            by_hyp: dict[str, list[EvidenceLink]] = defaultdict(list)
            for link in links:
                by_hyp[link.hypothesis_id].append(link)

            views = []
            for h in hyps:
                link_views = [
                    LinkView(
                        evidence_id=l.evidence_id,
                        app=evidence[l.evidence_id].source_app,
                        relation=l.relation,
                        strength=l.strength,
                        rationale=l.rationale,
                        assessed_by=l.assessed_by,
                        title=evidence[l.evidence_id].title,
                    )
                    for l in by_hyp[h.id]
                    if l.evidence_id in evidence
                ]
                confidence, support_apps = aggregate(h.prior, [(l.app, l.relation, l.strength) for l in link_views])
                supporting = sorted(
                    [l for l in link_views if l.relation == Relation.SUPPORTS],
                    key=lambda l: -STRENGTH_RANK[Strength(l.strength)],
                )
                contradicting = sorted(
                    [l for l in link_views if l.relation == Relation.CONTRADICTS],
                    key=lambda l: -STRENGTH_RANK[Strength(l.strength)],
                )
                status = provisional_status(confidence, support_apps, bool(contradicting))
                rationale = _rationale(supporting, contradicting)
                h.confidence, h.status, h.rationale = confidence, status.value, rationale
                views.append(
                    HypothesisView(
                        id=h.id,
                        kind=h.kind,
                        label=h.label,
                        statement=h.statement,
                        prior=h.prior,
                        confidence=confidence,
                        status=status.value,
                        supporting=supporting,
                        contradicting=contradicting,
                        support_apps=support_apps,
                        rationale=rationale,
                    )
                )
            return views

    def finalize(self, investigation_id: str, statuses: dict[str, str], missing: dict[str, list[str]]) -> None:
        with self.db.session() as s:
            for h in s.scalars(select(Hypothesis).where(Hypothesis.investigation_id == investigation_id)).all():
                if h.id in statuses:
                    h.status = statuses[h.id]
                h.missing_information = missing.get(h.id, [])

    # --- async twins, for callers migrated to AsyncSession ---

    async def agenerate(self, investigation_id: str) -> dict[str, str]:
        ids = {}
        async with self.db.async_session() as s:
            for rank, template in enumerate(CATALOG.values()):
                hid = new_id("hyp")
                ids[template.kind] = hid
                s.add(
                    Hypothesis(
                        id=hid,
                        investigation_id=investigation_id,
                        kind=template.kind,
                        label=template.label,
                        statement=template.statement,
                        prior=template.prior,
                        confidence=template.prior,
                        status=HypothesisStatus.CANDIDATE.value,
                        rationale="Generated after the anomaly was established; not yet tested.",
                        rank=rank,
                    )
                )
        return ids

    async def aapply(
        self, investigation_id: str, assessments: list[Assessment], hypothesis_ids: dict[str, str], evidence_ids: dict[str, str]
    ) -> int:
        applied = 0
        async with self.db.async_session() as s:
            for a in assessments:
                hid = hypothesis_ids.get(a.hypothesis_kind)
                eid = evidence_ids.get(a.evidence_key, a.evidence_key)
                if hid is None or a.relation == Relation.NEUTRAL or (await s.get(EvidenceItem, eid)) is None:
                    continue
                existing = await s.scalar(
                    select(EvidenceLink).where(EvidenceLink.evidence_id == eid, EvidenceLink.hypothesis_id == hid)
                )
                if existing:
                    replace = a.assessed_by == "llm" and existing.assessed_by != "llm"
                    replace = replace or STRENGTH_RANK[Strength(a.strength)] > STRENGTH_RANK[Strength(existing.strength)]
                    if not replace:
                        continue
                    existing.relation, existing.strength = a.relation.value, Strength(a.strength).value
                    existing.rationale, existing.assessed_by = a.rationale, a.assessed_by
                else:
                    s.add(
                        EvidenceLink(
                            investigation_id=investigation_id,
                            evidence_id=eid,
                            hypothesis_id=hid,
                            relation=a.relation.value,
                            strength=Strength(a.strength).value,
                            rationale=a.rationale[:1000],
                            assessed_by=a.assessed_by,
                        )
                    )
                applied += 1
        return applied

    async def aviews(self, investigation_id: str) -> list[HypothesisView]:
        async with self.db.async_session() as s:
            hyps = (
                await s.scalars(
                    select(Hypothesis).where(Hypothesis.investigation_id == investigation_id).order_by(Hypothesis.rank)
                )
            ).all()
            links = (
                await s.scalars(select(EvidenceLink).where(EvidenceLink.investigation_id == investigation_id))
            ).all()
            evidence = {
                e.id: e
                for e in (
                    await s.scalars(select(EvidenceItem).where(EvidenceItem.investigation_id == investigation_id))
                ).all()
            }
            by_hyp: dict[str, list[EvidenceLink]] = defaultdict(list)
            for link in links:
                by_hyp[link.hypothesis_id].append(link)

            views = []
            for h in hyps:
                link_views = [
                    LinkView(
                        evidence_id=l.evidence_id,
                        app=evidence[l.evidence_id].source_app,
                        relation=l.relation,
                        strength=l.strength,
                        rationale=l.rationale,
                        assessed_by=l.assessed_by,
                        title=evidence[l.evidence_id].title,
                    )
                    for l in by_hyp[h.id]
                    if l.evidence_id in evidence
                ]
                confidence, support_apps = aggregate(h.prior, [(l.app, l.relation, l.strength) for l in link_views])
                supporting = sorted(
                    [l for l in link_views if l.relation == Relation.SUPPORTS],
                    key=lambda l: -STRENGTH_RANK[Strength(l.strength)],
                )
                contradicting = sorted(
                    [l for l in link_views if l.relation == Relation.CONTRADICTS],
                    key=lambda l: -STRENGTH_RANK[Strength(l.strength)],
                )
                status = provisional_status(confidence, support_apps, bool(contradicting))
                rationale = _rationale(supporting, contradicting)
                h.confidence, h.status, h.rationale = confidence, status.value, rationale
                views.append(
                    HypothesisView(
                        id=h.id,
                        kind=h.kind,
                        label=h.label,
                        statement=h.statement,
                        prior=h.prior,
                        confidence=confidence,
                        status=status.value,
                        supporting=supporting,
                        contradicting=contradicting,
                        support_apps=support_apps,
                        rationale=rationale,
                    )
                )
            return views

    async def afinalize(self, investigation_id: str, statuses: dict[str, str], missing: dict[str, list[str]]) -> None:
        async with self.db.async_session() as s:
            result = await s.scalars(select(Hypothesis).where(Hypothesis.investigation_id == investigation_id))
            for h in result.all():
                if h.id in statuses:
                    h.status = statuses[h.id]
                h.missing_information = missing.get(h.id, [])


def _summarize(links: list[LinkView]) -> str:
    counts = Counter((l.rationale, l.app, l.strength) for l in links)
    return "; ".join(
        f"{rationale} [{app}, {strength}]" + (f" ×{n}" if n > 1 else "")
        for (rationale, app, strength), n in list(counts.items())[:4]
    )


def _rationale(supporting: list[LinkView], contradicting: list[LinkView]) -> str:
    if not supporting and not contradicting:
        return "No evidence linked yet."
    parts = []
    if supporting:
        parts.append("Supported by: " + _summarize(supporting) + ".")
    if contradicting:
        parts.append("Contradicted by: " + _summarize(contradicting) + ".")
    return " ".join(parts)
