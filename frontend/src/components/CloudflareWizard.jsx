/**
 * AI ORCHESTRATOR — Cloudflare Tunnel Setup Wizard
 */
import { useState, useEffect } from 'react'
import { api } from '../hooks/useApi'
import { copyToClipboard } from "../utils/clipboard"
import toast from 'react-hot-toast'
import {
  Key, Globe, Server, Zap, CheckCircle2, XCircle,
  RefreshCw, ChevronRight, ExternalLink, Copy, Check,
  ChevronDown, Eye, EyeOff, Play, Plus, AlertTriangle,
  Info, Rocket, Wifi, Terminal, RotateCcw, ArrowRight,
  Trash2, ShieldAlert,
} from 'lucide-react'
import clsx from 'clsx'

const wApi = {
  status:        () => api.get('/settings/wizard/status'),
  validateToken: (d) => api.post('/settings/wizard/validate-token', d),
  zones:         () => api.get('/settings/wizard/zones'),
  tunnels:       (d) => api.post('/settings/wizard/tunnels', d),
  createTunnel:  (d) => api.post('/settings/wizard/create-tunnel', d),
  useTunnel:     (d) => api.post('/settings/wizard/use-tunnel', d),
  configIngress: (d) => api.post('/settings/wizard/configure-ingress', d),
  deploy:        () => api.post('/settings/wizard/deploy'),
  reset:         (d) => api.post('/settings/wizard/reset', d),
}

// ── Helpers ───────────────────────────────────────────────────
function parseError(e) {
  // e.detail bisa string atau {code, message, hint}
  const d = e.detail
  if (!d) return { message: e.message || 'Terjadi kesalahan', hint: '' }
  if (typeof d === 'string') return { message: d, hint: '' }
  return { message: d.message || 'Terjadi kesalahan', hint: d.hint || '', code: d.code || '', log: d.error_log || [] }
}

// ── Primitives ────────────────────────────────────────────────
function CopyBtn({ text }) {
  const [ok, setOk] = useState(false)
  return (
    <button onClick={() => { copyToClipboard(text); setOk(true); setTimeout(() => setOk(false), 2000) }}
      className="p-1 rounded hover:bg-bg-5 text-ink-3 hover:text-ink transition-colors flex-shrink-0">
      {ok ? <Check size={11} className="text-success" /> : <Copy size={11} />}
    </button>
  )
}
function SecretInp({ value, onChange, placeholder, disabled }) {
  const [show, setShow] = useState(false)
  return (
    <div className="relative">
      <input type={show ? 'text' : 'password'} value={value} onChange={e => onChange(e.target.value)}
        placeholder={placeholder} disabled={disabled}
        className="w-full bg-bg-2 border border-border-2 rounded-lg px-3 py-2 pr-9 text-xs text-ink placeholder-ink-3 outline-none focus:border-accent font-mono disabled:opacity-50" />
      <button type="button" onClick={() => setShow(!show)} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-ink-3 hover:text-ink">
        {show ? <EyeOff size={13} /> : <Eye size={13} />}
      </button>
    </div>
  )
}
function Inp({ value, onChange, placeholder, mono, disabled }) {
  return (
    <input type="text" value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} disabled={disabled}
      className={clsx('w-full bg-bg-2 border border-border-2 rounded-lg px-3 py-2 text-xs text-ink placeholder-ink-3 outline-none focus:border-accent disabled:opacity-50', mono && 'font-mono')} />
  )
}
function Label({ children }) {
  return <label className="block text-[10px] text-ink-3 mb-1.5 uppercase tracking-wider font-medium">{children}</label>
}
function Btn({ label, onClick, loading, variant = 'default', icon: Icon, full, disabled, small }) {
  return (
    <button onClick={onClick} disabled={loading || disabled}
      className={clsx('flex items-center justify-center gap-1.5 rounded-lg font-medium transition-all disabled:opacity-50',
        full ? 'w-full' : '', small ? 'px-2.5 py-1.5 text-[10px]' : 'px-3 py-2.5 text-xs',
        variant === 'primary' && 'bg-accent hover:bg-accent/80 text-white',
        variant === 'success' && 'bg-success/10 hover:bg-success/20 border border-success/30 text-success',
        variant === 'danger'  && 'bg-danger/10 hover:bg-danger/20 border border-danger/30 text-danger',
        variant === 'warn'    && 'bg-warn/10 hover:bg-warn/20 border border-warn/30 text-warn',
        variant === 'default' && 'bg-bg-4 hover:bg-bg-5 border border-border text-ink-2 hover:text-ink',
      )}>
      {loading ? <RefreshCw size={12} className="animate-spin" /> : Icon && <Icon size={12} />}
      {label}
    </button>
  )
}
function ErrorBox({ error, onRetry }) {
  if (!error) return null
  const { message, hint, log } = error
  return (
    <div className="bg-danger/8 border border-danger/25 rounded-xl p-3 space-y-2 text-xs">
      <div className="flex items-start gap-2">
        <XCircle size={14} className="text-danger flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <div className="font-semibold text-danger">{message}</div>
          {hint && <div className="text-danger/80 mt-0.5 text-[10px]">{hint}</div>}
        </div>
        {onRetry && (
          <button onClick={onRetry} className="text-[10px] text-ink-3 hover:text-ink flex items-center gap-1 flex-shrink-0">
            <RotateCcw size={10} /> Coba lagi
          </button>
        )}
      </div>
      {log && log.length > 0 && (
        <div className="bg-bg-2 rounded-lg p-2 font-mono text-[10px] text-danger/70 space-y-0.5 max-h-24 overflow-y-auto">
          {log.map((l, i) => <div key={i}>{l}</div>)}
        </div>
      )}
    </div>
  )
}
function StepRow({ icon: Icon, label, done, active, onClick }) {
  return (
    <button onClick={onClick} className={clsx(
      'flex items-center gap-2 px-2 py-1.5 rounded-lg transition-all flex-1 min-w-0',
      active ? 'bg-bg-4' : 'hover:bg-bg-4/50',
    )}>
      <div className={clsx('w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0',
        done   ? 'bg-success text-white' :
        active ? 'bg-accent text-white ring-2 ring-accent/30' :
                 'bg-bg-5 text-ink-3 border border-border')}>
        {done ? <CheckCircle2 size={12} /> : <Icon size={11} />}
      </div>
      <span className={clsx('text-[10px] font-medium truncate hidden sm:block', active ? 'text-ink' : done ? 'text-success' : 'text-ink-3')}>
        {label}
      </span>
    </button>
  )
}
function DeployStepItem({ step }) {
  const colors = { ok: 'text-success', error: 'text-danger', warn: 'text-warn', running: 'text-ink-3' }
  const icons  = {
    ok:      <CheckCircle2 size={12} className="text-success flex-shrink-0" />,
    error:   <XCircle size={12} className="text-danger flex-shrink-0" />,
    warn:    <AlertTriangle size={12} className="text-warn flex-shrink-0" />,
    running: <RefreshCw size={12} className="text-ink-3 flex-shrink-0 animate-spin" />,
  }
  return (
    <div className={clsx('text-[10px] space-y-1', colors[step.status] || 'text-ink-3')}>
      <div className="flex items-center gap-1.5">{icons[step.status]}{step.msg}</div>
      {step.hint && <div className="ml-4 opacity-70">{step.hint}</div>}
      {step.log?.length > 0 && (
        <div className="ml-4 bg-bg-2 rounded p-1.5 font-mono space-y-0.5 max-h-20 overflow-y-auto">
          {step.log.map((l, i) => <div key={i}>{l}</div>)}
        </div>
      )}
    </div>
  )
}

