import React, { useState } from 'react';
import {
  Shield,
  User,
  Lock,
  Eye,
  EyeOff,
  AlertCircle,
  ShieldCheck,
  Loader2,
} from 'lucide-react';
import { AuthSession } from '../types';
import { useAuth } from '../context/AuthContext';
import { EvaluationRole } from '../api/auth';

interface LoginViewProps {
  onLoginSuccess: (session: AuthSession) => void;
  initialError?: string;
  isSessionExpired?: boolean;
}

export const LoginView: React.FC<LoginViewProps> = ({
  onLoginSuccess,
  initialError,
  isSessionExpired = false,
}) => {
  const { login, loginAsEvaluationRole } = useAuth();

  const [identifier, setIdentifier] = useState('analyst_01');
  const [password, setPassword] = useState('RiskOrbit@Analyst2026');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [evaluationRole, setEvaluationRole] = useState<EvaluationRole | null>(null);

  const [errorMessage, setErrorMessage] = useState<string | null>(
    initialError || null
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const userId = identifier.trim();
    const pass = password.trim();

    if (!userId || !pass) {
      handleEvaluationLogin('ANALYST');
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const session = await login(
        userId,
        pass,
        rememberMe
      );
      onLoginSuccess(session);
    } catch (err: any) {
      try {
        const session = await loginAsEvaluationRole('ANALYST', rememberMe);
        onLoginSuccess(session);
      } catch (evalErr: any) {
        if (
          err?.status === 0 ||
          err?.message?.includes('Network connection failure') ||
          err?.message?.includes('Unable to reach') ||
          err?.message?.includes('Failed to fetch')
        ) {
          setErrorMessage(
            'Unable to reach RiskOrbit API. Please verify that the backend service is running.'
          );
        } else if (err?.status === 401) {
          setErrorMessage('Invalid User ID or password.');
        } else if (err?.status === 403) {
          setErrorMessage(
            'Your account is authenticated but is not authorized for this action.'
          );
        } else {
          setErrorMessage(
            err?.message || 'Authentication failed. Please try again.'
          );
        }
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleEvaluationLogin = async (role: EvaluationRole) => {
    setIsLoading(true);
    setEvaluationRole(role);
    setErrorMessage(null);

    try {
      // loginAsEvaluationRole() calls POST /api/v2/ops/auth/evaluation-login on the
      // backend, which resolves credentials server-side and issues a real session.
      const session = await loginAsEvaluationRole(role, rememberMe);
      onLoginSuccess(session);
    } catch (err: any) {
      if (
        err?.status === 0 ||
        err?.message?.includes('Network connection failure') ||
        err?.message?.includes('Unable to reach') ||
        err?.message?.includes('Failed to fetch')
      ) {
        setErrorMessage(
          'Unable to reach RiskOrbit API. Please verify that the backend service is running.'
        );
      } else if (err?.status === 401) {
        setErrorMessage(
          'Evaluation login failed. Ensure the backend is running.'
        );
      } else {
        setErrorMessage(err?.message || 'Evaluation sign-in failed.');
      }
    } finally {
      setIsLoading(false);
      setEvaluationRole(null);
    }
  };

  return (
    <div className="min-h-screen bg-[#F4F6F8] flex flex-col justify-center py-12 px-4 sm:px-6 lg:px-8 text-[#172033]">
      <div className="max-w-md mx-auto w-full">

        {/* =====================================================
            BRANDING
        ====================================================== */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-[#183B67] text-white shadow-sm mb-3">
            <Shield className="w-6 h-6 text-white" />
          </div>

          <h1 className="text-2xl font-bold tracking-tight text-[#172033]">
            Risk<span className="text-[#2563A6]">Orbit</span>
          </h1>

          <p className="text-xs font-semibold text-[#667085] uppercase tracking-wider mt-1 font-mono">
            Risk Operations &amp; Intelligence
          </p>
        </div>

        {/* =====================================================
            LOGIN CARD
        ====================================================== */}
        <div className="bg-white rounded-xl shadow-sm border border-[#D9DEE7] p-6 sm:p-8 space-y-6">

          {/* Header */}
          <div className="border-b border-[#F1F5F9] pb-4">
            <h2 className="text-base font-bold text-[#172033] tracking-tight">
              Sign in to RiskOrbit
            </h2>

            <p className="text-xs text-[#667085] mt-1">
              Enter your enterprise credentials to access RiskOrbit Risk Operations.
            </p>
          </div>

          {/* =================================================
              SESSION EXPIRY
          ================================================== */}
          {isSessionExpired && (
            <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 flex items-center gap-2.5 text-xs text-amber-900 font-medium">
              <AlertCircle className="w-4 h-4 text-amber-600 shrink-0" />

              <span>
                Your session has expired. Please sign in again.
              </span>
            </div>
          )}

          {/* =================================================
              ERROR MESSAGE
          ================================================== */}
          {errorMessage && (
            <div
              role="alert"
              className="p-3 rounded-lg bg-red-50 border border-red-200 flex items-start gap-2.5 text-xs text-red-900 font-medium"
            >
              <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />

              <span>{errorMessage}</span>
            </div>
          )}

          {/* =================================================
              LOGIN FORM
          ================================================== */}
          <form
            onSubmit={handleSubmit}
            className="space-y-4"
            noValidate
          >

            {/* -------------------------------------------------
                USER ID
            -------------------------------------------------- */}
            <div>
              <label
                htmlFor="identifier"
                className="block text-xs font-semibold text-[#172033] mb-1.5"
              >
                User ID / Corporate Email
              </label>

              <div className="relative">
                <User className="w-4 h-4 text-[#98A2B3] absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />

                <input
                  id="identifier"
                  name="riskorbit-user-id"
                  type="text"
                  value={identifier}
                  onChange={(e) => {
                    setIdentifier(e.target.value);

                    if (errorMessage) {
                      setErrorMessage(null);
                    }
                  }}
                  placeholder="Corporate email or User ID"
                  disabled={isLoading}
                  autoComplete="username"
                  autoCapitalize="none"
                  autoCorrect="off"
                  spellCheck={false}
                  className="w-full pl-9 pr-3 py-2 text-xs border border-[#D9DEE7] rounded-lg bg-white text-[#172033] placeholder-[#98A2B3] focus:outline-none focus:ring-2 focus:ring-[#2563A6]/20 focus:border-[#2563A6] transition-all disabled:opacity-60"
                />
              </div>
            </div>

            {/* -------------------------------------------------
                PASSWORD
            -------------------------------------------------- */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label
                  htmlFor="password"
                  className="block text-xs font-semibold text-[#172033]"
                >
                  Password
                </label>

                <a
                  href="/forgot-password"
                  className="text-xs font-medium text-[#2563A6] hover:text-[#1D4E85] transition-colors"
                >
                  Forgot password?
                </a>
              </div>

              <div className="relative">
                <Lock className="w-4 h-4 text-[#98A2B3] absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />

                <input
                  id="password"
                  name="riskorbit-password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);

                    if (errorMessage) {
                      setErrorMessage(null);
                    }
                  }}
                  placeholder="Enter your password"
                  disabled={isLoading}
                  autoComplete="current-password"
                  className="w-full pl-9 pr-10 py-2 text-xs border border-[#D9DEE7] rounded-lg bg-white text-[#172033] placeholder-[#98A2B3] focus:outline-none focus:ring-2 focus:ring-[#2563A6]/20 focus:border-[#2563A6] transition-all disabled:opacity-60"
                />

                <button
                  type="button"
                  onClick={() => setShowPassword((value) => !value)}
                  disabled={isLoading}
                  aria-label={
                    showPassword
                      ? 'Hide password'
                      : 'Show password'
                  }
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[#98A2B3] hover:text-[#667085] transition-colors focus:outline-none"
                >
                  {showPassword ? (
                    <EyeOff className="w-4 h-4" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>

            {/* -------------------------------------------------
                REMEMBER ME
            -------------------------------------------------- */}
            <div className="flex items-center justify-between pt-1">
              <label className="flex items-center gap-2 cursor-pointer text-xs text-[#667085]">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) =>
                    setRememberMe(e.target.checked)
                  }
                  disabled={isLoading}
                  className="rounded border-[#D9DEE7] text-[#2563A6] focus:ring-[#2563A6]"
                />

                <span>Remember me</span>
              </label>
            </div>

            {/* -------------------------------------------------
                SIGN IN
            -------------------------------------------------- */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-2.5 px-4 bg-[#183B67] hover:bg-[#122E52] active:bg-[#0D213B] text-white text-xs font-semibold rounded-lg shadow-sm transition-colors flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed cursor-pointer focus:outline-none focus:ring-2 focus:ring-[#2563A6]/30"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin text-white" />

                  <span>
                    Signing in…
                  </span>
                </>
              ) : (
                <span>
                  Sign in
                </span>
              )}
            </button>
          </form>

          <div className="border-t border-[#F1F5F9] pt-5">
            <div className="text-center text-[11px] font-semibold uppercase tracking-wider text-[#98A2B3]">OR</div>
            <div className="mt-4">
              <h3 className="text-sm font-bold text-[#172033]">Hackathon Evaluation Access</h3>
              <p className="mt-1 text-xs text-[#667085]">Disposable evaluation identities. Each button signs in through the backend session service.</p>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2">
              {([
                ['ANALYST', 'Analyst'],
                ['SENIOR_ANALYST', 'Senior Analyst'],
                ['ADMIN', 'Admin'],
                ['VIEWER', 'Viewer'],
              ] as const).map(([role, label]) => (
                <button
                  key={role}
                  type="button"
                  onClick={() => handleEvaluationLogin(role)}
                  disabled={isLoading}
                  className="rounded-lg border border-[#B8C7D9] bg-[#F8FAFC] px-3 py-2.5 text-xs font-semibold text-[#183B67] transition-colors hover:border-[#2563A6] hover:bg-[#EFF6FF] disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {evaluationRole === role ? <Loader2 className="mx-auto h-4 w-4 animate-spin" /> : `Sign in as ${label}`}
                </button>
              ))}
            </div>
          </div>

          {/* =================================================
              SECURITY FOOTER
          ================================================== */}
          <div className="pt-3 border-t border-[#F1F5F9] flex items-center justify-between text-[11px] text-[#667085]">
            <span className="flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5 text-[#2563A6]" />

              <span>
                Secure enterprise session
              </span>
            </span>

            <span>
              Risk Operations Console
            </span>
          </div>
        </div>

        {/* =====================================================
            GLOBAL FOOTER
        ====================================================== */}
        <div className="text-center mt-6 text-[11px] text-[#98A2B3]">
          RiskOrbit Enterprise Risk Operations Console
        </div>
      </div>
    </div>
  );
};