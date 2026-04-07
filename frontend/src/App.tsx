import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { Suspense, lazy } from 'react';
import { AnimatePresence } from 'framer-motion';
import { ThemeProvider } from './context/ThemeContext';
import { AuthProvider } from './context/AuthContext';
import { queryClient } from './config/queryClient';
import { MainLayout } from './components/layout/MainLayout';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { LoadingSkeleton } from './components/common/LoadingSkeleton';
import { ToastContainer } from './components/common/ToastContainer';
import { useAuthStore } from './stores/authStore';

// Lazy-loaded pages
const LoginPage = lazy(() => import('./pages/LoginPage'));
const RegisterPage = lazy(() => import('./pages/RegisterPage'));
const ForgotPasswordPage = lazy(() => import('./pages/ForgotPasswordPage'));
const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const StrategyPage = lazy(() => import('./pages/StrategyPage'));
const BacktesterPage = lazy(() => import('./pages/BacktesterPage'));
const SettingsPage = lazy(() => import('./pages/SettingsPage'));
const ResetPasswordPage = lazy(() => import('./pages/ResetPasswordPage'));
const VerifyEmailPage = lazy(() => import('./pages/VerifyEmailPage'));

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  return isAuthenticated ? <>{children}</> : <Navigate to="/auth/login" replace />;
}

function AnimatedRoutes() {
  const location = useLocation();

  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        {/* Public routes */}
        <Route path="/auth/login" element={<LoginPage />} />
        <Route path="/auth/register" element={<RegisterPage />} />
        <Route path="/auth/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/auth/reset-password" element={<ResetPasswordPage />} />
        <Route path="/auth/verify" element={<VerifyEmailPage />} />

        {/* Protected routes */}
        <Route
          element={
            <PrivateRoute>
              <MainLayout />
            </PrivateRoute>
          }
        >
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/strategies" element={<StrategyPage />} />
          <Route path="/backtester" element={<BacktesterPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </AnimatePresence>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <AuthProvider>
            <BrowserRouter>
              <Suspense fallback={<LoadingSkeleton />}>
                <AnimatedRoutes />
              </Suspense>
              <ToastContainer />
            </BrowserRouter>
          </AuthProvider>
        </ThemeProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
