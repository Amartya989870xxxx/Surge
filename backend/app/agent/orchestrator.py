"""The stateful investigation loop: observe → hypothesize → test → synthesize → act → verify."""

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select

from app.actions.idempotency import action_marker, idempotency_key, incident_fingerprint, incident_marker
from app.actions.proposals import find_existing_incident, issue_title, render_findings
from app.agent.assessor import assess_with_llm
from app.agent.hypotheses import CATALOG
from app.agent.intent import parse_intent
from app.agent.policy import approval_required, risk_for
from app.agent.probes import PROBES, ProbeContext, ProbeDef
from app.agent.state import InvalidTransition
from app.agent.synthesizer import DISPLAY, SOURCE_CONTEXT
from app.agent.types import HypothesisView, InvestigationState, ProbeOutcome
from app.db.models import Action, Claim, EvidenceItem, Investigation, new_id
from app.enums import (
    TERMINAL_STATUSES,
    Actor,
    App,
    ApprovalMode,
    ApprovalStatus,
    ClaimType,
    ConnectorMode,
    EventType,
    ExecutionMode,
    ExecutionStatus,
    InvestigationStatus,
    Outcome,
    ReasoningMode,
    Strength,
    VerificationStatus,
)
from app.errors import CONNECTOR_LEVEL_CODES, ErrorCode, SurgeAPIError
from app.llm.client import LLMError
from app.tools.base import ToolContext

logger = logging.getLogger("surge.orchestrator")
S = InvestigationStatus
_CONNECTOR_LEVEL = {c.value for c in CONNECTOR_LEVEL_CODES}


def _title(request: str) -> str:
    first = request.strip().split("\n", 1)[0]
    for sep in (". ", "? ", "! "):
        if sep in first:
            first = first.split(sep, 1)[0]
            break
    return first[:120]


def _range_dict(time_range) -> dict | None:
    if not time_range:
        return None
    if hasattr(time_range, "model_dump"):
        time_range = time_range.model_dump()
    return {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in time_range.items()}


def _checks_summary(sufficiency: dict) -> str:
    return "; ".join(f"{k.replace('_', ' ')}: {'yes' if ok else 'no'}" for k, ok in sufficiency["checks"].items())


