import { Loader2 } from 'lucide-react';

export function BacktestStatus() {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-10">
      <Loader2 className="h-10 w-10 animate-spin text-blue-500" />
      <p className="text-sm font-medium text-slate-300">Executando backtest...</p>
      <div className="w-full max-w-xs overflow-hidden rounded-full bg-slate-700">
        <div className="h-1.5 animate-pulse rounded-full bg-blue-500" style={{ width: '70%' }} />
      </div>
      <p className="text-xs text-slate-500">
        Processando dados históricos, aguarde...
      </p>
    </div>
  );
}
