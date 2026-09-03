import React, { useEffect, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Lock,
  RefreshCw,
  ShieldCheck,
  BarChart3,
  Layers,
} from 'lucide-react';
import { SystemDriftSummary, UserContext } from '../types';
import { apiService } from '../services/api';
import { Badge, Button, Card, StatCard } from '../components/ui';

interface DriftViewProps {
  user: UserContext;
}

export const DriftView: React.FC<DriftViewProps> = () => {
  const [drift, setDrift] = useState<SystemDriftSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchDrift = async () => {
    try {
      const data = await apiService.getDriftReport();
      setDrift(data);
    } catch (err) {
      console.error('Failed to load drift summary', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDrift();
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const data = await apiService.recalculateDrift();
      setDrift(data);
    } catch (err) {
      console.error('Failed to recalculate drift summary', err);
    } finally {
      setRefreshing(false);
    }
  };

  if (loading || !drift) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="flex items-center gap-3 text-[#667085] font-mono text-xs">
          <Activity className="w-5 h-5 text-[#2563A6] animate-spin" />
          <span>Computing Feature Population Stability Index (PSI)...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-16 font-sans">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 bg-white rounded-2xl border border-[#D9DEE7] shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <Badge variant="navy" size="sm">
              FEATURE DRIFT & STABILITY
            </Badge>
            <span className="text-xs font-mono text-[#667085]">
              Baseline: Synthetic Reference Distribution (RandomState 42, n=200) &bull; Sliding Window: Active Replay
            </span>
          </div>
          <h1 className="text-xl font-bold tracking-tight text-[#172033] mt-1">
            Population Stability Index (PSI) Monitor
          </h1>
          <p className="text-xs text-[#667085] font-mono mt-0.5">
            Tracking statistical covariate shift and graph density drift against the frozen Phase 1/3 benchmark.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            icon={<RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin text-[#2563A6]' : ''}`} />}
            onClick={handleRefresh}
            disabled={refreshing}
          >
            {refreshing ? 'Recalculating...' : 'Recalculate PSI'}
          </Button>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 font-mono">
        <StatCard
          title="Overall Status"
          value={drift.overall_status === 'NO_DRIFT' ? 'STABLE' : drift.overall_status}
          subtitle={drift.overall_status === 'NO_CURRENT_WINDOW' ? 'Awaiting current observations' : 'Distribution Stability Confirmed'}
          badge={drift.overall_status === 'NO_DRIFT' ? 'PSI < 0.10' : 'Review'}
          badgeVariant={drift.overall_status === 'NO_DRIFT' ? 'success' : 'warning'}
          icon={<Activity className="w-4 h-4 text-[#15803D]" />}
        />

        <StatCard
          title="Maximum Feature PSI"
          value={drift.max_psi.toFixed(4)}
          subtitle="Target safety limit: < 0.1000"
          badge={drift.max_psi < 0.10 ? 'Safe' : 'Elevated'}
          badgeVariant={drift.max_psi < 0.10 ? 'success' : 'warning'}
          icon={<BarChart3 className="w-4 h-4 text-[#2563A6]" />}
        />

        <StatCard
          title="Evaluated Features"
          value={`${drift.evaluated_features_count}`}
          subtitle={`${drift.drifting_features_count} Drifting Features Detected`}
          badge="Covariates"
          badgeVariant="info"
          icon={<Layers className="w-4 h-4 text-[#183B67]" />}
        />

        <StatCard
          title="Model Freeze Guarantee"
          value="Offline Sealed"
          subtitle="Zero Automated Online Retraining"
          badge="Invariant #1"
          badgeVariant="purple"
          icon={<Lock className="w-4 h-4 text-purple-600" />}
        />
      </div>

      {/* Feature PSI Detail Table */}
      <Card
        title="Feature Population Stability Breakdown"
        subtitle={`Updated: ${drift.last_evaluated_at.slice(0, 19).replace('T', ' ')} UTC`}
        icon={<BarChart3 className="w-4 h-4 text-[#183B67]" />}
      >
        <div className="overflow-x-auto">
          <table className="w-full min-w-[850px] text-left text-xs font-mono">
            <thead>
              <tr className="bg-[#F8FAFC] border-b border-[#D9DEE7] text-[#667085] text-[11px]">
                <th className="p-3 font-semibold whitespace-nowrap">Feature Name</th>
                <th className="p-3 font-semibold text-center whitespace-nowrap">PSI Score</th>
                <th className="p-3 font-semibold text-center whitespace-nowrap">Status</th>
                <th className="p-3 font-semibold text-right whitespace-nowrap">Baseline Mean ± Std</th>
                <th className="p-3 font-semibold text-right whitespace-nowrap">Current Mean ± Std</th>
                <th className="p-3 font-semibold text-center whitespace-nowrap">Trend</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#F1F5F9]">
              {drift.feature_reports.map((report) => (
                <tr key={report.feature_name} className="hover:bg-[#F8FAFC] transition-colors">
                  <td className="p-3 font-bold text-[#172033] whitespace-nowrap">{report.feature_name}</td>
                  <td className="p-3 text-center text-[#2563A6] font-bold whitespace-nowrap">
                    {report.psi_score.toFixed(4)}
                  </td>
                  <td className="p-3 text-center whitespace-nowrap">
                    <Badge
                      variant={
                        report.status === 'NO_DRIFT'
                          ? 'success'
                          : report.status === 'MODERATE_DRIFT'
                          ? 'warning'
                          : 'critical'
                      }
                      size="sm"
                      icon={
                        report.status === 'NO_DRIFT' ? (
                          <CheckCircle2 className="w-3 h-3 text-[#15803D]" />
                        ) : (
                          <AlertTriangle className="w-3 h-3 text-[#B7791F]" />
                        )
                      }
                    >
                      {report.status}
                    </Badge>
                  </td>
                  <td className="p-3 text-right text-[#667085] whitespace-nowrap">
                    {report.baseline_mean.toLocaleString(undefined, { maximumFractionDigits: 2 })} ±{' '}
                    {report.baseline_std.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                  </td>
                  <td className="p-3 text-right text-[#172033] font-semibold whitespace-nowrap">
                    {report.current_mean.toLocaleString(undefined, { maximumFractionDigits: 2 })} ±{' '}
                    {report.current_std.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                  </td>
                  <td className="p-3 text-center whitespace-nowrap">
                    <span className="text-[#667085] text-[10px] font-semibold">{report.drift_direction}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Governance & Policy Advisory */}
      <div className="p-5 rounded-2xl bg-white border border-[#D9DEE7] shadow-sm space-y-2 text-xs font-mono">
        <div className="flex items-center gap-2 text-[#15803D] font-bold">
          <ShieldCheck className="w-4 h-4" />
          <span>System Governance Advisory</span>
        </div>
        <p className="text-[#172033] font-sans text-xs">{drift.recommendation}</p>
        <p className="text-[11px] text-[#667085] font-sans">
          <strong>Section 0 Invariant:</strong> If PSI exceeds 0.25 on primary signals, the system triggers alerts for human review and offline investigation. Automated retraining in production is strictly prohibited by system governance invariants.
        </p>
      </div>
    </div>
  );
};
