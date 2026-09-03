import React, { useState } from 'react';
import {
  CheckCircle2,
  Shield,
  Fingerprint,
  Gauge,
  MapPin,
  FileCode,
  Copy,
  Check,
} from 'lucide-react';
import { EvidenceItem } from '../types';
import { Badge } from './ui';

interface EvidenceCardProps {
  evidence: EvidenceItem;
}

export const EvidenceCard: React.FC<EvidenceCardProps> = ({ evidence }) => {
  const [copied, setCopied] = useState(false);

  const copyHash = () => {
    navigator.clipboard.writeText(evidence.hash_sha256);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getCategoryIcon = () => {
    switch (evidence.category) {
      case 'DEVICE_COLLUSION':
        return <Fingerprint className="w-4 h-4 text-[#B7791F]" />;
      case 'VELOCITY_ANOMALY':
        return <Gauge className="w-4 h-4 text-[#C53030]" />;
      case 'GEO_IMPOSSIBILITY':
        return <MapPin className="w-4 h-4 text-purple-600" />;
      default:
        return <Shield className="w-4 h-4 text-[#2563A6]" />;
    }
  };

  return (
    <div className="bg-white rounded-xl border border-[#D9DEE7] p-4 space-y-3 shadow-xs hover:border-[#2563A6]/60 transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-[#F8FAFC] border border-[#D9DEE7]">
            {getCategoryIcon()}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold text-[#183B67]">
                {evidence.evidence_id}
              </span>
              {evidence.verified && evidence.source_type !== 'FROZEN_EVALUATION_FIXTURE' && (
                <Badge variant="success" size="sm" icon={<CheckCircle2 className="w-3 h-3 text-[#15803D]" />}>
                  Grounded & Verified
                </Badge>
              )}
              {evidence.source_type === 'FROZEN_EVALUATION_FIXTURE' && (
                <Badge variant="info" size="sm">Frozen Evaluation Evidence</Badge>
              )}
            </div>
            <h4 className="text-xs font-bold text-[#172033] mt-0.5">{evidence.title}</h4>
          </div>
        </div>

        {/* Strength Meter */}
        <div className="text-right">
          <div className="text-xs font-mono font-bold text-[#172033]">
            {(evidence.strength * 100).toFixed(0)}%
          </div>
          <div className="w-16 h-1.5 bg-[#E2E8F0] rounded-full overflow-hidden mt-1">
            <div
              className={`h-full rounded-full ${
                evidence.strength > 0.8
                  ? 'bg-[#C53030]'
                  : evidence.strength > 0.5
                  ? 'bg-[#B7791F]'
                  : 'bg-[#15803D]'
              }`}
              style={{ width: `${evidence.strength * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* Description Narrative */}
      <p className="text-xs text-[#667085] leading-relaxed bg-[#F8FAFC] p-2.5 rounded-lg border border-[#D9DEE7] font-sans">
        {evidence.description}
      </p>

      {/* Structured Features Grid */}
      {evidence.features && Object.keys(evidence.features).length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs font-mono">
          {Object.entries(evidence.features).map(([key, val]) => (
            <div
              key={key}
              className="bg-[#F8FAFC] p-2 rounded-lg border border-[#E2E8F0] flex flex-col"
            >
              <span className="text-[10px] text-[#98A2B3] uppercase">{key.replace(/_/g, ' ')}</span>
              <span className="text-[#172033] font-bold truncate">
                {typeof val === 'boolean' ? (val ? 'TRUE' : 'FALSE') : String(val)}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Cryptographic Hash Signature */}
      <div className="flex items-center justify-between pt-2 text-[11px] font-mono text-[#667085] border-t border-[#F1F5F9]">
        <div className="flex items-center gap-1.5 truncate">
          <FileCode className="w-3.5 h-3.5 text-[#98A2B3]" />
          <span className="text-[#98A2B3]">SHA-256:</span>
          <span className="text-[#667085] truncate max-w-[240px]">
            {evidence.hash_sha256}
          </span>
        </div>
        <button
          onClick={copyHash}
          className="flex items-center gap-1 text-[#2563A6] hover:text-[#183B67] transition-colors"
          title="Copy Hash"
        >
          {copied ? <Check className="w-3 h-3 text-[#15803D]" /> : <Copy className="w-3 h-3" />}
          <span className="text-[10px] font-semibold">{copied ? 'Copied' : 'Copy'}</span>
        </button>
      </div>
    </div>
  );
};
