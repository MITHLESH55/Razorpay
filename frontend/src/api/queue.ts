/**
 * RiskOrbit — Risk Queue API Module
 */
import { apiRequest } from './client';
import { RiskCaseRecord } from '../types';

export interface QueueFilterParams {
  status?: string;
  priority?: string;
  pattern?: string;
  action?: string;
  min_score?: number;
  max_score?: number;
  amount_min?: number;
  amount_max?: number;
  search?: string;
  limit?: number;
  page?: number;
  page_size?: number;
}

export interface RiskQueueResponse {
  items: RiskCaseRecord[];
  total_count: number;
  page: number;
  page_size: number;
}

export const queueApi = {
  /**
   * Retrieve ranked risk cases matching all search and filter conditions
   */
  async getQueue(params: QueueFilterParams = {}): Promise<RiskCaseRecord[]> {
    // Uses the operations queue endpoint which returns List[RiskCaseRecord]
    return apiRequest<RiskCaseRecord[]>('/api/v2/ops/queue', {
      method: 'GET',
      params: {
        status: params.status,
        priority: params.priority,
        pattern: params.pattern,
        action: params.action,
        min_score: params.min_score,
        max_score: params.max_score,
        search: params.search,
        limit: params.limit || 100,
      },
    });
  },

  /**
   * Paginated queue endpoint from control plane
   */
  async getPaginatedQueue(params: QueueFilterParams = {}): Promise<RiskQueueResponse> {
    return apiRequest<RiskQueueResponse>('/risk/queue', {
      method: 'GET',
      params: {
        status: params.status,
        severity: params.priority,
        pattern: params.pattern,
        action: params.action,
        confidence_min: params.min_score,
        confidence_max: params.max_score,
        amount_min: params.amount_min,
        amount_max: params.amount_max,
        search: params.search,
        page: params.page || 1,
        page_size: params.page_size || 50,
      },
    });
  },
};
