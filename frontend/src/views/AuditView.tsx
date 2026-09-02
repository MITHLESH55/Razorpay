import React, { useEffect, useState } from 'react';
import {
  Search,
  Lock,
  ChevronDown,
  ChevronRight,
  Activity,
} from 'lucide-react';
import { AuditRecord, UserContext } from '../types';
import { apiService } from '../services/api';
import { Badge, Button, Card } from '../components/ui';

interface AuditViewProps {
  user: UserContext;
}

export const AuditView: React.FC<AuditViewProps> = () => {
  const [events, setEvents] = useState<AuditRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [eventTypeFilter, setEventTypeFilter] = useState('');
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null);

  const fetchAuditEvents = async () => {
    setLoading(true);
    try {
      const data = await apiService.getAuditTrail(search || undefined, 100);
      setEvents(data);
    } catch (err) {
      console.error('Audit trail load error', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditEvents();
  }, [eventTypeFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchAuditEvents();
  };

  const filteredEvents = events.filter((ev) => {
    if (eventTypeFilter && ev.event_type !== eventTypeFilter) return false;
    return true;
  });

  return (
    <div className="space-y-6 pb-16 font-sans">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 bg-white rounded-2xl border border-[#D9DEE7] shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <Badge variant="navy" size="sm">
              IMMUTABLE AUDIT TRAIL
            </Badge>
            <span className="text-xs font-mono text-[#667085]">Append-Only JSONL Record</span>
          </div>
          <h1 className="text-xl font-bold tracking-tight text-[#172033] mt-1">
            Forensic Audit & Action Ledger
          </h1>
          <p className="text-xs text-[#667085] font-mono mt-0.5">
            Cryptographically timestamped chronological history of all case lifecycle transitions and
            human approvals.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono text-[#667085]">
          <Badge variant="success" size="sm" icon={<Lock className="w-3.5 h-3.5 text-[#15803D]" />}>
            Tamper-Evident Ledger
          </Badge>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <Card>
        <div className="space-y-3">
          <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row gap-2">
            <div className="relative flex-1">
              <Search className="w-4 h-4 absolute left-3 top-2.5 text-[#98A2B3] pointer-events-none" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by Case ID (e.g. CASE-RING-A-01) or Actor..."
                className="w-full bg-[#F8FAFC] border border-[#D9DEE7] rounded-lg pl-9 pr-4 py-2 text-xs text-[#172033] placeholder-[#98A2B3] focus:bg-white focus:outline-none focus:ring-2 focus:ring-[#2563A6]/20 focus:border-[#2563A6] transition-all font-mono"
              />
            </div>
            <Button type="submit" variant="primary" size="md">
              Search Ledger
            </Button>
          </form>

          <div className="flex flex-wrap items-center gap-3 text-xs font-mono">
            <span className="text-[#667085]">Filter Event Type:</span>
            <select
              value={eventTypeFilter}
              onChange={(e) => setEventTypeFilter(e.target.value)}
              className="bg-[#F8FAFC] border border-[#D9DEE7] rounded-lg px-2.5 py-1 text-xs text-[#172033] font-semibold focus:outline-none focus:border-[#2563A6]"
            >
              <option value="">All Event Types</option>
              <option value="CASE_CREATED">CASE_CREATED</option>
              <option value="APPROVAL">APPROVAL</option>
              <option value="OVERRIDE">OVERRIDE</option>
              <option value="REJECTION">REJECTION</option>
              <option value="FEEDBACK_RECORDED">FEEDBACK_RECORDED</option>
              <option value="SIMULATION_EXECUTED">SIMULATION_EXECUTED</option>
            </select>
          </div>
        </div>
      </Card>

      {/* Audit Event Timeline Table */}
      <div className="rounded-xl bg-white border border-[#D9DEE7] overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[960px] text-left text-xs font-mono">
            <thead>
              <tr className="bg-[#F8FAFC] border-b border-[#D9DEE7] text-[#667085] text-[11px]">
                <th className="p-3.5 font-semibold whitespace-nowrap">Timestamp (UTC)</th>
                <th className="p-3.5 font-semibold whitespace-nowrap">Event Type</th>
                <th className="p-3.5 font-semibold whitespace-nowrap">Case ID</th>
                <th className="p-3.5 font-semibold whitespace-nowrap">Actor / Role</th>
                <th className="p-3.5 font-semibold whitespace-nowrap">State Transition</th>
                <th className="p-3.5 font-semibold whitespace-nowrap">Notes / Justification</th>
                <th className="p-3.5 font-semibold text-right whitespace-nowrap">Payload</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#F1F5F9]">
              {loading ? (
                <tr>
                  <td colSpan={7} className="p-8 text-center text-[#667085]">
                    <div className="flex items-center justify-center gap-2">
                      <Activity className="w-4 h-4 text-[#2563A6] animate-spin" />
                      <span>Loading forensic ledger...</span>
                    </div>
                  </td>
                </tr>
              ) : filteredEvents.length === 0 ? (
                <tr>
                  <td colSpan={7} className="p-8 text-center text-[#667085]">
                    No audit records matching query.
                  </td>
                </tr>
              ) : (
                filteredEvents.map((ev) => {
                  const isExpanded = expandedEventId === ev.event_id;
                  return (
                    <React.Fragment key={ev.event_id}>
                      <tr
                        className="hover:bg-[#F8FAFC] transition-colors cursor-pointer"
                        onClick={() =>
                          setExpandedEventId(isExpanded ? null : ev.event_id)
                        }
                      >
                        <td className="p-3.5 text-[#667085] whitespace-nowrap">
                          {ev.timestamp.slice(0, 19).replace('T', ' ')}
                        </td>
                        <td className="p-3.5 whitespace-nowrap">
                          <Badge
                            variant={
                              ev.event_type === 'APPROVAL'
                                ? 'success'
                                : ev.event_type === 'OVERRIDE'
                                ? 'warning'
                                : ev.event_type === 'REJECTION'
                                ? 'critical'
                                : 'neutral'
                            }
                            size="sm"
                          >
                            {ev.event_type}
                          </Badge>
                        </td>
                        <td className="p-3.5 font-bold text-[#183B67] whitespace-nowrap">{ev.case_id}</td>
                        <td className="p-3.5 text-[#172033] whitespace-nowrap">
                          <div>{ev.actor_id}</div>
                          <div className="text-[10px] text-[#98A2B3]">{ev.actor_role}</div>
                        </td>
                        <td className="p-3.5 text-[#667085] whitespace-nowrap">
                          {ev.previous_state ? (
                            <span>
                              {ev.previous_state} &rarr;{' '}
                              <strong className="text-[#172033]">{ev.new_state}</strong>
                            </span>
                          ) : (
                            <strong className="text-[#172033]">{ev.new_state}</strong>
                          )}
                        </td>
                        <td className="p-3.5 text-[#667085] max-w-[240px] truncate">
                          {ev.notes || ev.reason || '—'}
                        </td>
                        <td className="p-3.5 text-right text-[#98A2B3] whitespace-nowrap">
                          {isExpanded ? (
                            <ChevronDown className="w-4 h-4 ml-auto text-[#2563A6]" />
                          ) : (
                            <ChevronRight className="w-4 h-4 ml-auto" />
                          )}
                        </td>
                      </tr>

                      {/* Expandable JSON details */}
                      {isExpanded && (
                        <tr className="bg-[#F8FAFC]">
                          <td colSpan={7} className="p-4">
                            <div className="space-y-2">
                              <div className="flex items-center justify-between text-[11px] text-[#667085]">
                                <span>Event ID: {ev.event_id}</span>
                                <span>Policy: {ev.policy_version}</span>
                              </div>
                              <pre className="p-3 rounded-lg bg-white border border-[#D9DEE7] text-[11px] text-[#183B67] overflow-x-auto font-mono shadow-xs">
                                {JSON.stringify(ev, null, 2)}
                              </pre>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
