import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';

interface MonthlyReturn {
  month: string;
  return: number;
}

interface MonthlyReturnsProps {
  data: MonthlyReturn[];
  loading?: boolean;
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
  const sign = value >= 0 ? '+' : '';
  const color = value >= 0 ? '#10B981' : '#EF4444';
  return (
    <div className="rounded border border-slate-600 bg-slate-800 px-3 py-2 text-xs shadow-lg">
      <p className="text-slate-400">{label}</p>
      <p className="mt-0.5 font-mono font-semibold" style={{ color }}>
        {sign}{value.toFixed(1)}%
      </p>
    </div>
  );
}

function formatYAxis(value: number): string {
  return `${value}%`;
}

export function MonthlyReturns({ data, loading }: MonthlyReturnsProps) {
  if (loading) {
    return <div className="h-[200px] w-full animate-pulse rounded bg-slate-800" />;
  }

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
        <XAxis
          dataKey="month"
          tick={{ fill: '#94a3b8', fontSize: 11 }}
          axisLine={{ stroke: '#334155' }}
          tickLine={false}
        />
        <YAxis
          tickFormatter={formatYAxis}
          tick={{ fill: '#94a3b8', fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          width={40}
        />
        <Tooltip content={<CustomTooltip />} />
        <Bar dataKey="return" isAnimationActive={false} radius={[3, 3, 0, 0]}>
          {data.map((entry, index) => (
            <Cell
              key={`cell-${index}`}
              fill={entry.return >= 0 ? '#10B981' : '#EF4444'}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
