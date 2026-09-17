from enum import StrEnum


class InvestigationStatus(StrEnum):
    CREATED = "CREATED"
    PLANNING = "PLANNING"
    INVESTIGATING = "INVESTIGATING"
    SYNTHESIZING = "SYNTHESIZING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"


TERMINAL_STATUSES = frozenset(
    {
        InvestigationStatus.COMPLETED,
        InvestigationStatus.PARTIAL,
        InvestigationStatus.FAILED,
        InvestigationStatus.CANCELLED,
        InvestigationStatus.TIMED_OUT,
    }
)


class ExecutionMode(StrEnum):
    INTERACTIVE = "interactive"
    DEMO = "demo"
    EVALUATION = "evaluation"


class ApprovalMode(StrEnum):
    REQUIRED = "required"
    AUTO_LOW_RISK = "auto_low_risk"


class ReasoningMode(StrEnum):
    LLM = "llm"
    HEURISTIC = "heuristic"


class ConnectorMode(StrEnum):
    REAL = "REAL"
    DEMO = "DEMO"
    DISABLED = "DISABLED"


class App(StrEnum):
    SHEETS = "sheets"
    GITHUB = "github"
    SLACK = "slack"


class HypothesisStatus(StrEnum):
    CANDIDATE = "candidate"
    SUPPORTED = "supported"
    REJECTED = "rejected"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class Relation(StrEnum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    NEUTRAL = "neutral"


class Strength(StrEnum):
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


class Outcome(StrEnum):
    DIAGNOSIS = "diagnosis"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    NO_ANOMALY = "no_anomaly"


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ApprovalStatus(StrEnum):
    NOT_REQUESTED = "NOT_REQUESTED"
    NOT_REQUIRED = "NOT_REQUIRED"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ExecutionStatus(StrEnum):
    PROPOSED = "PROPOSED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    BLOCKED = "BLOCKED"
    EXECUTING = "EXECUTING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    REJECTED = "REJECTED"


class VerificationStatus(StrEnum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ClaimType(StrEnum):
    FACT = "FACT"
    INFERENCE = "INFERENCE"
    HYPOTHESIS = "HYPOTHESIS"
    RECOMMENDATION = "RECOMMENDATION"
    UNCERTAINTY = "UNCERTAINTY"


class Actor(StrEnum):
    AGENT = "agent"
    SYSTEM = "system"
    TOOL = "tool"
    USER = "user"


class EventType(StrEnum):
    INVESTIGATION_CREATED = "INVESTIGATION_CREATED"
    STATUS_CHANGED = "STATUS_CHANGED"
    PLAN = "PLAN"
    TOOL_CALL_STARTED = "TOOL_CALL_STARTED"
    TOOL_CALL_SUCCEEDED = "TOOL_CALL_SUCCEEDED"
    TOOL_CALL_FAILED = "TOOL_CALL_FAILED"
    TOOL_RETRY = "TOOL_RETRY"
    EVIDENCE = "EVIDENCE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    ANOMALY = "ANOMALY"
    HYPOTHESES_GENERATED = "HYPOTHESES_GENERATED"
    HYPOTHESIS_UPDATED = "HYPOTHESIS_UPDATED"
    SUFFICIENCY_CHECK = "SUFFICIENCY_CHECK"
    DEGRADED = "DEGRADED"
    SYNTHESIS = "SYNTHESIS"
    POLICY = "POLICY"
    ACTION_PROPOSED = "ACTION_PROPOSED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    ACTION_APPROVED = "ACTION_APPROVED"
    ACTION_REJECTED = "ACTION_REJECTED"
    ACTION_BLOCKED = "ACTION_BLOCKED"
    ACTION_EXECUTING = "ACTION_EXECUTING"
    ACTION_EXECUTED = "ACTION_EXECUTED"
    ACTION_AMBIGUOUS = "ACTION_AMBIGUOUS"
    ACTION_FAILED = "ACTION_FAILED"
    IDEMPOTENT_REPLAY = "IDEMPOTENT_REPLAY"
    VERIFICATION = "VERIFICATION"
    LLM_FALLBACK = "LLM_FALLBACK"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
