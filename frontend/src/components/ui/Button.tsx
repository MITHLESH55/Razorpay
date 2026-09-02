import React from 'react';

export type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'warning' | 'outline' | 'ghost' | 'navy' | 'purple' | 'success';
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: React.ReactNode;
  iconRight?: React.ReactNode;
  loading?: boolean;
  fullWidth?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  size = 'md',
  icon,
  iconRight,
  loading = false,
  fullWidth = false,
  className = '',
  disabled,
  ...props
}) => {
  const getVariantStyles = (): string => {
    switch (variant) {
      case 'navy':
        return 'bg-[#183B67] hover:bg-[#122E52] text-white border-transparent shadow-sm active:bg-[#0D223C]';
      case 'purple':
        return 'bg-purple-700 hover:bg-purple-800 text-white border-transparent shadow-sm active:bg-purple-900';
      case 'success':
        return 'bg-[#15803D] hover:bg-[#166534] text-white border-transparent shadow-sm active:bg-[#14532D]';
      case 'warning':
        return 'bg-[#B7791F] hover:bg-[#975A16] text-white border-transparent shadow-sm active:bg-[#744210]';
      case 'primary':
        return 'bg-[#2563A6] hover:bg-[#1D4ED8] text-white border-transparent shadow-sm active:bg-[#1E40AF]';
      case 'secondary':
        return 'bg-white hover:bg-slate-50 text-[#172033] border-[#D9DEE7] shadow-sm hover:border-[#CBD5E1] active:bg-slate-100';
      case 'danger':
        return 'bg-[#C53030] hover:bg-[#9B2C2C] text-white border-transparent shadow-sm active:bg-[#742A2A]';
      case 'outline':
        return 'bg-transparent hover:bg-slate-100 text-[#172033] border-[#D9DEE7] hover:border-[#CBD5E1]';
      case 'ghost':
        return 'bg-transparent hover:bg-slate-100 text-[#667085] hover:text-[#172033] border-transparent';
      default:
        return 'bg-[#2563A6] hover:bg-[#1D4ED8] text-white';
    }
  };

  const getSizeStyles = (): string => {
    switch (size) {
      case 'sm':
        return 'text-xs px-2.5 py-1.5 rounded-md gap-1.5';
      case 'lg':
        return 'text-sm px-4 py-2.5 rounded-lg gap-2.5 font-semibold';
      case 'md':
      default:
        return 'text-xs font-medium px-3.5 py-2 rounded-md gap-2';
    }
  };

  return (
    <button
      className={`inline-flex items-center justify-center font-sans border transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-[#2563A6]/20 disabled:opacity-50 disabled:cursor-not-allowed ${getVariantStyles()} ${getSizeStyles()} ${
        fullWidth ? 'w-full' : ''
      } ${className}`}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <svg
          className="animate-spin h-3.5 w-3.5 text-current"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          ></circle>
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          ></path>
        </svg>
      ) : (
        icon && <span className="shrink-0">{icon}</span>
      )}
      {children}
      {!loading && iconRight && <span className="shrink-0">{iconRight}</span>}
    </button>
  );
};
