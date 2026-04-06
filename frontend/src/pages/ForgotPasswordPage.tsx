import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link } from 'react-router-dom';
import { z } from 'zod';
import { motion } from 'framer-motion';
import { Loader2, BarChart2, Mail, ArrowLeft } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ROUTES } from '@/config/routes';
import { AuthCard } from '@/components/auth/AuthCard';

const forgotSchema = z.object({
  email: z.string().email('E-mail inválido'),
});

type ForgotFormData = z.infer<typeof forgotSchema>;

function ForgotPasswordForm() {
  const [sent, setSent] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm<ForgotFormData>({
    resolver: zodResolver(forgotSchema),
  });

  const onSubmit = async (_data: ForgotFormData) => {
    setApiError(null);
    try {
      // Endpoint not yet defined in the backend spec — simulating success for now
      await new Promise((resolve) => setTimeout(resolve, 800));
      setSent(true);
    } catch {
      setApiError('Não foi possível enviar o e-mail. Tente novamente.');
    }
  };

  if (sent) {
    return (
      <AuthCard>
        <div className="flex flex-col items-center gap-4 py-4 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-primary/20 text-primary">
            <Mail className="h-8 w-8" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-foreground">E-mail enviado!</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Verifique sua caixa de entrada em{' '}
              <span className="font-medium text-foreground">{getValues('email')}</span>{' '}
              para redefinir sua senha.
            </p>
          </div>
          <Link
            to={ROUTES.LOGIN}
            className="mt-2 inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:text-primary/80 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Voltar para o login
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
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Recuperar senha</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Informe seu e-mail para receber o link de recuperação
          </p>
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
          {isSubmitting ? 'Enviando...' : 'Enviar link de recuperação'}
        </button>
      </form>

      {/* Voltar para login */}
      <p className="mt-6 text-center">
        <Link
          to={ROUTES.LOGIN}
          className="inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Voltar para o login
        </Link>
      </p>
    </AuthCard>
  );
}

export default function ForgotPasswordPage() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-background flex items-center justify-center p-4">
      {/* Background grid decoration */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:64px_64px] pointer-events-none" />

      {/* Gradient orbs */}
      <div className="absolute top-1/3 left-1/3 w-80 h-80 bg-primary/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/3 right-1/3 w-80 h-80 bg-sky-500/10 rounded-full blur-3xl pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
        className="w-full max-w-md"
      >
        <ForgotPasswordForm />
      </motion.div>
    </div>
  );
}
