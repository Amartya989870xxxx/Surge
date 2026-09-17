export type AppType = 'sheets' | 'github' | 'slack';
export type ConnectorMode = 'DEMO' | 'REAL';
export type ReasoningMode = 'auto' | 'llm' | 'heuristic';
export type ApprovalMode = 'required' | 'autonomous';

export type InvestigationStatus =
  | 'CREATED'
  | 'PLANNING'
  | 'INVESTIGATING'
  | 'SYNTHESIZING'
  | 'AWAITING_APPROVAL'
  | 'EXECUTING'
  | 'VERIFYING'
  | 'COMPLETED'
  | 'PARTIAL'
  | 'FAILED'
  | 'CANCELLED'
  | 'TIMED_OUT';

export type EventCategory =
  | 'SYSTEM'
  | 'TOOL'
  | 'EVIDENCE'
  | 'HYPOTHESIS'
  | 'POLICY'
  | 'ACTION'
  | 'VERIFICATION'
  | 'ERROR'
  | 'RECOVERY'
  | 'PLAN'
  | 'ANOMALY'
  | 'SYNTHESIS'
  | 'STATUS_CHANGED'
  | 'SUFFICIENCY_CHECK';

export interface EventOut {
  id: number;
  investigation_id: string;
  sequence: number;
  timestamp: string;
  event_type: string;
  category: string;
  actor: string;
  status: string | null;
  title: string;
  summary: string | null;
  tool_name: string | null;
  external_app: string | null;
  duration_ms: number | null;
  input_summary: string | null;
  output_summary: string | null;
  error_code: string | null;
  evidence_ids: string[];
  hypothesis_ids: string[];
  action_id: string | null;
  data: Record<string, any>;
}

export interface EvidenceRelationOut {
  hypothesis_id: string;
  hypothesis_kind: string;
  hypothesis_label: string;
  relation: 'supports' | 'contradicts' | 'neutral';
  strength: 'strong' | 'moderate' | 'weak';
  rationale: string;
  assessed_by: string;
}

export interface EvidenceOut {
  id: string;
  investigation_id: string;
  source_app: string;
  source_type: string;
  source_record_id: string;
  epistemic_type: 'observation' | 'computed_observation' | 'absence_check';
  title: string;
  snippet: string;
  normalized_content: string;
  observed_at: string | null;
  retrieved_at: string;
  url: string | null;
  source_metadata: Record<string, any>;
  derived_from: string[];
  relevance_score: number;
  evidence_strength: string;
  connector_mode: string;
  probe_id: string | null;
  supports_hypothesis_ids: string[];
  contradicts_hypothesis_ids: string[];
  relations: EvidenceRelationOut[];
}

export interface HypothesisEvidenceOut {
  evidence_id: string;
  source_app: string;
  title: string;
  relation: 'supports' | 'contradicts' | 'neutral';
  strength: string;
  rationale: string;
  assessed_by: string;
}

export interface HypothesisOut {
  id: string;
  kind: string;
  label: string;
  statement: string;
  confidence: number;
  prior: number;
  status: string;
  rank: number;
  rationale: string;
  missing_information: string[];
  supporting_evidence_ids: string[];
  contradicting_evidence_ids: string[];
  independent_sources: string[];
  evidence: HypothesisEvidenceOut[];
}

export interface VerificationCheck {
  field: string;
  passed: boolean;
  expected?: any;
  observed?: any;
  message?: string;
  [key: string]: any;
}

export interface VerificationOut {
  method: string;
  result: 'passed' | 'failed' | 'inconclusive';
  checks: VerificationCheck[];
  expected_state: Record<string, any>;
  observed_state: Record<string, any>;
  confidence: number;
  attempted_at: string;
  error_code: string | null;
}

export interface LifecycleStageOut {
  stage: string;
  done: boolean;
  state: string | null;
}

export interface ActionOut {
  id: string;
  investigation_id: string;
  action_type: string;
  external_app: string;
  target: string;
  title: string;
  rationale: string;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH';
  approval_required: boolean;
  approval_status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'NOT_REQUIRED';
  execution_status: 'PENDING' | 'EXECUTING' | 'SUCCEEDED' | 'FAILED' | 'SKIPPED';
  verification_status: 'PENDING' | 'VERIFYING' | 'VERIFIED' | 'FAILED' | 'INCONCLUSIVE';
  idempotency_key: string;
  external_result_id: string | null;
  external_url: string | null;
  hypothesis_id: string | null;
  evidence_ids: string[];
  attempts: number;
  error: Record<string, any> | null;
  decided_by: string | null;
  created_at: string;
  decided_at: string | null;
  completed_at: string | null;
  preview: Record<string, any>;
  verification: VerificationOut | null;
  lifecycle: LifecycleStageOut[];
  requires_strong_confirmation: boolean;
}

export interface ClaimOut {
  id: string;
  claim_type: string;
  text: string;
  evidence_ids: string[];
  event_sequences: number[];
  hypothesis_id: string | null;
  requires_evidence: boolean;
  grounded: boolean;
  invalid_references: string[];
  source: string;
  position: number;
}

export interface HypothesisBrief {
  id: string;
  kind: string;
  label: string;
  confidence: number;
}

