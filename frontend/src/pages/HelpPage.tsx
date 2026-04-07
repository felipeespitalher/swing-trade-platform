import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  BookOpen,
  UserPlus,
  LayoutDashboard,
  Zap,
  BarChart,
  Wallet,
  Settings,
  ChevronDown,
  ChevronUp,
  Key,
  TrendingUp,
} from 'lucide-react';

const pageVariants = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0 },
};

interface Step {
  title: string;
  description: string;
}

interface Section {
  id: string;
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  subtitle: string;
  steps: Step[];
}

const SECTIONS: Section[] = [
  {
    id: 'getting-started',
    icon: UserPlus,
    title: 'Primeiros Passos',
    subtitle: 'Como criar sua conta e acessar a plataforma',
    steps: [
      {
        title: '1. Crie sua conta',
        description:
          'Acesse a página de cadastro e informe seu nome, e-mail e uma senha segura (mínimo 8 caracteres). Após o cadastro, você receberá um e-mail de verificação.',
      },
      {
        title: '2. Verifique seu e-mail',
        description:
          'Clique no link enviado para o seu e-mail para ativar sua conta. O link redireciona automaticamente para o app. Caso o e-mail não chegue, verifique a caixa de spam ou solicite um novo no login.',
      },
      {
        title: '3. Faça login',
        description:
          'Após a verificação, faça login com seu e-mail e senha. Você será direcionado ao Dashboard principal.',
      },
    ],
  },
  {
    id: 'dashboard',
    icon: LayoutDashboard,
    title: 'Dashboard',
    subtitle: 'Visão geral da sua performance de trading',
    steps: [
      {
        title: 'Resumo de performance',
        description:
          'O Dashboard exibe métricas consolidadas: lucro/prejuízo total, número de operações, taxa de acerto e drawdown máximo de todas as suas estratégias ativas.',
      },
      {
        title: 'Gráficos e histórico',
        description:
          'Visualize a evolução do seu portfólio ao longo do tempo. Os gráficos são atualizados conforme suas estratégias executam operações.',
      },
      {
        title: 'Alertas e notificações',
        description:
          'Configure alertas de preço e notificações de operações em Configurações → Preferências para receber avisos em tempo real.',
      },
    ],
  },
  {
    id: 'strategies',
    icon: Zap,
    title: 'Estratégias',
    subtitle: 'Como criar e gerenciar estratégias de trading',
    steps: [
      {
        title: '1. Adicione uma chave de exchange',
        description:
          'Antes de criar uma estratégia, vá em Configurações → Chaves de Exchange e adicione sua API Key e Secret da Binance, Coinbase ou Kraken. A chave deve ter permissão de leitura e trading.',
      },
      {
        title: '2. Crie uma estratégia',
        description:
          'Na página Estratégias, clique em "Nova Estratégia". Defina o par de moedas (ex: BTC/USDT), o timeframe (ex: 4h), o tipo de estratégia, stop loss e take profit. Selecione a chave de exchange a ser utilizada.',
      },
      {
        title: '3. Ative a estratégia',
        description:
          'Após criar, você pode ativar ou desativar a estratégia pelo botão de toggle. Estratégias ativas monitoram o mercado e executam ordens automaticamente.',
      },
      {
        title: '4. Associe a uma carteira',
        description:
          'Em Carteiras, você pode organizar suas estratégias em grupos (ex: "Carteira Agressiva", "Carteira Conservadora") para acompanhar a performance separadamente.',
      },
    ],
  },
  {
    id: 'backtester',
    icon: BarChart,
    title: 'Backtester',
    subtitle: 'Como testar estratégias em dados históricos',
    steps: [
      {
        title: '1. Configure o backtest',
        description:
          'Acesse o Backtester e selecione o par de moedas, o período de teste (data inicial e final), o capital inicial e a estratégia que deseja avaliar.',
      },
      {
        title: '2. Execute o backtest',
        description:
          'Clique em "Executar Backtest". O sistema simulará todas as operações que a estratégia teria realizado no período histórico selecionado.',
      },
      {
        title: '3. Analise os resultados',
        description:
          'Os resultados incluem: lucro líquido, número de operações, taxa de acerto, drawdown máximo e gráfico de curva de capital. Use esses dados para ajustar seus parâmetros antes de operar com dinheiro real.',
      },
      {
        title: 'Dica',
        description:
          'Realize backtests em diferentes períodos (touro, urso, lateral) para verificar a robustez da estratégia em variados cenários de mercado.',
      },
    ],
  },
  {
    id: 'portfolios',
    icon: Wallet,
    title: 'Carteiras',
    subtitle: 'Como organizar estratégias em carteiras',
    steps: [
      {
        title: '1. Crie uma carteira',
        description:
          'Na página Carteiras, clique em "Nova Carteira". Defina um nome, o capital alocado, o perfil de risco e uma descrição opcional.',
      },
      {
        title: '2. Associe estratégias',
        description:
          'Após criar uma carteira, você pode associar estratégias existentes a ela. Isso permite acompanhar a performance de cada grupo de estratégias separadamente.',
      },
      {
        title: '3. Monitore por carteira',
        description:
          'Cada carteira exibe métricas independentes: capital alocado, número de estratégias, perfil de risco e performance acumulada.',
      },
    ],
  },
  {
    id: 'exchange-keys',
    icon: Key,
    title: 'Chaves de Exchange',
    subtitle: 'Como conectar sua exchange com segurança',
    steps: [
      {
        title: '1. Gere a chave na exchange',
        description:
          'Acesse a sua exchange (Binance, Coinbase, Kraken), vá em Configurações de API e crie uma nova chave. Habilite as permissões de "Leitura" e "Trading". NÃO habilite permissão de saque.',
      },
      {
        title: '2. Adicione no app',
        description:
          'Em Configurações → Chaves de Exchange, clique em "Adicionar Exchange". Informe o nome da exchange, um rótulo para identificação, a API Key e o API Secret.',
      },
      {
        title: '3. Segurança',
        description:
          'Suas chaves são armazenadas de forma criptografada. Apenas os últimos caracteres da API Key são exibidos após o cadastro. Nunca compartilhe suas chaves com ninguém.',
      },
    ],
  },
  {
    id: 'investor-profile',
    icon: TrendingUp,
    title: 'Perfil de Investidor',
    subtitle: 'Como definir seu perfil para melhores recomendações',
    steps: [
      {
        title: 'Acesse o perfil',
        description:
          'Em Configurações → Perfil de Investidor, você encontra um formulário para definir seu nível de experiência, tolerância ao risco, mercados preferidos e capital disponível.',
      },
      {
        title: 'Perfil de risco',
        description:
          'Escolha entre Conservador (foco em preservação), Moderado (equilíbrio) ou Agressivo (foco em retorno). Esse perfil orienta o sistema nas sugestões de estratégias e limites de operação.',
      },
      {
        title: 'Mantenha atualizado',
        description:
          'Atualize seu perfil conforme sua experiência e objetivos evoluem. O sistema utilizará essas informações para personalizar recomendações.',
      },
    ],
  },
  {
    id: 'settings',
    icon: Settings,
    title: 'Configurações',
    subtitle: 'Personalize sua conta e preferências',
    steps: [
      {
        title: 'Conta',
        description:
          'Atualize seu nome, fuso horário e limite de risco por operação (%). O limite de risco define a porcentagem máxima do capital que pode ser arriscada em uma única operação.',
      },
      {
        title: 'Segurança',
        description:
          'Altere sua senha quando necessário. O log de auditoria registra todas as ações relevantes na sua conta, como logins, criação de estratégias e alterações de configuração.',
      },
      {
        title: 'Preferências',
        description:
          'Escolha entre tema escuro, claro ou o tema do sistema. Configure quais notificações deseja receber para operações executadas, backtests concluídos e alertas de preço.',
      },
    ],
  },
];

