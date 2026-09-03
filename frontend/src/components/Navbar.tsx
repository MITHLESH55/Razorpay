import React, { useState } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  Shield,
  Flame,
  ChevronDown,
  LogOut,
  Menu,
} from 'lucide-react';
import { UserContext, UserRole } from '../types';
import { Badge } from './ui';

interface NavbarProps {
  user: UserContext;
  onLogout: () => void;
  systemHealth: string;
  killSwitchActive: boolean;
  shadowModeEnabled: boolean;
  isSidebarCollapsed?: boolean;
  onToggleSidebar?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  user,
  onLogout,
  systemHealth,
  killSwitchActive,
  shadowModeEnabled,
  isSidebarCollapsed,
  onToggleSidebar,
}) => {
  const [showUserMenu, setShowUserMenu] = useState(false);

  const getRoleBadgeVariant = (role: UserRole) => {
    switch (role) {
      case 'ADMIN':
        return 'red';
      case 'SENIOR_ANALYST':
        return 'purple';
      case 'ANALYST':
        return 'blue';
      case 'VIEWER':
      default:
        return 'gray';
    }
  };

  const getHealthBadge = () => {
    if (killSwitchActive) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-red-50 text-[#C53030] border border-red-200 shadow-sm animate-pulse whitespace-nowrap">
          <Flame className="w-3.5 h-3.5 text-[#C53030]" />
          <span>SAFE MODE</span>
        </span>
      );
    }
    if (systemHealth === 'DEGRADED') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-50 text-[#B7791F] border border-amber-200 shadow-sm whitespace-nowrap">
          <ShieldAlert className="w-3.5 h-3.5 text-[#B7791F]" />
          <span>DEGRADED</span>
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-50 text-[#15803D] border border-emerald-200 shadow-sm whitespace-nowrap">
        <ShieldCheck className="w-3.5 h-3.5 text-[#15803D]" />
        <span>SYSTEM HEALTHY</span>
      </span>
    );
  };

  return (
    <header className="sticky top-0 z-40 bg-white border-b border-[#D9DEE7] shadow-sm">
      <div className="flex items-center justify-between px-4 sm:px-6 py-2.5">
        {/* Brand & Sidebar Toggle */}
        <div className="flex items-center gap-3">
          {onToggleSidebar && (
            <button
              onClick={onToggleSidebar}
              className="p-1.5 rounded-lg text-[#667085] hover:text-[#172033] hover:bg-[#F8FAFC] border border-[#D9DEE7] sm:hidden"
              aria-label="Toggle navigation menu"
            >
              <Menu className="w-4 h-4" />
            </button>
          )}

          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-[#183B67] to-[#2563A6] flex items-center justify-center text-white shadow-sm flex-shrink-0">
              <Shield className="w-4 h-4 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-sm sm:text-base font-bold tracking-tight text-[#172033]">
                  Risk<span className="text-[#2563A6]">Orbit</span>
                </span>
                <span className="px-1.5 py-0.2 text-[9px] font-bold tracking-wide uppercase bg-blue-50 text-[#183B67] border border-blue-200 rounded">
                  v2.0
                </span>
              </div>
              <p className="text-[10px] text-[#667085] hidden md:block">
                Autonomous Graph Fraud Operations & Governance
              </p>
            </div>
          </div>

          <div className="h-4 w-px bg-[#D9DEE7] mx-1 hidden sm:block" />

          {/* System Health Status */}
          <div className="flex items-center gap-2">
            {getHealthBadge()}
            {shadowModeEnabled && !killSwitchActive && (
              <span className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-purple-50 text-purple-800 border border-purple-200 font-semibold">
                SHADOW
              </span>
            )}
          </div>
        </div>

        {/* Center: Frozen Model & Benchmark Indicators */}
        <div className="hidden xl:flex items-center gap-2.5 text-xs font-mono">
          <div className="flex items-center gap-1.5 bg-[#F8FAFC] px-2.5 py-1 rounded-md border border-[#D9DEE7] text-[#667085]">
            <span>Model:</span>
            <span className="font-semibold text-[#172033]">riskorbit-risk-v1</span>
            <span className="text-[#2563A6] font-bold text-[10px]">(Frozen)</span>
          </div>
          <div className="flex items-center gap-1.5 bg-[#F8FAFC] px-2.5 py-1 rounded-md border border-[#D9DEE7] text-[#667085]">
            <span>Policy:</span>
            <span className="font-semibold text-[#172033]">phase3_final</span>
          </div>
          <div className="flex items-center gap-1.5 bg-[#F8FAFC] px-2.5 py-1 rounded-md border border-[#D9DEE7] text-[#667085]">
            <span>Held-Out:</span>
            <span className="font-bold text-[#15803D]">Artifact-backed</span>
          </div>
        </div>

        {/* Right: Authenticated User Menu */}
        <div className="flex items-center gap-3 relative">
          <div
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="flex items-center gap-2 p-1.5 pl-2 sm:pl-2.5 rounded-xl border border-[#D9DEE7] hover:border-[#CBD5E1] bg-[#F8FAFC] hover:bg-white cursor-pointer transition-all shadow-xs"
          >
            <div className="text-right hidden sm:block">
              <div className="flex items-center justify-end gap-1.5">
                <span className="text-xs font-bold text-[#172033] truncate max-w-[140px]">{user.name}</span>
                <Badge variant={getRoleBadgeVariant(user.role)} size="sm">
                  {user.role}
                </Badge>
              </div>
              <div className="text-[10px] font-mono text-[#98A2B3] truncate max-w-[140px]">{user.user_id}</div>
            </div>

            <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-[#E2E8F0] border border-[#CBD5E1] flex items-center justify-center text-[#183B67] font-bold text-xs flex-shrink-0">
              {user.name.split(' ').map((n) => n[0]).join('').slice(0, 2)}
            </div>

            <ChevronDown className={`w-3.5 h-3.5 text-[#98A2B3] transition-transform ${showUserMenu ? 'rotate-180' : ''}`} />
          </div>

          {/* User Dropdown Menu */}
          {showUserMenu && (
            <div className="absolute right-0 top-full mt-2 w-72 bg-white rounded-xl shadow-modal border border-[#D9DEE7] p-2 z-50 animate-in fade-in slide-in-from-top-2 duration-150">
              <div className="p-2.5 bg-[#F8FAFC] rounded-lg mb-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-[#172033]">{user.name}</span>
                  <Badge variant={getRoleBadgeVariant(user.role)} size="sm">
                    {user.role}
                  </Badge>
                </div>
                <div className="text-[11px] text-[#667085] mt-0.5 truncate">{user.email || `${user.user_id}@riskorbit.internal`}</div>
                {user.title && <div className="text-[10px] text-[#98A2B3] mt-0.5">{user.title}</div>}
              </div>

              {/* Logout Button */}
              <div className="pt-1 mt-1 border-t border-[#F1F5F9]">
                <button
                  onClick={() => {
                    setShowUserMenu(false);
                    onLogout();
                  }}
                  className="w-full text-left px-2.5 py-2 rounded-lg text-xs font-semibold text-[#C53030] hover:bg-red-50 flex items-center gap-2 transition-colors"
                >
                  <LogOut className="w-3.5 h-3.5 text-[#C53030]" />
                  <span>Sign Out Session</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
