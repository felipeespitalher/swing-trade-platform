import { useCallback } from 'react';
import { useNotificationStore } from '@/stores/notificationStore';

export function useNotification() {
  const { addToast } = useNotificationStore();

  const success = useCallback(
    (title: string, message?: string) => {
      addToast({ type: 'success', title, message, duration: 4000 });
    },
    [addToast],
  );

  const error = useCallback(
    (title: string, message?: string) => {
      addToast({ type: 'error', title, message, duration: 6000 });
    },
    [addToast],
  );

  const warning = useCallback(
    (title: string, message?: string) => {
      addToast({ type: 'warning', title, message, duration: 5000 });
    },
    [addToast],
  );

  const info = useCallback(
    (title: string, message?: string) => {
      addToast({ type: 'info', title, message, duration: 4000 });
    },
    [addToast],
  );

  return { success, error, warning, info };
}
