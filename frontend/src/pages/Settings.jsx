import { useState, useEffect, useRef } from 'react'
import { api } from '../hooks/useApi'
import { copyToClipboard } from "../utils/clipboard"
import toast from 'react-hot-toast'
import CloudflareWizard from '../components/CloudflareWizard'
import {
  Save, RefreshCw, RotateCcw, Globe, Shield,
  Play, Square, Copy, Check, ExternalLink, Download,
  Eye, EyeOff, ChevronDown, ChevronUp,
  Wifi, WifiOff, Terminal, CheckCircle2, XCircle, Zap,
  Plus, Trash2, Star, AlertTriangle, Info, ArrowRight, Wand2, Cpu,
} from 'lucide-react'
import clsx from 'clsx'

const sApi = {
  get:           () => api.get('/settings/'),
  saveApp:       (d) => api.post('/settings/app', d),
  saveTunnel:    (d) => api.post('/settings/tunnel', d),
  tunnelStatus:  () => api.get('/settings/tunnel/status'),
  startTunnel:   () => api.post('/settings/tunnel/start'),
  stopTunnel:    () => api.post('/settings/tunnel/stop'),
  tunnelUrl:     () => api.get('/settings/tunnel/url'),
  tunnelLogs:    () => api.get('/settings/tunnel/logs'),
  svcStatus:     () => api.get('/settings/tunnel/service-status'),
  svcControl:    (a) => api.post('/settings/tunnel/service-control', { action: a }),
  setupService:  () => api.post('/settings/tunnel/setup-service'),
  changeAdmin:   (d) => api.post('/settings/change-admin', d),
  restart:       () => api.post('/settings/restart'),
  installCf:     () => api.post('/settings/install-cloudflared'),
  getDomains:    () => api.get('/settings/domains'),
  addDomain:     (d) => api.post('/settings/domains', d),
  deleteDomain:  (id) => api.delete(`/settings/domains/${id}`),
  activateDomain:(id) => api.post(`/settings/domains/${id}/activate`),
  saveAiCore:    (d) => api.post('/settings/ai-core', d),
}

// ── UI primitives ─────────────────────────────────────────────
function Label({ children }) {
  return <label className="block text-[10px] text-ink-3 mb-1.5 uppercase tracking-wider font-medium">{children}</label>
}
function Inp({ value, onChange, placeholder, mono, disabled, type="text" }) {
  return <input type={type} value={value} onChange={e=>onChange(e.target.value)} placeholder={placeholder} disabled={disabled}
    className={clsx('w-full bg-bg-2 border border-border-2 rounded-lg px-3 py-2 text-xs text-ink placeholder-ink-3 outline-none focus:border-accent transition-colors disabled:opacity-50', mono&&'font-mono')}/>
}
function SecretInp({ value, onChange, placeholder }) {
  const [show, setShow] = useState(false)
  return (
    <div className="relative">
      <input type={show?'text':'password'} value={value} onChange={e=>onChange(e.target.value)} placeholder={placeholder}
        className="w-full bg-bg-2 border border-border-2 rounded-lg px-3 py-2 pr-9 text-xs text-ink placeholder-ink-3 outline-none focus:border-accent font-mono"/>
      <button type="button" onClick={()=>setShow(!show)} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-ink-3 hover:text-ink">
        {show?<EyeOff size={13}/>:<Eye size={13}/>}
      </button>
    </div>
  )
}
function Sel({ value, onChange, options }) {
  return <select value={value} onChange={e=>onChange(e.target.value)}
    className="w-full bg-bg-2 border border-border-2 rounded-lg px-3 py-2 text-xs text-ink outline-none focus:border-accent cursor-pointer">
    {options.map(([v,l])=><option key={v} value={v}>{l}</option>)}
  </select>
}
function Toggle({ value, onChange, label }) {
  return (
    <label className="flex items-center gap-2.5 cursor-pointer select-none">
      <div onClick={()=>onChange(!value)} className={clsx('w-9 h-5 rounded-full relative transition-colors',value?'bg-accent':'bg-bg-4 border border-border-2')}>
        <div className={clsx('absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform',value?'translate-x-4':'translate-x-0.5')}/>
      </div>
      <span className="text-xs text-ink-2">{label}</span>
    </label>
  )
}
function Btn({ label, onClick, loading, variant='default', icon:Icon, full, small, disabled }) {
  return (
    <button onClick={onClick} disabled={loading||disabled}
      className={clsx('flex items-center justify-center gap-1.5 rounded-lg font-medium transition-all disabled:opacity-50',
        full?'w-full':'', small?'px-2.5 py-1.5 text-[10px]':'px-3 py-2 text-xs',
        variant==='primary'&&'bg-accent hover:bg-accent/80 text-white',
        variant==='success'&&'bg-success/10 hover:bg-success/20 border border-success/30 text-success',
        variant==='danger' &&'bg-danger/10  hover:bg-danger/20  border border-danger/30  text-danger',
        variant==='warn'   &&'bg-warn/10    hover:bg-warn/20    border border-warn/30    text-warn',
        variant==='default'&&'bg-bg-4 hover:bg-bg-5 border border-border text-ink-2 hover:text-ink',
      )}>
      {loading?<RefreshCw size={small?10:12} className="animate-spin"/>:Icon&&<Icon size={small?10:12}/>}
      {label}
    </button>
  )
}
function Section({ title, icon, children, defaultOpen=false, badge, className }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className={clsx("bg-bg-3 border border-border rounded-xl overflow-hidden", className)}>
      <div className="flex items-center gap-2.5 px-4 py-3 cursor-pointer hover:bg-bg-4 transition-colors border-b border-border" onClick={()=>setOpen(!open)}>
        <span className="text-base">{icon}</span>
        <span className="text-sm font-semibold text-ink flex-1">{title}</span>
        {badge && <span className={clsx('text-[10px] px-2 py-0.5 rounded-full font-medium', badge.color)}>{badge.text}</span>}
        {open?<ChevronUp size={14} className="text-ink-3"/>:<ChevronDown size={14} className="text-ink-3"/>}
      </div>
      {open&&<div className="p-4">{children}</div>}
    </div>
  )
}
function CopyBtn({ text }) {
  const [copied, setCopied] = useState(false)
  return (
    <button onClick={()=>{copyToClipboard(text);setCopied(true);setTimeout(()=>setCopied(false),2000)}}
      className="p-1 rounded hover:bg-bg-5 text-ink-3 hover:text-ink transition-colors flex-shrink-0">
      {copied?<Check size={12} className="text-success"/>:<Copy size={12}/>}
    </button>
  )
}
function Alert({ type='info', children }) {
  const styles = {
    info:  'bg-accent/8 border-accent/25 text-ink-2',
    warn:  'bg-warn/8 border-warn/25 text-warn',
    error: 'bg-danger/8 border-danger/25 text-danger',
    ok:    'bg-success/8 border-success/25 text-success',
  }
  const icons = { info: Info, warn: AlertTriangle, error: XCircle, ok: CheckCircle2 }
  const Icon = icons[type]
  return (
    <div className={clsx('flex items-start gap-2 p-3 rounded-xl border text-xs', styles[type])}>
      <Icon size={13} className="flex-shrink-0 mt-0.5"/>
      <div>{children}</div>
    </div>
  )
}

