import axios from 'axios';
import { useEffect, useState } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { CheckCircle2, XCircle, Loader2, BarChart2 } from 'lucide-react';
import { ROUTES } from '@/config/routes';
import { AuthCard } from '@/components/auth/AuthCard';
import { authService } from '@/services/authService';
import { useAuthStore } from '@/stores/authStore';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

type Status = 'loading' | 'success' | 'error' | 'missing-token';

export default function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token') ?? '';
  const setAuth = useAuthStore((s) => s.setAuth);

  const [status, setStatus] = useState<Status>(token ? 'loading' : 'missing-token');
  const [errorMsg, setErrorMsg] = useState<string>('');

  useEffect(() => {
    if (!token) return;

    authService
      .verifyEmail(token)
      .then(async (data) => {
        const { access_token, refresh_token } = data ?? {};

        if (access_token && refresh_token) {
          try {
            // Usar axios direto com o token explícito — evita o interceptor de 401
            const { data: u } = await axios.get(`${API_BASE}/api/users/me`, {
              headers: { Authorization: `Bearer ${access_token}` },
            });
            setAuth(
              {
                id: u.id,
                email: u.email,
                full_name: `${u.first_name} ${u.last_name}`.trim(),
                timezone: u.timezone,
                risk_limit_pct: u.risk_limit_pct,
                is_active: u.is_active ?? u.is_email_verified,
              },
              access_token,
              refresh_token,
            );
            navigate(ROUTES.DASHBOARD, { replace: true });
            return;
          } catch {
            // getMe falhou — cai no fluxo de login manual
          }
        }

        // Fallback: mostra sucesso e redireciona para login
        setStatus('success');
        setTimeout(() => navigate(ROUTES.LOGIN, { replace: true }), 3000);
      })
      .catch((err: unknown) => {
        const detail =
          (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
          'Link de verificação inválido ou expirado.';
        setErrorMsg(detail);
        setStatus('error');
      });
  }, [token, navigate, setAuth]);

  if (status === 'loading') {
    return (
      <div className="relative min-h-screen overflow-hidden bg-background flex items-center justify-center p-4">
        <AuthCard>
          <div className="flex flex-col items-center gap-4 py-6 text-center">
            <Loader2 className="h-10 w-10 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground">Verificando seu e-mail…</p>
          </div>
        </AuthCard>
      </div>
    );
  }

  if (status === 'success') {
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
            <div className="flex flex-col items-center gap-4 py-4 text-center">
              <div className="flex h-14 w-14 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400">
                <CheckCircle2 className="h-8 w-8" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-foreground">E-mail verificado!</h2>
                <p className="mt-2 text-sm text-muted-foreground">
                  Sua conta está ativa. Redirecionando…
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

  return (
    <div className="relative min-h-screen overflow-hidden bg-background flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:64px_64px] pointer-events-none" />
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
          </div>
          <div className="flex flex-col items-center gap-4 py-2 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-destructive/20 text-destructive">
              <XCircle className="h-8 w-8" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-foreground">Link inválido</h2>
              <p className="mt-2 text-sm text-muted-foreground">
                {status === 'missing-token'
                  ? 'Nenhum token de verificação encontrado no link.'
                  : errorMsg}
              </p>
            </div>
            <Link
              to={ROUTES.LOGIN}
              className="mt-2 text-sm font-medium text-primary transition-colors hover:text-primary/80"
            >
              Voltar para o login
            </Link>
          </div>
        </AuthCard>
      </motion.div>
    </div>
  );
}
