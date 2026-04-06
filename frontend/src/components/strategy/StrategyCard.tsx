import { Pencil, Trash2, Play, Pause } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatRelativeTime } from '@/utils/format';
import type { Strategy } from '@/services/strategyService';

interface StrategyCardProps {
  strategy: Strategy;
  selected?: boolean;
  onSelect: (strategy: Strategy) => void;
  onEdit: (strategy: Strategy) => void;
  onDelete: (id: string) => void;
  onToggle: (id: string, newStatus: 'active' | 'inactive') => void;
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
        'inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium',
        config.className,
      )}
    >
      {config.label}
    </span>
  );
}

export function StrategyCard({
  strategy,
  selected,
  onSelect,
  onEdit,
  onDelete,
  onToggle,
}: StrategyCardProps) {
  const isActive = strategy.status === 'active';

  function handleToggle(e: React.MouseEvent) {
    e.stopPropagation();
    onToggle(strategy.id, isActive ? 'inactive' : 'active');
  }

  function handleEdit(e: React.MouseEvent) {
    e.stopPropagation();
    onEdit(strategy);
  }

  function handleDelete(e: React.MouseEvent) {
    e.stopPropagation();
    onDelete(strategy.id);
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onSelect(strategy)}
      onKeyDown={(e) => e.key === 'Enter' && onSelect(strategy)}
      className={cn(
        'cursor-pointer rounded-lg border p-4 transition-colors',
        selected
          ? 'border-blue-500 bg-blue-500/5'
          : 'border-slate-700 bg-slate-900 hover:border-slate-600',
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <p className="truncate text-sm font-semibold text-white">{strategy.name}</p>
        <StatusBadge status={strategy.status} />
      </div>

      {/* Meta */}
      <p className="mt-1.5 text-xs text-slate-500">
        {strategy.timeframe} &bull; {strategy.symbols.join(', ')}
      </p>

      {/* Stats */}
      <div className="mt-2 flex items-center gap-3 text-xs text-slate-400">
        <span>
          Acerto:{' '}
          <span className="font-medium text-white">
            {strategy.win_rate != null
              ? `${(strategy.win_rate * 100).toFixed(0)}%`
              : '—'}
          </span>
        </span>
        <span className="text-slate-700">|</span>
        <span>
          Operações:{' '}
          <span className="font-medium text-white">{strategy.total_trades}</span>
        </span>
      </div>

      {/* Last run */}
      <p className="mt-1 text-xs text-slate-600">
        {strategy.last_run
          ? `Última execução: ${formatRelativeTime(strategy.last_run)}`
          : 'Nunca executada'}
      </p>

      {/* Actions */}
      <div className="mt-3 flex items-center gap-2 border-t border-slate-800 pt-3">
        <button
          onClick={handleEdit}
          title="Editar estratégia"
          className="flex items-center gap-1 rounded px-2 py-1 text-xs text-slate-400 transition-colors hover:bg-slate-800 hover:text-white"
        >
          <Pencil className="h-3.5 w-3.5" />
          Editar
        </button>
        <button
          onClick={handleToggle}
          title={isActive ? 'Pausar estratégia' : 'Ativar estratégia'}
          className={cn(
            'flex items-center gap-1 rounded px-2 py-1 text-xs transition-colors',
            isActive
              ? 'text-amber-400 hover:bg-amber-500/10'
              : 'text-emerald-400 hover:bg-emerald-500/10',
          )}
        >
          {isActive ? (
            <>
              <Pause className="h-3.5 w-3.5" />
              Pausar
            </>
          ) : (
            <>
              <Play className="h-3.5 w-3.5" />
              Ativar
            </>
          )}
        </button>
        <button
          onClick={handleDelete}
          title="Excluir estratégia"
          className="ml-auto flex items-center gap-1 rounded px-2 py-1 text-xs text-red-500 transition-colors hover:bg-red-500/10"
        >
          <Trash2 className="h-3.5 w-3.5" />
          Excluir
        </button>
      </div>
    </div>
  );
}
