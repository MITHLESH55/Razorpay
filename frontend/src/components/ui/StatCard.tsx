import React from 'react';
import { Card } from './Card';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { Badge, BadgeVariant } from './Badge';

export interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  /** Pass a string to auto-render as a Badge with badgeVariant, or a ReactNode element for full control */
  badge?: React.ReactNode;
  badgeVariant?: BadgeVariant;
  icon?: React.ReactNode;
  trend?: {
    value: string;
    direction: 'up' | 'down' | 'neutral';
    label?: string;
    isGood?: boolean;
  };
  onClick?: () => void;
  className?: string;
  highlightColor?: 'blue' | 'red' | 'amber' | 'green' | 'navy';
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  badge,
  badgeVariant,
  icon,
  trend,
  onClick,
  className = '',
  highlightColor,
}) => {
  const getHighlightBorder = (): string => {
    switch (highlightColor) {
      case 'red':
        return 'border-l-4 border-l-[#C53030]';
      case 'amber':
        return 'border-l-4 border-l-[#B7791F]';
      case 'green':
        return 'border-l-4 border-l-[#15803D]';
      case 'blue':
        return 'border-l-4 border-l-[#2563A6]';
      case 'navy':
        return 'border-l-4 border-l-[#183B67]';
      default:
        return '';
    }
  };

  // Resolve final badge element
  const badgeEl: React.ReactNode =
    typeof badge === 'string' && badgeVariant ? (
      <Badge variant={badgeVariant} size="sm">{badge}</Badge>
    ) : badge != null ? (
      badge
    ) : null;

  return (
    <Card
      className={`relative overflow-hidden transition-all duration-200 ${getHighlightBorder()} ${
        onClick ? 'cursor-pointer hover:shadow-card-hover hover:border-[#CBD5E1]' : ''
      } ${className}`}
      padding="sm"
    >
      <div className="flex items-start justify-between gap-3" onClick={onClick}>
        <div className="space-y-2 min-w-0 flex-1">
          {/* Header Row: Title and Badge */}
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs font-semibold text-[#667085] uppercase tracking-wider">
              {title}
            </span>
            {badgeEl}
          </div>

          {/* Value Display */}
          <div className="space-y-0.5">
            <div className="text-2xl font-bold text-[#172033] tracking-tight font-mono leading-none">
              {value}
            </div>
            {subtitle && (
              <p className="text-xs text-[#667085] leading-relaxed pt-0.5">
                {subtitle}
              </p>
            )}
          </div>

          {/* Optional Trend Indicator */}
          {trend && (
            <div className="flex items-center gap-1.5 pt-1 text-xs">
              <span
                className={`inline-flex items-center gap-0.5 font-medium ${
                  trend.isGood === true
                    ? 'text-emerald-700'
                    : trend.isGood === false
                    ? 'text-red-700'
                    : 'text-slate-600'
                }`}
              >
                {trend.direction === 'up' && <TrendingUp className="w-3.5 h-3.5" />}
                {trend.direction === 'down' && <TrendingDown className="w-3.5 h-3.5" />}
                {trend.direction === 'neutral' && <Minus className="w-3.5 h-3.5" />}
                {trend.value}
              </span>
              {trend.label && <span className="text-[#98A2B3]">{trend.label}</span>}
            </div>
          )}
        </div>

        {icon && (
          <div className="p-2.5 rounded-xl bg-[#F8FAFC] border border-[#D9DEE7] text-[#183B67] shrink-0">
            {icon}
          </div>
        )}
      </div>
    </Card>
  );
};
