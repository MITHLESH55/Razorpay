import React, { useEffect, useState } from 'react';
import {
  Search,
  ChevronRight,
  RotateCcw,
} from 'lucide-react';
import { RiskCaseRecord, UserContext } from '../types';
import { apiService } from '../services/api';
import { Badge, Button, Card } from '../components/ui';

interface RiskQueueViewProps {
  user: UserContext;
  onSelectCase: (caseId: string) => void;
}

export const RiskQueueView: React.FC<RiskQueueViewProps> = ({ onSelectCase }) => {
  const [cases, setCases] = useState<RiskCaseRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [priorityFilter, setPriorityFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [patternFilter, setPatternFilter] = useState<string>('');

  const fetchQueue = async () => {
    setLoading(true);
    try {
      const data = await apiService.getQueue({
        search: search || undefined,
        priority: priorityFilter || undefined,
        status: statusFilter || undefined,
        pattern: patternFilter || undefined,
        limit: 100,
      });
      setCases(data);
    } catch (err) {
      console.error('Queue fetch error', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, [priorityFilter, statusFilter, patternFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchQueue();
  };

  return (
    <div className="space-y-5 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 bg-white rounded-2xl border border-[#D9DEE7] shadow-sm">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="navy" size="sm">
              WORKSTATION TRIAGE
            </Badge>
            <span className="text-xs font-mono text-[#667085]">Deterministic Priority Ranking</span>
          </div>
          <h1 className="text-xl font-bold tracking-tight text-[#172033]">
            Risk Operations Analyst Queue
          </h1>
          <p className="text-xs text-[#667085] mt-0.5">
            Prioritized case triage with bounded policy recommendations, graph topology metrics, and evidence audits.
          </p>
        </div>

        <div className="flex items-center gap-2 font-mono text-xs text-[#667085]">
          <div className="px-3.5 py-2 rounded-xl bg-[#F8FAFC] border border-[#D9DEE7]">
            Total Matched Cases: <strong className="text-[#183B67]">{cases.length}</strong>
          </div>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <Card>
        <div className="space-y-3.5">
          <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row gap-2">
            <div className="relative flex-1">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#98A2B3] pointer-events-none" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search Case ID, Transaction, Customer, Ring ID (e.g. CASE-RING-A-01)..."
                className="w-full bg-[#F8FAFC] border border-[#D9DEE7] rounded-lg pl-9 pr-4 py-2 text-xs text-[#172033] placeholder-[#98A2B3] focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#2563A6]/20 focus:border-[#2563A6] transition-all font-mono"
              />
            </div>
            <Button type="submit" variant="primary" size="md">
              Filter Queue
            </Button>
          </form>

          {/* Filter Dropdowns */}
          <div className="flex flex-wrap items-center gap-3 text-xs">
            <div className="flex items-center gap-1.5 font-medium text-[#667085]">
              <span>Priority:</span>
              <select
                value={priorityFilter}
                onChange={(e) => setPriorityFilter(e.target.value)}
                className="bg-[#F8FAFC] border border-[#D9DEE7] rounded-lg px-2.5 py-1 text-xs text-[#172033] font-semibold focus:outline-none focus:border-[#2563A6]"
              >
                <option value="">All Priorities</option>
                <option value="CRITICAL">CRITICAL</option>
                <option value="HIGH">HIGH</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="LOW">LOW</option>
              </select>
            </div>

            <div className="flex items-center gap-1.5 font-medium text-[#667085]">
              <span>Status:</span>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-[#F8FAFC] border border-[#D9DEE7] rounded-lg px-2.5 py-1 text-xs text-[#172033] font-semibold focus:outline-none focus:border-[#2563A6]"
              >
                <option value="">All Statuses</option>
                <option value="RECOMMENDED">RECOMMENDED</option>
                <option value="PENDING_APPROVAL">PENDING_APPROVAL</option>
                <option value="APPROVED">APPROVED</option>
                <option value="EDITED">EDITED</option>
                <option value="REJECTED">REJECTED</option>
                <option value="VERIFIED">VERIFIED</option>
              </select>
            </div>

            <div className="flex items-center gap-1.5 font-medium text-[#667085]">
              <span>Pattern:</span>
              <select
                value={patternFilter}
                onChange={(e) => setPatternFilter(e.target.value)}
                className="bg-[#F8FAFC] border border-[#D9DEE7] rounded-lg px-2.5 py-1 text-xs text-[#172033] font-semibold focus:outline-none focus:border-[#2563A6]"
              >
                <option value="">All Patterns</option>
                <option value="PATTERN_A_DEVICE_FARM">Pattern A (Device Farm)</option>
                <option value="PATTERN_B_CIRCULAR_LAYERING">Pattern B (Circular Layering)</option>
                <option value="PATTERN_C_SYNTHETIC_VELOCITY">Pattern C (Synthetic Velocity)</option>
                <option value="HARD_NEGATIVE_FESTIVE_SPIKE">Hard Negative (Festive)</option>
                <option value="HARD_NEGATIVE_SHARED_WIFI">Hard Negative (Shared WiFi)</option>
              </select>
            </div>

            {(priorityFilter || statusFilter || patternFilter || search) && (
              <Button
                variant="ghost"
                size="sm"
                icon={<RotateCcw className="w-3 h-3 text-[#C53030]" />}
                onClick={() => {
                  setPriorityFilter('');
                  setStatusFilter('');
                  setPatternFilter('');
                  setSearch('');
                }}
                className="text-[#C53030] hover:bg-red-50"
              >
                Reset Filters
              </Button>
            )}
          </div>
        </div>
      </Card>

      {/* Case Table */}
      <div className="rounded-xl bg-white border border-[#D9DEE7] overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1020px] text-left text-xs font-mono">
            <thead>
              <tr className="bg-[#F8FAFC] border-b border-[#D9DEE7] text-[#667085] text-[11px]">
                <th className="py-3 px-4 font-semibold whitespace-nowrap">Priority</th>
                <th className="py-3 px-4 font-semibold whitespace-nowrap">Case ID</th>
                <th className="py-3 px-4 font-semibold whitespace-nowrap">Customer / Members</th>
                <th className="py-3 px-4 font-semibold whitespace-nowrap">Transaction (INR)</th>
                <th className="py-3 px-4 font-semibold whitespace-nowrap">Decision Score</th>
                <th className="py-3 px-4 font-semibold whitespace-nowrap">Action / Policy</th>
                <th className="py-3 px-4 font-semibold whitespace-nowrap">Status</th>
                <th className="py-3 px-4 font-semibold text-right whitespace-nowrap">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#F1F5F9]">
              {loading ? (
                <tr>
                  <td colSpan={8} className="p-8 text-center text-[#667085]">
                    Loading Risk Cases...
                  </td>
                </tr>
              ) : cases.length === 0 ? (
                <tr>
                  <td colSpan={8} className="p-8 text-center text-[#667085]">
                    No cases match the selected filter criteria.
                  </td>
                </tr>
              ) : (
                cases.map((c) => (
                  <tr
                    key={c.case_id}
                    className="hover:bg-[#F8FAFC] transition-colors cursor-pointer"
                    onClick={() => onSelectCase(c.case_id)}
                  >
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <Badge
                        variant={
                          c.priority === 'CRITICAL'
                            ? 'critical'
                            : c.priority === 'HIGH'
                            ? 'warning'
                            : c.priority === 'MEDIUM'
                            ? 'info'
                            : 'neutral'
                        }
                        size="sm"
                        dot={c.priority === 'CRITICAL'}
                      >
                        {c.priority}
                      </Badge>
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <div className="font-bold text-[#183B67]">{c.case_id}</div>
                      {c.ring_id && (
                        <span className="text-[10px] text-[#2563A6] font-mono">
                          {c.ring_id}
                        </span>
                      )}
                      {c.is_hard_negative && (
                        <span className="text-[10px] text-[#15803D] font-bold font-mono block">
                          Hard Negative
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 font-sans whitespace-nowrap">
                      <div className="text-[#172033] font-semibold">{c.customer_id}</div>
                      <div className="text-[11px] text-[#667085] font-mono">
                        {c.member_count} member{c.member_count > 1 ? 's' : ''} in ring
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-sans whitespace-nowrap">
                      <div className="font-bold text-[#172033]">
                        ₹{c.amount_inr.toLocaleString()}
                      </div>
                      <div className="text-[11px] text-[#667085] font-mono">{c.transaction_id}</div>
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-[#172033]">
                          {c.decision_score.toFixed(3)}
                        </span>
                        <div className="w-14 h-1.5 bg-[#E2E8F0] rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              c.decision_score > 0.7
                                ? 'bg-[#C53030]'
                                : c.decision_score > 0.4
                                ? 'bg-[#B7791F]'
                                : 'bg-[#15803D]'
                            }`}
                            style={{ width: `${Math.min(100, c.decision_score * 100)}%` }}
                          />
                        </div>
                      </div>
                      <div className="text-[10px] text-[#98A2B3]">Tier: {c.tier}</div>
                    </td>
                    <td className="py-3.5 px-4 font-sans whitespace-nowrap">
                      <div className="font-bold text-[#C53030]">
                        {c.final_action || c.recommended_action}
                      </div>
                      <div className="text-[11px] text-[#667085] truncate max-w-[220px]">
                        {c.action_reason}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <Badge
                        variant={
                          c.status === 'APPROVED'
                            ? 'success'
                            : c.status === 'PENDING_APPROVAL'
                            ? 'warning'
                            : c.status === 'EDITED'
                            ? 'secondary'
                            : 'neutral'
                        }
                        size="sm"
                      >
                        {c.status}
                      </Badge>
                    </td>
                    <td className="py-3.5 px-4 text-right whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                      <Button
                        variant="outline"
                        size="sm"
                        iconRight={<ChevronRight className="w-3.5 h-3.5" />}
                        onClick={() => onSelectCase(c.case_id)}
                      >
                        Investigate
                      </Button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
