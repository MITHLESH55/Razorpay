/**
 * RiskOrbit — Operational Overview & Command Center API Module
 */
import { apiRequest } from './client';
import { OperationalOverviewSummary } from '../types';

export const overviewApi = {
  /**
   * Retrieve live aggregated command center overview metrics,
   * active cases summary, held-out validation metrics, and recent events.
   */
  async getOverview(): Promise<OperationalOverviewSummary> {
    return apiRequest<OperationalOverviewSummary>('/api/v2/ops/overview', {
      method: 'GET',
    });
  },
};
