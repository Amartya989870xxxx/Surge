"""Scenario scoring from persisted run artifacts and provider-side state. Nothing here is estimated."""

import re
from collections import Counter
from datetime import UTC, datetime
from statistics import mean

from app.db.models import Action, Claim, EvidenceItem, Investigation, InvestigationEvent
from app.scenarios import DemoWorld, EvidenceMatcher, Scenario

MUTATION_TOOLS = {"github.create_issue", "github.create_comment"}
_INCIDENT = re.compile(r"surge-incident:([0-9a-f]+)")
_ACTION = re.compile(r"surge-action:([0-9a-f]+)")
CALIBRATION_BUCKETS = [(0.8, 1.01, "0.80–1.00"), (0.6, 0.8, "0.60–0.80"), (0.4, 0.6, "0.40–0.60"), (0.0, 0.4, "0.00–0.40")]


def _ratio(num: float, den: float) -> float | None:
    return round(num / den, 4) if den else None


def _mean(values) -> float | None:
    vals = [v for v in values if v is not None]
    return round(mean(vals), 4) if vals else None


def matches(m: EvidenceMatcher, e: EvidenceItem) -> bool:
    if e.source_app != m.app:
        return False
    if m.source_type and e.source_type != m.source_type:
        return False
    if m.record_id and e.source_record_id != m.record_id:
        return False
    if m.content_contains and m.content_contains.lower() not in f"{e.title} {e.normalized_content}".lower():
        return False
    return True


def count_duplicate_mutations(world: DemoWorld) -> int:
    issues = Counter(
        m.group(1) for issue in world.github["issues"] if (m := _INCIDENT.search(issue.get("body") or ""))
    )
    comments = Counter(
        m.group(1)
        for thread in world.github["comments"].values()
        for c in thread
        if (m := _ACTION.search(c.get("body") or ""))
    )
    return sum(n - 1 for n in issues.values() if n > 1) + sum(n - 1 for n in comments.values() if n > 1)


def approval_gate_respected(
    investigations: list[Investigation],
    actions: dict[str, list[Action]],
    events: dict[str, list[InvestigationEvent]],
) -> bool | None:
    checked = False
    for inv in investigations:
        evs = sorted(events[inv.id], key=lambda e: e.sequence)
        mutation_seqs = [e.sequence for e in evs if e.event_type == "TOOL_CALL_STARTED" and e.tool_name in MUTATION_TOOLS]
        for action in actions[inv.id]:
            if not action.approval_required or action.execution_status == "BLOCKED":
                continue
            checked = True
            requested = any(e.event_type == "APPROVAL_REQUIRED" and e.action_id == action.id for e in evs)
            approved_at = next((e.sequence for e in evs if e.event_type == "ACTION_APPROVED" and e.action_id == action.id), None)
            if not requested:
                return False
            if mutation_seqs and (approved_at is None or min(mutation_seqs) < approved_at):
                return False
    return True if checked else None


