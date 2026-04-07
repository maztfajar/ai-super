import { useState, useEffect, useRef } from 'react'
import { api } from '../hooks/useApi'
import { RefreshCw, Filter, Download, Activity, AlertTriangle, Info, Bug } from 'lucide-react'
import clsx from 'clsx'

const LEVELS = ['ALL','INFO','WARN','ERROR','DEBUG']
const LEVEL_STYLE = {
  INFO:  'text-accent-2 bg-accent/10',
  WARN:  'text-warn bg-warn/10',
  ERROR: 'text-danger bg-danger/10',
  DEBUG: 'text-ink-3 bg-bg-5',
}

export default function Logs() {
  const [logs,    setLogs]    = useState([])
  const [loading, setLoading] = useState(false)
  const [level,   setLevel]   = useState('ALL')
  const [auto,    setAuto]    = useState(false)
  const [hint,    setHint]    = useState('')
  const bottomRef = useRef()
  const scrollContainerRef = useRef()
  const timerRef  = useRef()

  const load = async () => {
    setLoading(true)
    try {
      const r = await api.recentLogs(200, level === 'ALL' ? '' : level)
      setLogs(r.logs || [])
      if (r.hint) setHint(r.hint)
    } catch(e) {
      // Fallback: gunakan health endpoint untuk cek server
      setHint('Tidak dapat memuat log. Pastikan server berjalan.')
    } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [level])

  useEffect(() => {
    if (auto) {
      timerRef.current = setInterval(load, 5000)
    } else {
      clearInterval(timerRef.current)
    }
    return () => clearInterval(timerRef.current)
  }, [auto, level])

  useEffect(() => {
    if (auto && scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight
    }
  }, [logs, auto])

  const download = () => {
    const txt = logs.map(l => l.text).join('\n')
    const a = document.createElement('a')
    a.href = URL.createObjectURL(new Blob([txt], { type: 'text/plain' }))
    a.download = 'ai-super-assistant-logs.txt'
    a.click()
  }

  const counts = logs.reduce((acc, l) => {
    acc[l.level] = (acc[l.level] || 0) + 1; return acc
  }, {})

  return (
    <div className="p-4 md:p-6 w-full space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-lg font-bold text-ink flex items-center gap-2">
            <Activity size={18} className="text-accent-2"/>System Logs
          </h1>
          <p className="text-xs text-ink-3 mt-0.5">{logs.length} entri · 200 log terbaru</p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {/* Level stats */}
          {Object.entries(counts).map(([lvl, n]) => (
            <span key={lvl} className={clsx('text-[10px] px-2 py-1 rounded-lg font-mono font-semibold', LEVEL_STYLE[lvl] || 'text-ink-3 bg-bg-4')}>
              {lvl}: {n}
            </span>
          ))}
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-2 flex-wrap">
        {LEVELS.map(l => (
          <button key={l} onClick={() => setLevel(l)}
            className={clsx('text-xs px-3 py-1.5 rounded-lg font-medium transition-colors',
              level === l ? 'bg-accent text-white' : 'bg-bg-4 text-ink-3 hover:text-ink hover:bg-bg-5')}>
            {l}
          </button>
        ))}
        <div className="flex items-center gap-1.5 ml-auto">
          <label className="flex items-center gap-1.5 text-xs text-ink-3 cursor-pointer">
            <div onClick={() => setAuto(!auto)}
              className={clsx('w-8 h-4 rounded-full relative transition-colors',
                auto ? 'bg-success' : 'bg-bg-5 border border-border')}>
              <div className={clsx('absolute top-0.5 w-3 h-3 rounded-full bg-white shadow transition-transform',
                auto ? 'translate-x-4' : 'translate-x-0.5')}/>
            </div>
            Auto-refresh
          </label>
          <button onClick={load} disabled={loading}
            className="p-1.5 rounded-lg bg-bg-4 hover:bg-bg-5 text-ink-3 hover:text-ink">
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''}/>
          </button>
          <button onClick={download} className="p-1.5 rounded-lg bg-bg-4 hover:bg-bg-5 text-ink-3 hover:text-ink">
            <Download size={13}/>
          </button>
        </div>
      </div>

      {/* Log viewer */}
      <div className="bg-bg-2 border border-border rounded-xl overflow-hidden">
        <div ref={scrollContainerRef} className="h-[60vh] overflow-y-auto font-mono text-[11px] p-3 space-y-0.5">
          {hint && (
            <div className="flex items-center gap-2 p-3 bg-warn/8 border border-warn/20 rounded-xl text-warn text-xs mb-3">
              <AlertTriangle size={13}/>
              {hint}
            </div>
          )}
          {logs.length === 0 && !loading ? (
            <div className="text-center py-12 text-ink-3">
              <Activity size={24} className="mx-auto mb-2 opacity-30"/>
              <div className="text-sm">Tidak ada log yang cocok</div>
              <div className="text-xs mt-1">Coba filter ALL atau ubah level</div>
            </div>
          ) : (
            logs.map((log, i) => (
              <div key={i} className={clsx('flex items-start gap-2 px-2 py-0.5 rounded hover:bg-bg-4/50',
                log.level === 'ERROR' && 'bg-danger/5')}>
                <span className={clsx('flex-shrink-0 text-[9px] px-1.5 py-0.5 rounded font-bold mt-0.5',
                  LEVEL_STYLE[log.level] || 'text-ink-3 bg-bg-4')}>
                  {log.level || 'INFO'}
                </span>
                <span className="text-ink-2 leading-relaxed break-all">{log.text}</span>
              </div>
            ))
          )}
          <div ref={bottomRef}/>
        </div>
      </div>
    </div>
  )
}
