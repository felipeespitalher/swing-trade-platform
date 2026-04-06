import { useState, useCallback } from 'react';
import {
  backtestService,
  type BacktestRequest,
  type BacktestResult,
} from '@/services/backtestService';

export function useBacktest() {
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runBacktest = useCallback(async (request: BacktestRequest) => {
    setIsRunning(true);
    setError(null);
    setResult(null);
    try {
      const res = await backtestService.runBacktest(request);
      setResult(res);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : 'Erro ao executar backtest';
      setError(message);
    } finally {
      setIsRunning(false);
    }
  }, []);

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return { result, isRunning, error, runBacktest, reset };
}
