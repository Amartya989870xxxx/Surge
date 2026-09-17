from datetime import datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.enums import App, ApprovalMode, ReasoningMode


class TimeRange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start: datetime
    end: datetime

    @model_validator(mode="after")
    def _check(self):
        if self.end <= self.start:
            raise ValueError("end must be after start")
        if self.end - self.start > timedelta(days=31):
            raise ValueError("time range may not exceed 31 days")
        return self


class CreateInvestigationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request: str = Field(min_length=5, max_length=4000, description="Natural-language description of the problem")
    time_range: TimeRange | None = None
    mode: Literal["interactive"] = "interactive"
    approval_mode: ApprovalMode = ApprovalMode.REQUIRED
    connector_mode: Literal["DEMO", "REAL"] | None = Field(
        default=None, description="Override the server's default connector mode for every app"
    )
    disabled_apps: list[App] = Field(default_factory=list)
    scenario_id: str | None = Field(default=None, pattern=r"^[a-z0-9_]{3,80}$", description="Seeded demo world to use")
    inject_failures: list[str] = Field(default_factory=list, max_length=6, description="Fault presets, see /api/connectors")
    reasoning: ReasoningMode | None = Field(default=None, description="llm or heuristic; defaults to server setting")
    persona: str | None = Field(
        default=None,
        pattern=r"^(founder|student|engineer|designer|marketer|other)$",
        description="Overrides the signed-in user's saved persona for this one investigation; ignored if not signed in and no persona given",
    )
    session_id: str = Field(default="anonymous", max_length=64, pattern=r"^[\w:.\-]+$")


class InvestigationCreated(BaseModel):
    id: str
    status: str
    stream_url: str
    connector_mode: str
    reasoning_mode: str
    scenario_id: str | None
    injected_faults: list[dict[str, Any]]


class ApproveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action_id: str = Field(pattern=r"^act_[0-9a-f]{12}$")
    approved: bool = True
    comment: str | None = Field(default=None, max_length=500)
    decided_by: str = Field(default="user", min_length=1, max_length=64)


class RerunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    clear_faults: bool = True


class RunEvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reasoning: ReasoningMode = ReasoningMode.HEURISTIC
    scenario_ids: list[str] | None = Field(default=None, max_length=50)


class EventOut(BaseModel):
    id: int
    investigation_id: str
    sequence: int
    timestamp: datetime
    event_type: str
    category: str
    actor: str
    status: str | None
    title: str
    summary: str | None
    tool_name: str | None
    external_app: str | None
    duration_ms: int | None
    input_summary: str | None
    output_summary: str | None
    error_code: str | None
    evidence_ids: list[str]
    hypothesis_ids: list[str]
    action_id: str | None
    data: dict[str, Any]


class EvidenceRelationOut(BaseModel):
    hypothesis_id: str
    hypothesis_kind: str
    hypothesis_label: str
    relation: str
    strength: str
    rationale: str
    assessed_by: str


class EvidenceOut(BaseModel):
    id: str
    investigation_id: str
    source_app: str
    source_type: str
    source_record_id: str
    epistemic_type: str = Field(description="observation | computed_observation | absence_check")
    title: str
    snippet: str
    normalized_content: str
    observed_at: datetime | None
    retrieved_at: datetime
    url: str | None
    source_metadata: dict[str, Any]
    derived_from: list[str]
    relevance_score: float
    evidence_strength: str
    connector_mode: str
    probe_id: str | None
    supports_hypothesis_ids: list[str]
    contradicts_hypothesis_ids: list[str]
    relations: list[EvidenceRelationOut]


class HypothesisEvidenceOut(BaseModel):
    evidence_id: str
    source_app: str
    title: str
    relation: str
    strength: str
    rationale: str
    assessed_by: str


class HypothesisOut(BaseModel):
    id: str
    kind: str
    label: str
    statement: str
    confidence: float
    prior: float
    status: str
    rank: int
    rationale: str
    missing_information: list[str]
    supporting_evidence_ids: list[str]
    contradicting_evidence_ids: list[str]
    independent_sources: list[str]
    evidence: list[HypothesisEvidenceOut]


class VerificationOut(BaseModel):
    method: str
    result: str
    checks: list[dict[str, Any]]
    expected_state: dict[str, Any]
    observed_state: dict[str, Any]
    confidence: float
    attempted_at: datetime
    error_code: str | None


class LifecycleStageOut(BaseModel):
    stage: str
    done: bool
    state: str | None


class ActionOut(BaseModel):
    id: str
    investigation_id: str
    action_type: str
    external_app: str
    target: str
    title: str
    rationale: str
    risk_level: str
    approval_required: bool
    approval_status: str
    execution_status: str
    verification_status: str
    idempotency_key: str
    external_result_id: str | None
    external_url: str | None
    hypothesis_id: str | None
    evidence_ids: list[str]
    attempts: int
    error: dict[str, Any] | None
    decided_by: str | None
    created_at: datetime
    decided_at: datetime | None
    completed_at: datetime | None
    preview: dict[str, Any]
    verification: VerificationOut | None
    lifecycle: list[LifecycleStageOut]
    requires_strong_confirmation: bool


class ClaimOut(BaseModel):
    id: str
    claim_type: str
    text: str
    evidence_ids: list[str]
    event_sequences: list[int]
    hypothesis_id: str | None
    requires_evidence: bool
    grounded: bool
    invalid_references: list[str]
    source: str
    position: int


class HypothesisBrief(BaseModel):
    id: str
    kind: str
    label: str
    confidence: float


class InvestigationSummaryOut(BaseModel):
    id: str
    session_id: str
    title: str
    request: str
    status: str
    outcome: str | None
    strongest_hypothesis: HypothesisBrief | None
    confidence: float | None
    action_count: int
    verified: bool
    pending_approval: bool
    degraded: bool
    execution_mode: str
    connector_mode: str
    reasoning_mode: str
    scenario_id: str | None
    duration_ms: int | None
    created_at: datetime
    completed_at: datetime | None


class InvestigationDetailOut(InvestigationSummaryOut):
    approval_mode: str
    severity: str | None
    time_window_start: datetime | None
    time_window_end: datetime | None
    started_at: datetime | None
    updated_at: datetime
    intent: dict[str, Any] | None
    final_summary: str | None
    confidence_breakdown: dict[str, Any] | None
    root_cause_hypothesis_id: str | None
    missing_sources: list[str]
    tool_call_count: int
    error: dict[str, Any] | None
    fault_injection: list[dict[str, Any]]
    connectors: list[dict[str, Any]]
    synthesis: dict[str, Any] | None
    pending_action_ids: list[str]
    counts: dict[str, int]
    links: dict[str, str]


class InvestigationListOut(BaseModel):
    items: list[InvestigationSummaryOut]
    total: int


class ConnectorsOut(BaseModel):
    default_mode: str
    connectors: list[dict[str, Any]]
    fault_presets: dict[str, str]


class EvaluationSuiteSummaryOut(BaseModel):
    id: str
    status: str
    reasoning_mode: str
    agent_version: str
    scenario_count: int
    started_at: datetime
    completed_at: datetime | None
    headline: dict[str, Any] | None


class EvaluationSuiteOut(EvaluationSuiteSummaryOut):
    report: dict[str, Any] | None
    report_text: str | None
    error: dict[str, Any] | None
    runs: list[dict[str, Any]]
