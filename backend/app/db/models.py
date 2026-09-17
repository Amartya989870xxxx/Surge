import secrets
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(6)}"


class UTCDateTime(TypeDecorator):
    """Stores naive UTC, always returns tz-aware UTC (SQLite drops tzinfo)."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=UTC)


class Base(DeclarativeBase):
    pass


class Investigation(Base):
    __tablename__ = "investigations"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), default="anonymous")
    title: Mapped[str] = mapped_column(String(200))
    user_request: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), index=True)
    execution_mode: Mapped[str] = mapped_column(String(20))
    connector_mode: Mapped[str] = mapped_column(String(20))
    reasoning_mode: Mapped[str] = mapped_column(String(20))
    approval_mode: Mapped[str] = mapped_column(String(20))
    scenario_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    world_key: Mapped[str | None] = mapped_column(String(120), nullable=True)
    fault_injection: Mapped[list] = mapped_column(JSON, default=list)
    connector_profile: Mapped[dict] = mapped_column(JSON, default=dict)
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)

    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    time_window_start: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    time_window_end: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)

    intent: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(40), nullable=True)
    final_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    root_cause_hypothesis_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    synthesis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    degraded: Mapped[bool] = mapped_column(Boolean, default=False)
    missing_sources: Mapped[list] = mapped_column(JSON, default=list)
    tool_call_count: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class InvestigationEvent(Base):
    __tablename__ = "investigation_events"
    __table_args__ = (UniqueConstraint("investigation_id", "sequence"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    investigation_id: Mapped[str] = mapped_column(String(40), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    event_type: Mapped[str] = mapped_column(String(40))
    actor: Mapped[str] = mapped_column(String(16))
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    external_app: Mapped[str | None] = mapped_column(String(20), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    evidence_ids: Mapped[list] = mapped_column(JSON, default=list)
    hypothesis_ids: Mapped[list] = mapped_column(JSON, default=list)
    action_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict)


class EvidenceItem(Base):
    __tablename__ = "evidence_items"
    __table_args__ = (UniqueConstraint("investigation_id", "dedupe_key"),)

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    investigation_id: Mapped[str] = mapped_column(String(40), index=True)
    source_app: Mapped[str] = mapped_column(String(20))
    source_type: Mapped[str] = mapped_column(String(40))
    source_record_id: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(300))
    normalized_content: Mapped[str] = mapped_column(Text)
    observed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    derived_from: Mapped[list] = mapped_column(JSON, default=list)
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)
    evidence_strength: Mapped[str] = mapped_column(String(16), default="weak")
    dedupe_key: Mapped[str] = mapped_column(String(64))
    connector_mode: Mapped[str] = mapped_column(String(20))
    probe_id: Mapped[str | None] = mapped_column(String(60), nullable=True)


class EvidenceLink(Base):
    __tablename__ = "evidence_links"
    __table_args__ = (UniqueConstraint("evidence_id", "hypothesis_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    investigation_id: Mapped[str] = mapped_column(String(40), index=True)
    evidence_id: Mapped[str] = mapped_column(String(40), index=True)
    hypothesis_id: Mapped[str] = mapped_column(String(40), index=True)
    relation: Mapped[str] = mapped_column(String(16))
    strength: Mapped[str] = mapped_column(String(16))
    rationale: Mapped[str] = mapped_column(Text)
    assessed_by: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class Hypothesis(Base):
    __tablename__ = "hypotheses"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    investigation_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(60))
    label: Mapped[str] = mapped_column(String(120))
    statement: Mapped[str] = mapped_column(Text)
    prior: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(32))
    rationale: Mapped[str] = mapped_column(Text, default="")
    missing_information: Mapped[list] = mapped_column(JSON, default=list)
    tested_by: Mapped[list] = mapped_column(JSON, default=list)
    rank: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)


class Action(Base):
    __tablename__ = "actions"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    investigation_id: Mapped[str] = mapped_column(String(40), index=True)
    action_type: Mapped[str] = mapped_column(String(60))
    external_app: Mapped[str] = mapped_column(String(20))
    target: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(300))
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    rationale: Mapped[str] = mapped_column(Text, default="")
    risk_level: Mapped[str] = mapped_column(String(10))
    approval_required: Mapped[bool] = mapped_column(Boolean, default=True)
    approval_status: Mapped[str] = mapped_column(String(20))
    execution_status: Mapped[str] = mapped_column(String(20))
    idempotency_key: Mapped[str] = mapped_column(String(64), index=True)
    external_result_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    external_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    verification_status: Mapped[str] = mapped_column(String(20))
    verification_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    hypothesis_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    evidence_ids: Mapped[list] = mapped_column(JSON, default=list)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    decided_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


class Verification(Base):
    __tablename__ = "verifications"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    action_id: Mapped[str] = mapped_column(String(40), index=True)
    method: Mapped[str] = mapped_column(String(80))
    attempted_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    result: Mapped[str] = mapped_column(String(20))
    expected_state: Mapped[dict] = mapped_column(JSON, default=dict)
    observed_state: Mapped[dict] = mapped_column(JSON, default=dict)
    checks: Mapped[list] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    error_code: Mapped[str | None] = mapped_column(String(40), nullable=True)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    action_id: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20))
    external_result_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    external_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    investigation_id: Mapped[str] = mapped_column(String(40), index=True)
    claim_type: Mapped[str] = mapped_column(String(20))
    text: Mapped[str] = mapped_column(Text)
    evidence_ids: Mapped[list] = mapped_column(JSON, default=list)
    event_sequences: Mapped[list] = mapped_column(JSON, default=list)
    hypothesis_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    requires_evidence: Mapped[bool] = mapped_column(Boolean, default=True)
    grounded: Mapped[bool] = mapped_column(Boolean, default=False)
    invalid_references: Mapped[list] = mapped_column(JSON, default=list)
    source: Mapped[str] = mapped_column(String(16))
    position: Mapped[int] = mapped_column(Integer, default=0)


class EvaluationSuite(Base):
    __tablename__ = "evaluation_suites"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    status: Mapped[str] = mapped_column(String(20))
    reasoning_mode: Mapped[str] = mapped_column(String(20))
    agent_version: Mapped[str] = mapped_column(String(40))
    scenario_ids: Mapped[list] = mapped_column(JSON, default=list)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    report_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    suite_id: Mapped[str] = mapped_column(String(40), index=True)
    scenario_id: Mapped[str] = mapped_column(String(80))
    category: Mapped[str] = mapped_column(String(40))
    agent_version: Mapped[str] = mapped_column(String(40))
    reasoning_mode: Mapped[str] = mapped_column(String(20))
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    investigation_ids: Mapped[list] = mapped_column(JSON, default=list)
    expected_hypothesis: Mapped[str] = mapped_column(String(60))
    predicted_hypothesis: Mapped[str | None] = mapped_column(String(60), nullable=True)
    diagnosis_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    evidence_precision: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence_recall: Mapped[float | None] = mapped_column(Float, nullable=True)
    grounded_claim_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    unsupported_claim_count: Mapped[int] = mapped_column(Integer, default=0)
    claim_count: Mapped[int] = mapped_column(Integer, default=0)
    expected_action: Mapped[str] = mapped_column(String(60))
    action_taken: Mapped[str | None] = mapped_column(String(60), nullable=True)
    action_success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    verification_success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    duplicate_action_count: Mapped[int] = mapped_column(Integer, default=0)
    mutation_attempts: Mapped[int] = mapped_column(Integer, default=0)
    tool_calls: Mapped[int] = mapped_column(Integer, default=0)
    tool_failures: Mapped[int] = mapped_column(Integer, default=0)
    recovery_expected: Mapped[bool] = mapped_column(Boolean, default=False)
    recovery_success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    approval_respected: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    correctness: Mapped[bool] = mapped_column(Boolean, default=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    failure_reasons: Mapped[list] = mapped_column(JSON, default=list)
    details: Mapped[dict] = mapped_column(JSON, default=dict)


ANONYMOUS_USER_ID = "anonymous"


class User(Base):
    """A real signed-in identity (Firebase UID). Rows are created lazily on first verified
    request — there is no separate signup endpoint, Firebase owns the credential itself."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    picture_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    persona: Mapped[str | None] = mapped_column(String(40), nullable=True)
    persona_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    goal_template: Mapped[str | None] = mapped_column(String(120), nullable=True)
    answers: Mapped[dict] = mapped_column(JSON, default=dict)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)


class ConnectorCredential(Base):
    """Provider OAuth credential, scoped per user. `user_id` is ANONYMOUS_USER_ID for the
    single shared server-side token/OAuth app configured via .env in un-authenticated demo use."""

    __tablename__ = "connector_credentials"

    user_id: Mapped[str] = mapped_column(String(128), primary_key=True, default=ANONYMOUS_USER_ID)
    app: Mapped[str] = mapped_column(String(20), primary_key=True)
    account_label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    encrypted_access_token: Mapped[str] = mapped_column(Text)
    encrypted_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    scopes: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)


class OAuthState(Base):
    __tablename__ = "oauth_states"

    state: Mapped[str] = mapped_column(String(80), primary_key=True)
    app: Mapped[str] = mapped_column(String(20))
    user_id: Mapped[str] = mapped_column(String(128), default=ANONYMOUS_USER_ID)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