// ── Step 1: API Token ─────────────────────────────────────────
function Step1({ onDone, alreadyDone }) {
  const [token, setToken]   = useState('')
  const [loading, setLoad]  = useState(false)
  const [error, setError]   = useState(null)
  const [done, setDone]     = useState(alreadyDone)

  const validate = async () => {
    if (!token.trim()) { toast.error('Paste API Token terlebih dahulu'); return }
    setLoad(true); setError(null)
    try {
      const r = await wApi.validateToken({ api_token: token.trim() })
      toast.success(r.message)
      setDone(true)
      onDone({ accounts: r.accounts || [], tokenName: r.token_name || '' })
    } catch (e) { setError(parseError(e)) }
    finally { setLoad(false) }
  }

  return (
    <div className="space-y-3">
      <div className="bg-bg-4 rounded-xl border border-border p-3 text-[10px] text-ink-3 space-y-2">
        <div className="font-semibold text-xs text-ink-2">Cara mendapat API Token Cloudflare:</div>
        {[
          ['1', <>Buka <a href="https://dash.cloudflare.com/profile/api-tokens" target="_blank" rel="noopener noreferrer" className="text-accent-2 hover:underline inline-flex items-center gap-0.5">Cloudflare → Profile → API Tokens <ExternalLink size={9}/></a></>],
          ['2', 'Klik "Create Token"'],
          ['3', <>Pilih template <strong className="text-ink">Edit zone DNS</strong>, lalu tambah izin:<br/><code className="font-mono text-accent-2">Account → Cloudflare Tunnel → Edit</code><br/><code className="font-mono text-accent-2">Zone → DNS → Edit</code></>],
          ['4', 'Klik "Continue to summary" → "Create Token"'],
          ['5', 'Copy token → paste di bawah'],
        ].map(([n, text]) => (
          <div key={n} className="flex items-start gap-2">
            <span className="text-accent-2 font-semibold w-3 flex-shrink-0">{n}.</span>
            <span>{text}</span>
          </div>
        ))}
      </div>

      {done ? (
        <div className="flex items-center justify-between p-3 bg-success/8 border border-success/25 rounded-xl">
          <div className="flex items-center gap-2 text-xs text-success">
            <CheckCircle2 size={14} />API Token valid dan tersimpan ✓
          </div>
          <Btn label="Ganti Token" onClick={() => setDone(false)} variant="default" small />
        </div>
      ) : (
        <div className="space-y-2">
          <Label>API Token</Label>
          <SecretInp value={token} onChange={setToken} placeholder="paste token di sini..." />
          <ErrorBox error={error} onRetry={() => setError(null)} />
          <Btn label="Validasi Token" onClick={validate} loading={loading} variant="primary" icon={Key} full />
        </div>
      )}
    </div>
  )
}

