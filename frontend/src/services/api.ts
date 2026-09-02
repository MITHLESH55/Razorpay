/**
 * RiskOrbit — Central API Service Layer
 *
 * Exposes a unified singleton service backed by modular, fully-typed API clients.
 * Zero hardcoded business data or fake mock fallbacks.
 */
import {
  AuditRecord,
  AuthSession,
  CaseDetailResponse,
  DemoUserRecord,
  EvaluationMetricsResponse,
  FeedbackRecord,
  ManifestData,
  OverviewKPIs,
  RiskCaseRecord,
  SystemControlsState,
  SystemDriftSummary,
  UserContext,
  UserRole,
} from '../types';

import {
  authApi,
  queueApi,
  casesApi,
  simulationApi,
  feedbackApi,
  auditApi,
  evaluationApi,
  governanceApi,
  healthApi,
  getAuthToken,
  setAuthToken,
  clearAuthToken,
} from '../api';

class RiskOrbitApiService {
  private userContext: UserContext | null = null;

  constructor() {
    this.restoreSession();
  }

  private restoreSession() {
    try {
      const savedUser = localStorage.getItem('riskorbit_auth_user');
      if (savedUser) {
        this.userContext = JSON.parse(savedUser);
      }
    } catch {}
  }

  public setAuthSession(session: AuthSession) {
    this.userContext = session.user;
    setAuthToken(session.token);
    try {
      localStorage.setItem('riskorbit_auth_user', JSON.stringify(session.user));
    } catch {}
  }

  public clearSession() {
    clearAuthToken();
    this.userContext = null;
    try {
      localStorage.removeItem('riskorbit_auth_user');
    } catch {}
  }

  public setUserContext(user: UserContext) {
    this.userContext = user;
    try {
      localStorage.setItem('riskorbit_auth_user', JSON.stringify(user));
    } catch {}
  }

  public getUserContext(): UserContext | null {
    return this.userContext;
  }

  public getAuthToken(): string | null {
    return getAuthToken();
  }

  // ---------------------------------------------------------------------------
  // Authentication & Session Endpoints
  // ---------------------------------------------------------------------------

  async login(
    usernameOrEmail: string,
    password?: string,
    role?: UserRole
  ): Promise<AuthSession> {
    const session = await authApi.login({
      username_or_email: usernameOrEmail,
      ...(password ? { password } : {}),
      role,
    });
    this.setAuthSession(session);
    return session;
  }

  async validateSession(): Promise<{ valid: boolean; user: UserContext | null }> {
    try {
      const resp = await authApi.validateSession();
      if (resp && resp.valid && resp.user) {
        this.setUserContext(resp.user);
        return { valid: true, user: resp.user };
      }
      return { valid: false, user: null };
    } catch {
      // If token expired or invalid, clear session
      return { valid: false, user: null };
    }
  }

  async logout(): Promise<void> {
    try {
      await authApi.logout();
    } finally {
      this.clearSession();
    }
  }

  async getDemoUsers(): Promise<DemoUserRecord[]> {
    return authApi.getDemoUsers();
  }

  // ---------------------------------------------------------------------------
  // Core Operational Endpoints
  // ---------------------------------------------------------------------------

  async getOverview(): Promise<OverviewKPIs> {
    return healthApi.getOverviewKPIs();
  }

  async getQueue(params: Record<string, any> = {}): Promise<RiskCaseRecord[]> {
    return queueApi.getQueue(params);
  }

  async getCaseDetail(caseId: string): Promise<CaseDetailResponse> {
    return casesApi.getCase(caseId);
  }

  async approveCase(caseId: string, notes?: string, idempotencyKey?: string, expectedVersion?: number): Promise<RiskCaseRecord> {
    return casesApi.approveCase(caseId, {
      notes,
      idempotency_key: idempotencyKey,
      expected_version: expectedVersion,
    });
  }

  async editCaseAction(caseId: string, newAction: string, reason: string, idempotencyKey?: string, expectedVersion?: number): Promise<RiskCaseRecord> {
    return casesApi.editCase(caseId, {
      new_action: newAction,
      reason,
      idempotency_key: idempotencyKey,
      expected_version: expectedVersion,
    });
  }

  async rejectCase(caseId: string, reason: string, idempotencyKey?: string, expectedVersion?: number): Promise<RiskCaseRecord> {
    return casesApi.rejectCase(caseId, {
      reason,
      idempotency_key: idempotencyKey,
      expected_version: expectedVersion,
    });
  }

  async simulateExecution(caseId: string, action?: string, overrideParams?: Record<string, any>): Promise<any> {
    return simulationApi.simulateCase(caseId, {
      simulated_action: action,
      override_policy_parameters: overrideParams,
    });
  }

  async submitFeedback(data: {
    case_id: string;
    transaction_id: string;
    adjudication: 'TRUE_POSITIVE' | 'FALSE_POSITIVE' | 'NEEDS_REVIEW' | 'EVIDENCE_INSUFFICIENT';
    notes?: string;
    evidence_conflict_notes?: string;
    suggested_policy_tuning?: string;
  }): Promise<FeedbackRecord> {
    return feedbackApi.submitFeedback(data);
  }

  async getAuditTrail(caseId?: string, limit?: number): Promise<AuditRecord[]> {
    return auditApi.getAuditTrail({ case_id: caseId, limit });
  }

  async getDriftReport(): Promise<SystemDriftSummary> {
    return evaluationApi.getDriftReport();
  }

  async recalculateDrift(): Promise<SystemDriftSummary> {
    return evaluationApi.recalculateDrift();
  }

  async getControls(): Promise<SystemControlsState> {
    return governanceApi.getSystemControls();
  }

  async updateControls(updates: { shadow_mode?: boolean; kill_switch?: boolean; graph_available?: boolean; reason?: string }): Promise<SystemControlsState> {
    return governanceApi.updateSystemControls(updates);
  }

  async getManifest(): Promise<ManifestData> {
    return evaluationApi.getReleaseManifest();
  }

  async getEvaluationMetrics(): Promise<EvaluationMetricsResponse> {
    return evaluationApi.getEvaluationMetrics();
  }
}

export const apiService = new RiskOrbitApiService();