function SectionCard({ section }: { section: Section }) {
  const [open, setOpen] = useState(false);
  const Icon = section.icon;

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900 overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-slate-800/50 transition-colors"
        aria-expanded={open}
      >
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600/20 text-blue-400 shrink-0">
            <Icon className="h-4 w-4" />
          </div>
          <div>
            <p className="text-sm font-semibold text-white">{section.title}</p>
            <p className="text-xs text-slate-400">{section.subtitle}</p>
          </div>
        </div>
        {open ? (
          <ChevronUp className="h-4 w-4 text-slate-400 shrink-0" />
        ) : (
          <ChevronDown className="h-4 w-4 text-slate-400 shrink-0" />
        )}
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className="overflow-hidden"
          >
            <div className="border-t border-slate-700 px-5 py-4 space-y-4">
              {section.steps.map((step, i) => (
                <div key={i} className="flex gap-3">
                  <div className="flex h-5 w-5 items-center justify-center rounded-full bg-blue-600/20 text-blue-400 text-xs font-bold shrink-0 mt-0.5">
                    {String(i + 1)}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-white">{step.title}</p>
                    <p className="mt-1 text-sm text-slate-400 leading-relaxed">{step.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function HelpPage() {
  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      transition={{ duration: 0.25, ease: 'easeOut' }}
      className="space-y-6 max-w-3xl"
    >
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600/20 text-blue-400">
          <BookOpen className="h-5 w-5" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white">Guia de Uso</h1>
          <p className="text-sm text-slate-400">Aprenda a utilizar todas as funcionalidades da plataforma</p>
        </div>
      </div>

      {/* Quick start banner */}
      <div className="rounded-lg border border-blue-500/30 bg-blue-600/10 px-5 py-4">
        <p className="text-sm font-semibold text-blue-300 mb-1">Para começar rapidamente:</p>
        <ol className="text-sm text-slate-300 space-y-1 list-decimal list-inside">
          <li>Crie sua conta e verifique o e-mail</li>
          <li>Em Configurações → Chaves de Exchange, adicione sua API Key</li>
          <li>Crie uma estratégia e execute um backtest para validá-la</li>
          <li>Ative a estratégia para operar automaticamente</li>
        </ol>
      </div>

      {/* Sections */}
      <div className="space-y-3">
        {SECTIONS.map((section) => (
          <SectionCard key={section.id} section={section} />
        ))}
      </div>

      <p className="text-xs text-slate-500 text-center pb-4">
        Precisa de ajuda adicional? Entre em contato com o suporte.
      </p>
    </motion.div>
  );
}
