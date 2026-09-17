"""Heuristic evidence assessment for unstructured sources (code changes, chat messages).
Used directly in heuristic mode and as the validated fallback when the LLM assessor fails."""

import re

from app.agent.types import Assessment
from app.enums import Relation, Strength

S, C = Relation.SUPPORTS, Relation.CONTRADICTS
WEAK, MOD, STRONG = Strength.WEAK, Strength.MODERATE, Strength.STRONG

_CHECKOUT_PATH = re.compile(r"(^|/)(checkout|cart|basket|payment[-_]?form|purchase)", re.I)
_ANALYTICS_PATH = re.compile(r"(^|/)(analytics|tracking|telemetry|segment|gtag|gtm|pixel)|track(ing|er)?\.", re.I)
_PAYMENTS_PATH = re.compile(r"(^|/)(payments?|billing)/|stripe|adyen|braintree", re.I)
_NON_RUNTIME = re.compile(r"(^|/)(docs?|\.github)/|readme|changelog|\.md$|(^|/)tests?/|\.test\.|_test\.|\.spec\.", re.I)


def change_areas(files: list[str]) -> set[str]:
    areas: set[str] = set()
    for path in files:
        if _CHECKOUT_PATH.search(path):
            areas.add("checkout")
        if _ANALYTICS_PATH.search(path):
            areas.add("analytics")
        if _PAYMENTS_PATH.search(path):
            areas.add("payments_integration")
    if files and all(_NON_RUNTIME.search(p) for p in files):
        areas = {"non_runtime"}
    return areas


def assess_change(key: str, ref: str, files: list[str], minutes_before_onset: float) -> list[Assessment]:
    areas = change_areas(files)
    close = 0 <= minutes_before_onset <= 180
    shown = ", ".join(files[:3]) + ("…" if len(files) > 3 else "")
    if "non_runtime" in areas:
        why = f"{ref} only changed documentation/tests ({shown}); it cannot plausibly change runtime behaviour"
        return [
            Assessment(key, "checkout_regression", C, MOD, why),
            Assessment(key, "tracking_failure", C, MOD, why),
        ]
    out: list[Assessment] = []
    both = {"checkout", "analytics"} <= areas
    if "checkout" in areas:
        strength = STRONG if close and not both else MOD
        out.append(Assessment(key, "checkout_regression", S, strength, f"{ref} modified checkout code ({shown})"))
    if "analytics" in areas:
        strength = STRONG if close and not both else MOD
        out.append(Assessment(key, "tracking_failure", S, strength, f"{ref} modified analytics/tracking code ({shown})"))
    if "payments_integration" in areas:
        if "checkout" not in areas:
            out.append(Assessment(key, "checkout_regression", S, MOD, f"{ref} modified our payment integration ({shown})"))
        out.append(Assessment(key, "payment_provider_issue", S, WEAK, f"{ref} touched payment-provider integration code"))
    if not areas:
        out.append(
            Assessment(key, "checkout_regression", C, WEAK, f"{ref} did not touch checkout, payments or analytics code ({shown})")
        )
    if not close:
        for a in out:
            if a.relation == S:
                a.strength = WEAK
    return out


_FAIL = r"(fail|broken|break|error|spin|stuck|hang|not work|doesn'?t work|can'?t|cannot|unable|\b500\b|exception|bug|blank)"
_MESSAGE_RULES: list[tuple[re.Pattern, list[tuple[str, Relation, Strength, str]]]] = [
    (
        re.compile(
            rf"(checkout|place order|cart|payment form|purchase).{{0,60}}{_FAIL}|{_FAIL}.{{0,60}}(checkout|place order|payment form)",
            re.I,
        ),
        [("checkout_regression", S, MOD, "Independent report of checkout failures")],
    ),
    (
        re.compile(
            r"(stripe|adyen|braintree|payment provider|payments? gateway|processor|psp)\b.{0,80}"
            r"(degrad|outage|incident|error|down|elevated|timeout|declin)|card[_ ]declin",
            re.I,
        ),
        [("payment_provider_issue", S, MOD, "Report of a payment-provider problem")],
    ),
    (
        re.compile(r"(stripe|payment provider|psp)\b.{0,60}(green|operational|healthy|all good|no (incident|issues))", re.I),
        [("payment_provider_issue", C, MOD, "Payment provider reported as healthy")],
    ),
    (
        re.compile(
            r"(analytics|tracking|dashboard|segment|gtag|pixel)\b.{0,80}(broken|missing|not firing|stopped|wrong|off\b|cratered|zero|dropped)"
            r"|(numbers|dashboard|metrics)\b.{0,40}(look|seem|are)\b.{0,20}(off\b|wrong|weird)",
            re.I,
        ),
        [("tracking_failure", S, MOD, "Report that analytics numbers look wrong")],
    ),
    (
        re.compile(
            r"(orders|payouts|revenue|sales|transactions)\b.{0,60}(normal|fine|steady|as usual|look(s)? (ok|okay)|unchanged)",
            re.I,
        ),
        [
            ("tracking_failure", S, MOD, "Real orders/payouts reported normal while tracked conversions fell"),
            ("checkout_regression", C, MOD, "Orders reportedly unaffected, which a checkout failure would not allow"),
            ("payment_provider_issue", C, WEAK, "Payments reportedly flowing normally"),
        ],
    ),
    (
        re.compile(
            r"(campaign|influencer|creator|\bads?\b|utm|tiktok|promo|paid social).{0,80}"
            r"(live|launched|went out|started|spike|pouring|traffic|kicked off)",
            re.I,
        ),
        [("marketing_traffic_quality", S, MOD, "Report of a new campaign or traffic change")],
    ),
]


def assess_message(key: str, text: str) -> list[Assessment]:
    out: dict[tuple[str, Relation], Assessment] = {}
    for pattern, effects in _MESSAGE_RULES:
        if not pattern.search(text):
            continue
        for kind, relation, strength, rationale in effects:
            out.setdefault((kind, relation), Assessment(key, kind, relation, strength, rationale))
    kinds_supported = {k for k, r in out if r == S}
    # A message cannot both support and contradict the same hypothesis; support from explicit reports wins.
    return [a for (k, r), a in out.items() if not (r == C and k in kinds_supported)]
