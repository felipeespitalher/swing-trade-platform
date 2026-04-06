import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { motion } from 'framer-motion';
import {
  Eye,
  EyeOff,
  Trash2,
  Plus,
  Loader2,
  Shield,
  Key,
  User,
  SlidersHorizontal,
} from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import { useTheme } from '@/context/ThemeContext';
import { useNotification } from '@/hooks/useNotification';

const pageVariants = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0 },
};

// ─── Account tab schema ───────────────────────────────────────────────────────
const accountSchema = z.object({
  full_name: z.string().min(2, 'Nome deve ter ao menos 2 caracteres'),
  timezone: z.string().min(1, 'Selecione um fuso horário'),
  risk_limit_pct: z.coerce
    .number()
    .min(0.1, 'Mínimo 0.1%')
    .max(20, 'Máximo 20%'),
});
type AccountValues = z.infer<typeof accountSchema>;

// ─── Password tab schema ──────────────────────────────────────────────────────
const passwordSchema = z
  .object({
    old_password: z.string().min(1, 'Informe a senha atual'),
    new_password: z.string().min(8, 'Mínima 8 caracteres'),
    confirm_password: z.string().min(1, 'Confirme a nova senha'),
  })
  .refine((d) => d.new_password === d.confirm_password, {
    message: 'As senhas não coincidem',
    path: ['confirm_password'],
  });
type PasswordValues = z.infer<typeof passwordSchema>;

// ─── Exchange key schema ──────────────────────────────────────────────────────
const exchangeKeySchema = z.object({
  exchange: z.string().min(1, 'Selecione uma exchange'),
  label: z.string().min(1, 'Informe um rótulo'),
  api_key: z.string().min(10, 'API Key inválida'),
  api_secret: z.string().min(10, 'API Secret inválido'),
});
type ExchangeKeyValues = z.infer<typeof exchangeKeySchema>;

// ─── Mock exchange keys ───────────────────────────────────────────────────────
interface MockExchangeKey {
  id: string;
  exchange: string;
  label: string;
  api_key_masked: string;
  created_at: string;
  is_active: boolean;
}

const MOCK_KEYS: MockExchangeKey[] = [
  {
    id: '1',
    exchange: 'Binance',
    label: 'Conta Principal',
    api_key_masked: 'ABCD...WXYZ',
    created_at: '2025-01-10',
    is_active: true,
  },
];

// ─── Mock audit log ───────────────────────────────────────────────────────────
const AUDIT_LOG = [
  { id: '1', action: 'Login realizado', date: '2026-04-02 09:15', ip: '192.168.1.1' },
  { id: '2', action: 'Estratégia criada', date: '2026-04-01 14:30', ip: '192.168.1.1' },
  { id: '3', action: 'Backtest executado', date: '2026-03-30 11:00', ip: '192.168.1.1' },
  { id: '4', action: 'Senha alterada', date: '2026-03-28 16:45', ip: '192.168.1.2' },
  { id: '5', action: 'Chave de exchange adicionada', date: '2026-03-25 10:20', ip: '192.168.1.1' },
];

// ─── Tab definitions ──────────────────────────────────────────────────────────
type TabId = 'account' | 'exchanges' | 'preferences' | 'security';

