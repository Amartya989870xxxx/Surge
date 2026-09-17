from dataclasses import dataclass, field
from datetime import datetime

from app.enums import ReasoningMode, Relation, Strength
from app.tools.base import ToolResult


@dataclass
class EvidenceDraft:
    key: str
    source_app: str
    source_type: str
    source_record_id: str
    title: str
    content: str
    observed_at: datetime | None = None
    url: str | None = None
    metadata: dict = field(default_factory=dict)
    derived_from: list[str] = field(default_factory=list)
    strength: Strength = Strength.MODERATE
    llm_assessable: bool = False


@dataclass
class Assessment:
    evidence_key: str
    hypothesis_kind: str
    relation: Relation
    strength: Strength
    rationale: str
    assessed_by: str = "heuristic"


@dataclass
class ProbeOutcome:
    probe_id: str
    status: str  # ok | failed | not_applicable
    note: str = ""
    evidence: list[EvidenceDraft] = field(default_factory=list)
    assessments: list[Assessment] = field(default_factory=list)
    facts: dict = field(default_factory=dict)
    tool_calls: int = 0
    failed_tool: ToolResult | None = None


@dataclass
class Intent:
    metric: str
    metric_label: str
    window_start: datetime
    window_end: datetime
    read_start: datetime
    mentions_release: bool
    autonomous_action_requested: bool
    severity: str | None = None

    def to_dict(self) -> dict:
        return {
            "metric": self.metric,
            "metric_label": self.metric_label,
            "window_start": self.window_start.isoformat(),
            "window_end": self.window_end.isoformat(),
            "read_start": self.read_start.isoformat(),
            "mentions_release": self.mentions_release,
            "autonomous_action_requested": self.autonomous_action_requested,
            "severity": self.severity,
        }


@dataclass
class LinkView:
    evidence_id: str
    app: str
    relation: str
    strength: str
    rationale: str
    assessed_by: str
    title: str


@dataclass
class HypothesisView:
    id: str
    kind: str
    label: str
    statement: str
    prior: float
    confidence: float
    status: str
    supporting: list[LinkView]
    contradicting: list[LinkView]
    support_apps: list[str]
    rationale: str

    @property
    def tested(self) -> bool:
        return bool(self.supporting or self.contradicting)


@dataclass
class InvestigationState:
    investigation_id: str
    request: str
    intent: Intent
    now: datetime
    reasoning: ReasoningMode
    persona: str | None = None
    anomaly: dict | None = None
    anomaly_evidence_id: str | None = None
    sheet_tab: str | None = None
    sheet_columns: list[str] = field(default_factory=list)
    candidate_deployments: list[dict] = field(default_factory=list)
    probe_status: dict[str, str] = field(default_factory=dict)
    probe_notes: dict[str, str] = field(default_factory=dict)
    failed_apps: dict[str, dict] = field(default_factory=dict)
    succeeded_apps: set[str] = field(default_factory=set)
    hypothesis_ids: dict[str, str] = field(default_factory=dict)
    evidence_ids: dict[str, str] = field(default_factory=dict)
    tool_calls: int = 0
    last_probe: str | None = None
    decisions: list[dict] = field(default_factory=list)
