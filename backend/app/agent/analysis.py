"""Deterministic numeric analysis over sheet rows. The LLM never does arithmetic on metrics."""

import math
from datetime import datetime, timedelta

BASELINE_HOURS = 24


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)


def _var(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return sum((x - m) ** 2 for x in xs) / (len(xs) - 1)


def metric_value(row: dict, metric: str) -> float | None:
    value = row.get(metric)
    if value is None and metric == "conversion_rate":
        sessions, conversions = row.get("sessions"), row.get("conversions")
        if sessions and conversions is not None:
            value = 100 * conversions / sessions
    return value


def detect_change(
    rows: list[dict],
    metric: str,
    *,
    min_segment: int = 4,
    min_relative: float = 0.2,
    min_t: float = 4.0,
) -> dict:
    """Single change-point search: pick the split maximising Welch-like t, then require both a
    material relative drop and statistical separation from noise."""
    points = sorted(
        ((r["timestamp"], metric_value(r, metric), r.get("_row")) for r in rows),
        key=lambda p: p[0],
    )
    points = [p for p in points if p[1] is not None]
    n = len(points)
    if n < 2 * min_segment:
        return {"detected": False, "metric": metric, "reason": f"only {n} usable data points", "points": n}
    values = [p[1] for p in points]
    best = None
    for k in range(min_segment, n - min_segment + 1):
        a, b = values[:k], values[k:]
        ma, mb = _mean(a), _mean(b)
        pooled = math.sqrt(((len(a) - 1) * _var(a) + (len(b) - 1) * _var(b)) / (n - 2))
        se = pooled * math.sqrt(1 / len(a) + 1 / len(b))
        t = abs(mb - ma) / se if se > 0 else (999.0 if mb != ma else 0.0)
        if best is None or t > best[0]:
            best = (t, k, ma, mb)
    t, k, ma, mb = best
    relative = (mb - ma) / ma if ma else 0.0
    return {
        "detected": relative <= -min_relative and t >= min_t,
        "metric": metric,
        "onset": points[k][0],
        "before_mean": round(ma, 4),
        "after_mean": round(mb, 4),
        "relative_change": round(relative, 4),
        "t_stat": round(min(t, 999.0), 2),
        "baseline_points": k,
        "affected_points": n - k,
        "first_row": points[0][2],
        "onset_row": points[k][2],
        "last_row": points[-1][2],
        "series_start": points[0][0],
        "series_end": points[-1][0],
        "thresholds": {"min_relative_drop": min_relative, "min_t": min_t},
    }


def _split(rows: list[dict], onset: datetime) -> tuple[list[dict], list[dict]]:
    before = [r for r in rows if onset - timedelta(hours=BASELINE_HOURS) <= r["timestamp"] < onset]
    after = [r for r in rows if r["timestamp"] >= onset]
    return before, after


def _total(rows: list[dict], column: str) -> float:
    return sum(r.get(column) or 0.0 for r in rows)


def _rate(rows: list[dict], num: str, den: str) -> float | None:
    d = _total(rows, den)
    return _total(rows, num) / d if d else None


def _rel(before: float | None, after: float | None) -> float | None:
    if before is None or after is None or before == 0:
        return None
    return round((after - before) / before, 4)


def funnel_analysis(rows: list[dict], onset: datetime) -> dict:
    before, after = _split(rows, onset)
    sb, sa = _rate(before, "checkout_starts", "sessions"), _rate(after, "checkout_starts", "sessions")
    cb, ca = _rate(before, "orders_backend", "checkout_starts"), _rate(after, "orders_backend", "checkout_starts")
    return {
        "checkout_start_rate_before": sb,
        "checkout_start_rate_after": sa,
        "checkout_start_rate_change": _rel(sb, sa),
        "completion_rate_before": cb,
        "completion_rate_after": ca,
        "completion_rate_change": _rel(cb, ca),
        "hours_before": len(before),
        "hours_after": len(after),
    }


def payment_error_analysis(rows: list[dict], onset: datetime) -> dict:
    before, after = _split(rows, onset)
    eb, ea = _rate(before, "payment_errors", "checkout_starts"), _rate(after, "payment_errors", "checkout_starts")
    ratio = round(ea / eb, 2) if eb and ea is not None else None
    return {"error_rate_before": eb, "error_rate_after": ea, "ratio": ratio}


def tracking_analysis(rows: list[dict], onset: datetime) -> dict:
    before, after = _split(rows, onset)
    ab, aa = _rate(before, "conversions", "sessions"), _rate(after, "conversions", "sessions")
    ob, oa = _rate(before, "orders_backend", "sessions"), _rate(after, "orders_backend", "sessions")
    return {
        "analytics_conversions_per_session_change": _rel(ab, aa),
        "backend_orders_per_session_change": _rel(ob, oa),
        "tracked_share_before": round(_total(before, "conversions") / _total(before, "orders_backend"), 3)
        if _total(before, "orders_backend")
        else None,
        "tracked_share_after": round(_total(after, "conversions") / _total(after, "orders_backend"), 3)
        if _total(after, "orders_backend")
        else None,
    }


def traffic_mix_analysis(rows: list[dict], onset: datetime) -> dict:
    before, after = _split(rows, onset)
    per_hour_before = _total(before, "sessions") / len(before) if before else None
    per_hour_after = _total(after, "sessions") / len(after) if after else None
    share_before = _rate(before, "paid_sessions", "sessions")
    share_after = _rate(after, "paid_sessions", "sessions")
    delta_pp = (
        round(100 * (share_after - share_before), 1)
        if share_before is not None and share_after is not None
        else None
    )
    return {
        "sessions_per_hour_before": round(per_hour_before, 1) if per_hour_before else None,
        "sessions_per_hour_after": round(per_hour_after, 1) if per_hour_after else None,
        "sessions_change": _rel(per_hour_before, per_hour_after),
        "paid_share_before": round(share_before, 3) if share_before is not None else None,
        "paid_share_after": round(share_after, 3) if share_after is not None else None,
        "paid_share_delta_pp": delta_pp,
    }


def pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:+.0f}%"
