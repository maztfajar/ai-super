import { useEffect, useState, useRef } from 'react'
import { api } from '../hooks/useApi'
import {
  Activity, Bot, Zap, Cpu, Shield, Clock, ChevronRight,
  CheckCircle, XCircle, AlertTriangle, RefreshCw,
  BrainCircuit, Code2, Search, PenTool, Terminal,
  Palette, ClipboardCheck, MessageSquare, TrendingUp,
  Radio, Layers, Eye, Wifi, WifiOff
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import clsx from 'clsx'
import LiveModelPerformanceChart from '../components/MonitoringCharts'
import { ActiveSessionCardNew } from '../components/ActiveSessionCard'
import { AgentRegistry } from '../components/AgentRegistry'

// ── Agent Type Config ───────────────────────────────────────────
const AGENT_CONFIG = {
  reasoning:  { icon: BrainCircuit, color: '#8B5CF6', label: '🧠 Reasoning' },
  coding:     { icon: Code2,        color: '#3B82F6', label: '💻 Coding' },
  research:   { icon: Search,       color: '#10B981', label: '🔍 Research' },
  writing:    { icon: PenTool,      color: '#F59E0B', label: '✍️ Writing' },
  system:     { icon: Terminal,     color: '#EF4444', label: '🖥️ System' },
  creative:   { icon: Palette,      color: '#EC4899', label: '🎨 Creative' },
  validation: { icon: ClipboardCheck, color: '#06B6D4', label: '✅ Validation' },
  general:    { icon: MessageSquare,  color: '#64748B', label: '💬 General' },
}

// Warna gradient per model/provider
const modelColor = (model = '') => {
  const m = model.toLowerCase()
  if (m.includes('gpt') || m.includes('openai'))      return ['#10B981', '#34D399']
  if (m.includes('gemini') || m.includes('google'))   return ['#3B82F6', '#60A5FA']
  if (m.includes('claude') || m.includes('anthropic')) return ['#F59E0B', '#FCD34D']
  if (m.includes('llama') || m.includes('meta'))      return ['#EF4444', '#F87171']
  if (m.includes('seed') || m.includes('sumopod'))    return ['#8B5CF6', '#A78BFA']
  if (m.includes('deepseek'))                         return ['#EC4899', '#F472B6']
  return ['#6366F1', '#818CF8']
}

function getAgentConfig(type) {
  return AGENT_CONFIG[type] || AGENT_CONFIG.general
}

// ── Glass Card ──────────────────────────────────────────────────
function GlassCard({ children, className, glow }) {
  return (
    <div
      className={clsx('rounded-2xl overflow-hidden', className)}
      style={{
        background: 'rgba(255,255,255,0.04)',
        backdropFilter: 'blur(24px)',
        WebkitBackdropFilter: 'blur(24px)',
        boxShadow: glow
          ? `0 4px 40px ${glow}22`
          : '0 4px 24px rgba(0,0,0,0.06)',
      }}
    >
      {children}
    </div>
  )
}

// ── Active Session Card ─────────────────────────────────────────
function ActiveSessionCard({ session }) {
  const { t } = useTranslation()
  const [c1, c2] = modelColor(session.model_used)
  const modelShort = (session.model_used || '—').split('/').pop()
  const modelFull = session.model_used || '—'
  
  // Extract provider info from model name
  const getModelProvider = (model) => {
    const m = (model || '').toLowerCase()
    if (m.includes('gpt') || m.includes('openai')) return { name: 'OpenAI', icon: '🔷', color: '#10B981' }
    if (m.includes('gemini') || m.includes('google')) return { name: 'Google Gemini', icon: '🔵', color: '#3B82F6' }
    if (m.includes('claude') || m.includes('anthropic')) return { name: 'Anthropic Claude', icon: '🟠', color: '#F59E0B' }
    if (m.includes('llama') || m.includes('meta')) return { name: 'Meta Llama', icon: '🔴', color: '#EF4444' }
    if (m.includes('seed') || m.includes('sumopod')) return { name: 'Sumopod', icon: '🟣', color: '#8B5CF6' }
    if (m.includes('deepseek')) return { name: 'Deepseek', icon: '⭐', color: '#EC4899' }
    return { name: 'AI Model', icon: '🤖', color: '#6366F1' }
  }
  
  const provider = getModelProvider(modelFull)
  const lastActivity = session.last_activity
    ? new Date(session.last_activity).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    : '—'
  const lastActivityFull = session.last_activity
    ? new Date(session.last_activity).toLocaleString('id-ID')
    : '—'

  return (
    <div
      className="relative rounded-2xl p-4 transition-all hover:scale-[1.01] overflow-hidden"
      style={{
        background: `linear-gradient(135deg, ${c1}10, ${c2}08)`,
        border: `1px solid ${c1}30`,
        boxShadow: session.is_streaming ? `0 0 0 2px ${c1}50, 0 8px 24px ${c1}20` : 'none',
      }}
    >
      {/* Streaming pulse ring */}
      {session.is_streaming && (
        <div className="absolute inset-0 rounded-2xl pointer-events-none"
          style={{ boxShadow: `inset 0 0 0 1.5px ${c1}60`, animation: 'pulse 1.5s ease-in-out infinite' }} />
      )}

      {/* Header row */}
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center gap-2 min-w-0">
          {/* Model color dot */}
          <div className="w-2 h-2 rounded-full flex-shrink-0"
            style={{ background: `linear-gradient(135deg, ${c1}, ${c2})`, boxShadow: `0 0 8px ${c1}80` }} />
          <div className="min-w-0">
            <div className="text-base font-bold text-ink truncate uppercase tracking-tight" title={session.title}>
              {session.title || 'New Chat'}
            </div>
            <div className="text-xs text-ink-3 font-bold font-mono truncate uppercase tracking-widest opacity-60">
              #{session.session_id.slice(0, 8)}
            </div>
          </div>
        </div>
        {session.is_streaming ? (
          <span className="flex items-center gap-2 px-3 py-1.5 rounded-full text-[11px] font-bold uppercase tracking-widest flex-shrink-0"
            style={{ background: `${c1}20`, color: c1 }}>
            <span className="w-2 h-2 rounded-full animate-ping" style={{ background: c1 }} />
            {t('processing_label')}
          </span>
        ) : (
          <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-bold uppercase tracking-widest flex-shrink-0"
            style={{ background: 'rgba(16,185,129,0.12)', color: '#10B981' }}>
            <Eye size={12} /> {t('active_label')}
          </span>
        )}
      </div>

      {/* Model detail section */}
      <div className="mb-3 p-2.5 rounded-lg" style={{ background: `${c1}10` }}>
        {/* Model name */}
        <div className="flex items-center gap-2.5 mb-2.5">
          <Bot size={14} style={{ color: c1 }} />
          <span className="text-sm font-bold text-ink truncate uppercase tracking-tight">{modelShort}</span>
          <span className="text-[11px] text-ink-3 font-bold font-mono flex-shrink-0 bg-bg-4 px-2 py-0.5 rounded border border-border/30 shadow-inner">
            {modelFull}
          </span>
        </div>
        
        {/* Provider info */}
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-bg-4 border border-border/20 shadow-inner">
          <span className="text-sm">{provider.icon}</span>
          <span className="text-xs font-bold text-ink-2 uppercase tracking-widest">{provider.name}</span>
          <span className="ml-auto text-[10px] text-ink-3 font-bold uppercase tracking-widest opacity-50">{t('model_provider')}</span>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-3 text-center mb-3">
        <div className="rounded-xl py-2.5 bg-bg-4 border border-border/20 shadow-sm">
          <div className="text-xl font-bold font-mono tracking-tighter" style={{ color: c1 }}>{session.msg_count}</div>
          <div className="text-[10px] text-ink-3 uppercase tracking-widest font-bold opacity-60">{t('messages_label')}</div>
        </div>
        <div className="rounded-xl py-2.5 bg-bg-4 border border-border/20 shadow-sm">
          <div className="text-xl font-bold text-success">✓</div>
          <div className="text-[10px] text-ink-3 uppercase tracking-widest font-bold opacity-60">{t('active_label')}</div>
        </div>
        <div className="rounded-xl py-2.5 bg-bg-4 border border-border/20 shadow-sm">
          <div className="text-base font-bold font-mono text-ink-2" title={lastActivityFull}>{lastActivity.split(':').slice(0,2).join(':')}</div>
          <div className="text-[10px] text-ink-3 uppercase tracking-widest font-bold opacity-60">{t('updated_label')}</div>
        </div>
      </div>

      {/* Orchestrator info  */}
      <div className="px-3 py-2 rounded-xl bg-bg-3 border border-border/40 text-center shadow-md">
        <div className="text-[10px] text-ink-3 uppercase tracking-widest font-bold opacity-60">Orchestrator</div>
        <div className="text-base font-bold text-accent uppercase tracking-tighter mt-0.5">Auto-Orchestrator</div>
      </div>
    </div>
  )
}

// ── Status Badge ────────────────────────────────────────────────
function StatusBadge({ status }) {
  const map = {
    completed:    { color: '#10B981', bg: 'rgba(16,185,129,0.12)',   label: 'Completed' },
    executing:    { color: '#3B82F6', bg: 'rgba(59,130,246,0.12)',   label: 'Executing' },
    failed:       { color: '#EF4444', bg: 'rgba(239,68,68,0.12)',    label: 'Failed' },
    preprocessing:{ color: '#F59E0B', bg: 'rgba(245,158,11,0.12)',   label: 'Preprocessing' },
    decomposing:  { color: '#8B5CF6', bg: 'rgba(139,92,246,0.12)',   label: 'Decomposing' },
    validating:   { color: '#06B6D4', bg: 'rgba(6,182,212,0.12)',    label: 'Validating' },
    aggregating:  { color: '#EC4899', bg: 'rgba(236,72,153,0.12)',   label: 'Aggregating' },
  }
  const cfg = map[status] || map.executing
  return (
    <span className="text-[10px] font-bold px-3 py-1.5 rounded-full uppercase tracking-widest border border-border/30 shadow-sm"
      style={{ background: cfg.bg, color: cfg.color }}>
      {cfg.label}
    </span>
  )
}

// ── Metric Card ─────────────────────────────────────────────────
function MetricCard({ label, value, subtext, icon: Icon, color }) {
  return (
    <GlassCard className="p-6 group hover:scale-[1.02] transition-transform duration-300 shadow-lg">
      <div className="flex items-center justify-between mb-4">
        <span className="text-xs text-ink-3 uppercase tracking-widest font-bold opacity-60">{label}</span>
        <div className="p-2 rounded-xl" style={{ background: color + '18' }}>
          <Icon size={18} style={{ color }} />
        </div>
      </div>
      <div className="text-4xl font-bold text-ink tracking-tighter font-mono">{value}</div>
      {subtext && (
        <div className="flex items-center gap-2 mt-3">
          <TrendingUp size={12} className="text-success" />
          <span className="text-xs text-ink-3 font-bold uppercase tracking-tight opacity-80">{subtext}</span>
        </div>
      )}
    </GlassCard>
  )
}

// ── Main Page ───────────────────────────────────────────────────
export default function MonitoringAI() {
  const { t } = useTranslation()
  const [data, setData]             = useState(null)
  const [activeSessions, setActive] = useState([])
  const [loading, setLoading]       = useState(true)
  const [loadingAS, setLoadingAS]   = useState(true)
  const [error, setError]           = useState(null)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [lastUpdated, setLastUpdated] = useState(null)
  const tickRef = useRef(null)

  const fetchDashboard = async () => {
    try {
      const d = await api.monitoringDashboard()
      setData(d)
      setError(null)
    } catch (e) {
      setError(e.message || t('error_occurred'))
    } finally {
      setLoading(false)
    }
  }

  const fetchActiveSessions = async () => {
    try {
      const r = await api.activeSessions()
      setActive(r.active_sessions || [])
    } catch {
      // silent
    } finally {
      setLoadingAS(false)
    }
  }

  const fetchAll = async () => {
    await Promise.all([fetchDashboard(), fetchActiveSessions()])
    setLastUpdated(new Date())
  }

  useEffect(() => {
    fetchAll()
    if (!autoRefresh) return
    // Sesi aktif refresh lebih cepat (5 detik), dashboard lebih lambat (8 detik)
    const intervalAS   = setInterval(fetchActiveSessions, 5000)
    const intervalDash = setInterval(fetchDashboard, 8000)
    return () => {
      clearInterval(intervalAS)
      clearInterval(intervalDash)
    }
  }, [autoRefresh])

  // Live tick counter
  useEffect(() => {
    if (!autoRefresh) return
    let secs = 0
    tickRef.current = setInterval(() => { secs++ }, 1000)
    return () => clearInterval(tickRef.current)
  }, [autoRefresh])

  if (loading && !data) return (
    <div className="p-8 flex flex-col items-center justify-center min-h-[70vh] gap-8 text-accent">
      <div className="w-24 h-24 border-8 border-t-transparent border-accent rounded-full animate-spin shadow-2xl" />
      <span className="text-lg font-bold uppercase tracking-[0.5em] animate-pulse opacity-80">Loading AI Metrics...</span>
    </div>
  )

  if (error && !data) return (
    <div className="p-8 flex flex-col items-center justify-center min-h-[70vh] gap-5">
      <AlertTriangle size={64} className="text-warn opacity-40 animate-bounce" />
      <span className="text-base text-ink-2 font-bold uppercase tracking-tight">{error}</span>
      <button onClick={() => { setLoading(true); fetchAll() }}
        className="px-8 py-4 bg-accent hover:bg-accent/80 text-white text-sm font-bold uppercase tracking-widest rounded-2xl transition-all shadow-xl shadow-accent/20 active:scale-95">
        {t('retry')}
      </button>
    </div>
  )

  const stats       = data?.stats || {}
  const last24h     = stats.last_24h || {}
  const summaries   = stats.all_time_summaries || []
  const recentExecs = stats.recent_executions || []
  const health      = data?.agent_health || {}
  const recovery    = data?.recovery_stats || {}
  const agents      = data?.registered_agents || []

  const streamingCount = activeSessions.filter(s => s.is_streaming).length

  return (
    <div className="p-3 md:p-4 lg:p-6 lg:pt-4 w-full max-w-full space-y-4 md:space-y-6 relative overflow-hidden">
      {/* Background particles */}
      <div className="fixed inset-0 pointer-events-none opacity-10 z-0">
        {[...Array(20)].map((_, i) => (
          <div key={i} className="absolute rounded-full bg-accent animate-float" style={{
            width: Math.random() * 3 + 'px',
            height: Math.random() * 3 + 'px',
            left: Math.random() * 100 + '%',
            top: Math.random() * 100 + '%',
            animationDelay: Math.random() * 5 + 's',
            animationDuration: (Math.random() * 10 + 10) + 's'
          }} />
        ))}
      </div>

      {/* ── Header ────────────────────────────────────────────── */}
      <div className="flex flex-col xl:flex-row xl:items-end justify-between gap-8 relative z-10">
        <div className="space-y-2">
          <div className="flex items-center gap-3 text-accent">
            <Radio size={24} className="animate-pulse" />
            <span className="text-base font-bold uppercase tracking-[0.6em] opacity-80">Realtime</span>
          </div>
          <h1 className="text-5xl font-bold tracking-tighter text-ink lg:text-7xl bg-clip-text text-transparent bg-gradient-to-r from-ink to-ink-3">
            {t('monitoring_title')}
          </h1>
          <p className="text-lg text-ink-3 max-w-lg font-semibold uppercase tracking-tight opacity-80">
            {t('monitoring_desc')}
          </p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          {lastUpdated && (
            <span className="text-base text-ink-3 font-bold font-mono uppercase tracking-tight opacity-70">
              {t('updated_at')}: {lastUpdated.toLocaleTimeString('id-ID')}
            </span>
          )}
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={clsx(
              'flex items-center gap-3 px-6 py-3.5 rounded-2xl text-base font-bold uppercase tracking-widest transition-all shadow-xl',
              autoRefresh ? 'bg-success/20 text-success border border-success/30' : 'bg-bg-3 text-ink-3 border border-border/40'
            )}
          >
            {autoRefresh ? <Wifi size={20} /> : <WifiOff size={20} />}
            {autoRefresh ? 'Live ON' : 'Live OFF'}
          </button>
          <button onClick={fetchAll}
            className="flex items-center gap-3 px-8 py-3.5 bg-gradient-to-r from-accent to-accent-2 text-white rounded-2xl text-sm font-bold tracking-widest shadow-[0_15px_50px_rgba(var(--accent-rgb),0.5)] active:scale-95 transition-all">
            <RefreshCw size={18} /> {t('refresh')}
          </button>
        </div>
      </div>

      {/* ── Sesi Aktif AI — PANEL UTAMA ──────────────────────── */}
      <div className="relative z-10">
        <div className="flex items-center justify-between gap-3 mb-5 flex-wrap">
          <div className="flex items-center gap-3">
            <MessageSquare size={22} className="text-accent" />
            <h2 className="text-2xl font-bold text-ink uppercase tracking-tighter">📚 {t('active_sessions_title')}</h2>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-widest border border-border/30 shadow-inner"
              style={{ background: 'rgba(99,102,241,0.12)', color: '#6366F1' }}>
              {activeSessions.length} {t('running_label')}
            </div>
            {streamingCount > 0 && (
              <div className="flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-widest animate-pulse border border-success/30 shadow-md"
                style={{ background: 'rgba(16,185,129,0.15)', color: '#10B981' }}>
                <span className="w-2 h-2 rounded-full bg-success animate-ping" />
                {streamingCount} {t('processing_label')}
              </div>
            )}
          </div>
        </div>

        {loadingAS && activeSessions.length === 0 ? (
          <GlassCard className="p-10 flex items-center justify-center shadow-inner">
            <div className="flex items-center gap-4 text-ink-3">
              <RefreshCw size={24} className="animate-spin text-accent" />
              <span className="text-base font-bold uppercase tracking-widest opacity-60">{t('loading_active_sessions')}</span>
            </div>
          </GlassCard>
        ) : activeSessions.length === 0 ? (
          <GlassCard className="p-12 shadow-inner border-dashed border border-border/40 bg-bg-4/20">
            <div className="flex flex-col items-center justify-center gap-5 text-ink-3 py-6">
              <MessageSquare size={56} className="opacity-10" />
              <p className="text-xl font-bold uppercase tracking-tight opacity-40">{t('no_active_sessions')}</p>
              <p className="text-sm text-ink-3 font-semibold uppercase tracking-widest opacity-30 text-center">{t('session_activity_hint')}</p>
            </div>
          </GlassCard>
        ) : (
          <GlassCard className="p-5">
            <div className="space-y-2 max-h-96 overflow-y-auto custom-scrollbar">
              {activeSessions.map(session => (
                <ActiveSessionCardNew key={session.session_id} session={session} />
              ))}
            </div>
          </GlassCard>
        )}
      </div>

      {/* ── Summary Cards ──────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 lg:gap-6 relative z-10">
        <MetricCard label="Tasks (24h)"       value={last24h.total_tasks || 0}
          subtext={`${(last24h.success_rate * 100 || 0).toFixed(0)}% success`} icon={Zap}      color="#3B82F6" />
        <MetricCard label="Confidence"    value={`${((last24h.avg_confidence || 0) * 100).toFixed(0)}%`}
          subtext={t('quality_score')}                                           icon={Shield}    color="#10B981" />
        <MetricCard label="Avg Response"  value={`${Math.round(last24h.avg_time_ms || 0)}ms`}
          subtext={t('latency_label')} icon={Clock}     color="#F59E0B" />
        <MetricCard label="Cost (24h)"  value={`$${(last24h.total_cost || 0).toFixed(4)}`}
          subtext={t('token_spend')}                                               icon={Activity}  color="#8B5CF6" />
      </div>

      {/* ── Main Dashboard Grid: Responsive Layout ──────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 lg:gap-6 relative z-10">

        {/* ── Agent Registry Grid (Responsive Col) ──────────────── */}
        <GlassCard className="p-4 sm:p-5 lg:p-6 flex flex-col">
          <AgentRegistry />
        </GlassCard>

        {/* ── Model Power Distribution (Responsive Col) ─────────────────────── */}
        <GlassCard className="p-4 sm:p-5 lg:p-6 flex flex-col">
          <div className="flex items-center gap-3 mb-5">
            <Zap size={20} className="text-warn" />
            <h2 className="text-xl font-bold text-ink uppercase tracking-tight">{t('model_power')}</h2>
          </div>
          {activeSessions.length === 0 ? (
            <div className="flex items-center justify-center gap-4 text-ink-3 min-h-32 opacity-40">
              <Zap size={28} className="flex-shrink-0" />
              <span className="text-base font-bold uppercase tracking-widest">{t('no_active_sessions')}</span>
            </div>
          ) : (() => {
            const modelPower = {}
            activeSessions.forEach(s => {
              const model = s.model_used || 'Unknown'
              modelPower[model] = (modelPower[model] || 0) + 1
            })
            const totalPower = Object.values(modelPower).reduce((a, b) => a + b, 0)
            const modelEntries = Object.entries(modelPower)
              .map(([model, count]) => ({ model, power: (count / totalPower * 100).toFixed(1) }))
              .sort((a, b) => parseFloat(b.power) - parseFloat(a.power))
            
            return (
              <div className="space-y-2 flex-1">
                {modelEntries.map(({model, power}, i) => {
                  const [c1, c2] = modelColor(model)
                  const modelShort = model.split('/').pop()
                  return (
                    <div key={i} className="space-y-1.5">
                      <div className="flex items-center justify-between text-xs font-bold uppercase tracking-tight">
                        <span className="text-ink truncate max-w-[70%] shadow-sm" title={model}>
                          {modelShort}
                        </span>
                        <span style={{color: c1}} className="font-mono text-sm">{power}%</span>
                      </div>
                      <div className="w-full h-3 rounded-full bg-bg-5 border border-border/20 overflow-hidden shadow-inner">
                        <div 
                          className="h-full transition-all duration-700 relative rounded-full"
                          style={{
                            background: `linear-gradient(90deg, ${c1}, ${c2})`,
                            width: `${power}%`,
                            boxShadow: `0 0 12px ${c1}60`
                          }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            )
          })()}
        </GlassCard>

        {/* ── Model Performance (Live Area Chart - Full Width on Mobile, Spans 1 Col on Desktop) ──────────────── */}
        <GlassCard className="md:col-span-2 lg:col-span-1 p-4 sm:p-5 lg:p-6 flex flex-col">
          <LiveModelPerformanceChart activeSessions={activeSessions} />
        </GlassCard>
      </div>

      {/* ── Model Health (Circuit Breakers) ───────────────────── */}
      {Object.keys(health).length > 0 && (
        <GlassCard className="p-6 sm:p-8 lg:p-10 relative z-10 shadow-2xl">
          <div className="flex items-center gap-3 mb-5 lg:mb-8 border-b border-border/20 pb-4">
            <Shield size={24} className="text-warn" />
            <h2 className="text-2xl font-bold text-ink uppercase tracking-tight">{t('circuit_breakers')}</h2>
            <span className="ml-auto text-sm lg:text-base font-bold text-success uppercase tracking-widest bg-success/10 px-4 py-1 rounded-full border border-success/30 shadow-sm">
              {(recovery.success_rate * 100 || 0).toFixed(0)}% {t('healthy')}
            </span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3 lg:gap-5">
            {Object.entries(health).map(([model, status]) => (
              <div key={model}
                className={clsx('flex items-center gap-3 p-4 lg:p-5 rounded-2xl transition-all border shadow-md group',
                  status.circuit_open ? 'bg-danger/10 border-danger/40 animate-pulse' : 'bg-white/5 border-border/20 hover:border-accent/40')}>
                {status.available
                  ? <CheckCircle size={20} className="text-success flex-shrink-0 group-hover:scale-110 transition-transform" />
                  : <XCircle    size={20} className="text-danger  flex-shrink-0 group-hover:scale-110 transition-transform" />}
                <div className="flex-1 min-w-0">
                  <div className="text-base lg:text-lg font-bold text-ink truncate uppercase tracking-tight">{model.split('/').pop()}</div>
                  <div className="text-xs lg:text-sm text-ink-3 font-bold uppercase tracking-widest opacity-60 flex items-center gap-2">
                    {status.failures} {t('fails')} {status.circuit_open ? <span className="text-danger animate-pulse">{t('open')} ⚠️</span> : <span className="text-success">{t('closed')} ✓</span>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </GlassCard>
      )}

      {/* ── Recent Task Executions ────────────────────────────── */}
      {recentExecs.length > 0 && (
        <GlassCard className="p-6 sm:p-8 lg:p-10 relative z-10 shadow-2xl">
          <div className="flex items-center gap-3 mb-5 lg:mb-8 border-b border-border/20 pb-4">
            <Activity size={24} className="text-accent" />
            <h2 className="text-2xl font-bold text-ink uppercase tracking-tight">{t('recent_orchestrations')}</h2>
            <div className="ml-auto flex items-center gap-3">
              <div className="w-2 h-2 rounded-full bg-success animate-ping" />
              <span className="text-sm font-bold text-success uppercase tracking-[0.2em]">Live Stream</span>
            </div>
          </div>
          <div className="space-y-3 lg:space-y-4">
            {recentExecs.slice(0, 5).map((exec, i) => (
              <div key={i} className="flex items-center gap-4 lg:gap-6 p-4 lg:p-5 rounded-2xl bg-white/5 border border-border/20 hover:bg-white/10 hover:border-accent/40 transition-all group shadow-sm">
                <StatusBadge status={exec.status} />
                <div className="flex-1 min-w-0">
                  <div className="text-base lg:text-lg font-bold text-ink truncate uppercase tracking-tight">{exec.request}</div>
                  <div className="flex items-center gap-4 lg:gap-6 mt-1.5 text-xs text-ink-3 font-bold uppercase tracking-widest opacity-60">
                    <span className="flex items-center gap-2"><Clock size={14} className="text-accent"/> {exec.time_ms}ms</span>
                    <span className="flex items-center gap-2"><Zap size={14} className="text-warn"/> {exec.tokens} TOKENS</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </GlassCard>
      )}

      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes float {
          0%, 100% { transform: translateY(0) translateX(0); opacity: 0.1; }
          50% { transform: translateY(-100px) translateX(20px); opacity: 0.5; }
        }
        .animate-float { animation: float infinite linear; }
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(var(--accent-rgb), 0.2); border-radius: 10px; }
      `}} />
    </div>
  )
}
