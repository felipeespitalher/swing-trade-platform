import { api } from './api';

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

// Backend response shape
interface BackendStrategy {
  id: string;
  name: string;
  type: string;
  config: Record<string, unknown>;
  symbol: string;
  timeframe: string;
  is_active: boolean;
  created_at: string;
  updated_at: string | null;
  win_rate: number | null;
  total_trades: number;
  last_run: string | null;
}

function toFrontend(s: BackendStrategy): Strategy {
  return {
    id: s.id,
    name: s.name,
    status: s.is_active ? 'active' : 'inactive',
    win_rate: s.win_rate ?? null,
    total_trades: s.total_trades ?? 0,
    last_run: s.last_run ?? s.updated_at,
    created_at: s.created_at,
    description: s.config.description as string | undefined,
    symbols: s.symbol ? [s.symbol] : ['BTC/USDT'],
    timeframe: s.timeframe as '1h' | '4h' | '1d',
    entry_condition: (s.config.entry_condition as string) ?? '',
    exit_condition: (s.config.exit_condition as string) ?? '',
    stop_loss_pct: (s.config.stop_loss_pct as number) ?? 3,
    take_profit_pct: (s.config.take_profit_pct as number) ?? 8,
  };
}

type CreateInput = Omit<Strategy, 'id' | 'created_at' | 'win_rate' | 'total_trades' | 'last_run'>;

function toBackendCreate(data: CreateInput) {
  return {
    name: data.name,
    type: 'rsi_macd',
    symbol: data.symbols[0] ?? 'BTC/USDT',
    timeframe: data.timeframe,
    config: {
      description: data.description ?? '',
      entry_condition: data.entry_condition,
      exit_condition: data.exit_condition,
      stop_loss_pct: data.stop_loss_pct,
      take_profit_pct: data.take_profit_pct,
    },
  };
}

function toBackendUpdate(data: Partial<CreateInput>) {
  const payload: Record<string, unknown> = {};
  if (data.name !== undefined) payload.name = data.name;
  if (data.symbols !== undefined) payload.symbol = data.symbols[0] ?? 'BTC/USDT';
  if (data.timeframe !== undefined) payload.timeframe = data.timeframe;

  const configKeys = [
    'description',
    'entry_condition',
    'exit_condition',
    'stop_loss_pct',
    'take_profit_pct',
  ] as const;

  const hasConfigUpdate = configKeys.some((k) => data[k] !== undefined);
  if (hasConfigUpdate) {
    const config: Record<string, unknown> = {};
    for (const k of configKeys) {
      if (data[k] !== undefined) config[k] = data[k];
    }
    payload.config = config;
  }

  return payload;
}

export const strategyService = {
  async list(): Promise<Strategy[]> {
    const { data } = await api.get<BackendStrategy[]>('/api/strategies');
    return data.map(toFrontend);
  },

  async get(id: string): Promise<Strategy> {
    const { data } = await api.get<BackendStrategy>(`/api/strategies/${id}`);
    return toFrontend(data);
  },

  async create(input: CreateInput): Promise<Strategy> {
    const { data } = await api.post<BackendStrategy>('/api/strategies', toBackendCreate(input));
    return toFrontend(data);
  },

  async update(id: string, input: Partial<CreateInput>): Promise<Strategy> {
    const { data } = await api.put<BackendStrategy>(
      `/api/strategies/${id}`,
      toBackendUpdate(input),
    );
    return toFrontend(data);
  },

  async delete(id: string): Promise<void> {
    await api.delete(`/api/strategies/${id}`);
  },

  async toggle(id: string, status: 'active' | 'inactive'): Promise<Strategy> {
    const { data } = await api.patch<BackendStrategy>(`/api/strategies/${id}/status`, { status });
    return toFrontend(data);
  },
};
