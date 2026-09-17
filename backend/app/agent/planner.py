"""Chooses the next probe. Candidates and stop conditions are computed deterministically; in LLM
mode the model picks among valid candidates and explains why. It cannot add steps or skip policy."""

import json
from dataclasses import dataclass, field

from app.agent.hypotheses import CATALOG, MIN_INDEPENDENT_SOURCES, STOP_THRESHOLD
from app.agent.probes import PROBES, UNLOCKS, ProbeDef
from app.agent.types import HypothesisView, InvestigationState
from app.enums import HypothesisStatus, ReasoningMode
from app.llm.client import LLMError, StructuredLLM

MIN_CANDIDATE_SCORE = 0.3
RELEASE_BONUS = 1.5
FOLLOW_UP_BONUS = 1.0
UNTESTED_BONUS = 0.5

# Personas that ask Surge to keep digging past the confidence threshold rather than stop as soon
# as it's confident enough — depth, not just wording, is what "persona" is meant to change.
THOROUGH_PERSONAS = {"engineer"}


def is_tested(view: HypothesisView, state: InvestigationState) -> bool:
    """A hypothesis counts as tested once it has non-weak evidence either way, or once a probe that
    primarily targets it has run. Weak timing-only links do not count."""
    if any(link.strength != "weak" for link in (*view.supporting, *view.contradicting)):
        return True
    return any(
        state.probe_status.get(p.id) == "ok" and p.discriminates.get(view.kind, 0) >= 0.9 for p in PROBES.values()
    )


@dataclass
class Candidate:
    probe: ProbeDef
    score: float
    targets: list[str]
    unlocked: bool

    def public(self) -> dict:
        return {"probe_id": self.probe.id, "title": self.probe.title, "app": self.probe.app.value, "score": round(self.score, 2), "targets": self.targets}


@dataclass
class Decision:
    probe_id: str
    reason: str
    expected_information: list[str]
    decided_by: str
    score: float
    candidates: list[dict] = field(default_factory=list)
    fallback_reason: str | None = None
    model: str | None = None


PLANNER_SYSTEM = """You are the planning module of Surge, an evidence-first incident investigation agent.
Pick the single most useful next investigation step from the candidate list.

Guidance:
- Prefer steps that best separate the hypotheses that are still plausible.
- Follow up on a fresh lead from the previous step when it can confirm or rule out the leading hypothesis.
- Do not choose a step only because it is cheap; choose it because its result would change what we believe.
- The backend score is a heuristic hint. You may disagree when the investigation context warrants it.
- Write the reason as one or two plain sentences for an engineer watching the live timeline. Do not claim results you have not seen."""


