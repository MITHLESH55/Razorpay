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

export interface OutcomeResultResponse {
  case_id: string;
  execution_status: string;
  invariants_passed: boolean;
  actual_action_taken: string;
  outcome_timestamp: string;
  audit_hash: string;
}

export const simulationApi = {
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
      `/risk/cases/${encodeURIComponent(caseId)}/outcome`,
      {
        method: 'GET',
      }
    );
  },
};
