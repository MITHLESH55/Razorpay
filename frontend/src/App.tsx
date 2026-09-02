import React, { useState, useEffect, useCallback } from 'react';
import { Navbar } from './components/Navbar';
import { Sidebar, NavTab } from './components/Sidebar';
import { OverviewView } from './views/OverviewView';
import { RiskQueueView } from './views/RiskQueueView';
import { CaseDetailView } from './views/CaseDetailView';
import { SimulationView } from './views/SimulationView';
import { GovernanceView } from './views/GovernanceView';
import { AuditView } from './views/AuditView';
import { EvaluationView } from './views/EvaluationView';
import { DriftView } from './views/DriftView';
import { LoginView } from './views/LoginView';
import { AuthProvider, useAuth } from './context/AuthContext';
import { SystemControlsState } from './types';
import { apiService } from './services/api';
import { Flame, ShieldAlert, Shield } from 'lucide-react';

function getTabFromPath(path: string): { tab: NavTab | 'login'; caseId: string | null } {
  const cleanPath = path.toLowerCase().trim();
  if (cleanPath === '/login') {
    return { tab: 'login', caseId: null };
  }
  if (cleanPath === '/queue') {
    return { tab: 'queue', caseId: null };
  }
  if (cleanPath.startsWith('/cases/') || cleanPath.startsWith('/case-detail/')) {
    const parts = path.split('/');
    const id = parts[2] || null;
    return { tab: 'case-detail', caseId: id };
  }
  if (cleanPath === '/cases' || cleanPath === '/case-detail') {
    return { tab: 'case-detail', caseId: null };
  }
  if (cleanPath === '/simulation') {
    return { tab: 'simulation', caseId: null };
  }
  if (cleanPath === '/governance' || cleanPath === '/controls') {
    return { tab: 'governance', caseId: null };
  }
  if (cleanPath === '/audit') {
    return { tab: 'audit', caseId: null };
  }
  if (cleanPath === '/evaluation') {
    return { tab: 'evaluation', caseId: null };
  }
  if (cleanPath === '/drift') {
    return { tab: 'drift', caseId: null };
  }
  if (cleanPath === '/dashboard' || cleanPath === '/command-center') {
    return { tab: 'overview', caseId: null };
  }
  // Default to overview for /dashboard, /, or any other path
  return { tab: 'overview', caseId: null };
}

function getPathFromTab(tab: NavTab, caseId?: string | null): string {
  switch (tab) {
    case 'overview':
      return '/dashboard';
    case 'queue':
      return '/queue';
    case 'case-detail':
      return caseId ? `/cases/${caseId}` : '/cases';
    case 'simulation':
      return '/simulation';
    case 'governance':
      return '/governance';
    case 'audit':
      return '/audit';
    case 'evaluation':
      return '/evaluation';
    case 'drift':
      return '/drift';
    default:
      return '/dashboard';
  }
}

