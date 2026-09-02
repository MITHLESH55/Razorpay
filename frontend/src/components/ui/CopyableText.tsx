import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';

interface CopyableTextProps {
  text: string;
  displayText?: string;
  className?: string;
  truncateLength?: number;
  label?: string;
}

export const CopyableText: React.FC<CopyableTextProps> = ({
  text,
  displayText,
  className = '',
  truncateLength,
  label,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      // Fallback
    }
  };

  const getTruncated = (str: string) => {
    if (!truncateLength || str.length <= truncateLength) return str;
    const half = Math.floor((truncateLength - 3) / 2);
    return `${str.slice(0, half)}...${str.slice(-half)}`;
  };

  const visibleText = displayText || (truncateLength ? getTruncated(text) : text);

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-mono text-xs text-[#172033] bg-[#F8FAFC] px-2 py-0.5 rounded border border-[#D9DEE7] group hover:border-[#CBD5E1] transition-colors ${className}`}
      title={text}
    >
      {label && <span className="text-[10px] text-[#98A2B3] uppercase font-sans font-semibold">{label}:</span>}
      <span className="truncate">{visibleText}</span>
      <button
        onClick={handleCopy}
        type="button"
        className="text-[#98A2B3] hover:text-[#183B67] transition-colors p-0.5 rounded focus:outline-none"
        title="Copy to clipboard"
      >
        {copied ? (
          <Check className="w-3 h-3 text-emerald-600" />
        ) : (
          <Copy className="w-3 h-3 opacity-70 group-hover:opacity-100" />
        )}
      </button>
    </span>
  );
};
