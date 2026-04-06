import { Pencil, FlaskConical } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatRelativeTime } from '@/utils/format';
import type { Strategy } from '@/services/strategyService';

interface StrategyDetailsProps {
  strategy: Strategy;
  onEdit: (strategy: Strategy) => void;
  onRunBacktest: (id: string) => void;
}

function StatusBadge({ status }: { status: Strategy['status'] }) {
  const config = {
    active: { label: 'Ativa', className: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' },
    testing: { label: 'Testando', className: 'bg-amber-500/10 text-amber-400 border-amber-500/20' },
    inactive: {
      label: 'Inativa',
      className: 'bg-slate-700/50 text-slate-400 border-slate-600/20',
    },
  }[status];

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium',
        config.className,
      )}
    >
      {config.label}
    </span>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-4 py-2">
      <span className="text-xs text-slate-500">{label}</span>
      <span className="text-right text-xs font-medium text-white">{value}</span>
    </div>
  );
}

export function StrategyDetails({ strategy, onEdit, onRunBacktest }: StrategyDetailsProps) {
  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-white">{strategy.name}</h2>
          {strategy.description && (
            <p className="mt-1 text-xs text-slate-500">{strategy.description}</p>
          )}
        </div>
        <StatusBadge status={strategy.status} />
      </div>

      {/* Config */}
      <div className="rounded-lg border border-slate-700 bg-slate-800/40 px-4 divide-y divide-slate-700/50">
        <InfoRow label="Símbolos" value={strategy.symbols.join(', ')} />
        <InfoRow label="Timeframe" value={strategy.timeframe} />
        <InfoRow label="Stop Loss" value={`${strategy.stop_loss_pct}%`} />
        <InfoRow label="Take Profit" value={`${strategy.take_profit_pct}%`} />
      </div>

      {/* Conditions */}
      <div className="space-y-3">
        <div>
          <p className="mb-1.5 text-xs font-medium text-slate-400">Condição de Entrada</p>
          <pre className="rounded-md border border-slate-700 bg-slate-800 px-3 py-2.5 font-mono text-xs text-emerald-400 whitespace-pre-wrap break-words">
            {strategy.entry_condition}
          </pre>
        </div>
        <div>
          <p className="mb-1.5 text-xs font-medium text-slate-400">Condição de Saída</p>
          <pre className="rounded-md border border-slate-700 bg-slate-800 px-3 py-2.5 font-mono text-xs text-red-400 whitespace-pre-wrap break-words">
            {strategy.exit_condition}
          </pre>
        </div>
      </div>

      {/* Stats */}
      <div className="rounded-lg border border-slate-700 bg-slate-800/40 px-4 divide-y divide-slate-700/50">
        <InfoRow
          label="Taxa de Acerto"
          value={
            strategy.win_rate != null
              ? `${(strategy.win_rate * 100).toFixed(1)}%`
              : '—'
          }
        />
        <InfoRow label="Total de Operações" value={String(strategy.total_trades)} />
        <InfoRow
          label="Última Execução"
          value={strategy.last_run ? formatRelativeTime(strategy.last_run) : 'Nunca'}
        />
        <InfoRow
          label="Criada em"
          value={new Intl.DateTimeFormat('pt-BR').format(new Date(strategy.created_at))}
        />
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => onEdit(strategy)}
          className="flex flex-1 items-center justify-center gap-2 rounded-md border border-slate-600 px-4 py-2 text-sm text-white transition-colors hover:border-slate-500 hover:bg-slate-800"
        >
          <Pencil className="h-4 w-4" />
          Editar
        </button>
        <button
          onClick={() => onRunBacktest(strategy.id)}
          className="flex flex-1 items-center justify-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-500"
        >
          <FlaskConical className="h-4 w-4" />
          Executar Backtest
        </button>
      </div>
    </div>
  );
}
