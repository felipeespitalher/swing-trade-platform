import { useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-react';
import { useNotificationStore, type Toast, type ToastType } from '@/stores/notificationStore';

const ICONS: Record<ToastType, React.ComponentType<{ className?: string }>> = {
  success: CheckCircle,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
};

const BORDER_COLORS: Record<ToastType, string> = {
  success: 'border-l-emerald-500',
  error: 'border-l-red-500',
  warning: 'border-l-amber-500',
  info: 'border-l-blue-500',
};

const ICON_COLORS: Record<ToastType, string> = {
  success: 'text-emerald-400',
  error: 'text-red-400',
  warning: 'text-amber-400',
  info: 'text-blue-400',
};

function ToastItem({ toast }: { toast: Toast }) {
  const removeToast = useNotificationStore((s) => s.removeToast);
  const Icon = ICONS[toast.type];

  useEffect(() => {
    const duration = toast.duration ?? 4000;
    const timer = setTimeout(() => removeToast(toast.id), duration);
    return () => clearTimeout(timer);
  }, [toast.id, toast.duration, removeToast]);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 60 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 60 }}
      transition={{ duration: 0.22, ease: 'easeOut' }}
      className={`flex w-80 items-start gap-3 rounded-lg border border-l-4 border-slate-700 bg-slate-900 p-4 shadow-xl ${BORDER_COLORS[toast.type]}`}
    >
      <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${ICON_COLORS[toast.type]}`} />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-semibold text-white">{toast.title}</p>
        {toast.message && (
          <p className="mt-0.5 text-xs text-slate-400">{toast.message}</p>
        )}
      </div>
      <button
        onClick={() => removeToast(toast.id)}
        aria-label="Fechar notificação"
        className="shrink-0 rounded p-0.5 text-slate-500 transition-colors hover:text-white"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </motion.div>
  );
}

export function ToastContainer() {
  const toasts = useNotificationStore((s) => s.toasts);

  return (
    <div
      aria-live="polite"
      aria-atomic="false"
      className="fixed bottom-4 right-4 z-50 flex flex-col gap-2"
    >
      <AnimatePresence mode="popLayout">
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} />
        ))}
      </AnimatePresence>
    </div>
  );
}
