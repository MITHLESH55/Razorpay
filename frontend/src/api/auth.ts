/**
 * RiskOrbit — Authentication API Module
 */
import { apiRequest, clearAuthToken } from './client';
import { AuthSession, DemoUserRecord, GoogleOAuthConfig, UserContext } from '../types';

export interface LoginParams {
  username_or_email: string;
  password: string;
  remember_me?: boolean;
}

export interface GoogleLoginParams {
  id_token?: string;
  code?: string;
  redirect_uri?: string;
}

export interface LoginResponse {
  token: string;
  token_type: string;
  session_id: string;
  user: UserContext;
  expires_at: number;
}

export interface SessionValidateResponse {
  valid: boolean;
  session_id: string;
  user: UserContext;
  expires_at: number;
}

export const authApi = {
  /**
  * Authenticate with email or analyst ID.
   */
  async login(params: LoginParams): Promise<AuthSession> {
    const payload: Record<string, any> = {
      username_or_email: params.username_or_email.trim(),
      password: params.password,
      remember_me: params.remember_me !== false,
    };

    const data = await apiRequest<LoginResponse>('/api/v2/ops/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
      skipAuth: true,
    });
    return {
      token: data.token,
      user: data.user,
      session_id: data.session_id,
      expires_at: data.expires_at,
    };
  },

  /**
   * Validate active session token
   */
  async validateSession(): Promise<SessionValidateResponse> {
    return apiRequest<SessionValidateResponse>('/api/v2/ops/auth/session', {
      method: 'GET',
    });
  },

  /**
   * Invalidate active analyst session
   */
  async logout(): Promise<void> {
    try {
      await apiRequest('/api/v2/ops/auth/logout', {
        method: 'POST',
      });
    } finally {
      clearAuthToken();
    }
  },

  /**
   * Retrieve pre-seeded demo analyst accounts
   */
  async getDemoUsers(): Promise<DemoUserRecord[]> {
    return apiRequest<DemoUserRecord[]>('/api/v2/ops/auth/demo-users', {
      method: 'GET',
      skipAuth: true,
    });
  },

  /**
   * Retrieve Google OAuth configuration status
   */
  async getGoogleConfig(): Promise<GoogleOAuthConfig> {
    return apiRequest<GoogleOAuthConfig>('/api/v2/ops/auth/google/config', {
      method: 'GET',
      skipAuth: true,
    });
  },

  /**
   * Complete Google OAuth login with token/code
   */
  async loginWithGoogle(params: GoogleLoginParams): Promise<AuthSession> {
    const data = await apiRequest<LoginResponse>('/api/v2/ops/auth/google/login', {
      method: 'POST',
      body: JSON.stringify(params),
      skipAuth: true,
    });
    return {
      token: data.token,
      user: data.user,
      session_id: data.session_id,
      expires_at: data.expires_at,
    };
  },
};
