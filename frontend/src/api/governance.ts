/**
 * RiskOrbit — Governance & Policy Controls API Module
 */
import { apiRequest } from './client';
import { SystemControlsState } from '../types';

export interface GovernanceStateResponse {
  environment: string;
  model_version: string;
  graph_version: string;
  evidence_version: string;
  policy_version: string;
  shadow_mode: boolean;
  safe_mode: boolean;
  action_pause: boolean;
  release_manifest_hash: string;
  artifact_hashes: Record<string, string>;
}

export interface UpdateControlsPayload {
  shadow_mode?: boolean;
  kill_switch?: boolean;
  graph_available?: boolean;
  reason?: string;
}

export const governanceApi = {
  /**
   * Retrieve high-level governance and release checksum status
   */
  async getGovernanceState(): Promise<GovernanceStateResponse> {
    return apiRequest<GovernanceStateResponse>('/risk/governance', {
      method: 'GET',
    });
  },

  /**
   * Retrieve active system controls and health state
   */
  async getSystemControls(): Promise<SystemControlsState> {
    return apiRequest<SystemControlsState>('/api/v2/ops/controls', {
      method: 'GET',
    });
  },

  /**
   * Update emergency controls (Shadow Mode, Kill Switch, Safe Mode) — Admin role required
   */
  async updateSystemControls(payload: UpdateControlsPayload): Promise<SystemControlsState> {
    return apiRequest<SystemControlsState>('/api/v2/ops/controls', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },
};
