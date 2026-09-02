/**
 * RiskOrbit — Action Preview & Simulation API Module
 */
import { apiRequest } from './client';
import { ActionPreviewResponse } from './decisions';

export const actionsApi = {
  /**
   * Preview proposed intervention action impact, blast radius, and friction cost before execution
   */
  async getActionPreview(caseId: string): Promise<ActionPreviewResponse> {
    return apiRequest<ActionPreviewResponse>(`/risk/cases/${encodeURIComponent(caseId)}/action-preview`, {
      method: 'GET',
    });
  },
};
