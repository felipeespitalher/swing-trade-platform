import api from './api';

export interface DashboardMetrics {
  portfolio_value: number;
  portfolio_change_pct: number;
  win_rate: number;
  profit_factor: number;
  max_drawdown: number;
  monthly_pnl: number;
  monthly_pnl_pct: number;
  active_trades: number;
}

export interface EquityPoint {
  date: string;
  value: number;
}

export interface MonthlyReturn {
  month: string;
  return: number;
}

export interface Trade {
  id: string;
  symbol: string;
  entry_date: string;
  entry_price: number;
  exit_price: number | null;
  pnl_pct: number | null;
  status: 'open' | 'closed' | 'cancelled';
}

export const dashboardService = {
  async getMetrics(): Promise<DashboardMetrics> {
    const { data } = await api.get('/api/dashboard/metrics');
    return data;
  },

  async getEquityCurve(): Promise<EquityPoint[]> {
    const { data } = await api.get('/api/dashboard/equity-curve');
    return data;
  },

  async getMonthlyReturns(): Promise<MonthlyReturn[]> {
    const { data } = await api.get('/api/dashboard/monthly-returns');
    return data;
  },

  async getRecentTrades(): Promise<Trade[]> {
    const { data } = await api.get('/api/dashboard/recent-trades');
    return data;
  },
};
