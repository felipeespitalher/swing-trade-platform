import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { authService } from '@/services/authService';
import { ROUTES } from '@/config/routes';

export function useAuth() {
  const store = useAuthStore();
  const navigate = useNavigate();

  const login = async (email: string, password: string): Promise<void> => {
    const tokens = await authService.login({ email, password });
    // Set token immediately so the subsequent getMe() call is authenticated
    useAuthStore.getState().setToken(tokens.access_token);
    const user = await authService.getMe();
    store.setAuth(user, tokens.access_token, tokens.refresh_token);
  };

  const logout = (): void => {
    store.logout();
    navigate(ROUTES.LOGIN, { replace: true });
  };

  return {
    user: store.user,
    isAuthenticated: store.isAuthenticated,
    isLoading: store.isLoading,
    error: store.error,
    token: store.token,
    login,
    logout,
  };
}
