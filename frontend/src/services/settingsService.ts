import { api } from './api';

export interface UserSettings {
  full_name: string;
  first_name: string;
  last_name: string;
  email: string;
  timezone: string;
  risk_limit_pct: number;
}

interface BackendUser {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  timezone: string;
  risk_limit_pct: number;
  is_email_verified: boolean;
  created_at: string;
  updated_at: string;
}

function toSettings(u: BackendUser): UserSettings {
  return {
    full_name: `${u.first_name} ${u.last_name}`.trim(),
    first_name: u.first_name,
    last_name: u.last_name,
    email: u.email,
    timezone: u.timezone,
    risk_limit_pct: u.risk_limit_pct,
  };
}

export interface AuditLog {
  id: string;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
}

export interface ExchangeKey {
  id: string;
  exchange: string;
  label: string;
  api_key_masked: string;
  created_at: string;
  is_active: boolean;
}

export const settingsService = {
  async getSettings(): Promise<UserSettings> {
    const response = await api.get<BackendUser>('/api/users/me');
    return toSettings(response.data);
  },

  async updateSettings(data: Partial<UserSettings>): Promise<UserSettings> {
    const payload: Record<string, unknown> = {};
    if (data.first_name !== undefined) payload.first_name = data.first_name;
    if (data.last_name !== undefined) payload.last_name = data.last_name;
    if (data.timezone !== undefined) payload.timezone = data.timezone;
    if (data.risk_limit_pct !== undefined) payload.risk_limit_pct = data.risk_limit_pct;
    const response = await api.patch<BackendUser>('/api/users/me', payload);
    return toSettings(response.data);
  },

  async changePassword(old_password: string, new_password: string): Promise<void> {
    await api.patch('/api/users/me/password', { old_password, new_password });
  },

  async listExchangeKeys(): Promise<ExchangeKey[]> {
    const response = await api.get<{ keys: ExchangeKey[]; total: number } | ExchangeKey[]>('/api/exchange-keys');
    // Backend returns { keys: [], total: N } — extract the array
    if (Array.isArray(response.data)) return response.data;
    return response.data.keys ?? [];
  },

  async addExchangeKey(data: {
    exchange: string;
    label: string;
    api_key: string;
    api_secret: string;
  }): Promise<ExchangeKey> {
    const response = await api.post('/api/exchange-keys', data);
    return response.data;
  },

  async deleteExchangeKey(id: string): Promise<void> {
    await api.delete(`/api/exchange-keys/${id}`);
  },

  async getAuditLogs(limit = 20, offset = 0): Promise<{ logs: AuditLog[]; total: number }> {
    const response = await api.get<{ logs: AuditLog[]; total: number; limit: number; offset: number }>(
      `/api/audit/me?limit=${limit}&offset=${offset}`,
    );
    return { logs: response.data.logs ?? [], total: response.data.total ?? 0 };
  },
};
