import { useQuery } from '@tanstack/react-query';
import { dashboardService } from '@/services/dashboardService';

export function useDashboardMetrics() {
  return useQuery({
    queryKey: ['dashboard', 'metrics'],
    queryFn: () => dashboardService.getMetrics(),
    staleTime: 5 * 60 * 1000,
    refetchInterval: 30 * 1000,
  });
}

export function useEquityCurve() {
  return useQuery({
    queryKey: ['dashboard', 'equity'],
    queryFn: () => dashboardService.getEquityCurve(),
    staleTime: 5 * 60 * 1000,
    refetchInterval: 30 * 1000,
  });
}

export function useMonthlyReturns() {
  return useQuery({
    queryKey: ['dashboard', 'monthly'],
    queryFn: () => dashboardService.getMonthlyReturns(),
    staleTime: 5 * 60 * 1000,
    refetchInterval: 30 * 1000,
  });
}

export function useRecentTrades() {
  return useQuery({
    queryKey: ['dashboard', 'trades'],
    queryFn: () => dashboardService.getRecentTrades(),
    staleTime: 5 * 60 * 1000,
    refetchInterval: 30 * 1000,
  });
}
