import type { BacktestTrade } from '@/services/backtestService';

interface TradeLogProps {
  trades: BacktestTrade[];
}

function formatDate(dateStr: string): string {
  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: '2-digit',
  }).format(new Date(dateStr));
}

function formatPrice(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(value);
}

export function TradeLog({ trades }: TradeLogProps) {
  if (trades.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-slate-500">
        Nenhuma operação encontrada
      </p>
    );
  }

  return (
    <div className="max-h-80 overflow-y-auto">
      <table className="w-full text-sm">
        <thead className="sticky top-0 bg-slate-900">
          <tr className="border-b border-slate-700 text-left text-xs font-medium uppercase tracking-wide text-slate-400">
            <th className="px-4 py-3">Entrada</th>
            <th className="px-4 py-3">Saída</th>
            <th className="px-4 py-3">Ativo</th>
            <th className="px-4 py-3 text-right">Preço Entrada</th>
            <th className="px-4 py-3 text-right">Preço Saída</th>
            <th className="px-4 py-3 text-right">P&amp;L</th>
            <th className="px-4 py-3 text-right">P&amp;L %</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {trades.map((trade, index) => {
            const isProfit = trade.pnl_pct >= 0;
            return (
              <tr
                key={`${trade.entry_date}-${index}`}
                className="transition-colors hover:bg-slate-800/50"
              >
                <td className="px-4 py-2.5 text-slate-300">
                  {formatDate(trade.entry_date)}
                </td>
                <td className="px-4 py-2.5 text-slate-300">
                  {formatDate(trade.exit_date)}
                </td>
                <td className="px-4 py-2.5">
                  <span className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-xs text-slate-200">
                    {trade.symbol}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-right font-mono text-slate-300">
                  {formatPrice(trade.entry_price)}
                </td>
                <td className="px-4 py-2.5 text-right font-mono text-slate-300">
                  {formatPrice(trade.exit_price)}
                </td>
                <td
                  className={`px-4 py-2.5 text-right font-mono font-semibold ${isProfit ? 'text-emerald-400' : 'text-red-400'}`}
                >
                  {isProfit ? '+' : ''}
                  {formatPrice(trade.pnl)}
                </td>
                <td
                  className={`px-4 py-2.5 text-right font-mono font-semibold ${isProfit ? 'text-emerald-400' : 'text-red-400'}`}
                >
                  {isProfit ? '+' : ''}
                  {trade.pnl_pct.toFixed(2)}%
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
