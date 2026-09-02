/**
 * RiskOrbit — Append-Only Audit Trail API Module
 */
import { apiRequest } from './client';
import { AuditRecord } from '../types';

export interface AuditFilterParams {
  case_id?: string;
  actor?: string;
  event_type?: string;
  limit?: number;
}

export const auditApi = {
  /**
   * Retrieve chronological append-only audit trail entries
   */
  async getAuditTrail(params: AuditFilterParams = {}): Promise<AuditRecord[]> {
    return apiRequest<AuditRecord[]>('/api/v2/ops/audit', {
      method: 'GET',
      params: {
        case_id: params.case_id,
        actor: params.actor,
        event_type: params.event_type,
        limit: params.limit || 100,
      },
    });
  },

  /**
   * Retrieve audit history for a specific case
   */
  async getCaseAudit(caseId: string): Promise<AuditRecord[]> {
    return apiRequest<AuditRecord[]>(`/api/v2/ops/audit`, {
      method: 'GET',
      params: { case_id: caseId },
    });
  },
};
