import React from 'react';
import { Modal } from './ui';
import { KeyRound, Mail, ShieldCheck } from 'lucide-react';

interface ForgotPasswordModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ForgotPasswordModal: React.FC<ForgotPasswordModalProps> = ({
  isOpen,
  onClose,
}) => {
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Enterprise Password Recovery Policy"
      subtitle="Password management is governed by your enterprise Identity Provider (IdP)"
      maxWidth="lg"
      icon={<KeyRound className="w-5 h-5 text-[#183B67]" />}
    >
      <div className="space-y-4">
        {/* Credential Guide Card */}
        <div className="p-4 rounded-xl bg-[#F8FAFC] border border-[#D9DEE7] space-y-2">
          <h4 className="text-xs font-bold text-[#172033] flex items-center gap-2">
            <Mail className="w-4 h-4 text-[#2563A6]" />
            Identity Provider & SSO Managed
          </h4>
          <p className="text-xs text-[#667085] leading-relaxed">
            RiskOrbit integrates with enterprise identity directories (Okta, Azure AD, Google Workspace). Password changes, multi-factor authentication (MFA) resets, and account unblocking must be initiated through your corporate identity provider self-service portal.
          </p>
        </div>

        {/* Helpdesk Contact */}
        <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex items-start gap-2.5 text-xs text-[#667085]">
          <ShieldCheck className="w-4 h-4 text-[#183B67] shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-[#172033]">Security & Governance Assistance</p>
            <p className="text-[11.5px] mt-0.5 leading-relaxed">
              For emergency account unlocks, hardware token provisioning, or RBAC permission changes, contact Risk Infrastructure Support at{' '}
              <span className="font-mono text-[#2563A6] font-semibold">security-ops@riskorbit.internal</span>.
            </p>
          </div>
        </div>

        {/* Modal Close Button */}
        <div className="pt-2 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-[#172033] bg-white hover:bg-[#F8FAFC] border border-[#D9DEE7] rounded-lg transition-colors shadow-xs"
          >
            Close
          </button>
        </div>
      </div>
    </Modal>
  );
};
