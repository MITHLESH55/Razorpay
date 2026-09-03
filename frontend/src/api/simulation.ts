/**
 * RiskOrbit — Counterfactual Policy Simulation API Module
 */
import { apiRequest } from './client';

export interface SimulationRequestPayload {
  simulated_action?: string;
  policy_version?: string;
  override_policy_parameters?: Record<string, any>;
  simulation_parameters?: Record<string, any>;
}

export interface SimulationResultResponse {
  case_id: string;
  simulated_action: string;
  executed_status: string;
  projected_friction_cost_inr: number;
  prevented_loss_inr: number;
  net_recovery_inr: number;
  simulation_timestamp: string;
  verification_result: string;
  status?: string;
  policy_deltas?: Record<string, any>;
  blast_radius_delta?: string;
}

export interface PolicySimulationResponse {
  baseline: {
    total_prevented_loss_inr: number;
    total_friction_cost_inr: number;
    net_recovery_inr: number;
    hard_block_fpr_pct: number;
    intervention_fpr_pct: number;
    action_counts: Record<string, number>;
  };
  candidate: PolicySimulationResponse['baseline'];
  parameters: {
    tau_threshold: number;
    hard_block_floor: number;
    friction_weight: number;
    sample_size: number;
  };
  frozen_policy_version: string;
  status_tag: 'SIMULATED';
  provenance: string;
}

export interface OutcomeResultResponse {
  case_id: string;
  execution_status: string;
  invariants_passed: boolean;
  actual_action_taken: string;
  outcome_timestamp: string;
  audit_hash: string;
}

export const simulationApi = {
  async simulatePolicy(parameters: PolicySimulationResponse['parameters']): Promise<PolicySimulationResponse> {
    return apiRequest<PolicySimulationResponse>('/api/v2/ops/simulation', {
      method: 'POST',
      body: JSON.stringify(parameters),
    });
  },
  /**
   * Run offline counterfactual simulation against the frozen backend risk engine
   */
  async simulateCase(
    caseId: string,
    payload: SimulationRequestPayload = {}
  ): Promise<SimulationResultResponse> {
    return apiRequest<SimulationResultResponse>(
      `/api/v2/ops/cases/${encodeURIComponent(caseId)}/simulate`,
      {
        method: 'POST',
        body: JSON.stringify({
          case_id: caseId,
          simulated_action: payload.simulated_action,
          override_policy_parameters: payload.override_policy_parameters || payload.simulation_parameters,
        }),
      }
    );
  },

  /**
   * Retrieve simulated outcome verification
   */
  async getCaseOutcome(caseId: string): Promise<OutcomeResultResponse> {
    return apiRequest<OutcomeResultResponse>(
      `/api/v2/ops/cases/${encodeURIComponent(caseId)}/outcome`,
      {
        method: 'GET',
      }
    );
  },
};
