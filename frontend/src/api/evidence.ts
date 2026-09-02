/**
 * RiskOrbit — Grounded Evidence API Module
 */
import { apiRequest } from './client';
import { EvidenceItem } from '../types';

export interface CaseEvidenceResponse {
  case_id: string;
  case_summary?: string;
  why_flagged?: string;
  evidence_records: EvidenceItem[];
  timeline?: Array<{
    timestamp: string;
    event_type: string;
    entity_id: string;
    description: string;
  }>;
  uncertainties?: string[];
  missing_evidence?: string[];
}

export const evidenceApi = {
  /**
   * Retrieve grounded evidence bundle and timeline for a case
   */
  async getCaseEvidence(caseId: string): Promise<CaseEvidenceResponse> {
    return apiRequest<CaseEvidenceResponse>(`/risk/cases/${encodeURIComponent(caseId)}/evidence`, {
      method: 'GET',
    });
  },
};
