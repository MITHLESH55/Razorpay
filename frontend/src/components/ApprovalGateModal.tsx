import React, { useState } from 'react';
import {
  ShieldAlert,
  AlertTriangle,
  Send,
  X,
} from 'lucide-react';
import { RiskCaseRecord, UserContext } from '../types';
import { Badge, Button } from './ui';

interface ApprovalGateModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseRecord: RiskCaseRecord;
  user: UserContext;
  onApprove: (notes: string) => Promise<void>;
  onEdit: (newAction: string, reason: string) => Promise<void>;
  onReject: (reason: string) => Promise<void>;
}

export const ApprovalGateModal: React.FC<ApprovalGateModalProps> = ({
  isOpen,
  onClose,
  caseRecord,
  user,
  onApprove,
  onEdit,
  onReject,
}) => {
  const [mode, setMode] = useState<'APPROVE' | 'EDIT' | 'REJECT'>('APPROVE');
  const [notes, setNotes] = useState('');
  const [overrideAction, setOverrideAction] = useState('STEP_UP_2FA');
  const [overrideReason, setOverrideReason] = useState('');
  const [rejectReason, setRejectReason] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const isSeniorOrAdmin = user.role === 'SENIOR_ANALYST' || user.role === 'ADMIN';
  const isViewer = user.role === 'VIEWER';

  const handleSubmit = async () => {
    setError(null);
    setLoading(true);
    try {
      if (mode === 'APPROVE') {
        await onApprove(notes);
      } else if (mode === 'EDIT') {
        if (!overrideReason.trim()) {
          setError('Override reason is required.');
          setLoading(false);
          return;
        }
        await onEdit(overrideAction, overrideReason);
      } else if (mode === 'REJECT') {
        if (!rejectReason.trim()) {
          setError('Rejection reason is required.');
          setLoading(false);
          return;
        }
        await onReject(rejectReason);
      }
      onClose();
    } catch (err: any) {
      setError(err.message || 'Operation failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in">
      <div className="bg-white border border-[#D9DEE7] rounded-2xl max-w-lg w-full p-6 space-y-5 shadow-2xl relative font-sans">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-[#667085] hover:text-[#172033] hover:bg-[#F8FAFC] transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-[#F8FAFC] border border-[#D9DEE7] text-[#183B67]">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-base font-bold text-[#172033]">Human Approval Gate</h3>
            <p className="text-xs font-mono text-[#667085]">
              Case {caseRecord.case_id} — Version v{caseRecord.version}
            </p>
          </div>
        </div>

        {/* Current Recommendation Summary */}
        <div className="p-3.5 rounded-xl bg-[#F8FAFC] border border-[#D9DEE7] space-y-2 text-xs font-mono">
          <div className="flex justify-between items-center">
            <span className="text-[#667085]">Proposed Action:</span>
            <Badge variant="critical" size="sm">
              {caseRecord.recommended_action}
            </Badge>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-[#667085]">Decision Score:</span>
            <span className="font-bold text-[#172033]">{caseRecord.decision_score.toFixed(3)}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-[#667085]">Transaction Amount:</span>
            <span className="font-bold text-[#172033]">
              ₹{caseRecord.amount_inr.toLocaleString()}
            </span>
          </div>
        </div>

        {/* Mode Selector */}
        <div className="flex rounded-lg bg-[#F8FAFC] p-1 border border-[#D9DEE7] text-xs font-mono">
          <button
            onClick={() => setMode('APPROVE')}
            className={`flex-1 py-1.5 rounded-md font-semibold transition-all ${
              mode === 'APPROVE'
                ? 'bg-[#15803D] text-white shadow-sm'
                : 'text-[#667085] hover:text-[#172033]'
            }`}
          >
            Approve Action
          </button>
          <button
            onClick={() => setMode('EDIT')}
            disabled={!isSeniorOrAdmin}
            className={`flex-1 py-1.5 rounded-md font-semibold transition-all ${
              mode === 'EDIT'
                ? 'bg-[#B7791F] text-white shadow-sm'
                : !isSeniorOrAdmin
                ? 'text-[#98A2B3] cursor-not-allowed opacity-50'
                : 'text-[#667085] hover:text-[#172033]'
            }`}
          >
            Override (Sr.)
          </button>
          <button
            onClick={() => setMode('REJECT')}
            disabled={isViewer}
            className={`flex-1 py-1.5 rounded-md font-semibold transition-all ${
              mode === 'REJECT'
                ? 'bg-[#C53030] text-white shadow-sm'
                : isViewer
                ? 'text-[#98A2B3] cursor-not-allowed opacity-50'
                : 'text-[#667085] hover:text-[#172033]'
            }`}
          >
            Reject / Clear
          </button>
        </div>

        {/* Input Fields based on Mode */}
        {mode === 'APPROVE' && (
          <div className="space-y-2">
            <label className="block text-xs font-semibold text-[#172033] font-mono">
              Reviewer Approval Notes (Optional):
            </label>
            <textarea
              rows={3}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="e.g., Reviewed ring graph evidence and corroborated emulator fingerprint."
              className="w-full bg-[#F8FAFC] border border-[#D9DEE7] rounded-lg p-2.5 text-xs text-[#172033] placeholder-[#98A2B3] focus:bg-white focus:outline-none focus:border-[#2563A6] focus:ring-1 focus:ring-[#2563A6] font-sans"
            />
          </div>
        )}

        {mode === 'EDIT' && (
          <div className="space-y-3 font-mono text-xs">
            <div>
              <label className="block text-[#172033] font-semibold mb-1">Select New Action:</label>
              <select
                value={overrideAction}
                onChange={(e) => setOverrideAction(e.target.value)}
                className="w-full bg-[#F8FAFC] border border-[#D9DEE7] rounded-lg p-2 text-[#172033] font-semibold focus:outline-none focus:border-[#2563A6]"
              >
                <option value="STEP_UP_2FA">STEP_UP_2FA (Proportional Friction)</option>
                <option value="DELAY_SETTLEMENT">DELAY_SETTLEMENT (4h Hold)</option>
                <option value="MANUAL_REVIEW">MANUAL_REVIEW (Escalate)</option>
                <option value="RESTRICT_ACCOUNT">RESTRICT_ACCOUNT (Temporary)</option>
                <option value="BLOCK_TRANSACTION">BLOCK_TRANSACTION (Hard Block)</option>
                <option value="FREEZE_RING">FREEZE_RING (All Ring Members)</option>
                <option value="ALLOW">ALLOW (Clear Transaction)</option>
              </select>
            </div>
            <div>
              <label className="block text-[#172033] font-semibold mb-1">
                Mandatory Override Justification:
              </label>
              <textarea
                rows={2}
                value={overrideReason}
                onChange={(e) => setOverrideReason(e.target.value)}
                placeholder="Detail reason for policy override..."
                className="w-full bg-[#F8FAFC] border border-[#D9DEE7] rounded-lg p-2 text-xs text-[#172033] placeholder-[#98A2B3] focus:bg-white focus:outline-none focus:border-[#2563A6] font-sans"
              />
            </div>
          </div>
        )}

        {mode === 'REJECT' && (
          <div className="space-y-2">
            <label className="block text-xs font-semibold text-[#172033] font-mono">
              Mandatory Rejection Justification (Falls back to ALLOW):
            </label>
            <textarea
              rows={3}
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="e.g., False positive investigation; verified corporate festive purchase."
              className="w-full bg-[#F8FAFC] border border-[#D9DEE7] rounded-lg p-2.5 text-xs text-[#172033] placeholder-[#98A2B3] focus:bg-white focus:outline-none focus:border-[#C53030] font-sans"
            />
          </div>
        )}

        {/* Error notice */}
        {error && (
          <div className="p-2.5 rounded-lg bg-red-50 border border-red-200 text-[#C53030] text-xs font-mono flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 flex-shrink-0 text-[#C53030]" />
            <span>{error}</span>
          </div>
        )}

        {/* Footer Actions */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <Button variant="outline" size="md" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button
            variant={mode === 'APPROVE' ? 'primary' : mode === 'EDIT' ? 'warning' : 'danger'}
            size="md"
            icon={<Send className="w-3.5 h-3.5" />}
            onClick={handleSubmit}
            disabled={loading || isViewer}
          >
            {loading
              ? 'Executing...'
              : mode === 'APPROVE'
              ? 'Confirm & Sign Approval'
              : mode === 'EDIT'
              ? 'Execute Override'
              : 'Confirm Rejection'}
          </Button>
        </div>
      </div>
    </div>
  );
};
