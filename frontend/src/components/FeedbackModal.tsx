import React, { useState } from 'react';
import {
  MessageSquare,
  Lock,
  X,
  Send,
  ThumbsUp,
  ThumbsDown,
  HelpCircle,
  Sliders,
} from 'lucide-react';
import { RiskCaseRecord, UserContext } from '../types';
import { Button } from './ui';

interface FeedbackModalProps {
  isOpen: boolean;
  onClose: () => void;
  caseRecord: RiskCaseRecord;
  user: UserContext;
  onSubmitFeedback: (data: {
    adjudication: string;
    notes?: string;
    evidence_conflict_notes?: string;
    suggested_policy_tuning?: string;
  }) => Promise<void>;
}

export const FeedbackModal: React.FC<FeedbackModalProps> = ({
  isOpen,
  onClose,
  caseRecord,
  user,
  onSubmitFeedback,
}) => {
  const [adjudication, setAdjudication] = useState<'TRUE_POSITIVE' | 'FALSE_POSITIVE' | 'NEEDS_REVIEW'>('TRUE_POSITIVE');
  const [notes, setNotes] = useState('');
  const [conflictNotes, setConflictNotes] = useState('');
  const [policyTuning, setPolicyTuning] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async () => {
    setError(null);
    setLoading(true);
    try {
      await onSubmitFeedback({
        adjudication,
        notes,
        evidence_conflict_notes: conflictNotes,
        suggested_policy_tuning: policyTuning,
      });
      onClose();
    } catch (err: any) {
      setError(err.message || 'Submission failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in">
      <div className="bg-white border border-[#D9DEE7] rounded-2xl max-w-lg w-full p-6 space-y-5 shadow-2xl relative font-sans max-h-[90vh] overflow-y-auto">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-[#667085] hover:text-[#172033] hover:bg-[#F8FAFC] transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Header */}
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-purple-50 border border-purple-200 text-purple-700">
            <MessageSquare className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-base font-bold text-[#172033]">Analyst Domain Adjudication</h3>
            <p className="text-xs font-mono text-[#667085]">
              Adjudicating as <strong className="text-[#172033]">{user.name}</strong> ({user.role}) &bull; Case {caseRecord.case_id}
            </p>
          </div>
        </div>

        {/* Model Freeze Invariant Banner */}
        <div className="flex items-center gap-2.5 p-3 rounded-xl bg-indigo-50/60 border border-indigo-200 text-[#183B67] text-xs font-mono">
          <Lock className="w-4 h-4 text-[#2563A6] flex-shrink-0" />
          <span>
            Invariant: Feedback is stored in offline dataset. Active production models remain frozen.
          </span>
        </div>

        {/* Adjudication Selector Buttons */}
        <div className="space-y-2">
          <label className="block text-xs font-semibold text-[#172033] font-mono">
            Adjudication Classification:
          </label>
          <div className="grid grid-cols-3 gap-2 font-mono text-xs">
            <button
              onClick={() => setAdjudication('TRUE_POSITIVE')}
              className={`p-3 rounded-lg border flex flex-col items-center gap-1.5 transition-all ${
                adjudication === 'TRUE_POSITIVE'
                  ? 'bg-red-50 text-[#C53030] border-[#C53030] font-bold shadow-xs'
                  : 'bg-[#F8FAFC] text-[#667085] border-[#D9DEE7] hover:text-[#172033] hover:bg-white'
              }`}
            >
              <ThumbsUp className="w-4 h-4 text-[#C53030]" />
              <span>True Positive</span>
            </button>
            <button
              onClick={() => setAdjudication('FALSE_POSITIVE')}
              className={`p-3 rounded-lg border flex flex-col items-center gap-1.5 transition-all ${
                adjudication === 'FALSE_POSITIVE'
                  ? 'bg-emerald-50 text-[#15803D] border-[#15803D] font-bold shadow-xs'
                  : 'bg-[#F8FAFC] text-[#667085] border-[#D9DEE7] hover:text-[#172033] hover:bg-white'
              }`}
            >
              <ThumbsDown className="w-4 h-4 text-[#15803D]" />
              <span>False Positive</span>
            </button>
            <button
              onClick={() => setAdjudication('NEEDS_REVIEW')}
              className={`p-3 rounded-lg border flex flex-col items-center gap-1.5 transition-all ${
                adjudication === 'NEEDS_REVIEW'
                  ? 'bg-amber-50 text-[#B7791F] border-[#B7791F] font-bold shadow-xs'
                  : 'bg-[#F8FAFC] text-[#667085] border-[#D9DEE7] hover:text-[#172033] hover:bg-white'
              }`}
            >
              <HelpCircle className="w-4 h-4 text-[#B7791F]" />
              <span>Needs Review</span>
            </button>
          </div>
        </div>

        {/* Notes */}
        <div className="space-y-2">
          <label className="block text-xs font-semibold text-[#172033] font-mono">
            Analyst Investigation Notes:
          </label>
          <textarea
            rows={2}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Ground-truth rationale and findings..."
            className="w-full bg-[#F8FAFC] border border-[#D9DEE7] rounded-lg p-2.5 text-xs text-[#172033] placeholder-[#98A2B3] focus:bg-white focus:outline-none focus:border-purple-600 font-sans"
          />
        </div>

        {/* Evidence Conflict Notes */}
        <div className="space-y-2">
          <label className="block text-xs font-semibold text-[#172033] font-mono">
            Evidence Conflict Observations (Optional):
          </label>
          <textarea
            rows={2}
            value={conflictNotes}
            onChange={(e) => setConflictNotes(e.target.value)}
            placeholder="e.g. KYC verified by enterprise team despite emulator signature..."
            className="w-full bg-[#F8FAFC] border border-[#D9DEE7] rounded-lg p-2.5 text-xs text-[#172033] placeholder-[#98A2B3] focus:bg-white focus:outline-none focus:border-purple-600 font-sans"
          />
        </div>

        {/* Suggested Policy Tuning */}
        <div className="space-y-2">
          <label className="flex items-center gap-1.5 text-xs font-semibold text-[#172033] font-mono">
            <Sliders className="w-3.5 h-3.5 text-purple-600" />
            <span>Suggested Policy / Rule Tuning (Optional):</span>
          </label>
          <textarea
            rows={2}
            value={policyTuning}
            onChange={(e) => setPolicyTuning(e.target.value)}
            placeholder="e.g. Adjust emulator velocity threshold for trusted merchant categories..."
            className="w-full bg-[#F8FAFC] border border-[#D9DEE7] rounded-lg p-2.5 text-xs text-[#172033] placeholder-[#98A2B3] focus:bg-white focus:outline-none focus:border-purple-600 font-sans"
          />
        </div>

        {error && (
          <div className="p-2.5 rounded-lg bg-red-50 border border-red-200 text-[#C53030] text-xs font-mono">
            {error}
          </div>
        )}

        <div className="flex items-center justify-end gap-3 pt-2">
          <Button variant="outline" size="md" onClick={onClose} disabled={loading}>
            Cancel
          </Button>
          <Button
            variant="purple"
            size="md"
            icon={<Send className="w-3.5 h-3.5" />}
            onClick={handleSubmit}
            disabled={loading}
          >
            {loading ? 'Recording...' : 'Submit Adjudication'}
          </Button>
        </div>
      </div>
    </div>
  );
};