// ── Service Status Card ────────────────────────────────────────
function ServiceStatusCard({ onSetupDone }) {
  const [svc, setSvc]         = useState(null)
  const [loading, setLoading]  = useState(true)
  const [acting, setActing]    = useState(false)
  const [showLog, setShowLog]  = useState(false)
  const [setupLoading, setSetupLoading] = useState(false)

  const refresh = async () => {
    try { setSvc(await sApi.svcStatus()) } catch {}
    finally { setLoading(false) }
  }

  useEffect(() => { refresh(); const t = setInterval(refresh, 8000); return ()=>clearInterval(t) }, [])

  const control = async (action) => {
    setActing(true)
    try {
      await sApi.svcControl(action)
      toast.success(`cloudflared ${action} berhasil`)
      await new Promise(r=>setTimeout(r,1500))
      await refresh()
    } catch(e) { toast.error(e.message) }
    finally { setActing(false) }
  }

  const handleSetup = async () => {
    setSetupLoading(true)
    try {
      const r = await sApi.setupService()
      if (r.is_active) {
        toast.success(r.message)
      } else {
        toast(r.message, { icon: '⚠' })
      }
      await refresh()
      onSetupDone && onSetupDone()
    } catch(e) {
      const detail = e.response?.data?.detail || e.message || 'Gagal setup service'
      const msg = typeof detail === 'object' ? detail.message : detail
      const hint = typeof detail === 'object' ? detail.hint : ''
      toast.error(msg)
      if (hint) toast(hint, { icon: 'ℹ', duration: 6000 })
    }
    finally { setSetupLoading(false) }
  }

  if (loading) return <div className="text-xs text-ink-3 flex items-center gap-2"><RefreshCw size={12} className="animate-spin"/>Cek status service...</div>

  if (!svc?.service_exists) return (
    <div className="space-y-3">
      <Alert type="warn">
        <div className="font-semibold mb-1">cloudflared belum diinstall sebagai System Service</div>
        <div className="text-[10px] opacity-80">Klik tombol di bawah untuk setup otomatis (membutuhkan token tersimpan)</div>
      </Alert>
      <div className="flex gap-2">
        <Btn label={setupLoading ? 'Setup...' : '⚡ Setup Otomatis'} onClick={handleSetup} loading={setupLoading} variant="primary" full/>
      </div>
      <div className="text-[10px] text-ink-3">Atau manual: <code className="font-mono text-accent-2 bg-bg-4 px-1 rounded">bash scripts/setup-cloudflare-service.sh</code></div>
    </div>
  )

  return (
    <div className={clsx('rounded-xl border p-3.5 space-y-3', svc.is_active?'bg-success/5 border-success/25':'bg-bg-4 border-border')}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          {svc.is_active
            ? <><CheckCircle2 size={15} className="text-success"/><span className="text-sm font-semibold text-success">Service Aktif</span></>
            : <><XCircle size={15} className="text-danger"/><span className="text-sm font-semibold text-danger">Service Tidak Aktif</span></>}
          <span className={clsx('text-[10px] px-2 py-0.5 rounded-full font-medium', svc.is_enabled?'bg-success/10 text-success':'bg-bg-5 text-ink-3')}>
            {svc.is_enabled ? '● auto-start ON' : '○ auto-start OFF'}
          </span>
        </div>
        <div className="flex gap-1.5">
          {svc.is_active
            ? <Btn label="Stop" onClick={()=>control('stop')} loading={acting} variant="danger" icon={Square} small/>
            : <Btn label="Start" onClick={()=>control('start')} loading={acting} variant="success" icon={Play} small/>}
          <Btn label="Restart" onClick={()=>control('restart')} loading={acting} variant="default" icon={RotateCcw} small/>
          {!svc.is_enabled
            ? <Btn label="Enable" onClick={()=>control('enable')} loading={acting} variant="warn" small/>
            : <Btn label="Disable" onClick={()=>control('disable')} loading={acting} variant="default" small/>}
        </div>
      </div>
      <div>
        <button onClick={()=>setShowLog(!showLog)} className="text-[10px] text-ink-3 hover:text-ink flex items-center gap-1">
          <Terminal size={10}/> {showLog?'Sembunyikan':'Lihat'} log cloudflared ({svc.recent_log?.length||0} baris)
        </button>
        {showLog && svc.recent_log?.length > 0 && (
          <div className="mt-2 bg-bg-2 border border-border rounded-lg p-2.5 max-h-40 overflow-y-auto font-mono text-[10px] space-y-0.5">
            {svc.recent_log.map((l,i)=>(
              <div key={i} className={clsx(
                l.toLowerCase().includes('error')||l.toLowerCase().includes('failed')?'text-danger':
                l.toLowerCase().includes('warn')?'text-warn':
                l.toLowerCase().includes('connected')||l.toLowerCase().includes('registered')?'text-success':
                'text-ink-3'
              )}>{l}</div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Domain Manager ────────────────────────────────────────────
function DomainManager() {
  const [domains, setDomains]   = useState([])
  const [active, setActive]     = useState('')
  const [loading, setLoading]   = useState(true)
  const [showAdd, setShowAdd]   = useState(false)
  const [acting, setActing]     = useState({})
  // Form state
  const [sub, setSub]           = useState('')
  const [root, setRoot]         = useState('')
  const [port, setPort]         = useState('7860')
  const [path, setPath]         = useState('')
  const [notes, setNotes]       = useState('')

  const refresh = async () => {
    try {
      const r = await sApi.getDomains()
      setDomains(r.domains || [])
      setActive(r.active_domain || '')
    } catch {}
    finally { setLoading(false) }
  }

  useEffect(() => { refresh() }, [])

  const handleAdd = async () => {
    if (!root.trim()) { toast.error('Root domain wajib diisi'); return }
    setActing(a=>({...a, add: true}))
    try {
      await sApi.addDomain({ subdomain: sub.trim(), root_domain: root.trim(), local_port: port, local_path: path, notes })
      toast.success('Domain ditambahkan')
      setSub(''); setRoot(''); setPort('7860'); setPath(''); setNotes('')
      setShowAdd(false)
      await refresh()
    } catch(e) {
      const msg = typeof e.response?.data?.detail === 'string' ? e.response.data.detail : e.message
      toast.error(msg)
    }
    finally { setActing(a=>({...a, add: false})) }
  }

  const handleDelete = async (id) => {
    if (!confirm('Hapus domain ini?')) return
    setActing(a=>({...a, [id+'_del']: true}))
    try { await sApi.deleteDomain(id); toast.success('Domain dihapus'); await refresh() }
    catch(e) { toast.error(e.message) }
    finally { setActing(a=>({...a, [id+'_del']: false})) }
  }

  const handleActivate = async (id, domain) => {
    setActing(a=>({...a, [id+'_act']: true}))
    try {
      const r = await sApi.activateDomain(id)
      toast.success(r.message)
      if (r.webhook_url) toast(`📨 Webhook Telegram → ${r.webhook_url}`, {duration: 5000})
      setActive(domain)
      await refresh()
    } catch(e) { toast.error(e.message) }
    finally { setActing(a=>({...a, [id+'_act']: false})) }
  }

  const full = (d) => d.full_domain || (d.subdomain ? `${d.subdomain}.${d.root_domain}` : d.root_domain)

  return (
    <div className="space-y-3">
      {/* Active domain info */}
      {active && (
        <div className="flex items-center gap-2 p-2.5 bg-success/8 border border-success/20 rounded-xl">
          <Globe size={13} className="text-success flex-shrink-0"/>
          <div className="flex-1 min-w-0">
            <div className="text-[10px] text-success/70 mb-0.5">Domain Aktif</div>
            <code className="font-mono text-xs text-success truncate block">https://{active}</code>
          </div>
          <CopyBtn text={`https://${active}`}/>
          <a href={`https://${active}`} target="_blank" rel="noopener noreferrer" className="text-success hover:text-success/80">
            <ExternalLink size={12}/>
          </a>
        </div>
      )}

      {/* Domain list */}
      {loading ? (
        <div className="text-xs text-ink-3 flex items-center gap-2"><RefreshCw size={11} className="animate-spin"/>Memuat...</div>
      ) : domains.length === 0 ? (
        <div className="text-center py-6 text-ink-3 text-xs">
          <Globe size={24} className="mx-auto mb-2 opacity-30"/>
          Belum ada domain. Tambahkan domain pertama Anda.
        </div>
      ) : (
        <div className="space-y-2">
          {domains.map(d => (
            <div key={d.id} className={clsx('rounded-xl border p-3 transition-all', d.is_active ? 'bg-success/5 border-success/30' : 'bg-bg-4 border-border hover:border-border-2')}>
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    {d.is_active && <span className="text-[9px] bg-success/15 text-success px-1.5 py-0.5 rounded font-semibold">AKTIF</span>}
                    <code className="font-mono text-xs text-ink font-medium truncate">{full(d)}</code>
                  </div>
                  <div className="flex items-center gap-3 text-[10px] text-ink-3">
                    <span>→ {d.tunnel_type}://localhost:{d.local_port}{d.local_path ? '/'+d.local_path : ''}</span>
                    {d.notes && <span className="text-ink-3 truncate">· {d.notes}</span>}
                  </div>
                </div>
                <div className="flex items-center gap-1.5 flex-shrink-0">
                  {!d.is_active && (
                    <Btn label="Aktifkan" onClick={()=>handleActivate(d.id, full(d))} loading={acting[d.id+'_act']} variant="success" icon={Star} small/>
                  )}
                  <CopyBtn text={`https://${full(d)}`}/>
                  <button onClick={()=>handleDelete(d.id)} disabled={acting[d.id+'_del']}
                    className="p-1.5 rounded-lg text-ink-3 hover:text-danger hover:bg-danger/10 transition-colors disabled:opacity-50">
                    <Trash2 size={11}/>
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add form */}
      {showAdd ? (
        <div className="bg-bg-4 border border-border rounded-xl p-3.5 space-y-3">
          <div className="text-xs font-semibold text-ink mb-1">Tambah Domain Baru</div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <Label>Subdomain</Label>
              <Inp value={sub} onChange={setSub} placeholder="eai-super-assistant" mono/>
            </div>
            <div>
              <Label>Root Domain *</Label>
              <Inp value={root} onChange={setRoot} placeholder="kapanewonpengasih.my.id" mono/>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <Label>Port Lokal</Label>
              <Inp value={port} onChange={setPort} placeholder="7860" mono/>
            </div>
            <div>
              <Label>Path (opsional)</Label>
              <Inp value={path} onChange={setPath} placeholder="kosongkan untuk root" mono/>
            </div>
          </div>
          <div>
            <Label>Catatan (opsional)</Label>
            <Inp value={notes} onChange={setNotes} placeholder="Mis: domain utama, backup, dll"/>
          </div>
          {sub && root && (
            <div className="flex items-center gap-2 p-2 bg-bg-2 rounded-lg border border-border text-[10px] font-mono text-accent-2">
              <Globe size={10}/>
              Preview: https://{sub}.{root}{path ? '/'+path : ''}
              <ArrowRight size={10} className="text-ink-3"/>
              localhost:{port}
            </div>
          )}
          <div className="flex gap-2">
            <Btn label="Tambah Domain" onClick={handleAdd} loading={acting.add} variant="primary" icon={Plus}/>
            <Btn label="Batal" onClick={()=>setShowAdd(false)} variant="default"/>
          </div>
        </div>
      ) : (
        <Btn label="+ Tambah Domain" onClick={()=>setShowAdd(true)} variant="default" full/>
      )}

      {/* Setup guide */}
      <details className="group">
        <summary className="text-[10px] text-ink-3 cursor-pointer hover:text-ink-2 list-none flex items-center gap-1">
          <ChevronDown size={10} className="group-open:rotate-180 transition-transform"/>Cara konfigurasi hostname di Cloudflare Dashboard
        </summary>
        <div className="mt-2 bg-bg-2 rounded-xl p-3 border border-border text-[10px] text-ink-3 space-y-1.5">
          <div className="font-semibold text-ink-2 mb-2">Setelah domain ditambahkan dan diaktifkan:</div>
          <div>1. Buka <strong className="text-ink">Cloudflare Zero Trust Dashboard</strong> → Networks → Tunnels</div>
          <div>2. Klik tunnel → tab <strong className="text-ink">Public Hostname</strong> → <strong className="text-ink">Add a public hostname</strong></div>
          <div>3. Subdomain: isi sesuai subdomain yang didaftarkan</div>
          <div>4. Domain: pilih root domain Anda</div>
          <div>5. <strong className="text-ink">Path: kosongkan</strong> | Type: <code className="font-mono text-accent-2">HTTP</code> | URL: <code className="font-mono text-accent-2">localhost:7860</code></div>
          <div>6. Klik <strong className="text-ink">Save hostname</strong> → tunggu 30-60 detik</div>
          <div className="pt-1 text-warn">⚠ Path HARUS dikosongkan agar semua route bisa diakses</div>
        </div>
      </details>
    </div>
  )
}

// ── Tunnel Panel ──────────────────────────────────────────────
function TunnelPanel() {
  const [status, setStatus]       = useState({running:false,cloudflared_installed:false,quick_url:'',domain:'',has_token:false,recent_logs:[]})
  const [token, setToken]         = useState('')
  const [tunnelId, setTunnelId]   = useState('')
  const [autoStart, setAutoStart] = useState(true)
  const [load, setLoad]           = useState({})
  const [showLogs, setShowLogs]   = useState(false)
  const [logs, setLogs]           = useState([])
  const [errorDetail, setErrorDetail] = useState(null)
  const urlPollRef    = useRef(null)
  const statusPollRef = useRef(null)

  const setL = (k,v) => setLoad(l=>({...l,[k]:v}))

  const refreshStatus = async () => {
    try { const s = await sApi.tunnelStatus(); setStatus(s) } catch {}
  }

  useEffect(()=>{
    refreshStatus()
    statusPollRef.current = setInterval(refreshStatus, 5000)
    return ()=>{ clearInterval(statusPollRef.current); clearInterval(urlPollRef.current) }
  },[])

  const startUrlPolling = () => {
    let tries = 0
    urlPollRef.current = setInterval(async()=>{
      tries++
      try {
        const r = await sApi.tunnelUrl()
        if(r.url){ setStatus(s=>({...s,quick_url:r.url})); toast.success(`🌐 URL: ${r.url}`,{duration:8000}); clearInterval(urlPollRef.current) }
      } catch {}
      if(tries>25) clearInterval(urlPollRef.current)
    },3000)
  }

  const handleStart = async () => {
    setL('start',true)
    setErrorDetail(null)
    try {
      // Simpan config dulu jika ada perubahan
      const saveData = { provider: 'cloudflare', enabled: true, auto_start: autoStart }
      if (token && token !== '••••••••') saveData.cloudflare_token = token
      if (tunnelId) saveData.tunnel_id = tunnelId
      await sApi.saveTunnel(saveData)

      const r = await sApi.startTunnel()
      toast.success(r.message)
      await refreshStatus()
      if(r.mode==='quick') startUrlPolling()
    } catch(e) {
      const detail = e.response?.data?.detail || {}
      if (typeof detail === 'object') {
        setErrorDetail(detail)
        toast.error(detail.message || 'Gagal start tunnel')
      } else {
        toast.error(e.message||'Gagal start tunnel')
      }
    }
    finally { setL('start',false) }
  }

  const handleStop = async () => {
    setL('stop',true)
    setErrorDetail(null)
    clearInterval(urlPollRef.current)
    try { await sApi.stopTunnel(); toast('⏹ Tunnel dihentikan',{icon:'⏹'}); await refreshStatus() }
    catch(e){ toast.error(e.message) }
    finally { setL('stop',false) }
  }

  const handleSave = async () => {
    setL('save',true)
    try {
      const saveData = { provider: 'cloudflare', enabled: status.running, auto_start: autoStart }
      if (token && token !== '••••••••') saveData.cloudflare_token = token
      if (tunnelId) saveData.tunnel_id = tunnelId
      const r = await sApi.saveTunnel(saveData)
      toast.success(r.message)
      setToken('')
      await refreshStatus()
    } catch(e){ toast.error(e.message) }
    finally { setL('save',false) }
  }

  const fetchLogs = async () => {
    try { const r = await sApi.tunnelLogs(); setLogs(r.logs||[]); setShowLogs(true) } catch { toast.error('Gagal ambil logs') }
  }

  return (
    <div className="space-y-4">
      {/* ── System Service Status ──────────────────────────── */}
      <div>
        <div className="text-xs font-semibold text-ink mb-2 flex items-center gap-1.5">
          <Zap size={13} className="text-accent-2"/> Status cloudflared System Service
          <span className="text-[10px] font-normal text-ink-3">(Rekomendasi: gunakan ini agar otomatis berjalan)</span>
        </div>
        <ServiceStatusCard onSetupDone={refreshStatus}/>
      </div>

      <div className="border-t border-border pt-3">
        <div className="text-xs font-semibold text-ink mb-3 flex items-center gap-2">
          Kontrol Tunnel Manual
          <span className="text-[10px] font-normal text-ink-3">— gunakan jika system service tidak tersedia</span>
        </div>

        {/* Status bar */}
        <div className={clsx('rounded-xl border p-3 mb-3', status.running?'bg-success/5 border-success/25':'bg-bg-4 border-border')}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {status.running
                ? <><Wifi size={14} className="text-success"/><span className="text-xs font-semibold text-success">Aktif (Manual)</span></>
                : <><WifiOff size={14} className="text-ink-3"/><span className="text-xs text-ink-3">Tidak aktif</span></>}
              {status.cloudflared_installed
                ? <span className="text-[9px] bg-success/10 text-success px-1.5 py-0.5 rounded">cloudflared ✓</span>
                : <span className="text-[9px] bg-danger/10 text-danger px-1.5 py-0.5 rounded">cloudflared tidak ditemukan</span>}
              {status.has_token
                ? <span className="text-[9px] bg-accent/10 text-accent-2 px-1.5 py-0.5 rounded">Token ✓</span>
                : <span className="text-[9px] bg-warn/10 text-warn px-1.5 py-0.5 rounded">Quick tunnel mode</span>}
            </div>
            <div className="flex gap-1.5">
              {status.running
                ? <Btn label="Stop" onClick={handleStop} loading={load.stop} variant="danger" icon={Square} small/>
                : <Btn label="Start" onClick={handleStart} loading={load.start} variant="success" icon={Play} small
                    disabled={!status.cloudflared_installed}/>}
              {status.running && <Btn label="Logs" onClick={fetchLogs} variant="default" icon={Terminal} small/>}
            </div>
          </div>
          {status.running&&(status.quick_url||status.domain)&&(
            <div className="flex items-center gap-2 mt-2 p-2 bg-success/8 border border-success/20 rounded-lg">
              <Globe size={11} className="text-success flex-shrink-0"/>
              <code className="text-[10px] font-mono text-success flex-1 truncate">
                {status.quick_url || `https://${status.domain}`}
              </code>
              <CopyBtn text={status.quick_url || `https://${status.domain}`}/>
              <a href={status.quick_url || `https://${status.domain}`} target="_blank" rel="noopener noreferrer" className="text-success">
                <ExternalLink size={10}/>
              </a>
            </div>
          )}
        </div>

        {/* Error detail */}
        {errorDetail && (
          <div className="mb-3">
            <Alert type="error">
              <div className="font-semibold">{errorDetail.message}</div>
              {errorDetail.hint && <div className="mt-1 opacity-80">{errorDetail.hint}</div>}
              {errorDetail.error_log?.length > 0 && (
                <div className="mt-2 bg-bg-2/50 rounded p-2 font-mono text-[10px] space-y-0.5 max-h-28 overflow-y-auto">
                  {errorDetail.error_log.map((l,i)=><div key={i}>{l}</div>)}
                </div>
              )}
            </Alert>
          </div>
        )}

        {/* Token form */}
        <div className="space-y-2.5">
          <div>
            <Label>Tunnel Token {status.has_token && <span className="text-success normal-case">· tersimpan ✓</span>}</Label>
            <SecretInp value={token} onChange={setToken} placeholder={status.has_token ? "••••••••  (biarkan kosong untuk tetap pakai yang lama)" : "eyJhIjoiMTkzN... (dari Cloudflare Dashboard)"}/>
          </div>
          <div>
            <Label>Tunnel ID (opsional)</Label>
            <Inp value={tunnelId} onChange={setTunnelId} placeholder="0927e164-e2c0-... (dari Cloudflare Dashboard)" mono/>
          </div>
          <Toggle value={autoStart} onChange={setAutoStart} label="Auto-start saat server dimulai"/>
        </div>

        <div className="flex gap-2 mt-3">
          <Btn label="Simpan" onClick={handleSave} loading={load.save} variant="primary" icon={Save}/>
          {!status.cloudflared_installed && (
            <Btn label="Install cloudflared" onClick={async()=>{
              try { const r = await sApi.installCf(); toast(r.message, {icon:'ℹ'})} catch(e){toast.error(e.message)}
            }} variant="warn" icon={Download}/>
          )}
        </div>
      </div>

      {/* Logs */}
      {showLogs&&logs.length>0&&(
        <div className="bg-bg-2 border border-border rounded-xl overflow-hidden">
          <div className="flex items-center justify-between px-3 py-2 border-b border-border">
            <span className="text-xs font-medium text-ink flex items-center gap-1.5"><Terminal size={12}/>Log cloudflared</span>
            <button onClick={()=>setShowLogs(false)} className="text-ink-3 hover:text-ink text-xs">tutup</button>
          </div>
          <div className="p-3 max-h-44 overflow-y-auto font-mono text-[10px] text-ink-3 space-y-0.5">
            {logs.map((l,i)=>(
              <div key={i} className={clsx(
                l.toLowerCase().includes('error')||l.toLowerCase().includes('failed')?'text-danger':
                l.toLowerCase().includes('warn')?'text-warn':
                l.includes('trycloudflare.com')||l.toLowerCase().includes('connected')?'text-success':''
              )}>{l}</div>
            ))}
          </div>
        </div>
      )}

      {/* Terminal commands */}
      <details className="group">
        <summary className="text-[10px] text-ink-3 cursor-pointer hover:text-ink-2 list-none flex items-center gap-1">
          <ChevronDown size={10} className="group-open:rotate-180 transition-transform"/>Perintah terminal
        </summary>
        <div className="mt-2 bg-bg-2 rounded-xl p-3 border border-border space-y-2">
          {[
            ['Setup service', 'bash scripts/setup-cloudflare-service.sh'],
            ['Status service','sudo systemctl status cloudflared'],
            ['Log live',      'sudo journalctl -u cloudflared -f'],
            ['Restart',       'sudo systemctl restart cloudflared'],
            ['Uninstall',     'sudo cloudflared service uninstall'],
          ].map(([lbl,cmd])=>(
            <div key={lbl} className="flex items-center gap-2">
              <span className="text-[10px] text-ink-3 w-24 flex-shrink-0">{lbl}</span>
              <code className="text-[10px] font-mono text-accent-2 flex-1">{cmd}</code>
              <CopyBtn text={cmd}/>
            </div>
          ))}
        </div>
      </details>
    </div>
  )
}

// ── Tunnel Tabbed (Wizard + Manual) ──────────────────────────
function TunnelTabbed({ settings }) {
  const [tab, setTab] = useState(() => {
    // Jika belum ada tunnel_token, tampilkan wizard dulu
    const env = settings?.tunnel
    return (!env?.has_token) ? 'wizard' : 'manual'
  })
  return (
    <div className="space-y-3">
      {/* Tab switcher */}
      <div className="flex gap-1 bg-bg-4 rounded-xl p-1 border border-border">
        <button onClick={()=>setTab('wizard')}
          className={clsx('flex-1 flex items-center justify-center gap-1.5 rounded-lg py-2 text-xs font-medium transition-all',
            tab==='wizard' ? 'bg-accent text-white shadow' : 'text-ink-3 hover:text-ink')}>
          <Wand2 size={12}/>
          Setup Wizard
          {!settings?.tunnel?.has_token && (
            <span className="ml-1 text-[9px] bg-white/20 px-1.5 py-0.5 rounded-full">Mulai di sini</span>
          )}
        </button>
        <button onClick={()=>setTab('manual')}
          className={clsx('flex-1 flex items-center justify-center gap-1.5 rounded-lg py-2 text-xs font-medium transition-all',
            tab==='manual' ? 'bg-bg-2 text-ink shadow' : 'text-ink-3 hover:text-ink')}>
          <Terminal size={12}/>
          Kontrol Manual
        </button>
      </div>

      {/* Tab content */}
      {tab === 'wizard' ? (
        <CloudflareWizard onClose={()=>window.location.reload()}/>
      ) : (
        <TunnelPanel/>
      )}
    </div>
  )
}


// ── Main ──────────────────────────────────────────────────────
export default function SettingsPage() {
  const [settings,   setSettings]   = useState(null)
  const [loading,    setLoading]    = useState(true)
  const [saving,     setSaving]     = useState({})
  const [restarting, setRestarting] = useState(false)
  const [appName,    setAppName]    = useState('')
  const [appPort,    setAppPort]    = useState('')
  const [logLevel,   setLogLevel]   = useState('INFO')
  const [debug,      setDebug]      = useState(false)
  const [newPass,    setNewPass]    = useState('')
  const [newUser,    setNewUser]    = useState('')
  const [systemPrompt, setSystemPrompt] = useState('')

  const load = async () => {
    try {
      const s = await sApi.get()
      setSettings(s)
      setAppName(s.app?.name||'AI SUPER ASSISTANT')
      setAppPort(s.app?.port||'7860')
      setLogLevel(s.app?.log_level||'INFO')
      setDebug(s.app?.debug==='true')
      setSystemPrompt(s.ai_core?.system_prompt || '')
    } catch {}
    finally { setLoading(false) }
  }
  useEffect(()=>{ load() },[])

  const saveApp = async () => {
    setSaving(s=>({...s,app:true}))
    try { const r = await sApi.saveApp({name:appName,port:appPort,log_level:logLevel,debug:String(debug)}); toast.success(`✓ ${r.message}`) }
    catch(e){ toast.error(e.message) }
    finally { setSaving(s=>({...s,app:false})) }
  }
  const saveAdmin = async () => {
    if(!newPass&&!newUser){ toast.error('Isi minimal satu field'); return }
    setSaving(s=>({...s,admin:true}))
    try { await sApi.changeAdmin({new_password:newPass,new_username:newUser||undefined}); toast.success('✓ Kredensial diperbarui'); setNewPass(''); setNewUser('') }
    catch(e){ toast.error(e.message) }
    finally { setSaving(s=>({...s,admin:false})) }
  }
  const saveAiCore = async () => {
    setSaving(s=>({...s,aiCore:true}))
    try { await sApi.saveAiCore({system_prompt: systemPrompt}); toast.success('✓ System Prompt Global disimpan') }
    catch(e){ toast.error(e.message) }
    finally { setSaving(s=>({...s,aiCore:false})) }
  }
  const restart = async () => {
    if(!confirm('Restart AI SUPER ASSISTANT server?')) return
    setRestarting(true)
    try { await sApi.restart(); toast.loading('Restarting...',{duration:4000}); await new Promise(r=>setTimeout(r,4500)); toast.success('✓ Server restart selesai!'); await load() }
    catch(e){ toast.error(e.message) }
    finally { setRestarting(false) }
  }

  if(loading) return <div className="p-6 text-sm text-ink-3 flex items-center gap-2"><RefreshCw size={14} className="animate-spin"/>Memuat...</div>

  return (
    <div className="p-4 md:p-6 w-full">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-lg font-bold text-ink">Pengaturan</h1>
          <p className="text-xs text-ink-3 mt-0.5">Server, Cloudflare Tunnel, Domain, Akun Admin</p>
        </div>
        <Btn label={restarting?'Restarting...':'Restart Server'} onClick={restart} loading={restarting} variant="danger" icon={RotateCcw}/>
      </div>
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">

        <Section title="Cloudflare Tunnel" icon="☁" className="xl:col-span-2" defaultOpen={false}
          badge={settings?.tunnel_status?.running
            ? {text:'Aktif', color:'bg-success/10 text-success'}
            : settings?.tunnel_status?.cloudflared_installed
              ? {text:'Terpasang', color:'bg-bg-5 text-ink-3'}
              : {text:'Belum Setup', color:'bg-warn/10 text-warn'}}>
          <TunnelTabbed settings={settings}/>
        </Section>

        <Section title="AI Core (Global System Prompt)" icon="🧠" className="xl:col-span-2" defaultOpen={false}>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label>Global System Prompt (Core Engine)</Label>
              <div className="text-[10px] text-ink-3 italic">Mendukung format Markdown</div>
            </div>
            <textarea 
              value={systemPrompt} 
              onChange={e=>setSystemPrompt(e.target.value)}
              placeholder="Masukkan System Prompt Global di sini..."
              className="w-full h-80 bg-bg-2 border border-border-2 rounded-xl px-4 py-3 text-xs text-ink placeholder-ink-3 outline-none focus:border-accent font-mono leading-relaxed"
            />
            <div className="flex items-center justify-between p-3 bg-accent/5 border border-accent/20 rounded-xl">
              <div className="flex items-center gap-2 text-[10px] text-ink-2">
                <Info size={12} className="text-accent"/>
                <span>Prompt ini akan menjadi instruksi utama bagi seluruh orchestrator AI.</span>
              </div>
              <Btn label="Simpan Prompt" onClick={saveAiCore} loading={saving.aiCore} variant="primary" icon={Save}/>
            </div>
          </div>
        </Section>

        <Section title="Manajemen Domain" icon="🌐" className="xl:col-span-2" defaultOpen={false}
          badge={settings?.tunnel?.domain ? {text: settings.tunnel.domain, color:'bg-success/10 text-success'} : {text:'Belum dikonfigurasi', color:'bg-warn/10 text-warn'}}>
          <DomainManager/>
        </Section>

        <Section title="Pengaturan Aplikasi" icon="⚙" defaultOpen={false}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
            <div><Label>Nama Aplikasi</Label><Inp value={appName} onChange={setAppName} placeholder="AI SUPER ASSISTANT"/></div>
            <div><Label>Port</Label><Inp value={appPort} onChange={setAppPort} placeholder="7860" mono/></div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
            <div><Label>Log Level</Label><Sel value={logLevel} onChange={setLogLevel} options={[['DEBUG','DEBUG'],['INFO','INFO'],['WARNING','WARNING'],['ERROR','ERROR']]}/></div>
            <div className="flex items-end pb-1"><Toggle value={debug} onChange={setDebug} label="Debug Mode"/></div>
          </div>
          <div className="pt-3 border-t border-border flex items-center justify-between">
            <span className="text-[10px] text-ink-3">DB: <code className="font-mono text-accent-2">{settings?.database?.url_type}</code></span>
            <Btn label="Simpan" onClick={saveApp} loading={saving.app} variant="primary" icon={Save}/>
          </div>
        </Section>

        <Section title="Akun Admin" icon="🔐" defaultOpen={false}>
          <div className="mb-3 p-2.5 bg-bg-4 rounded-lg border border-border text-[10px] text-ink-3 flex items-center gap-2">
            <Shield size={12} className="text-accent-2"/>Username saat ini: <code className="font-mono text-accent-2">{settings?.admin?.username}</code>
          </div>
          <div className="space-y-3">
            <div><Label>Username Baru</Label><Inp value={newUser} onChange={setNewUser} placeholder="admin"/></div>
            <div><Label>Password Baru</Label><SecretInp value={newPass} onChange={setNewPass} placeholder="password baru..."/></div>
            <Btn label="Update" onClick={saveAdmin} loading={saving.admin} variant="primary" icon={Save}/>
          </div>
        </Section>

        <Section title="Info Sistem" icon="ℹ" defaultOpen={false}>
          <div className="grid grid-cols-2 gap-2">
            {[['Versi',settings?.app?.version||'1.0.0'],['Build',settings?.app?.build||'1'],['Port',settings?.app?.port||'7860'],['DB',settings?.database?.url_type||'sqlite'],
              ['Local',`http://localhost:${settings?.app?.port||'7860'}`],['Docs',`http://localhost:${settings?.app?.port||'7860'}/docs`]].map(([k,v])=>(
              <div key={k} className="flex items-center gap-2 p-2.5 bg-bg-4 rounded-lg border border-border">
                <span className="text-[10px] text-ink-3 w-10 flex-shrink-0">{k}</span>
                <code className="font-mono text-[10px] text-accent-2 flex-1 truncate">{v}</code>
                <CopyBtn text={v}/>
              </div>
            ))}
          </div>
        </Section>
      </div>
    </div>
  )
}
