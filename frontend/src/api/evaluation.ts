/**
 * RiskOrbit — Evaluation, Benchmarks & Release Manifest API Module
 */
import { apiRequest } from './client';
import { EvaluationMetricsResponse, ManifestData, SystemDriftSummary } from '../types';

export const evaluationApi = {
  /**
   * Retrieve Single Source of Truth canonical evaluation metrics from RISKORBIT_FINAL_METRICS.json
   */
  async getEvaluationMetrics(): Promise<EvaluationMetricsResponse> {
    return apiRequest<EvaluationMetricsResponse>('/api/v2/ops/evaluation', {
      method: 'GET',
    });
  },

  /**
   * Retrieve immutable cryptographic release manifest and checksums from RISKORBIT_FINAL_MANIFEST.json
   */
  async getReleaseManifest(): Promise<ManifestData> {
    return apiRequest<ManifestData>('/api/v2/ops/manifest', {
      method: 'GET',
    });
  },

  /**
   * Evaluate covariate distribution shift (Population Stability Index) against frozen test baseline
   */
  async getDriftReport(): Promise<SystemDriftSummary> {
    return apiRequest<SystemDriftSummary>('/api/v2/ops/drift', {
      method: 'GET',
    });
  },

  /**
   * Explicitly recalculate covariate distribution shift (PSI) across sliding window against frozen test baseline
   */
  async recalculateDrift(): Promise<SystemDriftSummary> {
    return apiRequest<SystemDriftSummary>('/api/v2/ops/drift/recalculate', {
      method: 'POST',
    });
  },
};
