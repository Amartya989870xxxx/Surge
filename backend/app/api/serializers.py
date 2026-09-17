from app.agent.hypotheses import aggregate
from app.db.models import (
    Action,
    Claim,
    EvaluationRun,
    EvaluationSuite,
    EvidenceItem,
    EvidenceLink,
    Hypothesis,
    Investigation,
    Verification,
)

_EPISTEMIC = {
    "message": "observation",
    "deployment": "observation",
    "code_change": "observation",
    "deployment_absence": "absence_check",
}


def _dt(value):
    return value.isoformat() if value else None


def investigation_summary(inv: Investigation, actions: list[Action]) -> dict:
    synthesis = inv.synthesis or {}
    strongest = None
    if inv.root_cause_hypothesis_id:
        h = next((h for h in synthesis.get("hypotheses", []) if h["id"] == inv.root_cause_hypothesis_id), None)
        if h:
            strongest = {"id": h["id"], "kind": h["kind"], "label": h["label"], "confidence": h["confidence"]}
    return {
        "id": inv.id,
        "session_id": inv.session_id,
        "title": inv.title,
        "request": inv.user_request,
        "status": inv.status,
        "outcome": inv.outcome,
        "strongest_hypothesis": strongest,
        "confidence": inv.final_confidence,
        "action_count": len(actions),
        "verified": any(a.verification_status == "VERIFIED" for a in actions),
        "pending_approval": any(a.approval_status == "PENDING" for a in actions),
        "degraded": bool(inv.degraded),
        "execution_mode": inv.execution_mode,
        "connector_mode": inv.connector_mode,
        "reasoning_mode": inv.reasoning_mode,
        "scenario_id": inv.scenario_id,
        "duration_ms": inv.duration_ms,
        "created_at": _dt(inv.created_at),
        "completed_at": _dt(inv.completed_at),
    }


def investigation_detail(inv: Investigation, actions: list[Action], connectors: list[dict], counts: dict) -> dict:
    base = f"/api/investigations/{inv.id}"
    return {
        **investigation_summary(inv, actions),
        "approval_mode": inv.approval_mode,
        "severity": inv.severity,
        "time_window_start": _dt(inv.time_window_start),
        "time_window_end": _dt(inv.time_window_end),
        "started_at": _dt(inv.started_at),
        "updated_at": _dt(inv.updated_at),
        "intent": inv.intent,
        "final_summary": inv.final_summary,
        "confidence_breakdown": inv.confidence_breakdown,
        "root_cause_hypothesis_id": inv.root_cause_hypothesis_id,
        "missing_sources": inv.missing_sources or [],
        "tool_call_count": inv.tool_call_count or 0,
        "error": inv.error,
        "fault_injection": inv.fault_injection or [],
        "connectors": connectors,
        "synthesis": inv.synthesis,
        "pending_action_ids": [a.id for a in actions if a.approval_status == "PENDING"],
        "counts": counts,
        "links": {
            "events": f"{base}/events",
            "stream": f"{base}/stream",
            "evidence": f"{base}/evidence",
            "hypotheses": f"{base}/hypotheses",
            "actions": f"{base}/actions",
            "claims": f"{base}/claims",
        },
    }


def evidence_item(e: EvidenceItem, links: list[EvidenceLink], hypotheses: dict[str, Hypothesis]) -> dict:
    relations = [
        {
            "hypothesis_id": l.hypothesis_id,
            "hypothesis_kind": hypotheses[l.hypothesis_id].kind,
            "hypothesis_label": hypotheses[l.hypothesis_id].label,
            "relation": l.relation,
            "strength": l.strength,
            "rationale": l.rationale,
            "assessed_by": l.assessed_by,
        }
        for l in links
        if l.hypothesis_id in hypotheses
    ]
    return {
        "id": e.id,
        "investigation_id": e.investigation_id,
        "source_app": e.source_app,
        "source_type": e.source_type,
        "source_record_id": e.source_record_id,
        "epistemic_type": _EPISTEMIC.get(e.source_type, "computed_observation"),
        "title": e.title,
        "snippet": e.normalized_content[:600],
        "normalized_content": e.normalized_content,
        "observed_at": _dt(e.observed_at),
        "retrieved_at": _dt(e.retrieved_at),
        "url": e.url,
        "source_metadata": e.source_metadata or {},
        "derived_from": e.derived_from or [],
        "relevance_score": e.relevance_score,
        "evidence_strength": e.evidence_strength,
        "connector_mode": e.connector_mode,
        "probe_id": e.probe_id,
        "supports_hypothesis_ids": [r["hypothesis_id"] for r in relations if r["relation"] == "supports"],
        "contradicts_hypothesis_ids": [r["hypothesis_id"] for r in relations if r["relation"] == "contradicts"],
        "relations": relations,
    }