// ── Step 2: Pilih / Buat Tunnel ───────────────────────────────
function Step2({ accounts, savedAccountId, savedTunnelId, onDone }) {
  const [mode, setMode]           = useState('create')
  const [accountId, setAccountId] = useState(accounts[0]?.id || savedAccountId || '')
  const [name, setName]           = useState('ai-orchestrator')
  const [tunnels, setTunnels]     = useState([])
  const [selTunnel, setSelTunnel] = useState(savedTunnelId || '')
  const [loading, setLoad]        = useState(false)
  const [loadList, setLoadList]   = useState(false)
  const [error, setError]         = useState(null)
  const [result, setResult]       = useState(null)

  const fetchTunnels = async () => {
    if (!accountId) return
    setLoadList(true)
    try { const r = await wApi.tunnels({ account_id: accountId }); setTunnels(r.tunnels || []) }
    catch (e) { toast.error(parseError(e).message) }
    finally { setLoadList(false) }
  }

  useEffect(() => { if (mode === 'existing') fetchTunnels() }, [mode, accountId])

  const handleCreate = async () => {
    if (!name.trim()) { toast.error('Nama tunnel wajib diisi'); return }
    setLoad(true); setError(null)
    try {
      const r = await wApi.createTunnel({ account_id: accountId, tunnel_name: name.trim() })
      toast.success(r.message)
      setResult(r)
      onDone({ accountId, tunnelId: r.tunnel_id, tunnelName: r.tunnel_name })
    } catch (e) { setError(parseError(e)) }
    finally { setLoad(false) }
  }

  const handleUse = async () => {
    if (!selTunnel) { toast.error('Pilih tunnel'); return }
    setLoad(true); setError(null)
    try {
      const r = await wApi.useTunnel({ account_id: accountId, tunnel_id: selTunnel })
      toast.success(r.message)
      setResult(r)
      onDone({ accountId, tunnelId: r.tunnel_id, tunnelName: r.tunnel_name })
    } catch (e) { setError(parseError(e)) }
    finally { setLoad(false) }
  }

  if (result) return (
    <div className="space-y-3">
      <div className="p-3 bg-success/8 border border-success/25 rounded-xl space-y-1.5">
        <div className="flex items-center gap-2 text-xs text-success font-semibold"><CheckCircle2 size={14}/>Tunnel: {result.tunnel_name}</div>
        <div className="flex items-center gap-1.5 text-[10px] font-mono text-ink-3">
          <span className="text-ink-3">ID:</span>
          <span className="text-accent-2 flex-1 truncate">{result.tunnel_id}</span>
          <CopyBtn text={result.tunnel_id} />
        </div>
        <div className="text-[10px] text-success/70">Token tunnel tersimpan ke .env ✓</div>
      </div>
      <Btn label="Ganti Tunnel" onClick={() => setResult(null)} variant="default" small />
    </div>
  )

  return (
    <div className="space-y-3">
      {accounts.length > 1 && (
        <div>
          <Label>Akun Cloudflare</Label>
          <select value={accountId} onChange={e => setAccountId(e.target.value)}
            className="w-full bg-bg-2 border border-border-2 rounded-lg px-3 py-2 text-xs text-ink outline-none focus:border-accent">
            {accounts.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
          </select>
        </div>
      )}

      <div className="grid grid-cols-2 gap-2">
        {[
          { v: 'create', icon: '🆕', title: 'Buat Tunnel Baru', desc: 'Rekomendasi untuk setup pertama' },
          { v: 'existing', icon: '📋', title: 'Pakai Yang Ada', desc: 'Gunakan tunnel yang sudah dibuat' },
        ].map(opt => (
          <div key={opt.v} onClick={() => setMode(opt.v)}
            className={clsx('p-2.5 rounded-xl border cursor-pointer transition-all',
              mode === opt.v ? 'border-accent bg-accent/8' : 'border-border bg-bg-4 hover:border-border-2')}>
            <div className="text-xs font-semibold text-ink">{opt.icon} {opt.title}</div>
            <div className="text-[10px] text-ink-3 mt-0.5">{opt.desc}</div>
          </div>
        ))}
      </div>

      {mode === 'create' ? (
        <div className="space-y-2">
          <Label>Nama Tunnel</Label>
          <Inp value={name} onChange={setName} placeholder="ai-orchestrator" mono />
          <div className="text-[10px] text-ink-3">Nama unik untuk tunnel ini di Cloudflare Dashboard</div>
          <ErrorBox error={error} onRetry={() => setError(null)} />
          <Btn label="Buat Tunnel" onClick={handleCreate} loading={loading} variant="primary" icon={Plus} full />
        </div>
      ) : (
        <div className="space-y-2">
          {loadList ? (
            <div className="text-xs text-ink-3 flex items-center gap-2"><RefreshCw size={11} className="animate-spin" />Memuat...</div>
          ) : tunnels.length === 0 ? (
            <div className="p-2.5 bg-warn/8 border border-warn/25 rounded-xl text-xs text-warn">
              Belum ada tunnel. Gunakan mode "Buat Tunnel Baru".
            </div>
          ) : (
            <div className="space-y-1.5 max-h-48 overflow-y-auto">
              {tunnels.map(t => (
                <div key={t.id} onClick={() => setSelTunnel(t.id)}
                  className={clsx('p-2.5 rounded-xl border cursor-pointer transition-all',
                    selTunnel === t.id ? 'border-accent bg-accent/8' : 'border-border bg-bg-4 hover:border-border-2')}>
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-ink">{t.name}</span>
                    <span className={clsx('text-[9px] px-1.5 py-0.5 rounded-full',
                      t.status === 'healthy' ? 'bg-success/10 text-success' : 'bg-bg-5 text-ink-3')}>{t.status}</span>
                  </div>
                  <div className="text-[10px] text-ink-3 font-mono truncate mt-0.5">{t.id}</div>
                </div>
              ))}
            </div>
          )}
          <ErrorBox error={error} onRetry={() => setError(null)} />
          {tunnels.length > 0 && (
            <Btn label="Gunakan Tunnel Ini" onClick={handleUse} loading={loading}
              disabled={!selTunnel} variant="primary" icon={ChevronRight} full />
          )}
        </div>
      )}
    </div>
  )
}

// ── Step 3: Konfigurasi Domain + DNS ──────────────────────────
function Step3({ accountId, tunnelId, savedDomain, onDone }) {
  const [zones, setZones]     = useState([])
  const [zoneId, setZoneId]   = useState('')
  const [sub, setSub]         = useState(() => {
    if (!savedDomain) return ''
    const parts = savedDomain.split('.')
    return parts.length > 2 ? parts[0] : ''
  })
  const [port, setPort]       = useState('7860')
  const [loading, setLoad]    = useState(false)
  const [loadZones, setLoadZ] = useState(true)
  const [error, setError]     = useState(null)
  const [result, setResult]   = useState(null)

  useEffect(() => {
    wApi.zones().then(r => {
      setZones(r.zones || [])
      if (r.zones?.[0]) setZoneId(r.zones[0].id)
    }).catch(e => setError(parseError(e))).finally(() => setLoadZ(false))
  }, [])

  const zone    = zones.find(z => z.id === zoneId)
  const preview = sub.trim() ? `${sub.trim()}.${zone?.name || ''}` : (zone?.name || '')

  const handleConfigure = async () => {
    if (!zoneId || !zone) { toast.error('Pilih domain terlebih dahulu'); return }
    setLoad(true); setError(null)
    try {
      const r = await wApi.configIngress({
        account_id:  accountId,
        tunnel_id:   tunnelId,
        zone_id:     zoneId,
        subdomain:   sub.trim(),
        root_domain: zone.name,
        local_port:  port,
      })
      r.success ? toast.success(r.message) : toast(r.message, { icon: '⚠' })
      setResult(r)
      onDone({ fullDomain: r.full_domain })
    } catch (e) { setError(parseError(e)) }
    finally { setLoad(false) }
  }

  if (result) return (
    <div className="space-y-3">
      <div className={clsx('p-3 rounded-xl border space-y-2',
        result.success ? 'bg-success/8 border-success/25' : 'bg-warn/8 border-warn/25')}>
        <div className={clsx('flex items-center gap-2 text-xs font-semibold', result.success ? 'text-success' : 'text-warn')}>
          {result.success ? <CheckCircle2 size={14}/> : <AlertTriangle size={14}/>}{result.message}
        </div>
        {result.steps_done.map((s, i) => <div key={i} className="text-[10px] text-success/80">{s}</div>)}
        {result.steps_failed.map((s, i) => <div key={i} className="text-[10px] text-danger">{s}</div>)}
      </div>
      <div className="flex items-center gap-2 p-2.5 bg-bg-4 border border-border rounded-xl">
        <Globe size={11} className="text-accent-2" />
        <code className="font-mono text-xs text-accent-2 flex-1">https://{result.full_domain}</code>
        <CopyBtn text={`https://${result.full_domain}`} />
      </div>
      {result.steps_failed.length > 0 && (
        <Btn label="Coba Lagi" onClick={() => setResult(null)} variant="warn" icon={RotateCcw} small />
      )}
    </div>
  )

  return (
    <div className="space-y-3">
      <div className="bg-accent/8 border border-accent/20 rounded-xl p-2.5 text-[10px] text-ink-2 flex items-start gap-2">
        <Info size={12} className="text-accent-2 flex-shrink-0 mt-0.5" />
        AI ORCHESTRATOR akan otomatis membuat DNS record CNAME dan mengkonfigurasi routing di tunnel Cloudflare Anda.
      </div>

      {loadZones ? (
        <div className="text-xs text-ink-3 flex items-center gap-2"><RefreshCw size={11} className="animate-spin" />Memuat domain...</div>
      ) : error && zones.length === 0 ? (
        <ErrorBox error={error} onRetry={() => { setError(null); setLoadZ(true); wApi.zones().then(r => { setZones(r.zones||[]); if(r.zones?.[0]) setZoneId(r.zones[0].id) }).catch(e=>setError(parseError(e))).finally(()=>setLoadZ(false)) }} />
      ) : (
        <>
          <div>
            <Label>Domain Anda (dari Cloudflare)</Label>
            <select value={zoneId} onChange={e => setZoneId(e.target.value)}
              className="w-full bg-bg-2 border border-border-2 rounded-lg px-3 py-2 text-xs text-ink outline-none focus:border-accent">
              {zones.map(z => <option key={z.id} value={z.id}>{z.name}</option>)}
            </select>
          </div>

          <div>
            <Label>Subdomain (opsional)</Label>
            <Inp value={sub} onChange={setSub} placeholder="ai-orchestrator  ← subdomain.domain.com" mono />
            <div className="text-[10px] text-ink-3 mt-1">
              Kosongkan untuk pakai apex: <code className="font-mono">{zone?.name}</code>
            </div>
          </div>

          <div>
            <Label>Port Lokal AI ORCHESTRATOR</Label>
            <Inp value={port} onChange={setPort} placeholder="7860" mono />
          </div>

          {preview && (
            <div className="p-2.5 bg-bg-4 border border-border rounded-xl text-[10px] font-mono space-y-1">
              <div className="text-ink-3">Yang akan dibuat:</div>
              <div className="flex items-center gap-2 text-ink-2">
                <span className="text-accent-2">DNS CNAME</span>
                <ArrowRight size={9} className="text-ink-3" />
                <span>{preview} → {tunnelId?.substring(0,8)}....cfargotunnel.com</span>
              </div>
              <div className="flex items-center gap-2 text-ink-2">
                <span className="text-accent-2">Route</span>
                <ArrowRight size={9} className="text-ink-3" />
                <span>https://{preview} → localhost:{port}</span>
              </div>
            </div>
          )}

          <ErrorBox error={error} onRetry={() => setError(null)} />
          <Btn label="Buat DNS & Konfigurasi Tunnel" onClick={handleConfigure}
            loading={loading} disabled={!zoneId} variant="primary" icon={Globe} full />
        </>
      )}
    </div>
  )
}

// ── Step 4: Deploy ────────────────────────────────────────────
function Step4({ hasSudo, onDone }) {
  const [loading, setLoad]   = useState(false)
  const [result, setResult]  = useState(null)
  const [error, setError]    = useState(null)

  const handleDeploy = async () => {
    setLoad(true); setError(null)
    try {
      const r = await wApi.deploy()
      setResult(r)
      if (r.success) { toast.success(r.message); onDone() }
      else toast(r.message, { icon: '⚠' })
    } catch (e) {
      setError(parseError(e))
    }
    finally { setLoad(false) }
  }

  if (result) return (
    <div className="space-y-3">
      <div className={clsx('p-3 rounded-xl border',
        result.success ? 'bg-success/8 border-success/25' : 'bg-warn/8 border-warn/25')}>
        <div className={clsx('flex items-center gap-2 text-sm font-semibold mb-2',
          result.success ? 'text-success' : 'text-warn')}>
          {result.success ? <CheckCircle2 size={15}/> : <AlertTriangle size={15}/>}
          {result.message}
        </div>
        {result.tunnel_domain && result.success && (
          <a href={`https://${result.tunnel_domain}`} target="_blank" rel="noopener noreferrer"
            className="text-[10px] font-mono text-success/80 hover:text-success flex items-center gap-1 underline">
            https://{result.tunnel_domain} <ExternalLink size={9}/>
          </a>
        )}
      </div>

      <div className="space-y-2">
        {(result.steps || []).map((s, i) => <DeployStepItem key={i} step={s} />)}
      </div>

      {!result.success && (
        <div className="space-y-2">
          <div className="text-[10px] text-ink-3 p-2.5 bg-bg-4 rounded-xl border border-border">
            <div className="font-semibold text-ink-2 mb-1">Coba install manual:</div>
            <code className="font-mono text-accent-2">sudo bash scripts/setup-cloudflare-service.sh</code>
            <div className="mt-1">Atau cek log: <code className="font-mono text-accent-2">sudo journalctl -u cloudflared -n 30</code></div>
          </div>
          <Btn label="Coba Lagi" onClick={() => setResult(null)} variant="warn" icon={RotateCcw} />
        </div>
      )}
    </div>
  )

  return (
    <div className="space-y-3">
      <div className="bg-accent/8 border border-accent/20 rounded-xl p-2.5 text-[10px] text-ink-2 flex items-start gap-2">
        <Info size={12} className="text-accent-2 flex-shrink-0 mt-0.5" />
        Langkah terakhir: install cloudflared dan jalankan sebagai system service agar tunnel otomatis aktif setiap server dinyalakan.
      </div>

      {!hasSudo && (
        <div className="bg-warn/8 border border-warn/25 rounded-xl p-2.5 text-[10px] text-warn flex items-start gap-2">
          <AlertTriangle size={12} className="flex-shrink-0 mt-0.5" />
          <div>
            <div className="font-semibold">sudo memerlukan password</div>
            <div className="opacity-80 mt-0.5">Deploy mungkin memerlukan izin. Jika gagal, jalankan manual di terminal:<br/>
              <code className="font-mono text-warn">sudo bash scripts/setup-cloudflare-service.sh</code>
            </div>
          </div>
        </div>
      )}

      <div className="bg-bg-4 border border-border rounded-xl p-3 space-y-1.5 text-[10px] text-ink-3">
        <div className="font-semibold text-ink-2 text-xs mb-2">Yang akan dilakukan:</div>
        {[
          'Install cloudflared (jika belum ada)',
          'Install cloudflared sebagai systemd service',
          'Enable auto-start saat server boot',
          'Start tunnel sekarang',
          'Verifikasi koneksi',
        ].map((item, i) => (
          <div key={i} className="flex items-center gap-2">
            <CheckCircle2 size={11} className="text-accent-2 flex-shrink-0" />{item}
          </div>
        ))}
      </div>

      <ErrorBox error={error} onRetry={() => setError(null)} />

      <Btn label={loading ? 'Deploying... (15-30 detik)' : '🚀 Deploy Tunnel Sekarang'}
        onClick={handleDeploy} loading={loading} variant="primary" full />

      {loading && (
        <div className="text-center text-[10px] text-ink-3 animate-pulse">
          Sedang proses... jangan tutup halaman ini
        </div>
      )}
    </div>
  )
}

// ── Reset Confirmation Dialog ─────────────────────────────────
function ResetDialog({ onClose, onConfirm }) {
  const [deleteTunnel, setDeleteTunnel] = useState(false)
  const [loading, setLoading]           = useState(false)
  const [result, setResult]             = useState(null)
  const [confirmText, setConfirmText]   = useState('')

  const canConfirm = confirmText.toLowerCase() === 'reset'

  const handleConfirm = async () => {
    if (!canConfirm) return
    setLoading(true)
    try {
      const r = await wApi.reset({ stop_service: true, delete_cf_tunnel: deleteTunnel })
      setResult(r)
    } catch (e) {
      setResult({ success: false, steps: [], message: parseError(e).message })
    }
    finally { setLoading(false) }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{backdropFilter:'blur(4px)',background:'rgba(0,0,0,0.6)'}}>
      <div className="bg-bg-3 border border-danger/30 rounded-2xl w-full max-w-sm shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="bg-danger/8 border-b border-danger/20 px-4 py-3 flex items-center gap-2.5">
          <ShieldAlert size={18} className="text-danger flex-shrink-0"/>
          <div>
            <div className="text-sm font-semibold text-danger">Reset Konfigurasi Cloudflare</div>
            <div className="text-[10px] text-danger/70">Tindakan ini tidak bisa dibatalkan</div>
          </div>
        </div>

        <div className="p-4 space-y-3">
          {!result ? (
            <>
              {/* Yang akan dihapus */}
              <div className="bg-bg-4 border border-border rounded-xl p-3 text-[10px] text-ink-3 space-y-1.5">
                <div className="font-semibold text-ink-2 text-xs mb-2">Yang akan dihapus:</div>
                {[
                  'API Token Cloudflare dari .env',
                  'Tunnel Token & Tunnel ID dari .env',
                  'Domain konfigurasi dari .env',
                  'Daftar domain lokal (.domains.json)',
                  'cloudflared systemd service (stop + uninstall)',
                ].map((item, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <XCircle size={10} className="text-danger flex-shrink-0"/>{item}
                  </div>
                ))}
              </div>

              {/* Opsi hapus tunnel di CF */}
              <label className="flex items-start gap-2.5 p-2.5 rounded-xl border border-border bg-bg-4 cursor-pointer hover:border-danger/30 transition-colors">
                <input type="checkbox" checked={deleteTunnel} onChange={e => setDeleteTunnel(e.target.checked)}
                  className="mt-0.5 accent-danger flex-shrink-0"/>
                <div>
                  <div className="text-xs font-medium text-ink">Hapus tunnel di Cloudflare Dashboard</div>
                  <div className="text-[10px] text-ink-3 mt-0.5">
                    Menghapus tunnel secara permanen dari akun Cloudflare.<br/>
                    <span className="text-warn">⚠ Tidak dapat dipulihkan!</span>
                  </div>
                </div>
              </label>

              {/* Konfirmasi ketik "reset" */}
              <div>
                <div className="text-[10px] text-ink-3 mb-1.5">
                  Ketik <code className="font-mono bg-bg-4 px-1 rounded text-danger">reset</code> untuk mengkonfirmasi:
                </div>
                <input
                  type="text"
                  value={confirmText}
                  onChange={e => setConfirmText(e.target.value)}
                  placeholder="ketik: reset"
                  className="w-full bg-bg-2 border border-border-2 rounded-lg px-3 py-2 text-xs text-ink placeholder-ink-3 outline-none focus:border-danger font-mono"
                  onKeyDown={e => { if (e.key === 'Enter' && canConfirm) handleConfirm() }}
                />
              </div>

              <div className="flex gap-2 pt-1">
                <button onClick={onClose}
                  className="flex-1 px-3 py-2 text-xs rounded-lg bg-bg-4 hover:bg-bg-5 border border-border text-ink-2 hover:text-ink font-medium transition-colors">
                  Batal
                </button>
                <button onClick={handleConfirm} disabled={!canConfirm || loading}
                  className="flex-1 px-3 py-2 text-xs rounded-lg bg-danger hover:bg-danger/80 text-white font-medium transition-all disabled:opacity-40 flex items-center justify-center gap-1.5">
                  {loading ? <><RefreshCw size={11} className="animate-spin"/>Mereset...</> : <><Trash2 size={11}/>Reset Sekarang</>}
                </button>
              </div>
            </>
          ) : (
            /* Hasil reset */
            <div className="space-y-3">
              <div className={clsx('flex items-center gap-2 text-sm font-semibold',
                result.success ? 'text-success' : 'text-danger')}>
                {result.success ? <CheckCircle2 size={16}/> : <XCircle size={16}/>}
                {result.message}
              </div>
              <div className="space-y-1.5">
                {(result.steps || []).map((s, i) => (
                  <div key={i} className={clsx('flex items-start gap-1.5 text-[10px]',
                    s.status === 'ok'   ? 'text-success' :
                    s.status === 'warn' ? 'text-warn' : 'text-danger')}>
                    {s.status === 'ok' ? <CheckCircle2 size={11} className="flex-shrink-0 mt-0.5"/> :
                     s.status === 'warn' ? <AlertTriangle size={11} className="flex-shrink-0 mt-0.5"/> :
                     <XCircle size={11} className="flex-shrink-0 mt-0.5"/>}
                    {s.msg}
                  </div>
                ))}
              </div>
              <button onClick={() => { onConfirm(); onClose() }}
                className="w-full px-3 py-2 text-xs rounded-lg bg-bg-4 hover:bg-bg-5 border border-border text-ink font-medium transition-colors">
                Tutup & Refresh
              </button>
            </div>
          )}
        </div>
      </div>
      {showReset && (
        <ResetDialog
          onClose={() => setShowReset(false)}
          onConfirm={() => {
            setStatus(null); setStep(1); setFinished(false)
            setAccounts([]); setAccountId(''); setTunnelId('')
            // reload wizard status
            wApi.status().then(setStatus).catch(() => {})
          }}
        />
      )}
    </div>
  )
}


