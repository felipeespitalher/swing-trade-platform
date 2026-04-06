import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link, useNavigate } from 'react-router-dom';
import { Eye, EyeOff, Loader2, BarChart2 } from 'lucide-react';
import { loginSchema, type LoginFormData } from '@/utils/validation';
import { authService } from '@/services/authService';
import { useAuthStore } from '@/stores/authStore';
import { cn } from '@/lib/utils';
import { ROUTES } from '@/config/routes';
import { AuthCard } from './AuthCard';

export function LoginForm() {
  const [showPassword, setShowPassword] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const navigate = useNavigate();
  const setAuth = useAuthStore((state) => state.setAuth);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: { rememberMe: false },
  });

  const onSubmit = async (data: LoginFormData) => {
    setApiError(null);
    try {
      const tokens = await authService.login({ email: data.email, password: data.password });
      // Set token first so getMe() request is authenticated
      useAuthStore.getState().setToken(tokens.access_token);
      const user = await authService.getMe();
      setAuth(user, tokens.access_token, tokens.refresh_token);
      navigate(ROUTES.DASHBOARD, { replace: true });
    } catch (err: unknown) {
      const message =
        err instanceof Error
          ? err.message
          : 'Falha ao autenticar. Verifique suas credenciais.';
      setApiError(message);
    }
  };

  return (
    <AuthCard>
      {/* Logo + heading */}
      <div className="mb-8 flex flex-col items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/20 text-primary">
          <BarChart2 className="h-7 w-7" />
        </div>
        <div className="text-center">
          <h1 className="text-2xl font-bold tracking-tight text-foreground">STAP</h1>
          <p className="mt-1 text-sm text-muted-foreground">Bem-vindo de volta</p>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">
        {/* E-mail */}
        <div className="space-y-1.5">
          <label htmlFor="email" className="block text-sm font-medium text-foreground">
            E-mail
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            aria-label="E-mail"
            aria-invalid={!!errors.email}
            aria-describedby={errors.email ? 'email-error' : undefined}
            className={cn(
              'w-full rounded-lg border bg-background/60 px-3 py-2.5 text-sm text-foreground',
              'placeholder:text-muted-foreground/50 outline-none transition-colors',
              'focus:border-primary focus:ring-2 focus:ring-primary/20',
              errors.email
                ? 'border-red-500 focus:border-red-500 focus:ring-red-500/20'
                : 'border-white/10 hover:border-white/20'
            )}
            placeholder="voce@exemplo.com"
            {...register('email')}
          />
          {errors.email && (
            <p id="email-error" role="alert" className="text-xs text-red-400">
              {errors.email.message}
            </p>
          )}
        </div>

        {/* Senha */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label htmlFor="password" className="block text-sm font-medium text-foreground">
              Senha
            </label>
            <Link
              to="/auth/forgot-password"
              className="text-xs text-primary hover:text-primary/80 transition-colors"
            >
              Esqueceu a senha?
            </Link>
          </div>
          <div className="relative">
            <input
              id="password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              aria-label="Senha"
              aria-invalid={!!errors.password}
              aria-describedby={errors.password ? 'password-error' : undefined}
              className={cn(
                'w-full rounded-lg border bg-background/60 px-3 py-2.5 pr-10 text-sm text-foreground',
                'placeholder:text-muted-foreground/50 outline-none transition-colors',
                'focus:border-primary focus:ring-2 focus:ring-primary/20',
                errors.password
                  ? 'border-red-500 focus:border-red-500 focus:ring-red-500/20'
                  : 'border-white/10 hover:border-white/20'
              )}
              placeholder="••••••••"
              {...register('password')}
            />
            <button
              type="button"
              aria-label={showPassword ? 'Ocultar senha' : 'Mostrar senha'}
              onClick={() => setShowPassword((prev) => !prev)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
            >
              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
          {errors.password && (
            <p id="password-error" role="alert" className="text-xs text-red-400">
              {errors.password.message}
            </p>
          )}
        </div>

        {/* Lembrar de mim */}
        <div className="flex items-center gap-2">
          <input
            id="rememberMe"
            type="checkbox"
            aria-label="Lembrar de mim"
            className="h-4 w-4 rounded border-white/20 bg-background/60 text-primary accent-primary cursor-pointer"
            {...register('rememberMe')}
          />
          <label htmlFor="rememberMe" className="text-sm text-muted-foreground cursor-pointer select-none">
            Lembrar de mim
          </label>
        </div>

        {/* Erro de API */}
        {apiError && (
          <div
            role="alert"
            className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2.5 text-sm text-red-400"
          >
            {apiError}
          </div>
        )}

        {/* Botão de submit */}
        <button
          type="submit"
          disabled={isSubmitting}
          className={cn(
            'w-full rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-white',
            'transition-all hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-primary/50',
            'disabled:cursor-not-allowed disabled:opacity-60',
            'flex items-center justify-center gap-2'
          )}
        >
          {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
          {isSubmitting ? 'Entrando...' : 'Entrar'}
        </button>
      </form>

      {/* Link para cadastro */}
      <p className="mt-6 text-center text-sm text-muted-foreground">
        Não tem conta?{' '}
        <Link
          to={ROUTES.REGISTER}
          className="font-medium text-primary hover:text-primary/80 transition-colors"
        >
          Cadastre-se
        </Link>
      </p>
    </AuthCard>
  );
}
