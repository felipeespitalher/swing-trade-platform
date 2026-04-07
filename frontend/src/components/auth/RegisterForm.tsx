import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link } from 'react-router-dom';
import { Eye, EyeOff, Loader2, BarChart2, CheckCircle2 } from 'lucide-react';
import { registerSchema, type RegisterFormData } from '@/utils/validation';
import { authService } from '@/services/authService';
import { cn } from '@/lib/utils';
import { ROUTES } from '@/config/routes';
import { AuthCard } from './AuthCard';
import { PasswordStrength } from './PasswordStrength';

export function RegisterForm() {
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [successEmail, setSuccessEmail] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  });

  const passwordValue = watch('password', '');

  const onSubmit = async (data: RegisterFormData) => {
    setApiError(null);
    try {
      await authService.register({
        email: data.email,
        password: data.password,
        full_name: data.full_name,
      });
      setSuccessEmail(data.email);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      if (detail?.includes('not verified')) {
        // Account exists but not verified — show success screen (new email was sent)
        setSuccessEmail(data.email);
        return;
      }
      const message = detail ?? 'Erro ao criar conta. Tente novamente.';
      setApiError(message);
    }
  };

  if (successEmail) {
    return (
      <AuthCard>
        <div className="flex flex-col items-center gap-4 py-4 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400">
            <CheckCircle2 className="h-8 w-8" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-foreground">Verifique seu e-mail</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              E-mail de verificação enviado para{' '}
              <span className="font-medium text-foreground">{successEmail}</span>.
              Acesse sua caixa de entrada para ativar sua conta.
            </p>
          </div>
          <Link
            to={ROUTES.LOGIN}
            className="mt-2 text-sm font-medium text-primary hover:text-primary/80 transition-colors"
          >
            Ir para o login
          </Link>
        </div>
      </AuthCard>
    );
  }

  return (
    <AuthCard>
      {/* Logo + heading */}
      <div className="mb-8 flex flex-col items-center gap-3">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/20 text-primary">
          <BarChart2 className="h-7 w-7" />
        </div>
        <div className="text-center">
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Criar Conta</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Comece a automatizar suas estratégias
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">
        {/* Nome completo */}
        <div className="space-y-1.5">
          <label htmlFor="full_name" className="block text-sm font-medium text-foreground">
            Nome completo
          </label>
          <input
            id="full_name"
            type="text"
            autoComplete="name"
            aria-label="Nome completo"
            aria-invalid={!!errors.full_name}
            aria-describedby={errors.full_name ? 'full-name-error' : undefined}
            className={cn(
              'w-full rounded-lg border bg-background/60 px-3 py-2.5 text-sm text-foreground',
              'placeholder:text-muted-foreground/50 outline-none transition-colors',
              'focus:border-primary focus:ring-2 focus:ring-primary/20',
              errors.full_name
                ? 'border-red-500 focus:border-red-500 focus:ring-red-500/20'
                : 'border-white/10 hover:border-white/20'
            )}
            placeholder="João Silva"
            {...register('full_name')}
          />
          {errors.full_name && (
            <p id="full-name-error" role="alert" className="text-xs text-red-400">
              {errors.full_name.message}
            </p>
          )}
        </div>

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
          <label htmlFor="password" className="block text-sm font-medium text-foreground">
            Senha
          </label>
          <div className="relative">
            <input
              id="password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="new-password"
              aria-label="Senha"
              aria-invalid={!!errors.password}
              aria-describedby={errors.password ? 'password-error' : 'password-strength'}
              className={cn(
                'w-full rounded-lg border bg-background/60 px-3 py-2.5 pr-10 text-sm text-foreground',
                'placeholder:text-muted-foreground/50 outline-none transition-colors',
                'focus:border-primary focus:ring-2 focus:ring-primary/20',
                errors.password
                  ? 'border-red-500 focus:border-red-500 focus:ring-red-500/20'
                  : 'border-white/10 hover:border-white/20'
              )}
              placeholder="Mínimo 8 caracteres"
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
          {errors.password ? (
            <p id="password-error" role="alert" className="text-xs text-red-400">
              {errors.password.message}
            </p>
          ) : (
            <div id="password-strength">
              <PasswordStrength password={passwordValue} />
            </div>
          )}
        </div>

        {/* Confirmar senha */}
        <div className="space-y-1.5">
          <label htmlFor="confirmPassword" className="block text-sm font-medium text-foreground">
            Confirmar senha
          </label>
          <div className="relative">
            <input
              id="confirmPassword"
              type={showConfirm ? 'text' : 'password'}
              autoComplete="new-password"
              aria-label="Confirmar senha"
              aria-invalid={!!errors.confirmPassword}
              aria-describedby={errors.confirmPassword ? 'confirm-password-error' : undefined}
              className={cn(
                'w-full rounded-lg border bg-background/60 px-3 py-2.5 pr-10 text-sm text-foreground',
                'placeholder:text-muted-foreground/50 outline-none transition-colors',
                'focus:border-primary focus:ring-2 focus:ring-primary/20',
                errors.confirmPassword
                  ? 'border-red-500 focus:border-red-500 focus:ring-red-500/20'
                  : 'border-white/10 hover:border-white/20'
              )}
              placeholder="Repita a senha"
              {...register('confirmPassword')}
            />
            <button
              type="button"
              aria-label={showConfirm ? 'Ocultar confirmação' : 'Mostrar confirmação'}
              onClick={() => setShowConfirm((prev) => !prev)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
            >
              {showConfirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
          {errors.confirmPassword && (
            <p id="confirm-password-error" role="alert" className="text-xs text-red-400">
              {errors.confirmPassword.message}
            </p>
          )}
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
          {isSubmitting ? 'Criando conta...' : 'Criar conta'}
        </button>
      </form>

      {/* Link para login */}
      <p className="mt-6 text-center text-sm text-muted-foreground">
        Já tem conta?{' '}
        <Link
          to={ROUTES.LOGIN}
          className="font-medium text-primary hover:text-primary/80 transition-colors"
        >
          Entrar
        </Link>
      </p>
    </AuthCard>
  );
}
