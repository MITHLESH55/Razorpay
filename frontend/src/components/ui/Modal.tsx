import React, { useEffect } from 'react';
import { X } from 'lucide-react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  children: React.ReactNode;
  footer?: React.ReactNode;
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | '3xl' | '4xl';
  icon?: React.ReactNode;
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  subtitle,
  children,
  footer,
  maxWidth = 'lg',
  icon,
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    }
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const getMaxWidthClass = (): string => {
    switch (maxWidth) {
      case 'sm':
        return 'max-w-sm';
      case 'md':
        return 'max-w-md';
      case 'xl':
        return 'max-w-xl';
      case '2xl':
        return 'max-w-2xl';
      case '3xl':
        return 'max-w-3xl';
      case '4xl':
        return 'max-w-4xl';
      case 'lg':
      default:
        return 'max-w-lg';
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-[#0F172A]/40 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Dialog Positioning */}
      <div className="flex min-h-full items-center justify-center p-4 text-center sm:p-0">
        <div
          className={`relative transform overflow-hidden rounded-xl bg-white text-left shadow-modal transition-all w-full my-8 ${getMaxWidthClass()} border border-[#D9DEE7]`}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-start justify-between px-6 py-4 border-b border-[#D9DEE7] bg-[#F8FAFC]">
            <div className="flex items-center gap-3 min-w-0">
              {icon && (
                <div className="p-2 rounded-lg bg-white border border-[#D9DEE7] text-[#183B67] shrink-0">
                  {icon}
                </div>
              )}
              <div className="min-w-0">
                <h3 className="text-base font-semibold text-[#172033] tracking-tight">{title}</h3>
                {subtitle && <p className="text-xs text-[#667085] mt-0.5">{subtitle}</p>}
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-[#98A2B3] hover:text-[#172033] p-1.5 rounded-lg hover:bg-slate-200/50 transition-colors focus:outline-none"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Body */}
          <div className="px-6 py-5 max-h-[calc(100vh-16rem)] overflow-y-auto">{children}</div>

          {/* Footer */}
          {footer && (
            <div className="flex items-center justify-end gap-3 px-6 py-3.5 border-t border-[#D9DEE7] bg-[#F8FAFC]">
              {footer}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
