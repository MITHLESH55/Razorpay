import React from 'react';

export interface CardProps {
  children: React.ReactNode;
  className?: string;
  header?: React.ReactNode;
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  badge?: React.ReactNode;
  actions?: React.ReactNode;
  headerRight?: React.ReactNode;
  icon?: React.ReactNode;
  padding?: 'none' | 'sm' | 'md' | 'lg';
  footer?: React.ReactNode;
  noBorder?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  className = '',
  header,
  title,
  subtitle,
  badge,
  actions,
  headerRight,
  icon,
  padding = 'md',
  footer,
  noBorder = false,
}) => {
  const getPaddingClass = (): string => {
    switch (padding) {
      case 'none':
        return 'p-0';
      case 'sm':
        return 'p-3.5';
      case 'lg':
        return 'p-6';
      case 'md':
      default:
        return 'p-5';
    }
  };

  const rightElement = headerRight || actions;
  const hasCustomHeader = Boolean(header);
  const hasStandardHeader = Boolean(title || subtitle || badge || rightElement || icon);

  return (
    <div
      className={`bg-white rounded-lg transition-shadow duration-150 ${noBorder ? '' : 'border border-[#D9DEE7]'} shadow-card ${className}`}
    >
      {hasCustomHeader && (
        <div className="border-b border-[#D9DEE7] px-5 py-3.5 bg-[#F8FAFC]/70 rounded-t-lg">
          {header}
        </div>
      )}

      {!hasCustomHeader && hasStandardHeader && (
        <div className="flex items-center justify-between border-b border-[#D9DEE7] px-5 py-3.5 bg-[#F8FAFC]/50 rounded-t-lg">
          <div className="flex items-center gap-2.5 min-w-0">
            {icon && <span className="shrink-0">{icon}</span>}
            {typeof title === 'string' ? (
              <h3 className="text-sm font-semibold text-[#172033] truncate tracking-tight">{title}</h3>
            ) : (
              title
            )}
            {badge}
            {subtitle && (
              <p className="text-xs text-[#667085] truncate hidden sm:inline">{subtitle}</p>
            )}
          </div>
          {rightElement && <div className="flex items-center gap-2 shrink-0">{rightElement}</div>}
        </div>
      )}

      <div className={getPaddingClass()}>{children}</div>

      {footer && (
        <div className="border-t border-[#D9DEE7] px-5 py-3 bg-[#F8FAFC]/60 rounded-b-lg">
          {footer}
        </div>
      )}
    </div>
  );
};
