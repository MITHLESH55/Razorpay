export type UserRole = 'VIEWER' | 'ANALYST' | 'SENIOR_ANALYST' | 'ADMIN';

export interface UserContext {
  user_id: string;
  role: UserRole;
  name: string;
  email?: string;
  title?: string;
  capabilities?: string[];
}

export interface DemoUserRecord {
  user_id: string;
  role: UserRole;
  name: string;
  email: string;
  title: string;
  department: string;
  password_hint: string;
  capabilities: string[];
}

export type AuthStatus = 'unauthenticated' | 'authenticating' | 'authenticated' | 'session_expired';

export interface AuthSession {
  token: string;
  user: UserContext;
  session_id: string;
  expires_at: number;
}

export interface GoogleOAuthConfig {
  configured: boolean;
  client_id?: string;
  message: string;
}

export type CaseStatus =
  | 'RECOMMENDED'
  | 'PENDING_APPROVAL'
  | 'APPROVED'
  | 'EDITED'
  | 'REJECTED'
  | 'EXECUTED_SIMULATION'
  | 'VERIFIED';

export type CasePriority = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export interface RiskCaseRecord {
  case_id: string;
  transaction_id: string;
  customer_id: string;
  amount_inr: number;
  timestamp: string;
  phase1_risk: number;
  membership_confidence: number;
  evidence_strength: number;
  decision_score: number;
  tier: string;
  recommended_action: string;
  final_action: string;
  requires_human_approval: boolean;
  escalation_reason?: string;
  action_reason: string;
  expected_friction_cost_inr: number;
  ring_id?: string;
  pattern_type?: string;
  is_hard_negative: boolean;
  hard_negative_type?: string;
  status: CaseStatus;
  priority: CasePriority;
  version: number;
  idempotency_keys: string[];
  assigned_reviewer?: string;
  reviewed_by?: string;
  reviewed_at?: string;
  reviewer_notes?: string;
  original_action?: string;
  member_count: number;
  shared_devices: string[];
  shared_ips: string[];
  created_at: string;
  updated_at: string;
}

export interface GraphNode {
  id: string;
  type: 'customer' | 'device' | 'ip' | 'merchant';
  label: string;
  role: string;
  tier: string;
  risk_score: number;
  x?: number;
  y?: number;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  weight: number;
}

export interface EvidenceItem {
  evidence_id: string;
  category: string;
  title: string;
  strength: number;
  verified: boolean;
  hash_sha256: string;
  description: string;
  features: Record<string, any>;
}

export interface DecisionTrace {
  p1_raw_score: number;
  sigma_membership_confidence: number;
  rho_evidence_strength: number;
  tier_multiplier: number;
  final_decision_score: number;
  policy_rule_matched: string;
  friction_cost_estimate_inr: number;
  bounded_intervention: string;
}

export interface CaseDetailResponse {
  case: RiskCaseRecord;
  graph: {
    nodes: GraphNode[];
    edges: GraphEdge[];
  };
  evidence_records: EvidenceItem[];
  decision_trace: DecisionTrace;
  narrative: string;
  pattern_name: string;
}

export interface SystemControlsState {
  health_status: 'HEALTHY' | 'DEGRADED' | 'SAFE_MODE' | 'UNAVAILABLE';
  shadow_mode_enabled: boolean;
  kill_switch_active: boolean;
  graph_engine_available: boolean;
  model_version: string;
  policy_version: string;
  active_environment: string;
  last_state_change: string;
  degradation_reason?: string;
}

export interface OverviewKPIs {
  active_cases_total: number;
  critical_priority_count: number;
  pending_human_approvals: number;
  approved_interventions: number;
  hard_negatives_evaluated: number;
  pending_exposure_inr: number;
  system_health: string;
  degradation_reason?: string;
  shadow_mode_enabled: boolean;
  kill_switch_active: boolean;
  graph_engine_available: boolean;
  latency_p50_ms: number;
  latency_p95_ms: number;
  model_version: string;
  policy_version: string;
  held_out_metrics: {
    ring_recall: string;
    intervention_fpr: string;
    hard_block_fpr: string;
    direct_txn_recall: string;
    held_out_transactions: number;
  };
}

export type OperationalOverviewSummary = OverviewKPIs;

export interface AuditRecord {
  event_id: string;
  case_id: string;
  actor_id: string;
  actor_role: string;
  event_type: string;
  timestamp: string;
  model_version: string;
  policy_version: string;
  evidence_version: string;
  previous_state?: string;
  new_state?: string;
  notes?: string;
  reason?: string;
  details: Record<string, any>;
}

export interface FeedbackRecord {
  feedback_id: string;
  case_id: string;
  transaction_id: string;
  adjudication: 'TRUE_POSITIVE' | 'FALSE_POSITIVE' | 'NEEDS_REVIEW' | 'EVIDENCE_INSUFFICIENT';
  actor_id: string;
  actor_role: string;
  notes?: string;
  evidence_conflict_notes?: string;
  suggested_policy_tuning?: string;
  timestamp: string;
  model_version: string;
  policy_version: string;
  status_notice: string;
}

export interface FeatureDriftReport {
  feature_name: string;
  psi_score: number;
  status: 'NO_DRIFT' | 'MODERATE_DRIFT' | 'SIGNIFICANT_DRIFT';
  baseline_mean: number;
  current_mean: number;
  baseline_std: number;
  current_std: number;
  drift_direction: 'STABLE' | 'INCREASED' | 'DECREASED';
  bins_summary: Array<{
    bin_range: string;
    baseline_pct: number;
    current_pct: number;
    bin_psi: number;
  }>;
}

