import React from 'react';
import {
  LayoutDashboard,
  Inbox,
  Network,
  Sliders,
  ShieldCheck,
  History,
  FileCheck2,
  Activity,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { Badge } from './ui';

export type NavTab =
  | 'overview'
  | 'queue'
  | 'case-detail'
  | 'simulation'
  | 'governance'
  | 'audit'
  | 'evaluation'
  | 'drift';

interface SidebarProps {
  currentTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  pendingApprovalsCount: number;
  criticalCasesCount: number;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

interface NavSection {
  title: string;
  items: {
    id: NavTab;
    label: string;
    icon: React.ElementType;
    badge: string | null;
    badgeVariant: 'gray' | 'red' | 'blue' | 'green' | 'navy';
    desc: string;
  }[];
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentTab,
  onSelectTab,
  pendingApprovalsCount,
  criticalCasesCount,
  isCollapsed = false,
  onToggleCollapse,
}) => {
  const sections: NavSection[] = [
    {
      title: 'OPERATIONS',
      items: [
        {
          id: 'overview',
          label: 'Command Center',
          icon: LayoutDashboard,
          badge: null,
          badgeVariant: 'gray',
          desc: 'Operational KPIs & Live Telemetry',
        },
        {
          id: 'queue',
          label: 'Risk Queue',
          icon: Inbox,
          badge: criticalCasesCount > 0 ? `${criticalCasesCount} Crit` : null,
          badgeVariant: 'red',
          desc: 'Prioritized Case Workbench',
        },
        {
          id: 'case-detail',
          label: 'Case Investigation',
          icon: Network,
          badge: pendingApprovalsCount > 0 ? `${pendingApprovalsCount} Action` : null,
          badgeVariant: 'blue',
          desc: 'Subgraph, Evidence & Decisions',
        },
      ],
    },
    {
      title: 'DECISIONING',
      items: [
        {
          id: 'simulation',
          label: 'Counterfactual Simulation',
          icon: Sliders,
          badge: null,
          badgeVariant: 'gray',
          desc: 'Offline Policy Sandbox',
        },
      ],
    },
    {
      title: 'GOVERNANCE',
      items: [
        {
          id: 'audit',
          label: 'Audit Trail',
          icon: History,
          badge: null,
          badgeVariant: 'gray',
          desc: 'Immutable Append-Only Logs',
        },
        {
          id: 'evaluation',
          label: 'Evaluation & Hashes',
          icon: FileCheck2,
          badge: '100% Recall',
          badgeVariant: 'green',
          desc: 'Held-Out Test Certification',
        },
        {
          id: 'governance',
          label: 'Controls & Health',
          icon: ShieldCheck,
          badge: null,
          badgeVariant: 'gray',
          desc: 'Kill Switch, Shadow & Fallback',
        },
        {
          id: 'drift',
          label: 'Drift Monitor',
          icon: Activity,
          badge: 'PSI < 0.05',
          badgeVariant: 'navy',
          desc: 'Feature Distribution Stability',
        },
      ],
    },
  ];

  return (
    <aside
      className={`${
        isCollapsed ? 'w-16' : 'w-64'
      } flex-shrink-0 bg-[#FFFFFF] border-r border-[#D9DEE7] flex flex-col justify-between p-3 min-h-[calc(100vh-61px)] transition-all duration-200 z-30 select-none`}
    >
      <div className="space-y-4">
        {/* Toggle button */}
        {onToggleCollapse && (
          <div className="flex items-center justify-end px-1 pb-1">
            <button
              onClick={onToggleCollapse}
              className="p-1 rounded-lg text-[#98A2B3] hover:text-[#172033] hover:bg-[#F8FAFC] border border-transparent hover:border-[#D9DEE7] transition-all"
              title={isCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
              aria-label={isCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
            >
              {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
            </button>
          </div>
        )}

        {sections.map((section) => (
          <div key={section.title} className="space-y-1">
            {!isCollapsed && (
              <div className="px-3 py-1 text-[10px] font-extrabold tracking-wider text-[#98A2B3] uppercase font-mono">
                {section.title}
              </div>
            )}

            {section.items.map((item) => {
              const Icon = item.icon;
              const isActive = currentTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onSelectTab(item.id)}
                  title={isCollapsed ? `${item.label} — ${item.desc}` : undefined}
                  className={`w-full flex items-center ${
                    isCollapsed ? 'justify-center px-2 py-2.5' : 'justify-between px-3 py-2'
                  } rounded-xl text-xs font-medium transition-all group ${
                    isActive
                      ? 'bg-blue-50 text-[#183B67] font-bold border border-blue-200 shadow-xs'
                      : 'text-[#667085] hover:text-[#172033] hover:bg-[#F8FAFC] border border-transparent'
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <Icon
                      className={`w-4 h-4 flex-shrink-0 transition-colors ${
                        isActive ? 'text-[#2563A6]' : 'text-[#98A2B3] group-hover:text-[#172033]'
                      }`}
                    />
                    {!isCollapsed && (
                      <div className="text-left min-w-0">
                        <div className="text-xs font-semibold truncate">{item.label}</div>
                        <div className="text-[10px] text-[#98A2B3] line-clamp-1">{item.desc}</div>
                      </div>
                    )}
                  </div>

                  {!isCollapsed && item.badge && (
                    <Badge variant={item.badgeVariant} size="sm" className="flex-shrink-0 ml-1">
                      {item.badge}
                    </Badge>
                  )}
                </button>
              );
            })}
          </div>
        ))}
      </div>

      {/* Footer status card */}
      {!isCollapsed ? (
        <div className="p-3.5 rounded-xl bg-[#F8FAFC] border border-[#D9DEE7] space-y-2 mt-4">
          <div className="flex items-center justify-between text-xs font-bold text-[#172033]">
            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-[#15803D]" />
              Evaluation Artifacts
            </span>
          </div>
          <div className="space-y-1 text-[11px] font-mono text-[#667085]">
            <div className="flex justify-between">
              <span>Model Weights:</span>
              <span className="font-semibold text-[#2563A6]">Frozen v1</span>
            </div>
            <div className="text-[#667085]">Metrics available in Evaluation.</div>
          </div>
        </div>
      ) : (
        <div
          className="p-2 rounded-xl bg-[#F8FAFC] border border-[#D9DEE7] flex items-center justify-center text-[#15803D]"
          title="Evaluation artifacts"
        >
          <CheckCircle2 className="w-4 h-4 text-[#15803D]" />
        </div>
      )}
    </aside>
  );
};
