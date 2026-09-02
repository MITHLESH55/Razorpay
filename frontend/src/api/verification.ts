/**
 * RiskOrbit — Verification API Module
 */
import { apiRequest } from './client';
import { VerificationResultResponse } from './decisions';

export const verificationApi = {
  /**
   * Retrieve deterministic non-LLM evidence invariant verification result
   */
  async getCaseVerification(caseId: string): Promise<VerificationResultResponse> {
    return apiRequest<VerificationResultResponse>(`/risk/cases/${encodeURIComponent(caseId)}/verification`, {
      method: 'GET',
    });
  },
};
