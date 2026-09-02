/**
 * RiskOrbit — Frontend/Backend REST & Contract Verification Script
 *
 * Verifies that all types, schemas, and state transition contracts
 * used in the frontend match the backend Pydantic v2 schemas and Blueprint specifications.
 */

import { apiService } from '../services/api';
import {
  RiskCaseRecord,
  EvaluationMetricsResponse,
  SystemControlsState,
  SystemDriftSummary,
  AuditRecord,
  CaseDetailResponse,
} from '../types';

function assert(condition: boolean, message: string) {
  if (!condition) {
    console.error(`❌ Verification Failure: ${message}`);
    process.exit(1);
  }
}

async function runVerification() {
  console.log('🧪 Starting RiskOrbit Frontend Contract Verification...\n');

  // 1. Verify Demo Cases
  console.log('1. Verifying Demo Cases Schema & Blueprint Parity...');
  const queueCases: RiskCaseRecord[] = await apiService.getQueue();
  assert(queueCases.length >= 4, 'Must contain at least 4 flagship demo cases');

  const patternIds = ['CASE-RING-A', 'CASE-RING-B', 'CASE-RING-C', 'CASE-HARDNEG'];
  patternIds.forEach((pid: string) => {
    const c = queueCases.find((item: RiskCaseRecord) => item.case_id.includes(pid) || item.pattern_type?.includes(pid));
    assert(!!c, `Missing flagship demo case for ${pid}`);
  });

  queueCases.forEach((c: RiskCaseRecord) => {
    assert(typeof c.case_id === 'string' && c.case_id.length > 0, `Case ID missing on ${JSON.stringify(c)}`);
    assert(typeof c.transaction_id === 'string', `Transaction ID missing on ${c.case_id}`);
    assert(typeof c.customer_id === 'string', `Customer ID missing on ${c.case_id}`);
    assert(typeof c.amount_inr === 'number' && c.amount_inr > 0, `Invalid amount on ${c.case_id}`);
    assert(typeof c.decision_score === 'number' && c.decision_score >= 0 && c.decision_score <= 1, `Invalid decision score on ${c.case_id}`);
    assert(typeof c.phase1_risk === 'number' && c.phase1_risk >= 0 && c.phase1_risk <= 1, `Invalid Phase 1 risk score on ${c.case_id}`);
    assert(typeof c.membership_confidence === 'number' && c.membership_confidence >= 0 && c.membership_confidence <= 1, `Invalid membership confidence on ${c.case_id}`);
    assert(typeof c.evidence_strength === 'number' && c.evidence_strength >= 0 && c.evidence_strength <= 1, `Invalid evidence strength on ${c.case_id}`);
    assert(['PRIMARY', 'SECONDARY', 'ISOLATED'].includes(c.tier), `Invalid tier ${c.tier} on ${c.case_id}`);
    assert(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].includes(c.priority), `Invalid priority ${c.priority} on ${c.case_id}`);
    assert(['HARD_BLOCK_ACCOUNT', 'FREEZE_RING', 'BLOCK_TRANSACTION', 'RESTRICT_ACCOUNT', 'FREEZE_REFUND_CAPABILITY', 'DELAY_SETTLEMENT', 'STEP_UP_2FA', 'ALLOW'].includes(c.recommended_action), `Invalid recommended action ${c.recommended_action} on ${c.case_id}`);
    assert(typeof c.version === 'number' && c.version >= 1, `Invalid version ${c.version} on ${c.case_id}`);
  });
  console.log('   ✅ All Demo Cases adhere to RiskCaseRecord contract.\n');

  // 2. Verify Evaluation Metrics (Single Source of Truth)
  console.log('2. Verifying Single Source of Truth Metrics...');
  const m: EvaluationMetricsResponse = await apiService.getEvaluationMetrics();
  assert(m.metadata.dataset_rows === 28591, `Dataset size must be 28,591, got ${m.metadata.dataset_rows}`);
  assert(m.metadata.abuse_rows === 290, `Abuse count must be 290, got ${m.metadata.abuse_rows}`);
  assert(m.metadata.benign_rows === 28301, `Benign count must be 28,301, got ${m.metadata.benign_rows}`);
  assert(m.ring_intervention_recall === 1.0, `Ring intervention recall must be 100%, got ${m.ring_intervention_recall}`);
  assert(m.hard_block_fpr === 0.0004, `Hard-block FPR must be 0.04%, got ${m.hard_block_fpr}`);
  assert(m.intervention_fpr === 0.0045, `Intervention FPR must be 0.45%, got ${m.intervention_fpr}`);
  assert(m.pattern_A_recall === 1.0, `Pattern A recall must be 1.0, got ${m.pattern_A_recall}`);
  assert(m.pattern_B_recall === 1.0, `Pattern B recall must be 1.0, got ${m.pattern_B_recall}`);
  assert(m.pattern_C_recall === 1.0, `Pattern C recall must be 1.0, got ${m.pattern_C_recall}`);
  assert(m.economics.gross_synthetic_abuse_volume_inr === 1317260.28, `Abuse volume mismatch: ${m.economics.gross_synthetic_abuse_volume_inr}`);
  console.log('   ✅ Held-out test evaluation matches canonical JSON reports.\n');

  // 3. Verify System Health and Controls
  console.log('3. Verifying System Health & Safe Degradation Matrix...');
  const health: SystemControlsState = await apiService.getControls();
  assert(['HEALTHY', 'DEGRADED', 'SAFE_MODE', 'UNAVAILABLE'].includes(health.health_status), `Invalid status ${health.health_status}`);
  assert(health.model_version === 'riskorbit-risk-v1', 'Model version mismatch');
  assert(health.policy_version === 'phase3_final_policy', 'Policy version mismatch');
  console.log('   ✅ System Health state verified.\n');

  // 4. Verify Distribution Drift Monitoring Data
  console.log('4. Verifying Feature Drift Monitoring Contract...');
  const drift: SystemDriftSummary = await apiService.getDriftReport();
  assert(['NO_DRIFT', 'MODERATE_DRIFT', 'SIGNIFICANT_DRIFT'].includes(drift.overall_status), `Invalid drift status: ${drift.overall_status}`);
  assert(typeof drift.max_psi === 'number' && drift.max_psi < 0.1, `Max PSI must be < 0.1 for stable, got ${drift.max_psi}`);
  assert(drift.feature_reports.length >= 2, 'Must monitor features for PSI drift');
  drift.feature_reports.forEach((f) => {
    assert(f.psi_score >= 0, `Invalid PSI score ${f.psi_score} for feature ${f.feature_name}`);
    assert(['NO_DRIFT', 'MODERATE_DRIFT', 'SIGNIFICANT_DRIFT'].includes(f.status), `Invalid drift status for ${f.feature_name}`);
  });
  console.log('   ✅ PSI Drift monitoring records verified.\n');

  // 5. Verify Case Detail Payload
  console.log('5. Verifying Flagship Case Detail...');
  const caseDetail: CaseDetailResponse = await apiService.getCaseDetail('CASE-RING-A-01');
  assert(caseDetail.case.case_id === 'CASE-RING-A-01', 'Case ID mismatch in detail');
  assert(caseDetail.graph.nodes.length >= 3, 'Graph should have nodes');
  assert(caseDetail.graph.edges.length >= 2, 'Graph should have edges');
  assert(caseDetail.evidence_records.length >= 2, 'Evidence items should be present');
  assert(caseDetail.decision_trace.final_decision_score > 0, 'Decision trace score should be positive');
  console.log('   ✅ Case Detail contract verified.\n');

  console.log('🎉 All Frontend/Backend Contract & Blueprint Invariants Verified Successfully!');
}

runVerification().catch((err) => {
  console.error('Unhandled verification error:', err);
  process.exit(1);
});
