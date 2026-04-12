import { useEffect, useState, useRef } from 'react'
import { api } from '../hooks/useApi'
import {
  Activity, Bot, Zap, Cpu, Shield, Clock, ChevronRight,
  CheckCircle, XCircle, AlertTriangle, RefreshCw,
  BrainCircuit, Code2, Search, PenTool, Terminal,
  Palette, ClipboardCheck, MessageSquare, TrendingUp,
  Radio, Layers, Eye, Wifi, WifiOff
} from 'lucide-react'
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
        border: '1px solid rgba(255,255,255,0.08)',
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
            <div className="text-[13px] font-bold text-ink truncate" title={session.title}>
              {session.title || 'New Chat'}
            </div>
            <div className="text-[10px] text-ink-3 font-mono truncate">
              #{session.session_id.slice(0, 8)}
            </div>
          </div>
        </div>
        {session.is_streaming ? (
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-wider flex-shrink-0"
            style={{ background: `${c1}20`, color: c1 }}>
            <span className="w-1.5 h-1.5 rounded-full animate-ping" style={{ background: c1 }} />
            Memproses
          </span>
        ) : (
          <span className="flex items-center gap-1 px-2 py-1 rounded-full text-[10px] font-bold uppercase flex-shrink-0"
            style={{ background: 'rgba(16,185,129,0.12)', color: '#10B981' }}>
            <Eye size={9} /> Aktif
          </span>
        )}
      </div>

      {/* Model detail section */}
      <div className="mb-3 p-2.5 rounded-lg" style={{ background: `${c1}10`, border: `0.5px solid ${c1}20` }}>
        {/* Model name */}
        <div className="flex items-center gap-2 mb-2">
          <Bot size={11} style={{ color: c1 }} />
          <span className="text-[10px] font-semibold text-ink truncate">{modelShort}</span>
          <span className="text-[8px] text-ink-3 font-mono flex-shrink-0 bg-bg-4 px-1.5 py-0.5 rounded">
            {modelFull}
          </span>
        </div>
        
        {/* Provider info */}
        <div className="flex items-center gap-1.5 px-2 py-1.5 rounded bg-bg-4/50 border border-border/40">
          <span>{provider.icon}</span>
          <span className="text-[9px] font-medium text-ink-2">{provider.name}</span>
          <span className="ml-auto text-[8px] text-ink-3">Provider</span>
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-2 text-center mb-2">
        <div className="rounded-lg py-1.5" style={{ background: 'rgba(255,255,255,0.04)' }}>
          <div className="text-[15px] font-black" style={{ color: c1 }}>{session.msg_count}</div>
          <div className="text-[9px] text-ink-3 uppercase tracking-wider">Pesan</div>
        </div>
        <div className="rounded-lg py-1.5" style={{ background: 'rgba(255,255,255,0.04)' }}>
          <div className="text-[13px] font-black text-success">✓</div>
          <div className="text-[9px] text-ink-3 uppercase tracking-wider">Aktif</div>
        </div>
        <div className="rounded-lg py-1.5" style={{ background: 'rgba(255,255,255,0.04)' }}>
          <div className="text-[11px] font-bold text-ink-2" title={lastActivityFull}>{lastActivity}</div>
          <div className="text-[9px] text-ink-3 uppercase tracking-wider">Update</div>
        </div>
      </div>

      {/* Orchestrator info  */}
      <div className="px-2 py-1.5 rounded bg-bg-3/70 border border-border/30 text-center">
        <div className="text-[8px] text-ink-3 uppercase tracking-wider font-semibold">Orchestrator</div>
        <div className="text-[10px] font-bold text-accent mt-0.5">Auto-Orchestrator</div>
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
    <span className="text-[10px] font-bold px-2.5 py-1 rounded-full uppercase tracking-wider"
      style={{ background: cfg.bg, color: cfg.color }}>
      {cfg.label}
    </span>
  )
}

// ── Metric Card ─────────────────────────────────────────────────
function MetricCard({ label, value, subtext, icon: Icon, color }) {
  return (
    <GlassCard className="p-5 group hover:scale-[1.02] transition-transform duration-300">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[10px] text-ink-3 uppercase tracking-[0.1em] font-semibold">{label}</span>
        <div className="p-1.5 rounded-lg" style={{ background: color + '18' }}>
          <Icon size={14} style={{ color }} />
        </div>
      </div>
      <div className="text-3xl font-black text-ink tracking-tight">{value}</div>
      {subtext && (
        <div className="flex items-center gap-1.5 mt-2">
          <TrendingUp size={10} className="text-success" />
          <span className="text-[9px] text-ink-3 font-medium">{subtext}</span>
        </div>
      )}
    </GlassCard>
  )
}

