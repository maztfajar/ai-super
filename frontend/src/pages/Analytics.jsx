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
import { useTranslation } from 'react-i18next'
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
          <span className="text-lg font-bold font-mono" style={{ color }}>
            {unit === '%' ? Math.round(value) : value}{unit}
          </span>
        </div>
      </div>
      <div className="text-xs font-bold text-ink-3 uppercase tracking-widest mt-2">{label}</div>
      {sub && <div className="text-[11px] text-ink-3 text-center mt-1.5 font-semibold uppercase tracking-tight opacity-70">{sub}</div>}
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
    <div className="bg-bg-3 border border-border rounded-xl p-5 shadow-sm">
      <div className={clsx('w-9 h-9 rounded-lg flex items-center justify-center mb-3', colorClass + '/15')}>
        <Icon size={16} className={colorClass.replace('bg-', 'text-')}/>
      </div>
      <div className="text-2xl font-bold font-mono text-ink tracking-tight">{value}</div>
      <div className="text-xs font-bold text-ink-3 uppercase tracking-wider mt-1.5">{label}</div>
      {sub && <div className="text-[11px] text-ink-2 mt-2 font-semibold uppercase tracking-tight opacity-70">{sub}</div>}
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
            <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-bg-2 border border-border
              rounded-lg px-2.5 py-1 text-xs text-ink whitespace-nowrap opacity-0
              group-hover:opacity-100 transition-opacity pointer-events-none z-10 font-bold shadow-lg">
              {day}: {(d[valueKey] || 0).toLocaleString()}
            </div>
            <div className="w-full rounded-t transition-all duration-500"
              style={{ height: `${h}%`, background: color, opacity: 0.75 }}/>
            <div className="text-[11px] text-ink-3 font-bold uppercase tracking-tighter mt-1">{day?.slice(3)}</div>
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
      <div className="text-xs text-ink-3 mb-2 uppercase tracking-widest font-bold opacity-60">Per Core</div>
      <div className="grid gap-1.5" style={{ gridTemplateColumns: `repeat(${Math.min(cores.length, 8)}, 1fr)` }}>
        {cores.map((pct, i) => (
          <div key={i} className="text-center">
            <div className={clsx('h-10 rounded-lg flex items-end justify-center pb-1 relative overflow-hidden',
              'bg-bg-5 border border-border/20')}>
              <div className={clsx('absolute bottom-0 w-full rounded-lg transition-all duration-500',
                pct > 85 ? 'bg-danger/60' : pct > 65 ? 'bg-warn/60' : 'bg-accent/50')}
                style={{ height: `${Math.max(pct, 2)}%` }}/>
              <span className="relative text-[11px] font-mono text-ink-2 z-10 font-bold">{Math.round(pct)}</span>
            </div>
            <div className="text-[10px] text-ink-3 mt-1 font-bold uppercase tracking-tighter">C{i}</div>
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
        <div className="bg-danger/10 border-b-2 border-danger/20 px-5 py-4 flex items-center gap-3">
          <ShieldAlert size={22} className="text-danger"/>
          <div>
            <div className="text-lg font-bold text-danger uppercase tracking-tight">Reset Data Analytics</div>
            <div className="text-xs text-danger/80 font-semibold uppercase tracking-widest mt-0.5">Semua riwayat chat & statistik akan dihapus permanen</div>
          </div>
        </div>
        <div className="p-5 space-y-4">
          <div className="bg-bg-4 border border-border/30 rounded-xl p-4 text-sm text-ink-3 space-y-2 font-semibold">
            {['Semua pesan chat', 'Semua sesi percakapan', 'Log penggunaan API & model', 'Statistik token & biaya'].map((item, i) => (
              <div key={i} className="flex items-center gap-3"><XCircle size={14} className="text-danger"/>{item}</div>
            ))}
          </div>
          <div>
            <div className="text-xs text-ink-3 mb-2 font-bold uppercase tracking-widest opacity-70">
              Ketik <code className="font-mono bg-bg-4 px-1.5 py-0.5 rounded text-danger font-bold">reset</code> untuk konfirmasi:
            </div>
            <input value={text} onChange={e => setText(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && ok && go()}
              placeholder="ketik: reset"
              className="w-full bg-bg-2 border border-border rounded-xl px-4 py-3 text-sm font-mono text-ink outline-none focus:border-danger placeholder-ink-3 shadow-inner"/>
          </div>
          <div className="flex gap-3 pt-2">
            <button onClick={onClose}
              className="flex-1 px-4 py-3 text-sm rounded-xl bg-bg-4 hover:bg-bg-5 border border-border text-ink-2 font-bold uppercase tracking-tight transition-all">Batal</button>
            <button onClick={go} disabled={!ok || load}
              className="flex-1 px-4 py-3 text-sm rounded-xl bg-danger hover:bg-danger/80 text-white font-bold uppercase tracking-tight disabled:opacity-40 flex items-center justify-center gap-2 transition-all shadow-lg shadow-danger/20 active:scale-95">
              {load ? <><RefreshCw size={14} className="animate-spin"/>Mereset...</> : <><Trash2 size={14}/>Reset Sekarang</>}
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
    <div className="flex items-center gap-3 bg-bg-2 border border-border rounded-xl px-4 py-3 group shadow-inner">
      <code className="flex-1 font-mono text-sm text-accent-2 break-all font-bold">{cmd}</code>
      <button onClick={() => { copyToClipboard(cmd); setCopied(true); setTimeout(() => setCopied(false), 2000) }}
        className="flex-shrink-0 text-ink-3 hover:text-ink transition-all p-1.5 rounded-lg hover:bg-bg-4">
        {copied ? <Check size={16} className="text-success"/> : <Copy size={16}/>}
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
    venv:   'cd ~/Downloads/ai-orchestrator/backend && source venv/bin/activate && pip install psutil',
    system: 'pip3 install psutil --break-system-packages',
    apt:    'sudo apt install -y python3-psutil',
  }
  return (
    <div className="bg-warn/10 border border-warn/30 rounded-2xl overflow-hidden shadow-md">
      <div className="flex items-center gap-3.5 p-5 border-b-2 border-warn/15 bg-warn/5">
        <span className="text-2xl">⚠️</span>
        <div>
          <div className="text-lg font-bold text-warn uppercase tracking-tight">Modul psutil belum terinstall</div>
          <div className="text-xs text-warn/80 font-bold uppercase tracking-widest mt-1">Install untuk aktifkan monitoring CPU, RAM, dan Disk</div>
        </div>
      </div>
      <div className="p-3.5 space-y-3">
        {/* Tab selector */}
        <div className="flex gap-2 bg-bg-4 border border-border/20 rounded-xl p-1.5 shadow-inner">
          {tabs.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)}
              className={clsx('flex-1 py-2 text-sm font-bold uppercase tracking-tight rounded-lg transition-all',
                tab === t.id ? 'bg-bg-2 text-accent-2 shadow-lg border border-border/50' : 'text-ink-3 hover:text-ink hover:bg-bg-5')}>
              {t.label}
            </button>
          ))}
        </div>

        {/* Command */}
        <div className="space-y-2">
          <div className="text-xs text-ink-3 font-bold uppercase tracking-widest opacity-70">
            {tab === 'venv'   && 'Install ke virtualenv AI ORCHESTRATOR (paling aman):'}
            {tab === 'system' && 'Jika virtualenv tidak ditemukan atau pakai Python sistem:'}
            {tab === 'apt'    && 'Sudah install via apt tapi masih error? Aktifkan akses ke sistem:'}
          </div>
          <CmdLine cmd={cmds[tab]}/>
        </div>

        {tab === 'apt' && (
          <div className="text-xs text-ink-3 bg-bg-4 rounded-lg p-2.5 space-y-1.5 font-medium">
            <div>✅ Sudah install via apt tapi masih error? Virtualenv tidak bisa akses paket sistem.</div>
            <div>Aktifkan akses paket sistem ke virtualenv:</div>
            <code className="block font-mono text-accent-2 bg-bg-2 px-2 py-1 rounded font-semibold">cd ~/Downloads/ai-orchestrator/backend && source venv/bin/activate && pip install psutil --break-system-packages</code>
            <div className="pt-1">Atau jalankan langsung tanpa venv:</div>
            <code className="block font-mono text-accent-2 bg-bg-2 px-2 py-1 rounded font-semibold">pip3 install psutil --break-system-packages</code>
          </div>
        )}
        {tab === 'venv' && (
          <div className="text-xs text-ink-3 bg-bg-4 rounded-lg p-2.5 font-medium">
            💡 Setelah install, tekan tombol "Coba lagi" — tidak perlu restart server.
          </div>
        )}

        <div className="flex items-center gap-3 pt-2">
          <button onClick={onRetry}
            className="flex items-center gap-2 px-4 py-2.5 text-sm rounded-xl bg-warn/10 hover:bg-warn/20 border border-warn/30 text-warn font-bold uppercase tracking-tight transition-all shadow-md active:scale-95">
            <RefreshCw size={14}/>Coba lagi setelah install
          </button>
        </div>
      </div>
    </div>
  )
}


