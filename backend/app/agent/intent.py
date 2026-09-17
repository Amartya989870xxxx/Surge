import re
from datetime import datetime, timedelta

from app.agent.policy import requests_autonomous_action
from app.agent.types import Intent
from app.scenarios import parse_dt

BASELINE_PADDING = timedelta(hours=24)
_RELEASE = re.compile(r"releas|deploy|ship|rollout|roll out|launch|version|push(ed)? to prod", re.I)
_SEVERITY = re.compile(r"\b(sev ?[0-4]|p[0-4])\b|critical|urgent", re.I)


def parse_intent(request: str, time_range: dict | None, now: datetime) -> Intent:
    text = request or ""
    metric, label = "conversion_rate", "conversion rate"
    if re.search(r"\border", text, re.I) and not re.search(r"conver", text, re.I):
        metric, label = "orders_backend", "orders"

    if time_range and time_range.get("start") and time_range.get("end"):
        start, end = parse_dt(time_range["start"]), parse_dt(time_range["end"])
    else:
        lookback = timedelta(hours=48)
        if re.search(r"last week|past week|7 days", text, re.I):
            lookback = timedelta(days=7)
        end, start = now, now - lookback

    severity = None
    if m := _SEVERITY.search(text):
        severity = m.group(0).lower()

    return Intent(
        metric=metric,
        metric_label=label,
        window_start=start,
        window_end=end,
        read_start=start - BASELINE_PADDING,
        mentions_release=bool(_RELEASE.search(text)),
        autonomous_action_requested=requests_autonomous_action(text),
        severity=severity,
    )
