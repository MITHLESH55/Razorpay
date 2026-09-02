/**
 * RiskOrbit — Approvals API Module
 */
import { casesApi, ApproveActionPayload, EditActionPayload, RejectActionPayload } from './cases';
import { RiskCaseRecord } from '../types';

export const approvalsApi = {
  /**
   * Approve proposed case action (enforces RBAC, optimistic locking, and idempotency)
   */
  async approve(caseId: string, payload: ApproveActionPayload = {}): Promise<RiskCaseRecord> {
    return casesApi.approveCase(caseId, payload);
  },

  /**
   * Edit / override proposed case action (SENIOR_ANALYST / ADMIN only)
   */
  async edit(caseId: string, payload: EditActionPayload): Promise<RiskCaseRecord> {
    return casesApi.editCase(caseId, payload);
  },

  /**
   * Reject / dismiss proposed case action
   */
  async reject(caseId: string, payload: RejectActionPayload): Promise<RiskCaseRecord> {
    return casesApi.rejectCase(caseId, payload);
  },
};
