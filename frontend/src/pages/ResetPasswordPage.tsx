import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { z } from 'zod';
import { motion } from 'framer-motion';
import { Loader2, BarChart2, Eye, EyeOff, CheckCircle2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ROUTES } from '@/config/routes';
import { AuthCard } from '@/components/auth/AuthCard';
import { authService } from '@/services/authService';

const resetSchema = z
  .object({
    new_password: z
      .string()
      .min(8, 'Mínimo 8 caracteres')
      .regex(/[A-Z]/, 'Deve conter ao menos uma letra maiúscula')
      .regex(/[a-z]/, 'Deve conter ao menos uma letra minúscula')
      .regex(/\d/, 'Deve conter ao menos um número')
      .regex(/[!@#$%^&*()_+\-=\[\]{};:'",./<>?]/, 'Deve conter ao menos um caractere especial'),
    confirm_password: z.string().min(1, 'Confirme a nova senha'),
  })
  .refine((d) => d.new_password === d.confirm_password, {
    message: 'As senhas não coincidem',
    path: ['confirm_password'],
  });

type ResetFormData = z.infer<typeof resetSchema>;

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token') ?? '';

  const [done, setDone] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ResetFormData>({ resolver: zodResolver(resetSchema) });

  if (!token) {
    return (
      <div className="relative min-h-screen overflow-hidden bg-background flex items-center justify-center p-4">
        <AuthCard>
          <div className="flex flex-col items-center gap-4 py-4 text-center">
            <p className="text-sm text-red-400">Link de redefinição inválido ou expirado.</p>
            <Link
              to={ROUTES.FORGOT_PASSWORD}
              className="text-sm font-medium text-primary hover:text-primary/80 transition-colors"
            >
              Solicitar novo link
            </Link>
          </div>
        </AuthCard>
      </div>
    );
  }

  if (done) {
    return (
      <div className="relative min-h-screen overflow-hidden bg-background flex items-center justify-center p-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
          className="w-full max-w-md"
        >
          <AuthCard>
            <div className="flex flex-col items-center gap-4 py-4 text-center">
              <div className="flex h-14 w-14 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400">
                <CheckCircle2 className="h-8 w-8" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-foreground">Senha redefinida!</h2>
                <p className="mt-2 text-sm text-muted-foreground">
                  Sua senha foi atualizada com sucesso.
                </p>
              </div>
              <button
                onClick={() => navigate(ROUTES.LOGIN, { replace: true })}
                className="mt-2 w-full rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-primary/90"
              >
                Fazer Login
              </button>
            </div>
          </AuthCard>
        </motion.div>
      </div>
    );
  }

  const onSubmit = async (data: ResetFormData) => {
    setApiError(null);
    try {
      await authService.resetPassword(token, data.new_password);
      setDone(true);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Não foi possível redefinir a senha. O link pode ter expirado.';
      setApiError(msg);
    }
  };

  const inputCls = cn(
    'w-full rounded-lg border bg-input/50 px-3 py-2.5 text-sm text-foreground',
    'placeholder:text-muted-foreground/50 outline-none transition-colors',
    'focus:border-primary focus:ring-2 focus:ring-primary/20',
  );

  return (
    <div className="relative min-h-screen overflow-hidden bg-background flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:64px_64px] pointer-events-none" />
      <div className="absolute top-1/4 right-1/4 w-96 h-96 bg-primary/10 rounded-full blur-3xl pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
        className="w-full max-w-md"
      >
        <AuthCard>
          <div className="mb-8 flex flex-col items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/20 text-primary">
              <BarChart2 className="h-7 w-7" />
            </div>
            <div className="text-center">
              <h1 className="text-2xl font-bold tracking-tight text-foreground">Nova Senha</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                Crie uma senha forte para sua conta
              </p>
            </div>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-5">
            {apiError && (
              <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                {apiError}
              </div>
            )}

            {/* Nova senha */}
            <div className="space-y-1.5">
              <label htmlFor="new_password" className="block text-sm font-medium text-foreground">
                Nova Senha
              </label>
              <div className="relative">
                <input
                  id="new_password"
                  type={showNew ? 'text' : 'password'}
                  autoComplete="new-password"
                  placeholder="Mínimo 8 caracteres"
                  {...register('new_password')}
                  className={cn(inputCls, 'pr-10', errors.new_password && 'border-destructive')}
                />
                <button
                  type="button"
                  onClick={() => setShowNew((v) => !v)}
                  aria-label={showNew ? 'Ocultar senha' : 'Mostrar senha'}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors hover:text-foreground"
                >
                  {showNew ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {errors.new_password && (
                <p className="text-xs text-destructive">{errors.new_password.message}</p>
              )}
            </div>

            {/* Confirmar senha */}
            <div className="space-y-1.5">
              <label htmlFor="confirm_password" className="block text-sm font-medium text-foreground">
                Confirmar Senha
              </label>
              <div className="relative">
                <input
                  id="confirm_password"
                  type={showConfirm ? 'text' : 'password'}
                  autoComplete="new-password"
                  placeholder="Repita a nova senha"
                  {...register('confirm_password')}
                  className={cn(inputCls, 'pr-10', errors.confirm_password && 'border-destructive')}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirm((v) => !v)}
                  aria-label={showConfirm ? 'Ocultar senha' : 'Mostrar senha'}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors hover:text-foreground"
                >
                  {showConfirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {errors.confirm_password && (
                <p className="text-xs text-destructive">{errors.confirm_password.message}</p>
              )}
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className={cn(
                'flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-primary/90',
                isSubmitting && 'cursor-not-allowed opacity-60',
              )}
            >
              {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
              Redefinir Senha
            </button>

            <p className="text-center text-sm text-muted-foreground">
              <Link
                to={ROUTES.LOGIN}
                className="font-medium text-primary transition-colors hover:text-primary/80"
              >
                Voltar para o login
              </Link>
            </p>
          </form>
        </AuthCard>
      </motion.div>
    </div>
  );
}
