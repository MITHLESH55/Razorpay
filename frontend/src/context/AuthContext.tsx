/**
 * RiskOrbit — Enterprise Authentication & Session Context
 *
 * Implements the authoritative server-backed session lifecycle:
 * INITIALIZING -> AUTHENTICATING -> AUTHENTICATED / UNAUTHENTICATED / EXPIRED / ERROR
 */
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authApi } from '../api/auth';
import { clearAuthToken, setAuthToken, getAuthToken } from '../api/client';
import { UserContext, UserRole, AuthSession } from '../types';

export type AuthLifecycleStatus =
  | 'INITIALIZING'
  | 'AUTHENTICATING'
  | 'AUTHENTICATED'
  | 'UNAUTHENTICATED'
  | 'EXPIRED'
  | 'ERROR';

export interface AuthContextType {
  status: AuthLifecycleStatus;
  user: UserContext | null;
  role: UserRole | null;
  session: AuthSession | null;
  error: string | null;
  login: (usernameOrEmail: string, password: string, rememberMe?: boolean) => Promise<AuthSession>;
  loginAsEvaluationRole: (role: 'ANALYST' | 'SENIOR_ANALYST' | 'ADMIN' | 'VIEWER', rememberMe?: boolean) => Promise<AuthSession>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [status, setStatus] = useState<AuthLifecycleStatus>('INITIALIZING');
  const [user, setUser] = useState<UserContext | null>(null);
  const [session, setSession] = useState<AuthSession | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Initialize and validate session against backend
  const refresh = useCallback(async () => {
    try {
      const existingToken = getAuthToken();
      if (!existingToken) {
        setStatus('UNAUTHENTICATED');
        setUser(null);
        setSession(null);
        return;
      }

      // Validate token with backend GET /api/v2/ops/auth/session
      const validateRes = await authApi.validateSession();
      if (validateRes && validateRes.valid && validateRes.user) {
        setUser(validateRes.user);
        setSession({
          session_id: validateRes.session_id || `sess_${validateRes.user.user_id}`,
          token: existingToken,
          user: validateRes.user,
          expires_at: validateRes.expires_at || (Date.now() / 1000 + 86400),
        });
        setStatus('AUTHENTICATED');
        setError(null);
      } else {
        clearAuthToken();
        setUser(null);
        setSession(null);
        setStatus('UNAUTHENTICATED');
      }
    } catch (err: any) {
      console.error('Session validation error:', err);
      if (err.status === 401) {
        clearAuthToken();
        setUser(null);
        setSession(null);
        setStatus('EXPIRED');
      } else {
        setStatus('UNAUTHENTICATED');
      }
      setError(err.message || 'Session verification failed');
    }
  }, []);

  useEffect(() => {
    refresh();

    // Listen for global 401 Unauthorized events from API client
    const handleUnauthorized = () => {
      clearAuthToken();
      setUser(null);
      setSession(null);
      setStatus('EXPIRED');
    };

    window.addEventListener('riskorbit:unauthorized', handleUnauthorized);
    return () => {
      window.removeEventListener('riskorbit:unauthorized', handleUnauthorized);
    };
  }, [refresh]);

  // Login action
  const login = async (
    usernameOrEmail: string,
    password: string,
    rememberMe = true
  ): Promise<AuthSession> => {
    setStatus('AUTHENTICATING');
    setError(null);
    try {
      const resp = await authApi.login({
        username_or_email: usernameOrEmail,
        password,
        remember_me: rememberMe,
      });

      setAuthToken(resp.token, rememberMe);
      // The login response only gives us a provisional token. The backend
      // session endpoint is the authority for both identity and role.
      const validated = await authApi.validateSession();
      if (!validated.valid || !validated.user) {
        throw new Error('The backend did not validate the newly issued session.');
      }
      const newSession: AuthSession = {
        session_id: validated.session_id || resp.session_id,
        token: resp.token,
        user: validated.user,
        expires_at: validated.expires_at || resp.expires_at,
      };

      setUser(validated.user);
      setSession(newSession);
      setStatus('AUTHENTICATED');
      return newSession;
    } catch (err: any) {
      clearAuthToken();
      setStatus('UNAUTHENTICATED');
      setError(err.message || 'Login failed');
      throw err;
    }
  };

  const loginAsEvaluationRole = async (
    role: 'ANALYST' | 'SENIOR_ANALYST' | 'ADMIN' | 'VIEWER',
    rememberMe = true
  ): Promise<AuthSession> => {
    setStatus('AUTHENTICATING');
    setError(null);
    try {
      const resp = await authApi.loginAsEvaluationRole(role, rememberMe);
      setAuthToken(resp.token, rememberMe);
      const validated = await authApi.validateSession();
      if (!validated.valid || !validated.user) {
        throw new Error('The backend did not validate the evaluation session.');
      }
      const newSession: AuthSession = {
        session_id: validated.session_id || resp.session_id,
        token: resp.token,
        user: validated.user,
        expires_at: validated.expires_at || resp.expires_at,
      };
      setUser(validated.user);
      setSession(newSession);
      setStatus('AUTHENTICATED');
      return newSession;
    } catch (err: any) {
      clearAuthToken();
      setStatus('UNAUTHENTICATED');
      setError(err.message || 'Evaluation login failed');
      throw err;
    }
  };

  // Logout action
  const logout = async (): Promise<void> => {
    try {
      await authApi.logout();
    } catch (err) {
      console.warn('Logout API error:', err);
    } finally {
      clearAuthToken();
      setUser(null);
      setSession(null);
      setStatus('UNAUTHENTICATED');
    }
  };

  return (
    <AuthContext.Provider
      value={{
        status,
        user,
        role: user?.role || null,
        session,
        error,
        login,
        loginAsEvaluationRole,
        logout,
        refresh,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
