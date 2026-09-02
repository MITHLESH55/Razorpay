/**
 * RiskOrbit — Case Lifecycle & Investigation API Module
 */
import { apiRequest } from './client';
import { CaseDetailResponse, RiskCaseRecord } from '../types';

export interface ApproveActionPayload {
  expected_version?: number;
  notes?: string;
  idempotency_key?: string;
}

export interface EditActionPayload {
  new_action: string;
  reason: string;
  expected_version?: number;
  idempotency_key?: string;
}

export interface RejectActionPayload {
  reason: string;
  expected_version?: number;
  idempotency_key?: string;
}

export const casesApi = {
  /**
   * Retrieve full case details including graph topology, evidence bundle, and decision trace
   */
  async getCase(caseId: string): Promise<CaseDetailResponse> {
    return apiRequest<CaseDetailResponse>(`/api/v2/ops/cases/${encodeURIComponent(caseId)}`, {
      method: 'GET',
    });
  },

  /**
   * Retrieve single case record
   */
  async getCaseRecord(caseId: string): Promise<RiskCaseRecord> {
    const detail = await this.getCase(caseId);
    return detail.case;
  },

  /**
   * Approve proposed case intervention (enforces two-person review and optimistic locking)
   */
  async approveCase(caseId: string, payload: ApproveActionPayload = {}): Promise<RiskCaseRecord> {
    return apiRequest<RiskCaseRecord>(`/api/v2/ops/cases/${encodeURIComponent(caseId)}/approve`, {
      method: 'POST',
      body: JSON.stringify({
        idempotency_key: payload.idempotency_key || `idemp_appr_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
        notes: payload.notes,
        expected_version: payload.expected_version,
      }),
    });
  },

  /**
   * Override/edit recommended action (Senior Analyst / Admin only)
   */
  async editCase(caseId: string, payload: EditActionPayload): Promise<RiskCaseRecord> {
    return apiRequest<RiskCaseRecord>(`/api/v2/ops/cases/${encodeURIComponent(caseId)}/edit`, {
      method: 'POST',
      body: JSON.stringify({
        new_action: payload.new_action,
        reason: payload.reason,
        idempotency_key: payload.idempotency_key || `idemp_edit_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
        expected_version: payload.expected_version,
      }),
    });
  },

  /**
   * Reject proposed action, falling back to ALLOW with audit logging
   */
  async rejectCase(caseId: string, payload: RejectActionPayload): Promise<RiskCaseRecord> {
    return apiRequest<RiskCaseRecord>(`/api/v2/ops/cases/${encodeURIComponent(caseId)}/reject`, {
      method: 'POST',
      body: JSON.stringify({
        reason: payload.reason,
        idempotency_key: payload.idempotency_key || `idemp_rej_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
        expected_version: payload.expected_version,
      }),
    });
  },
};
