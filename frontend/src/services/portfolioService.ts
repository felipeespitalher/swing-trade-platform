import { api } from './api';

export type PortfolioMode = 'paper' | 'live';
export type RiskProfile = 'conservador' | 'moderado' | 'agressivo';

export interface Portfolio {
  id: string;
  name: string;
  description: string | null;
  capital_allocation: number;
  risk_profile: RiskProfile;
  mode: PortfolioMode;
  is_active: boolean;
  strategy_count: number;
  total_pnl: number | null;
  created_at: string;
  updated_at: string | null;
}

export interface PortfolioStrategy {
  id: string;
  name: string;
  type: string;
  is_active: boolean;
  symbol: string;
  timeframe: string;
  win_rate: number | null;
  total_trades: number;
}

export interface MarketStatus {
  is_open: boolean;
  market_name: string;
  local_time?: string;
  open_time?: string;
  close_time?: string;
  timezone?: string;
  reason: string;
}

export interface CreatePortfolioInput {
  name: string;
  description?: string;
  capital_allocation: number;
  risk_profile: RiskProfile;
  mode: PortfolioMode;
}

export interface UpdatePortfolioInput {
  name?: string;
  description?: string;
  capital_allocation?: number;
  risk_profile?: RiskProfile;
  mode?: PortfolioMode;
  is_active?: boolean;
}

export const portfolioService = {
  async list(): Promise<Portfolio[]> {
    const { data } = await api.get<Portfolio[]>('/api/portfolios');
    return data;
  },

  async get(id: string): Promise<Portfolio> {
    const { data } = await api.get<Portfolio>(`/api/portfolios/${id}`);
    return data;
  },

  async create(input: CreatePortfolioInput): Promise<Portfolio> {
    const { data } = await api.post<Portfolio>('/api/portfolios', input);
    return data;
  },

  async update(id: string, input: UpdatePortfolioInput): Promise<Portfolio> {
    const { data } = await api.put<Portfolio>(`/api/portfolios/${id}`, input);
    return data;
  },

  async delete(id: string): Promise<void> {
    await api.delete(`/api/portfolios/${id}`);
  },

  async listStrategies(id: string): Promise<PortfolioStrategy[]> {
    const { data } = await api.get<PortfolioStrategy[]>(`/api/portfolios/${id}/strategies`);
    return data;
  },

  async assignStrategies(id: string, strategy_ids: string[]): Promise<string[]> {
    const { data } = await api.patch<string[]>(`/api/portfolios/${id}/strategies`, { strategy_ids });
    return data;
  },

  async getMarketStatus(portfolioId: string, exchange = 'b3'): Promise<MarketStatus> {
    const { data } = await api.get<MarketStatus>(
      `/api/portfolios/${portfolioId}/market-status?exchange=${exchange}`,
    );
    return data;
  },
};