export interface SystemDriftSummary {
  overall_status: 'NO_DRIFT' | 'MODERATE_DRIFT' | 'SIGNIFICANT_DRIFT';
  max_psi: number;
  evaluated_features_count: number;
  drifting_features_count: number;
  last_evaluated_at: string;
  feature_reports: FeatureDriftReport[];
  recommendation: string;
}

export interface RingMetrics {
  total_rings: number;
  detection_recall: number;
  intervention_recall: number;
  hard_block_recall: number;
  strong_ring_recall: number;
  complete_ring_detection_rate: number;
}

export interface PatternMetrics {
  pattern_A_rings?: number;
  pattern_A_detected?: number;
  pattern_A_intervened?: number;
  pattern_A_hard_blocked?: number;
  pattern_A_recall?: number;
  pattern_A_intervention_recall?: number;
  pattern_B_rings?: number;
  pattern_B_detected?: number;
  pattern_B_intervened?: number;
  pattern_B_hard_blocked?: number;
  pattern_B_recall?: number;
  pattern_B_intervention_recall?: number;
  pattern_C_rings?: number;
  pattern_C_detected?: number;
  pattern_C_intervened?: number;
  pattern_C_hard_blocked?: number;
  pattern_C_recall?: number;
  pattern_C_intervention_recall?: number;
  [key: string]: any;
}

export interface OperationalMetrics {
  intervention_rate_pct: number;
  hard_block_rate_pct: number;
  hard_block_fpr_pct: number;
  hard_block_count: number;
  legitimate_hard_blocks: number;
  abuse_hard_blocks: number;
  review_rate_pct: number;
  review_count: number;
  legitimate_transactions_affected: number;
  legitimate_customers_affected: number;
}

export interface EconomicsMetrics {
  gross_synthetic_abuse_volume_inr: number;
  modeled_prevented_loss_inr: number;
  uncaught_abuse_loss_inr: number;
  benign_friction_cost_inr: number;
  review_cost_inr: number;
  total_operational_cost_inr: number;
  net_modeled_utility_inr: number;
}

export interface HardNegativeCategory {
  txns: number;
  policy_b_blocks: number;
  policy_b_cost: number;
  policy_d_blocks: number;
  policy_d_cost: number;
  cost_reduction_pct: number;
}

export interface HardNegativeMetrics {
  categories: Record<string, HardNegativeCategory>;
  total_hard_negatives: number;
  total_hard_blocks: number;
  hard_block_fpr_pct: number;
}

export interface SafetyAuditMetrics {
  all_invariants_passed: boolean;
  invariants_passed_count: string;
  hard_negative_hard_blocks: number;
  unsafe_actions_count: number;
  human_gate_bypass_count: number;
  scope_isolation_violations: number;
}

export interface EvidenceAuditMetrics {
  grounding_rate: number;
  provenance_completeness: number;
  invalid_evidence_count: number;
}

export interface TestSuiteMetrics {
  tests_total: number;
  tests_passed: number;
  tests_failed: number;
  pytest_verified: boolean;
  test_runner: string;
}

export interface HistoricalFailure {
  phase: string;
  failure_title: string;
  symptom: string;
  root_cause: string;
  fix: string;
  measured_result: string;
}

export interface ComparisonPhaseMetrics {
  name: string;
  confusion_matrix: {
    TP: number;
    TN: number;
    FP: number;
    FN: number;
  };
  precision: number;
  recall: number;
  f1: number;
  pr_auc: number;
  fpr_pct: number;
  intervention_fpr_pct: number;
  hard_block_rate_pct: number;
  hard_block_fpr_pct: number;
  fp_cost_inr: number;
  ring_metrics: RingMetrics;
  pattern_metrics: PatternMetrics;
  operational: OperationalMetrics;
  economics: EconomicsMetrics;
  action_distribution: Record<string, number>;
}

export interface EvaluationMetricsResponse {
  metadata: {
    dataset: string;
    dataset_checksum: string;
    dataset_rows: number;
    abuse_rows: number;
    benign_rows: number;
    model_version: string;
    policy_version: string;
    evaluator_version: string;
    evaluation_timestamp: string;
    environment: string;
  };
  test_suite: TestSuiteMetrics;
  ring_intervention_recall: number;
  hard_block_fpr: number;
  intervention_fpr: number;
  pattern_A_recall: number;
  pattern_B_recall: number;
  pattern_C_recall: number;
  transaction_metrics: {
    confusion_matrix: {
      TP: number;
      TN: number;
      FP: number;
      FN: number;
    };
    precision: number;
    recall: number;
    f1: number;
    pr_auc: number;
    fpr_pct: number;
    intervention_fpr_pct: number;
    hard_block_rate_pct: number;
    hard_block_fpr_pct: number;
    fp_cost_inr: number;
  };
  ring_metrics: RingMetrics;
  pattern_metrics: PatternMetrics;
  hard_negative_metrics: HardNegativeMetrics;
  operational: OperationalMetrics;
  economics: EconomicsMetrics;
  action_distribution: Record<string, number>;
  safety_audit: SafetyAuditMetrics;
  evidence_audit: EvidenceAuditMetrics;
  cryptographic_manifest?: any;
  comparison_phases: {
    phase1_point_model: ComparisonPhaseMetrics;
    phase22_blanket_expansion: ComparisonPhaseMetrics;
    phase31_binary_gating: ComparisonPhaseMetrics;
    phase32_final_tiered: ComparisonPhaseMetrics;
  };
  historical_failures: HistoricalFailure[];
}

export interface ManifestData {
  manifest_version?: string;
  timestamp?: string;
  status?: string;
  test_suite?: TestSuiteMetrics;
  environment?: string;
  sign_off?: {
    lead: string;
    role: string;
    date: string;
    status: string;
  };
  cryptographic_hashes?: Record<string, string>;
  final_heldout_metrics_summary?: Record<string, any>;
  [key: string]: any;
}
