/**
 * RiskOrbit — Decisions, Verification & Action Preview API Module
 */
import { apiRequest } from './client';
import { DecisionTrace } from '../types';

export interface DecisionResultResponse {
  case_id: string;
  transaction_risk: number;
  membership_confidence: number;
  evidence_strength: number;
  decision_score: number;
  risk_tier: string;
  recommended_action: string;
  why_flagged: string;
  why_not_stronger?: string;
  why_not_weaker?: string;
  policy_version: string;
  decision_trace?: DecisionTrace;
}

export interface VerificationResultResponse {
  case_id: string;
  evidence_sufficient: boolean;
  provenance_valid: boolean;
  point_in_time_valid: boolean;
  contradictions_found: boolean;
  policy_constraints_satisfied: boolean;
  safety_invariants_passed: boolean;
  verification_status: 'VERIFIED' | 'WARNING' | 'FAILED';
  verification_notes?: string;
}

export interface ActionPreviewResponse {
  case_id: string;
  recommended_action: string;
  target_entity: string;
  scope: string;
  rationale: string;
  evidence_summary: string;
  policy_version: string;
  projected_friction_cost_inr: number;
  estimated_review_cost_inr: number;
  blast_radius: string;
  requires_approval: boolean;
  expires_at?: string;
}

export const decisionsApi = {
  /**
   * Retrieve grounded decision score, tiering, and counterfactual rationale
   */
  async getCaseDecision(caseId: string): Promise<DecisionResultResponse> {
    return apiRequest<DecisionResultResponse>(`/risk/cases/${encodeURIComponent(caseId)}/decision`, {
      method: 'GET',
    });
  },

  /**
   * Retrieve deterministic non-LLM evidence invariant verification result
   */
  async getCaseVerification(caseId: string): Promise<VerificationResultResponse> {
    return apiRequest<VerificationResultResponse>(`/risk/cases/${encodeURIComponent(caseId)}/verification`, {
      method: 'GET',
    });
  },

  /**
   * Preview proposed action impact, blast radius, and friction cost before execution
   */
  async getActionPreview(caseId: string): Promise<ActionPreviewResponse> {
    return apiRequest<ActionPreviewResponse>(`/risk/cases/${encodeURIComponent(caseId)}/action-preview`, {
      method: 'GET',
    });
  },
};
