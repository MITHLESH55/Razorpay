/**
 * RiskOrbit — Graph & Network Topology API Module
 */
import { apiRequest } from './client';
import { GraphEdge, GraphNode } from '../types';

export interface CaseGraphResponse {
  case_id: string;
  root_entity?: string;
  member_accounts?: string[];
  shared_devices?: string[];
  shared_ips?: string[];
  targeted_merchants?: string[];
  graph_statistics?: Record<string, any>;
  nodes?: GraphNode[];
  edges?: GraphEdge[];
}

export const graphApi = {
  /**
   * Retrieve graph topology for a specific case
   */
  async getCaseGraph(caseId: string): Promise<CaseGraphResponse> {
    return apiRequest<CaseGraphResponse>(`/risk/cases/${encodeURIComponent(caseId)}/graph`, {
      method: 'GET',
    });
  },
};
