import json
from pathlib import Path


def _rate(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def _fraction(block: dict, key: str) -> str:
    if not block["total"]:
        return "n/a"
    return f"{block[key]}/{block['total']} ({_rate(block['rate'])})"


def render_text(report: dict) -> str:
    h = report["headline"]
    tools, dup, lat = h["tool_success_rate"], h["duplicate_action_rate"], h["latency_ms"]
    mode = report["reasoning_mode"] + (f" ({report['model']})" if report.get("model") else "")
    rows = [
        ("Scenarios", str(report["scenario_count"])),
        ("End-to-end success", _fraction(h["end_to_end_success"], "passed")),
        ("Diagnosis accuracy", _fraction(h["diagnosis_accuracy"], "correct")),
        ("Evidence recall", _rate(h["evidence_recall"])),
        ("Evidence precision", _rate(h["evidence_precision"])),
        ("Grounded conclusion rate", _rate(h["grounded_conclusion_rate"])),
        ("Unsupported claim rate", _rate(h["unsupported_claim_rate"])),
        (
            "Tool success",
            f"{_rate(tools['rate'])} ({tools['failures']} failed of {tools['calls']}, {tools['injected_failures']} injected; "
            f"{_rate(tools['rate_excluding_injected'])} excluding injected)",
        ),
        ("Recovery success", _fraction(h["recovery_success"], "recovered")),
        ("Action success", _fraction(h["action_success"], "succeeded")),
        ("Verification success", _fraction(h["verification_success"], "verified")),
        ("Duplicate action rate", f"{_rate(dup['rate'])} ({dup['duplicates']} of {dup['mutation_attempts']} mutation attempts)"),
        ("Approval gate compliance", _fraction(h["approval_gate_compliance"], "respected")),
        ("Latency p50 / p95", f"{lat['p50']} ms / {lat['p95']} ms"),
    ]
    lines = [
        "SURGE RELIABILITY REPORT",
        f"Suite {report['suite_id']} · reasoning: {mode} · agent {report['agent_version']} · {report['generated_at']}",
        "",
        *[f"{label + ':':<27} {value}" for label, value in rows],
        "",
        "Confidence checks (diagnosis outcomes only):",
    ]
    buckets = [b for b in report["calibration"] if b["count"]]
    lines += [
        f"  {b['bucket']}: {_rate(b['accuracy'])} correct ({b['correct']}/{b['count']}, mean confidence {b['mean_confidence']:.2f})"
        for b in buckets
    ] or ["  (no diagnosis outcomes)"]
    if report.get("llm_usage"):
        lines += ["", "LLM routing (served / failed calls per model):"]
        lines += [f"  {u['model']}: {u['successes']} served, {u['failures']} failed" for u in report["llm_usage"]]
    lines += ["", "Scenario results:"]
    for s in report["scenarios"]:
        mark = "✓" if s["passed"] else "✗"
        conf = f"  conf {s['confidence']:.2f}" if s["confidence"] is not None else ""
        lines.append(f"  {mark} {s['scenario_id']:<30} {s['title']}{conf}")
        for reason in s["failure_reasons"]:
            lines.append(f"      - {reason}")
    lines += ["", "Known weaknesses:"]
    lines += [f"  - {w}" for w in report["known_weaknesses"]] or ["  - none observed in this suite"]
    lines += ["", "Notes:"] + [f"  - {n}" for n in report["notes"]]
    return "\n".join(lines)


def write_report_files(directory: Path, report: dict, text: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, indent=2, default=str)
    markdown = f"# Surge reliability report\n\n```text\n{text}\n```\n"
    for stem in (report["suite_id"], "latest"):
        (directory / f"{stem}.json").write_text(payload)
        (directory / f"{stem}.md").write_text(markdown)
