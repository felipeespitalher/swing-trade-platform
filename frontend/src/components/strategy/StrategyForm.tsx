import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { cn } from '@/lib/utils';
import type { Strategy } from '@/services/strategyService';

const strategySchema = z.object({
  name: z.string().min(3, 'Nome deve ter pelo menos 3 caracteres'),
  description: z.string().optional(),
  symbols: z.string().min(1, 'Informe pelo menos um símbolo'),
  timeframe: z.enum(['1h', '4h', '1d']),
  entry_condition: z.string().min(5, 'Descreva a condição de entrada'),
  exit_condition: z.string().min(5, 'Descreva a condição de saída'),
  stop_loss_pct: z.coerce.number().min(0.5, 'Mínimo 0.5%').max(20, 'Máximo 20%'),
  take_profit_pct: z.coerce.number().min(1, 'Mínimo 1%').max(50, 'Máximo 50%'),
});

type StrategyFormValues = z.infer<typeof strategySchema>;

interface StrategyFormProps {
  initial?: Strategy;
  onSubmit: (
    data: Omit<Strategy, 'id' | 'created_at' | 'win_rate' | 'total_trades' | 'last_run'>,
  ) => void;
  onCancel: () => void;
  isSubmitting?: boolean;
}

function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return <p className="mt-1 text-xs text-red-400">{message}</p>;
}

const labelClass = 'block text-xs font-medium text-slate-400 mb-1';
const inputClass = cn(
  'w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white',
  'placeholder-slate-500 outline-none transition-colors',
  'focus:border-blue-500 focus:ring-1 focus:ring-blue-500/30',
);

export function StrategyForm({ initial, onSubmit, onCancel, isSubmitting }: StrategyFormProps) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<StrategyFormValues>({
    resolver: zodResolver(strategySchema),
    defaultValues: initial
      ? {
          name: initial.name,
          description: initial.description ?? '',
          symbols: initial.symbols.join(', '),
          timeframe: initial.timeframe,
          entry_condition: initial.entry_condition,
          exit_condition: initial.exit_condition,
          stop_loss_pct: initial.stop_loss_pct,
          take_profit_pct: initial.take_profit_pct,
        }
      : {
          timeframe: '4h',
          stop_loss_pct: 3,
          take_profit_pct: 8,
        },
  });

  useEffect(() => {
    if (initial) {
      reset({
        name: initial.name,
        description: initial.description ?? '',
        symbols: initial.symbols.join(', '),
        timeframe: initial.timeframe,
        entry_condition: initial.entry_condition,
        exit_condition: initial.exit_condition,
        stop_loss_pct: initial.stop_loss_pct,
        take_profit_pct: initial.take_profit_pct,
      });
    }
  }, [initial, reset]);

  function onValid(values: StrategyFormValues) {
    onSubmit({
      name: values.name,
      description: values.description,
      symbols: values.symbols.split(',').map((s) => s.trim()).filter(Boolean),
      timeframe: values.timeframe,
      entry_condition: values.entry_condition,
      exit_condition: values.exit_condition,
      stop_loss_pct: values.stop_loss_pct,
      take_profit_pct: values.take_profit_pct,
      status: initial?.status ?? 'inactive',
      portfolio_id: initial?.portfolio_id ?? null,
    });
  }

  return (
    <form onSubmit={handleSubmit(onValid)} className="space-y-4">
      <div>
        <h2 className="text-base font-semibold text-white">
          {initial ? 'Editar Estratégia' : 'Nova Estratégia'}
        </h2>
        <p className="mt-0.5 text-xs text-slate-500">
          Preencha as configurações da estratégia de trading
        </p>
      </div>

      {/* Name */}
      <div>
        <label className={labelClass} htmlFor="name">
          Nome
        </label>
        <input
          id="name"
          {...register('name')}
          placeholder="Ex: RSI Momentum BTC"
          className={inputClass}
        />
        <FieldError message={errors.name?.message} />
      </div>

      {/* Description */}
      <div>
        <label className={labelClass} htmlFor="description">
          Descrição <span className="text-slate-600">(opcional)</span>
        </label>
        <textarea
          id="description"
          {...register('description')}
          rows={2}
          placeholder="Descreva brevemente a estratégia..."
          className={cn(inputClass, 'resize-none')}
        />
      </div>

      {/* Symbols */}
      <div>
        <label className={labelClass} htmlFor="symbols">
          Símbolos <span className="text-slate-600">(separados por vírgula)</span>
        </label>
        <input
          id="symbols"
          {...register('symbols')}
          placeholder="BTC/USDT, ETH/USDT"
          className={inputClass}
        />
        <FieldError message={errors.symbols?.message} />
      </div>

      {/* Timeframe */}
      <div>
        <label className={labelClass} htmlFor="timeframe">
          Timeframe
        </label>
        <select id="timeframe" {...register('timeframe')} className={inputClass}>
          <option value="1h">1 hora</option>
          <option value="4h">4 horas</option>
          <option value="1d">1 dia</option>
        </select>
        <FieldError message={errors.timeframe?.message} />
      </div>

      {/* Entry condition */}
      <div>
        <label className={labelClass} htmlFor="entry_condition">
          Condição de Entrada
        </label>
        <textarea
          id="entry_condition"
          {...register('entry_condition')}
          rows={2}
          placeholder="Ex: RSI < 30 AND price above 200 SMA"
          className={cn(inputClass, 'resize-none font-mono text-xs')}
        />
        <FieldError message={errors.entry_condition?.message} />
      </div>

      {/* Exit condition */}
      <div>
        <label className={labelClass} htmlFor="exit_condition">
          Condição de Saída
        </label>
        <textarea
          id="exit_condition"
          {...register('exit_condition')}
          rows={2}
          placeholder="Ex: RSI > 60 OR stop loss hit"
          className={cn(inputClass, 'resize-none font-mono text-xs')}
        />
        <FieldError message={errors.exit_condition?.message} />
      </div>

      {/* Stop loss + take profit */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={labelClass} htmlFor="stop_loss_pct">
            Stop Loss (%)
          </label>
          <input
            id="stop_loss_pct"
            type="number"
            step="0.1"
            min="0.5"
            max="20"
            {...register('stop_loss_pct')}
            className={inputClass}
          />
          <FieldError message={errors.stop_loss_pct?.message} />
        </div>
        <div>
          <label className={labelClass} htmlFor="take_profit_pct">
            Take Profit (%)
          </label>
          <input
            id="take_profit_pct"
            type="number"
            step="0.1"
            min="1"
            max="50"
            {...register('take_profit_pct')}
            className={inputClass}
          />
          <FieldError message={errors.take_profit_pct?.message} />
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-end gap-3 pt-2">
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md px-4 py-2 text-sm text-slate-400 transition-colors hover:text-white"
        >
          Cancelar
        </button>
        <button
          type="submit"
          disabled={isSubmitting}
          className={cn(
            'rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-500',
            isSubmitting && 'cursor-not-allowed opacity-60',
          )}
        >
          {isSubmitting ? 'Salvando...' : initial ? 'Salvar Alterações' : 'Criar Estratégia'}
        </button>
      </div>
    </form>
  );
}
