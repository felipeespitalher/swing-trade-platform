import { motion } from 'framer-motion';
import { DollarSign, TrendingUp, BarChart2, TrendingDown } from 'lucide-react';
import { StatCard } from '@/components/dashboard/StatCard';
import { ChartCard } from '@/components/dashboard/ChartCard';
import { EquityCurve } from '@/components/dashboard/EquityCurve';
import { MonthlyReturns } from '@/components/dashboard/MonthlyReturns';
import { TradeTable } from '@/components/dashboard/TradeTable';
import {
  useDashboardMetrics,
  useEquityCurve,
  useMonthlyReturns,
  useRecentTrades,
} from '@/hooks/useDashboard';
import { formatCurrency, formatPercent } from '@/utils/format';

const pageVariants = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0 },
};

export default function DashboardPage() {
  const { data: metrics, isLoading: metricsLoading } = useDashboardMetrics();
  const { data: equity, isLoading: equityLoading } = useEquityCurve();
  const { data: monthly, isLoading: monthlyLoading } = useMonthlyReturns();
  const { data: trades, isLoading: tradesLoading } = useRecentTrades();

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
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="mt-1 text-sm text-slate-400">Visão geral do seu portfólio</p>
      </div>

      {/* Row 1: Stat cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          title="Valor do Portfólio"
          value={metrics ? formatCurrency(metrics.portfolio_value) : '—'}
          change={metrics ? formatPercent(metrics.portfolio_change_pct) : undefined}
          trend="up"
          icon={<DollarSign className="h-5 w-5" />}
          loading={metricsLoading}
        />
        <StatCard
          title="Taxa de Acerto"
          value={metrics ? `${(metrics.win_rate * 100).toFixed(0)}%` : '—'}
          change={metrics ? `${(metrics.win_rate * 100).toFixed(0)}% das operações` : undefined}
          trend="up"
          icon={<TrendingUp className="h-5 w-5" />}
          loading={metricsLoading}
        />
        <StatCard
          title="Fator de Lucro"
          value={metrics ? metrics.profit_factor.toFixed(2) : '—'}
          change={metrics ? `Índice ${metrics.profit_factor.toFixed(2)}` : undefined}
          trend="up"
          icon={<BarChart2 className="h-5 w-5" />}
          loading={metricsLoading}
        />
        <StatCard
          title="Drawdown Máximo"
          value={metrics ? `${metrics.max_drawdown.toFixed(1)}%` : '—'}
          change={metrics ? formatPercent(metrics.max_drawdown) : undefined}
          trend="down"
          icon={<TrendingDown className="h-5 w-5" />}
          loading={metricsLoading}
        />
      </div>

      {/* Row 2: Charts */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <ChartCard
          title="Curva de Capital"
          subtitle="Evolução do portfólio ao longo do tempo"
          loading={equityLoading}
          className="lg:col-span-2"
        >
          <EquityCurve data={equity ?? []} />
        </ChartCard>

        <ChartCard
          title="Retornos Mensais"
          subtitle="P&L por mês em %"
          loading={monthlyLoading}
          className="lg:col-span-1"
        >
          <div className="flex h-[250px] items-center">
            <MonthlyReturns data={monthly ?? []} />
          </div>
        </ChartCard>
      </div>

      {/* Row 3: Trade table */}
      <div className="rounded-lg border border-slate-700 bg-slate-900">
        <div className="border-b border-slate-700 px-5 py-4">
          <h3 className="text-sm font-semibold text-white">Operações Recentes</h3>
          <p className="mt-0.5 text-xs text-slate-500">Últimas operações registradas</p>
        </div>
        <TradeTable trades={trades ?? []} loading={tradesLoading} maxRows={10} />
      </div>
    </motion.div>
  );
}
