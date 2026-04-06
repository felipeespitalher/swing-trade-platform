import { TrendingUp, TrendingDown } from 'lucide-react';
import { cn } from '@/lib/utils';

interface StatCardProps {
  title: string;
  value: string;
  change?: string;
  trend?: 'up' | 'down' | 'neutral';
  icon?: React.ReactNode;
  loading?: boolean;
  className?: string;
}

export function StatCard({ title, value, change, trend, icon, loading, className }: StatCardProps) {
  if (loading) {
    return (
      <div
        className={cn(
          'rounded-lg border border-slate-700 bg-slate-900 p-5',
          className,
        )}
      >
        <div className="flex items-start justify-between">
          <div className="flex-1 space-y-3">
            <div className="h-3 w-24 animate-pulse rounded bg-slate-700" />
            <div className="h-7 w-32 animate-pulse rounded bg-slate-700" />
            <div className="h-3 w-16 animate-pulse rounded bg-slate-700" />
          </div>
          <div className="ml-4 h-10 w-10 animate-pulse rounded-full bg-slate-700" />
        </div>
      </div>
    );
  }

  const trendColor = {
    up: 'text-emerald-400',
    down: 'text-red-400',
    neutral: 'text-slate-400',
  }[trend ?? 'neutral'];

  const TrendIcon =
    trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : null;

  return (
    <div
      className={cn(
        'rounded-lg border border-slate-700 bg-slate-900 p-5 transition-colors hover:border-slate-600',
        className,
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            {title}
          </p>
          <p className="mt-2 font-mono text-2xl font-bold text-white leading-none">
            {value}
          </p>
          {change && (
            <div className={cn('mt-2 flex items-center gap-1 text-sm font-medium', trendColor)}>
              {TrendIcon && <TrendIcon className="h-3.5 w-3.5 flex-shrink-0" />}
              <span>{change}</span>
            </div>
          )}
        </div>
        {icon && (
          <div className="ml-4 flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-blue-500/10 text-blue-400">
            {icon}
          </div>
        )}
      </div>
    </div>
  );
}
