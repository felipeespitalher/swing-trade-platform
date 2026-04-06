import { BarChart2, Search, User, Menu } from 'lucide-react';
import { ThemeToggle } from '../common/ThemeToggle';
import { useUIStore } from '../../stores/uiStore';
import { cn } from '../../lib/utils';

interface HeaderProps {
  className?: string;
}

export function Header({ className }: HeaderProps) {
  const toggleSidebar = useUIStore((state) => state.toggleSidebar);

  return (
    <header
      className={cn(
        'fixed top-0 left-0 right-0 z-50 h-16',
        'flex items-center justify-between px-4 md:px-6',
        'bg-card border-b border-border',
        className
      )}
    >
      {/* Left: hamburger + logo */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={toggleSidebar}
          aria-label="Toggle sidebar"
          className="inline-flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
        >
          <Menu className="h-5 w-5" />
        </button>

        <div className="flex items-center gap-2">
          <BarChart2 className="h-6 w-6 text-primary" />
          <span className="text-lg font-bold text-foreground tracking-tight">
            STAP
          </span>
        </div>
      </div>

      {/* Center: search (hidden on mobile) */}
      <div className="hidden md:flex flex-1 max-w-md mx-8">
        <div className="relative w-full">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search strategies, symbols..."
            className={cn(
              'w-full h-9 pl-9 pr-4 rounded-md text-sm',
              'bg-background border border-border',
              'text-foreground placeholder:text-muted-foreground',
              'focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent',
              'transition-colors'
            )}
          />
        </div>
      </div>

      {/* Right: theme toggle + user avatar */}
      <div className="flex items-center gap-2">
        <ThemeToggle />

        <button
          type="button"
          aria-label="User menu"
          className={cn(
            'inline-flex h-8 w-8 items-center justify-center rounded-full',
            'bg-primary/10 text-primary hover:bg-primary/20',
            'transition-colors duration-200'
          )}
        >
          <User className="h-4 w-4" />
        </button>
      </div>
    </header>
  );
}
