import { useState } from 'react';
import { motion } from 'framer-motion';
import { Plus } from 'lucide-react';
import { StrategyCard } from '@/components/strategy/StrategyCard';
import { StrategyForm } from '@/components/strategy/StrategyForm';
import { StrategyDetails } from '@/components/strategy/StrategyDetails';
import {
  useStrategies,
  useCreateStrategy,
  useUpdateStrategy,
  useDeleteStrategy,
  useToggleStrategy,
} from '@/hooks/useStrategy';
import type { Strategy } from '@/services/strategyService';

type PanelMode = 'view' | 'create' | 'edit';

export default function StrategyPage() {
  const { data: strategies, isLoading } = useStrategies();
  const createMutation = useCreateStrategy();
  const updateMutation = useUpdateStrategy();
  const deleteMutation = useDeleteStrategy();
  const toggleMutation = useToggleStrategy();

  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(null);
  const [panelMode, setPanelMode] = useState<PanelMode>('view');

  function handleSelectStrategy(strategy: Strategy) {
    setSelectedStrategy(strategy);
    setPanelMode('view');
  }

  function handleNewStrategy() {
    setSelectedStrategy(null);
    setPanelMode('create');
  }

  function handleEditStrategy(strategy: Strategy) {
    setSelectedStrategy(strategy);
    setPanelMode('edit');
  }

  function handleDeleteStrategy(id: string) {
    deleteMutation.mutate(id, {
      onSuccess: () => {
        if (selectedStrategy?.id === id) {
          setSelectedStrategy(null);
          setPanelMode('view');
        }
      },
    });
  }

  function handleToggleStrategy(id: string, newStatus: 'active' | 'inactive') {
    toggleMutation.mutate({ id, status: newStatus });
  }

  function handleFormSubmit(
    data: Omit<Strategy, 'id' | 'created_at' | 'win_rate' | 'total_trades' | 'last_run'>,
  ) {
    if (panelMode === 'create') {
      createMutation.mutate(data, {
        onSuccess: (created) => {
          setSelectedStrategy(created);
          setPanelMode('view');
        },
      });
    } else if (panelMode === 'edit' && selectedStrategy) {
      updateMutation.mutate(
        { id: selectedStrategy.id, data },
        {
          onSuccess: (updated) => {
            setSelectedStrategy(updated);
            setPanelMode('view');
          },
        },
      );
    }
  }

  function handleFormCancel() {
    setPanelMode(selectedStrategy ? 'view' : 'view');
  }

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  function handleRunBacktest(_id: string) {
    // TODO: implement backtest runner
  }

  const isFormSubmitting = createMutation.isPending || updateMutation.isPending;

  const pageVariants = {
    initial: { opacity: 0, y: 10 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0 },
  };

  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      transition={{ duration: 0.25, ease: 'easeOut' }}
      className="space-y-4"
    >
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Estratégias</h1>
        <p className="mt-1 text-sm text-slate-400">Gerencie suas estratégias de trading automatizado</p>
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Left: strategy list */}
        <div className="lg:col-span-1">
          <div className="rounded-lg border border-slate-700 bg-slate-900">
            {/* List header */}
            <div className="flex items-center justify-between border-b border-slate-700 px-4 py-3">
              <h2 className="text-sm font-semibold text-white">Minhas Estratégias</h2>
              <button
                onClick={handleNewStrategy}
                className="flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-blue-500"
              >
                <Plus className="h-3.5 w-3.5" />
                Nova
              </button>
            </div>

            {/* Scrollable card list */}
            <div className="max-h-[calc(100vh-220px)] overflow-y-auto p-3 space-y-2">
              {isLoading ? (
                <div className="space-y-2">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <div
                      key={i}
                      className="h-32 animate-pulse rounded-lg bg-slate-800"
                    />
                  ))}
                </div>
              ) : !strategies || strategies.length === 0 ? (
                <p className="py-8 text-center text-sm text-slate-500">
                  Nenhuma estratégia cadastrada
                </p>
              ) : (
                strategies.map((strategy) => (
                  <StrategyCard
                    key={strategy.id}
                    strategy={strategy}
                    selected={selectedStrategy?.id === strategy.id}
                    onSelect={handleSelectStrategy}
                    onEdit={handleEditStrategy}
                    onDelete={handleDeleteStrategy}
                    onToggle={handleToggleStrategy}
                  />
                ))
              )}
            </div>
          </div>
        </div>

        {/* Right: details or form */}
        <div className="lg:col-span-2">
          <div className="rounded-lg border border-slate-700 bg-slate-900 p-5">
            {panelMode === 'create' || panelMode === 'edit' ? (
              <StrategyForm
                initial={panelMode === 'edit' ? selectedStrategy ?? undefined : undefined}
                onSubmit={handleFormSubmit}
                onCancel={handleFormCancel}
                isSubmitting={isFormSubmitting}
              />
            ) : selectedStrategy ? (
              <StrategyDetails
                strategy={selectedStrategy}
                onEdit={handleEditStrategy}
                onRunBacktest={handleRunBacktest}
              />
            ) : (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <p className="text-sm text-slate-500">
                  Selecione uma estratégia para ver os detalhes
                </p>
                <button
                  onClick={handleNewStrategy}
                  className="mt-4 flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-500"
                >
                  <Plus className="h-4 w-4" />
                  Criar primeira estratégia
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