def hypotheses_list(hyps: list[Hypothesis], links: list[EvidenceLink], evidence: dict[str, EvidenceItem]) -> list[dict]:
    out = []
    for h in hyps:
        own = [l for l in links if l.hypothesis_id == h.id and l.evidence_id in evidence]
        _, sources = aggregate(h.prior, [(evidence[l.evidence_id].source_app, l.relation, l.strength) for l in own])
        out.append(
            {
                "id": h.id,
                "kind": h.kind,
                "label": h.label,
                "statement": h.statement,
                "confidence": h.confidence,
                "prior": h.prior,
                "status": h.status,
                "rank": 0,
                "rationale": h.rationale,
                "missing_information": h.missing_information or [],
                "supporting_evidence_ids": [l.evidence_id for l in own if l.relation == "supports"],
                "contradicting_evidence_ids": [l.evidence_id for l in own if l.relation == "contradicts"],
                "independent_sources": sources,
                "evidence": [
                    {
                        "evidence_id": l.evidence_id,
                        "source_app": evidence[l.evidence_id].source_app,
                        "title": evidence[l.evidence_id].title,
                        "relation": l.relation,
                        "strength": l.strength,
                        "rationale": l.rationale,
                        "assessed_by": l.assessed_by,
                    }
                    for l in own
                ],
            }
        )
    out.sort(key=lambda h: -h["confidence"])
    for rank, h in enumerate(out, start=1):
        h["rank"] = rank
    return out


def action_item(a: Action, verifications: list[Verification]) -> dict:
    latest = max(verifications, key=lambda v: v.attempted_at) if verifications else None
    p = a.parameters or {}
    return {
        "id": a.id,
        "investigation_id": a.investigation_id,
        "action_type": a.action_type,
        "external_app": a.external_app,
        "target": a.target,
        "title": a.title,
        "rationale": a.rationale,
        "risk_level": a.risk_level,
        "approval_required": a.approval_required,
        "approval_status": a.approval_status,
        "execution_status": a.execution_status,
        "verification_status": a.verification_status,
        "idempotency_key": a.idempotency_key,
        "external_result_id": a.external_result_id,
        "external_url": a.external_url,
        "hypothesis_id": a.hypothesis_id,
        "evidence_ids": a.evidence_ids or [],
        "attempts": a.attempts or 0,
        "error": a.error,
        "decided_by": a.decided_by,
        "created_at": _dt(a.created_at),
        "decided_at": _dt(a.decided_at),
        "completed_at": _dt(a.completed_at),
        "preview": {
            "title": p.get("title") or p.get("existing_title"),
            "body": p.get("body"),
            "labels": p.get("labels", []),
            "issue_number": p.get("issue_number"),
        },
        "verification": {
            "method": latest.method,
            "result": latest.result,
            "checks": latest.checks or [],
            "expected_state": latest.expected_state or {},
            "observed_state": latest.observed_state or {},
            "confidence": latest.confidence,
            "attempted_at": _dt(latest.attempted_at),
            "error_code": latest.error_code,
        }
        if latest
        else None,
        "lifecycle": [
            {"stage": "PROPOSED", "done": True, "state": "PROPOSED"},
            {"stage": "APPROVED", "done": a.approval_status in ("APPROVED", "NOT_REQUIRED"), "state": a.approval_status},
            {"stage": "EXECUTED", "done": a.execution_status == "SUCCEEDED", "state": a.execution_status},
            {"stage": "VERIFIED", "done": a.verification_status == "VERIFIED", "state": a.verification_status},
        ],
        "requires_strong_confirmation": a.risk_level == "HIGH",
    }


def claim_item(c: Claim) -> dict:
    return {
        "id": c.id,
        "claim_type": c.claim_type,
        "text": c.text,
        "evidence_ids": c.evidence_ids or [],
        "event_sequences": c.event_sequences or [],
        "hypothesis_id": c.hypothesis_id,
        "requires_evidence": c.requires_evidence,
        "grounded": c.grounded,
        "invalid_references": c.invalid_references or [],
        "source": c.source,
        "position": c.position,
    }


def suite_summary(suite: EvaluationSuite) -> dict:
    return {
        "id": suite.id,
        "status": suite.status,
        "reasoning_mode": suite.reasoning_mode,
        "agent_version": suite.agent_version,
        "scenario_count": len(suite.scenario_ids or []),
        "started_at": _dt(suite.started_at),
        "completed_at": _dt(suite.completed_at),
        "headline": (suite.report or {}).get("headline"),
    }


def run_item(r: EvaluationRun) -> dict:
    return {
        "id": r.id,
        "scenario_id": r.scenario_id,
        "category": r.category,
        "passed": r.passed,
        "expected_hypothesis": r.expected_hypothesis,
        "predicted_hypothesis": r.predicted_hypothesis,
        "diagnosis_correct": r.diagnosis_correct,
        "evidence_precision": r.evidence_precision,
        "evidence_recall": r.evidence_recall,
        "grounded_claim_rate": r.grounded_claim_rate,
        "unsupported_claim_count": r.unsupported_claim_count,
        "expected_action": r.expected_action,
        "action_taken": r.action_taken,
        "action_success": r.action_success,
        "verification_success": r.verification_success,
        "duplicate_action_count": r.duplicate_action_count,
        "tool_calls": r.tool_calls,
        "tool_failures": r.tool_failures,
        "recovery_expected": r.recovery_expected,
        "recovery_success": r.recovery_success,
        "approval_respected": r.approval_respected,
        "confidence": r.confidence,
        "latency_ms": r.latency_ms,
        "failure_reasons": r.failure_reasons or [],
        "investigation_ids": r.investigation_ids or [],
        "timestamp": _dt(r.timestamp),
    }
