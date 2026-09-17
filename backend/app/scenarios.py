"""Scenario and demo-world loading.

A *world* is seeded provider data (sheet rows, deployments, Slack messages). It contains no
labels about causes. A *scenario* pairs a world with a request, optional fault injection and a
ground truth block. Ground truth is only ever read by the evaluation harness.
"""

import copy
import math
import random
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

METRIC_COLUMNS = [
    "timestamp",
    "sessions",
    "paid_sessions",
    "checkout_starts",
    "orders_backend",
    "conversions",
    "payment_errors",
    "conversion_rate",
]


def parse_dt(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    text = str(value).strip().replace("Z", "+00:00")
    if " " in text and "T" not in text:
        text = text.replace(" ", "T")
    dt = datetime.fromisoformat(text)
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


class EvidenceMatcher(BaseModel):
    key: str | None = None
    app: str
    source_type: str | None = None
    record_id: str | None = None
    content_contains: str | None = None


class GroundTruth(BaseModel):
    expected_outcome: str
    acceptable_outcomes: list[str] = Field(default_factory=list)
    required_evidence: list[EvidenceMatcher] = Field(default_factory=list)
    relevant_evidence: list[EvidenceMatcher] = Field(default_factory=list)
    expected_action: str = "none"  # create_github_issue | comment_github_issue | blocked | none
    acceptable_actions: list[str] = Field(default_factory=list)
    approval_required: bool = True
    expect_verified: bool = False
    expect_degraded: bool = False
    recovery_expected: bool = False
    max_confidence: float | None = None
    min_confidence: float | None = None

    def accepts(self, outcome_key: str | None) -> bool:
        allowed = set(self.acceptable_outcomes) | {self.expected_outcome}
        return outcome_key in allowed


class Scenario(BaseModel):
    scenario_id: str
    title: str
    category: str
    description: str = ""
    request: str
    time_range: dict | None = None
    repeat: int = 1
    approval: str = "approve"
    world: str
    world_overrides: dict = Field(default_factory=dict)
    faults: list[dict] = Field(default_factory=list)
    ground_truth: GroundTruth

    def public_view(self) -> dict:
        return {
            "scenario_id": self.scenario_id,
            "title": self.title,
            "category": self.category,
            "description": self.description,
            "request": self.request,
            "faults": self.faults,
        }


@dataclass
class DemoWorld:
    world_id: str
    reference_time: datetime
    sheets: dict
    github: dict
    slack: dict
    meta: dict = field(default_factory=dict)


def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def generate_metric_rows(generator: dict, columns: list[str] | None = None) -> tuple[list[str], list[list[str]]]:
    columns = columns or METRIC_COLUMNS
    start = parse_dt(generator["start"])
    rng = random.Random(generator.get("seed", 1))
    params = {
        "sessions": 1000.0,
        "paid_share": 0.22,
        "checkout_start_rate": 0.19,
        "completion_rate": 0.44,
        "payment_error_rate": 0.012,
        "tracking_ratio": 1.0,
        "extra_paid_sessions": 0.0,
        "extra_intent": 1.0,
    }
    params.update(generator.get("baseline", {}))
    noise = float(generator.get("noise", 0.03))
    diurnal = float(generator.get("diurnal", 0.2))
    changes = generator.get("changes", [])

    def jitter() -> float:
        return max(0.0, rng.gauss(1.0, noise))

    rows: list[list[str]] = []
    for i in range(int(generator.get("hours", 48))):
        ts = start + timedelta(hours=i)
        p = dict(params)
        for change in changes:
            at = parse_dt(change["at"])
            until = parse_dt(change["until"]) if change.get("until") else None
            if ts >= at and (until is None or ts < until):
                for k, v in change.get("multiply", {}).items():
                    p[k] *= v
                for k, v in change.get("set", {}).items():
                    p[k] = v
        daily = 1 + diurnal * math.sin((ts.hour - 8) / 24 * 2 * math.pi)
        base_sessions = p["sessions"] * daily * jitter()
        extra = p["extra_paid_sessions"] * daily * jitter()
        sessions = base_sessions + extra
        paid = base_sessions * p["paid_share"] + extra
        starts = base_sessions * p["checkout_start_rate"] * jitter() + (
            extra * p["checkout_start_rate"] * p["extra_intent"]
        )
        orders = starts * p["completion_rate"] * jitter()
        payment_errors = starts * p["payment_error_rate"] * jitter()
        conversions = orders * p["tracking_ratio"]
        record = {
            "timestamp": ts.strftime("%Y-%m-%d %H:%M"),
            "sessions": str(round(sessions)),
            "paid_sessions": str(round(paid)),
            "checkout_starts": str(round(starts)),
            "orders_backend": str(round(orders)),
            "conversions": str(round(conversions)),
            "payment_errors": str(round(payment_errors)),
            "conversion_rate": f"{(100 * round(conversions) / round(sessions)) if round(sessions) else 0:.2f}",
        }
        rows.append([record[c] for c in columns])
    return columns, rows


def build_world(raw: dict) -> DemoWorld:
    sheets = copy.deepcopy(raw.get("sheets", {}))
    for tab in sheets.get("tabs", {}).values():
        if "generator" in tab:
            cols, rows = generate_metric_rows(tab["generator"], tab.get("columns"))
            tab["columns"], tab["rows"] = cols, rows
            del tab["generator"]
    github = copy.deepcopy(raw.get("github", {}))
    github.setdefault("deployments", [])
    github.setdefault("issues", [])
    github.setdefault("comments", {})
    github["next_issue_number"] = max([i["number"] for i in github["issues"]] or [180]) + 1
    slack = copy.deepcopy(raw.get("slack", {}))
    slack.setdefault("channels", [])
    slack.setdefault("messages", [])
    return DemoWorld(
        world_id=raw["world_id"],
        reference_time=parse_dt(raw["reference_time"]),
        sheets=sheets,
        github=github,
        slack=slack,
        meta={"title": raw.get("title", raw["world_id"])},
    )


class ScenarioLibrary:
    def __init__(self, scenarios_dir: Path, worlds_dir: Path):
        self.scenarios_dir = scenarios_dir
        self.worlds_dir = worlds_dir

    def list(self) -> list[Scenario]:
        return [self._load_scenario(p) for p in sorted(self.scenarios_dir.glob("*.yaml"))]

    def get(self, scenario_id: str) -> Scenario:
        path = self.scenarios_dir / f"{scenario_id}.yaml"
        if not path.exists():
            raise KeyError(scenario_id)
        return self._load_scenario(path)

    def build_world(self, scenario: Scenario) -> DemoWorld:
        path = self.worlds_dir / f"{scenario.world}.yaml"
        raw = yaml.safe_load(path.read_text())
        if scenario.world_overrides:
            raw = _deep_merge(raw, scenario.world_overrides)
        return build_world(raw)

    @staticmethod
    def _load_scenario(path: Path) -> Scenario:
        return Scenario.model_validate(yaml.safe_load(path.read_text()))


class WorldRegistry:
    """Process-wide demo worlds, so provider-side state (e.g. created issues) persists across
    investigations in demo mode, the way a real provider would."""

    def __init__(self, library: ScenarioLibrary):
        self.library = library
        self._worlds: dict[str, DemoWorld] = {}

    def get(self, world_key: str, scenario_id: str) -> DemoWorld:
        if world_key not in self._worlds:
            self._worlds[world_key] = self.library.build_world(self.library.get(scenario_id))
        return self._worlds[world_key]

    def put(self, world_key: str, world: DemoWorld) -> None:
        self._worlds[world_key] = world

    def reset(self, world_key: str | None = None) -> None:
        if world_key is None:
            self._worlds.clear()
        else:
            self._worlds.pop(world_key, None)
