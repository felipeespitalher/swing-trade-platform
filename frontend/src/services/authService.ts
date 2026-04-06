import { api } from './api';

interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
}

interface LoginRequest {
  email: string;
  password: string;
}

interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface User {
  id: string;
  email: string;
  full_name?: string;
  timezone?: string;
  risk_limit_pct?: number;
  is_active: boolean;
}

export const authService = {
  async register(data: RegisterRequest): Promise<User> {
    const parts = (data.full_name ?? '').trim().split(/\s+/);
    const first_name = parts[0] ?? '';
    const last_name = parts.slice(1).join(' ') || first_name;
    const response = await api.post<User>('/api/auth/register', {
      email: data.email,
      password: data.password,
      first_name,
      last_name,
    });
    return response.data;
  },

  async login(data: LoginRequest): Promise<AuthResponse> {
    const formData = new URLSearchParams();
    formData.append('username', data.email);
    formData.append('password', data.password);
    const response = await api.post<AuthResponse>('/api/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    return response.data;
  },

  async getMe(): Promise<User> {
    const response = await api.get<{
      id: string;
      email: string;
      first_name: string;
      last_name: string;
      timezone: string;
      risk_limit_pct: number;
      is_active?: boolean;
      is_email_verified: boolean;
    }>('/api/users/me');
    const u = response.data;
    return {
      id: u.id,
      email: u.email,
      full_name: `${u.first_name} ${u.last_name}`.trim(),
      timezone: u.timezone,
      risk_limit_pct: u.risk_limit_pct,
      is_active: u.is_active ?? u.is_email_verified,
    };
  },

  async refresh(refreshToken: string): Promise<{ access_token: string }> {
    const response = await api.post<{ access_token: string }>('/api/auth/refresh', {
      refresh_token: refreshToken,
    });
    return response.data;
  },

  async verifyEmail(token: string): Promise<void> {
    await api.get(`/api/auth/verify/${token}`);
  },

  async forgotPassword(email: string): Promise<void> {
    await api.post('/api/auth/forgot-password', { email });
  },

  async resetPassword(token: string, new_password: string): Promise<void> {
    await api.post('/api/auth/reset-password', { token, new_password });
  },
};
