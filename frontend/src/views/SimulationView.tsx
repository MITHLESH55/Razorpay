import React, { useEffect, useState } from 'react';
import {
  Sliders,
  Play,
  RotateCcw,
  ShieldAlert,
  CheckCircle2,
  DollarSign,
} from 'lucide-react';
import { UserContext } from '../types';
import { apiService } from '../services/api';
import { PolicySimulationResponse } from '../api/simulation';
import { Badge, Button, Card, StatCard } from '../components/ui';

interface SimulationViewProps {
  user: UserContext;
}

const isPolicySimulationResponse = (value: unknown): value is PolicySimulationResponse => {
  if (!value || typeof value !== 'object') return false;
  const response = value as PolicySimulationResponse;
  const hasMetrics = (metrics: PolicySimulationResponse['baseline']) =>
    metrics &&
    typeof metrics.total_prevented_loss_inr === 'number' &&
    typeof metrics.total_friction_cost_inr === 'number' &&
    typeof metrics.net_recovery_inr === 'number' &&
    typeof metrics.hard_block_fpr_pct === 'number' &&
    typeof metrics.intervention_fpr_pct === 'number' &&
    metrics.action_counts &&
    typeof metrics.action_counts === 'object';
  return hasMetrics(response.baseline) &&
    hasMetrics(response.candidate) &&
    typeof response.parameters?.tau_threshold === 'number' &&
    typeof response.parameters?.hard_block_floor === 'number' &&
    typeof response.parameters?.friction_weight === 'number' &&
    typeof response.parameters?.sample_size === 'number' &&
    typeof response.frozen_policy_version === 'string' &&
    response.status_tag === 'SIMULATED' &&
    typeof response.provenance === 'string';
};

