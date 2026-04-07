import { useState, useEffect, useCallback } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Plus,
  Trash2,
  Wallet,
  Loader2,
  ChevronDown,
  ChevronUp,
  FlaskConical,
  Banknote,
  Clock,
  CheckCircle2,
  XCircle,
  RefreshCw,
  LinkIcon,
} from 'lucide-react';
import { portfolioService, type Portfolio, type PortfolioStrategy, type MarketStatus } from '@/services/portfolioService';
import { strategyService, type Strategy } from '@/services/strategyService';
import { useNotification } from '@/hooks/useNotification';

const pageVariants = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0 },
};

const portfolioSchema = z.object({
  name: z.string().min(2, 'Nome deve ter ao menos 2 caracteres'),
  description: z.string().optional(),
  capital_allocation: z.coerce.number().min(0, 'Valor inválido'),
  risk_profile: z.enum(['conservador', 'moderado', 'agressivo']),
  mode: z.enum(['paper', 'live']),
});
type PortfolioFormValues = z.infer<typeof portfolioSchema>;

const riskBadge: Record<string, string> = {
  conservador: 'bg-emerald-900/50 text-emerald-400',
  moderado: 'bg-blue-900/50 text-blue-400',
  agressivo: 'bg-red-900/50 text-red-400',
};

const inputCls =
  'w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50';

function InputField({
  id,
  label,
  error,
  children,
}: {
  id: string;
  label: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-slate-300 mb-1">
        {label}
      </label>
      {children}
      {error && <p className="mt-1 text-xs text-red-400">{error}</p>}
    </div>
  );
}

// ─── Market Status Badge ──────────────────────────────────────────────────────
function MarketStatusBadge({ status }: { status: MarketStatus | null }) {
  if (!status) return null;

  const reasonLabels: Record<string, string> = {
    open: 'Pregão aberto',
    weekend: 'Fim de semana',
    holiday: 'Feriado',
    outside_trading_hours: 'Fora do pregão',
    '24h_market': 'Mercado 24h',
    unknown_exchange: '24h',
  };

  const label = reasonLabels[status.reason] ?? (status.is_open ? 'Aberto' : 'Fechado');

  return (
    <span
      className={`flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${
        status.is_open
          ? 'bg-emerald-900/50 text-emerald-400'
          : 'bg-slate-700 text-slate-400'
      }`}
    >
      {status.is_open ? (
        <CheckCircle2 className="h-3 w-3" />
      ) : (
        <XCircle className="h-3 w-3" />
      )}
      {label}
      {status.local_time && (
        <span className="ml-0.5 opacity-70">{status.local_time.split(' ')[1]}</span>
      )}
    </span>
  );
}

