import { api } from './api';

export interface UserSettings {
  full_name: string;
  email: string;
  timezone: string;
  risk_limit_pct: number;
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
    const response = await api.get('/api/users/me');
    return response.data;
  },

  async updateSettings(data: Partial<UserSettings>): Promise<UserSettings> {
    const response = await api.patch('/api/users/me', data);
    return response.data;
  },

  async changePassword(old_password: string, new_password: string): Promise<void> {
    await api.patch('/api/users/me/password', { old_password, new_password });
  },

  async listExchangeKeys(): Promise<ExchangeKey[]> {
    const response = await api.get('/api/exchange-keys');
    return response.data;
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
};
