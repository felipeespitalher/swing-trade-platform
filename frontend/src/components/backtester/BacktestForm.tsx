import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Loader2, Play } from 'lucide-react';
import { useStrategies } from '@/hooks/useStrategy';
import type { BacktestRequest } from '@/services/backtestService';

const schema = z
  .object({
    strategy_id: z.string().min(1, 'Selecione uma estratégia'),
    symbol: z
      .string()
      .min(1, 'Informe o símbolo')
      .regex(/^[A-Z0-9]+\/[A-Z0-9]+$/, 'Formato esperado: XXX/USDT'),
    start_date: z.string().min(1, 'Informe a data de início'),
    end_date: z.string().min(1, 'Informe a data de término'),
    initial_capital: z.coerce
      .number({ invalid_type_error: 'Informe um número válido' })
      .min(100, 'Capital mínimo: R$ 100'),
  })
  .refine((data) => data.start_date < data.end_date, {
    message: 'A data de início deve ser anterior à data de término',
    path: ['end_date'],
  });

type FormValues = z.infer<typeof schema>;

interface BacktestFormProps {
  onSubmit: (data: BacktestRequest) => void;
  isRunning: boolean;
  initialStrategyId?: string;
}

export function BacktestForm({ onSubmit, isRunning, initialStrategyId }: BacktestFormProps) {
  const { data: strategies, isLoading: loadingStrategies } = useStrategies();

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      strategy_id: initialStrategyId ?? '',
      symbol: 'BTC/USDT',
      initial_capital: 10000,
      start_date: '2025-01-01',
      end_date: '2026-01-01',
    },
  });

  useEffect(() => {
    if (initialStrategyId) {
      setValue('strategy_id', initialStrategyId);
    }
  }, [initialStrategyId, setValue]);

  function handleFormSubmit(values: FormValues) {
    onSubmit(values);
  }

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-4">
      {/* Strategy selector */}
      <div>
        <label
          htmlFor="strategy_id"
          className="block text-sm font-medium text-slate-300 mb-1"
        >
          Estratégia
        </label>
        <select
          id="strategy_id"
          {...register('strategy_id')}
          disabled={loadingStrategies}
          className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50"
        >
          <option value="">
            {loadingStrategies ? 'Carregando...' : 'Selecione uma estratégia'}
          </option>
          {strategies?.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
        {errors.strategy_id && (
          <p className="mt-1 text-xs text-red-400">{errors.strategy_id.message}</p>
        )}
      </div>

      {/* Symbol + Initial Capital row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label
            htmlFor="symbol"
            className="block text-sm font-medium text-slate-300 mb-1"
          >
            Ativo (par)
          </label>
          <input
            id="symbol"
            type="text"
            placeholder="BTC/USDT"
            {...register('symbol')}
            className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          {errors.symbol && (
            <p className="mt-1 text-xs text-red-400">{errors.symbol.message}</p>
          )}
        </div>

        <div>
          <label
            htmlFor="initial_capital"
            className="block text-sm font-medium text-slate-300 mb-1"
          >
            Capital Inicial (USD)
          </label>
          <input
            id="initial_capital"
            type="number"
            min={100}
            step={100}
            {...register('initial_capital')}
            className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          {errors.initial_capital && (
            <p className="mt-1 text-xs text-red-400">{errors.initial_capital.message}</p>
          )}
        </div>
      </div>

      {/* Date range row */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label
            htmlFor="start_date"
            className="block text-sm font-medium text-slate-300 mb-1"
          >
            Data de Início
          </label>
          <input
            id="start_date"
            type="date"
            {...register('start_date')}
            className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          {errors.start_date && (
            <p className="mt-1 text-xs text-red-400">{errors.start_date.message}</p>
          )}
        </div>

        <div>
          <label
            htmlFor="end_date"
            className="block text-sm font-medium text-slate-300 mb-1"
          >
            Data de Término
          </label>
          <input
            id="end_date"
            type="date"
            {...register('end_date')}
            className="w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          {errors.end_date && (
            <p className="mt-1 text-xs text-red-400">{errors.end_date.message}</p>
          )}
        </div>
      </div>

      {/* Submit button */}
      <button
        type="submit"
        disabled={isRunning}
        className="flex w-full items-center justify-center gap-2 rounded-md bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isRunning ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Executando...
          </>
        ) : (
          <>
            <Play className="h-4 w-4" />
            Executar Backtest
          </>
        )}
      </button>
    </form>
  );
}