interface Tab {
  id: TabId;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

const TABS: Tab[] = [
  { id: 'account', label: 'Conta', icon: User },
  { id: 'exchanges', label: 'Chaves de Exchange', icon: Key },
  { id: 'preferences', label: 'Preferências', icon: SlidersHorizontal },
  { id: 'security', label: 'Segurança', icon: Shield },
];

// ─── Input helper ─────────────────────────────────────────────────────────────
function InputField({
  id,
  label,
  error,
  children,
}: {
  id: string;
  label: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-slate-300 mb-1">
        {label}
      </label>
      {children}
      {error && <p className="mt-1 text-xs text-red-400">{error}</p>}
    </div>
  );
}

const inputCls =
  'w-full rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-50';

// ─── Account Tab ──────────────────────────────────────────────────────────────
function AccountTab() {
  const user = useAuthStore((s) => s.user);
  const notify = useNotification();
  const [saving, setSaving] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<AccountValues>({
    resolver: zodResolver(accountSchema),
    defaultValues: {
      full_name: user?.full_name ?? '',
      timezone: user?.timezone ?? 'America/Sao_Paulo',
      risk_limit_pct: user?.risk_limit_pct ?? 2,
    },
  });

  async function onSubmit() {
    setSaving(true);
    await new Promise((r) => setTimeout(r, 800));
    setSaving(false);
    notify.success('Configurações salvas', 'Suas preferências foram atualizadas.');
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5 max-w-lg">
      <InputField id="full_name" label="Nome Completo" error={errors.full_name?.message}>
        <input
          id="full_name"
          type="text"
          placeholder="Seu nome"
          {...register('full_name')}
          className={inputCls}
        />
      </InputField>

      <InputField id="email" label="E-mail">
        <input
          id="email"
          type="email"
          value={user?.email ?? ''}
          readOnly
          className={`${inputCls} cursor-not-allowed`}
        />
        <p className="mt-1 text-xs text-slate-500">
          Para alterar o e-mail, entre em contato com o suporte.
        </p>
      </InputField>

      <InputField id="timezone" label="Fuso Horário" error={errors.timezone?.message}>
        <select id="timezone" {...register('timezone')} className={inputCls}>
          <option value="UTC">UTC</option>
          <option value="America/Sao_Paulo">America/Sao_Paulo (BRT)</option>
          <option value="America/New_York">America/New_York (EST)</option>
          <option value="Europe/London">Europe/London (GMT)</option>
          <option value="Asia/Tokyo">Asia/Tokyo (JST)</option>
        </select>
      </InputField>

      <InputField
        id="risk_limit_pct"
        label="Limite de Risco por Operação (%)"
        error={errors.risk_limit_pct?.message}
      >
        <input
          id="risk_limit_pct"
          type="number"
          step={0.1}
          min={0.1}
          max={20}
          {...register('risk_limit_pct')}
          className={inputCls}
        />
      </InputField>

      <button
        type="submit"
        disabled={saving}
        className="flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-blue-500 disabled:opacity-60"
      >
        {saving && <Loader2 className="h-4 w-4 animate-spin" />}
        Salvar Alterações
      </button>
    </form>
  );
}

// ─── Exchange Keys Tab ────────────────────────────────────────────────────────
function ExchangeKeysTab() {
  const [keys, setKeys] = useState<MockExchangeKey[]>(MOCK_KEYS);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);
  const [showApiSecret, setShowApiSecret] = useState(false);
  const notify = useNotification();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ExchangeKeyValues>({
    resolver: zodResolver(exchangeKeySchema),
  });

  async function onSubmit(values: ExchangeKeyValues) {
    setSaving(true);
    await new Promise((r) => setTimeout(r, 800));
    const newKey: MockExchangeKey = {
      id: crypto.randomUUID(),
      exchange: values.exchange,
      label: values.label,
      api_key_masked: `${values.api_key.slice(0, 4)}...${values.api_key.slice(-4)}`,
      created_at: new Date().toISOString().split('T')[0],
      is_active: true,
    };
    setKeys((prev) => [...prev, newKey]);
    setSaving(false);
    setShowForm(false);
    reset();
    notify.success('Chave adicionada', `${values.exchange} conectada com sucesso.`);
  }

  function handleDelete(id: string) {
    setKeys((prev) => prev.filter((k) => k.id !== id));
    notify.info('Chave removida', 'A chave de API foi desconectada.');
  }

