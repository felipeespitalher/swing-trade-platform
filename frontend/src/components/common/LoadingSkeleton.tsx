import { cn } from '../../lib/utils';

interface SkeletonProps {
  className?: string;
}

function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        'animate-pulse rounded-md bg-muted',
        className
      )}
    />
  );
}

function CardSkeleton() {
  return (
    <div className="card-surface space-y-3">
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-4 w-1/2" />
      <Skeleton className="h-20 w-full" />
    </div>
  );
}

function FullPageSkeleton() {
  return (
    <div className="flex min-h-screen bg-background">
      {/* Sidebar skeleton */}
      <div className="w-60 border-r border-border bg-card p-4 space-y-2 hidden md:flex md:flex-col">
        <Skeleton className="h-8 w-32 mb-6" />
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>

      {/* Main content skeleton */}
      <div className="flex-1 flex flex-col">
        {/* Header skeleton */}
        <div className="h-16 border-b border-border bg-card px-6 flex items-center justify-between">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-8 w-8 rounded-full" />
        </div>

        {/* Content skeleton */}
        <div className="flex-1 p-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
      </div>
    </div>
  );
}

interface LoadingSkeletonProps {
  variant?: 'fullpage' | 'card';
  className?: string;
}

export function LoadingSkeleton({
  variant = 'fullpage',
  className,
}: LoadingSkeletonProps) {
  if (variant === 'card') {
    return <CardSkeleton />;
  }

  return (
    <div className={cn(className)}>
      <FullPageSkeleton />
    </div>
  );
}

export { Skeleton };