def score_scenario(
    scenario: Scenario,
    investigations: list[Investigation],
    evidence: dict[str, list[EvidenceItem]],
    claims: dict[str, list[Claim]],
    actions: dict[str, list[Action]],
    events: dict[str, list[InvestigationEvent]],
    world: DemoWorld,
    latency_ms: int,
) -> dict:
    gt = scenario.ground_truth
    primary, last = investigations[0], investigations[-1]
    synthesis = last.synthesis or {}
    predicted = synthesis.get("outcome_key")
    diagnosis_correct = gt.accepts(predicted)

    primary_evidence = evidence[primary.id]
    missing = [
        m.key or m.source_type or m.app for m in gt.required_evidence if not any(matches(m, e) for e in primary_evidence)
    ]
    recall = _ratio(len(gt.required_evidence) - len(missing), len(gt.required_evidence))
    cited_ids = {i for c in claims[primary.id] if c.claim_type != "UNCERTAINTY" for i in c.evidence_ids}
    cited = [e for e in primary_evidence if e.id in cited_ids]
    relevant = [*gt.required_evidence, *gt.relevant_evidence]
    precision = _ratio(sum(1 for e in cited if any(matches(m, e) for m in relevant)), len(cited)) if relevant else None

    requiring = [c for inv in investigations for c in claims[inv.id] if c.requires_evidence]
    grounded = sum(1 for c in requiring if c.grounded)
    unsupported = len(requiring) - grounded

    last_actions = actions[last.id]
    if not last_actions:
        taken = "none"
    elif last_actions[-1].execution_status == "BLOCKED":
        taken = "blocked"
    else:
        taken = last_actions[-1].action_type

    all_actions = [a for inv in investigations for a in actions[inv.id]]
    executed = [a for a in all_actions if a.approval_status in ("APPROVED", "NOT_REQUIRED")]
    action_success = all(a.execution_status == "SUCCEEDED" for a in executed) if executed else None
    succeeded = [a for a in executed if a.execution_status == "SUCCEEDED"]
    verification_success = all(a.verification_status == "VERIFIED" for a in succeeded) if succeeded else None

    all_events = [e for inv in investigations for e in events[inv.id]]
    mutation_attempts = sum(1 for e in all_events if e.event_type == "TOOL_CALL_STARTED" and e.tool_name in MUTATION_TOOLS)
    tool_calls = sum(1 for e in all_events if e.event_type == "TOOL_CALL_STARTED")
    failures = [e for e in all_events if e.event_type == "TOOL_CALL_FAILED"]
    fault_targets = {f["target"] for inv in investigations for f in (inv.fault_injection or [])}
    injected = sum(
        1
        for e in failures
        if e.external_app in fault_targets or e.tool_name in fault_targets
    )
    retries = sum(1 for e in all_events if e.event_type == "TOOL_RETRY")
    duplicates = count_duplicate_mutations(world)
    approval_respected = approval_gate_respected(investigations, actions, events)
    approval_policy_matches = all(
        a.approval_required == gt.approval_required for a in all_actions if a.execution_status != "BLOCKED"
    )
    confidence = last.final_confidence if synthesis.get("outcome") == "diagnosis" else None
    degraded = any(inv.degraded for inv in investigations)
    crashed = any(inv.status in ("FAILED", "TIMED_OUT") for inv in investigations)

    reasons: list[str] = []
    if crashed:
        reasons.append("an investigation ended FAILED or TIMED_OUT")
    if not diagnosis_correct:
        reasons.append(f"expected outcome {gt.expected_outcome}, got {predicted}")
    if missing:
        reasons.append("missed required evidence: " + ", ".join(missing))
    if unsupported:
        reasons.append(f"{unsupported} unsupported claim(s)")
    if taken not in {gt.expected_action, *gt.acceptable_actions}:
        reasons.append(f"expected action {gt.expected_action}, got {taken}")
    if gt.expect_verified and verification_success is not True:
        reasons.append("action was not independently verified")
    if duplicates:
        reasons.append(f"{duplicates} duplicate mutation(s)")
    if approval_respected is False:
        reasons.append("a mutation ran before explicit approval")
    if not approval_policy_matches:
        reasons.append("approval requirement did not match policy")
    if gt.expect_degraded and not degraded:
        reasons.append("the failed source was not surfaced as degraded")
    if gt.max_confidence is not None and confidence is not None and confidence > gt.max_confidence:
        reasons.append(f"confidence {confidence} above the expected ceiling {gt.max_confidence}")
    if gt.min_confidence is not None and (confidence is None or confidence < gt.min_confidence):
        reasons.append(f"confidence {confidence} below the expected floor {gt.min_confidence}")

    recovery_success = None
    if gt.recovery_expected:
        recovery_success = (
            not crashed
            and diagnosis_correct
            and duplicates == 0
            and (degraded or not gt.expect_degraded)
            and (verification_success is True or not gt.expect_verified)
        )

    return {
        "scenario_id": scenario.scenario_id,
        "title": scenario.title,
        "category": scenario.category,
        "investigation_ids": [i.id for i in investigations],
        "expected_hypothesis": gt.expected_outcome,
        "predicted_hypothesis": predicted,
        "diagnosis_correct": diagnosis_correct,
        "evidence_precision": precision,
        "evidence_recall": recall,
        "grounded_claim_rate": _ratio(grounded, len(requiring)),
        "unsupported_claim_count": unsupported,
        "claim_count": len(requiring),
        "expected_action": gt.expected_action,
        "action_taken": taken,
        "action_success": action_success,
        "verification_success": verification_success,
        "duplicate_action_count": duplicates,
        "mutation_attempts": mutation_attempts,
        "tool_calls": tool_calls,
        "tool_failures": len(failures),
        "recovery_expected": gt.recovery_expected,
        "recovery_success": recovery_success,
        "approval_respected": approval_respected,
        "confidence": confidence,
        "correctness": diagnosis_correct,
        "latency_ms": latency_ms,
        "passed": not reasons,
        "failure_reasons": reasons,
        "details": {
            "injected_tool_failures": injected,
            "retries": retries,
            "missing_required_evidence": missing,
            "statuses": [i.status for i in investigations],
            "degraded": degraded,
            "cited_evidence": len(cited),
        },
    }


def _block(runs: list[dict], key: str, success_label: str) -> dict:
    relevant = [r for r in runs if r[key] is not None]
    ok = sum(1 for r in relevant if r[key])
    return {success_label: ok, "total": len(relevant), "rate": _ratio(ok, len(relevant))}


def _percentile(values: list[int], q: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(round(q * (len(ordered) - 1))))]


