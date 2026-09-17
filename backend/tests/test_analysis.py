from app.agent.analysis import detect_change, funnel_analysis, tracking_analysis, traffic_mix_analysis
from app.scenarios import generate_metric_rows, parse_dt
from app.tools.sheets import _number

BASE = {"start": "2026-09-11T09:00:00Z", "hours": 48, "seed": 11}
ONSET = parse_dt("2026-09-12T14:00:00Z")


def rows(generator: dict) -> list[dict]:
    columns, raw = generate_metric_rows(generator)
    out = []
    for index, values in enumerate(raw, start=2):
        record = {"_row": index}
        for column, value in zip(columns, values, strict=True):
            record[column] = parse_dt(value) if column == "timestamp" else _number(value)
        out.append(record)
    return out


def with_change(**multiply) -> dict:
    return {**BASE, "changes": [{"at": "2026-09-12T14:00:00Z", "multiply": multiply}]}


def test_change_point_detects_drop_at_true_onset():
    result = detect_change(rows(with_change(completion_rate=0.37)), "conversion_rate")
    assert result["detected"]
    assert result["onset"] == ONSET
    assert result["relative_change"] < -0.5


def test_normal_noise_is_not_reported_as_an_anomaly():
    for seed in range(1, 25):
        assert not detect_change(rows({**BASE, "seed": seed}), "conversion_rate")["detected"], seed


def test_too_little_data_is_reported_not_guessed():
    result = detect_change(rows({**BASE, "hours": 5}), "conversion_rate")
    assert not result["detected"] and "reason" in result


def test_funnel_localizes_failure_inside_checkout():
    f = funnel_analysis(rows(with_change(completion_rate=0.37)), ONSET)
    assert f["completion_rate_change"] < -0.5
    assert abs(f["checkout_start_rate_change"]) < 0.15


def test_tracking_failure_keeps_backend_orders_flat():
    t = tracking_analysis(rows(with_change(tracking_ratio=0.3)), ONSET)
    assert t["analytics_conversions_per_session_change"] < -0.5
    assert abs(t["backend_orders_per_session_change"]) < 0.12


def test_campaign_traffic_shifts_paid_share():
    generator = {**BASE, "changes": [{"at": "2026-09-12T14:00:00Z", "set": {"extra_paid_sessions": 900, "extra_intent": 0.15}}]}
    m = traffic_mix_analysis(rows(generator), ONSET)
    assert m["paid_share_delta_pp"] > 20
    assert m["sessions_change"] > 0.5
