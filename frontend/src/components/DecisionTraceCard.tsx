import React from 'react';
import {
  Cpu,
  Scale,
} from 'lucide-react';
import { DecisionTrace } from '../types';
import { Badge } from './ui';

interface DecisionTraceCardProps {
  trace: DecisionTrace;
}

export const DecisionTraceCard: React.FC<DecisionTraceCardProps> = ({ trace }) => {
  const scores = [
    {
      label: 'p₁ Point Risk',
      sub: 'Transaction Model',
      value: trace.p1_raw_score,
      color: 'text-[#B7791F]',
      barColor: 'bg-[#B7791F]',
      desc: 'Supervised tree model probability',
    },
    {
      label: 'σ Membership',
      sub: 'Graph Ring Confidence',
      value: trace.sigma_membership_confidence,
      color: 'text-purple-700',
      barColor: 'bg-purple-600',
      desc: 'Topological distance & hubness penalty',
    },
    {
      label: 'ρ Evidence',
      sub: 'Multi-Family Strength',
      value: trace.rho_evidence_strength,
      color: 'text-[#2563A6]',
      barColor: 'bg-[#2563A6]',
      desc: 'Device + IP + Velocity signals',
    },
    {
      label: 'Tier Multiplier',
      sub: 'Blast Radius Limiter',
      value: trace.tier_multiplier,
      color: 'text-[#183B67]',
      barColor: 'bg-[#183B67]',
      desc: 'Proportional friction bounding',
    },
  ];

  return (
    <div className="bg-white rounded-xl border border-[#D9DEE7] p-5 space-y-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-[#F8FAFC] border border-[#D9DEE7]">
            <Cpu className="w-4 h-4 text-[#183B67]" />
          </div>
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-[#172033] font-mono">
              5-Score Decision Trace
            </h4>
            <p className="text-[11px] text-[#667085]">
              Grounded mathematical derivation of final intervention
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1.5 bg-[#F8FAFC] px-2.5 py-1 rounded-md border border-[#D9DEE7] text-xs font-mono">
          <span className="text-[#98A2B3]">Policy:</span>
          <span className="text-[#172033] font-bold">{trace.policy_rule_matched}</span>
        </div>
      </div>

      {/* 4 Input Decompositions */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
        {scores.map((s, idx) => (
          <div
            key={idx}
            className="bg-[#F8FAFC] p-3 rounded-lg border border-[#D9DEE7] space-y-1.5 relative overflow-hidden"
          >
            <div className="flex justify-between items-start">
              <div>
                <span className="text-xs font-mono font-bold text-[#172033]">{s.label}</span>
                <p className="text-[10px] text-[#98A2B3]">{s.sub}</p>
              </div>
              <span className={`text-sm font-mono font-bold ${s.color}`}>
                {(s.value * 100).toFixed(0)}%
              </span>
            </div>

            <div className="w-full h-1.5 bg-[#E2E8F0] rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${s.barColor}`}
                style={{ width: `${Math.min(100, s.value * 100)}%` }}
              />
            </div>
            <p className="text-[9.5px] text-[#667085] font-mono truncate">{s.desc}</p>
          </div>
        ))}
      </div>

      {/* Final Decision Score Derivation Banner */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-4 rounded-xl bg-[#F8FAFC] border border-[#D9DEE7] shadow-xs font-mono text-xs">
        <div className="flex items-center gap-3">
          <Scale className="w-5 h-5 text-[#183B67] flex-shrink-0" />
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[#667085]">Final Decision Score:</span>
              <span className="text-base font-extrabold text-[#172033]">
                {trace.final_decision_score.toFixed(3)}
              </span>
              <Badge
                variant={
                  trace.final_decision_score >= 0.7
                    ? 'critical'
                    : trace.final_decision_score >= 0.4
                    ? 'warning'
                    : 'success'
                }
                size="sm"
              >
                {trace.final_decision_score >= 0.7
                  ? 'CRITICAL RISK'
                  : trace.final_decision_score >= 0.4
                  ? 'ELEVATED RISK'
                  : 'LOW / ISOLATED'}
              </Badge>
            </div>
            <p className="text-[10px] text-[#98A2B3] mt-0.5">
              Formula: S = (0.35 × p₁) + (0.35 × σ) + (0.30 × ρ) bounded by tier multiplier
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 text-right flex-shrink-0 self-end sm:self-center">
          <div>
            <span className="text-[10px] text-[#98A2B3] block">Friction Cost:</span>
            <div className="text-xs font-bold text-[#183B67]">
              ₹{trace.friction_cost_estimate_inr.toLocaleString()}
            </div>
          </div>
          <div className="h-6 w-px bg-[#D9DEE7]" />
          <div>
            <span className="text-[10px] text-[#98A2B3] block">Intervention:</span>
            <div className="text-xs font-bold text-[#C53030] uppercase">
              {trace.bounded_intervention}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
