import api from './api';

export interface BacktestRequest {
  strategy_id: string;
  symbol: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
}

export interface BacktestTrade {
  entry_date: string;
  exit_date: string;
  symbol: string;
  entry_price: number;
  exit_price: number;
  pnl: number;
  pnl_pct: number;
  direction: 'long' | 'short';
}

export interface BacktestMetrics {
  win_rate: number;
  profit_factor: number;
  sharpe_ratio: number;
  max_drawdown: number;
  total_return: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
}

export interface BacktestResult {
  id: string;
  strategy_id: string;
  symbol: string;
  start_date: string;
  end_date: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  metrics: BacktestMetrics | null;
  equity_curve: Array<{ date: string; value: number }> | null;
  trades: BacktestTrade[] | null;
  error?: string;
}

export const backtestService = {
  async runBacktest(request: BacktestRequest): Promise<BacktestResult> {
    const { data } = await api.post('/api/backtest/run', request);
    return data;
  },
};