  return (
    <div className="space-y-4 max-w-xl">
      {/* Existing keys */}
      {keys.length === 0 ? (
        <p className="text-sm text-slate-500">Nenhuma exchange conectada.</p>
      ) : (
        <div className="space-y-3">
          {keys.map((key) => (
            <div
              key={key.id}
              className="flex items-center justify-between rounded-lg border border-slate-700 bg-slate-800 px-4 py-3"
            >
              <div>
                <p className="text-sm font-medium text-white">{key.exchange}</p>
                <p className="text-xs text-slate-400">{key.label}</p>
                <p className="mt-0.5 font-mono text-xs text-slate-500">{key.api_key_masked}</p>
              </div>
              <div className="flex items-center gap-3">
                {key.is_active && (
                  <span className="rounded-full bg-emerald-900/50 px-2 py-0.5 text-xs text-emerald-400">
                    Ativa
                  </span>
                )}
                <button
                  onClick={() => handleDelete(key.id)}
                  aria-label={`Remover chave ${key.label}`}
                  className="rounded p-1 text-slate-400 transition-colors hover:bg-red-900/40 hover:text-red-400"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add key button */}
      {!showForm && (
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 rounded-md border border-slate-700 bg-slate-800 px-4 py-2 text-sm text-slate-300 transition-colors hover:border-blue-500 hover:text-white"
        >
          <Plus className="h-4 w-4" />
          Adicionar Exchange
        </button>
      )}

      {/* Inline add form */}
      {showForm && (
        <form
          onSubmit={handleSubmit(onSubmit)}
          className="rounded-lg border border-slate-700 bg-slate-800 p-4 space-y-3"
        >
          <h3 className="text-sm font-semibold text-white">Nova Chave de API</h3>

          <InputField id="exchange" label="Exchange" error={errors.exchange?.message}>
            <select id="exchange" {...register('exchange')} className={inputCls}>
              <option value="">Selecione...</option>
              <option value="Binance">Binance</option>
              <option value="Coinbase">Coinbase</option>
              <option value="Kraken">Kraken</option>
            </select>
          </InputField>

          <InputField id="label" label="Rótulo" error={errors.label?.message}>
            <input
              id="label"
              type="text"
              placeholder="Ex: Conta Principal"
              {...register('label')}
              className={inputCls}
            />
          </InputField>

          <InputField id="api_key" label="API Key" error={errors.api_key?.message}>
            <div className="relative">
              <input
                id="api_key"
                type={showApiKey ? 'text' : 'password'}
                placeholder="Sua API Key"
                {...register('api_key')}
                className={`${inputCls} pr-10`}
              />
              <button
                type="button"
                aria-label={showApiKey ? 'Ocultar API Key' : 'Mostrar API Key'}
                onClick={() => setShowApiKey((v) => !v)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
              >
                {showApiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </InputField>

          <InputField id="api_secret" label="API Secret" error={errors.api_secret?.message}>
            <div className="relative">
              <input
                id="api_secret"
                type={showApiSecret ? 'text' : 'password'}
                placeholder="Sua API Secret"
                {...register('api_secret')}
                className={`${inputCls} pr-10`}
              />
              <button
                type="button"
                aria-label={showApiSecret ? 'Ocultar API Secret' : 'Mostrar API Secret'}
                onClick={() => setShowApiSecret((v) => !v)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
              >
                {showApiSecret ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </InputField>

          <div className="flex gap-2 pt-1">
            <button
              type="submit"
              disabled={saving}
              className="flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-blue-500 disabled:opacity-60"
            >
              {saving && <Loader2 className="h-4 w-4 animate-spin" />}
              Salvar
            </button>
            <button
              type="button"
              onClick={() => {
                setShowForm(false);
                reset();
              }}
              className="rounded-md border border-slate-700 px-4 py-2 text-sm text-slate-400 transition-colors hover:text-white"
            >
              Cancelar
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

// ─── Preferences Tab ──────────────────────────────────────────────────────────
function PreferencesTab() {
  const { theme, setTheme } = useTheme();
  const [language, setLanguage] = useState('pt');
  const [notifications, setNotifications] = useState({
    trade_executed: true,
    backtest_completed: true,
    price_alert: false,
  });
  const notify = useNotification();

  function toggleNotification(key: keyof typeof notifications) {
    setNotifications((prev) => {
      const next = { ...prev, [key]: !prev[key] };
      notify.info(
        'Preferência atualizada',
        `Notificação ${next[key] ? 'ativada' : 'desativada'}.`,
      );
      return next;
    });
  }

  return (
    <div className="space-y-6 max-w-lg">
      {/* Theme */}
      <div>
        <h3 className="text-sm font-semibold text-white mb-3">Tema</h3>
        <div className="flex gap-2">
          {(['dark', 'light', 'system'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTheme(t)}
              className={`rounded-md border px-4 py-1.5 text-sm capitalize transition-colors ${
                theme === t
                  ? 'border-blue-500 bg-blue-600/20 text-blue-400'
                  : 'border-slate-700 text-slate-400 hover:border-slate-500 hover:text-white'
              }`}
            >
              {t === 'dark' ? 'Escuro' : t === 'light' ? 'Claro' : 'Sistema'}
            </button>
          ))}
        </div>
      </div>

      {/* Language */}
      <div>
        <label htmlFor="language" className="block text-sm font-semibold text-white mb-3">
          Idioma
        </label>
        <select
          id="language"
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          className={`${inputCls} max-w-xs`}
        >
          <option value="pt">Português</option>
          <option value="en">English</option>
        </select>
      </div>

      {/* Notifications */}
      <div>
        <h3 className="text-sm font-semibold text-white mb-3">Notificações</h3>
        <div className="space-y-3">
          {(
            [
              { key: 'trade_executed', label: 'Operação executada' },
              { key: 'backtest_completed', label: 'Backtest concluído' },
              { key: 'price_alert', label: 'Alerta de preço' },
            ] as const
          ).map(({ key, label }) => (
            <div key={key} className="flex items-center justify-between">
              <span className="text-sm text-slate-300">{label}</span>
              <button
                role="switch"
                aria-checked={notifications[key]}
                onClick={() => toggleNotification(key)}
                className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none ${
                  notifications[key] ? 'bg-blue-600' : 'bg-slate-700'
                }`}
              >
                <span
                  className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                    notifications[key] ? 'translate-x-4' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Security Tab ─────────────────────────────────────────────────────────────
function SecurityTab() {
  const [saving, setSaving] = useState(false);
  const [showOld, setShowOld] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const notify = useNotification();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<PasswordValues>({
    resolver: zodResolver(passwordSchema),
  });

  async function onSubmit() {
    setSaving(true);
    await new Promise((r) => setTimeout(r, 800));
    setSaving(false);
    reset();
    notify.success('Senha alterada', 'Sua senha foi atualizada com sucesso.');
  }

  return (
    <div className="space-y-6">
      {/* Change Password */}
      <div className="max-w-md">
        <h3 className="mb-4 text-sm font-semibold text-white">Alterar Senha</h3>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <InputField
            id="old_password"
            label="Senha Atual"
            error={errors.old_password?.message}
          >
            <div className="relative">
              <input
                id="old_password"
                type={showOld ? 'text' : 'password'}
                {...register('old_password')}
                className={`${inputCls} pr-10`}
              />
              <button
                type="button"
                aria-label={showOld ? 'Ocultar senha atual' : 'Mostrar senha atual'}
                onClick={() => setShowOld((v) => !v)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
              >
                {showOld ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </InputField>

          <InputField
            id="new_password"
            label="Nova Senha"
            error={errors.new_password?.message}
          >
            <div className="relative">
              <input
                id="new_password"
                type={showNew ? 'text' : 'password'}
                {...register('new_password')}
                className={`${inputCls} pr-10`}
              />
              <button
                type="button"
                aria-label={showNew ? 'Ocultar nova senha' : 'Mostrar nova senha'}
                onClick={() => setShowNew((v) => !v)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
              >
                {showNew ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </InputField>

          <InputField
            id="confirm_password"
            label="Confirmar Nova Senha"
            error={errors.confirm_password?.message}
          >
            <div className="relative">
              <input
                id="confirm_password"
                type={showConfirm ? 'text' : 'password'}
                {...register('confirm_password')}
                className={`${inputCls} pr-10`}
              />
              <button
                type="button"
                aria-label={showConfirm ? 'Ocultar confirmação de senha' : 'Mostrar confirmação de senha'}
                onClick={() => setShowConfirm((v) => !v)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
              >
                {showConfirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </InputField>

          <button
            type="submit"
            disabled={saving}
            className="flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-blue-500 disabled:opacity-60"
          >
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            Alterar Senha
          </button>
        </form>
      </div>

      {/* Active sessions */}
      <div>
        <h3 className="mb-3 text-sm font-semibold text-white">Sessões Ativas</h3>
        <div className="rounded-lg border border-slate-700 bg-slate-800 px-4 py-3 text-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-white">Sessão atual</p>
              <p className="text-xs text-slate-400">Chrome / Windows — 192.168.1.1</p>
            </div>
            <span className="rounded-full bg-emerald-900/50 px-2 py-0.5 text-xs text-emerald-400">
              Ativa
            </span>
          </div>
        </div>
      </div>

      {/* Audit log */}
      <div>
        <h3 className="mb-3 text-sm font-semibold text-white">Log de Auditoria</h3>
        <div className="rounded-lg border border-slate-700 bg-slate-900 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700 text-left text-xs font-medium uppercase tracking-wide text-slate-400">
                <th className="px-4 py-3">Ação</th>
                <th className="px-4 py-3">Data</th>
                <th className="px-4 py-3">IP</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {AUDIT_LOG.map((entry) => (
                <tr key={entry.id} className="hover:bg-slate-800/50 transition-colors">
                  <td className="px-4 py-2.5 text-slate-300">{entry.action}</td>
                  <td className="px-4 py-2.5 font-mono text-xs text-slate-400">{entry.date}</td>
                  <td className="px-4 py-2.5 font-mono text-xs text-slate-500">{entry.ip}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ─── Main SettingsPage ────────────────────────────────────────────────────────
export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabId>('account');

  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      transition={{ duration: 0.25, ease: 'easeOut' }}
      className="space-y-6"
    >
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Configurações</h1>
        <p className="mt-1 text-sm text-slate-400">Gerencie sua conta e preferências</p>
      </div>

      {/* Tab navigation */}
      <div className="border-b border-slate-700">
        <nav className="-mb-px flex gap-0 overflow-x-auto">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                aria-current={isActive ? 'page' : undefined}
                className={`flex shrink-0 items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium transition-colors ${
                  isActive
                    ? 'border-blue-500 text-blue-400'
                    : 'border-transparent text-slate-400 hover:border-slate-500 hover:text-slate-200'
                }`}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab content */}
      <div className="rounded-lg border border-slate-700 bg-slate-900 p-5">
        {activeTab === 'account' && <AccountTab />}
        {activeTab === 'exchanges' && <ExchangeKeysTab />}
        {activeTab === 'preferences' && <PreferencesTab />}
        {activeTab === 'security' && <SecurityTab />}
      </div>
    </motion.div>
  );
}
