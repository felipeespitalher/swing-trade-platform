import { cn } from '@/lib/utils';

interface AuthCardProps {
  children: React.ReactNode;
  className?: string;
}

export function AuthCard({ children, className }: AuthCardProps) {
  return (
    <div
      className={cn(
        'w-full rounded-2xl border border-white/10 bg-surface/80 backdrop-blur-md',
        'shadow-2xl shadow-black/40 p-8',
        className
      )}
    >
      {children}
    </div>
  );
}
