import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('@/services/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

import { settingsService } from '@/services/settingsService';
import { api } from '@/services/api';

const mockApi = api as unknown as {
  get: ReturnType<typeof vi.fn>;
  post: ReturnType<typeof vi.fn>;
  put: ReturnType<typeof vi.fn>;
  patch: ReturnType<typeof vi.fn>;
  delete: ReturnType<typeof vi.fn>;
};

beforeEach(() => {
  vi.clearAllMocks();
});

// ─── getSettings ──────────────────────────────────────────────────────────────

describe('settingsService.getSettings', () => {
  it('maps backend user to UserSettings', async () => {
    mockApi.get.mockResolvedValue({
      data: {
        id: 'user-1',
        email: 'user@example.com',
        first_name: 'João',
        last_name: 'Silva',
        timezone: 'America/Sao_Paulo',
        risk_limit_pct: 2,
        is_email_verified: true,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
    });

    const result = await settingsService.getSettings();

    expect(result.full_name).toBe('João Silva');
    expect(result.email).toBe('user@example.com');
    expect(result.timezone).toBe('America/Sao_Paulo');
    expect(result.risk_limit_pct).toBe(2);
  });

  it('trims full_name when last_name is absent', async () => {
    mockApi.get.mockResolvedValue({
      data: {
        id: 'user-1',
        email: 'user@example.com',
        first_name: 'João',
        last_name: '',
        timezone: 'UTC',
        risk_limit_pct: 1,
        is_email_verified: true,
        created_at: '',
        updated_at: '',
      },
    });

    const result = await settingsService.getSettings();

    expect(result.full_name).toBe('João');
  });
});

// ─── updateSettings ───────────────────────────────────────────────────────────

describe('settingsService.updateSettings', () => {
  it('sends only defined fields to PATCH /api/users/me', async () => {
    mockApi.patch.mockResolvedValue({
      data: {
        id: 'user-1',
        email: 'user@example.com',
        first_name: 'João',
        last_name: 'Silva',
        timezone: 'America/New_York',
        risk_limit_pct: 3,
        is_email_verified: true,
        created_at: '',
        updated_at: '',
      },
    });

    await settingsService.updateSettings({ timezone: 'America/New_York', risk_limit_pct: 3 });

    const payload = mockApi.patch.mock.calls[0][1];
    expect(payload).toEqual({ timezone: 'America/New_York', risk_limit_pct: 3 });
    expect(payload).not.toHaveProperty('email');
  });

  it('omits undefined fields from payload', async () => {
    mockApi.patch.mockResolvedValue({
      data: {
        id: 'u1', email: 'e@e.com', first_name: 'A', last_name: 'B',
        timezone: 'UTC', risk_limit_pct: 1, is_email_verified: true,
        created_at: '', updated_at: '',
      },
    });

    await settingsService.updateSettings({ first_name: 'Carlos' });

    const payload = mockApi.patch.mock.calls[0][1];
    expect(payload).toEqual({ first_name: 'Carlos' });
    expect(payload).not.toHaveProperty('timezone');
    expect(payload).not.toHaveProperty('risk_limit_pct');
  });
});

// ─── listExchangeKeys ─────────────────────────────────────────────────────────

describe('settingsService.listExchangeKeys', () => {
  it('extracts keys array from { keys, total } backend response', async () => {
    const keys = [
      { id: 'k1', exchange: 'binance', label: 'Main', api_key_masked: '****abcd', created_at: '2026-01-01', is_active: true },
    ];
    mockApi.get.mockResolvedValue({ data: { keys, total: 1 } });

    const result = await settingsService.listExchangeKeys();

    expect(result).toHaveLength(1);
    expect(result[0].id).toBe('k1');
  });

  it('returns array directly when backend returns plain array', async () => {
    const keys = [
      { id: 'k2', exchange: 'clear_xp', label: 'B3', api_key_masked: '****efgh', created_at: '2026-01-01', is_active: true },
    ];
    mockApi.get.mockResolvedValue({ data: keys });

    const result = await settingsService.listExchangeKeys();

    expect(result).toHaveLength(1);
    expect(result[0].exchange).toBe('clear_xp');
  });

  it('returns empty array when keys field is missing', async () => {
    mockApi.get.mockResolvedValue({ data: { keys: undefined, total: 0 } });

    const result = await settingsService.listExchangeKeys();

    expect(result).toEqual([]);
  });
});

// ─── getAuditLogs ─────────────────────────────────────────────────────────────

describe('settingsService.getAuditLogs', () => {
  it('fetches audit logs with default limit/offset', async () => {
    mockApi.get.mockResolvedValue({
      data: {
        logs: [
          {
            id: 'log-1',
            action: 'login',
            resource_type: null,
            resource_id: null,
            ip_address: '127.0.0.1',
            user_agent: 'Mozilla/5.0',
            created_at: '2026-04-07T10:00:00Z',
          },
        ],
        total: 1,
        limit: 20,
        offset: 0,
      },
    });

    const result = await settingsService.getAuditLogs();

    expect(mockApi.get).toHaveBeenCalledWith('/api/audit/me?limit=20&offset=0');
    expect(result.logs).toHaveLength(1);
    expect(result.total).toBe(1);
    expect(result.logs[0].action).toBe('login');
  });

  it('passes custom limit and offset to query string', async () => {
    mockApi.get.mockResolvedValue({ data: { logs: [], total: 0, limit: 5, offset: 10 } });

    await settingsService.getAuditLogs(5, 10);

    expect(mockApi.get).toHaveBeenCalledWith('/api/audit/me?limit=5&offset=10');
  });

  it('returns empty logs array when logs field is missing', async () => {
    mockApi.get.mockResolvedValue({ data: { total: 0 } });

    const result = await settingsService.getAuditLogs();

    expect(result.logs).toEqual([]);
    expect(result.total).toBe(0);
  });
});

// ─── changePassword ───────────────────────────────────────────────────────────

describe('settingsService.changePassword', () => {
  it('sends old_password and new_password to PATCH /api/users/me/password', async () => {
    mockApi.patch.mockResolvedValue({ data: undefined });

    await settingsService.changePassword('oldPass123', 'newPass456');

    expect(mockApi.patch).toHaveBeenCalledWith('/api/users/me/password', {
      old_password: 'oldPass123',
      new_password: 'newPass456',
    });
  });
});