// ── Main ──────────────────────────────────────────────────────
export default function Analytics() {
  const { t } = useTranslation()
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
  const [mediaFiles, setMediaFiles] = useState([])
  const [mediaLoading, setMediaLoading] = useState(false)
  const [healingEvents, setHealingEvents] = useState([])
  const [healingStatus, setHealingStatus] = useState(null)
  const [snapshots, setSnapshots] = useState([])
  const [rollbackLoading, setRollbackLoading] = useState(false)
  const [triggerLoading, setTriggerLoading] = useState(false)
  const [telegramLoading, setTelegramLoading] = useState(false)
  const [telegramMsg, setTelegramMsg] = useState(null)
  const sysTimer = useRef(null)

  const formatBytes = (bytes) => {
    if (!bytes || bytes === 0) return '0 B'
    const units = ['B', 'KB', 'MB', 'GB', 'TB']
    let value = bytes
    let index = 0
    while (value >= 1024 && index < units.length - 1) {
      value /= 1024
      index += 1
    }
    return `${value.toFixed(1)} ${units[index]}`
  }

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
      const [d, u, tl, h, hs, s] = await Promise.allSettled([
        api.dashboard(), api.usage(), api.timeline(),
        api.healingEvents(20), api.healingStatus(), api.getSnapshots(10)
      ])
      if (d.status === 'fulfilled') setDash(d.value)
      if (u.status === 'fulfilled') setUsage(u.value)
      if (tl.status === 'fulfilled') setTL(tl.value)
      if (h.status === 'fulfilled') setHealingEvents(h.value.events || [])
      if (hs.status === 'fulfilled') setHealingStatus(hs.value)
      if (s.status === 'fulfilled') setSnapshots(s.value.snapshots || [])
      setLastRef(new Date())
    } finally { setLoading(false) }
  }, [])

  useEffect(() => {
    fetchAll()
    fetchSystem()
    api.storageInfo().then(setStorage).catch(() => {})
    fetchMedia()
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

  const fetchMedia = async () => {
    setMediaLoading(true)
    try {
      const res = await api.listMedia()
      setMediaFiles(res.files || [])
    } catch (e) {
      console.error('Failed to fetch media', e)
    } finally {
      setMediaLoading(false)
    }
  }

  const deleteMediaFile = async (filename) => {
    if (!confirm(`Hapus file "${filename}"?`)) return
    try {
      await api.deleteMedia(filename)
      setMediaFiles(prev => prev.filter(f => f.filename !== filename))
    } catch (e) {
      alert('Gagal menghapus file: ' + e.message)
    }
  }

  const deleteAllMediaFiles = async () => {
    if (!confirm(`Hapus semua ${mediaFiles.length} file media? Tindakan ini tidak bisa dibatalkan.`)) return
    try {
      const res = await api.deleteAllMedia()
      alert(res.detail || 'Semua file media berhasil dihapus')
      setMediaFiles([])
      await fetchMedia()
    } catch (e) {
      alert('Gagal menghapus semua file: ' + e.message)
    }
  }

  const handleCleanStorage = async (componentId) => {
    if (!confirm(`Bersihkan storage "${componentId}"? (Hasil mungkin tidak diproses jika backend belum siap)`)) return
    setCleaning(prev => ({ ...prev, [componentId]: true }))
    try {
      const res = await api.cleanStorage(componentId)
      setCleanMsg(res.detail || `Storage "${componentId}" berhasil dibersihkan`)
      await new Promise(r => setTimeout(r, 1500))
      api.storageInfo().then(setStorage).catch(() => {})
      setTimeout(() => setCleanMsg(null), 4000)
    } catch (e) {
      alert('Gagal membersihkan storage: ' + e.message)
    } finally {
      setCleaning(prev => ({ ...prev, [componentId]: false }))
    }
  }

  const handleTriggerHealing = async () => {
    setTriggerLoading(true)
    try {
      const res = await api.triggerHealingCheck()
      setHealingEvents(res.events || [])
      if (res.engine_status) setHealingStatus(res.engine_status)
    } catch (e) {
      alert('Gagal trigger check: ' + e.message)
    } finally {
      setTriggerLoading(false)
    }
  }

  const handleTestTelegram = async () => {
    setTelegramLoading(true)
    setTelegramMsg(null)
    try {
      const res = await api.testHealingTelegram()
      setTelegramMsg(res.success
        ? { ok: true, text: res.message }
        : { ok: false, text: res.error })
    } catch (e) {
      setTelegramMsg({ ok: false, text: e.message })
    } finally {
      setTelegramLoading(false)
      setTimeout(() => setTelegramMsg(null), 6000)
    }
  }

  const handleRollback = async () => {
    if (!confirm('Peringatan: Ini akan mengembalikan sistem ke kondisi stabil terakhir (sebelum aksi AI terakhir). Apakah Anda yakin?')) return
    setRollbackLoading(true)
    try {
      const res = await api.rollbackSnapshot()
      if (res.success) {
        alert('Rollback berhasil! Sistem telah dikembalikan ke state sebelumnya.')
        await fetchAll()
      } else {
        alert('Gagal melakukan rollback: ' + res.error)
      }
    } catch (e) {
      alert('Error saat rollback: ' + e.message)
    } finally {
      setRollbackLoading(false)
    }
  }

  const stats     = dash?.stats || {}
  const totalTok  = usage.reduce((a, u) => a + (u.tokens || 0), 0)
  const totalCost = usage.reduce((a, u) => a + (u.cost_usd || 0), 0)
  const maxReq    = Math.max(...usage.map(u => u.count), 1)

  return (
    <div className="p-4 md:pt-4 max-w-full space-y-4">

      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-3xl font-bold text-ink uppercase tracking-tighter">{t('analytics_title')}</h1>
          <p className="text-base text-ink-3 font-semibold uppercase tracking-tight opacity-80">
            {t('analytics_desc')}
            {lastRef && <span className="ml-3 opacity-50">· {lastRef.toLocaleTimeString()}</span>}
          </p>
        </div>
        <div className="flex gap-3">
          <button onClick={fetchAll} disabled={loading}
            className="flex items-center gap-2 px-5 py-2.5 text-sm rounded-xl bg-bg-4 hover:bg-bg-5 border border-border text-ink-2 hover:text-ink disabled:opacity-50 font-bold uppercase tracking-tight transition-all shadow-md active:scale-95">
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''}/>{t('refresh')}
          </button>
          <button onClick={() => setShowReset(true)}
            className="flex items-center gap-2 px-5 py-2.5 text-sm rounded-xl bg-danger/10 hover:bg-danger/20 border border-danger/30 text-danger font-bold uppercase tracking-tight transition-all shadow-md active:scale-95">
            <Trash2 size={16}/>{t('reset')}
          </button>
        </div>
      </div>

      {resetMsg && (
        <div className="flex items-center gap-2 p-3 bg-success/10 border border-success/30 rounded-xl text-xs text-success">
          <CheckCircle2 size={14}/>{resetMsg}
        </div>
      )}

      {cleanMsg && (
        <div className="flex items-center gap-2 p-3 bg-accent/10 border border-accent/30 rounded-xl text-xs text-accent">
          <CheckCircle2 size={14}/>{cleanMsg}
        </div>
      )}

      {/* ── Stat Cards ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard label={t('total_messages')}   value={(stats.total_messages||0).toLocaleString()} icon={MessageSquare} colorClass="bg-accent"  sub={`${stats.total_sessions||0} sesi`}/>
        <StatCard label={t('total_tokens')}   value={totalTok.toLocaleString()}                  icon={Zap}           colorClass="bg-warn"   sub={`$${totalCost.toFixed(4)}`}/>
        <StatCard label={t('rag_docs')}   value={stats.total_docs||0}                        icon={HardDrive}     colorClass="bg-success" sub="terindeks"/>
        <StatCard label={t('server_uptime')} value={system?.uptime || '—'}                      icon={Clock}         colorClass="bg-pink"/>
      </div>

      {/* ── System Resources ── */}
      <div className="bg-bg-3 border border-border rounded-2xl overflow-hidden shadow-lg">
        <div className="flex items-center justify-between px-5 py-4 border-b-2 border-border bg-bg-2/30">
          <div className="flex items-center gap-3">
            <Activity size={20} className="text-accent-2"/>
            <span className="text-lg font-bold text-ink uppercase tracking-tight">{t('system_resources')}</span>
            <span className="text-xs text-ink-3 bg-bg-4 px-3 py-1 rounded-full font-bold uppercase tracking-widest border border-border/30 shadow-inner ml-2">{t('realtime_desc')}</span>
          </div>
          {system && (
            <button onClick={() => setShowCores(!showCores)}
              className="text-xs text-ink-3 hover:text-accent-2 flex items-center gap-2 font-bold uppercase tracking-widest transition-all p-2 rounded-lg hover:bg-bg-4">
              {showCores ? <ChevronUp size={16}/> : <ChevronDown size={16}/>}
              {t('per_core')}
            </button>
          )}
        </div>

        <div className="p-4">
          {sysErr ? (
            <PsutilInstallGuide onRetry={fetchSystem} />
          ) : !system ? (
            <div className="flex items-center justify-center h-20 text-xs text-ink-3 gap-2">
              <RefreshCw size={13} className="animate-spin"/>{t('loading_system_data')}
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
                <div className="bg-bg-4 border border-border/20 rounded-2xl p-4 space-y-3 shadow-inner">
                  <div className="flex items-center gap-3 mb-1">
                    <Cpu size={18} className="text-accent-2"/>
                    <span className="text-base font-bold text-ink uppercase tracking-tight">CPU</span>
                    <span className="ml-auto text-sm font-mono text-accent-2 font-bold">{system.cpu.percent}%</span>
                  </div>
                  <Bar pct={system.cpu.percent} color="bg-accent"/>
                  <div className="grid grid-cols-2 gap-2 text-xs text-ink-3 font-semibold uppercase tracking-tight">
                    <span>Logical: <b className="text-ink font-bold">{system.cpu.count}</b></span>
                    <span>Physical: <b className="text-ink font-bold">{system.cpu.count_phys||'—'}</b></span>
                    <span>Frekuensi: <b className="text-ink font-bold">{system.cpu.freq_mhz||0} MHz</b></span>
                  </div>
                  {showCores && <CpuCores cores={system.cpu.per_core || []}/>}
                </div>

                <div className="bg-bg-4 border border-border/20 rounded-2xl p-4 space-y-3 shadow-inner">
                  <div className="flex items-center gap-3 mb-1">
                    <MemoryStick size={18} className="text-success"/>
                    <span className="text-base font-bold text-ink uppercase tracking-tight">Memori RAM</span>
                    <span className="ml-auto text-sm font-mono text-success font-bold">{system.memory.percent}%</span>
                  </div>
                  <Bar pct={system.memory.percent} color="bg-success"/>
                  <div className="grid grid-cols-2 gap-2 text-xs text-ink-3 font-semibold uppercase tracking-tight">
                    <span>Digunakan: <b className="text-ink font-bold">{system.memory.used_mb} MB</b></span>
                    <span>Tersedia: <b className="text-ink font-bold">{system.memory.free_mb} MB</b></span>
                    <span>Total: <b className="text-ink font-bold">{system.memory.total_mb} MB</b></span>
                    {system.memory.cached_mb > 0 && <span>Cache: <b className="text-ink font-bold">{system.memory.cached_mb} MB</b></span>}
                  </div>
                </div>

                <div className="bg-bg-4 border border-border/20 rounded-2xl p-4 space-y-3 shadow-inner">
                  <div className="flex items-center gap-3 mb-1">
                    <HardDrive size={18} className="text-warn"/>
                    <span className="text-base font-bold text-ink uppercase tracking-tight">Penyimpanan</span>
                    <span className="ml-auto text-sm font-mono text-warn font-bold">{system.disk.percent}%</span>
                  </div>
                  <Bar pct={system.disk.percent} color="bg-warn"/>
                  <div className="grid grid-cols-2 gap-2 text-xs text-ink-3 font-semibold uppercase tracking-tight">
                    <span>Digunakan: <b className="text-ink font-bold">{system.disk.used_gb} GB</b></span>
                    <span>Tersedia: <b className="text-ink font-bold">{system.disk.free_gb} GB</b></span>
                    <span>Total: <b className="text-ink font-bold">{system.disk.total_gb} GB</b></span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Media Management */}
      <div className="bg-bg-3 border border-border rounded-2xl p-6 shadow-lg">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between mb-5">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <FolderOpen size={20} className="text-accent"/>
              <span className="text-lg font-bold text-ink uppercase tracking-tight">{t('media_management')}</span>
            </div>
            <div className="text-xs text-ink-3 font-bold uppercase tracking-widest opacity-60">
              {mediaFiles.length} {t('total_files')} · {t('total_size')} {formatBytes(mediaFiles.reduce((sum, file) => sum + (file.size_bytes || 0), 0))}
            </div>
          </div>
          <div className="flex gap-3">
            <button onClick={fetchMedia} disabled={mediaLoading} className="text-sm text-accent hover:text-accent-2 disabled:opacity-50 font-bold uppercase tracking-tight transition-all">
              {mediaLoading ? t('processing') : t('refresh_list')}
            </button>
            {mediaFiles.length > 0 && (
              <button 
                onClick={deleteAllMediaFiles} 
                disabled={mediaLoading}
                className="text-xs px-4 py-2 rounded-xl bg-danger/10 hover:bg-danger/20 text-danger font-bold uppercase tracking-widest disabled:opacity-50 transition-all border border-danger/20 shadow-sm"
              >
                {t('delete_all')}
              </button>
            )}
          </div>
        </div>
        {mediaFiles.length > 0 ? (
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {mediaFiles.map((file) => (
              <div key={file.filename} className="flex items-center justify-between p-4 bg-bg-4 rounded-2xl border border-border/50 hover:border-accent/30 hover:bg-bg-5 transition-all shadow-sm group">
                <div className="flex-1 min-w-0">
                  <div className="text-base font-semibold text-ink truncate">{file.filename}</div>
                  <div className="text-xs text-ink-3 font-bold uppercase tracking-tight opacity-70 mt-0.5">
                    {(file.size_bytes / 1024).toFixed(1)} KB • {new Date(file.modified * 1000).toLocaleDateString('id-ID', { dateStyle: 'medium' })}
                  </div>
                </div>
                <button
                  onClick={() => deleteMediaFile(file.filename)}
                  className="ml-3 p-2 text-danger hover:bg-danger/10 rounded-xl transition-all opacity-0 group-hover:opacity-100"
                  title="Hapus file"
                >
                  <Trash2 size={18} />
                </button>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-ink-3">
            <FolderOpen size={24} className="mx-auto mb-2 opacity-50" />
            <p className="text-sm">Tidak ada file media</p>
          </div>
        )}
      </div>

      {storage && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {storage.components.map(comp => (
            <div key={comp.id} className="bg-bg-4 border border-border rounded-2xl p-5 space-y-3 shadow-md hover:border-accent/30 transition-all group">
              <div className="flex items-center justify-between">
                <span className="text-2xl group-hover:scale-110 transition-transform">{comp.icon}</span>
                <span className="text-base font-mono font-bold text-ink bg-bg-2 px-2 py-1 rounded-lg border border-border/50 shadow-inner">{comp.size}</span>
              </div>
              <div className="text-base font-bold text-ink uppercase tracking-tight">{comp.name}</div>
              <div className="text-xs text-ink-3 font-semibold uppercase tracking-tight opacity-70 leading-relaxed">{comp.desc}</div>
              {comp.can_clean && (
                <button 
                  onClick={() => handleCleanStorage(comp.id)}
                  disabled={cleaning[comp.id]}
                  className="mt-3 text-xs text-accent hover:text-accent-2 disabled:opacity-50 font-bold uppercase tracking-widest transition-all p-2 rounded-lg hover:bg-bg-3 border border-border/30 w-full text-center"
                >
                  {cleaning[comp.id] ? 'Sedang membersihkan...' : 'Bersihkan Storage'}
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* ── Healing & Snapshots ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Self-Healing Engine */}
        <div className="bg-bg-3 border border-border rounded-2xl overflow-hidden flex flex-col shadow-lg">
          <div className="px-5 py-4 border-b-2 border-border bg-bg-2/30 space-y-4">
            <div className="flex items-center gap-3">
              <ShieldAlert size={20} className="text-success"/>
              <span className="text-base font-bold text-ink uppercase tracking-tight">{t('self_healing_title')}</span>
              {healingStatus && (
                <span className={clsx("ml-auto text-xs px-3 py-1 rounded-full font-bold tracking-widest border shadow-sm", 
                  healingStatus.running ? "bg-success/10 text-success border-success/30" : "bg-danger/10 text-danger border-danger/30"
                )}>
                  {healingStatus.running ? "ACTIVE" : "STOPPED"}
                </span>
              )}
            </div>
            
            <div className="flex flex-wrap items-center gap-3">
              <button 
                onClick={handleTriggerHealing}
                disabled={triggerLoading}
                className="flex-1 flex items-center justify-center gap-2 text-xs px-3 py-2.5 rounded-xl bg-accent/10 hover:bg-accent/20 text-accent font-bold uppercase tracking-widest border border-accent/30 disabled:opacity-50 transition-all shadow-sm active:scale-95"
              >
                <Activity size={14} className={triggerLoading ? "animate-spin" : ""}/>
                {triggerLoading ? 'Checking...' : 'Check Status'}
              </button>
              
              <button 
                onClick={handleTestTelegram}
                disabled={telegramLoading}
                className="flex-1 flex items-center justify-center gap-2 text-xs px-3 py-2.5 rounded-xl bg-blue-500/10 hover:bg-blue-500/20 text-blue-500 font-bold uppercase tracking-widest border border-blue-500/30 disabled:opacity-50 transition-all shadow-sm active:scale-95"
              >
                <Monitor size={14} className={telegramLoading ? "animate-spin" : ""}/>
                {telegramLoading ? 'Sending...' : 'Test Bot'}
              </button>
            </div>

            {telegramMsg && (
              <div className={clsx("text-xs p-2 rounded font-medium", telegramMsg.ok ? "bg-success/10 text-success" : "bg-danger/10 text-danger")}>
                {telegramMsg.text}
              </div>
            )}
          </div>
          
          <div className="p-3 max-h-96 overflow-y-auto space-y-2 flex-1 scrollbar-thin">
            {healingEvents.length > 0 ? (
              healingEvents.map((ev, i) => (
                <div key={i} className="p-4 rounded-2xl bg-bg-4 border border-border/40 hover:border-success/30 transition-all shadow-sm">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold text-accent-2 uppercase tracking-widest">{ev.issue_type?.toUpperCase()}</span>
                    <span className="text-[11px] text-ink-3 font-semibold uppercase tracking-tight opacity-60">{new Date(ev.timestamp * 1000).toLocaleString('id-ID', { dateStyle: 'short', timeStyle: 'short' })}</span>
                  </div>
                  <div className="text-sm text-ink-2 mb-2 font-semibold leading-relaxed">{ev.description}</div>
                  <div className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-widest">
                    <CheckCircle2 size={14} className={ev.success ? "text-success" : "text-danger"}/>
                    <span className="text-ink-3 opacity-60">Action:</span>
                    <span className={clsx("font-bold", ev.success ? "text-success" : "text-danger")}>{ev.action_taken}</span>
                  </div>
                </div>
              ))
            ) : (
              <div className="py-10 text-center text-[11px] text-ink-3">Belum ada aktivitas self-healing</div>
            )}
          </div>
        </div>

        {/* AI Snapshots (Git) */}
        <div className="bg-bg-3 border border-border rounded-2xl overflow-hidden flex flex-col shadow-lg">
          <div className="flex items-center gap-3 px-5 py-4 border-b-2 border-border bg-bg-2/30">
            <RotateCcw size={20} className="text-accent"/>
            <span className="text-base font-bold text-ink uppercase tracking-tight">{t('rollback_title')}</span>
            <button 
              onClick={handleRollback}
              disabled={rollbackLoading || snapshots.length === 0}
              className="ml-auto text-xs px-3 py-2 rounded-xl bg-accent/10 hover:bg-accent/20 text-accent font-bold uppercase tracking-widest border border-accent/30 disabled:opacity-40 transition-all shadow-sm active:scale-95"
            >
              {rollbackLoading ? 'Rolling back...' : 'Rollback'}
            </button>
          </div>
          <div className="p-3 max-h-96 overflow-y-auto space-y-2 flex-1 scrollbar-thin">
            {snapshots.length > 0 ? (
              snapshots.map((s, i) => (
                <div key={i} className="p-4 rounded-2xl bg-bg-4 border border-border/40 hover:border-accent/30 transition-all group shadow-sm">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-mono text-accent-2 font-bold border border-accent/20 px-1.5 py-0.5 rounded-lg bg-bg-2 shadow-inner">{s.hash?.slice(0, 7)}</span>
                    <span className="text-[11px] text-ink-3 font-semibold uppercase tracking-tight opacity-60">{s.time}</span>
                  </div>
                  <div className="text-sm text-ink font-bold leading-relaxed truncate" title={s.message}>{s.message}</div>
                </div>
              ))
            ) : (
              <div className="py-10 text-center text-[11px] text-ink-3">Belum ada snapshot (Save Point)</div>
            )}
          </div>
        </div>
      </div>

      {showReset && <ResetModal onClose={() => setShowReset(false)} onConfirm={handleReset} />}
    </div>
  )
}
