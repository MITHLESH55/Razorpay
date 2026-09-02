import React from 'react';

export type BadgeVariant =
  | 'critical'
  | 'high'
  | 'medium'
  | 'low'
  | 'primary'
  | 'secondary'
  | 'isolated'
  | 'success'
  | 'warning'
  | 'danger'
  | 'info'
  | 'neutral'
  | 'navy'
  | 'purple'
  | 'blue'
  | 'red'
  | 'green'
  | 'gray';

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  size?: 'sm' | 'md';
  className?: string;
  icon?: React.ReactNode;
  dot?: boolean;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'neutral',
  size = 'md',
  className = '',
  icon,
  dot = false,
}) => {
  const getVariantStyles = (): string => {
    switch (variant) {
      case 'critical':
      case 'danger':
      case 'red':
        return 'bg-red-50 text-[#C53030] border-red-200';
      case 'high':
      case 'warning':
        return 'bg-amber-50 text-[#B7791F] border-amber-200';
      case 'medium':
        return 'bg-amber-50/70 text-amber-700 border-amber-200';
      case 'low':
      case 'success':
      case 'green':
        return 'bg-emerald-50 text-[#15803D] border-emerald-200';
      case 'primary':
      case 'info':
      case 'blue':
        return 'bg-blue-50 text-[#2563A6] border-blue-200';
      case 'navy':
        return 'bg-slate-100 text-[#183B67] border-slate-300 font-semibold';
      case 'secondary':
      case 'purple':
        return 'bg-purple-50 text-purple-800 border-purple-200';
      case 'isolated':
      case 'gray':
      case 'neutral':
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  const getDotStyles = (): string => {
    switch (variant) {
      case 'critical':
      case 'danger':
      case 'red':
        return 'bg-[#C53030]';
      case 'high':
      case 'warning':
        return 'bg-[#B7791F]';
      case 'medium':
        return 'bg-amber-400';
      case 'low':
      case 'success':
      case 'green':
        return 'bg-[#15803D]';
      case 'primary':
      case 'info':
      case 'blue':
        return 'bg-[#2563A6]';
      case 'navy':
        return 'bg-[#183B67]';
      case 'secondary':
      case 'purple':
        return 'bg-purple-600';
      case 'isolated':
      case 'gray':
      case 'neutral':
      default:
        return 'bg-slate-400';
    }
  };

  const sizeStyles = size === 'sm' ? 'text-[11px] px-1.5 py-0.5' : 'text-xs px-2.5 py-0.5';

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-medium rounded-md border tracking-tight ${getVariantStyles()} ${sizeStyles} ${className}`}
    >
      {dot && <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${getDotStyles()}`} />}
      {icon && <span className="shrink-0">{icon}</span>}
      <span>{children}</span>
    </span>
  );
};