export interface InvestigationSummaryOut {
  id: string;
  title: string;
  request: string;
  status: InvestigationStatus;
  outcome: string | null;
  strongest_hypothesis: HypothesisBrief | null;
  confidence: number | null;
  action_count: number;
  verified: boolean;
  pending_approval: boolean;
  degraded: boolean;
  execution_mode: string;
  connector_mode: string;
  reasoning_mode: string;
  scenario_id: string | null;
  duration_ms: number | null;
  created_at: string;
  completed_at: string | null;
}

export interface InvestigationDetailOut extends InvestigationSummaryOut {
  approval_mode: string;
  severity: string | null;
  time_window_start: string | null;
  time_window_end: string | null;
  started_at: string | null;
  updated_at: string;
  intent: Record<string, any> | null;
  final_summary: string | null;
  confidence_breakdown: Record<string, any> | null;
  root_cause_hypothesis_id: string | null;
  missing_sources: string[];
  tool_call_count: number;
  error: Record<string, any> | null;
  fault_injection: Array<Record<string, any>>;
  connectors: Array<{
    app: string;
    mode?: string;
    status?: string;
    display_name?: string;
    account_label?: string;
  }>;
  synthesis: Record<string, any> | null;
  pending_action_ids: string[];
  counts: {
    events: number;
    evidence: number;
    hypotheses: number;
    claims: number;
  };
  links: Record<string, string>;
}

export interface InvestigationListOut {
  items: InvestigationSummaryOut[];
  total: number;
}

export interface CreateInvestigationRequest {
  request: string;
  time_range?: {
    start: string;
    end: string;
  };
  mode?: 'interactive';
  approval_mode?: ApprovalMode;
  connector_mode?: ConnectorMode;
  disabled_apps?: AppType[];
  scenario_id?: string;
  inject_failures?: string[];
  reasoning?: ReasoningMode;
  session_id?: string;
}

export interface InvestigationCreated {
  id: string;
  status: string;
  stream_url: string;
  connector_mode: string;
  reasoning_mode: string;
  scenario_id: string | null;
  injected_faults: Array<Record<string, any>>;
}

export interface ApproveRequest {
  action_id: string;
  approved: boolean;
  comment?: string;
  decided_by?: string;
}

export interface ConnectorInfo {
  app: string;
  display_name: string;
  mode: 'DEMO' | 'REAL';
  status: string;
  account_label: string;
  capabilities: string[];
  detail: string;
  simulated_latency_ms: number;
  oauth_configured: boolean;
  connect_endpoint: string;
}

export interface ConnectorsOut {
  default_mode: string;
  connectors: ConnectorInfo[];
  fault_presets: Record<string, string>;
}

export interface ScenarioRun {
  id: string;
  scenario_id: string;
  category: string;
  passed: boolean;
  expected_hypothesis: string;
  predicted_hypothesis: string;
  diagnosis_correct: boolean;
  evidence_precision: number;
  evidence_recall: number;
  grounded_claim_rate: number;
  unsupported_claim_count: number;
  expected_action: string;
  action_taken: string;
  action_success: boolean | null;
  verification_success: boolean | null;
  duplicate_action_count: number;
  tool_calls: number;
  tool_failures: number;
  recovery_expected: boolean;
  recovery_success: boolean | null;
  approval_respected: boolean | null;
  confidence: number | null;
  latency_ms: number;
  failure_reasons: string[];
  investigation_ids: string[];
  timestamp: string;
}

export interface EvaluationSuiteOut {
  id: string;
  status: string;
  reasoning_mode: string;
  agent_version: string;
  scenario_count: number;
  started_at: string;
  completed_at: string | null;
  headline: {
    scenarios_total?: number;
    scenarios_passed?: number;
    diagnosis_accuracy?: number;
    action_verification_rate?: number;
    duplicate_actions?: number;
    recovery_rate?: number;
    [key: string]: any;
  } | null;
  report: Record<string, any> | null;
  report_text: string | null;
  error: Record<string, any> | null;
  runs: ScenarioRun[];
}

export interface EvaluationSuiteSummaryOut {
  id: string;
  status: string;
  reasoning_mode: string;
  agent_version: string;
  scenario_count: number;
  started_at: string;
  completed_at: string | null;
  headline: Record<string, any> | null;
}

export interface SystemInfo {
  name: string;
  version: string;
  reasoning: {
    default_mode: string;
    llm_available: boolean;
    active_model: string | null;
    router: any;
  };
  connectors: {
    default_mode: string;
    demo_scenario: string;
    demo_simulated_latency_ms: number;
  };
  policy: {
    default_approval: string;
    action_risk: Record<string, string>;
    diagnosis: {
      supported_threshold: number;
      stop_threshold: number;
      min_independent_sources: number;
      min_margin_over_runner_up: number;
    };
    max_tool_calls: number;
  };
  hypothesis_catalog: Array<{
    kind: string;
    label: string;
    statement: string;
  }>;
  probes: Array<{
    id: string;
    app: string;
    title: string;
    purpose: string;
    discriminates: string[];
  }>;
  fault_presets: Record<string, string>;
  enums: Record<string, string[]>;
}