class Orchestrator:
    def __init__(self, services):
        self.s = services

    # ------------------------------------------------------------------ creation

    def create_investigation(
        self,
        *,
        request: str,
        time_range=None,
        connector_mode: ConnectorMode | str | None = None,
        disabled_apps: list | None = None,
        connector_profile: dict | None = None,
        scenario_id: str | None = None,
        faults: list[dict] | None = None,
        approval_mode: ApprovalMode | str = ApprovalMode.REQUIRED,
        reasoning: ReasoningMode | str | None = None,
        execution_mode: ExecutionMode | None = None,
        world_key: str | None = None,
        latency_ms: int | None = None,
        session_id: str = "anonymous",
        persona: str | None = None,
    ) -> str:
        s = self.s
        profile = connector_profile or s.connectors.default_profile(
            ConnectorMode(connector_mode) if connector_mode else None,
            [App(a).value for a in (disabled_apps or [])],
        )
        modes = set(profile.values()) - {ConnectorMode.DISABLED.value}
        if ConnectorMode.DEMO.value in modes:
            scenario_id = scenario_id or s.settings.demo_scenario
            try:
                s.library.get(scenario_id)
            except KeyError as exc:
                raise SurgeAPIError(ErrorCode.NOT_FOUND, f"Unknown demo scenario '{scenario_id}'", http_status=404) from exc
            world_key = world_key or f"demo:{scenario_id}"
        else:
            scenario_id, world_key = None, None

        reasoning = ReasoningMode(reasoning) if reasoning else s.settings.resolved_reasoning_mode()
        if reasoning == ReasoningMode.LLM and not s.llm.available:
            raise SurgeAPIError(
                ErrorCode.INVALID_STATE, "LLM reasoning requested but no Groq or Gemini API key is configured", http_status=409
            )
        if execution_mode is None:
            execution_mode = ExecutionMode.INTERACTIVE if ConnectorMode.REAL.value in modes else ExecutionMode.DEMO
        mode_label = "MIXED" if len(modes) > 1 else (next(iter(modes)) if modes else ConnectorMode.DISABLED.value)
        latency = s.settings.demo_latency_ms if latency_ms is None else latency_ms
        requested_range = _range_dict(time_range)

        inv_id = new_id("inv")
        with s.db.session() as db:
            db.add(
                Investigation(
                    id=inv_id,
                    session_id=session_id,
                    title=_title(request),
                    user_request=request,
                    status=S.CREATED.value,
                    execution_mode=ExecutionMode(execution_mode).value,
                    connector_mode=mode_label,
                    reasoning_mode=reasoning.value,
                    approval_mode=ApprovalMode(approval_mode).value,
                    scenario_id=scenario_id,
                    world_key=world_key,
                    fault_injection=faults or [],
                    connector_profile={"apps": profile, "latency_ms": latency},
                    intent={"requested_time_range": requested_range, "persona": persona},
                )
            )
        s.bus.publish(
            inv_id,
            EventType.INVESTIGATION_CREATED,
            "Investigation created",
            actor=Actor.USER,
            status=S.CREATED.value,
            summary=request[:500],
            data={
                "connectors": profile,
                "reasoning_mode": reasoning.value,
                "approval_mode": ApprovalMode(approval_mode).value,
                "scenario_id": scenario_id,
                "injected_faults": faults or [],
                "persona": persona,
            },
        )
        return inv_id

    def rerun(self, investigation_id: str, *, clear_faults: bool = True) -> str:
        with self.s.db.session() as db:
            inv = db.get(Investigation, investigation_id)
            if inv is None:
                raise SurgeAPIError(ErrorCode.NOT_FOUND, "Investigation not found", http_status=404)
            db.expunge(inv)
        if inv.execution_mode == ExecutionMode.EVALUATION:
            raise SurgeAPIError(ErrorCode.INVALID_STATE, "Evaluation runs cannot be re-run from the API", http_status=409)
        return self.create_investigation(
            request=inv.user_request,
            time_range=(inv.intent or {}).get("requested_time_range"),
            connector_profile=(inv.connector_profile or {}).get("apps"),
            scenario_id=inv.scenario_id,
            faults=[] if clear_faults else inv.fault_injection,
            approval_mode=inv.approval_mode,
            reasoning=inv.reasoning_mode,
            world_key=inv.world_key,
            latency_ms=(inv.connector_profile or {}).get("latency_ms"),
            session_id=inv.session_id,
            persona=(inv.intent or {}).get("persona"),
        )

    # ------------------------------------------------------------------ run

    async def run(self, investigation_id: str) -> None:
        try:
            async with asyncio.timeout(self.s.settings.investigation_timeout_s):
                await self._investigate(investigation_id)
        except TimeoutError:
            self._terminate(investigation_id, S.TIMED_OUT, "Investigation exceeded its time budget")
        except asyncio.CancelledError:
            self._terminate(investigation_id, S.CANCELLED, "Cancelled")
        except Exception as exc:
            logger.exception("Investigation %s crashed", investigation_id)
            self._terminate(
                investigation_id,
                S.FAILED,
                f"Internal error ({type(exc).__name__}); state up to this point is preserved",
                error={"code": ErrorCode.INTERNAL.value, "type": type(exc).__name__},
            )

    async def _investigate(self, inv_id: str) -> None:
        s = self.s
        with s.db.session() as db:
            inv = db.get(Investigation, inv_id)
            db.expunge(inv)
        connectors = s.runtime.connectors_for(inv)
        simulated_clock = connectors.world is not None and all(
            h.mode != ConnectorMode.REAL for h in connectors.handles.values()
        )
        now = connectors.world.reference_time if simulated_clock else datetime.now(UTC)
        requested = (inv.intent or {}).get("requested_time_range")
        persona = (inv.intent or {}).get("persona")
        intent = parse_intent(inv.user_request, requested, now)
        state = InvestigationState(inv_id, inv.user_request, intent, now, ReasoningMode(inv.reasoning_mode), persona=persona)

        s.lifecycle.transition(
            inv_id,
            S.PLANNING,
            reason="Interpreting the request",
            time_window_start=intent.window_start,
            time_window_end=intent.window_end,
            intent={"requested_time_range": requested, "persona": persona, "simulated_clock": simulated_clock, **intent.to_dict()},
            severity=intent.severity,
        )
        for app, handle in connectors.handles.items():
            if handle.mode == ConnectorMode.DISABLED:
                state.failed_apps[app.value] = {
                    "code": ErrorCode.CONNECTOR_DISABLED.value,
                    "message": "Disabled for this investigation",
                    "event_sequence": None,
                }
            elif handle.client is None:
                event = s.bus.publish(
                    inv_id, EventType.DEGRADED, f"{DISPLAY[app.value]} is not connected",
                    actor=Actor.SYSTEM, external_app=app.value, status="unavailable", summary=handle.detail,
                    error_code=ErrorCode.CONNECTOR_UNAVAILABLE.value,
                )
                state.failed_apps[app.value] = {
                    "code": ErrorCode.CONNECTOR_UNAVAILABLE.value,
                    "message": handle.detail,
                    "event_sequence": event["sequence"],
                }

        establish = PROBES["establish_anomaly"]
        s.bus.publish(
            inv_id,
            EventType.PLAN,
            f"Establish whether {intent.metric_label} actually changed",
            external_app=establish.app.value,
            summary="Read the raw metrics before forming any hypothesis, so the anomaly is discovered from data rather than assumed from the request.",
            data={
                "probe_id": establish.id,
                "decided_by": "policy",
                "expected_information": establish.expected_information,
                "window": {"start": intent.window_start.isoformat(), "end": intent.window_end.isoformat()},
            },
        )
        s.lifecycle.transition(inv_id, S.INVESTIGATING, reason="Gathering evidence")
        await self._run_probe(state, establish, connectors)

        if state.anomaly and state.anomaly.get("detected"):
            state.hypothesis_ids = s.engine.generate(inv_id)
            views = s.engine.views(inv_id)
            s.bus.publish(
                inv_id,
                EventType.HYPOTHESES_GENERATED,
                f"Generated {len(views)} competing hypotheses",
                summary="; ".join(v.label for v in views),
                hypothesis_ids=[v.id for v in views],
                data={
                    "hypotheses": [
                        {"id": v.id, "kind": v.kind, "label": v.label, "statement": v.statement, "prior": v.prior}
                        for v in views
                    ]
                },
            )
            await self._investigation_loop(state, connectors)

        s.lifecycle.transition(inv_id, S.SYNTHESIZING, reason="Weighing the evidence", tool_call_count=state.tool_calls)
        await self._synthesize_and_act(state, connectors)

    async def _investigation_loop(self, state: InvestigationState, connectors) -> None:
        s = self.s
        inv_id = state.investigation_id
        while True:
            if s.runtime.is_cancelled(inv_id):
                raise asyncio.CancelledError()
            views = s.engine.views(inv_id)
            candidates, not_applicable = s.planner.candidates(state, views)
            for probe, reason in not_applicable:
                state.probe_status[probe.id] = "not_applicable"
                state.probe_notes[probe.id] = reason
                s.bus.publish(
                    inv_id, EventType.NOT_APPLICABLE, f"Skipped: {probe.title}",
                    external_app=probe.app.value, summary=reason, data={"probe_id": probe.id},
                )
            sufficiency = s.planner.sufficiency(state, views, candidates)
            stop = None
            if sufficiency["sufficient"]:
                stop = "Evidence is sufficient — stopping the investigation"
            elif not candidates:
                stop = "No remaining step would change the conclusion — stopping"
            elif state.tool_calls >= s.settings.max_tool_calls:
                stop = f"Tool-call budget of {s.settings.max_tool_calls} reached — stopping"
            if stop:
                s.bus.publish(
                    inv_id, EventType.SUFFICIENCY_CHECK, stop, summary=_checks_summary(sufficiency),
                    hypothesis_ids=[v.id for v in views], data=sufficiency,
                )
                return

            decision = await s.planner.decide(state, views, candidates)
            if decision.fallback_reason:
                s.bus.publish(
                    inv_id, EventType.LLM_FALLBACK, "Planner LLM unavailable; used the deterministic planner",
                    actor=Actor.SYSTEM, summary=decision.fallback_reason[:300], data={"component": "planner", "fallback_to": "heuristic"},
                )
            probe = PROBES[decision.probe_id]
            state.decisions.append({"probe_id": probe.id, "decided_by": decision.decided_by, "score": round(decision.score, 3)})
            s.bus.publish(
                inv_id,
                EventType.PLAN,
                probe.title,
                external_app=probe.app.value,
                summary=decision.reason,
                data={
                    "probe_id": probe.id,
                    "decided_by": decision.decided_by,
                    "model": decision.model,
                    "score": round(decision.score, 2),
                    "expected_information": decision.expected_information,
                    "candidates": decision.candidates,
                    "sufficiency": sufficiency["checks"],
                    "leading_hypothesis": sufficiency["leading_hypothesis"],
                    "leading_confidence": sufficiency["leading_confidence"],
                },
            )
            await self._run_probe(state, probe, connectors)

    async def _run_probe(self, state: InvestigationState, probe: ProbeDef, connectors) -> None:
        s = self.s
        inv_id = state.investigation_id
        outcome = await probe.run(ProbeContext(state, s.runner, ToolContext(inv_id, connectors), s.settings))
        state.tool_calls += outcome.tool_calls
        state.last_probe = probe.id
        state.probe_status[probe.id] = outcome.status
        state.probe_notes[probe.id] = outcome.note

        if outcome.status == "failed":
            self._record_failure(state, probe, outcome)
            return
        if outcome.status == "not_applicable":
            s.bus.publish(
                inv_id, EventType.NOT_APPLICABLE, f"Skipped: {probe.title}",
                external_app=probe.app.value, summary=outcome.note, data={"probe_id": probe.id},
            )
            return

        state.succeeded_apps.add(probe.app.value)
        if probe.id == "establish_anomaly":
            state.anomaly = outcome.facts.get("anomaly")

        assessments = list(outcome.assessments)
        assessable = [d for d in outcome.evidence if d.llm_assessable]
        if assessable and state.hypothesis_ids and state.reasoning == ReasoningMode.LLM and s.llm.available:
            try:
                llm_assessments = await assess_with_llm(s.llm, state, assessable)
                keys = {d.key for d in assessable}
                assessments = [a for a in assessments if a.evidence_key not in keys] + llm_assessments
            except LLMError as exc:
                s.bus.publish(
                    inv_id, EventType.LLM_FALLBACK, "LLM evidence assessment unavailable; used the deterministic classifier",
                    actor=Actor.SYSTEM, summary=str(exc)[:300], data={"component": "assessor", "fallback_to": "heuristic"},
                )

        linked = {a.evidence_key for a in assessments}
        onset = state.anomaly.get("onset") if state.anomaly else None
        kept = [d for d in outcome.evidence if d.source_type != "message" or d.key in linked]
        for draft in kept:
            mode = connectors.mode(draft.source_app).value
            eid, created = s.evidence.add(inv_id, draft, mode=mode, probe_id=probe.id, onset=onset)
            state.evidence_ids[draft.key] = eid
            if draft.source_type == "metric_anomaly":
                state.anomaly_evidence_id = eid
            if not created:
                continue
            relations = [
                {
                    "hypothesis": a.hypothesis_kind,
                    "relation": a.relation.value,
                    "strength": Strength(a.strength).value,
                    "rationale": a.rationale,
                    "assessed_by": a.assessed_by,
                }
                for a in assessments
                if a.evidence_key == draft.key
            ]
            s.bus.publish(
                inv_id,
                EventType.ANOMALY if draft.source_type == "metric_anomaly" else EventType.EVIDENCE,
                draft.title,
                external_app=draft.source_app,
                summary=draft.content[:500],
                evidence_ids=[eid],
                data={
                    "source_type": draft.source_type,
                    "relations": relations,
                    "url": draft.url,
                    "observed_at": draft.observed_at.isoformat() if draft.observed_at else None,
                    "connector_mode": mode,
                },
            )
        if probe.id == "search_slack_reports" and not kept:
            s.bus.publish(
                inv_id, EventType.EVIDENCE, "No relevant team reports found", external_app="slack",
                summary=(
                    f"{outcome.facts.get('hits', 0)} message(s) matched the search but none bear on the hypotheses. "
                    "Absence of reports is not treated as evidence against any hypothesis."
                ),
                data={"absence": True, "hits": outcome.facts.get("hits", 0)},
            )

        if state.hypothesis_ids and assessments:
            before = {v.kind: v.confidence for v in s.engine.views(inv_id)}
            s.engine.apply(inv_id, assessments, state.hypothesis_ids, state.evidence_ids)
            views = s.engine.views(inv_id)
            moved = sorted(
                [v for v in views if abs(v.confidence - before[v.kind]) >= 0.01],
                key=lambda v: -abs(v.confidence - before[v.kind]),
            )
            if moved:
                s.bus.publish(
                    inv_id,
                    EventType.HYPOTHESIS_UPDATED,
                    "; ".join(f"{v.label} {before[v.kind]:.2f} → {v.confidence:.2f}" for v in moved[:3]),
                    summary=moved[0].rationale[:500],
                    hypothesis_ids=[v.id for v in moved],
                    data={
                        "hypotheses": [
                            {
                                "id": v.id,
                                "kind": v.kind,
                                "label": v.label,
                                "confidence": v.confidence,
                                "previous": before[v.kind],
                                "status": v.status,
                                "independent_sources": v.support_apps,
                            }
                            for v in views
                        ]
                    },
                )

    def _record_failure(self, state: InvestigationState, probe: ProbeDef, outcome: ProbeOutcome) -> None:
        s = self.s
        inv_id = state.investigation_id
        error = outcome.failed_tool.error
        app = probe.app.value
        if app in state.failed_apps:
            return
        if error.code in _CONNECTOR_LEVEL or app not in state.succeeded_apps:
            state.failed_apps[app] = {
                "code": error.code,
                "message": error.message,
                "event_sequence": outcome.failed_tool.event_sequence,
            }
            remaining = [DISPLAY[a.value] for a in App if a.value not in state.failed_apps]
            s.bus.publish(
                inv_id,
                EventType.DEGRADED,
                f"{DISPLAY[app]} unavailable — continuing without it",
                actor=Actor.SYSTEM,
                external_app=app,
                status="degraded",
                error_code=error.code,
                summary=(
                    f"{error.message}. {SOURCE_CONTEXT[app].capitalize()} could not be checked. "
                    f"Continuing with {', '.join(remaining) or 'no other sources'}. Missing evidence is not treated as "
                    "evidence against any hypothesis; confidence is reduced where this source mattered."
                ),
                data={"missing_source": app, "probe_id": probe.id, "remaining_sources": remaining},
            )
        else:
            s.bus.publish(
                inv_id, EventType.DEGRADED, f"{probe.title} failed — continuing",
                actor=Actor.SYSTEM, external_app=app, status="degraded", error_code=error.code,
                summary=error.message, data={"probe_id": probe.id},
            )

    # ------------------------------------------------------------------ synthesis & actions

    async def _synthesize_and_act(self, state: InvestigationState, connectors) -> None:
        s = self.s
        inv_id = state.investigation_id
        views = s.engine.views(inv_id) if state.hypothesis_ids else []
        evidence_rows = s.evidence.list(inv_id)
        synthesis, decision = await s.synthesizer.build(state, views, evidence_rows)
        if synthesis.get("llm_error"):
            s.bus.publish(
                inv_id, EventType.LLM_FALLBACK, "Narrative LLM unavailable; used the template summary",
                actor=Actor.SYSTEM, summary=synthesis["llm_error"][:300], data={"component": "synthesizer", "fallback_to": "heuristic"},
            )
        breakdown = synthesis.get("confidence_breakdown") or {}
        if breakdown and (breakdown["coverage_factor"] < 1 or breakdown["caps"]):
            reasons = [f"{DISPLAY[a]} unavailable ({SOURCE_CONTEXT[a]})" for a in breakdown["missing_sources"]]
            reasons += [c["reason"] for c in breakdown["caps"]]
            s.bus.publish(
                inv_id, EventType.POLICY,
                f"Confidence adjusted from {breakdown['posterior']:.2f} to {breakdown['final']:.2f}",
                actor=Actor.SYSTEM, summary="; ".join(reasons), data={"confidence_breakdown": breakdown},
            )

        outcome = Outcome(synthesis["outcome"])
        selected: HypothesisView | None = decision["selected"]
        if outcome == Outcome.DIAGNOSIS:
            title = f"Strongest supported hypothesis: {selected.label} ({synthesis['confidence']:.2f})"
        elif outcome == Outcome.INSUFFICIENT_EVIDENCE:
            title = "Insufficient evidence to identify a cause"
        else:
            title = "No significant anomaly found"
        s.bus.publish(
            inv_id,
            EventType.SYNTHESIS,
            title,
            summary=synthesis["summary"],
            evidence_ids=synthesis["evidence_ids"],
            hypothesis_ids=[h["id"] for h in synthesis["hypotheses"]],
            data={
                "outcome": outcome.value,
                "confidence": synthesis["confidence"],
                "confidence_breakdown": breakdown,
                "summary_source": synthesis["summary_source"],
                "llm_model": synthesis.get("llm_model"),
                "uncertainties": synthesis["uncertainties"],
            },
        )
        s.lifecycle.update(
            inv_id,
            outcome=outcome.value,
            final_summary=synthesis["summary"],
            final_confidence=synthesis["confidence"],
            confidence_breakdown=breakdown or None,
            root_cause_hypothesis_id=selected.id if selected else None,
            synthesis=synthesis,
            degraded=bool(state.failed_apps),
            missing_sources=sorted(state.failed_apps),
            tool_call_count=state.tool_calls,
        )

        if outcome != Outcome.DIAGNOSIS:
            final = S.PARTIAL if state.anomaly is None else S.COMPLETED
            s.lifecycle.transition(inv_id, final, reason=synthesis.get("reason"))
            s.bus.publish(
                inv_id, EventType.COMPLETED,
                "Investigation complete" if final == S.COMPLETED else "Investigation ended with partial results",
                actor=Actor.SYSTEM, status=final.value, summary=synthesis["summary"][:500],
            )
            return
        await self._propose_action(state, synthesis, selected, views, evidence_rows, connectors)

    @staticmethod
    def _claim(inv_id: str, text: str, ids: list[str], hypothesis_id: str | None, valid: set[str]) -> Claim:
        return Claim(
            id=new_id("clm"),
            investigation_id=inv_id,
            claim_type=ClaimType.RECOMMENDATION.value,
            text=text,
            evidence_ids=ids,
            hypothesis_id=hypothesis_id,
            requires_evidence=True,
            grounded=bool(ids) and all(i in valid for i in ids),
            source="backend",
            position=999,
        )

    async def _propose_action(
        self,
        state: InvestigationState,
        synthesis: dict,
        selected: HypothesisView,
        views: list[HypothesisView],
        evidence_rows: list[EvidenceItem],
        connectors,
    ) -> None:
        s = self.s
        inv_id = state.investigation_id
        template = CATALOG[selected.kind]
        evidence = {e.id: e for e in evidence_rows}
        supporting_ids = [l.evidence_id for l in selected.supporting[:8]]
        onset = state.anomaly["onset"]
        fingerprint = incident_fingerprint(state.intent.metric, selected.kind, onset)

        if "github" in state.failed_apps:
            await self._block_action(state, synthesis, selected, supporting_ids, set(evidence),
                                     f"GitHub is unavailable ({state.failed_apps['github']['code']})")
            return

        ctx = ToolContext(inv_id, connectors)
        existing = await s.runner.call(
            ctx, "github.list_issues", {"state": "open"}, purpose="Check for an existing incident before proposing a new one"
        )
        if not existing.success:
            await self._block_action(state, synthesis, selected, supporting_ids, set(evidence),
                                     f"the duplicate-incident check failed ({existing.error.code})")
            return

        repo = connectors.client(App.GITHUB).repo
        duplicate = find_existing_incident(existing.items, fingerprint, selected.kind, onset)
        key_target = f"{repo}#{duplicate['number']}" if duplicate else repo
        action_type = "comment_github_issue" if duplicate else "create_github_issue"
        key = idempotency_key(inv_id, action_type, key_target)
        markers = [action_marker(key), incident_marker(fingerprint)]
        body = render_findings(
            investigation_id=inv_id, synthesis=synthesis, selected=selected, views=views,
            evidence=evidence, marker_lines=markers,
        )
        if duplicate:
            display_title = f"Add Surge findings to existing incident #{duplicate['number']}"
            parameters = {
                "issue_number": duplicate["number"],
                "existing_title": duplicate["title"],
                "body": body,
                "markers": [markers[1]],
            }
            s.bus.publish(
                inv_id, EventType.POLICY,
                f"Existing incident #{duplicate['number']} found — proposing an update instead of a new issue",
                actor=Actor.SYSTEM, external_app="github",
                summary=f"“{duplicate['title']}” is open and matches this incident, so creating another issue would duplicate it.",
                data={"existing_issue": duplicate["number"], "fingerprint": fingerprint},
            )
        else:
            title = issue_title(synthesis, selected, state.intent.metric_label, evidence)
            display_title = f"Create GitHub issue: {title}"
            parameters = {"title": title, "body": body, "labels": ["incident", template.team, "surge"], "markers": [markers[1]]}

        with s.db.session() as db:
            approval_mode = db.get(Investigation, inv_id).approval_mode
        risk = risk_for(action_type)
        required = approval_required(risk, approval_mode)
        action_id = new_id("act")
        rationale = (
            f"Share the strongest supported hypothesis ({selected.label.lower()}, confidence {synthesis['confidence']:.2f}) "
            f"with the {template.team} team, with every claim linked to stored evidence."
        )
        with s.db.session() as db:
            db.add(
                Action(
                    id=action_id,
                    investigation_id=inv_id,
                    action_type=action_type,
                    external_app="github",
                    target=key_target,
                    title=display_title[:300],
                    parameters=parameters,
                    rationale=rationale,
                    risk_level=risk.value,
                    approval_required=required,
                    approval_status=(ApprovalStatus.PENDING if required else ApprovalStatus.NOT_REQUIRED).value,
                    execution_status=(ExecutionStatus.AWAITING_APPROVAL if required else ExecutionStatus.PROPOSED).value,
                    idempotency_key=key,
                    verification_status=VerificationStatus.PENDING.value,
                    hypothesis_id=selected.id,
                    evidence_ids=supporting_ids,
                )
            )
            db.add(self._claim(inv_id, f"Recommended action: {display_title}", supporting_ids, selected.id, set(evidence)))
        s.lifecycle.update(inv_id, synthesis={**synthesis, "proposed_actions": [action_id]})
        s.bus.publish(
            inv_id, EventType.ACTION_PROPOSED, display_title, external_app="github", action_id=action_id,
            summary=rationale, evidence_ids=supporting_ids, hypothesis_ids=[selected.id],
            data={"action_type": action_type, "target": key_target, "risk_level": risk.value,
                  "approval_required": required, "idempotency_key": key},
        )
        if state.intent.autonomous_action_requested and required:
            s.bus.publish(
                inv_id, EventType.POLICY, "Autonomous execution declined by policy", actor=Actor.SYSTEM, action_id=action_id,
                summary=(
                    f"The request asked Surge to act without approval. {action_type} is {risk.value} risk, so explicit "
                    "approval is still required; auto-execution is limited to LOW-risk actions with auto mode enabled."
                ),
            )
        if required:
            s.lifecycle.transition(inv_id, S.AWAITING_APPROVAL, reason="Waiting for explicit approval")
            s.bus.publish(
                inv_id, EventType.APPROVAL_REQUIRED, f"Approval required: {display_title}",
                actor=Actor.SYSTEM, external_app="github", action_id=action_id, status="pending",
                summary=f"{risk.value} risk · target {key_target}",
                data={
                    "risk_level": risk.value,
                    "tool": "github.create_comment" if duplicate else "github.create_issue",
                    "target": key_target,
                },
            )
            return
        s.lifecycle.transition(inv_id, S.EXECUTING, reason="Low-risk action auto-approved by policy")
        await self.run_action(inv_id, action_id)

    async def _block_action(
        self, state: InvestigationState, synthesis: dict, selected: HypothesisView,
        supporting_ids: list[str], valid: set[str], why: str,
    ) -> None:
        s = self.s
        inv_id = state.investigation_id
        action_id = new_id("act")
        team = CATALOG[selected.kind].team
        with s.db.session() as db:
            db.add(
                Action(
                    id=action_id,
                    investigation_id=inv_id,
                    action_type="create_github_issue",
                    external_app="github",
                    target="github",
                    title=f"Create GitHub incident issue for the {team} team",
                    parameters={},
                    rationale=f"Blocked: {why}.",
                    risk_level=risk_for("create_github_issue").value,
                    approval_required=True,
                    approval_status=ApprovalStatus.NOT_REQUESTED.value,
                    execution_status=ExecutionStatus.BLOCKED.value,
                    idempotency_key=idempotency_key(inv_id, "create_github_issue", "github"),
                    verification_status=VerificationStatus.NOT_APPLICABLE.value,
                    hypothesis_id=selected.id,
                    evidence_ids=supporting_ids,
                    error={"code": "ACTION_BLOCKED", "message": why},
                )
            )
            db.add(
                self._claim(
                    inv_id,
                    f"Recommended action (blocked): open an incident issue for the {team} team once GitHub is reachable",
                    supporting_ids, selected.id, valid,
                )
            )
        s.lifecycle.update(inv_id, synthesis={**synthesis, "proposed_actions": [action_id]})
        s.bus.publish(
            inv_id, EventType.ACTION_BLOCKED, "Cannot open an incident issue right now",
            actor=Actor.SYSTEM, external_app="github", action_id=action_id, status="blocked",
            summary=(
                f"Blocked because {why}. The diagnosis stands; Surge does not queue mutations against a provider it "
                "cannot reach or verify. Re-run once GitHub recovers."
            ),
        )
        s.lifecycle.transition(inv_id, S.PARTIAL, reason="Diagnosis complete; the incident action is blocked")
        s.bus.publish(
            inv_id, EventType.COMPLETED, "Investigation ended with partial results",
            actor=Actor.SYSTEM, status=S.PARTIAL.value, summary=synthesis["summary"][:500],
        )

    async def decide_action(
        self,
        investigation_id: str,
        action_id: str,
        approved: bool,
        *,
        decided_by: str = "user",
        comment: str | None = None,
        schedule: bool = True,
    ) -> None:
        s = self.s
        async with s.runtime.lock(f"action:{action_id}"):
            with s.db.session() as db:
                inv = db.get(Investigation, investigation_id)
                if inv is None:
                    raise SurgeAPIError(ErrorCode.NOT_FOUND, "Investigation not found", http_status=404)
                action = db.get(Action, action_id)
                if action is None or action.investigation_id != investigation_id:
                    raise SurgeAPIError(
                        ErrorCode.NOT_FOUND, "Action not found for this investigation",
                        http_status=404, investigation_id=investigation_id,
                    )
                if action.approval_status != ApprovalStatus.PENDING.value or inv.status != S.AWAITING_APPROVAL.value:
                    raise SurgeAPIError(
                        ErrorCode.INVALID_STATE,
                        f"Action is {action.approval_status} and the investigation is {inv.status}; there is nothing to decide",
                        http_status=409, investigation_id=investigation_id,
                    )
                now = datetime.now(UTC)
                action.approval_status = (ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED).value
                action.decided_at = now
                action.decided_by = decided_by[:64]
                if not approved:
                    action.execution_status = ExecutionStatus.REJECTED.value
                    action.verification_status = VerificationStatus.NOT_APPLICABLE.value
                    action.completed_at = now
                title = action.title

            if approved:
                s.bus.publish(
                    investigation_id, EventType.ACTION_APPROVED, f"Approved by {decided_by}",
                    actor=Actor.USER, action_id=action_id, status="approved", summary=comment or title,
                )
                s.lifecycle.transition(investigation_id, S.EXECUTING, reason="Action approved")
                if schedule:
                    s.runtime.spawn(investigation_id, self.run_action(investigation_id, action_id))
            else:
                s.bus.publish(
                    investigation_id, EventType.ACTION_REJECTED, f"Rejected by {decided_by}",
                    actor=Actor.USER, action_id=action_id, status="rejected", summary=comment or title,
                )
                s.lifecycle.transition(investigation_id, S.COMPLETED, reason="Action rejected; the diagnosis is kept")
                s.bus.publish(
                    investigation_id, EventType.COMPLETED, "Investigation complete — action not taken",
                    actor=Actor.SYSTEM, status=S.COMPLETED.value,
                )

    async def run_action(self, investigation_id: str, action_id: str) -> None:
        s = self.s
        try:
            with s.db.session() as db:
                inv = db.get(Investigation, investigation_id)
                db.expunge(inv)
            connectors = s.runtime.connectors_for(inv)
            action = await s.executor.execute(investigation_id, action_id, connectors)
            if action.execution_status == ExecutionStatus.SUCCEEDED and action.verification_status == VerificationStatus.VERIFIED:
                s.lifecycle.transition(investigation_id, S.COMPLETED, reason="Action executed and independently verified")
                s.bus.publish(
                    investigation_id, EventType.COMPLETED, "Investigation complete — action verified",
                    actor=Actor.SYSTEM, status=S.COMPLETED.value, action_id=action_id,
                    summary=action.external_url or action.external_result_id,
                )
            else:
                reason = f"Action {action.execution_status.lower()}, verification {action.verification_status.lower()}"
                s.lifecycle.transition(investigation_id, S.PARTIAL, reason=reason)
                s.bus.publish(
                    investigation_id, EventType.COMPLETED, "Investigation ended with partial results",
                    actor=Actor.SYSTEM, status=S.PARTIAL.value, action_id=action_id, summary=reason,
                )
        except asyncio.CancelledError:
            self._terminate(investigation_id, S.CANCELLED, "Cancelled during action execution")
        except Exception as exc:
            logger.exception("Action %s crashed", action_id)
            self._terminate(
                investigation_id, S.FAILED, f"Internal error during action execution ({type(exc).__name__})",
                error={"code": ErrorCode.INTERNAL.value, "type": type(exc).__name__},
            )

    # ------------------------------------------------------------------ termination

    async def cancel(self, investigation_id: str) -> str:
        s = self.s
        with s.db.session() as db:
            if db.get(Investigation, investigation_id) is None:
                raise SurgeAPIError(ErrorCode.NOT_FOUND, "Investigation not found", http_status=404)
        status = s.lifecycle.status(investigation_id)
        if status in TERMINAL_STATUSES:
            raise SurgeAPIError(
                ErrorCode.INVALID_STATE, f"Investigation is already {status.value}",
                http_status=409, investigation_id=investigation_id,
            )
        await s.runtime.cancel(investigation_id)
        self._terminate(investigation_id, S.CANCELLED, "Cancelled by user")
        return s.lifecycle.status(investigation_id).value

    def _terminate(self, investigation_id: str, status: InvestigationStatus, reason: str, error: dict | None = None) -> None:
        s = self.s
        if s.lifecycle.status(investigation_id) in TERMINAL_STATUSES:
            return
        try:
            s.lifecycle.transition(investigation_id, status, reason=reason, **({"error": error} if error else {}))
        except InvalidTransition:
            return
        with s.db.session() as db:
            for action in db.scalars(
                select(Action).where(
                    Action.investigation_id == investigation_id,
                    Action.approval_status == ApprovalStatus.PENDING.value,
                )
            ).all():
                action.approval_status = ApprovalStatus.REJECTED.value
                action.execution_status = ExecutionStatus.REJECTED.value
                action.verification_status = VerificationStatus.NOT_APPLICABLE.value
                action.decided_by = "system"
                action.decided_at = datetime.now(UTC)
        titles = {
            S.CANCELLED: "Investigation cancelled",
            S.TIMED_OUT: "Investigation timed out",
            S.FAILED: "Investigation failed",
        }
        s.bus.publish(
            investigation_id,
            EventType.CANCELLED if status == S.CANCELLED else EventType.FAILED,
            titles[status],
            actor=Actor.SYSTEM,
            status=status.value,
            summary=reason,
        )
