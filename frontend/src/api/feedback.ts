/**
 * RiskOrbit — Analyst Domain Feedback & Adjudication API Module
 */
import { apiRequest } from './client';
import { FeedbackRecord } from '../types';

export interface SubmitFeedbackPayload {
  case_id: string;
  transaction_id: string;
  adjudication: 'TRUE_POSITIVE' | 'FALSE_POSITIVE' | 'NEEDS_REVIEW' | 'EVIDENCE_INSUFFICIENT';
  notes?: string;
  evidence_conflict_notes?: string;
  suggested_policy_tuning?: string;
}

export const feedbackApi = {
  /**
   * Record analyst domain adjudication (enforces Model Freeze Invariant — weights remain frozen)
   */
  async submitFeedback(payload: SubmitFeedbackPayload): Promise<FeedbackRecord> {
    return apiRequest<FeedbackRecord>('/api/v2/ops/feedback', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  /**
   * List historical feedback records
   */
  async listFeedback(limit = 100): Promise<FeedbackRecord[]> {
    return apiRequest<FeedbackRecord[]>('/api/v2/ops/feedback', {
      method: 'GET',
      params: { limit },
    });
  },
};
