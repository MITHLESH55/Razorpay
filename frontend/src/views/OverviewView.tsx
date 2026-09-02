import React, { useEffect, useState } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  Zap,
  Activity,
  ArrowUpRight,
  Clock,
  Layers,
  CheckCircle2,
  Lock,
  Search,
} from 'lucide-react';
import { OverviewKPIs, RiskCaseRecord, UserContext } from '../types';
import { apiService } from '../services/api';
import { Badge, Button, Card, StatCard } from '../components/ui';

interface OverviewViewProps {
  user: UserContext;
  onSelectCase: (caseId: string) => void;
}

export const OverviewView: React.FC<OverviewViewProps> = ({ onSelectCase }) => {
  const [kpis, setKpis] = useState<OverviewKPIs | null>(null);
  const [recentCases, setRecentCases] = useState<RiskCaseRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [overviewData, queueData] = await Promise.all([
        apiService.getOverview(),
        apiService.getQueue({ limit: 6 }),
      ]);
      setKpis(overviewData);
      setRecentCases(queueData);
    } catch (e: any) {
      console.error('Failed to load overview data', e);
      setError(
        e.message || 'Unable to reach RiskOrbit API. Please verify the backend service is running.'
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="flex items-center gap-3 text-[#667085] font-mono text-xs">
          <Activity className="w-5 h-5 text-[#2563A6] animate-spin" />
          <span>Synchronizing Operational Telemetry...</span>
        </div>
      </div>
    );
  }

  if (error || !kpis) {
    return (
      <div className="flex flex-col items-center justify-center h-96 p-6 text-center bg-white rounded-2xl border border-[#D9DEE7] shadow-sm max-w-lg mx-auto my-12">
        <div className="w-12 h-12 rounded-xl bg-red-50 text-red-600 flex items-center justify-center mb-3">
          <ShieldAlert className="w-6 h-6" />
        </div>
        <h3 className="text-sm font-bold text-[#172033]">Operational Telemetry Synchronization Failed</h3>
        <p className="text-xs text-[#667085] mt-1 mb-4 leading-relaxed">
          {error || 'Unable to reach RiskOrbit API. Please verify the backend service is running.'}
        </p>
        <Button variant="outline" size="sm" onClick={fetchData}>
          Retry Connection
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-12">
      {/* Top Banner: Global Operational Posture & Telemetry */}
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 p-6 rounded-2xl bg-white border border-[#D9DEE7] shadow-sm">
        <div className="space-y-1.5 min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="navy" size="sm">
              OPERATIONAL STATUS: ACTIVE
            </Badge>
            <span className="text-xs font-mono text-[#667085]">
              Environment: <strong className="text-[#172033]">LIVE LOCAL BACKEND</strong>
            </span>
          </div>
          <h1 className="text-xl font-bold tracking-tight text-[#172033]">
            Executive Command Center & Observability
          </h1>
          <p className="text-xs text-[#667085] max-w-3xl">
            Real-time bounded risk governance, human approval gate, graph relationship telemetry,
            and frozen model release monitoring.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3 font-mono text-xs flex-shrink-0">
          <div className="bg-[#F8FAFC] px-3.5 py-2 rounded-xl border border-[#D9DEE7] text-right">
            <span className="text-[10px] uppercase font-bold text-[#98A2B3] block">Latency p50 / p95</span>
            <span className="font-bold text-[#172033]">
              {kpis.latency_p50_ms} ms / {kpis.latency_p95_ms} ms
            </span>
          </div>
          <div className="bg-[#F8FAFC] px-3.5 py-2 rounded-xl border border-[#D9DEE7] text-right">
            <span className="text-[10px] uppercase font-bold text-[#98A2B3] block">Ring Recall Rate</span>
            <span className="font-bold text-[#15803D]">{kpis.held_out_metrics.ring_recall}</span>
          </div>
        </div>
      </div>

      {/* Primary Operational KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {/* Card 1: Critical Cases */}
        <StatCard
          title="Critical Threat Cases"
          value={kpis.critical_priority_count}
          subtitle="Primary ring members requiring intervention"
          badge="High Blast Radius"
          badgeVariant="critical"
          icon={<ShieldAlert className="w-4 h-4 text-[#C53030]" />}
        />

        {/* Card 2: Pending Human Approvals */}
        <StatCard
          title="Pending Approvals"
          value={kpis.pending_human_approvals}
          subtitle="High-impact actions awaiting sign-off"
          badge="In Gate Queue"
          badgeVariant="warning"
          icon={<Clock className="w-4 h-4 text-[#B7791F]" />}
        />

        {/* Card 3: Pending INR Exposure */}
        <StatCard
          title="Pending Exposure"
          value={`₹${(kpis.pending_exposure_inr / 1000).toFixed(0)}k`}
          subtitle="Total transaction volume in active review"
          badge="INR Volume"
          badgeVariant="info"
          icon={<Zap className="w-4 h-4 text-[#2563A6]" />}
        />

        {/* Card 4: Hard Block FPR (Invariant) */}
        <StatCard
          title="Hard-Block FPR"
          value={kpis.held_out_metrics.hard_block_fpr}
          subtitle="Zero innocent customer friction on 13,373 rows"
          badge="5/5 Invariant Pass"
          badgeVariant="success"
          icon={<CheckCircle2 className="w-4 h-4 text-[#15803D]" />}
        />
      </div>

      {/* Priority Case Queue (Operational Workbench) */}
      <Card
        title="Active Priority Cases in Queue"
        subtitle="Ranked deterministically by 3-tier evidence score and potential blast radius"
        headerRight={
          <Button
            variant="outline"
            size="sm"
            onClick={() => onSelectCase(recentCases[0]?.case_id || 'CASE-RING-A-01')}
          >
            Open Full Queue Workbench &rarr;
          </Button>
        }
      >
        <div className="overflow-x-auto">
          <table className="w-full min-w-[960px] text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-[#D9DEE7] text-[#667085] text-[11px] bg-[#F8FAFC]">
                <th className="py-2.5 px-3.5 font-semibold whitespace-nowrap">Case ID</th>
                <th className="py-2.5 px-3.5 font-semibold whitespace-nowrap">Customer / TXN</th>
                <th className="py-2.5 px-3.5 font-semibold whitespace-nowrap">Amount (INR)</th>
                <th className="py-2.5 px-3.5 font-semibold whitespace-nowrap">Priority</th>
                <th className="py-2.5 px-3.5 font-semibold whitespace-nowrap">Decision Score</th>
                <th className="py-2.5 px-3.5 font-semibold whitespace-nowrap">Recommended Action</th>
                <th className="py-2.5 px-3.5 font-semibold whitespace-nowrap">Status</th>
                <th className="py-2.5 px-3.5 font-semibold text-right whitespace-nowrap">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#F1F5F9]">
              {recentCases.map((c) => (
                <tr key={c.case_id} className="hover:bg-[#F8FAFC] transition-colors">
                  <td className="py-3 px-3.5 font-bold text-[#183B67] whitespace-nowrap">{c.case_id}</td>
                  <td className="py-3 px-3.5 text-[#172033] whitespace-nowrap">
                    <div className="font-semibold">{c.customer_id}</div>
                    <div className="text-[10px] text-[#98A2B3]">{c.transaction_id}</div>
                  </td>
                  <td className="py-3 px-3.5 font-semibold text-[#172033] whitespace-nowrap">
                    ₹{c.amount_inr.toLocaleString()}
                  </td>
                  <td className="py-3 px-3.5 whitespace-nowrap">
                    <Badge
                      variant={
                        c.priority === 'CRITICAL'
                          ? 'critical'
                          : c.priority === 'HIGH'
                          ? 'warning'
                          : 'neutral'
                      }
                      size="sm"
                    >
                      {c.priority}
                    </Badge>
                  </td>
                  <td className="py-3 px-3.5 font-semibold text-[#172033] whitespace-nowrap">
                    {c.decision_score.toFixed(3)}
                  </td>
                  <td className="py-3 px-3.5 font-bold text-[#C53030] whitespace-nowrap">
                    {c.recommended_action}
                  </td>
                  <td className="py-3 px-3.5 whitespace-nowrap">
                    <Badge variant="neutral" size="sm">
                      {c.status}
                    </Badge>
                  </td>
                  <td className="py-3 px-3.5 text-right whitespace-nowrap">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onSelectCase(c.case_id)}
                    >
                      Investigate
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Flagship Demonstration Scenarios */}
      <Card
        title="Flagship Demonstration Scenarios"
        subtitle="Inspect verified 2-hop subgraph topology and source-grounded evidence records"
        badge={<Badge variant="navy">Evaluation Cases</Badge>}
      >
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {/* Pattern A */}
          <div
            onClick={() => onSelectCase('CASE-RING-A-01')}
            className="p-4 rounded-xl border border-[#D9DEE7] bg-[#F8FAFC] hover:bg-white hover:border-[#2563A6] hover:shadow-md cursor-pointer transition-all space-y-2.5 group flex flex-col justify-between"
          >
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Badge variant="critical" size="sm">
                  PATTERN A: DEVICE FARM
                </Badge>
                <span className="text-xs font-mono text-[#667085] group-hover:text-[#2563A6] flex items-center gap-1">
                  Inspect <ArrowUpRight className="w-3.5 h-3.5" />
                </span>
              </div>
              <h4 className="text-xs font-bold text-[#172033]">Android Emulator Device Farm Collusion</h4>
              <p className="text-[11px] text-[#667085] leading-relaxed line-clamp-2">
                32 synthetic accounts routing rapid micropayments through a rooted Android emulator ID.
              </p>
            </div>
            <div className="flex justify-between items-center text-[10.5px] font-mono text-[#667085] pt-2 border-t border-[#E2E8F0]">
              <span>Score: <strong className="text-[#172033]">0.895</strong></span>
              <span className="text-[#C53030] font-bold whitespace-nowrap">BLOCK_TRANSACTION</span>
            </div>
          </div>

          {/* Pattern B */}
          <div
            onClick={() => onSelectCase('CASE-RING-B-02')}
            className="p-4 rounded-xl border border-[#D9DEE7] bg-[#F8FAFC] hover:bg-white hover:border-[#2563A6] hover:shadow-md cursor-pointer transition-all space-y-2.5 group flex flex-col justify-between"
          >
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Badge variant="purple" size="sm">
                  PATTERN B: CIRCULAR
                </Badge>
                <span className="text-xs font-mono text-[#667085] group-hover:text-[#2563A6] flex items-center gap-1">
                  Inspect <ArrowUpRight className="w-3.5 h-3.5" />
                </span>
              </div>
              <h4 className="text-xs font-bold text-[#172033]">Circular Layering Syndicate</h4>
              <p className="text-[11px] text-[#667085] leading-relaxed line-clamp-2">
                4-hop circular UPI fund layering chain with 96.9% volume retention across multiple nodes.
              </p>
            </div>
            <div className="flex justify-between items-center text-[10.5px] font-mono text-[#667085] pt-2 border-t border-[#E2E8F0]">
              <span>Score: <strong className="text-[#172033]">0.942</strong></span>
              <span className="text-[#C53030] font-bold whitespace-nowrap">FREEZE_RING</span>
            </div>
          </div>

          {/* Pattern C / Hard Negative */}
          <div
            onClick={() => onSelectCase('CASE-HARDNEG-04')}
            className="p-4 rounded-xl border border-[#D9DEE7] bg-[#F8FAFC] hover:bg-white hover:border-[#2563A6] hover:shadow-md cursor-pointer transition-all space-y-2.5 group flex flex-col justify-between md:col-span-2 xl:col-span-1"
          >
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Badge variant="success" size="sm">
                  HARD NEGATIVE
                </Badge>
                <span className="text-xs font-mono text-[#667085] group-hover:text-[#2563A6] flex items-center gap-1">
                  Inspect <ArrowUpRight className="w-3.5 h-3.5" />
                </span>
              </div>
              <h4 className="text-xs font-bold text-[#172033]">Festive Corporate Spend Spike</h4>
              <p className="text-[11px] text-[#667085] leading-relaxed line-clamp-2">
                ₹89k legitimate enterprise purchase. Bounded 2FA step-up without destructive block.
              </p>
            </div>
            <div className="flex justify-between items-center text-[10.5px] font-mono text-[#667085] pt-2 border-t border-[#E2E8F0]">
              <span>Score: <strong className="text-[#172033]">0.284</strong></span>
              <span className="text-[#2563A6] font-bold whitespace-nowrap">STEP_UP_2FA (0.04% FPR)</span>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
};