export const SimulationView: React.FC<SimulationViewProps> = () => {
  // Candidate policy parameters
  const [tauThreshold, setTauThreshold] = useState(0.35);
  const [frictionWeight, setFrictionWeight] = useState(1.0);
  const [autoBlockThreshold, setAutoBlockThreshold] = useState(0.70);
  const [sampleSize] = useState(100);

  // Simulation execution state
  const [simulating, setSimulating] = useState(false);
  const [loadingBaseline, setLoadingBaseline] = useState(true);
  const [simulationError, setSimulationError] = useState<string | null>(null);

  // Baseline vs Candidate Comparison Data (initialized dynamically from backend)
  const [baseline, setBaseline] = useState<PolicySimulationResponse['baseline'] | null>(null);

  const [candidate, setCandidate] = useState<PolicySimulationResponse['baseline'] | null>(null);

  // Load baseline metrics dynamically on mount
  const loadBaseline = async () => {
    setLoadingBaseline(true);
    setSimulationError(null);
    try {
        const result = await apiService.simulatePolicy({
          tau_threshold: 0.35,
          hard_block_floor: 0.70,
          friction_weight: 1.0,
          sample_size: sampleSize,
        });
        if (!isPolicySimulationResponse(result)) throw new Error('Invalid simulation response');
        setBaseline(result.baseline);
        setCandidate(result.candidate);
    } catch (err) {
      console.error('Failed to load backend simulation baseline', err);
      setBaseline(null);
      setCandidate(null);
      setSimulationError('Counterfactual simulation unavailable.');
    } finally {
      setLoadingBaseline(false);
    }
  };

  useEffect(() => {
    loadBaseline();
  }, []);

  const handleRunSimulation = async () => {
    setSimulating(true);
    try {
      setSimulationError(null);
      const result = await apiService.simulatePolicy({
        tau_threshold: tauThreshold,
        hard_block_floor: autoBlockThreshold,
        friction_weight: frictionWeight,
        sample_size: sampleSize,
      });
      if (!isPolicySimulationResponse(result)) throw new Error('Invalid simulation response');
      setBaseline(result.baseline);
      setCandidate(result.candidate);
    } catch (err) {
      console.error('Simulation run failed', err);
      setSimulationError('Counterfactual simulation unavailable.');
    } finally {
      setSimulating(false);
    }
  };

  const handleReset = () => {
    setTauThreshold(0.35);
    setFrictionWeight(1.0);
    setAutoBlockThreshold(0.70);
    setCandidate(baseline);
  };

  if (loadingBaseline) {
    return (
      <div className="flex items-center justify-center h-96 text-[#667085] font-mono text-xs">
        Loading backend counterfactual policy baseline...
      </div>
    );
  }

  if (simulationError || !baseline || !candidate) {
    return (
      <div className="flex flex-col items-center justify-center h-96 gap-3 text-[#667085] font-mono text-xs">
        <span>{simulationError || 'Counterfactual simulation unavailable.'}</span>
        <Button variant="outline" size="sm" onClick={loadBaseline}>
          Retry
        </Button>
      </div>
    );
  }

  const netDiff = candidate.net_recovery_inr - baseline.net_recovery_inr;
  const frictionDiff = candidate.total_friction_cost_inr - baseline.total_friction_cost_inr;

  return (
    <div className="space-y-6 pb-16 font-sans">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 bg-white rounded-2xl border border-[#D9DEE7] shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <Badge variant="navy" size="sm">
              COUNTERFACTUAL WORKBENCH
            </Badge>
            <span className="text-xs font-mono text-[#667085]">Offline Policy Sandbox</span>
          </div>
          <h1 className="text-xl font-bold tracking-tight text-[#172033] mt-1">
            Counterfactual Policy Simulation
          </h1>
          <p className="text-xs text-[#667085] font-mono mt-0.5">
            Compare bounded response strategies offline without changing the frozen production policy.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            icon={<RotateCcw className="w-3.5 h-3.5" />}
            onClick={handleReset}
          >
            Reset (τ = 0.35)
          </Button>
          <Button
            variant="primary"
            size="md"
            icon={<Play className="w-3.5 h-3.5 fill-current" />}
            onClick={handleRunSimulation}
            disabled={simulating}
          >
            {simulating ? 'Simulating Queue...' : 'Run Simulation'}
          </Button>
        </div>
      </div>

      {/* Control Sliders Card */}
      <Card
        title="Candidate Policy Hyperparameters"
        subtitle="Test counterfactuals against the frozen production baseline"
        headerRight={
          <span className="text-xs font-mono text-[#667085]">
            Frozen Baseline: <strong className="text-[#183B67]">τ = 0.35</strong>
          </span>
        }
      >
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-6">
          {/* Slider 1: Tau Threshold */}
          <div className="space-y-2 bg-[#F8FAFC] p-4 rounded-xl border border-[#D9DEE7]">
            <div className="flex justify-between items-center text-xs font-mono">
              <span className="text-[#172033] font-semibold">Intervention Threshold (τ)</span>
              <span className="text-[#2563A6] font-bold text-sm">{tauThreshold.toFixed(2)}</span>
            </div>
            <input
              type="range"
              min="0.10"
              max="0.80"
              step="0.01"
              value={tauThreshold}
              onChange={(e) => setTauThreshold(parseFloat(e.target.value))}
              className="w-full h-1.5 bg-[#E2E8F0] rounded-lg appearance-none cursor-pointer accent-[#2563A6]"
            />
            <p className="text-[11px] text-[#667085] font-mono">
              Lower values trigger 2FA on softer ring signals. Default = 0.35.
            </p>
          </div>

          {/* Slider 2: Auto-Block Threshold */}
          <div className="space-y-2 bg-[#F8FAFC] p-4 rounded-xl border border-[#D9DEE7]">
            <div className="flex justify-between items-center text-xs font-mono">
              <span className="text-[#172033] font-semibold">Hard Block Score Floor</span>
              <span className="text-[#C53030] font-bold text-sm">
                {autoBlockThreshold.toFixed(2)}
              </span>
            </div>
            <input
              type="range"
              min="0.50"
              max="0.95"
              step="0.01"
              value={autoBlockThreshold}
              onChange={(e) => setAutoBlockThreshold(parseFloat(e.target.value))}
              className="w-full h-1.5 bg-[#E2E8F0] rounded-lg appearance-none cursor-pointer accent-[#C53030]"
            />
            <p className="text-[11px] text-[#667085] font-mono">
              High confidence boundary for blocking. Default = 0.70.
            </p>
          </div>

          {/* Slider 3: Friction Penalty Weight */}
          <div className="space-y-2 bg-[#F8FAFC] p-4 rounded-xl border border-[#D9DEE7]">
            <div className="flex justify-between items-center text-xs font-mono">
              <span className="text-[#172033] font-semibold">Friction Penalty Weight</span>
              <span className="text-[#183B67] font-bold text-sm">
                {frictionWeight.toFixed(1)}x
              </span>
            </div>
            <input
              type="range"
              min="0.5"
              max="3.0"
              step="0.1"
              value={frictionWeight}
              onChange={(e) => setFrictionWeight(parseFloat(e.target.value))}
              className="w-full h-1.5 bg-[#E2E8F0] rounded-lg appearance-none cursor-pointer accent-[#183B67]"
            />
            <p className="text-[11px] text-[#667085] font-mono">
              Simulated churn & merchant friction cost factor.
            </p>
          </div>
        </div>
      </Card>

      {/* Comparison Delta Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 font-mono">
        {/* Metric 1: Modeled Net Protection */}
        <StatCard
          title="Modeled Net Protection"
          value={`₹${(candidate.net_recovery_inr / 100000).toFixed(2)}L`}
          subtitle={
            netDiff >= 0
              ? `+₹${netDiff.toLocaleString()} INR vs Baseline`
              : `-₹${Math.abs(netDiff).toLocaleString()} INR vs Baseline`
          }
          badge={netDiff >= 0 ? '+Gain' : '-Drop'}
          badgeVariant={netDiff >= 0 ? 'success' : 'critical'}
          icon={<DollarSign className="w-4 h-4 text-[#15803D]" />}
        />

        {/* Metric 2: Estimated Abuse Loss Prevented */}
        <StatCard
          title="Estimated Abuse Loss Prevented"
          value={`₹${(candidate.total_prevented_loss_inr / 100000).toFixed(2)}L`}
          subtitle="Gross malicious ring volume intercepted"
          badge="Ring Interception"
          badgeVariant="info"
          icon={<ShieldAlert className="w-4 h-4 text-[#2563A6]" />}
        />

        {/* Metric 3: Friction Cost INR */}
        <StatCard
          title="Simulated Friction Cost"
          value={`₹${candidate.total_friction_cost_inr.toLocaleString()}`}
          subtitle={
            frictionDiff === 0
              ? 'No incremental friction vs Baseline'
              : `${frictionDiff > 0 ? '+' : '-'}₹${Math.abs(frictionDiff).toLocaleString()} vs Baseline`
          }
          badge="Friction"
          badgeVariant="warning"
          icon={<Sliders className="w-4 h-4 text-[#B7791F]" />}
        />

        {/* Metric 4: Hard Block FPR */}
        <StatCard
          title="Hard-Block FPR"
          value={`${candidate.hard_block_fpr_pct}%`}
          subtitle="Target safety ceiling: ≤ 0.05%"
          badge={candidate.hard_block_fpr_pct <= 0.05 ? 'Pass' : 'Breach'}
          badgeVariant={candidate.hard_block_fpr_pct <= 0.05 ? 'success' : 'critical'}
          icon={<CheckCircle2 className="w-4 h-4 text-[#15803D]" />}
        />
      </div>

      {/* Action Breakdown & Policy Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 font-mono text-xs">
        {/* Baseline Distribution */}
        <Card
          title="Baseline Production Distribution (τ = 0.35)"
          subtitle="Authoritative production policy behavior"
          badge={<Badge variant="neutral" size="sm">Baseline</Badge>}
        >
          <div className="space-y-2">
            {Object.entries(baseline.action_counts).map(([act, count]) => (
              <div
                key={act}
                className="flex items-center justify-between p-2.5 rounded-lg bg-[#F8FAFC] border border-[#D9DEE7]"
              >
                <span className="text-[#172033] font-semibold">{act}</span>
                <div className="flex items-center gap-2">
                  <span className="text-[#667085]">{count} cases</span>
                  <div className="w-24 h-2 bg-[#E2E8F0] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[#183B67] rounded-full"
                      style={{ width: `${(count / 100) * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Candidate Distribution */}
        <Card
          title={`Candidate Counterfactual Distribution (τ = ${tauThreshold.toFixed(2)})`}
          subtitle="Simulated counterfactual policy outcome"
          badge={<Badge variant="info" size="sm">Simulated</Badge>}
        >
          <div className="space-y-2">
            {Object.entries(candidate.action_counts).map(([act, count]) => (
              <div
                key={act}
                className="flex items-center justify-between p-2.5 rounded-lg bg-[#F8FAFC] border border-[#D9DEE7]"
              >
                <span className="text-[#172033] font-semibold">{act}</span>
                <div className="flex items-center gap-2">
                  <span className="text-[#667085]">{count} cases</span>
                  <div className="w-24 h-2 bg-[#E2E8F0] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[#2563A6] rounded-full"
                      style={{ width: `${(count / 100) * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
};