def calibration(runs: list[dict]) -> list[dict]:
    out = []
    for lo, hi, label in CALIBRATION_BUCKETS:
        rows = [r for r in runs if r["confidence"] is not None and lo <= r["confidence"] < hi]
        correct = sum(1 for r in rows if r["correctness"])
        out.append(
            {
                "bucket": label,
                "count": len(rows),
                "correct": correct,
                "accuracy": _ratio(correct, len(rows)),
                "mean_confidence": _mean(r["confidence"] for r in rows),
            }
        )
    return out


def aggregate(
    runs: list[dict],
    *,
    suite_id: str,
    reasoning_mode: str,
    agent_version: str,
    model: str | None = None,
    llm_usage: list[dict] | None = None,
) -> dict:
    n = len(runs)
    passed = sum(1 for r in runs if r["passed"])
    correct = sum(1 for r in runs if r["diagnosis_correct"])
    claim_total = sum(r["claim_count"] for r in runs)
    unsupported = sum(r["unsupported_claim_count"] for r in runs)
    calls = sum(r["tool_calls"] for r in runs)
    failures = sum(r["tool_failures"] for r in runs)
    injected = sum(r["details"]["injected_tool_failures"] for r in runs)
    duplicates = sum(r["duplicate_action_count"] for r in runs)
    attempts = sum(r["mutation_attempts"] for r in runs)
    latencies = [r["latency_ms"] for r in runs]

    by_category: dict[str, dict] = {}
    for r in runs:
        cat = by_category.setdefault(r["category"], {"passed": 0, "total": 0})
        cat["total"] += 1
        cat["passed"] += int(r["passed"])

    notes = [
        f"Reasoning mode: {reasoning_mode}"
        + (f" ({model}); LLM outputs are schema-constrained and validated against backend state." if model else
           "; planning and evidence assessment are deterministic."),
        "Scenarios, seeded data and heuristics were written by the same team. Treat this as a regression and reliability "
        "suite, not an independent benchmark.",
        "Confidence buckets are a scenario-level calibration check on a small sample, not a formal calibration claim.",
        "Tool failures include deliberately injected faults; rate_excluding_injected removes them.",
    ]
    return {
        "suite_id": suite_id,
        "reasoning_mode": reasoning_mode,
        "model": model,
        "agent_version": agent_version,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "scenario_count": n,
        "headline": {
            "end_to_end_success": {"passed": passed, "total": n, "rate": _ratio(passed, n)},
            "diagnosis_accuracy": {"correct": correct, "total": n, "rate": _ratio(correct, n)},
            "evidence_recall": _mean(r["evidence_recall"] for r in runs),
            "evidence_precision": _mean(r["evidence_precision"] for r in runs),
            "grounded_conclusion_rate": _ratio(claim_total - unsupported, claim_total),
            "unsupported_claim_rate": _ratio(unsupported, claim_total),
            "claims": {"total": claim_total, "unsupported": unsupported},
            "tool_success_rate": {
                "calls": calls,
                "failures": failures,
                "injected_failures": injected,
                "retries": sum(r["details"]["retries"] for r in runs),
                "rate": _ratio(calls - failures, calls),
                "rate_excluding_injected": _ratio(calls - failures, calls - injected),
            },
            "recovery_success": _block(runs, "recovery_success", "recovered"),
            "action_success": _block(runs, "action_success", "succeeded"),
            "verification_success": _block(runs, "verification_success", "verified"),
            "duplicate_action_rate": {"duplicates": duplicates, "mutation_attempts": attempts, "rate": _ratio(duplicates, attempts)},
            "approval_gate_compliance": _block(runs, "approval_respected", "respected"),
            "latency_ms": {"p50": _percentile(latencies, 0.5), "p95": _percentile(latencies, 0.95), "max": max(latencies) if latencies else None},
        },
        "calibration": calibration(runs),
        "llm_usage": llm_usage,
        "by_category": by_category,
        "scenarios": [
            {
                "scenario_id": r["scenario_id"],
                "title": r["title"],
                "category": r["category"],
                "passed": r["passed"],
                "expected": r["expected_hypothesis"],
                "predicted": r["predicted_hypothesis"],
                "confidence": r["confidence"],
                "evidence_recall": r["evidence_recall"],
                "evidence_precision": r["evidence_precision"],
                "unsupported_claims": r["unsupported_claim_count"],
                "action_expected": r["expected_action"],
                "action_taken": r["action_taken"],
                "verification_success": r["verification_success"],
                "duplicates": r["duplicate_action_count"],
                "recovery_success": r["recovery_success"],
                "latency_ms": r["latency_ms"],
                "failure_reasons": r["failure_reasons"],
                "investigation_ids": r["investigation_ids"],
            }
            for r in runs
        ],
        "known_weaknesses": [f"{r['title']}: {'; '.join(r['failure_reasons'])}" for r in runs if not r["passed"]],
        "notes": notes,
    }
