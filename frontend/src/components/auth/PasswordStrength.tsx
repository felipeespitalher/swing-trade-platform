import { cn } from '@/lib/utils';

interface PasswordStrengthProps {
  password: string;
}

function getStrength(password: string): { score: number; label: string } {
  if (!password) return { score: 0, label: '' };

  let score = 0;
  if (password.length >= 8) score++;
  if (/[A-Z]/.test(password)) score++;
  if (/[0-9]/.test(password)) score++;
  if (/[^A-Za-z0-9]/.test(password)) score++;

  const labels = ['', 'Fraca', 'Média', 'Forte', 'Muito forte'];
  return { score, label: labels[score] ?? 'Muito forte' };
}

export function PasswordStrength({ password }: PasswordStrengthProps) {
  const { score, label } = getStrength(password);

  if (!password) return null;

  const colorMap: Record<number, string> = {
    1: 'bg-red-500',
    2: 'bg-yellow-500',
    3: 'bg-emerald-500',
    4: 'bg-emerald-400',
  };

  const textColorMap: Record<number, string> = {
    1: 'text-red-400',
    2: 'text-yellow-400',
    3: 'text-emerald-400',
    4: 'text-emerald-300',
  };

  const barColor = colorMap[score] ?? 'bg-emerald-400';
  const textColor = textColorMap[score] ?? 'text-emerald-300';

  return (
    <div className="mt-2 space-y-1.5">
      <div className="flex gap-1" aria-hidden="true">
        {[1, 2, 3, 4].map((step) => (
          <div
            key={step}
            className={cn(
              'h-1 flex-1 rounded-full transition-all duration-300',
              step <= score ? barColor : 'bg-white/10'
            )}
          />
        ))}
      </div>
      <p className={cn('text-xs font-medium', textColor)} aria-live="polite">
        Força da senha: {label}
      </p>
    </div>
  );
}
