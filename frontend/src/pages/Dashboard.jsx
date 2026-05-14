import { useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../hooks/useApi'
import { 
  MessageSquare, 
  Activity, 
  BookOpen, 
  Repeat2, 
  Download, 
  Calendar, 
  TrendingUp, 
  Bot, 
  Zap,
  LayoutDashboard,
  Clock,
  AlertCircle,
  ChevronRight,
  Sparkles,
  Cpu,
  BrainCircuit,
  Command,
  CloudLightning,
  Atom
} from 'lucide-react'
import clsx from 'clsx'
import { useTranslation } from 'react-i18next'

// ── Sparkline Components (unique per card) ──────────────────

// Card 1: Smooth wave
function WaveSparkline() {
  return (
    <svg className="w-full h-full" viewBox="0 0 200 80" preserveAspectRatio="none" fill="none">
      <path
        d="M0 60 C 15 40, 30 65, 50 35 S 80 55, 100 30 S 130 50, 155 22 S 180 40, 200 18"
        stroke="#3B82F6" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
        fill="none" opacity="0.2"
        className="spark-wave"
      />
    </svg>
  )
}

// Card 2: Heartbeat / EKG
function HeartbeatSparkline() {
  return (
    <svg className="w-full h-full" viewBox="0 0 200 80" preserveAspectRatio="none" fill="none">
      <path
        d="M0 45 L 30 45 L 38 20 L 48 70 L 56 45 L 90 45 L 98 10 L 108 72 L 116 45 L 150 45 L 158 25 L 168 60 L 176 45 L 200 45"
        stroke="#10B981" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
        fill="none" opacity="0.2"
        className="spark-heartbeat"
      />
    </svg>
  )
}

// Card 3: Vector Search visualization
function VectorSearchSparkline() {
  const center = { cx: 75, cy: 40 }
  const docs = [
    { x: 18,  y: 8  },
    { x: 132, y: 5  },
    { x: 142, y: 52 },
    { x: 10,  y: 60 },
    { x: 80,  y: 72 },
  ]
  return (
    <svg className="w-full h-full" viewBox="0 0 160 85" preserveAspectRatio="xMidYMid meet" fill="none">
      {/* Lines from center to docs */}
      {docs.map((d, i) => (
        <line
          key={`vl${i}`}
          x1={center.cx} y1={center.cy}
          x2={d.x + 4} y2={d.y + 5}
          stroke="#F59E0B" strokeWidth="1" opacity="0.15"
          className="vs-line"
          style={{ animationDelay: `${0.4 + i * 0.1}s` }}
        />
      ))}
      {/* Document icons */}
      {docs.map((d, i) => (
        <rect
          key={`vd${i}`}
          x={d.x} y={d.y} width="8" height="10" rx="1.5"
          fill="#F59E0B" opacity="0.22"
          className="vs-doc"
          style={{ animationDelay: `${0.7 + i * 0.12}s` }}
        />
      ))}
      {/* Center node — outer glow */}
      <circle cx={center.cx} cy={center.cy} r="7" fill="#F59E0B" opacity="0.15" className="vs-center" />
      {/* Center node — inner dot */}
      <circle cx={center.cx} cy={center.cy} r="3.5" fill="#F59E0B" opacity="0.35" className="vs-center" />
    </svg>
  )
}

// Card 4: Node network graph
function NodeNetworkSparkline() {
  const nodes = [
    { cx: 30,  cy: 55 },
    { cx: 70,  cy: 22 },
    { cx: 120, cy: 50 },
    { cx: 155, cy: 18 },
    { cx: 90,  cy: 68 },
    { cx: 175, cy: 55 },
  ]
  const edges = [
    [0,1],[1,2],[2,3],[0,4],[4,2],[3,5],[2,5],[1,4],
  ]
  return (
    <svg className="w-full h-full" viewBox="0 0 200 80" preserveAspectRatio="none" fill="none">
      {edges.map(([a,b], i) => (
        <line
          key={`e${i}`}
          x1={nodes[a].cx} y1={nodes[a].cy}
          x2={nodes[b].cx} y2={nodes[b].cy}
          stroke="#7C3AED" strokeWidth="1" opacity="0.15"
          className="spark-edge"
          style={{ animationDelay: `${0.6 + i * 0.08}s` }}
        />
      ))}
      {nodes.map((n, i) => (
        <circle
          key={`n${i}`}
          cx={n.cx} cy={n.cy} r="3"
          fill="#7C3AED" opacity="0.3"
          className="spark-node"
          style={{ animationDelay: `${0.3 + i * 0.12}s` }}
        />
      ))}
    </svg>
  )
}

// ── Components ─────────────────────────────────────────────────

function Card({ children, className, sparkline }) {
  return (
    <div className={clsx("bg-bg-3 rounded-2xl shadow-2xl overflow-hidden backdrop-blur-3xl relative group/card", className)}>
      {/* Sparkline layer — behind content */}
      {sparkline && (
        <div className="absolute bottom-0 right-0 w-[65%] h-[65%] pointer-events-none z-0">
          {sparkline}
        </div>
      )}
      <div className="relative z-[1] h-full">{children}</div>
    </div>
  )
}

// ── Gauge Configuration ───────────────────────────────────────
const GAUGE_CONFIG = {
  cpu:  { label: 'CPU',  colors: ['#60A5FA', '#3B82F6'], glow: 'rgba(96,165,250,0.35)',  shadow: '0 0 20px rgba(96,165,250,0.25)'  },
  ram:  { label: 'RAM',  colors: ['#34D399', '#10B981'], glow: 'rgba(52,211,153,0.35)',  shadow: '0 0 20px rgba(52,211,153,0.25)'  },
  disk: { label: 'DISK', colors: ['#A78BFA', '#7C3AED'], glow: 'rgba(167,139,250,0.35)', shadow: '0 0 20px rgba(167,139,250,0.25)' },
  swap: { label: 'SWAP', colors: ['#FCD34D', '#F59E0B'], glow: 'rgba(252,211,77,0.35)',  shadow: '0 0 20px rgba(252,211,77,0.25)'  },
  gpu:  { label: 'GPU',  colors: ['#FB7185', '#EF4444'], glow: 'rgba(251,113,133,0.35)', shadow: '0 0 20px rgba(251,113,133,0.25)' },
}

function GlassGauge({ metricKey, percent, subtext }) {
  const cfg = GAUGE_CONFIG[metricKey]
  const radius = 38
  const stroke = 7
  const circumference = 2 * Math.PI * radius
  const gradId = `gauge-grad-${metricKey}`
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    // Trigger animation from 0 → value after mount
    const raf = requestAnimationFrame(() => setMounted(true))
    return () => cancelAnimationFrame(raf)
  }, [])

  const animatedOffset = mounted
    ? circumference - (percent / 100) * circumference
    : circumference // fully hidden before mount

  return (
    <div
      className="flex flex-col items-center gap-3 group/gauge"
      style={{ flex: '1 1 0', minWidth: 0 }}
    >
      {/* Glass Card */}
      <div
        className="relative rounded-2xl p-4 flex flex-col items-center transition-all duration-300 group-hover/gauge:scale-[1.04]"
        style={{
          background: 'rgba(255,255,255,0.06)',
          backdropFilter: 'blur(16px)',
          WebkitBackdropFilter: 'blur(16px)',
          boxShadow: `0 4px 24px rgba(0,0,0,0.06)`,
        }}
        onMouseEnter={e => { e.currentTarget.style.boxShadow = `0 8px 32px rgba(0,0,0,0.12), ${cfg.shadow}` }}
        onMouseLeave={e => { e.currentTarget.style.boxShadow = `0 4px 24px rgba(0,0,0,0.06)` }}
      >
        {/* SVG Gauge */}
        <div className="relative w-24 h-24 md:w-28 md:h-28">
          {/* Subtle glow behind ring */}
          <div
            className="absolute inset-3 rounded-full blur-xl opacity-0 group-hover/gauge:opacity-100 transition-opacity duration-500"
            style={{ background: cfg.glow }}
          />

          <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
            <defs>
              <linearGradient id={gradId} x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor={cfg.colors[0]} />
                <stop offset="100%" stopColor={cfg.colors[1]} />
              </linearGradient>
            </defs>

            {/* Track */}
            <circle
              cx="50" cy="50" r={radius}
              fill="none"
              stroke="rgba(255,255,255,0.06)"
              strokeWidth={stroke}
            />

            {/* Fill */}
            <circle
              cx="50" cy="50" r={radius}
              fill="none"
              stroke={`url(#${gradId})`}
              strokeWidth={stroke}
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={animatedOffset}
              style={{
                transition: 'stroke-dashoffset 1s cubic-bezier(0.22, 1, 0.36, 1)',
                filter: `drop-shadow(0 0 4px ${cfg.colors[1]})`,
              }}
            />
          </svg>

          {/* Center Text */}
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span
              className="text-xl md:text-2xl font-semibold tracking-tight leading-none"
              style={{ color: cfg.colors[0] }}
            >
              {Math.round(percent)}%
            </span>
          </div>
        </div>

        {/* Labels */}
        <div className="text-center mt-3 space-y-1">
          <div className="text-[10px] font-bold text-ink-2 uppercase tracking-widest opacity-60">
            {cfg.label}
          </div>
          <div className="text-xs text-ink-3 opacity-80 truncate max-w-[120px] font-bold uppercase tracking-tight">
            {subtext}
          </div>
        </div>
      </div>
    </div>
  )
}

