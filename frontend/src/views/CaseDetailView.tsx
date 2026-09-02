import React, { useEffect, useState } from 'react';
import {
  ArrowLeft,
  ShieldCheck,
  Activity,
  Sliders,
  CheckCircle2,
  MessageSquare,
} from 'lucide-react';
import {
  AuditRecord,
  CaseDetailResponse,
  GraphNode,
  UserContext,
} from '../types';
import { apiService } from '../services/api';
import { CanvasGraph } from '../components/CanvasGraph';
import { EvidenceCard } from '../components/EvidenceCard';
import { DecisionTraceCard } from '../components/DecisionTraceCard';
import { ApprovalGateModal } from '../components/ApprovalGateModal';
import { FeedbackModal } from '../components/FeedbackModal';
import { Badge, Button, Card } from '../components/ui';

interface CaseDetailViewProps {
  caseId: string;
  user: UserContext;
  onBack: () => void;
}

export const CaseDetailView: React.FC<CaseDetailViewProps> = ({ caseId, user, onBack }) => {
  const [data, setData] = useState<CaseDetailResponse | null>(null);
  const [auditEvents, setAuditEvents] = useState<AuditRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  // Modals
  const [isApprovalModalOpen, setIsApprovalModalOpen] = useState(false);
  const [isFeedbackModalOpen, setIsFeedbackModalOpen] = useState(false);
  const [simResult, setSimResult] = useState<any | null>(null);
  const [simLoading, setSimLoading] = useState(false);

  const loadCase = async () => {
    setLoading(true);
    try {
      const [detailData, auditData] = await Promise.all([
        apiService.getCaseDetail(caseId),
        apiService.getAuditTrail(caseId),
      ]);
      setData(detailData);
      setAuditEvents(auditData);
    } catch (err) {
      console.error('Case detail load error', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCase();
  }, [caseId]);

  const handleApprove = async (notes: string) => {
    await apiService.approveCase(caseId, notes);
    await loadCase();
  };

  const handleEdit = async (newAction: string, reason: string) => {
    await apiService.editCaseAction(caseId, newAction, reason);
    await loadCase();
  };

  const handleReject = async (reason: string) => {
    await apiService.rejectCase(caseId, reason);
    await loadCase();
  };

  const handleSubmitFeedback = async (fData: any) => {
    await apiService.submitFeedback({
      case_id: caseId,
      transaction_id: data?.case.transaction_id || '',
      adjudication: fData.adjudication,
      notes: fData.notes,
      evidence_conflict_notes: fData.evidence_conflict_notes,
      suggested_policy_tuning: fData.suggested_policy_tuning,
    });
    await loadCase();
  };

  const handleRunSimulation = async () => {
    setSimLoading(true);
    try {
      const res = await apiService.simulateExecution(caseId);
      setSimResult(res);
      await loadCase();
    } catch (err) {
      console.error('Sim error', err);
    } finally {
      setSimLoading(false);
    }
  };

  if (loading || !data) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="flex items-center gap-3 text-[#667085] font-mono text-xs">
          <Activity className="w-5 h-5 text-[#2563A6] animate-spin" />
          <span>Retrieving Grounded Investigation Dossier...</span>
        </div>
      </div>
    );
  }

  const { case: c, graph, evidence_records, decision_trace, narrative, pattern_name } = data;

  return (
    <div className="space-y-6 pb-16">
      {/* Top Breadcrumb & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <Button
          variant="ghost"
          size="sm"
          icon={<ArrowLeft className="w-4 h-4" />}
          onClick={onBack}
          className="text-[#667085] hover:text-[#172033]"
        >
          Back to Queue
        </Button>

        <div className="flex flex-wrap items-center gap-2">
          {/* Quick Case Switcher for Demonstration */}
          <span className="text-[11px] font-mono text-[#98A2B3]">Demo Evaluation Cases:</span>
          <button
            onClick={() => apiService.getCaseDetail('CASE-RING-A-01').then(() => loadCase())}
            className={`px-2.5 py-1 rounded text-xs font-mono border transition-all ${
              caseId === 'CASE-RING-A-01'
                ? 'bg-red-50 text-[#C53030] border-[#C53030] font-bold'
                : 'bg-white text-[#667085] border-[#D9DEE7] hover:bg-[#F8FAFC]'
            }`}
          >
            Pattern A
          </button>
          <button
            onClick={() => apiService.getCaseDetail('CASE-RING-B-02').then(() => loadCase())}
            className={`px-2.5 py-1 rounded text-xs font-mono border transition-all ${
              caseId === 'CASE-RING-B-02'
                ? 'bg-purple-50 text-purple-700 border-purple-400 font-bold'
                : 'bg-white text-[#667085] border-[#D9DEE7] hover:bg-[#F8FAFC]'
            }`}
          >
            Pattern B
          </button>
          <button
            onClick={() => apiService.getCaseDetail('CASE-HARDNEG-04').then(() => loadCase())}
            className={`px-2.5 py-1 rounded text-xs font-mono border transition-all ${
              caseId === 'CASE-HARDNEG-04'
                ? 'bg-emerald-50 text-[#15803D] border-[#15803D] font-bold'
                : 'bg-white text-[#667085] border-[#D9DEE7] hover:bg-[#F8FAFC]'
            }`}
          >
            Hard Negative
          </button>
        </div>
      </div>

      {/* Case Header Card */}
      <div className="p-6 rounded-2xl bg-white border border-[#D9DEE7] shadow-sm space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2.5">
              <h2 className="text-xl font-bold tracking-tight text-[#172033] font-mono">{c.case_id}</h2>
              <Badge
                variant={
                  c.priority === 'CRITICAL'
                    ? 'critical'
                    : c.priority === 'HIGH'
                    ? 'warning'
                    : 'neutral'
                }
                size="sm"
                dot={c.priority === 'CRITICAL'}
              >
                {c.priority} PRIORITY
              </Badge>
              <Badge
                variant={
                  c.status === 'APPROVED'
                    ? 'success'
                    : c.status === 'PENDING_APPROVAL'
                    ? 'warning'
                    : 'secondary'
                }
                size="sm"
              >
                {c.status} (v{c.version})
              </Badge>
              {c.is_hard_negative && (
                <Badge variant="success" size="sm">
                  Ground-Truth Hard Negative
                </Badge>
              )}
            </div>
            <p className="text-xs text-[#2563A6] font-mono mt-1 font-semibold">{pattern_name}</p>
          </div>

          {/* Quick Metrics */}
          <div className="flex items-center gap-3 text-xs font-mono">
            <div className="bg-[#F8FAFC] px-3.5 py-2 rounded-xl border border-[#D9DEE7] text-right">
              <span className="text-[10px] text-[#98A2B3] uppercase font-bold block">Amount Exposure</span>
              <span className="font-bold text-[#172033]">₹{c.amount_inr.toLocaleString()}</span>
            </div>
            <div className="bg-[#F8FAFC] px-3.5 py-2 rounded-xl border border-[#D9DEE7] text-right">
              <span className="text-[10px] text-[#98A2B3] uppercase font-bold block">Decision Score</span>
              <span className="font-bold text-[#C53030]">{c.decision_score.toFixed(3)}</span>
            </div>
          </div>
        </div>

        {/* Narrative Banner */}
        <div className="p-3.5 rounded-xl bg-[#F8FAFC] border border-[#D9DEE7] text-xs text-[#667085] leading-relaxed font-sans">
          <strong className="text-[#183B67] font-mono font-bold">Executive Summary: </strong>
          {narrative}
        </div>
      </div>

      {/* Main 2-Column Investigation Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
        {/* Left 7-Cols: Canvas Subgraph & Evidence Artifacts */}
        <div className="xl:col-span-7 space-y-6">
          {/* Subtopology Graph */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold text-[#172033] font-mono uppercase tracking-wider">
                Graph Relationship Subtopology
              </h3>
              <span className="text-[11px] text-[#98A2B3] font-mono">Interactive Canvas</span>
            </div>
            <CanvasGraph
              nodes={graph.nodes}
              edges={graph.edges}
              selectedNodeId={selectedNode?.id}
              onSelectNode={(n) => setSelectedNode(n)}
            />
          </div>

          {/* Grounded Evidence Bundle */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold text-[#172033] font-mono uppercase tracking-wider">
                Corroborated Grounded Evidence ({evidence_records.length})
              </h3>
              <Badge variant="success" size="sm">
                Source-Grounded Evidence
              </Badge>
            </div>

            <div className="space-y-3">
              {evidence_records.map((ev) => (
                <EvidenceCard key={ev.evidence_id} evidence={ev} />
              ))}
            </div>
          </div>
        </div>

        {/* Right 5-Cols: Decision Trace, Action Gate & Simulation */}
        <div className="xl:col-span-5 space-y-6">
          {/* 5-Score Trace */}
          <DecisionTraceCard trace={decision_trace} />

          {/* Action Gate Card */}
          <div className="p-5 rounded-2xl bg-white border border-[#D9DEE7] shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-[#2563A6]" />
                <h3 className="text-xs font-bold text-[#172033] font-mono uppercase tracking-wider">
                  Human Approval Gate
                </h3>
              </div>
              <span className="text-[10px] font-mono text-[#667085]">
                Role: <strong className="text-[#183B67]">{user.role}</strong>
              </span>
            </div>

            <div className="p-3.5 rounded-xl bg-[#F8FAFC] border border-[#D9DEE7] space-y-2 text-xs font-mono">
              <div className="flex justify-between items-center">
                <span className="text-[#667085]">Recommended Action:</span>
                <span className="font-bold text-[#C53030]">{c.recommended_action}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[#667085]">Final Resolved Action:</span>
                <span className="font-bold text-[#172033]">{c.final_action || '—'}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-[#667085]">Friction Cost INR:</span>
                <span className="text-[#183B67] font-bold">
                  ₹{c.expected_friction_cost_inr.toLocaleString()}
                </span>
              </div>
              {c.reviewed_by && (
                <div className="pt-2 border-t border-[#D9DEE7] text-[11px] text-[#667085]">
                  Reviewed by <strong className="text-[#172033]">{c.reviewed_by}</strong> at{' '}
                  {c.reviewed_at?.slice(0, 19).replace('T', ' ')}
                  {c.reviewer_notes && (
                    <div className="text-[#667085] italic mt-0.5">"{c.reviewer_notes}"</div>
                  )}
                </div>
              )}
            </div>

            {/* Action Buttons */}
            <div className="space-y-2 font-mono">
              <Button
                variant="primary"
                size="md"
                fullWidth
                icon={<ShieldCheck className="w-4 h-4" />}
                onClick={() => setIsApprovalModalOpen(true)}
              >
                Open Human Approval Gate
              </Button>

              <div className="grid grid-cols-2 gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  icon={<Sliders className="w-3.5 h-3.5 text-[#2563A6]" />}
                  onClick={handleRunSimulation}
                  disabled={simLoading}
                >
                  {simLoading ? 'Simulating...' : 'Run Simulation'}
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  icon={<MessageSquare className="w-3.5 h-3.5 text-purple-600" />}
                  onClick={() => setIsFeedbackModalOpen(true)}
                >
                  Adjudicate
                </Button>
              </div>
            </div>

            {/* Simulation Feedback Result */}
            {simResult && (
              <div className="p-3 rounded-xl bg-blue-50/60 border border-blue-200 text-[#183B67] text-xs font-mono space-y-1">
                <div className="font-bold flex items-center gap-1.5 text-[#2563A6]">
                  <CheckCircle2 className="w-3.5 h-3.5 text-[#15803D]" />
                  Simulation Result Verified
                </div>
                <div className="text-[11px] text-[#667085]">
                  Prevented Loss: ₹{simResult.prevented_loss_inr.toLocaleString()} | Friction Cost: ₹
                  {simResult.projected_friction_cost_inr.toLocaleString()} | Modeled Net Protection: ₹
                  {simResult.net_recovery_inr.toLocaleString()}
                </div>
              </div>
            )}
          </div>

          {/* Case Audit Timeline */}
          <Card
            title="Case Audit History"
            subtitle="Immutable chronological trail"
            headerRight={<Badge variant="neutral" size="sm">Tamper-Evident</Badge>}
          >
            <div className="space-y-2 font-mono text-xs">
              {auditEvents.length === 0 ? (
                <p className="text-[#98A2B3] text-xs">No prior modifications recorded.</p>
              ) : (
                auditEvents.map((ev) => (
                  <div
                    key={ev.event_id}
                    className="p-2.5 rounded-lg bg-[#F8FAFC] border border-[#D9DEE7] space-y-1"
                  >
                    <div className="flex justify-between items-center text-[10px]">
                      <span className="font-bold text-[#183B67]">{ev.event_type}</span>
                      <span className="text-[#98A2B3]">
                        {ev.timestamp.slice(11, 19)} ({ev.actor_role})
                      </span>
                    </div>
                    <div className="text-[11px] text-[#667085]">
                      Actor: <span className="text-[#172033] font-semibold">{ev.actor_id}</span>
                      {ev.new_state && <span> &rarr; State: <strong>{ev.new_state}</strong></span>}
                    </div>
                  </div>
                ))
              )}
            </div>
          </Card>
        </div>
      </div>

      {/* Modals */}
      <ApprovalGateModal
        isOpen={isApprovalModalOpen}
        onClose={() => setIsApprovalModalOpen(false)}
        caseRecord={c}
        user={user}
        onApprove={handleApprove}
        onEdit={handleEdit}
        onReject={handleReject}
      />

      <FeedbackModal
        isOpen={isFeedbackModalOpen}
        onClose={() => setIsFeedbackModalOpen(false)}
        caseRecord={c}
        user={user}
        onSubmitFeedback={handleSubmitFeedback}
      />
    </div>
  );
};
