import { cn } from '@/lib/utils';
import { formatDate, formatPercent, formatPrice } from '@/utils/format';

interface Trade {
  id: string;
  symbol: string;
  entry_date: string;
  entry_price: number;
  exit_price: number | null;
  pnl_pct: number | null;
  status: 'open' | 'closed' | 'cancelled';
}

interface TradeTableProps {
  trades: Trade[];
  loading?: boolean;
  maxRows?: number;
}

function StatusBadge({ status }: { status: Trade['status'] }) {
  const config = {
    open: { label: 'Aberta', className: 'bg-blue-500/10 text-blue-400 border-blue-500/20' },
    closed: { label: 'Fechada', className: 'bg-slate-700/50 text-slate-400 border-slate-600/20' },
    cancelled: {
      label: 'Cancelada',
      className: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
    },
  }[status];

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium',
        config.className,
      )}
    >
      {config.label}
    </span>
  );
}

function SkeletonRows() {
  return (
    <>
      {Array.from({ length: 5 }).map((_, i) => (
        <tr key={i}>
          {Array.from({ length: 6 }).map((__, j) => (
            <td key={j} className="px-4 py-3">
              <div className="h-4 animate-pulse rounded bg-slate-700" />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

export function TradeTable({ trades, loading, maxRows = 10 }: TradeTableProps) {
  const rows = trades.slice(0, maxRows);

  return (
    <div className="w-full overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-700">
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
              Símbolo
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
              Data de Entrada
            </th>
            <th className="hidden px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-slate-500 sm:table-cell">
              Preço Entrada
            </th>
            <th className="hidden px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-slate-500 sm:table-cell">
              Preço Saída
            </th>
            <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">
              P&L%
            </th>
            <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">
              Status
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {loading ? (
            <SkeletonRows />
          ) : rows.length === 0 ? (
            <tr>
              <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                Nenhuma operação encontrada
              </td>
            </tr>
          ) : (
            rows.map((trade) => (
              <tr key={trade.id} className="transition-colors hover:bg-slate-800/40">
                <td className="px-4 py-3 font-mono font-semibold text-white">
                  {trade.symbol}
                </td>
                <td className="px-4 py-3 text-slate-400">{formatDate(trade.entry_date)}</td>
                <td className="hidden px-4 py-3 text-right font-mono text-slate-300 sm:table-cell">
                  {formatPrice(trade.entry_price)}
                </td>
                <td className="hidden px-4 py-3 text-right font-mono text-slate-300 sm:table-cell">
                  {trade.exit_price != null ? formatPrice(trade.exit_price) : '—'}
                </td>
                <td className="px-4 py-3 text-right font-mono font-medium">
                  {trade.pnl_pct != null ? (
                    <span
                      className={trade.pnl_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}
                    >
                      {formatPercent(trade.pnl_pct)}
                    </span>
                  ) : (
                    <span className="text-slate-500">—</span>
                  )}
                </td>
                <td className="px-4 py-3 text-right">
                  <StatusBadge status={trade.status} />
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