// ── Main Page ───────────────────────────────────────────────────
export default function MonitoringAI() {
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
      setError(e.message || 'Gagal memuat data monitoring')
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
    <div className="p-8 flex flex-col items-center justify-center min-h-[70vh] gap-6 text-accent">
      <div className="w-20 h-20 border-4 border-t-transparent border-accent rounded-full animate-spin" />
      <span className="text-sm font-black uppercase tracking-[0.4em] animate-pulse">Loading AI Metrics...</span>
    </div>
  )

  if (error && !data) return (
    <div className="p-8 flex flex-col items-center justify-center min-h-[70vh] gap-4">
      <AlertTriangle size={48} className="text-warn opacity-60" />
      <span className="text-sm text-ink-2 font-medium">{error}</span>
      <button onClick={() => { setLoading(true); fetchAll() }}
        className="px-5 py-2.5 bg-accent hover:bg-accent/80 text-white text-xs font-bold rounded-xl transition-colors">
        Coba Lagi
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
    <div className="p-3 md:p-6 lg:p-8 w-full max-w-full space-y-4 md:space-y-6 lg:space-y-8 relative overflow-hidden">
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
            <Radio size={22} className="animate-pulse" />
            <span className="text-xs font-black uppercase tracking-[0.5em] opacity-70">Realtime</span>
          </div>
          <h1 className="text-5xl font-black tracking-tighter text-ink lg:text-7xl bg-clip-text text-transparent bg-gradient-to-r from-ink to-ink-3">
            Monitoring AI
          </h1>
          <p className="text-sm text-ink-3 max-w-lg">
            Pantau kinerja AI secara realtime — model aktif, sesi berjalan, dan metrik performa orchestrator.
          </p>
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          {lastUpdated && (
            <span className="text-[10px] text-ink-3 font-mono">
              Diperbarui: {lastUpdated.toLocaleTimeString('id-ID')}
            </span>
          )}
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={clsx(
              'flex items-center gap-2 px-4 py-3 rounded-2xl text-xs font-bold transition-all shadow-lg',
              autoRefresh ? 'bg-success/20 text-success' : 'bg-bg-3 text-ink-3'
            )}
          >
            {autoRefresh ? <Wifi size={14} /> : <WifiOff size={14} />}
            {autoRefresh ? 'Live ON' : 'Live OFF'}
          </button>
          <button onClick={fetchAll}
            className="flex items-center gap-2 px-5 py-3 bg-gradient-to-r from-accent to-accent-2 text-white rounded-2xl text-xs font-black shadow-[0_10px_40px_rgba(var(--accent-rgb),0.4)] active:scale-95 transition-all">
            <RefreshCw size={14} /> REFRESH
          </button>
        </div>
      </div>

      {/* ── Sesi Aktif AI — PANEL UTAMA ──────────────────────── */}
      <div className="relative z-10">
        <div className="flex items-center justify-between gap-3 mb-5 flex-wrap">
          <div className="flex items-center gap-2">
            <MessageSquare size={18} className="text-accent" />
            <h2 className="text-xl font-black text-ink tracking-tight">📚 Sesi Aktif AI</h2>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-black uppercase"
              style={{ background: 'rgba(99,102,241,0.12)', color: '#6366F1' }}>
              {activeSessions.length} Running
            </div>
            {streamingCount > 0 && (
              <div className="flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-black uppercase animate-pulse"
                style={{ background: 'rgba(16,185,129,0.15)', color: '#10B981' }}>
                <span className="w-1.5 h-1.5 rounded-full bg-success animate-ping" />
                {streamingCount} Processing
              </div>
            )}
          </div>
        </div>

        {loadingAS && activeSessions.length === 0 ? (
          <GlassCard className="p-8 flex items-center justify-center">
            <div className="flex items-center gap-3 text-ink-3">
              <RefreshCw size={16} className="animate-spin" />
              <span className="text-sm">Memuat sesi aktif...</span>
            </div>
          </GlassCard>
        ) : activeSessions.length === 0 ? (
          <GlassCard className="p-8">
            <div className="flex flex-col items-center justify-center gap-3 text-ink-3 py-4">
              <MessageSquare size={40} className="opacity-20" />
              <p className="text-sm font-medium">Tidak ada sesi aktif saat ini</p>
              <p className="text-[11px] text-ink-3">Sesi dengan aktivitas dalam 30 menit terakhir akan muncul di sini</p>
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
          subtext="Quality score"                                           icon={Shield}    color="#10B981" />
        <MetricCard label="Avg Response"  value={`${Math.round(last24h.avg_time_ms || 0)}ms`}
          subtext="Latency" icon={Clock}     color="#F59E0B" />
        <MetricCard label="Cost (24h)"  value={`$${(last24h.total_cost || 0).toFixed(4)}`}
          subtext="Token spend"                                               icon={Activity}  color="#8B5CF6" />
      </div>

      {/* ── Main Dashboard Grid: Responsive Layout ──────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 lg:gap-6 relative z-10">

        {/* ── Agent Registry Grid (Responsive Col) ──────────────── */}
        <GlassCard className="p-4 sm:p-5 lg:p-6 flex flex-col">
          <AgentRegistry />
        </GlassCard>

        {/* ── Model Power Distribution (Responsive Col) ─────────────────────── */}
        <GlassCard className="p-4 sm:p-5 lg:p-6 flex flex-col">
          <div className="flex items-center gap-2 mb-3 lg:mb-5">
            <Zap size={16} className="text-warn" />
            <h2 className="text-base lg:text-lg font-black text-ink tracking-tight">Model Power</h2>
          </div>
          {activeSessions.length === 0 ? (
            <div className="flex items-center justify-center gap-2 text-ink-3 min-h-32">
              <Zap size={20} className="opacity-30 flex-shrink-0" />
              <span className="text-xs lg:text-sm">No active sessions</span>
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
                    <div key={i} className="space-y-0.5">
                      <div className="flex items-center justify-between text-[10px] lg:text-[11px]">
                        <span className="font-semibold text-ink truncate" title={model}>
                          {modelShort}
                        </span>
                        <span className="font-bold" style={{color: c1}}>{power}%</span>
                      </div>
                      <div className="w-full h-2 rounded-full bg-bg-4/50 overflow-hidden">
                        <div 
                          className="h-full transition-all duration-500 relative"
                          style={{
                            background: `linear-gradient(90deg, ${c1}, ${c2})`,
                            width: `${power}%`,
                            boxShadow: `0 0 8px ${c1}80`
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
        <GlassCard className="p-4 sm:p-5 lg:p-6 relative z-10">
          <div className="flex items-center gap-2 mb-3 lg:mb-5">
            <Shield size={16} className="text-warn" />
            <h2 className="text-base lg:text-lg font-black text-ink tracking-tight">Circuit Breakers</h2>
            <span className="ml-auto text-[9px] lg:text-[10px] font-bold text-ink-3">
              {(recovery.success_rate * 100 || 0).toFixed(0)}% OK
            </span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-2 lg:gap-4">
            {Object.entries(health).map(([model, status]) => (
              <div key={model}
                className={clsx('flex items-center gap-2 p-2 lg:p-3 rounded-lg transition-all text-xs',
                  status.circuit_open ? 'bg-danger/10 border border-danger/20' : 'bg-white/3')}>
                {status.available
                  ? <CheckCircle size={14} className="text-success flex-shrink-0" />
                  : <XCircle    size={14} className="text-danger  flex-shrink-0" />}
                <div className="flex-1 min-w-0">
                  <div className="text-[11px] lg:text-[12px] font-semibold text-ink truncate">{model.split('/').pop()}</div>
                  <div className="text-[9px] lg:text-[10px] text-ink-3">
                    {status.failures} {status.circuit_open ? '⚠️' : '✓'}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </GlassCard>
      )}

      {/* ── Recent Task Executions ────────────────────────────── */}
      {recentExecs.length > 0 && (
        <GlassCard className="p-4 sm:p-5 lg:p-6 relative z-10">
          <div className="flex items-center gap-2 mb-3 lg:mb-5">
            <Activity size={16} className="text-accent" />
            <h2 className="text-base lg:text-lg font-black text-ink tracking-tight">Recent Orchestrations</h2>
            <div className="ml-auto flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-success animate-ping" />
              <span className="text-[8px] lg:text-[10px] font-black text-success uppercase tracking-widest">Live</span>
            </div>
          </div>
          <div className="space-y-2 lg:space-y-3">
            {recentExecs.slice(0, 5).map((exec, i) => (
              <div key={i} className="flex items-center gap-2 lg:gap-4 p-2 lg:p-4 rounded-lg bg-white/3 hover:bg-white/5 transition-all group text-xs">
                <StatusBadge status={exec.status} />
                <div className="flex-1 min-w-0">
                  <div className="text-[11px] lg:text-[13px] font-medium text-ink truncate">{exec.request}</div>
                  <div className="flex items-center gap-2 lg:gap-3 mt-0.5 text-[9px] lg:text-[10px] text-ink-3 truncate">
                    <span>⏱ {exec.time_ms}ms</span>
                    <span>• 🎟 {exec.tokens}</span>
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