function ModelIcon({ name = '' }) {
  const n = name.toLowerCase()
  let Icon = Bot
  let grad = "from-blue-600 to-cyan-400"
  
  if (n.includes('gpt')) { Icon = Sparkles; grad = "from-emerald-600 to-teal-400" }
  else if (n.includes('claude') || n.includes('anthropic')) { Icon = Zap; grad = "from-orange-600 to-amber-400" }
  else if (n.includes('llama') || n.includes('meta')) { Icon = BrainCircuit; grad = "from-purple-600 to-indigo-400" }
  else if (n.includes('gemini') || n.includes('google')) { Icon = CloudLightning; grad = "from-blue-600 to-indigo-400" }
  else if (n.includes('deepseek') || n.includes('r1')) { Icon = Atom; grad = "from-rose-600 to-pink-400" }
  else if (n.includes('seed') || n.includes('sumo')) { Icon = Cpu; grad = "from-cyan-600 to-blue-400" }
  else if (n.includes('auto')) { Icon = Command; grad = "from-slate-600 to-slate-400" }

  return (
    <div className="relative shrink-0 group/icon">
      <div className={clsx("absolute inset-0 bg-gradient-to-br rounded-xl blur-md opacity-30 group-hover/icon:opacity-60 transition-opacity", grad)} />
      <div className={clsx("w-10 h-10 rounded-xl flex items-center justify-center bg-bg-4 relative z-10 overflow-hidden shadow-inner border-0")}>
        <div className={clsx("absolute inset-0 bg-gradient-to-br opacity-20", grad)} />
        <Icon size={18} className={clsx("relative z-10 transition-transform group-hover/icon:scale-110", grad.split(' ')[0].replace('from-', 'text-'))} />
      </div>
    </div>
  )
}

