import { useState, useEffect, useRef, useCallback } from 'react'
import { api } from '../hooks/useApi'
import { copyToClipboard } from "../utils/clipboard"
import {
  Cpu, MemoryStick, HardDrive, Wifi, RefreshCw, Trash2,
  TrendingUp, MessageSquare, DollarSign, Zap, Clock,
  ShieldAlert, CheckCircle2, XCircle, ChevronUp, ChevronDown,
  BarChart3, Monitor, Thermometer, Activity, Copy, Check,
  Database, FolderOpen, ScrollText, Eraser, RotateCcw, AlertTriangle,
} from 'lucide-react'
import clsx from 'clsx'

// ── Gauge SVG ─────────────────────────────────────────────────
function Gauge({ value, max = 100, size = 90, label, sub, unit = '%' }) {
  const pct   = Math.min(value / max, 1)
  const r     = (size - 14) / 2
  const circ  = 2 * Math.PI * r
  const color = pct > 0.85 ? '#ef4444' : pct > 0.65 ? '#f59e0b' : '#6366f1'
  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
          <circle cx={size/2} cy={size/2} r={r} fill="none"
            stroke="rgba(255,255,255,0.06)" strokeWidth={10}/>
          <circle cx={size/2} cy={size/2} r={r} fill="none"
            stroke={color} strokeWidth={10} strokeLinecap="round"
            strokeDasharray={`${circ * pct} ${circ * (1 - pct)}`}
            style={{ transition: 'stroke-dasharray 0.6s ease, stroke 0.3s' }}/>
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-sm font-bold font-mono" style={{ color }}>
            {unit === '%' ? Math.round(value) : value}{unit}
          </span>
        </div>
      </div>
      <div className="text-[11px] font-semibold text-ink-2 mt-1">{label}</div>
      {sub && <div className="text-[9px] text-ink-3 text-center mt-0.5">{sub}</div>}
    </div>
  )
}

// ── Progress bar ──────────────────────────────────────────────
function Bar({ pct, color = 'bg-accent', thin }) {
  const danger = pct > 85
  return (
    <div className={clsx('w-full bg-bg-5 rounded-full overflow-hidden', thin ? 'h-1' : 'h-2')}>
      <div className={clsx('h-full rounded-full transition-all duration-700',
        danger ? 'bg-danger' : color)}
        style={{ width: `${Math.min(pct, 100)}%` }}/>
    </div>
  )
}

// ── Stat card ─────────────────────────────────────────────────
function StatCard({ label, value, icon: Icon, colorClass, sub }) {
  return (
    <div className="bg-bg-3 border border-border rounded-xl p-3.5">
      <div className={clsx('w-7 h-7 rounded-lg flex items-center justify-center mb-2', colorClass + '/15')}>
        <Icon size={14} className={colorClass.replace('bg-', 'text-')}/>
      </div>
      <div className="text-xl font-bold font-mono text-ink">{value}</div>
      <div className="text-[10px] text-ink-3 mt-0.5">{label}</div>
      {sub && <div className="text-[10px] text-ink-2 mt-0.5">{sub}</div>}
    </div>
  )
}

// ── Mini bar chart ────────────────────────────────────────────
function MiniBarChart({ data, valueKey, color }) {
  const max = Math.max(...data.map(d => d[valueKey] || 0), 1)
  return (
    <div className="flex items-end gap-1 h-14 w-full">
      {data.map((d, i) => {
        const h = Math.max(((d[valueKey] || 0) / max) * 100, 2)
        const day = (d.day || '').slice(5)
        return (
          <div key={i} className="flex-1 flex flex-col items-center gap-0.5 group relative">
            <div className="absolute -top-6 left-1/2 -translate-x-1/2 bg-bg-2 border border-border
              rounded px-1.5 py-0.5 text-[9px] text-ink whitespace-nowrap opacity-0
              group-hover:opacity-100 transition-opacity pointer-events-none z-10">
              {day}: {(d[valueKey] || 0).toLocaleString()}
            </div>
            <div className="w-full rounded-t transition-all duration-500"
              style={{ height: `${h}%`, background: color, opacity: 0.75 }}/>
            <div className="text-[8px] text-ink-3">{day?.slice(3)}</div>
          </div>
        )
      })}
    </div>
  )
}

