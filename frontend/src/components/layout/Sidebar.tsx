import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Zap,
  TrendingUp,
  BarChart,
  Settings,
} from 'lucide-react';
import { useUIStore } from '../../stores/uiStore';
import { ROUTES } from '../../config/routes';
import { cn } from '../../lib/utils';

interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', href: ROUTES.DASHBOARD, icon: LayoutDashboard },
  { label: 'Strategies', href: ROUTES.STRATEGIES, icon: Zap },
  { label: 'Trades', href: '/trades', icon: TrendingUp },
  { label: 'Backtester', href: ROUTES.BACKTESTER, icon: BarChart },
  { label: 'Settings', href: ROUTES.SETTINGS, icon: Settings },
];

export function Sidebar() {
  const { isSidebarOpen, setSidebarOpen } = useUIStore();

  return (
    <>
      {/* Mobile overlay */}
      {isSidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/50 md:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar panel */}
      <aside
        className={cn(
          'fixed top-16 left-0 z-40 h-[calc(100vh-4rem)] w-60',
          'bg-card border-r border-border',
          'flex flex-col',
          'transition-transform duration-300 ease-in-out',
          isSidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.href}
                to={item.href}
                onClick={() => {
                  // Close sidebar on mobile after navigation
                  if (window.innerWidth < 768) setSidebarOpen(false);
                }}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium',
                    'transition-colors duration-150',
                    isActive
                      ? [
                          'bg-primary/10 text-primary',
                          'border-l-2 border-primary ml-[-1px] pl-[11px]',
                        ]
                      : 'text-muted-foreground hover:text-foreground hover:bg-accent'
                  )
                }
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>

        {/* Sidebar footer */}
        <div className="px-3 py-4 border-t border-border">
          <p className="text-xs text-muted-foreground text-center">
            STAP v0.1.0
          </p>
        </div>
      </aside>
    </>
  );
}