const AppContent: React.FC = () => {
  const { status, user, logout } = useAuth();

  const [currentPath, setCurrentPath] = useState<string>(() => window.location.pathname || '/');
  const [currentTab, setCurrentTab] = useState<NavTab>('overview');
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [controls, setControls] = useState<SystemControlsState | null>(null);
  const [pendingApprovalsCount, setPendingApprovalsCount] = useState<number>(0);
  const [criticalCasesCount, setCriticalCasesCount] = useState<number>(0);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  // Synchronize route state with URL pathname
  const syncRoute = useCallback((path: string) => {
    setCurrentPath(path);
    const { tab, caseId } = getTabFromPath(path);
    if (tab !== 'login') {
      setCurrentTab(tab);
    }
    if (caseId) {
      setSelectedCaseId(caseId);
    }
  }, []);

  const navigate = useCallback((path: string, options?: { replace?: boolean }) => {
    if (options?.replace) {
      window.history.replaceState({}, '', path);
    } else {
      window.history.pushState({}, '', path);
    }
    syncRoute(path);
  }, [syncRoute]);

  // Initial route synchronization and browser popstate listener
  useEffect(() => {
    syncRoute(window.location.pathname);

    const handlePopState = () => {
      syncRoute(window.location.pathname);
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, [syncRoute]);

  // Route protection and redirection guards
  useEffect(() => {
    if (status === 'INITIALIZING' || status === 'AUTHENTICATING') return;

    const path = window.location.pathname;

    if (status === 'UNAUTHENTICATED' || status === 'EXPIRED') {
      if (path !== '/login') {
        navigate('/login', { replace: true });
      }
    } else if (status === 'AUTHENTICATED') {
      if (path === '/login' || path === '/') {
        navigate('/dashboard', { replace: true });
      }
    }
  }, [status, navigate]);

  // Auto-collapse sidebar on smaller screens
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 1100) {
        setIsSidebarCollapsed(true);
      }
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const fetchLiveCounts = async () => {
    try {
      const overview = await apiService.getOverview();
      setPendingApprovalsCount(overview.pending_human_approvals);
      setCriticalCasesCount(overview.critical_priority_count);
    } catch {
      // Degraded / offline
    }
  };

  const fetchControls = async () => {
    try {
      const data = await apiService.getControls();
      setControls(data);
    } catch (err) {
      console.error('Failed to load controls', err);
      setControls(null);
    }
  };

  useEffect(() => {
    if (status !== 'AUTHENTICATED') return;
    fetchControls();
    fetchLiveCounts();
  }, [status]);

  const handleSelectTab = (tab: NavTab) => {
    setCurrentTab(tab);
    const targetPath = getPathFromTab(tab, tab === 'case-detail' ? selectedCaseId : null);
    navigate(targetPath);
  };

  const handleSelectCase = (caseId: string) => {
    setSelectedCaseId(caseId);
    setCurrentTab('case-detail');
    navigate(`/cases/${caseId}`);
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  // Loading splash during bootstrap session check or active authentication
  if (status === 'INITIALIZING' || status === 'AUTHENTICATING') {
    return (
      <div className="min-h-screen bg-[#F4F6F8] flex items-center justify-center text-[#172033]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#183B67] flex items-center justify-center text-white animate-pulse shadow-sm">
            <Shield className="w-6 h-6" />
          </div>
          <p className="text-xs font-semibold text-[#667085]">Verifying secure session...</p>
        </div>
      </div>
    );
  }

  // If unauthenticated or session expired, render Dedicated Standalone Login Page
  if (status === 'UNAUTHENTICATED' || status === 'EXPIRED' || !user) {
    return (
      <LoginView
        onLoginSuccess={() => {
          navigate('/dashboard', { replace: true });
        }}
        isSessionExpired={status === 'EXPIRED'}
      />
    );
  }

  // Authenticated Command Center Application
  return (
    <div className="min-h-screen bg-[#F4F6F8] text-[#172033] flex flex-col font-sans selection:bg-[#2563A6] selection:text-white">
      {/* Top Header */}
      <Navbar
        user={user}
        onLogout={handleLogout}
        systemHealth={controls?.health_status || 'UNKNOWN'}
        killSwitchActive={controls?.kill_switch_active || false}
        shadowModeEnabled={controls?.shadow_mode_enabled || false}
        isSidebarCollapsed={isSidebarCollapsed}
        onToggleSidebar={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
      />

      {/* Global Kill Switch Banner */}
      {controls?.kill_switch_active && (
        <div className="bg-red-50 border-b border-red-200 text-[#C53030] px-4 sm:px-6 py-2 flex items-center justify-between text-xs font-mono shadow-xs">
          <div className="flex items-center gap-2">
            <Flame className="w-4 h-4 text-[#C53030] animate-pulse shrink-0" />
            <strong className="font-bold">GRAPH ENGINE KILL SWITCH ACTIVE:</strong>
            <span className="hidden sm:inline">
              Operating in degraded SAFE MODE. Graph traversal disabled; fallback to Phase 1 point model risk scoring.
            </span>
          </div>
          <button
            onClick={() => handleSelectTab('governance')}
            className="underline font-bold hover:text-red-900 shrink-0"
          >
            Manage Controls &rarr;
          </button>
        </div>
      )}

      {/* Shadow Mode Banner */}
      {controls?.shadow_mode_enabled && !controls?.kill_switch_active && (
        <div className="bg-purple-50 border-b border-purple-200 text-purple-900 px-4 sm:px-6 py-1.5 flex items-center justify-between text-xs font-mono">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-purple-700 shrink-0" />
            <strong>SHADOW MODE ACTIVE:</strong>
            <span className="hidden sm:inline">
              All policy interventions evaluated and logged without active transaction disruption.
            </span>
          </div>
        </div>
      )}

      {/* Main Workstation Layout */}
      <div className="flex flex-1 overflow-hidden min-h-0">
        {/* Sidebar Navigation */}
        <Sidebar
          currentTab={currentTab}
          onSelectTab={handleSelectTab}
          pendingApprovalsCount={pendingApprovalsCount}
          criticalCasesCount={criticalCasesCount}
          isCollapsed={isSidebarCollapsed}
          onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        />

        {/* Dynamic View Container */}
        <main className="flex-1 min-w-0 overflow-y-auto p-4 sm:p-6 bg-[#F4F6F8]">
          <div className="w-full max-w-[1720px] mx-auto space-y-6">
            {currentTab === 'overview' && (
              <OverviewView user={user} onSelectCase={handleSelectCase} />
            )}
            {currentTab === 'queue' && (
              <RiskQueueView user={user} onSelectCase={handleSelectCase} />
            )}
            {currentTab === 'case-detail' && selectedCaseId && (
              <CaseDetailView
                caseId={selectedCaseId}
                user={user}
                onBack={() => handleSelectTab('queue')}
              />
            )}
            {currentTab === 'case-detail' && !selectedCaseId && (
              <div className="flex items-center justify-center h-96 text-[#667085]">
                <p className="text-sm font-semibold">Please select a case from the queue to inspect</p>
              </div>
            )}
            {currentTab === 'simulation' && <SimulationView user={user} />}
            {currentTab === 'governance' && (
              <GovernanceView
                user={user}
                onControlsChanged={fetchControls}
              />
            )}
            {currentTab === 'audit' && <AuditView user={user} />}
            {currentTab === 'evaluation' && <EvaluationView user={user} />}
            {currentTab === 'drift' && <DriftView user={user} />}
          </div>
        </main>
      </div>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
};