// ── Main Wizard ───────────────────────────────────────────────
export default function CloudflareWizard({ onClose }) {
  const [status, setStatus]     = useState(null)
  const [loading, setLoading]   = useState(true)
  const [step, setStep]         = useState(1)
  const [finished, setFinished] = useState(false)
  const [showReset, setShowReset] = useState(false)

  // Collected state
  const [accounts, setAccounts]   = useState([])
  const [accountId, setAccountId] = useState('')
  const [tunnelId, setTunnelId]   = useState('')

  useEffect(() => {
    wApi.status().then(s => {
      setStatus(s)
      // Jika service aktif (termasuk install via terminal), langsung tampilkan layar sukses
      if (s.service_active) { setFinished(true); return }
      // Lanjutkan wizard dari step yang sesuai
      if (s.has_domain && s.has_tunnel_token) { setStep(4); setAccountId(s.account_id); setTunnelId(s.tunnel_id); return }
      if (s.has_tunnel_token) { setStep(3); setAccountId(s.account_id); setTunnelId(s.tunnel_id); return }
      if (s.has_api_token) { setStep(2); return }
    }).catch(() => {}).finally(() => setLoading(false))
  }, [])


  const STEPS = [
    { n: 1, label: 'API Token',  icon: Key    },
    { n: 2, label: 'Tunnel',     icon: Server },
    { n: 3, label: 'Domain/DNS', icon: Globe  },
    { n: 4, label: 'Deploy',     icon: Rocket },
  ]

  const isDone = (n) => {
    if (!status) return false
    if (n === 1) return status.has_api_token
    if (n === 2) return status.has_tunnel_token
    if (n === 3) return status.has_domain
    if (n === 4) return status.service_active
    return false
  }

  if (loading) return (
    <div className="flex items-center justify-center py-10 text-xs text-ink-3 gap-2">
      <RefreshCw size={14} className="animate-spin" />Memeriksa status konfigurasi...
    </div>
  )

  if (finished) return (
    <div className="space-y-4 py-2 text-center">
      <div className="text-5xl mb-2">🎉</div>
      <div className="text-sm font-semibold text-ink">Cloudflare Tunnel Aktif!</div>
      <div className="text-xs text-ink-3">
        {status?.installed_via_terminal
          ? 'Tunnel terdeteksi berjalan (instalasi via terminal)'
          : 'AI ORCHESTRATOR dapat diakses dari internet'}
      </div>

      {/* Badge status tunnel via terminal */}
      {status?.installed_via_terminal && (
        <div className="flex items-center justify-center gap-2 p-2.5 bg-accent/8 border border-accent/25 rounded-xl text-[10px] text-accent-2">
          <Terminal size={12} />
          Tunnel dikelola oleh sistem (bukan via wizard). Untuk manajemen penuh, gunakan "Setup via Wizard" di bawah.
        </div>
      )}

      {/* Domain */}
      {status?.tunnel_domain ? (
        <div className="flex items-center justify-center gap-2 p-3 bg-success/8 border border-success/25 rounded-xl">
          <Wifi size={14} className="text-success" />
          <code className="font-mono text-sm text-success">{status.tunnel_domain}</code>
          <CopyBtn text={`https://${status.tunnel_domain}`} />
          <a href={`https://${status.tunnel_domain}`} target="_blank" rel="noopener noreferrer" className="text-success"><ExternalLink size={13}/></a>
        </div>
      ) : (
        <div className="flex items-center justify-center gap-2 p-3 bg-success/8 border border-success/25 rounded-xl text-xs text-success">
          <Wifi size={14} />
          Tunnel aktif. Domain tidak terdeteksi otomatis — cek di Cloudflare Dashboard.
        </div>
      )}

      {/* Status grid */}
      <div className="grid grid-cols-2 gap-2 text-[10px] text-left">
        {[
          ['cloudflared', status?.cloudflared_installed],
          ['Service', status?.service_active],
          ['API Token', status?.has_api_token],
          ['Domain', status?.has_domain],
        ].map(([l, ok]) => (
          <div key={l} className={clsx('flex items-center gap-1.5 p-2 rounded-lg border',
            ok ? 'bg-success/8 border-success/20 text-success' : 'bg-bg-4 border-border text-ink-3')}>
            {ok ? <CheckCircle2 size={11}/> : <XCircle size={11}/>}{l}
          </div>
        ))}
      </div>

      <div className="flex gap-2 flex-wrap justify-center">
        {status?.installed_via_terminal
          ? <Btn label="Setup via Wizard (Opsional)" onClick={() => { setFinished(false); setStep(1) }} variant="default" icon={Key} />
          : <Btn label="Setup Ulang" onClick={() => { setFinished(false); setStep(1) }} variant="default" />
        }
        <Btn label="Reset Semua" onClick={() => setShowReset(true)} variant="danger" icon={Trash2} />
        {onClose && <Btn label="Tutup" onClick={() => { onClose(); window.location.reload() }} variant="primary" />}
      </div>
    </div>
  )


  return (
    <div className="space-y-4">
      {/* Step bar */}
      <div className="flex items-center">
        {STEPS.map((s, i) => (
          <div key={s.n} className="flex items-center flex-1 min-w-0">
            <StepRow icon={s.icon} label={s.label} done={isDone(s.n)} active={step === s.n}
              onClick={() => { if (isDone(s.n) || s.n <= step) setStep(s.n) }} />
            {i < STEPS.length - 1 && (
              <div className={clsx('h-0.5 w-3 flex-shrink-0', isDone(s.n) ? 'bg-success' : 'bg-border')} />
            )}
          </div>
        ))}
      </div>

      {/* Content */}
      <div className="min-h-24">
        {step === 1 && (
          <Step1 alreadyDone={status?.has_api_token} onDone={(d) => {
            setAccounts(d.accounts || [])
            if (d.accounts?.[0]) setAccountId(d.accounts[0].id)
            setStatus(s => ({ ...s, has_api_token: true }))
            setStep(2)
          }} />
        )}
        {step === 2 && (
          <Step2 accounts={accounts} savedAccountId={accountId} savedTunnelId={tunnelId}
            onDone={(d) => {
              setAccountId(d.accountId); setTunnelId(d.tunnelId)
              setStatus(s => ({ ...s, has_tunnel_token: true, tunnel_id: d.tunnelId, account_id: d.accountId }))
              setStep(3)
            }} />
        )}
        {step === 3 && (
          <Step3 accountId={accountId || status?.account_id} tunnelId={tunnelId || status?.tunnel_id}
            savedDomain={status?.tunnel_domain}
            onDone={(d) => {
              setStatus(s => ({ ...s, has_domain: true, tunnel_domain: d.fullDomain }))
              setStep(4)
            }} />
        )}
        {step === 4 && (
          <Step4 hasSudo={status?.has_sudo !== false}
            onDone={() => {
              setStatus(s => ({ ...s, service_active: true }))
              setFinished(true)
            }} />
        )}
      </div>

      {/* Reset button */}
      {(status?.has_api_token || status?.has_tunnel_token || status?.has_domain) && (
        <div className="flex justify-end">
          <button onClick={() => setShowReset(true)}
            className="flex items-center gap-1 text-[10px] text-ink-3 hover:text-danger transition-colors px-2 py-1 rounded-lg hover:bg-danger/8">
            <Trash2 size={10}/>Reset semua settingan
          </button>
        </div>
      )}

      {/* Nav */}
      <div className="flex items-center justify-between pt-1 border-t border-border">
        <button onClick={() => setStep(s => Math.max(1, s - 1))} disabled={step === 1}
          className="text-xs text-ink-3 hover:text-ink disabled:opacity-30 flex items-center gap-1">
          ← Kembali
        </button>
        <span className="text-[10px] text-ink-3">Langkah {step} dari 4</span>
        {step < 4 && (
          <button onClick={() => setStep(s => Math.min(4, s + 1))}
            className="text-xs text-accent-2 hover:text-accent flex items-center gap-1">
            Lewati <ChevronRight size={12} />
          </button>
        )}
      </div>
      {showReset && (
        <ResetDialog
          onClose={() => setShowReset(false)}
          onConfirm={() => {
            setStatus(null); setStep(1); setFinished(false)
            setAccounts([]); setAccountId(''); setTunnelId('')
            // reload wizard status
            wApi.status().then(setStatus).catch(() => {})
          }}
        />
      )}
    </div>
  )
}
