import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import type { BacktestResult } from '@/services/backtestService';

interface ResultsPanelProps {
  result: BacktestResult;
}

interface MetricCardProps {
  label: string;
  value: string;
  positive?: boolean | null;
}

function MetricCard({ label, value, positive }: MetricCardProps) {
  const valueClass =
    positive === null || positive === undefined
      ? 'text-white'
      : positive
        ? 'text-emerald-400'
        : 'text-red-400';

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800 p-4">
      <p className="text-xs text-slate-400">{label}</p>
      <p className={`mt-1 text-xl font-bold font-mono ${valueClass}`}>{value}</p>
    </div>
  );
}

function formatXAxis(dateStr: string): string {
  return new Intl.DateTimeFormat('pt-BR', { month: 'short' }).format(new Date(dateStr));
}

function formatYAxis(value: number): string {
  if (value >= 1000) return `$${(value / 1000).toFixed(0)}k`;
  return `$${value}`;
}

interface TooltipPayload {
  value: number;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: TooltipPayload[];
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  const value = payload[0].value;
  const formatted = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
  }).format(value);
  const date = label
    ? new Intl.DateTimeFormat('pt-BR', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
      }).format(new Date(label))
    : '';
  return (
    <div className="rounded border border-slate-600 bg-slate-800 px-3 py-2 text-xs shadow-lg">
      <p className="text-slate-400">{date}</p>
      <p className="mt-0.5 font-mono font-semibold text-white">{formatted}</p>
    </div>
  );
}

export function ResultsPanel({ result }: ResultsPanelProps) {
  const { metrics, equity_curve } = result;
  if (!metrics) return null;

  const totalReturnPositive = metrics.total_return >= 0;
  const winLossRatio =
    metrics.losing_trades > 0
      ? (metrics.winning_trades / metrics.losing_trades).toFixed(2)
      : '∞';

  return (
    <div className="space-y-4">
      {/* KPI cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <MetricCard
          label="Taxa de Acerto"
          value={`${(metrics.win_rate * 100).toFixed(1)}%`}
          positive={metrics.win_rate >= 0.5}
        />
        <MetricCard
          label="Fator de Lucro"
          value={metrics.profit_factor.toFixed(2)}
          positive={metrics.profit_factor >= 1}
        />
        <MetricCard
          label="Índice Sharpe"
          value={metrics.sharpe_ratio.toFixed(2)}
          positive={metrics.sharpe_ratio >= 1}
        />
        <MetricCard
          label="Drawdown Máximo"
          value={`${metrics.max_drawdown.toFixed(1)}%`}
          positive={false}
        />
      </div>

      {/* Additional stats */}
      <div className="flex flex-wrap gap-4 rounded-lg border border-slate-700 bg-slate-800 px-4 py-3 text-sm">
        <div>
          <span className="text-slate-400">Retorno Total: </span>
          <span
            className={`font-semibold font-mono ${totalReturnPositive ? 'text-emerald-400' : 'text-red-400'}`}
          >
            {totalReturnPositive ? '+' : ''}
            {metrics.total_return.toFixed(2)}%
          </span>
        </div>
        <div>
          <span className="text-slate-400">Total de Trades: </span>
          <span className="font-semibold text-white">{metrics.total_trades}</span>
        </div>
        <div>
          <span className="text-slate-400">Ganhos / Perdas: </span>
          <span className="font-semibold text-emerald-400">{metrics.winning_trades}</span>
          <span className="text-slate-500"> / </span>
          <span className="font-semibold text-red-400">{metrics.losing_trades}</span>
        </div>
        <div>
          <span className="text-slate-400">Razão G/P: </span>
          <span className="font-semibold text-white">{winLossRatio}</span>
        </div>
      </div>

      {/* Equity curve chart */}
      {equity_curve && equity_curve.length > 0 && (
        <div
          className="rounded-lg border border-slate-700 bg-slate-900 p-4"
          role="img"
          aria-label="Curva de capital do backtest"
        >
          <h3 className="mb-3 text-sm font-semibold text-white">Curva de Capital</h3>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={equity_curve} margin={{ top: 4, right: 8, left: 8, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis
                dataKey="date"
                tickFormatter={formatXAxis}
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                axisLine={{ stroke: '#334155' }}
                tickLine={false}
              />
              <YAxis
                tickFormatter={formatYAxis}
                tick={{ fill: '#94a3b8', fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                width={52}
              />
              <Tooltip content={<CustomTooltip />} />
              <Line
                type="monotone"
                dataKey="value"
                stroke="#10b981"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
