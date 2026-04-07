export const ROUTES = {
  HOME: '/',
  DASHBOARD: '/dashboard',
  LOGIN: '/auth/login',
  REGISTER: '/auth/register',
  FORGOT_PASSWORD: '/auth/forgot-password',
  RESET_PASSWORD: '/auth/reset-password',
  VERIFY_EMAIL: '/auth/verify',
  STRATEGIES: '/strategies',
  BACKTESTER: '/backtester',
  SETTINGS: '/settings',
  NOT_FOUND: '*',
} as const;
