import { cn } from '@/lib/utils';

interface ChartCardProps {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  loading?: boolean;
  className?: string;
}

export function ChartCard({ title, subtitle, children, loading, className }: ChartCardProps) {
  return (
    <div
      className={cn(
        'rounded-lg border border-slate-700 bg-slate-900 p-5',
        className,
      )}
    >
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-white">{title}</h3>
        {subtitle && <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>}
      </div>
      <div className="min-h-[250px] w-full">
        {loading ? (
          <div className="flex h-[250px] w-full flex-col gap-3">
            <div className="h-full w-full animate-pulse rounded bg-slate-800" />
          </div>
        ) : (
          children
        )}
      </div>
    </div>
  );
}
