import { Moon, Sun } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { cn } from '../../lib/utils';

interface ThemeToggleProps {
  className?: string;
}

export function ThemeToggle({ className }: ThemeToggleProps) {
  const { resolvedTheme, setTheme } = useTheme();

  const isDark = resolvedTheme === 'dark';

  const handleToggle = () => {
    setTheme(isDark ? 'light' : 'dark');
  };

  return (
    <button
      type="button"
      onClick={handleToggle}
      aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
      className={cn(
        'relative inline-flex h-8 w-8 items-center justify-center rounded-md',
        'text-muted-foreground hover:text-foreground',
        'hover:bg-accent transition-colors duration-200',
        className
      )}
    >
      <Sun
        className={cn(
          'h-4 w-4 transition-all duration-300',
          isDark ? 'scale-0 opacity-0 absolute' : 'scale-100 opacity-100'
        )}
      />
      <Moon
        className={cn(
          'h-4 w-4 transition-all duration-300',
          isDark ? 'scale-100 opacity-100' : 'scale-0 opacity-0 absolute'
        )}
      />
    </button>
  );
}
