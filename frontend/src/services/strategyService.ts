export interface Strategy {
  id: string;
  name: string;
  status: 'active' | 'inactive' | 'testing';
  win_rate: number | null;
  total_trades: number;
  last_run: string | null;
  created_at: string;
  description?: string;
  symbols: string[];
  timeframe: '1h' | '4h' | '1d';
  entry_condition: string;
  exit_condition: string;
  stop_loss_pct: number;
  take_profit_pct: number;
}

const MOCK_STRATEGIES: Strategy[] = [
  {
    id: '1',
    name: 'RSI Momentum BTC',
    status: 'active',
    win_rate: 0.65,
    total_trades: 48,
    last_run: '2026-04-02T10:00:00Z',
    description: 'RSI oversold bounce strategy for Bitcoin',
    symbols: ['BTC/USDT'],
    timeframe: '4h',
    entry_condition: 'RSI < 30 AND price above 200 SMA',
    exit_condition: 'RSI > 60 OR stop loss hit',
    stop_loss_pct: 3,
    take_profit_pct: 8,
    created_at: '2026-01-15T00:00:00Z',
  },
  {
    id: '2',
    name: 'MACD Cross ETH',
    status: 'testing',
    win_rate: 0.55,
    total_trades: 12,
    last_run: '2026-04-01T14:00:00Z',
    description: 'MACD crossover strategy for Ethereum',
    symbols: ['ETH/USDT', 'BTC/USDT'],
    timeframe: '1d',
    entry_condition: 'MACD line crosses signal line upward',
    exit_condition: 'MACD line crosses signal line downward',
    stop_loss_pct: 5,
    take_profit_pct: 15,
    created_at: '2026-02-20T00:00:00Z',
  },
  {
    id: '3',
    name: 'Volume Breakout ALT',
    status: 'inactive',
    win_rate: null,
    total_trades: 0,
    last_run: null,
    description: 'Volume-based breakout for altcoins',
    symbols: ['SOL/USDT', 'ADA/USDT'],
    timeframe: '1h',
    entry_condition: 'Volume > 2x average AND price breakout',
    exit_condition: 'Volume drops below average',
    stop_loss_pct: 4,
    take_profit_pct: 12,
    created_at: '2026-03-10T00:00:00Z',
  },
];

export const strategyService = {
  async list(): Promise<Strategy[]> {
    return MOCK_STRATEGIES;
  },

  async get(id: string): Promise<Strategy> {
    const found = MOCK_STRATEGIES.find((s) => s.id === id);
    if (!found) throw new Error(`Strategy ${id} not found`);
    return found;
  },

  async create(
    data: Omit<Strategy, 'id' | 'created_at' | 'win_rate' | 'total_trades' | 'last_run'>,
  ): Promise<Strategy> {
    return {
      ...data,
      id: Math.random().toString(36).slice(2),
      win_rate: null,
      total_trades: 0,
      last_run: null,
      created_at: new Date().toISOString(),
    };
  },

  async update(id: string, data: Partial<Strategy>): Promise<Strategy> {
    const existing = MOCK_STRATEGIES.find((s) => s.id === id) ?? MOCK_STRATEGIES[0];
    return { ...existing, ...data, id };
  },

  async delete(_id: string): Promise<void> {
    // mock: no-op
  },

  async toggle(id: string, status: 'active' | 'inactive'): Promise<Strategy> {
    const existing = MOCK_STRATEGIES.find((s) => s.id === id) ?? MOCK_STRATEGIES[0];
    return { ...existing, id, status };
  },
};