function StatCard({ label, value, subtext, icon: Icon, colorClass, glowClass, sparkline, accentColor }) {
  return (
    <Card
      className={clsx("p-6 transition-all duration-500 group", glowClass)}
      sparkline={sparkline || null}
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          {accentColor && (
            <span
              className="w-2 h-2 rounded-full flex-shrink-0"
              style={{ background: accentColor }}
            />
          )}
          <h3 className="text-xs font-bold text-ink-3 uppercase tracking-widest opacity-60">{label}</h3>
        </div>
        <div className={clsx("p-2.5 rounded-xl bg-opacity-10", colorClass, colorClass.replace('bg-', 'text-'))}>
          <Icon size={20} />
        </div>
      </div>
      
      <div className="text-5xl font-bold text-ink tracking-tighter font-mono">{value}</div>
      <div className="flex items-center gap-2 mt-4">
        <TrendingUp size={14} className="text-success" />
        <p className="text-xs font-bold text-ink-3 tracking-widest uppercase opacity-60">{subtext}</p>
      </div>
    </Card>
  )
}

function ScanningLine() {
  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden z-20">
      <div className="absolute left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-accent to-transparent opacity-40 animate-scan" />
    </div>
  )
}

function OverviewChart({ data, metric }) {
  if (!data || data.length === 0) return (
    <div className="h-[180px] flex flex-col items-center justify-center gap-2 text-ink-3">
      <Clock size={20} className="opacity-30" />
      <span className="text-sm font-semibold">{t('no_data_available')}</span>
      <span className="text-xs opacity-60 font-medium">{t('no_messages')}</span>
    </div>
  )
  
  const getVal = (d) => {
    if (metric === 'Pesan') return d.messages
    if (metric === 'Token') return d.tokens
    if (metric === 'Latensi') return 30 + (d.messages % 20) // Simulated
    return 0.1 // Error
  }

  const maxVal = Math.max(...data.map(d => getVal(d)), 1)
  const colors = ["bg-gradient-to-t from-blue-600 to-blue-400", "bg-gradient-to-t from-emerald-600 to-emerald-400", "bg-gradient-to-t from-purple-600 to-purple-400", "bg-gradient-to-t from-orange-600 to-orange-400"]

  return (
    <div className="relative h-[180px] w-full mt-6 px-2">
      <ScanningLine />
      <div className="flex items-end justify-between gap-3 md:gap-6 h-full">
        {data.map((item, i) => {
          const val = getVal(item)
          return (
            <div key={i} className="flex flex-col items-center flex-1 h-full relative group">
              <div className="absolute -top-12 px-3 py-1.5 bg-bg/90 rounded-xl shadow-2xl text-xs font-bold text-ink opacity-0 group-hover:opacity-100 transition-all transform group-hover:-translate-y-2 z-30 backdrop-blur-md">
                {val.toLocaleString()} {metric}
              </div>
              
              <div className="w-full bg-ink/5 rounded-t-2xl relative overflow-hidden h-full">
                <div 
                  className={clsx("absolute bottom-0 w-full transition-all duration-1000 ease-in-out rounded-t-xl group-hover:brightness-125", colors[i % colors.length])}
                  style={{ height: `${(val / maxVal) * 100}%`, minHeight: '6px' }}
                />
              </div>
              <div className="text-xs font-bold text-ink-3 mt-4 uppercase tracking-widest opacity-60 group-hover:opacity-100">
                {item.label}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function SystemMonitor({ system }) {
  if (!system) return null
  const gpu = system.gpu && system.gpu.length > 0 ? system.gpu[0] : null
  
  return (
    <div
      className="rounded-2xl p-6 md:p-8 h-[320px] flex flex-col"
      style={{
        background: 'rgba(255,255,255,0.03)',
        backdropFilter: 'blur(24px)',
        WebkitBackdropFilter: 'blur(24px)',
        boxShadow: '0 4px 24px rgba(0,0,0,0.06)',
      }}
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <Cpu size={18} className="text-accent-2" />
        <span className="text-xs font-bold text-ink-2 uppercase tracking-widest opacity-60">System Resources</span>
        <div className="ml-auto flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-success animate-pulse shadow-lg" />
          <span className="text-[10px] font-bold text-success uppercase tracking-widest border border-success/30 px-2 py-0.5 rounded-full bg-success/10">Live</span>
        </div>
      </div>

      {/* Gauges Row */}
      <div className="flex items-center justify-between gap-2 md:gap-4 flex-1">
        <GlassGauge metricKey="cpu"  percent={system.cpu.percent}    subtext="8-CORE TURBO" />
        <GlassGauge metricKey="ram"  percent={system.memory.percent} subtext={`${system.memory.used_mb}MB / 16GB`} />
        <GlassGauge metricKey="disk" percent={system.disk.percent}   subtext={`${system.disk.used_gb}GB / 512GB`} />
        <GlassGauge metricKey="swap" percent={system.swap.percent}   subtext="ZRAM OPTIMIZING" />
        <GlassGauge metricKey="gpu"  percent={gpu ? gpu.util_pct : 0} subtext={gpu ? `${gpu.temp_c}°C ACTIVE` : 'INACTIVE'} />
      </div>
    </div>
  )
}

// ── Main Page ──────────────────────────────────────────────────

export default function Dashboard() {
  const { t } = useTranslation()
  const [data, setData] = useState(null)
  const [system, setSystem] = useState(null)
  const [savedModels, setSavedModels] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [metric, setMetric] = useState('Pesan')
  const navigate = useNavigate()
  const scrollRef = useRef(null)
  const [cpuHistory, setCpuHistory] = useState(Array(20).fill(0))

  useEffect(() => {
    const fetchDashboard = () => {
      api.dashboard()
        .then(d => { setData(d); setError(null) })
        .catch(e => { console.error(e); setError(e.message || t('error_occurred')) })
        .finally(() => setLoading(false))
    }
    fetchDashboard()
    const int = setInterval(fetchDashboard, 10000)
    return () => clearInterval(int)
  }, [])

  // Load saved models from integrations
  useEffect(() => {
    api.listSavedModels?.()
      .then(r => setSavedModels(r.models || []))
      .catch(() => setSavedModels([]))
  }, [])

  useEffect(() => {
    const fetchSys = async () => {
      try {
        const s = await api.systemStats()
        if (s) {
          setSystem(s)
          setCpuHistory(prev => [...prev.slice(1), s.cpu.percent])
        }
      } catch(e) {}
    }
    fetchSys()
    const int = setInterval(fetchSys, 3000)
    return () => clearInterval(int)
  }, [])

  const downloadReport = () => {
    if (!data) return
    const csv = "Model,Requests,Tokens,Latency,ErrorRate\n" + 
      data.usage.map(u => `${u.model},${u.count},${u.tokens},${u.latency}ms,${u.error_rate}%`).join("\n")
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `ai-orchestrator-report-${new Date().toISOString().split('T')[0]}.csv`
    a.click()
  }

  if (loading) return (
    <div className="p-8 flex flex-col items-center justify-center min-h-[70vh] gap-6 text-accent">
      <div className="w-20 h-20 border-4 border-t-transparent border-accent rounded-full animate-spin" />
      <span className="text-sm font-bold uppercase tracking-[0.4em] animate-pulse">Synchronizing Grid...</span>
    </div>
  )

  // Error state with retry
  if (error && !data) return (
    <div className="p-8 flex flex-col items-center justify-center min-h-[70vh] gap-4">
      <AlertCircle size={48} className="text-danger opacity-60" />
      <span className="text-sm text-ink-2 font-medium">{error}</span>
      <button
        onClick={() => { setLoading(true); setError(null); api.dashboard().then(d => { setData(d); setError(null) }).catch(e => setError(e.message)).finally(() => setLoading(false)) }}
        className="px-5 py-2.5 bg-accent hover:bg-accent/80 text-white text-xs font-semibold rounded-xl transition-colors"
      >
        {t('refresh')}
      </button>
    </div>
  )

  const stats = data?.stats || {}
  const timeline = data?.timeline || []
  const logs = data?.logs || []

  // ── Bug Fix: Only show models that are SAVED in integrations ──
  // Filter usage data to only include models saved in .env or .custom_models.json
  const rawUsage = data?.usage || []
  const activeModels = data?.models || []
  const usageMap = new Map(rawUsage.map(u => [u.model, u]))
  
  // Create a set of saved model IDs for quick lookup
  const savedModelIds = new Set(savedModels.map(m => m.id))
  
  // Merge active models that have no usage yet, but ONLY if they're saved
  for (const m of activeModels) {
    if (!usageMap.has(m.id) && savedModelIds.has(m.id)) {
      usageMap.set(m.id, {
        model: m.id,
        count: 0,
        tokens: 0,
        latency: 0,
        error_rate: 0,
      })
    }
  }
  
  // Filter to only include saved models
  const usage = Array.from(usageMap.values()).filter(u => savedModelIds.has(u.model))

  const chartData = timeline.map(t => ({
    label: t.day.split('-').slice(1).join('/'),
    messages: t.messages,
    tokens: t.tokens
  }))

  return (
    <div className="p-4 md:p-6 md:pt-4 w-full max-w-full space-y-6 relative overflow-hidden">
      
      {/* Background Particles (VFX) */}
      <div className="fixed inset-0 pointer-events-none opacity-20 z-0">
        {[...Array(30)].map((_, i) => (
          <div key={i} className="absolute rounded-full bg-white animate-float" style={{
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
        <div className="space-y-3">
          <div className="flex items-center gap-3 text-accent transition-all hover:translate-x-1">
            <Bot size={28} className="animate-bounce" />
            <span className="text-xs font-bold uppercase tracking-[0.6em] opacity-60">AI Orchestrator Platform</span>
          </div>
          <h1 className="text-6xl font-bold tracking-tighter text-ink lg:text-8xl bg-clip-text text-transparent bg-gradient-to-r from-ink via-ink-2 to-ink-3 uppercase">Dashboard</h1>
        </div>
        <div className="flex items-center gap-4">
          <button className="flex items-center gap-3 px-6 py-4 bg-bg-3 border border-border rounded-2xl text-sm font-bold text-ink hover:bg-bg-4 transition-all shadow-xl backdrop-blur-md uppercase tracking-widest">
            <Calendar size={18} className="text-accent" /> Mar 20, 2026 - Mar 28, 2026
          </button>
          <button onClick={downloadReport} className="flex items-center gap-3 px-8 py-4 bg-gradient-to-r from-accent to-accent-2 text-white rounded-2xl text-sm font-bold shadow-[0_10px_40px_rgba(var(--accent-rgb),0.4)] active:scale-95 transition-all uppercase tracking-widest">
            <Download size={18} /> {t('download_report') || 'DOWNLOAD REPORT'}
          </button>
        </div>
      </div>

      {/* ── StatCards Row ──────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8 relative z-10">
        <StatCard label={t('total_messages')} value={(stats.total_messages ?? 0).toLocaleString()} subtext={t('avg_latency_desc') || "+24.1% average"} icon={MessageSquare} colorClass="bg-blue-600" glowClass="hover:shadow-blue-500/20" sparkline={<WaveSparkline/>} accentColor="#3B82F6" />
        <StatCard label={t('active_sessions')} value={(stats.total_sessions ?? 0).toLocaleString()} subtext={t('new_sessions_desc') || "+102 new sessions"} icon={Zap} colorClass="bg-emerald-600" glowClass="hover:shadow-emerald-500/20" sparkline={<HeartbeatSparkline/>} accentColor="#10B981" />
        <StatCard label={t('knowledge_capacity')} value={(stats.total_docs ?? 0).toLocaleString()} subtext={t('docs_uploaded_desc') || "+12 files uploaded"} icon={BookOpen} colorClass="bg-orange-600" glowClass="hover:shadow-orange-500/20" sparkline={<VectorSearchSparkline/>} accentColor="#F59E0B" />
        <StatCard label={t('workflow_runs')} value={(stats.workflow_runs ?? 0).toLocaleString()} subtext={t('exec_hours_desc') || "+1.2k hours exec"} icon={Repeat2} colorClass="bg-purple-600" glowClass="hover:shadow-purple-500/20" sparkline={<NodeNetworkSparkline/>} accentColor="#7C3AED" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 relative z-10">
        
        {/* Left Column Stack */}
        <div className="lg:col-span-8 flex flex-col gap-8">
          <Card className="p-8 bg-gradient-to-br from-bg-3 to-bg-4 border border-border/50 h-[320px] flex flex-col shadow-2xl">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
              <div className="space-y-1">
                <h2 className="text-3xl font-bold text-ink tracking-tighter uppercase">{t('activity_overview')}</h2>
                <p className="text-[10px] font-bold text-ink-3 uppercase tracking-[0.4em] opacity-50">{t('daily_stats')}</p>
              </div>
              <div className="flex p-1.5 bg-bg/40 rounded-2xl backdrop-blur-xl border border-border/10 shadow-inner">
                {['messages', 'tokens', 'avg_latency', 'error_rate'].map(tKey => (
                  <button key={tKey} onClick={() => setMetric(tKey)} className={clsx("px-6 py-2.5 text-[10px] font-bold tracking-[0.2em] transition-all rounded-xl uppercase", metric === tKey ? "bg-accent text-white shadow-xl" : "text-ink-3 hover:text-ink")}>
                    {t(tKey)}
                  </button>
                ))}
              </div>
            </div>
            <OverviewChart data={chartData} metric={metric} />
          </Card>

          <SystemMonitor system={system} cpuHistory={cpuHistory} />
        </div>

        {/* Right Column (Orchestration) */}
        {(() => {
          const ORCH_PALETTE = ['#3B82F6', '#10B981', '#7C3AED', '#F59E0B', '#EF4444', '#EC4899']
          const sortedUsage = [...usage].sort((a,b) => b.count - a.count)
          const getInitials = (name) => {
            const base = name.split('/').pop() || name
            return base.replace(/[^a-zA-Z0-9]/g, '').slice(0, 2).toUpperCase()
          }
          return (
            <Card className="lg:col-span-4 p-6 flex flex-col bg-gradient-to-b from-bg-3 to-ink/5 h-[672px]">
              {/* Header */}
              <div className="flex items-center justify-between mb-6 px-1">
                <div>
                  <div className="flex items-center gap-3 mb-1">
                    <h2 className="text-2xl font-bold text-ink tracking-tighter uppercase">{t('ai_orchestration')}</h2>
                    <div className="w-2.5 h-2.5 rounded-full bg-success animate-pulse shadow-[0_0_12px_#10b981]" />
                  </div>
                  <p className="text-[10px] font-bold text-ink-3 uppercase tracking-widest opacity-50">{t('workload_distribution')}</p>
                </div>
                {sortedUsage.length > 0 && (
                  <span className="text-[10px] font-bold uppercase tracking-widest px-3 py-1.5 rounded-full shadow-inner border border-success/30" style={{ background: 'rgba(16,185,129,0.12)', color: '#10B981' }}>
                    {sortedUsage.length} {t('active_models_label')}
                  </span>
                )}
              </div>

              {/* Model List */}
              <div className="flex-1 overflow-y-auto custom-scrollbar pr-1" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {sortedUsage.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center opacity-20">
                    <LayoutDashboard size={40} className="mb-4" />
                    <span className="text-xs font-bold uppercase tracking-widest">{t('system_standby')}</span>
                  </div>
                ) : (
                  sortedUsage.map((u, i) => {
                    const accent = ORCH_PALETTE[i % ORCH_PALETTE.length]
                    const initials = getInitials(u.model)
                    const modelName = u.model.split('/').pop()
                    const provider = u.model.split('/')[0]
                    return (
                      <div
                        key={i}
                        className="group flex items-center gap-4 rounded-2xl overflow-hidden transition-all hover:brightness-110 shadow-sm"
                        style={{
                          background: 'var(--bg-4)',
                          padding: '12px 16px',
                          position: 'relative',
                        }}
                      >
                        {/* Accent Bar */}
                        <div
                          className="absolute left-0 top-0 bottom-0 w-[4px] rounded-l-2xl"
                          style={{ background: accent }}
                        />

                        {/* Avatar */}
                        <div
                          className="w-10 h-10 rounded-xl flex items-center justify-center text-xs font-bold flex-shrink-0 shadow-inner"
                          style={{
                            background: accent + '18',
                            color: accent,
                          }}
                        >
                          {initials}
                        </div>

                        {/* Name & Provider */}
                        <div className="flex-1 min-w-0">
                          <div className="text-base font-bold text-ink truncate tracking-tight leading-tight">{modelName}</div>
                          <div className="text-[10px] text-ink-3 uppercase tracking-widest leading-tight mt-1 font-bold opacity-60">{provider}</div>
                        </div>

                        {/* Stats */}
                        <div className="flex flex-col items-end gap-1 flex-shrink-0">
                          <div className="text-sm font-bold font-mono" style={{ color: accent }}>+{u.count} req</div>
                          <div className="text-[10px] text-ink-3 font-bold uppercase tracking-tight opacity-70">{u.latency}ms · {u.error_rate}%</div>
                        </div>
                      </div>
                    )
                  })
                )}
              </div>

              <button
                onClick={() => navigate('/chat')}
                className="mt-6 w-full flex items-center justify-center gap-3 rounded-2xl text-sm font-bold uppercase tracking-widest text-white transition-all shadow-xl active:scale-95"
                style={{
                  background: 'linear-gradient(135deg, #6366F1, #8B5CF6)',
                  padding: '18px',
                  border: 'none',
                  cursor: 'pointer',
                }}
              >
                <Bot size={20} className="text-white" />
                <span>{t('launch_agent') || 'LAUNCH AGENT'}</span>
              </button>
            </Card>
          )
        })()}
      </div>

      {/* ── Live Event Feed ───────────────────────────────────── */}
      <Card className="p-10 bg-bg-4/50 backdrop-blur-3xl border border-border/50 relative z-10 transition-all hover:bg-bg-4/70 group shadow-2xl">
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
             <div className="p-3 rounded-2xl bg-accent/20 text-accent shadow-lg"><Activity size={20} /></div>
             <h2 className="text-2xl font-bold text-ink tracking-tighter uppercase">{t('live_event_feed')}</h2>
          </div>
          <div className="flex items-center gap-3 border border-success/30 px-3 py-1 rounded-full bg-success/5 shadow-inner">
            <div className="w-2.5 h-2.5 rounded-full bg-success animate-ping" />
            <span className="text-[10px] font-bold text-success uppercase tracking-widest">{t('streaming')}</span>
          </div>
        </div>
        
        <div className="space-y-3 font-mono">
          {logs.length === 0 ? (
            <div className="py-12 text-center text-sm text-ink-3 opacity-40 italic font-bold uppercase tracking-widest">{t('waiting_events') || 'Waiting for events...'}</div>
          ) : (
            logs.map((log, i) => (
              <div key={i} className="flex items-center gap-5 text-[11px] group/item p-3 rounded-xl hover:bg-white/5 transition-all font-bold border border-transparent hover:border-border/30 shadow-sm">
                 <span className="text-accent opacity-60 font-mono tracking-tighter">{new Date().toLocaleTimeString()}</span>
                 <div className="w-2 h-2 rounded-full bg-accent/40 shadow-inner" />
                 <span className={clsx("flex-1 text-ink-2 truncate uppercase tracking-tight", log.level === 'ERROR' && "text-danger")}>{log.text}</span>
                 <ChevronRight size={18} className="text-ink-3 opacity-0 group-hover/item:opacity-100 transition-all transform translate-x-0 group-hover/item:translate-x-1" />
              </div>
            ))
          )}
        </div>
      </Card>

      <style dangerouslySetInnerHTML={{ __html: `
        /* Wave & Heartbeat — stroke draw */
        @keyframes spark-draw {
          from { stroke-dashoffset: 500; }
          to   { stroke-dashoffset: 0; }
        }
        .spark-wave {
          stroke-dasharray: 500;
          stroke-dashoffset: 500;
          animation: spark-draw 1.8s ease forwards 0.3s;
        }
        .spark-heartbeat {
          stroke-dasharray: 500;
          stroke-dashoffset: 500;
          animation: spark-draw 1.6s ease forwards 0.3s;
        }

        /* Vector Search — center node scale in */
        @keyframes vs-center-in {
          from { transform: scale(0); opacity: 0; }
          to   { transform: scale(1); opacity: 1; }
        }
        .vs-center {
          transform-origin: center;
          transform: scale(0);
          animation: vs-center-in 0.3s ease forwards 0.3s;
        }

        /* Vector Search — lines draw */
        @keyframes vs-line-draw {
          from { stroke-dashoffset: 180; opacity: 0; }
          to   { stroke-dashoffset: 0; opacity: 0.15; }
        }
        .vs-line {
          stroke-dasharray: 180;
          stroke-dashoffset: 180;
          opacity: 0;
          animation: vs-line-draw 0.4s ease forwards;
        }

        /* Vector Search — doc icons fade in */
        @keyframes vs-doc-in {
          from { opacity: 0; transform: scale(0.5); }
          to   { opacity: 0.22; transform: scale(1); }
        }
        .vs-doc {
          opacity: 0;
          transform-origin: center;
          animation: vs-doc-in 0.35s ease forwards;
        }

        /* Node network — nodes fade in */
        @keyframes spark-node-in {
          from { r: 0; opacity: 0; }
          to   { r: 3; opacity: 0.3; }
        }
        .spark-node {
          r: 0;
          opacity: 0;
          animation: spark-node-in 0.4s ease forwards;
        }

        /* Node network — edges draw */
        @keyframes spark-edge-in {
          from { opacity: 0; stroke-dashoffset: 200; }
          to   { opacity: 0.15; stroke-dashoffset: 0; }
        }
        .spark-edge {
          stroke-dasharray: 200;
          stroke-dashoffset: 200;
          opacity: 0;
          animation: spark-edge-in 0.5s ease forwards;
        }

        @keyframes float { 
          0%, 100% { transform: translateY(0) translateX(0); opacity: 0.1; }
          50% { transform: translateY(-100px) translateX(20px); opacity: 0.5; }
        }
        .animate-float { animation: float infinite linear; }
        @keyframes scan {
          0% { transform: translateY(0); opacity: 0; }
          50% { opacity: 1; }
          100% { transform: translateY(180px); opacity: 0; }
        }
        .animate-scan { animation: scan 3s linear infinite; }
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(var(--accent-rgb), 0.2); border-radius: 10px; }
      `}} />

    </div>
  )
}
