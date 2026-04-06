import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { strategyService, type Strategy } from '@/services/strategyService';

export function useStrategies() {
  return useQuery({
    queryKey: ['strategies'],
    queryFn: () => strategyService.list(),
    staleTime: 5 * 60 * 1000,
  });
}

export function useCreateStrategy() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (
      data: Omit<Strategy, 'id' | 'created_at' | 'win_rate' | 'total_trades' | 'last_run'>,
    ) => strategyService.create(data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['strategies'] }),
  });
}

export function useUpdateStrategy() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Strategy> }) =>
      strategyService.update(id, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['strategies'] }),
  });
}

export function useDeleteStrategy() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => strategyService.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['strategies'] }),
  });
}

export function useToggleStrategy() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: 'active' | 'inactive' }) =>
      strategyService.toggle(id, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['strategies'] }),
  });
}