// ─── Strategy Selector Modal ──────────────────────────────────────────────────
function StrategySelector({
  portfolioId,
  currentStrategyIds,
  onClose,
  onSaved,
}: {
  portfolioId: string;
  currentStrategyIds: string[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [allStrategies, setAllStrategies] = useState<Strategy[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set(currentStrategyIds));
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const notify = useNotification();

  useEffect(() => {
    strategyService.list().then(setAllStrategies).finally(() => setLoading(false));
  }, []);

  async function handleSave() {
    setSaving(true);
    try {
      await portfolioService.assignStrategies(portfolioId, [...selected]);
      notify.success('Estratégias atualizadas', 'Associação salva com sucesso.');
      onSaved();
    } catch {
      notify.error('Erro', 'Não foi possível atualizar as estratégias.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        className="w-full max-w-md rounded-xl border border-slate-700 bg-slate-900 p-5 shadow-2xl"
      >
        <h2 className="mb-4 text-sm font-semibold text-white">Associar Estratégias</h2>
        {loading ? (
          <div className="flex justify-center py-6">
            <Loader2 className="h-5 w-5 animate-spin text-slate-400" />
          </div>
        ) : allStrategies.length === 0 ? (
          <p className="text-sm text-slate-500 py-4">Nenhuma estratégia criada ainda.</p>
        ) : (
          <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
            {allStrategies.map((s) => (
              <label
                key={s.id}
                className="flex cursor-pointer items-center gap-3 rounded-lg border border-slate-700 bg-slate-800/50 px-3 py-2.5 hover:border-slate-500 transition-colors"
              >
                <input
                  type="checkbox"
                  checked={selected.has(s.id)}
                  onChange={(e) => {
                    const next = new Set(selected);
                    if (e.target.checked) { next.add(s.id); } else { next.delete(s.id); }
                    setSelected(next);
                  }}
                  className="accent-blue-500"
                />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white truncate">{s.name}</p>
                  <p className="text-xs text-slate-400">
                    {s.symbols[0]} · {s.timeframe} ·{' '}
                    <span className={s.status === 'active' ? 'text-emerald-400' : 'text-slate-500'}>
                      {s.status === 'active' ? 'Ativa' : 'Inativa'}
                    </span>
                  </p>
                </div>
              </label>
            ))}
          </div>
        )}
        <div className="mt-4 flex gap-2">
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-60"
          >
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            Salvar
          </button>
          <button
            onClick={onClose}
            className="rounded-md border border-slate-700 px-4 py-2 text-sm text-slate-400 hover:text-white"
          >
            Cancelar
          </button>
        </div>
      </motion.div>
    </div>
  );
}

// ─── Portfolio Card ───────────────────────────────────────────────────────────
function PortfolioCard({
  portfolio,
  onDelete,
  onUpdated,
}: {
  portfolio: Portfolio;
  onDelete: () => void;
  onUpdated: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [strategies, setStrategies] = useState<PortfolioStrategy[]>([]);
  const [loadingStrategies, setLoadingStrategies] = useState(false);
  const [marketStatus, setMarketStatus] = useState<MarketStatus | null>(null);
  const [showStrategySelector, setShowStrategySelector] = useState(false);

  // Determine the exchange to check market hours for
  const exchangeForMarket = portfolio.mode === 'live' ? 'b3' : 'b3';

  const loadStrategies = useCallback(async () => {
    setLoadingStrategies(true);
    try {
      const [strats, status] = await Promise.all([
        portfolioService.listStrategies(portfolio.id),
        portfolioService.getMarketStatus(portfolio.id, exchangeForMarket),
      ]);
      setStrategies(strats);
      setMarketStatus(status);
    } catch {
      // ignore
    } finally {
      setLoadingStrategies(false);
    }
  }, [portfolio.id, exchangeForMarket]);

  useEffect(() => {
    if (expanded) loadStrategies();
  }, [expanded, loadStrategies]);

  const isLive = portfolio.mode === 'live';

  return (
    <>
      <motion.div
        layout
        className={`rounded-lg border overflow-hidden transition-colors ${
          isLive
            ? 'border-amber-600/40 bg-amber-950/10'
            : 'border-slate-700 bg-slate-900'
        }`}
      >
        {/* Card Header */}
        <div className="flex items-center justify-between px-4 py-3 gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <div
              className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${
                isLive ? 'bg-amber-500/20 text-amber-400' : 'bg-blue-600/20 text-blue-400'
              }`}
            >
              {isLive ? <Banknote className="h-4 w-4" /> : <FlaskConical className="h-4 w-4" />}
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <p className="text-sm font-medium text-white truncate">{portfolio.name}</p>
                <span
                  className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-bold ${
                    isLive
                      ? 'bg-amber-500/20 text-amber-400'
                      : 'bg-blue-500/20 text-blue-400'
                  }`}
                >
                  {isLive ? 'REAL' : 'FAKE'}
                </span>
              </div>
              {portfolio.description && (
                <p className="text-xs text-slate-400 truncate">{portfolio.description}</p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <span className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${riskBadge[portfolio.risk_profile]}`}>
              {portfolio.risk_profile}
            </span>
            <span className="text-sm font-mono text-slate-300">
              R$ {portfolio.capital_allocation.toLocaleString('pt-BR')}
            </span>
            <span className="text-xs text-slate-500">
              {portfolio.strategy_count} estratégia{portfolio.strategy_count !== 1 ? 's' : ''}
            </span>
            <button
              onClick={() => setExpanded((v) => !v)}
              aria-label="Expandir"
              className="rounded p-1 text-slate-400 hover:text-white transition-colors"
            >
              {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>
            <button
              onClick={onDelete}
              aria-label={`Excluir ${portfolio.name}`}
              className="rounded p-1 text-slate-400 hover:bg-red-900/40 hover:text-red-400 transition-colors"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Expanded Content */}
        <AnimatePresence>
          {expanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden border-t border-slate-700/60"
            >
              <div className="px-4 py-3 space-y-3">
                {/* Market status + PnL row */}
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center gap-2">
                    <Clock className="h-3.5 w-3.5 text-slate-500" />
                    <MarketStatusBadge status={marketStatus} />
                    <button
                      onClick={loadStrategies}
                      className="rounded p-0.5 text-slate-500 hover:text-slate-300"
                      aria-label="Atualizar status"
                    >
                      <RefreshCw className="h-3 w-3" />
                    </button>
                  </div>
                  {portfolio.total_pnl !== null && (
                    <span
                      className={`text-sm font-mono font-semibold ${
                        portfolio.total_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'
                      }`}
                    >
                      {portfolio.total_pnl >= 0 ? '+' : ''}
                      R$ {portfolio.total_pnl.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                    </span>
                  )}
                </div>

                {/* Warning for live mode */}
                {isLive && (
                  <div className="rounded-md border border-amber-600/30 bg-amber-900/20 px-3 py-2 text-xs text-amber-400">
                    Carteira em modo REAL — operações executadas com dinheiro real na corretora.
                  </div>
                )}

                {/* Strategies list */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs font-medium text-slate-400 uppercase tracking-wide">Estratégias</p>
                    <button
                      onClick={() => setShowStrategySelector(true)}
                      className="flex items-center gap-1 rounded px-2 py-0.5 text-xs text-blue-400 hover:text-blue-300 border border-blue-500/30 hover:border-blue-400/50 transition-colors"
                    >
                      <LinkIcon className="h-3 w-3" />
                      Gerenciar
                    </button>
                  </div>

                  {loadingStrategies ? (
                    <div className="flex justify-center py-3">
                      <Loader2 className="h-4 w-4 animate-spin text-slate-500" />
                    </div>
                  ) : strategies.length === 0 ? (
                    <p className="text-xs text-slate-500 py-2">
                      Nenhuma estratégia associada. Clique em "Gerenciar" para adicionar.
                    </p>
                  ) : (
                    <div className="space-y-1.5">
                      {strategies.map((s) => (
                        <div
                          key={s.id}
                          className="flex items-center justify-between rounded bg-slate-800/50 px-3 py-2 text-sm"
                        >
                          <div>
                            <span className="text-white font-medium">{s.name}</span>
                            <span className="ml-2 text-xs text-slate-400">
                              {s.symbol} · {s.timeframe}
                            </span>
                          </div>
                          <div className="flex items-center gap-3">
                            {s.win_rate !== null && (
                              <span className="text-xs text-slate-400">
                                {(s.win_rate * 100).toFixed(0)}% win
                              </span>
                            )}
                            <span
                              className={`text-xs ${s.is_active ? 'text-emerald-400' : 'text-slate-500'}`}
                            >
                              {s.is_active ? 'Ativa' : 'Inativa'}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Meta */}
                <p className="text-xs text-slate-600">
                  Criada em{' '}
                  {new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short' }).format(
                    new Date(portfolio.created_at),
                  )}
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Strategy Selector Modal */}
      <AnimatePresence>
        {showStrategySelector && (
          <StrategySelector
            portfolioId={portfolio.id}
            currentStrategyIds={strategies.map((s) => s.id)}
            onClose={() => setShowStrategySelector(false)}
            onSaved={() => {
              setShowStrategySelector(false);
              loadStrategies();
              onUpdated();
            }}
          />
        )}
      </AnimatePresence>
    </>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function PortfoliosPage() {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const notify = useNotification();

  const loadPortfolios = useCallback(async () => {
    try {
      const data = await portfolioService.list();
      setPortfolios(data);
    } catch {
      notify.error('Erro', 'Não foi possível carregar as carteiras.');
    } finally {
      setLoading(false);
    }
  }, [notify]);

  useEffect(() => { loadPortfolios(); }, [loadPortfolios]);

  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors },
  } = useForm<PortfolioFormValues>({
    resolver: zodResolver(portfolioSchema),
    defaultValues: {
      name: '',
      description: '',
      capital_allocation: 0,
      risk_profile: 'moderado',
      mode: 'paper',
    },
  });

  const selectedMode = watch('mode');

  async function onSubmit(values: PortfolioFormValues) {
    setSaving(true);
    try {
      const p = await portfolioService.create(values);
      setPortfolios((prev) => [p, ...prev]);
      setShowForm(false);
      reset();
      notify.success('Carteira criada', `"${values.name}" adicionada com sucesso.`);
    } catch {
      notify.error('Erro', 'Não foi possível criar a carteira.');
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: string) {
    try {
      await portfolioService.delete(id);
      setPortfolios((prev) => prev.filter((p) => p.id !== id));
      notify.info('Carteira removida', 'A carteira foi excluída.');
    } catch {
      notify.error('Erro', 'Não foi possível remover a carteira.');
    }
  }

  const paperCount = portfolios.filter((p) => p.mode === 'paper').length;
  const liveCount = portfolios.filter((p) => p.mode === 'live').length;

  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      transition={{ duration: 0.25, ease: 'easeOut' }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Carteiras</h1>
          <p className="mt-1 text-sm text-slate-400">
            Organize estratégias em carteiras independentes — simuladas ou com dinheiro real
          </p>
          {portfolios.length > 0 && (
            <div className="mt-2 flex items-center gap-3 text-xs">
              <span className="flex items-center gap-1 text-blue-400">
                <FlaskConical className="h-3 w-3" />
                {paperCount} fake
              </span>
              <span className="flex items-center gap-1 text-amber-400">
                <Banknote className="h-3 w-3" />
                {liveCount} real
              </span>
            </div>
          )}
        </div>
        {!showForm && (
          <button
            onClick={() => setShowForm(true)}
            className="flex shrink-0 items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-blue-500"
          >
            <Plus className="h-4 w-4" />
            Nova Carteira
          </button>
        )}
      </div>

      {/* Mode explanation */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div className="rounded-lg border border-blue-500/20 bg-blue-900/10 px-4 py-3">
          <div className="flex items-center gap-2 mb-1">
            <FlaskConical className="h-4 w-4 text-blue-400" />
            <p className="text-sm font-semibold text-blue-300">Modo Fake (Paper)</p>
          </div>
          <p className="text-xs text-slate-400">
            Simula operações sem dinheiro real. Ideal para testar estratégias em condições de mercado reais, sem riscos.
          </p>
        </div>
        <div className="rounded-lg border border-amber-600/20 bg-amber-900/10 px-4 py-3">
          <div className="flex items-center gap-2 mb-1">
            <Banknote className="h-4 w-4 text-amber-400" />
            <p className="text-sm font-semibold text-amber-300">Modo Real (Live)</p>
          </div>
          <p className="text-xs text-slate-400">
            Executa ordens reais na corretora conectada. Requer chave de API com permissão de trading. Validações de horário de pregão aplicadas.
          </p>
        </div>
      </div>

      {/* Create form */}
      <AnimatePresence>
        {showForm && (
          <motion.form
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            onSubmit={handleSubmit(onSubmit)}
            className={`rounded-lg border p-5 space-y-4 ${
              selectedMode === 'live'
                ? 'border-amber-600/40 bg-amber-950/10'
                : 'border-slate-700 bg-slate-900'
            }`}
          >
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold text-white">Nova Carteira</h2>
              {selectedMode === 'live' && (
                <span className="rounded-full bg-amber-500/20 px-2 py-0.5 text-xs font-bold text-amber-400">
                  MODO REAL
                </span>
              )}
            </div>

            {/* Mode selector */}
            <div>
              <p className="text-sm font-medium text-slate-300 mb-2">Modo</p>
              <div className="grid grid-cols-2 gap-2">
                {(['paper', 'live'] as const).map((m) => (
                  <label
                    key={m}
                    className={`flex cursor-pointer items-center gap-2 rounded-lg border p-3 transition-colors ${
                      selectedMode === m
                        ? m === 'live'
                          ? 'border-amber-500 bg-amber-900/20'
                          : 'border-blue-500 bg-blue-900/20'
                        : 'border-slate-700 hover:border-slate-500'
                    }`}
                  >
                    <input type="radio" value={m} {...register('mode')} className="sr-only" />
                    {m === 'paper' ? (
                      <FlaskConical className="h-4 w-4 text-blue-400 shrink-0" />
                    ) : (
                      <Banknote className="h-4 w-4 text-amber-400 shrink-0" />
                    )}
                    <div>
                      <p className={`text-sm font-semibold ${m === 'live' ? 'text-amber-300' : 'text-blue-300'}`}>
                        {m === 'paper' ? 'Fake (Paper)' : 'Real (Live)'}
                      </p>
                      <p className="text-xs text-slate-500">
                        {m === 'paper' ? 'Sem risco, simulado' : 'Dinheiro real, corretora'}
                      </p>
                    </div>
                  </label>
                ))}
              </div>
              {errors.mode && <p className="mt-1 text-xs text-red-400">{errors.mode.message}</p>}
            </div>

            {selectedMode === 'live' && (
              <div className="rounded-md border border-amber-600/30 bg-amber-900/20 px-3 py-2 text-xs text-amber-400">
                Atenção: carteiras em modo Real executam ordens com dinheiro real. Certifique-se de ter uma chave de API ativa em Configurações → Chaves de Exchange.
              </div>
            )}

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <InputField id="name" label="Nome" error={errors.name?.message}>
                <input
                  id="name"
                  type="text"
                  placeholder={selectedMode === 'live' ? 'Ex: Carteira B3 Real' : 'Ex: Carteira Teste'}
                  {...register('name')}
                  className={inputCls}
                />
              </InputField>

              <InputField id="capital_allocation" label="Capital Alocado (R$)" error={errors.capital_allocation?.message}>
                <input
                  id="capital_allocation"
                  type="number"
                  step={100}
                  min={0}
                  placeholder="0"
                  {...register('capital_allocation')}
                  className={inputCls}
                />
              </InputField>
            </div>

            <InputField id="description" label="Descrição (opcional)" error={errors.description?.message}>
              <input
                id="description"
                type="text"
                placeholder="Ex: FIIs e ações conservadoras na B3"
                {...register('description')}
                className={inputCls}
              />
            </InputField>

            <InputField id="risk_profile" label="Perfil de Risco" error={errors.risk_profile?.message}>
              <select id="risk_profile" {...register('risk_profile')} className={inputCls}>
                <option value="conservador">Conservador</option>
                <option value="moderado">Moderado</option>
                <option value="agressivo">Agressivo</option>
              </select>
            </InputField>

            <div className="flex gap-2 pt-1">
              <button
                type="submit"
                disabled={saving}
                className="flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-blue-500 disabled:opacity-60"
              >
                {saving && <Loader2 className="h-4 w-4 animate-spin" />}
                Criar Carteira
              </button>
              <button
                type="button"
                onClick={() => { setShowForm(false); reset(); }}
                className="rounded-md border border-slate-700 px-4 py-2 text-sm text-slate-400 transition-colors hover:text-white"
              >
                Cancelar
              </button>
            </div>
          </motion.form>
        )}
      </AnimatePresence>

      {/* Portfolio list */}
      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
        </div>
      ) : portfolios.length === 0 && !showForm ? (
        <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-700 py-16 text-center">
          <Wallet className="h-10 w-10 text-slate-600 mb-3" />
          <p className="text-sm font-medium text-slate-400">Nenhuma carteira criada</p>
          <p className="mt-1 text-xs text-slate-500">
            Crie carteiras fake para testar e reais para operar com capital real.
          </p>
          <button
            onClick={() => setShowForm(true)}
            className="mt-4 flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-blue-500"
          >
            <Plus className="h-4 w-4" />
            Criar Carteira
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {portfolios.map((p) => (
            <PortfolioCard
              key={p.id}
              portfolio={p}
              onDelete={() => handleDelete(p.id)}
              onUpdated={loadPortfolios}
            />
          ))}
        </div>
      )}
    </motion.div>
  );
}