// ── Core usage card (per core CPU) ───────────────────────────
function CpuCores({ cores = [] }) {
  if (!cores.length) return null
  return (
    <div>
      <div className="text-[9px] text-ink-3 mb-1.5 uppercase tracking-wider">Per Core</div>
      <div className="grid gap-1" style={{ gridTemplateColumns: `repeat(${Math.min(cores.length, 8)}, 1fr)` }}>
        {cores.map((pct, i) => (
          <div key={i} className="text-center">
            <div className={clsx('h-8 rounded flex items-end justify-center pb-0.5 relative overflow-hidden',
              'bg-bg-5')}>
              <div className={clsx('absolute bottom-0 w-full rounded transition-all duration-500',
                pct > 85 ? 'bg-danger/60' : pct > 65 ? 'bg-warn/60' : 'bg-accent/50')}
                style={{ height: `${Math.max(pct, 2)}%` }}/>
              <span className="relative text-[8px] font-mono text-ink-2 z-10">{Math.round(pct)}</span>
            </div>
            <div className="text-[7px] text-ink-3 mt-0.5">C{i}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Reset Modal ───────────────────────────────────────────────
function ResetModal({ onClose, onConfirm }) {
  const [text, setText] = useState('')
  const [load, setLoad] = useState(false)
  const ok = text.toLowerCase() === 'reset'
  const go = async () => {
    if (!ok) return
    setLoad(true)
    try { await onConfirm(); onClose() } catch {} finally { setLoad(false) }
  }
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ backdropFilter: 'blur(4px)', background: 'rgba(0,0,0,0.65)' }}>
      <div className="bg-bg-3 border border-danger/30 rounded-2xl w-full max-w-sm shadow-2xl overflow-hidden">
        <div className="bg-danger/8 border-b border-danger/20 px-4 py-3 flex items-center gap-2.5">
          <ShieldAlert size={18} className="text-danger"/>
          <div>
            <div className="text-sm font-bold text-danger">Reset Data Analytics</div>
            <div className="text-[10px] text-danger/70">Semua riwayat chat & statistik akan dihapus permanen</div>
          </div>
        </div>
        <div className="p-4 space-y-3">
          <div className="bg-bg-4 rounded-xl p-3 text-[10px] text-ink-3 space-y-1.5">
            {['Semua pesan chat', 'Semua sesi percakapan', 'Log penggunaan API & model', 'Statistik token & biaya'].map((item, i) => (
              <div key={i} className="flex items-center gap-2"><XCircle size={10} className="text-danger"/>{item}</div>
            ))}
          </div>
          <div>
            <div className="text-[10px] text-ink-3 mb-1.5">
              Ketik <code className="font-mono bg-bg-4 px-1 rounded text-danger">reset</code> untuk konfirmasi:
            </div>
            <input value={text} onChange={e => setText(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && ok && go()}
              placeholder="ketik: reset"
              className="w-full bg-bg-2 border border-border-2 rounded-lg px-3 py-2 text-xs font-mono text-ink outline-none focus:border-danger placeholder-ink-3"/>
          </div>
          <div className="flex gap-2">
            <button onClick={onClose}
              className="flex-1 px-3 py-2 text-xs rounded-lg bg-bg-4 hover:bg-bg-5 border border-border text-ink-2 font-medium">Batal</button>
            <button onClick={go} disabled={!ok || load}
              className="flex-1 px-3 py-2 text-xs rounded-lg bg-danger hover:bg-danger/80 text-white font-medium disabled:opacity-40 flex items-center justify-center gap-1.5">
              {load ? <><RefreshCw size={11} className="animate-spin"/>Mereset...</> : <><Trash2 size={11}/>Reset Sekarang</>}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Panduan install psutil ────────────────────────────────────
function CmdLine({ cmd }) {
  const [copied, setCopied] = useState(false)
  return (
    <div className="flex items-center gap-2 bg-bg-2 border border-border rounded-lg px-3 py-2 group">
      <code className="flex-1 font-mono text-[11px] text-accent-2 break-all">{cmd}</code>
      <button onClick={() => { copyToClipboard(cmd); setCopied(true); setTimeout(() => setCopied(false), 2000) }}
        className="flex-shrink-0 text-ink-3 hover:text-ink transition-colors">
        {copied ? <Check size={13} className="text-success"/> : <Copy size={13}/>}
      </button>
    </div>
  )
}

function PsutilInstallGuide({ onRetry }) {
  const [tab, setTab] = useState('venv')
  const tabs = [
    { id: 'venv',   label: 'Venv (Rekomendasi)' },
    { id: 'system', label: 'System Python' },
    { id: 'apt',    label: 'apt (Ubuntu)' },
  ]
  const cmds = {
    venv:   'cd ~/Downloads/ai-super-assistant/backend && source venv/bin/activate && pip install psutil',
    system: 'pip3 install psutil --break-system-packages',
    apt:    'sudo apt install -y python3-psutil',
  }
  return (
    <div className="bg-warn/5 border border-warn/25 rounded-xl overflow-hidden">
      <div className="flex items-center gap-2.5 p-3.5 border-b border-warn/15">
        <span className="text-xl">⚠️</span>
        <div>
          <div className="text-sm font-semibold text-warn">Modul psutil belum terinstall</div>
          <div className="text-[10px] text-warn/70">Install untuk aktifkan monitoring CPU, RAM, dan Disk</div>
        </div>
      </div>
      <div className="p-3.5 space-y-3">
        {/* Tab selector */}
        <div className="flex gap-1 bg-bg-4 rounded-lg p-1">
          {tabs.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)}
              className={clsx('flex-1 py-1.5 text-[11px] font-medium rounded-md transition-all',
                tab === t.id ? 'bg-bg-2 text-ink shadow' : 'text-ink-3 hover:text-ink')}>
              {t.label}
            </button>
          ))}
        </div>

        {/* Command */}
        <div className="space-y-1.5">
          <div className="text-[10px] text-ink-3">
            {tab === 'venv'   && 'Install ke virtualenv AI SUPER ASSISTANT (paling aman):'}
            {tab === 'system' && 'Jika virtualenv tidak ditemukan atau pakai Python sistem:'}
            {tab === 'apt'    && 'Sudah install via apt tapi masih error? Aktifkan akses ke sistem:'}
          </div>
          <CmdLine cmd={cmds[tab]}/>
        </div>

        {tab === 'apt' && (
          <div className="text-[10px] text-ink-3 bg-bg-4 rounded-lg p-2.5 space-y-1.5">
            <div>✅ Sudah install via apt tapi masih error? Virtualenv tidak bisa akses paket sistem.</div>
            <div>Aktifkan akses paket sistem ke virtualenv:</div>
            <code className="block font-mono text-accent-2 bg-bg-2 px-2 py-1 rounded">cd ~/Downloads/ai-super-assistant/backend && source venv/bin/activate && pip install psutil --break-system-packages</code>
            <div className="pt-1">Atau jalankan langsung tanpa venv:</div>
            <code className="block font-mono text-accent-2 bg-bg-2 px-2 py-1 rounded">pip3 install psutil --break-system-packages</code>
          </div>
        )}
        {tab === 'venv' && (
          <div className="text-[10px] text-ink-3 bg-bg-4 rounded-lg p-2.5">
            💡 Setelah install, tekan tombol "Coba lagi" — tidak perlu restart server.
          </div>
        )}

        <div className="flex items-center gap-2 pt-1">
          <button onClick={onRetry}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg bg-warn/10 hover:bg-warn/20 border border-warn/30 text-warn font-medium transition-colors">
            <RefreshCw size={11}/>Coba lagi setelah install
          </button>
        </div>
      </div>
    </div>
  )
}


// ── Main ──────────────────────────────────────────────────────
export default function Analytics() {
  const [dash,      setDash]      = useState(null)
  const [usage,     setUsage]     = useState([])
  const [system,    setSystem]    = useState(null)
  const [timeline,  setTL]        = useState([])
  const [loading,   setLoading]   = useState(true)
  const [sysErr,    setSysErr]    = useState(null)
  const [showReset, setShowReset] = useState(false)
  const [storage,   setStorage]   = useState(null)
  const [cleaning,  setCleaning]  = useState({})
  const [cleanMsg,  setCleanMsg]  = useState(null)
  const [rotateMsg, setRotateMsg] = useState(null)
  const [resetMsg,  setResetMsg]  = useState(null)
  const [lastRef,   setLastRef]   = useState(null)
  const [showCores, setShowCores] = useState(false)
  const sysTimer = useRef(null)

  const fetchSystem = useCallback(async () => {
    try {
      const s = await api.systemStats()
      if (!s || s.available === false) {
        setSysErr(s?.install_hint || 'pip install psutil')
        setSystem(null)
      } else {
        setSystem(s)
        setSysErr(null)
      }
    } catch (e) {
      const msg = e.message || ''
      if (msg.includes('500') || msg.includes('psutil')) {
        setSysErr('pip install psutil')
      } else {
        setSysErr('pip install psutil  (atau cek koneksi backend)')
      }
      setSystem(null)
    }
  }, [])

  const fetchAll = useCallback(async () => {
    setLoading(true)
    try {
      const [d, u, tl] = await Promise.allSettled([
        api.dashboard(), api.usage(), api.timeline(),
      ])
      if (d.status === 'fulfilled') setDash(d.value)
      if (u.status === 'fulfilled') setUsage(u.value)
      if (tl.status === 'fulfilled') setTL(tl.value)
      setLastRef(new Date())
    } finally { setLoading(false) }
  }, [])

  useEffect(() => {
    fetchAll()
    fetchSystem()
    api.storageInfo().then(setStorage).catch(() => {})
    sysTimer.current = setInterval(fetchSystem, 3000)
    return () => clearInterval(sysTimer.current)
  }, [])

  const handleReset = async () => {
    await api.resetAnalytics()
    setResetMsg('Data analytics berhasil direset!')
    setDash(null); setUsage([]); setTL([])
    await fetchAll()
    setTimeout(() => setResetMsg(null), 4000)
  }

  const stats     = dash?.stats || {}
  const totalTok  = usage.reduce((a, u) => a + (u.tokens || 0), 0)
  const totalCost = usage.reduce((a, u) => a + (u.cost_usd || 0), 0)
  const maxReq    = Math.max(...usage.map(u => u.count), 1)

  return (
    <div className="p-4 md:p-6 max-w-full space-y-4">

      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-lg font-bold text-ink">Analytics</h1>
          <p className="text-xs text-ink-3">
            Monitoring penggunaan & performa sistem
            {lastRef && <span className="ml-2 opacity-50">· {lastRef.toLocaleTimeString()}</span>}
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={fetchAll} disabled={loading}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs rounded-lg bg-bg-4 hover:bg-bg-5 border border-border text-ink-2 hover:text-ink disabled:opacity-50">
            <RefreshCw size={11} className={loading ? 'animate-spin' : ''}/>Refresh
          </button>
          <button onClick={() => setShowReset(true)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs rounded-lg bg-danger/10 hover:bg-danger/20 border border-danger/30 text-danger font-medium">
            <Trash2 size={11}/>Reset
          </button>
        </div>
      </div>

      {resetMsg && (
        <div className="flex items-center gap-2 p-3 bg-success/10 border border-success/30 rounded-xl text-xs text-success">
          <CheckCircle2 size={14}/>{resetMsg}
        </div>
      )}

      {/* ── Stat Cards ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard label="Total Pesan"   value={(stats.total_messages||0).toLocaleString()} icon={MessageSquare} colorClass="bg-accent"  sub={`${stats.total_sessions||0} sesi`}/>
        <StatCard label="Total Token"   value={totalTok.toLocaleString()}                  icon={Zap}           colorClass="bg-warn"   sub={`$${totalCost.toFixed(4)}`}/>
        <StatCard label="Dokumen RAG"   value={stats.total_docs||0}                        icon={HardDrive}     colorClass="bg-success" sub="terindeks"/>
        <StatCard label="Uptime Server" value={system?.uptime || '—'}                      icon={Clock}         colorClass="bg-pink"/>
      </div>

      {/* ── System Resources ── */}
      <div className="bg-bg-3 border border-border rounded-xl overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-border">
          <div className="flex items-center gap-2">
            <Activity size={14} className="text-accent-2"/>
            <span className="text-sm font-semibold text-ink">Sumber Daya Sistem</span>
            <span className="text-[9px] text-ink-3 bg-bg-4 px-2 py-0.5 rounded-full">Realtime · 3 detik</span>
          </div>
          {system && (
            <button onClick={() => setShowCores(!showCores)}
              className="text-[10px] text-ink-3 hover:text-ink flex items-center gap-1">
              {showCores ? <ChevronUp size={11}/> : <ChevronDown size={11}/>}
              Per Core
            </button>
          )}
        </div>

        <div className="p-4">
          {sysErr ? (
            <PsutilInstallGuide onRetry={fetchSystem} />
          ) : !system ? (
            <div className="flex items-center justify-center h-20 text-xs text-ink-3 gap-2">
              <RefreshCw size={13} className="animate-spin"/>Memuat data sistem...
            </div>
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4 justify-items-center py-2">
                <Gauge value={system.cpu.percent} label="CPU"
                  sub={`${system.cpu.count} core · ${system.cpu.freq_mhz||0}MHz`}/>
                <Gauge value={system.memory.percent} label="RAM"
                  sub={`${system.memory.used_mb} / ${system.memory.total_mb} MB`}/>
                <Gauge value={system.disk.percent} label="Disk"
                  sub={`${system.disk.used_gb} / ${system.disk.total_gb} GB`}/>
                {system.swap.total_mb > 0 && (
                  <Gauge value={system.swap.percent} label="Swap"
                    sub={`${system.swap.used_mb} / ${system.swap.total_mb} MB`}/>
                )}
                {system.gpu.map((g, i) => (
                  <Gauge key={i} value={g.util_pct} label={`GPU ${i}`}
                    sub={`${g.mem_used_mb}/${g.mem_total_mb}MB · ${g.temp_c}°C`}/>
                ))}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                <div className="bg-bg-4 rounded-xl p-3 space-y-2">
                  <div className="flex items-center gap-2 mb-1">
                    <Cpu size={12} className="text-accent-2"/>
                    <span className="text-[11px] font-semibold text-ink">CPU</span>
                    <span className="ml-auto text-[10px] font-mono text-accent-2 font-bold">{system.cpu.percent}%</span>
                  </div>
                  <Bar pct={system.cpu.percent} color="bg-accent"/>
                  <div className="grid grid-cols-2 gap-1 text-[10px] text-ink-3">
                    <span>Logical: <b className="text-ink">{system.cpu.count}</b></span>
                    <span>Physical: <b className="text-ink">{system.cpu.count_phys||'—'}</b></span>
                    <span>Frekuensi: <b className="text-ink">{system.cpu.freq_mhz||0} MHz</b></span>
                  </div>
                  {showCores && <CpuCores cores={system.cpu.per_core || []}/>}
                </div>

                <div className="bg-bg-4 rounded-xl p-3 space-y-2">
                  <div className="flex items-center gap-2 mb-1">
                    <MemoryStick size={12} className="text-success"/>
                    <span className="text-[11px] font-semibold text-ink">Memori RAM</span>
                    <span className="ml-auto text-[10px] font-mono text-success font-bold">{system.memory.percent}%</span>
                  </div>
                  <Bar pct={system.memory.percent} color="bg-success"/>
                  <div className="grid grid-cols-2 gap-1 text-[10px] text-ink-3">
                    <span>Digunakan: <b className="text-ink">{system.memory.used_mb} MB</b></span>
                    <span>Tersedia: <b className="text-ink">{system.memory.free_mb} MB</b></span>
                    <span>Total: <b className="text-ink">{system.memory.total_mb} MB</b></span>
                    {system.memory.cached_mb > 0 && <span>Cache: <b className="text-ink">{system.memory.cached_mb} MB</b></span>}
                  </div>
                </div>

                <div className="bg-bg-4 rounded-xl p-3 space-y-2">
                  <div className="flex items-center gap-2 mb-1">
                    <HardDrive size={12} className="text-warn"/>
                    <span className="text-[11px] font-semibold text-ink">Penyimpanan</span>
                    <span className="ml-auto text-[10px] font-mono text-warn font-bold">{system.disk.percent}%</span>
                  </div>
                  <Bar pct={system.disk.percent} color="bg-warn"/>
                  <div className="grid grid-cols-2 gap-1 text-[10px] text-ink-3">
                    <span>Digunakan: <b className="text-ink">{system.disk.used_gb} GB</b></span>
                    <span>Tersedia: <b className="text-ink">{system.disk.free_gb} GB</b></span>
                    <span>Total: <b className="text-ink">{system.disk.total_gb} GB</b></span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {timeline.length > 0 && (
        <div className="bg-bg-3 border border-border rounded-xl p-4">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp size={14} className="text-success"/>
            <span className="text-sm font-semibold text-ink">Aktivitas 7 Hari Terakhir</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <div className="text-[10px] text-ink-3 mb-2">Pesan per hari</div>
              <MiniBarChart data={timeline} valueKey="messages" color="#6366f1"/>
            </div>
            <div>
              <div className="text-[10px] text-ink-3 mb-2">Token per hari</div>
              <MiniBarChart data={timeline} valueKey="tokens" color="#10b981"/>
            </div>
          </div>
        </div>
      )}

      {storage && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {storage.components.map(comp => (
            <div key={comp.id} className="bg-bg-4 border border-border rounded-xl p-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-lg">{comp.icon}</span>
                <span className="text-xs font-mono font-bold text-ink">{comp.size}</span>
              </div>
              <div className="text-xs font-semibold text-ink">{comp.name}</div>
              <div className="text-[10px] text-ink-3">{comp.desc}</div>
              {comp.can_clean && (
                <button onClick={() => {}} className="mt-2 text-[10px] text-accent hover:underline">Bersihkan</button>
              )}
            </div>
          ))}
        </div>
      )}

      {showReset && <ResetModal onClose={() => setShowReset(false)} onConfirm={handleReset} />}
    </div>
  )
}
