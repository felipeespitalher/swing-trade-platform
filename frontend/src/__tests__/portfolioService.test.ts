import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the api module before importing portfolioService
vi.mock('@/services/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

import { portfolioService } from '@/services/portfolioService';
import { api } from '@/services/api';

const mockApi = api as unknown as {
  get: ReturnType<typeof vi.fn>;
  post: ReturnType<typeof vi.fn>;
  put: ReturnType<typeof vi.fn>;
  patch: ReturnType<typeof vi.fn>;
  delete: ReturnType<typeof vi.fn>;
};

const MOCK_PORTFOLIO = {
  id: 'test-uuid-1',
  name: 'Carteira Teste',
  description: 'Descrição de teste',
  capital_allocation: 10000,
  risk_profile: 'moderado' as const,
  mode: 'paper' as const,
  is_active: true,
  strategy_count: 0,
  total_pnl: null,
  created_at: '2026-04-07T10:00:00Z',
  updated_at: null,
};

const MOCK_STRATEGY = {
  id: 'strategy-uuid-1',
  name: 'RSI Strategy',
  type: 'rsi_only',
  is_active: true,
  symbol: 'BTC/USDT',
  timeframe: '1h',
  win_rate: 0.6,
  total_trades: 10,
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe('portfolioService.list', () => {
  it('returns array from GET /api/portfolios', async () => {
    mockApi.get.mockResolvedValue({ data: [MOCK_PORTFOLIO] });

    const result = await portfolioService.list();

    expect(mockApi.get).toHaveBeenCalledWith('/api/portfolios');
    expect(result).toHaveLength(1);
    expect(result[0].id).toBe('test-uuid-1');
  });

  it('returns empty array when no portfolios', async () => {
    mockApi.get.mockResolvedValue({ data: [] });

    const result = await portfolioService.list();

    expect(result).toEqual([]);
  });
});

describe('portfolioService.get', () => {
  it('returns single portfolio from GET /api/portfolios/:id', async () => {
    mockApi.get.mockResolvedValue({ data: MOCK_PORTFOLIO });

    const result = await portfolioService.get('test-uuid-1');

    expect(mockApi.get).toHaveBeenCalledWith('/api/portfolios/test-uuid-1');
    expect(result.name).toBe('Carteira Teste');
    expect(result.mode).toBe('paper');
  });
});

describe('portfolioService.create', () => {
  it('sends POST to /api/portfolios with correct payload', async () => {
    mockApi.post.mockResolvedValue({ data: MOCK_PORTFOLIO });

    const input = {
      name: 'Carteira Teste',
      description: 'Descrição de teste',
      capital_allocation: 10000,
      risk_profile: 'moderado' as const,
      mode: 'paper' as const,
    };

    const result = await portfolioService.create(input);

    expect(mockApi.post).toHaveBeenCalledWith('/api/portfolios', input);
    expect(result.id).toBe('test-uuid-1');
  });

  it('sends live mode portfolio correctly', async () => {
    const liveMock = { ...MOCK_PORTFOLIO, mode: 'live' as const };
    mockApi.post.mockResolvedValue({ data: liveMock });

    const input = {
      name: 'Carteira Real',
      capital_allocation: 5000,
      risk_profile: 'agressivo' as const,
      mode: 'live' as const,
    };

    const result = await portfolioService.create(input);

    expect(mockApi.post).toHaveBeenCalledWith('/api/portfolios', input);
    expect(result.mode).toBe('live');
  });
});

describe('portfolioService.update', () => {
  it('sends PUT to /api/portfolios/:id', async () => {
    const updated = { ...MOCK_PORTFOLIO, name: 'Nome Atualizado' };
    mockApi.put.mockResolvedValue({ data: updated });

    const result = await portfolioService.update('test-uuid-1', { name: 'Nome Atualizado' });

    expect(mockApi.put).toHaveBeenCalledWith('/api/portfolios/test-uuid-1', { name: 'Nome Atualizado' });
    expect(result.name).toBe('Nome Atualizado');
  });
});

describe('portfolioService.delete', () => {
  it('sends DELETE to /api/portfolios/:id', async () => {
    mockApi.delete.mockResolvedValue({ data: undefined });

    await portfolioService.delete('test-uuid-1');

    expect(mockApi.delete).toHaveBeenCalledWith('/api/portfolios/test-uuid-1');
  });
});

describe('portfolioService.listStrategies', () => {
  it('returns strategies from GET /api/portfolios/:id/strategies', async () => {
    mockApi.get.mockResolvedValue({ data: [MOCK_STRATEGY] });

    const result = await portfolioService.listStrategies('test-uuid-1');

    expect(mockApi.get).toHaveBeenCalledWith('/api/portfolios/test-uuid-1/strategies');
    expect(result).toHaveLength(1);
    expect(result[0].symbol).toBe('BTC/USDT');
  });

  it('returns empty array when no strategies', async () => {
    mockApi.get.mockResolvedValue({ data: [] });

    const result = await portfolioService.listStrategies('test-uuid-1');

    expect(result).toEqual([]);
  });
});

describe('portfolioService.assignStrategies', () => {
  it('sends PATCH to /api/portfolios/:id/strategies', async () => {
    const strategyIds = ['s1', 's2'];
    mockApi.patch.mockResolvedValue({ data: strategyIds });

    const result = await portfolioService.assignStrategies('test-uuid-1', strategyIds);

    expect(mockApi.patch).toHaveBeenCalledWith(
      '/api/portfolios/test-uuid-1/strategies',
      { strategy_ids: strategyIds },
    );
    expect(result).toEqual(strategyIds);
  });

  it('sends empty array to unlink all strategies', async () => {
    mockApi.patch.mockResolvedValue({ data: [] });

    const result = await portfolioService.assignStrategies('test-uuid-1', []);

    expect(mockApi.patch).toHaveBeenCalledWith(
      '/api/portfolios/test-uuid-1/strategies',
      { strategy_ids: [] },
    );
    expect(result).toEqual([]);
  });
});

describe('portfolioService.getMarketStatus', () => {
  it('fetches market status for b3 by default', async () => {
    const statusMock = {
      is_open: false,
      market_name: 'B3',
      reason: 'outside_trading_hours',
    };
    mockApi.get.mockResolvedValue({ data: statusMock });

    const result = await portfolioService.getMarketStatus('test-uuid-1');

    expect(mockApi.get).toHaveBeenCalledWith(
      '/api/portfolios/test-uuid-1/market-status?exchange=b3',
    );
    expect(result.market_name).toBe('B3');
  });

  it('uses provided exchange param', async () => {
    const statusMock = { is_open: true, market_name: 'Binance', reason: '24h_market' };
    mockApi.get.mockResolvedValue({ data: statusMock });

    const result = await portfolioService.getMarketStatus('test-uuid-1', 'binance');

    expect(mockApi.get).toHaveBeenCalledWith(
      '/api/portfolios/test-uuid-1/market-status?exchange=binance',
    );
    expect(result.is_open).toBe(true);
  });
});
