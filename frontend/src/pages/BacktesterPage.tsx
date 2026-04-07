import { useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { BacktestForm } from '@/components/backtester/BacktestForm';
import { BacktestStatus } from '@/components/backtester/BacktestStatus';
import { ResultsPanel } from '@/components/backtester/ResultsPanel';
import { TradeLog } from '@/components/backtester/TradeLog';
import { useBacktest } from '@/hooks/useBacktest';
import { useNotification } from '@/hooks/useNotification';
import type { BacktestRequest } from '@/services/backtestService';

const pageVariants = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0 },
};

export default function BacktesterPage() {
  const [searchParams] = useSearchParams();
  const initialStrategyId = searchParams.get('strategy_id') ?? undefined;
  const { result, isRunning, error, runBacktest } = useBacktest();
  const notify = useNotification();

  async function handleSubmit(request: BacktestRequest) {
    try {
      await runBacktest(request);
      notify.success('Backtest concluído', 'Resultados disponíveis abaixo.');
    } catch {
      notify.error('Erro no backtest', 'Não foi possível executar o backtest.');
    }
  }

  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      transition={{ duration: 0.25, ease: 'easeOut' }}
      className="space-y-6"
    >
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Backtester</h1>
        <p className="mt-1 text-sm text-slate-400">
          Valide suas estratégias com dados históricos
        </p>
      </div>

      {/* Section 1: Form */}
      <div className="rounded-lg border border-slate-700 bg-slate-900 p-5">
        <h2 className="mb-4 text-sm font-semibold text-white">Configurar Simulação</h2>
        <BacktestForm onSubmit={handleSubmit} isRunning={isRunning} initialStrategyId={initialStrategyId} />
      </div>

      {/* Section 2: Status / Results */}
      {(isRunning || result || error) && (
        <div className="rounded-lg border border-slate-700 bg-slate-900 p-5">
          {isRunning && <BacktestStatus />}

          {error && !isRunning && (
            <div className="rounded-md border border-red-800 bg-red-950/40 px-4 py-3 text-sm text-red-400">
              {error}
            </div>
          )}

          {result && !isRunning && result.status === 'completed' && (
            <>
              <h2 className="mb-4 text-sm font-semibold text-white">Resultados</h2>
              <ResultsPanel result={result} />
            </>
          )}
        </div>
      )}

      {/* Section 3: Trade Log */}
      {result && !isRunning && result.trades && result.trades.length > 0 && (
        <div className="rounded-lg border border-slate-700 bg-slate-900">
          <div className="border-b border-slate-700 px-5 py-4">
            <h2 className="text-sm font-semibold text-white">Registro de Operações</h2>
            <p className="mt-0.5 text-xs text-slate-500">
              {result.trades.length} operações simuladas
            </p>
          </div>
          <TradeLog trades={result.trades} />
        </div>
      )}
    </motion.div>
  );
}