class Planner:
    def __init__(self, llm: StructuredLLM):
        self.llm = llm

    def candidates(self, state: InvestigationState, views: list[HypothesisView]) -> tuple[list[Candidate], list[tuple[ProbeDef, str]]]:
        by_kind = {v.kind: v for v in views}
        out: list[Candidate] = []
        not_applicable: list[tuple[ProbeDef, str]] = []
        for probe in PROBES.values():
            if probe.id == "establish_anomaly" or probe.id in state.probe_status:
                continue
            if probe.app.value in state.failed_apps:
                continue
            readiness, reason = probe.readiness(state)
            if readiness == "not_applicable":
                not_applicable.append((probe, reason))
                continue
            if readiness == "not_ready":
                continue
            score, targets = 0.0, []
            for kind, weight in probe.discriminates.items():
                view = by_kind.get(kind)
                if view is None or view.status == HypothesisStatus.REJECTED:
                    continue
                info = 4 * view.confidence * (1 - view.confidence) + (0 if is_tested(view, state) else UNTESTED_BONUS)
                score += weight * info
                if weight >= 0.5:
                    targets.append(kind)
            unlocked = probe.id in UNLOCKS.get(state.last_probe or "", ())
            if probe.id == "check_recent_deployments" and state.intent.mentions_release:
                score += RELEASE_BONUS
            if unlocked:
                score += FOLLOW_UP_BONUS
            score -= probe.cost
            if score >= MIN_CANDIDATE_SCORE:
                out.append(Candidate(probe, score, targets, unlocked))
        out.sort(key=lambda c: -c.score)
        return out, not_applicable

    def sufficiency(self, state: InvestigationState, views: list[HypothesisView], candidates: list[Candidate]) -> dict:
        ranked = sorted(views, key=lambda v: -v.confidence)
        top = ranked[0]
        testable = {k for c in candidates for k in c.targets}
        untested = [
            v.label
            for v in ranked[1:]
            if v.status != HypothesisStatus.REJECTED and not is_tested(v, state) and v.kind in testable
        ]
        temporal_pending = (
            state.intent.mentions_release
            and "check_recent_deployments" not in state.probe_status
            and "github" not in state.failed_apps
        )
        checks = {
            "top_confidence_at_least_%.2f" % STOP_THRESHOLD: top.confidence >= STOP_THRESHOLD,
            "independent_supporting_sources": len(top.support_apps) >= MIN_INDEPENDENT_SOURCES,
            "alternatives_tested": not untested,
            "release_timing_checked": not temporal_pending,
        }
        if state.persona in THOROUGH_PERSONAS:
            # Thorough mode: don't stop just because we're confident enough — stop only once no
            # further step is scored as useful (planner truly has nothing left to check).
            checks["no_remaining_leads_(thorough_mode)"] = not candidates
        return {
            "sufficient": all(checks.values()),
            "checks": checks,
            "leading_hypothesis": top.kind,
            "leading_confidence": top.confidence,
            "untested_alternatives": untested,
        }

    async def decide(self, state: InvestigationState, views: list[HypothesisView], candidates: list[Candidate]) -> Decision:
        heuristic = self._heuristic(state, candidates)
        if state.reasoning != ReasoningMode.LLM or not self.llm.available:
            return heuristic
        try:
            result = await self.llm.complete_json(
                purpose="plan_next_step",
                system=PLANNER_SYSTEM,
                prompt=self._prompt(state, views, candidates),
                schema=self._schema([c.probe.id for c in candidates]),
                max_tokens=1500,
                trace_id=state.investigation_id,
            )
            data = result.data
            chosen = next((c for c in candidates if c.probe.id == data.get("probe_id")), None)
            if chosen is None:
                raise LLMError(f"Planner chose an invalid step: {data.get('probe_id')!r}")
            reason = str(data.get("reason", "")).strip()[:500] or heuristic.reason
            expected = [str(x)[:120] for x in (data.get("expected_information") or [])][:4] or chosen.probe.expected_information
            return Decision(chosen.probe.id, reason, expected, "llm", chosen.score, heuristic.candidates, model=result.route)
        except LLMError as exc:
            heuristic.fallback_reason = str(exc)
            return heuristic

    def _heuristic(self, state: InvestigationState, candidates: list[Candidate]) -> Decision:
        best = candidates[0]
        labels = [CATALOG[k].label.lower() for k in best.targets]
        if best.probe.id == "check_recent_deployments" and state.intent.mentions_release:
            reason = (
                "The request points at a release, and a code-level cause needs something to have shipped just before the drop. "
                "Check what was deployed around the onset."
            )
        elif best.unlocked:
            purpose = best.probe.purpose
            reason = f"Follow up on the previous step: {purpose[0].lower()}{purpose[1:]}"
        elif not labels:
            reason = f"{best.probe.purpose} This narrows down the remaining candidates."
        elif len(labels) == 1:
            reason = f"{best.probe.purpose} This directly tests the {labels[0]} hypothesis."
        else:
            reason = f"{best.probe.purpose} This helps separate {', '.join(labels[:-1])} and {labels[-1]}."
        return Decision(
            best.probe.id, reason, best.probe.expected_information, "heuristic", best.score,
            [c.public() for c in candidates],
        )

    @staticmethod
    def _schema(ids: list[str]) -> dict:
        return {
            "type": "object",
            "properties": {
                "probe_id": {"type": "string", "enum": ids},
                "reason": {"type": "string"},
                "expected_information": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["probe_id", "reason", "expected_information"],
            "additionalProperties": False,
        }

    @staticmethod
    def _prompt(state: InvestigationState, views: list[HypothesisView], candidates: list[Candidate]) -> str:
        anomaly = state.anomaly or {}
        summary = {
            "request": state.request,
            "anomaly": {
                "metric": state.intent.metric_label,
                "relative_change": anomaly.get("relative_change"),
                "onset": anomaly["onset"].isoformat() if anomaly.get("onset") else None,
            },
            "request_mentions_release": state.intent.mentions_release,
            "previous_step": state.last_probe,
            "completed_steps": state.probe_status,
            "unavailable_sources": {app: info.get("code") for app, info in state.failed_apps.items()},
            "hypotheses": [
                {
                    "kind": v.kind,
                    "label": v.label,
                    "confidence": v.confidence,
                    "status": v.status,
                    "supporting": [f"{l.title} ({l.strength})" for l in v.supporting[:4]],
                    "contradicting": [f"{l.title} ({l.strength})" for l in v.contradicting[:4]],
                }
                for v in views
            ],
            "candidates": [
                {
                    "probe_id": c.probe.id,
                    "title": c.probe.title,
                    "source": c.probe.app.value,
                    "purpose": c.probe.purpose,
                    "tests": c.targets,
                    "heuristic_score": round(c.score, 2),
                }
                for c in candidates
            ],
        }
        return "Current investigation state (JSON):\n" + json.dumps(summary, ensure_ascii=False, indent=1)
