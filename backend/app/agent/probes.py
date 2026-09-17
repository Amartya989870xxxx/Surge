"""Investigation probes: each is a bounded, allowlisted evidence-gathering step with a declared
information value for specific hypotheses. The planner chooses among them; it cannot invent new ones."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import timedelta

from app.agent.analysis import (
    detect_change,
    funnel_analysis,
    payment_error_analysis,
    pct,
    tracking_analysis,
    traffic_mix_analysis,
)
from app.agent.classify import assess_change, assess_message
from app.agent.types import Assessment, EvidenceDraft, InvestigationState, ProbeOutcome
from app.config import Settings
from app.enums import App, Relation, Strength
from app.tools.base import ToolContext
from app.tools.runner import ToolRunner

S, C = Relation.SUPPORTS, Relation.CONTRADICTS
WEAK, MOD, STRONG = Strength.WEAK, Strength.MODERATE, Strength.STRONG

SLACK_TERMS = [
    "checkout", "payment", "order", "conversion", "tracking", "analytics",
    "dashboard", "campaign", "stripe", "broken", "error", "declin",
]


@dataclass
class ProbeContext:
    state: InvestigationState
    runner: ToolRunner
    tool_ctx: ToolContext
    settings: Settings


@dataclass
class ProbeDef:
    id: str
    app: App
    title: str
    purpose: str
    expected_information: list[str]
    discriminates: dict[str, float]
    cost: float
    run: Callable[[ProbeContext], Awaitable[ProbeOutcome]]
    requires_columns: tuple[str, ...] = ()
    requires_deployments: bool = False

    def readiness(self, state: InvestigationState) -> tuple[str, str | None]:
        """ready | not_ready (may become runnable later) | not_applicable (never runnable in this run)."""
        if self.requires_columns:
            missing = [c for c in self.requires_columns if c not in state.sheet_columns]
            if missing:
                return "not_applicable", (
                    f"The metrics sheet has no {', '.join(missing)} column(s), so '{self.title.lower()}' cannot be checked from Sheets."
                )
        if self.requires_deployments:
            if state.probe_status.get("check_recent_deployments") != "ok":
                return "not_ready", None
            if not state.candidate_deployments:
                return "not_applicable", "No deployment shipped shortly before the decline, so there is no code change to inspect."
        return "ready", None


def _fmt_rate(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1%}"


def _failed(probe_id: str, result, calls: int) -> ProbeOutcome:
    return ProbeOutcome(probe_id, "failed", note=result.error.message, tool_calls=calls, failed_tool=result)


async def _read_columns(p: ProbeContext, columns: list[str], purpose: str):
    st = p.state
    return await p.runner.call(
        p.tool_ctx,
        "sheets.read_rows",
        {
            "tab": st.sheet_tab,
            "columns": ["timestamp", *columns],
            "start": st.intent.read_start.isoformat(),
            "end": st.intent.window_end.isoformat(),
        },
        purpose=purpose,
    )


async def establish_anomaly(p: ProbeContext) -> ProbeOutcome:
    st = p.state
    meta = await p.runner.call(p.tool_ctx, "sheets.get_metadata", {}, purpose="Inspect the metrics spreadsheet")
    if not meta.success:
        return _failed("establish_anomaly", meta, 1)
    tabs = [t["name"] for t in meta.data.get("tabs", [])]
    if not tabs:
        return ProbeOutcome("establish_anomaly", "not_applicable", note="Spreadsheet has no tabs", tool_calls=1)
    st.sheet_tab = p.settings.sheets_tab if p.settings.sheets_tab in tabs else tabs[0]

    metric, label = st.intent.metric, st.intent.metric_label
    columns = list(dict.fromkeys(["sessions", "conversions", "conversion_rate", metric]))
    rows = await _read_columns(p, columns, f"Read the {label} time series")
    if not rows.success:
        return _failed("establish_anomaly", rows, 2)
    st.sheet_columns = rows.data.get("all_columns", [])
    result = detect_change(rows.items, metric)
    tab = st.sheet_tab
    if "onset" not in result:
        return ProbeOutcome(
            "establish_anomaly", "ok", note=f"Not enough data to test for a change ({result['reason']}).",
            facts={"anomaly": result}, tool_calls=2,
        )

    onset = result["onset"]
    unit = "%" if metric == "conversion_rate" else ""
    span = f"{tab}!rows {result['first_row']}-{result['last_row']}"
    if result["detected"]:
        title = (
            f"{label.capitalize()} fell {abs(result['relative_change']) * 100:.0f}% "
            f"({result['before_mean']:.2f}{unit} → {result['after_mean']:.2f}{unit}) from {onset:%b %d %H:%M} UTC"
        )
        content = (
            f"Change-point analysis over {result['baseline_points'] + result['affected_points']} hourly rows ({span}) "
            f"found a sustained shift starting at row {result['onset_row']}: mean {result['before_mean']:.2f}{unit} before "
            f"vs {result['after_mean']:.2f}{unit} after (t={result['t_stat']}). Detection thresholds: drop of at least "
            f"20% and t of at least 4."
        )
        draft = EvidenceDraft(
            "anomaly", "sheets", "metric_anomaly", f"{tab}:{metric}:change@{onset:%Y-%m-%dT%H:%M}",
            title, content, observed_at=onset, metadata=result, derived_from=[span], strength=STRONG,
        )
        note = title
    else:
        title = (
            f"No significant {label} drop (largest shift {result['relative_change'] * 100:+.0f}%, t={result['t_stat']})"
        )
        content = (
            f"Change-point analysis over {span} found no shift meeting the thresholds (≥20% drop and t≥4). "
            f"Largest candidate shift at {onset:%b %d %H:%M} UTC: {result['before_mean']:.2f}{unit} → {result['after_mean']:.2f}{unit}."
        )
        draft = EvidenceDraft(
            "stability", "sheets", "metric_stability", f"{tab}:{metric}:stable@{st.intent.window_end:%Y-%m-%dT%H:%M}",
            title, content, observed_at=st.intent.window_end, metadata=result, derived_from=[span], strength=MOD,
        )
        note = title
    return ProbeOutcome("establish_anomaly", "ok", note=note, evidence=[draft], facts={"anomaly": result}, tool_calls=2)


async def check_checkout_funnel(p: ProbeContext) -> ProbeOutcome:
    st = p.state
    onset = st.anomaly["onset"]
    wanted = ["sessions", "checkout_starts", "orders_backend"] + (
        ["payment_errors"] if "payment_errors" in st.sheet_columns else []
    )
    res = await _read_columns(p, wanted, "Read checkout funnel metrics (starts, completions, payment errors)")
    if not res.success:
        return _failed("check_checkout_funnel", res, 1)
    rows, tab = res.items, st.sheet_tab
    f = funnel_analysis(rows, onset)
    sr, cr = f["checkout_start_rate_change"], f["completion_rate_change"]
    evidence = [
        EvidenceDraft(
            "funnel", "sheets", "funnel_analysis", f"{tab}:funnel@{onset:%Y-%m-%dT%H:%M}",
            f"Checkout funnel after onset: start rate {pct(sr)}, completion rate {pct(cr)}",
            f"Share of sessions starting checkout: {_fmt_rate(f['checkout_start_rate_before'])} → "
            f"{_fmt_rate(f['checkout_start_rate_after'])}. Share of checkout starts completing an order (backend orders): "
            f"{_fmt_rate(f['completion_rate_before'])} → {_fmt_rate(f['completion_rate_after'])}. "
            f"Baseline {f['hours_before']}h vs {f['hours_after']}h after onset.",
            observed_at=onset, metadata=f, derived_from=[f"{tab}!checkout_starts,orders_backend,sessions"], strength=MOD,
        )
    ]
    a: list[Assessment] = []
    if sr is not None and cr is not None:
        if cr <= -0.25 and abs(sr) < 0.15:
            a += [
                Assessment("funnel", "checkout_regression", S, MOD, "Visitors still reach checkout at the usual rate, but far fewer complete it: the failure is inside checkout"),
                Assessment("funnel", "payment_provider_issue", S, WEAK, "Completion failures are also consistent with payments failing"),
                Assessment("funnel", "marketing_traffic_quality", C, MOD, "The checkout-start rate is unchanged, so visitor intent did not fall"),
            ]
        elif sr <= -0.25 and abs(cr) < 0.15:
            a += [
                Assessment("funnel", "marketing_traffic_quality", S, MOD, "Fewer visitors start checkout while those who do complete normally: an intent/traffic change"),
                Assessment("funnel", "checkout_regression", C, MOD, "Checkout completion is unchanged, so checkout itself works"),
                Assessment("funnel", "payment_provider_issue", C, MOD, "Checkout completion is unchanged, so payments are succeeding"),
            ]
        elif abs(sr) < 0.15 and abs(cr) < 0.15:
            a += [
                Assessment("funnel", "checkout_regression", C, MOD, "Backend checkout funnel ratios are unchanged"),
                Assessment("funnel", "payment_provider_issue", C, MOD, "Backend checkout completion is unchanged"),
                Assessment("funnel", "marketing_traffic_quality", C, MOD, "The checkout-start rate is unchanged"),
            ]

    if "payment_errors" in wanted:
        e = payment_error_analysis(rows, onset)
        ratio = e["ratio"]
        evidence.append(
            EvidenceDraft(
                "payment_errors", "sheets", "error_rate_analysis", f"{tab}:payment_errors@{onset:%Y-%m-%dT%H:%M}",
                f"Payment errors per checkout: {ratio if ratio is not None else 'n/a'}x baseline "
                f"({_fmt_rate(e['error_rate_before'])} → {_fmt_rate(e['error_rate_after'])})",
                "Payment errors divided by checkout starts, 24h before onset vs after onset.",
                observed_at=onset, metadata=e, derived_from=[f"{tab}!payment_errors,checkout_starts"], strength=MOD,
            )
        )
        if ratio is not None and ratio >= 3:
            a += [
                Assessment("payment_errors", "payment_provider_issue", S, STRONG, f"Payment errors per checkout rose {ratio}x after the onset"),
                Assessment("payment_errors", "checkout_regression", C, WEAK, "A spike in provider-side payment errors points away from our own checkout code"),
            ]
        elif ratio is not None and ratio <= 1.5:
            a.append(
                Assessment("payment_errors", "payment_provider_issue", C, MOD, f"Payment error rate is essentially unchanged ({ratio}x); a provider failure would raise it")
            )
    return ProbeOutcome("check_checkout_funnel", "ok", note=evidence[0].title, evidence=evidence, assessments=a, tool_calls=1)


async def check_tracking_consistency(p: ProbeContext) -> ProbeOutcome:
    st = p.state
    onset = st.anomaly["onset"]
    res = await _read_columns(p, ["sessions", "conversions", "orders_backend"], "Compare tracked conversions with backend orders")
    if not res.success:
        return _failed("check_tracking_consistency", res, 1)
    t = tracking_analysis(res.items, onset)
    an, be = t["analytics_conversions_per_session_change"], t["backend_orders_per_session_change"]
    key = "tracking"
    draft = EvidenceDraft(
        key, "sheets", "tracking_consistency", f"{st.sheet_tab}:tracking@{onset:%Y-%m-%dT%H:%M}",
        f"Tracked conversions/session {pct(an)} vs backend orders/session {pct(be)}",
        f"Analytics-tracked conversions per session changed {pct(an)}; orders recorded by the backend per session changed "
        f"{pct(be)}. Tracked share of backend orders: {t['tracked_share_before']} → {t['tracked_share_after']}.",
        observed_at=onset, metadata=t, derived_from=[f"{st.sheet_tab}!conversions,orders_backend,sessions"], strength=STRONG,
    )
    a: list[Assessment] = []
    if an is not None and be is not None:
        if an <= -0.25 and abs(be) < 0.12:
            a += [
                Assessment(key, "tracking_failure", S, STRONG, "Backend orders held steady while tracked conversions fell: purchases happen but are not recorded"),
                Assessment(key, "checkout_regression", C, STRONG, "Backend orders per session are unchanged, so customers are still completing checkout"),
                Assessment(key, "payment_provider_issue", C, STRONG, "Backend orders per session are unchanged, so payments are succeeding"),
                Assessment(key, "marketing_traffic_quality", C, MOD, "Real orders per session are unchanged, so visitor intent has not fallen"),
            ]
        elif abs(an - be) < 0.12:
            a += [
                Assessment(key, "tracking_failure", C, STRONG, "Backend orders fell in step with tracked conversions: the drop is real, not a tracking artifact"),
                Assessment(key, "checkout_regression", S, WEAK, "The drop is confirmed in backend orders"),
                Assessment(key, "payment_provider_issue", S, WEAK, "The drop is confirmed in backend orders"),
                Assessment(key, "marketing_traffic_quality", S, WEAK, "The drop is confirmed in backend orders"),
            ]
    return ProbeOutcome("check_tracking_consistency", "ok", note=draft.title, evidence=[draft], assessments=a, tool_calls=1)


async def check_traffic_mix(p: ProbeContext) -> ProbeOutcome:
    st = p.state
    onset = st.anomaly["onset"]
    res = await _read_columns(p, ["sessions", "paid_sessions"], "Check traffic volume and paid-traffic mix")
    if not res.success:
        return _failed("check_traffic_mix", res, 1)
    m = traffic_mix_analysis(res.items, onset)
    delta, change = m["paid_share_delta_pp"], m["sessions_change"]
    key = "traffic"
    draft = EvidenceDraft(
        key, "sheets", "traffic_mix", f"{st.sheet_tab}:traffic@{onset:%Y-%m-%dT%H:%M}",
        f"Traffic after onset: sessions/hour {pct(change)}, paid share "
        f"{_fmt_rate(m['paid_share_before'])} → {_fmt_rate(m['paid_share_after'])}",
        f"Average sessions per hour {m['sessions_per_hour_before']} → {m['sessions_per_hour_after']}; paid share of "
        f"sessions changed by {delta} percentage points.",
        observed_at=onset, metadata=m, derived_from=[f"{st.sheet_tab}!sessions,paid_sessions"], strength=MOD,
    )
    a: list[Assessment] = []
    if delta is not None:
        if delta >= 10 or (change is not None and change >= 0.3 and delta >= 5):
            a.append(Assessment(key, "marketing_traffic_quality", S, STRONG, f"Paid traffic share rose {delta:+.0f} pp with the drop: a large influx of new visitors"))
        elif abs(delta) < 5 and (change is None or abs(change) < 0.2):
            a.append(Assessment(key, "marketing_traffic_quality", C, MOD, "Traffic volume and paid share are essentially unchanged"))
    return ProbeOutcome("check_traffic_mix", "ok", note=draft.title, evidence=[draft], assessments=a, tool_calls=1)


async def check_recent_deployments(p: ProbeContext) -> ProbeOutcome:
    st = p.state
    onset = st.anomaly["onset"]
    since = onset - timedelta(hours=24)
    until = max(min(onset + timedelta(hours=2), st.now), onset + timedelta(minutes=1))
    res = await p.runner.call(
        p.tool_ctx, "github.list_deployments",
        {"since": since.isoformat(), "until": until.isoformat()},
        purpose="Check what shipped around the onset",
    )
    if not res.success:
        return _failed("check_recent_deployments", res, 1)
    deployments = res.items
    repo = res.data.get("repo", "repository")
    preceding = sorted(
        [d for d in deployments if timedelta(0) <= onset - d["created_at"] <= timedelta(hours=6)],
        key=lambda d: onset - d["created_at"],
    )
    later = [d for d in deployments if d["created_at"] > onset]
    evidence, a = [], []
    for d in preceding[:3]:
        minutes = (onset - d["created_at"]).total_seconds() / 60
        key = f"deploy:{d['id']}"
        evidence.append(
            EvidenceDraft(
                key, "github", "deployment", str(d["id"]),
                f"{d['ref']} deployed to {d['environment'] or 'production'} {minutes:.0f} min before the decline",
                f"{d['description'] or d['ref']} (sha {d['sha'][:7]}, by {d['creator'] or 'unknown'}) at "
                f"{d['created_at']:%Y-%m-%d %H:%M} UTC. Timing alone does not establish cause.",
                observed_at=d["created_at"], url=d.get("url"),
                metadata={"ref": d["ref"], "sha": d["sha"], "environment": d["environment"], "minutes_before_onset": round(minutes)},
                strength=WEAK,
            )
        )
        why = f"{d['ref']} shipped {minutes:.0f} min before the decline (timing only)"
        a += [
            Assessment(key, "checkout_regression", S, WEAK, why),
            Assessment(key, "tracking_failure", S, WEAK, why),
        ]
    for d in later[:2]:
        minutes = (d["created_at"] - onset).total_seconds() / 60
        evidence.append(
            EvidenceDraft(
                f"deploy:{d['id']}", "github", "deployment", str(d["id"]),
                f"{d['ref']} deployed {minutes:.0f} min after the decline began",
                f"{d['description'] or d['ref']} shipped after the onset, so it cannot explain when the decline started.",
                observed_at=d["created_at"], url=d.get("url"), metadata={"ref": d["ref"], "sha": d["sha"]}, strength=WEAK,
            )
        )
    if not preceding:
        evidence.append(
            EvidenceDraft(
                "no_deploy", "github", "deployment_absence", f"{repo}:none-before:{onset:%Y%m%dT%H%M}",
                "No deployments or releases in the 6 hours before the decline",
                f"Checked {repo} deployments and releases from {since:%b %d %H:%M} to {until:%b %d %H:%M} UTC: "
                f"{len(deployments)} found, none in the 6 hours before the onset.",
                observed_at=onset, metadata={"checked": len(deployments), "repo": repo}, strength=MOD,
            )
        )
        a += [
            Assessment("no_deploy", "checkout_regression", C, MOD, "No code shipped shortly before the decline"),
            Assessment("no_deploy", "tracking_failure", C, WEAK, "No release that could have broken tracking"),
        ]
    st.candidate_deployments = preceding[:2]
    note = (
        f"{len(preceding)} deployment(s) shipped in the 6h before onset: {', '.join(d['ref'] for d in preceding[:3])}"
        if preceding
        else "No deployment shipped in the 6h before onset"
    )
    return ProbeOutcome("check_recent_deployments", "ok", note=note, evidence=evidence, assessments=a, tool_calls=1)


async def inspect_deployment_changes(p: ProbeContext) -> ProbeOutcome:
    st = p.state
    onset = st.anomaly["onset"]
    evidence, a, calls, last_failure = [], [], 0, None
    for d in st.candidate_deployments[:2]:
        res = await p.runner.call(
            p.tool_ctx, "github.list_deployment_changes", {"deployment_id": d["id"]},
            purpose=f"Inspect the code shipped in {d['ref']}",
        )
        calls += 1
        if not res.success:
            last_failure = res
            continue
        files = res.data.get("files", [])
        commits = res.items
        minutes = (onset - d["created_at"]).total_seconds() / 60
        key = f"change:{d['id']}"
        evidence.append(
            EvidenceDraft(
                key, "github", "code_change", f"{d['id']}:changes",
                f"{d['ref']} changed {len(files)} file(s): {', '.join(files[:3])}{'…' if len(files) > 3 else ''}",
                "Commits: " + "; ".join(f"{c['sha'][:7]} {c['message']}" for c in commits[:5])
                + ". Files: " + ", ".join(files[:12]),
                observed_at=d["created_at"], url=(commits[0].get("url") if commits else d.get("url")),
                metadata={"ref": d["ref"], "files": files, "commits": [{"sha": c["sha"], "message": c["message"]} for c in commits[:5]], "minutes_before_onset": round(minutes)},
                strength=MOD, llm_assessable=True,
            )
        )
        a += assess_change(key, d["ref"], files, minutes)
    if not evidence and last_failure is not None:
        return _failed("inspect_deployment_changes", last_failure, calls)
    return ProbeOutcome(
        "inspect_deployment_changes", "ok", note="; ".join(e.title for e in evidence), evidence=evidence, assessments=a, tool_calls=calls
    )


async def search_slack_reports(p: ProbeContext) -> ProbeOutcome:
    st = p.state
    onset = st.anomaly["onset"]
    since = onset - timedelta(hours=2)
    until = max(st.now, onset + timedelta(minutes=1))
    res = await p.runner.call(
        p.tool_ctx, "slack.search_messages",
        {"terms": SLACK_TERMS, "since": since.isoformat(), "until": until.isoformat(), "limit": 50},
        purpose="Search team channels for reports around the onset",
    )
    if not res.success:
        return _failed("search_slack_reports", res, 1)
    evidence, a = [], []
    for m in res.items:
        key = f"msg:{m['id']}"
        evidence.append(
            EvidenceDraft(
                key, "slack", "message", m["id"],
                f"#{m['channel_name']} · {m['user']}: “{m['text'][:100]}{'…' if len(m['text']) > 100 else ''}”",
                m["text"], observed_at=m["observed_at"], url=m.get("url"),
                metadata={"channel": m["channel_name"], "user": m["user"]}, strength=WEAK, llm_assessable=True,
            )
        )
        a += assess_message(key, m["text"])
    return ProbeOutcome(
        "search_slack_reports", "ok", note=f"{len(res.items)} message(s) matched the search",
        evidence=evidence, assessments=a, facts={"hits": len(res.items)}, tool_calls=1,
    )


PROBES: dict[str, ProbeDef] = {
    p.id: p
    for p in [
        ProbeDef(
            "establish_anomaly", App.SHEETS, "Establish the anomaly",
            "Confirm from raw metrics whether the metric actually dropped, when, and by how much.",
            ["onset time", "size of the change"], {}, 0.1, establish_anomaly,
        ),
        ProbeDef(
            "check_recent_deployments", App.GITHUB, "Check recent deployments",
            "A code-level cause requires something to have shipped shortly before the drop.",
            ["deployments near the onset", "time between deploy and drop"],
            {"checkout_regression": 0.9, "tracking_failure": 0.5}, 0.15, check_recent_deployments,
        ),
        ProbeDef(
            "inspect_deployment_changes", App.GITHUB, "Inspect shipped code",
            "Look at which files the nearby deployment changed to see which system it could have broken.",
            ["changed files", "affected area"],
            {"checkout_regression": 1.0, "tracking_failure": 0.7, "payment_provider_issue": 0.3}, 0.15,
            inspect_deployment_changes, requires_deployments=True,
        ),
        ProbeDef(
            "check_checkout_funnel", App.SHEETS, "Check the checkout funnel",
            "Locate where in the funnel customers are lost and whether payment errors rose.",
            ["checkout start rate", "checkout completion rate", "payment error rate"],
            {"checkout_regression": 0.8, "payment_provider_issue": 0.8, "marketing_traffic_quality": 0.6}, 0.1,
            check_checkout_funnel, requires_columns=("sessions", "checkout_starts", "orders_backend"),
        ),
        ProbeDef(
            "check_tracking_consistency", App.SHEETS, "Check tracking consistency",
            "Compare analytics-tracked conversions with orders recorded by the backend to rule a measurement artifact in or out.",
            ["tracked vs backend orders"],
            {"tracking_failure": 1.0, "checkout_regression": 0.4, "payment_provider_issue": 0.4, "marketing_traffic_quality": 0.3},
            0.1, check_tracking_consistency, requires_columns=("sessions", "conversions", "orders_backend"),
        ),
        ProbeDef(
            "check_traffic_mix", App.SHEETS, "Check traffic mix",
            "See whether traffic volume or paid-traffic share changed with the drop.",
            ["sessions per hour", "paid traffic share"],
            {"marketing_traffic_quality": 1.0}, 0.1, check_traffic_mix, requires_columns=("sessions", "paid_sessions"),
        ),
        ProbeDef(
            "search_slack_reports", App.SLACK, "Search team reports",
            "Find independent human reports (support, engineering, marketing) that corroborate or contradict the candidates.",
            ["customer or engineer reports", "campaign or provider announcements"],
            {"checkout_regression": 0.7, "payment_provider_issue": 0.8, "tracking_failure": 0.6, "marketing_traffic_quality": 0.6},
            0.25, search_slack_reports,
        ),
    ]
}

UNLOCKS = {"check_recent_deployments": ("inspect_deployment_changes",)}
