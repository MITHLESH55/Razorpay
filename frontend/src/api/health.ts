/**
 * RiskOrbit — Health, Probes & Observability API Module
 */
import { apiRequest } from './client';
import { OverviewKPIs } from '../types';

export interface ComponentHealthDetail {
  status: 'HEALTHY' | 'DEGRADED' | 'UNAVAILABLE';
  details?: string;
}

export interface SystemHealthResponse {
  overall_status: 'HEALTHY' | 'DEGRADED' | 'UNAVAILABLE';
  components: Record<string, ComponentHealthDetail>;
}

export interface Phase1HealthResponse {
  status: string;
  model_version: string;
  threshold: number;
}

export const healthApi = {
  /**
   * High-level overview KPIs for executive command center
   */
  async getOverviewKPIs(): Promise<OverviewKPIs> {
    return apiRequest<OverviewKPIs>('/api/v2/ops/overview', {
      method: 'GET',
    });
  },

  /**
   * Readiness probe across all subsystems (API, Model, Graph, Evidence, Policy, Storage)
   */
  async getReadiness(): Promise<SystemHealthResponse> {
    return apiRequest<SystemHealthResponse>('/ready', {
      method: 'GET',
    });
  },

  /**
   * Liveness probe for process uptime
   */
  async getLiveness(): Promise<SystemHealthResponse> {
    return apiRequest<SystemHealthResponse>('/live', {
      method: 'GET',
    });
  },

  /**
   * Basic API health probe
   */
  async getBasicHealth(): Promise<Phase1HealthResponse> {
    return apiRequest<Phase1HealthResponse>('/health', {
      method: 'GET',
    });
  },
};
