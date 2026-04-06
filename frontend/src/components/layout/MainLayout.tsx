import { Outlet } from 'react-router-dom';
import { useEffect } from 'react';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { useUIStore } from '../../stores/uiStore';
import { cn } from '../../lib/utils';

export function MainLayout() {
  const { isSidebarOpen, setSidebarOpen } = useUIStore();

  // Close sidebar on initial load for mobile
  useEffect(() => {
    if (window.innerWidth < 768) {
      setSidebarOpen(false);
    }
  }, [setSidebarOpen]);

  // Listen for resize and auto-open/close sidebar
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 768) {
        setSidebarOpen(true);
      } else {
        setSidebarOpen(false);
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [setSidebarOpen]);

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <Sidebar />

      {/* Main content: offset for header (top-16) and sidebar (left-60 when open) */}
      <main
        className={cn(
          'pt-16 transition-all duration-300 ease-in-out min-h-screen',
          isSidebarOpen ? 'md:pl-60' : 'pl-0'
        )}
      >
        <div className="p-6 animate-fade-in">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
