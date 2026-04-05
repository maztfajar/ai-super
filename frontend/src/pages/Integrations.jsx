import { useState, useEffect, useRef } from 'react'
import { useModelsStore, useOrchestratorStore } from '../store'
import { api } from '../hooks/useApi'
import { copyToClipboard } from "../utils/clipboard"
import toast from 'react-hot-toast'
import {
  Save, RefreshCw, CheckCircle2, XCircle, Eye, EyeOff,
  RotateCcw, Send, AlertCircle, ChevronDown, ChevronUp,
  Play, Square, Wifi, WifiOff, Webhook, Plus, Trash2,
  Copy, Check, Code, Zap, Globe,
} from 'lucide-react'
import clsx from 'clsx'

const intApi = {
  status:          () => api.get('/integrations/status'),
  saveKey:         (p, f) => api.post('/integrations/save-key', { provider: p, fields: f }),
  reloadModels:    () => api.post('/integrations/reload-models'),
  restart:         () => api.post('/integrations/restart'),
  testTelegram:    () => api.post('/integrations/telegram/test'),
  testOllama:      () => api.post('/integrations/ollama/test'),
  testSumopod:     () => api.post('/integrations/sumopod/test'),
  pollingStatus:   () => api.get('/integrations/telegram/polling-status'),
  startPolling:    () => api.post('/integrations/telegram/start-polling'),
  stopPolling:     () => api.post('/integrations/telegram/stop-polling'),
  listWebhooks:    () => api.listWebhooks(),
  createWebhook:   (d) => api.createWebhook(d),
  updateWebhook:   (id, d) => api.updateWebhook(id, d),
  deleteWebhook:   (id) => api.deleteWebhook(id),
  testWebhook:     (id) => api.testWebhook(id),
  webhookTemplates:() => api.webhookTemplates(),
  // Custom model providers
  listCustomModels:     () => api.listCustomModels(),
  addCustomModel:       (d) => api.addCustomModel(d),
  deleteCustomModel:    (id) => api.deleteCustomModel(id),
  testCustomModel:      (id) => api.testCustomModel(id),
  testCustomConnection: (d) => api.testCustomConnection(d),
}

/**
 * Sync backend models (from useModelsStore) → orchestrator store (activeConfiguredModels).
 * Converts backend format {id, provider, display, status} into orchestrator format {id, name, provider}.
 */
function syncModelsToOrchestrator(models) {
  if (!models || !Array.isArray(models)) return
  const mapped = models.map(m => ({
    id: m.id,
    name: `🧠 ${m.display || m.id}`,
    provider: (m.provider || 'unknown').charAt(0).toUpperCase() + (m.provider || 'unknown').slice(1),
  }))
  useOrchestratorStore.getState().setActiveConfiguredModels(mapped)
}

// ── Primitives ────────────────────────────────────────────────
function Label({ children }) {
  return <label className="block text-[10px] text-ink-3 mb-1 uppercase tracking-wider font-medium">{children}</label>
}

function SecretInput({ label, value, onChange, placeholder, hint, disabled }) {
  const [show, setShow] = useState(false)
  return (
    <div>
      {label && <Label>{label}</Label>}
      <div className="relative">
        <input type={show ? 'text' : 'password'} value={value} onChange={e => onChange(e.target.value)}
          placeholder={placeholder} disabled={disabled}
          autoComplete="new-password"
          className="w-full bg-bg-2 border border-border-2 rounded-lg px-3 py-2 text-xs text-ink placeholder-ink-3 outline-none focus:border-accent pr-9 font-mono disabled:opacity-50"/>
        <button type="button" onClick={() => setShow(!show)}
          className="absolute right-2.5 top-1/2 -translate-y-1/2 text-ink-3 hover:text-ink">
          {show ? <EyeOff size={13}/> : <Eye size={13}/>}
        </button>
      </div>
      {hint && <p className="text-[10px] text-ink-3 mt-1">{hint}</p>}
    </div>
  )
}

function TextInput({ label, value, onChange, placeholder, hint, mono, disabled }) {
  return (
    <div>
      {label && <Label>{label}</Label>}
      <input type="text" value={value} onChange={e => onChange(e.target.value)}
        placeholder={placeholder} disabled={disabled}
        className={clsx('w-full bg-bg-2 border border-border-2 rounded-lg px-3 py-2 text-xs text-ink placeholder-ink-3 outline-none focus:border-accent disabled:opacity-50', mono && 'font-mono')}/>
      {hint && <p className="text-[10px] text-ink-3 mt-1">{hint}</p>}
    </div>
  )
}

function Textarea({ label, value, onChange, placeholder, hint, rows = 3 }) {
  return (
    <div>
      {label && <Label>{label}</Label>}
      <textarea value={value} onChange={e => onChange(e.target.value)}
        placeholder={placeholder} rows={rows}
        className="w-full bg-bg-2 border border-border-2 rounded-lg px-3 py-2 text-xs text-ink placeholder-ink-3 outline-none focus:border-accent font-mono resize-none"/>
      {hint && <p className="text-[10px] text-ink-3 mt-1">{hint}</p>}
    </div>
  )
}

function StatusBadge({ ok }) {
  return ok
    ? <span className="flex items-center gap-1 text-[10px] font-medium text-success bg-success/10 border border-success/20 px-2 py-0.5 rounded-full"><CheckCircle2 size={10}/>Aktif</span>
    : <span className="flex items-center gap-1 text-[10px] font-medium text-ink-3 bg-bg-4 border border-border px-2 py-0.5 rounded-full"><XCircle size={10}/>Belum Setup</span>
}

function Btn({ label, onClick, loading, variant = 'default', icon: Icon, small, disabled, full }) {
  return (
    <button onClick={onClick} disabled={loading || disabled}
      className={clsx('flex items-center justify-center gap-1.5 rounded-lg font-medium transition-all disabled:opacity-50',
        full ? 'w-full' : '',
        small ? 'px-2.5 py-1.5 text-[10px]' : 'px-3 py-2 text-xs',
        variant === 'primary' && 'bg-accent hover:bg-accent/80 text-white',
        variant === 'success' && 'bg-success/10 hover:bg-success/20 border border-success/30 text-success',
        variant === 'danger'  && 'bg-danger/10 hover:bg-danger/20 border border-danger/30 text-danger',
        variant === 'warn'    && 'bg-warn/10 hover:bg-warn/20 border border-warn/30 text-warn',
        variant === 'default' && 'bg-bg-4 hover:bg-bg-5 border border-border text-ink-2 hover:text-ink',
      )}>
      {loading ? <RefreshCw size={small ? 10 : 12} className="animate-spin"/> : Icon && <Icon size={small ? 10 : 12}/>}
      {label}
    </button>
  )
}

function CopyBtn({ text }) {
  const [ok, setOk] = useState(false)
  return (
    <button onClick={() => { copyToClipboard(text); setOk(true); setTimeout(() => setOk(false), 2000) }}
      className="p-1 rounded hover:bg-bg-5 text-ink-3 hover:text-ink transition-colors flex-shrink-0">
      {ok ? <Check size={11} className="text-success"/> : <Copy size={11}/>}
    </button>
  )
}

// ── Card collapsible ──────────────────────────────────────────
function Card({ icon, title, subtitle, configured, children }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="bg-bg-3 border border-border shadow-sm rounded-xl overflow-hidden transition-all duration-200">
      <button className="w-full flex items-center gap-3 px-4 py-3.5 hover:bg-bg-4 transition-colors"
        onClick={() => setOpen(!open)}>
        <div className="w-8 h-8 rounded-lg bg-bg-4 border border-border flex items-center justify-center text-lg flex-shrink-0">{icon}</div>
        <div className="flex-1 min-w-0 text-left">
          <div className="text-sm font-semibold text-ink">{title}</div>
          <div className="text-[10px] text-ink-3">{subtitle}</div>
        </div>
        <StatusBadge ok={configured}/>
        {open ? <ChevronUp size={14} className="text-ink-3 flex-shrink-0"/> : <ChevronDown size={14} className="text-ink-3 flex-shrink-0"/>}
      </button>
      <div className={clsx("grid transition-all duration-300 ease-in-out", open ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0")}>
        <div className="overflow-hidden">
          <div className="px-4 pb-4 pt-1 border-t border-border">{children}</div>
        </div>
      </div>
    </div>
  )
}

// ── MaskedField — tampil masked + tombol Ganti ────────────────
function MaskedField({ masked, label, value, onChange, placeholder, hint, onSave, saving, isSecret = true }) {
  const [editing, setEditing] = useState(false)

  if (masked && !editing) {
    return (
      <div className="mt-3">
        <Label>{label}</Label>
        <div className="flex items-center gap-2 p-2.5 bg-bg-4 rounded-xl border border-border">
          <div className="flex-1 min-w-0">
            <div className="font-mono text-xs text-accent-2 truncate">{masked}</div>
          </div>
          <button onClick={() => setEditing(true)}
            className="text-[10px] text-ink-3 hover:text-accent-2 border border-border hover:border-accent/40 px-2.5 py-1 rounded-lg transition-colors flex-shrink-0">
            Ganti
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="mt-3 space-y-2.5">
      {masked && editing && (
        <div className="flex items-center justify-between text-[10px] p-2 bg-warn/8 border border-warn/25 rounded-lg">
          <span className="text-warn">Mengganti nilai yang tersimpan</span>
          <button onClick={() => { setEditing(false); onChange('') }} className="text-ink-3 hover:text-ink">✕ Batal</button>
        </div>
      )}
      {isSecret
        ? <SecretInput label={label} value={value} onChange={onChange} placeholder={placeholder} hint={hint}/>
        : <TextInput   label={label} value={value} onChange={onChange} placeholder={placeholder} hint={hint}/>
      }
      <Btn label="Simpan" onClick={() => { onSave(); !masked && setEditing(false) }}
        loading={saving} variant="primary" icon={Save} disabled={!value.trim()}/>
    </div>
  )
}

// ── Telegram Card ─────────────────────────────────────────────
function TelegramCard({ status, onSave, saving, onTest, testing }) {
  const [token, setToken]             = useState('')
  const [webhook, setWebhook]         = useState('')
  const [showTokenForm, setShowTF]    = useState(false)
  const [polling, setPolling]         = useState({ running: false, configured: false })
  const [pollingLoading, setPollLoad] = useState(false)
  const [botInfo, setBotInfo]         = useState(null)
  const timer = useRef(null)

  const configured = status?.telegram?.configured

  const loadPolling = async () => {
    try { const r = await intApi.pollingStatus(); setPolling(r) } catch {}
  }

  useEffect(() => {
    loadPolling()
    timer.current = setInterval(loadPolling, 5000)
    return () => clearInterval(timer.current)
  }, [])

  const handleStart = async () => {
    setPollLoad(true)
    try {
      const r = await intApi.startPolling()
      setBotInfo({ name: r.bot_name, username: r.username })
      toast.success(`🤖 Bot @${r.username} mulai berjalan!`)
      await loadPolling()
    } catch (e) { toast.error(`✗ ${e.message}`) }
    finally { setPollLoad(false) }
  }

  const handleStop = async () => {
    setPollLoad(true)
    try { await intApi.stopPolling(); setBotInfo(null); toast('⏹ Bot dihentikan', { icon: '⏹' }); await loadPolling() }
    catch (e) { toast.error(e.message) }
    finally { setPollLoad(false) }
  }

  const [open, setOpen] = useState(false)

  return (
    <div className="bg-bg-3 border border-border shadow-sm rounded-xl overflow-hidden transition-all duration-200">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center gap-3 px-4 py-3.5 hover:bg-bg-4 transition-colors">
        <div className="w-8 h-8 rounded-lg bg-bg-4 border border-border flex items-center justify-center text-lg flex-shrink-0">✈️</div>
        <div className="flex-1 min-w-0 text-left">
          <div className="text-sm font-semibold text-ink">Telegram Bot</div>
          <div className="text-[10px] text-ink-3">Auto-reply via AI ke chat Telegram</div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <StatusBadge ok={configured}/>
          {polling.running && (
            <span className="flex items-center gap-1 text-[10px] font-medium text-sky-400 bg-sky-400/10 border border-sky-400/20 px-2 py-0.5 rounded-full">
              <span className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-pulse"/>Polling
            </span>
          )}
          {open ? <ChevronUp size={14} className="text-ink-3 flex-shrink-0"/> : <ChevronDown size={14} className="text-ink-3 flex-shrink-0"/>}
        </div>
      </button>

      <div className={clsx("grid transition-all duration-300 ease-in-out", open ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0")}>
        <div className="overflow-hidden">
          <div className="px-4 pb-4 pt-2 border-t border-border">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-3">
                {configured && status?.telegram?.token_masked && !showTokenForm ? (
                  <div>
                    <Label>Bot Token</Label>
                    <div className="flex items-center gap-2 p-2.5 bg-bg-4 rounded-xl border border-border">
                      <div className="flex-1 min-w-0">
                        <div className="font-mono text-xs text-accent-2 truncate">{status.telegram.token_masked}</div>
                      </div>
                      <button onClick={() => setShowTF(true)}
                        className="text-[10px] text-ink-3 hover:text-accent-2 border border-border hover:border-accent/40 px-2.5 py-1 rounded-lg transition-colors flex-shrink-0">
                        Ganti
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-2.5">
                    {showTokenForm && (
                      <div className="flex items-center justify-between text-[10px] p-2 bg-warn/8 border border-warn/25 rounded-lg">
                        <span className="text-warn">Mengganti token tersimpan</span>
                        <button onClick={() => { setShowTF(false); setToken('') }} className="text-ink-3 hover:text-ink">✕ Batal</button>
                      </div>
                    )}
                    <SecretInput label="Bot Token" value={token} onChange={setToken}
                      placeholder="1234567890:ABCDEFxxxx"
                      hint="Dari @BotFather → /newbot atau /token"/>
                    <TextInput label="Webhook URL (opsional)" value={webhook} onChange={setWebhook}
                      placeholder="https://domain-kamu.com/api/integrations/telegram/webhook"
                      hint="Kosongkan untuk mode Polling (cocok localhost)" mono/>
                    <div className="flex gap-2">
                      <Btn label="Simpan" onClick={() => {
                        if (!token.trim()) { toast.error('Isi token terlebih dahulu'); return }
                        onSave('telegram', { TELEGRAM_BOT_TOKEN: token, ...(webhook ? { TELEGRAM_WEBHOOK_URL: webhook } : {}) })
                        setShowTF(false); setToken(''); setWebhook('')
                      }} loading={saving} variant="primary" icon={Save}/>
                      <Btn label="Test" onClick={onTest} loading={testing} variant="default" icon={Send}/>
                    </div>
                  </div>
                )}

                <div className="bg-bg-4 rounded-xl p-3 text-[10px] space-y-1 text-ink-3">
                  <div className="text-ink-2 font-semibold mb-1.5">📱 Cara setup:</div>
                  {[
                    ['Buka Telegram → cari', '@BotFather', ' → kirim /newbot'],
                    ['Ikuti instruksi → copy token'],
                    ['Tempel token di atas → Simpan'],
                    ['Klik Start Bot di kanan →'],
                  ].map((parts, i) => (
                    <div key={i}>{i + 1}. {parts.map((p, j) => (
                      p.startsWith('@') || p.startsWith('/') ? <code key={j} className="font-mono text-accent-2">{p}</code> : p
                    ))}</div>
                  ))}
                  <div className="pt-1 font-mono text-accent-2">/start /help /clear /model</div>
                </div>
              </div>

              <div className="space-y-3">
                <div className={clsx('rounded-xl border p-3.5', polling.running ? 'bg-sky-400/5 border-sky-400/20' : 'bg-bg-4 border-border')}>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      {polling.running ? <Wifi size={13} className="text-sky-400"/> : <WifiOff size={13} className="text-ink-3"/>}
                      <span className="text-xs font-semibold text-ink">
                        {polling.running ? 'Bot Aktif (Polling)' : 'Bot Tidak Aktif'}
                      </span>
                    </div>
                    {polling.running
                      ? <Btn label="Stop Bot" onClick={handleStop} loading={pollingLoading} variant="danger" icon={Square} small/>
                      : <Btn label="Start Bot" onClick={handleStart} loading={pollingLoading} variant="success" icon={Play} small disabled={!configured}/>
                    }
                  </div>

                  {polling.running && botInfo && (
                    <div className="text-[10px] text-sky-400 font-mono mb-1.5">🤖 @{botInfo.username} ({botInfo.name})</div>
                  )}

                  <div className="text-[10px] text-ink-3">
                    {polling.running
                      ? 'Bot menerima & menjawab pesan secara otomatis via AI.'
                      : configured
                        ? 'Klik Start Bot untuk mulai menerima pesan dari Telegram.'
                        : 'Simpan token Bot dulu sebelum menjalankan.'
                    }
                  </div>
                </div>

                {!configured && (
                  <div className="p-3 bg-accent/8 border border-accent/20 rounded-xl text-[10px] text-ink-2">
                    <strong className="text-ink block mb-1">Tips:</strong>
                    Mode Polling tidak memerlukan domain publik atau HTTPS — cocok untuk menjalankan di localhost / komputer rumah.
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── CustomModelSection ────────────────────────────────────────
function CustomModelSection() {
  const [providers, setProviders] = useState([])
  const [loading, setLoading]     = useState(true)
  const [showAdd, setShowAdd]     = useState(false)
  const [acting, setActing]       = useState({})
  const [testResult, setTestResult] = useState(null)

  const emptyForm = { name: '', base_url: '', api_key: '', models: '', icon: '🔌' }
  const [form, setForm] = useState(emptyForm)
  const setF = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const ICON_OPTIONS = ['🔌', '🧠', '⚡', '🚀', '💡', '🌐', '🔮', '🤖', '🎯', '💎']

  const load = async () => {
    setLoading(true)
    try {
      const r = await intApi.listCustomModels()
      setProviders(r.providers || [])
    } catch {} finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const handleTestConnection = async () => {
    if (!form.base_url.trim() || !form.api_key.trim()) {
      toast.error('Isi Base URL dan API Key terlebih dahulu')
      return
    }
    setActing(a => ({ ...a, testConn: true }))
    setTestResult(null)
    try {
      const r = await intApi.testCustomConnection({
        base_url: form.base_url,
        api_key: form.api_key,
        models: form.models,
      })
      setTestResult({ status: 'ok', message: r.message, models: r.available_models })
      toast.success(r.message)
      if (!form.models.trim() && r.available_models?.length > 0) {
        setF('models', r.available_models.slice(0, 5).join(','))
      }
    } catch (e) {
      setTestResult({ status: 'error', message: e.message })
      toast.error(`✗ ${e.message}`)
    } finally { setActing(a => ({ ...a, testConn: false })) }
  }

  const handleSave = async () => {
    if (!form.name.trim() || !form.base_url.trim() || !form.api_key.trim() || !form.models.trim()) {
      toast.error('Semua field wajib diisi'); return
    }
    setActing(a => ({ ...a, save: true }))
    try {
      const r = await intApi.addCustomModel(form)
      if (r.models) { useModelsStore.setState({ models: r.models }); syncModelsToOrchestrator(r.models) }
      toast.success('✅ Provider berhasil ditambahkan!')
      setShowAdd(false); setForm(emptyForm); setTestResult(null); await load()
    } catch (e) { toast.error(e.message) }
    finally { setActing(a => ({ ...a, save: false })) }
  }

  const handleDelete = async (id) => {
    if (!confirm('Hapus provider ini?')) return
    setActing(a => ({ ...a, [id + '_del']: true }))
    try {
      const r = await intApi.deleteCustomModel(id)
      if (r.models) { useModelsStore.setState({ models: r.models }); syncModelsToOrchestrator(r.models) }
      toast.success('Provider dihapus'); await load()
    } catch (e) { toast.error(e.message) }
    finally { setActing(a => ({ ...a, [id + '_del']: false })) }
  }

  const handleTest = async (id) => {
    setActing(a => ({ ...a, [id + '_test']: true }))
    try {
      const r = await intApi.testCustomModel(id)
      toast.success(`✅ ${r.message}`); await load()
    } catch (e) { toast.error(`✗ ${e.message}`) }
    finally { setActing(a => ({ ...a, [id + '_test']: false })) }
  }

  const STATUS_STYLE = {
    connected: { label: 'Tersambung', cls: 'text-success bg-success/10 border-success/20' },
    untested:  { label: 'Belum Ditest', cls: 'text-warn bg-warn/10 border-warn/20' },
    error:     { label: 'Error', cls: 'text-danger bg-danger/10 border-danger/20' },
  }

  const [open, setOpen] = useState(false)

  return (
    <div className="bg-bg-3 border border-border shadow-sm rounded-xl overflow-hidden mt-0">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between px-4 py-3.5 hover:bg-bg-4 transition-colors">
        <div className="flex items-center gap-3 text-left">
          <div className="w-8 h-8 rounded-lg bg-bg-4 border border-border flex items-center justify-center text-lg flex-shrink-0">🔌</div>
          <div>
            <div className="text-sm font-semibold text-ink">Custom Model Provider</div>
            <div className="text-[10px] text-ink-3">Tambah model API pihak ketiga (format OpenAI)</div>
          </div>
          {providers.length > 0 && <span className="ml-2 text-[10px] bg-accent/15 text-accent-2 px-1.5 py-0.5 rounded-full">{providers.length} provider</span>}
        </div>
        {open ? <ChevronUp size={14} className="text-ink-3 flex-shrink-0"/> : <ChevronDown size={14} className="text-ink-3 flex-shrink-0"/>}
      </button>

      <div className={clsx("grid transition-all duration-300 ease-in-out", open ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0")}>
        <div className="overflow-hidden">
          <div className="p-4 space-y-3 border-t border-border">
            <div className="flex justify-end mb-1">
              <Btn label="+ Tambah Provider" onClick={() => { setShowAdd(!showAdd); setForm(emptyForm); setTestResult(null) }} variant="primary" icon={Plus} small/>
            </div>
            {showAdd && (
              <div className="bg-bg-4 border border-accent/25 rounded-xl p-4 space-y-3 animate-fade">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-ink">➕ Tambah Model AI Provider</span>
                  <button onClick={() => { setShowAdd(false); setTestResult(null) }} className="text-ink-3 hover:text-ink text-xs">✕</button>
                </div>
                <div>
                  <Label>Ikon</Label>
                  <div className="flex gap-1.5 flex-wrap">
                    {ICON_OPTIONS.map(ic => (
                      <button key={ic} onClick={() => setF('icon', ic)}
                        className={clsx('w-8 h-8 rounded-lg flex items-center justify-center text-base border transition-all',
                          form.icon === ic ? 'border-accent bg-accent/10' : 'border-border bg-bg-3 hover:border-border-2')}>
                        {ic}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <TextInput label="Nama Provider *" value={form.name} onChange={v => setF('name', v)} placeholder="Together AI, Groq, dll"/>
                  <TextInput label="Base URL *" value={form.base_url} onChange={v => setF('base_url', v)} placeholder="https://api.together.xyz/v1" mono/>
                </div>
                <SecretInput label="API Key *" value={form.api_key} onChange={v => setF('api_key', v)} placeholder="sk-..."/>
                <TextInput label="Model (pisah koma) *" value={form.models} onChange={v => setF('models', v)} placeholder="llama-3.1-70b,mixtral-8x7b" mono/>
                <div className="flex items-center gap-2">
                  <Btn label="Test Koneksi" onClick={handleTestConnection} loading={acting.testConn} variant="success" icon={Send}/>
                  {testResult && (
                    <div className={clsx('flex-1 text-[10px] px-3 py-2 rounded-lg font-medium',
                      testResult.status === 'ok' ? 'bg-success/10 text-success border border-success/20' : 'bg-danger/10 text-danger border border-danger/20')}>
                      {testResult.message}
                    </div>
                  )}
                </div>
                <div className="flex items-center justify-end gap-2 pt-1">
                  <Btn label="Batal" onClick={() => { setShowAdd(false); setTestResult(null) }} variant="default" small/>
                  <Btn label="Simpan Provider" onClick={handleSave} loading={acting.save} variant="primary" icon={Save}/>
                </div>
              </div>
            )}
            {loading ? (
              <div className="text-xs text-ink-3 flex items-center gap-2 py-2"><RefreshCw size={11} className="animate-spin"/>Memuat...</div>
            ) : providers.length === 0 && !showAdd ? (
              <div className="text-center py-6 text-xs text-ink-3">Belum ada custom provider.</div>
            ) : (
              <div className="space-y-2">
                {providers.map(p => {
                  const st = STATUS_STYLE[p.status] || STATUS_STYLE.untested
                  return (
                    <div key={p.id} className="bg-bg-4 rounded-xl border border-border p-3">
                      <div className="flex items-start gap-2">
                        <span className="text-base flex-shrink-0 mt-0.5">{p.icon || '🔌'}</span>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-xs font-semibold text-ink">{p.name}</span>
                            <span className={clsx('text-[9px] px-1.5 py-0.5 rounded-full font-medium border', st.cls)}>{st.label}</span>
                          </div>
                          <div className="text-[9px] text-ink-3 mt-0.5">Model: {p.models}</div>
                        </div>
                        <div className="flex items-center gap-1.5 flex-shrink-0">
                          <Btn label="Test" onClick={() => handleTest(p.id)} loading={acting[p.id+'_test']} variant="success" icon={Send} small/>
                          <button onClick={() => handleDelete(p.id)} disabled={acting[p.id+'_del']} className="p-1.5 rounded-lg text-ink-3 hover:text-danger hover:bg-danger/10 transition-colors">
                            <Trash2 size={11}/>
                          </button>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// ── WebhookSection ────────────────────────────────────────────
const PROVIDER_META = {
  fonnte: { label: 'Fonnte',  color: 'bg-green-500/15 text-green-400',   emoji: '📱' },
  n8n:    { label: 'n8n',     color: 'bg-pink-500/15 text-pink-400',     emoji: '🔄' },
  make:   { label: 'Make',    color: 'bg-purple-500/15 text-purple-400', emoji: '⚙️' },
  zapier: { label: 'Zapier',  color: 'bg-orange-500/15 text-orange-400', emoji: '⚡' },
  custom: { label: 'Custom',  color: 'bg-bg-5 text-ink-3',               emoji: '🔗' },
}

function WebhookSection() {
  const [hooks, setHooks]         = useState([])
  const [templates, setTemplates] = useState([])
  const [loading, setLoad]        = useState(true)
  const [showAdd, setShowAdd]     = useState(false)
  const [showTpl, setShowTpl]     = useState(false)
  const [acting, setActing]       = useState({})
  const [testRes, setTestRes]     = useState({})
  const [editId, setEditId]       = useState(null)

  const emptyForm = { name:'', description:'', provider:'custom', url:'', method:'POST', secret:'', events:['message'], headers_json:'{}', body_template:'', enabled:true }
  const [form, setForm] = useState(emptyForm)
  const setF = (k, v) => setForm(f => ({ ...f, [k]: v }))
  const setAct = (k, v) => setActing(a => ({ ...a, [k]: v }))

  const load = async () => {
    setLoad(true)
    try {
      const [h, t] = await Promise.allSettled([intApi.listWebhooks(), intApi.webhookTemplates()])
      if (h.status === 'fulfilled') setHooks(h.value.webhooks || [])
      if (t.status === 'fulfilled') setTemplates(t.value.templates || [])
    } finally { setLoad(false) }
  }

  useEffect(() => { load() }, [])
  const pm = p => PROVIDER_META[p] || PROVIDER_META.custom

  const handleSave = async () => {
    if (!form.name.trim() || !form.url.trim()) { toast.error('Nama dan URL wajib diisi'); return }
    setAct('save', true)
    try {
      editId ? await intApi.updateWebhook(editId, form) : await intApi.createWebhook(form)
      toast.success('Berhasil disimpan'); setShowAdd(false); setEditId(null); setForm(emptyForm); await load()
    } catch(e) { toast.error(e.message) } finally { setAct('save', false) }
  }

  const handleDelete = async (id) => {
    if (!confirm('Hapus webhook?')) return
    setAct(id+'_del', true)
    try { await intApi.deleteWebhook(id); toast.success('Dihapus'); await load() }
    catch(e) { toast.error(e.message) } finally { setAct(id+'_del', false) }
  }

  const handleTest = async (id) => {
    setAct(id+'_test', true)
    try {
      const r = await intApi.testWebhook(id)
      setTestRes(res => ({ ...res, [id]: r }))
      toast.success(r.message)
    } catch(e) { toast.error(e.message) } finally { setAct(id+'_test', false) }
  }

  const [open, setOpen] = useState(false)

  return (
    <div className="bg-bg-3 border border-border shadow-sm rounded-xl overflow-hidden mt-0">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between px-4 py-3.5 hover:bg-bg-4 transition-colors">
        <div className="flex items-center gap-3 text-left">
          <div className="w-8 h-8 rounded-lg bg-bg-4 border border-border flex items-center justify-center text-accent-2 flex-shrink-0"><Webhook size={16}/></div>
          <div>
            <div className="text-sm font-semibold text-ink">Webhook Lanjutan</div>
            <div className="text-[10px] text-ink-3">Kirim triggger ke Fonnte, n8n, Make, Zapier, dll</div>
          </div>
        </div>
        {open ? <ChevronUp size={14} className="text-ink-3 flex-shrink-0"/> : <ChevronDown size={14} className="text-ink-3 flex-shrink-0"/>}
      </button>

      <div className={clsx("grid transition-all duration-300 ease-in-out", open ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0")}>
        <div className="overflow-hidden">
          <div className="p-4 space-y-3 border-t border-border">
            <div className="flex gap-2 justify-end mb-2">
              <Btn label="+ Tambah Webhook" onClick={() => { setShowAdd(!showAdd); setEditId(null); setForm(emptyForm) }} variant="primary" icon={Plus} small/>
            </div>
            {showAdd && (
              <div className="bg-bg-4 border border-accent/25 rounded-xl p-4 space-y-3">
                <TextInput label="Nama Webhook *" value={form.name} onChange={v => setF('name', v)}/>
                <TextInput label="URL Endpoint *" value={form.url} onChange={v => setF('url', v)} mono/>
                <div className="flex items-center justify-end gap-2 pt-1">
                  <Btn label="Simpan Webhook" onClick={handleSave} loading={acting.save} variant="primary" icon={Save}/>
                </div>
              </div>
            )}
            {loading ? (
              <div className="text-xs text-ink-3"><RefreshCw size={11} className="animate-spin mr-2"/>Memuat...</div>
            ) : hooks.length === 0 ? (
              <div className="text-center py-6 text-xs text-ink-3">Belum ada webhook.</div>
            ) : (
              <div className="space-y-2">
                {hooks.map(h => {
                  const meta = pm(h.provider)
                  return (
                    <div key={h.id} className="bg-bg-4 rounded-xl border border-border p-3">
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="text-xs font-semibold text-ink">{h.name}</div>
                          <div className="text-[9px] text-ink-3 font-mono truncate max-w-xs">{h.url}</div>
                        </div>
                        <div className="flex gap-1.5">
                          <Btn label="Test" onClick={() => handleTest(h.id)} loading={acting[h.id+'_test']} variant="success" icon={Send} small/>
                          <button onClick={() => handleDelete(h.id)} className="text-ink-3 hover:text-danger"><Trash2 size={11}/></button>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// ── GoogleDriveCard ───────────────────────────────────────────
function GoogleDriveCard({ status, onSave, saving }) {
  const [creds, setCreds] = useState('')
  const [open, setOpen] = useState(false)
  const configured = status?.google_drive?.configured

  return (
    <div className="bg-bg-3 border border-border shadow-sm rounded-xl overflow-hidden transition-all duration-200">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center gap-3 px-4 py-3.5 hover:bg-bg-4 transition-colors">
        <div className="w-8 h-8 rounded-lg bg-bg-4 border border-border flex items-center justify-center text-lg flex-shrink-0">☁️</div>
        <div className="flex-1 min-w-0 text-left">
          <div className="text-sm font-semibold text-ink">Google Drive</div>
          <div className="text-[10px] text-ink-3">Beri akses AI untuk membuat dan menyimpan file langsung ke Google Drive</div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <StatusBadge ok={configured}/>
          {open ? <ChevronUp size={14} className="text-ink-3 flex-shrink-0"/> : <ChevronDown size={14} className="text-ink-3 flex-shrink-0"/>}
        </div>
      </button>

      <div className={clsx("grid transition-all duration-300 ease-in-out", open ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0")}>
        <div className="overflow-hidden">
          <div className="px-4 pb-4 pt-2 border-t border-border">
            <div className="space-y-3">
              <Textarea 
                label="Service Account JSON Kredensial" 
                value={creds} 
                onChange={setCreds} 
                placeholder='{ "type": "service_account", "project_id": "...", ... }' 
                hint="Tempel seluruh isi file kredensial JSON tipe Service Account dari Google Cloud"
                rows={4}
              />
              <Btn label="Simpan Kredensial" onClick={() => {
                if (!creds.trim()) { toast.error('Isi kredensial JSON'); return; }
                if (!creds.trim().startsWith('{')) { toast.error('Harus berformat JSON valid'); return; }
                
                // Safe UTF-8 Base64 encoding
                const encoded = btoa(encodeURIComponent(creds.trim()).replace(/%([0-9A-F]{2})/g, (match, p1) => String.fromCharCode('0x' + p1)))
                onSave('google_drive', { GOOGLE_DRIVE_CREDENTIALS: encoded })
                setCreds('')
              }} loading={saving} variant="primary" icon={Save}/>
              
              <div className="bg-bg-4 rounded-xl p-3 text-[10px] space-y-1 text-ink-3 mt-2">
                <div className="text-ink-2 font-semibold mb-1.5 flex items-center gap-1"><AlertCircle size={12}/> Cara mendapatkan JSON Google Cloud:</div>
                <div className="pl-2 space-y-1">
                  <div>1. Login ke <a href="https://console.cloud.google.com" target="_blank" rel="noopener noreferrer" className="text-accent underline">Google Cloud Console</a>.</div>
                  <div>2. Buat Project baru dan pastikan <span className="font-semibold text-ink-2">Google Drive API</span> sudah **Enabled**.</div>
                  <div>3. Masuk ke **APIs & Services** {'>'} **Credentials**. Klik Create Credentials {'>'} **Service Account**.</div>
                  <div>4. Buka Service Account tersebut, tab **Keys** {'>'} Add Key {'>'} Create New Key (JSON).</div>
                  <div>5. File JSON akan terdownload. Tempel seluruh isinya di atas.</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Main Integrations ─────────────────────────────────────────
export default function Integrations() {
  const [status,     setStatus]     = useState(null)
  const [loading,    setLoading]    = useState(true)
  const [saving,     setSaving]     = useState({})
  const [testing,    setTesting]    = useState({})
  const [reloading,  setReloading]  = useState(false)
  const [restarting, setRestarting] = useState(false)

  const [openaiKey,      setOpenaiKey]      = useState('')
  const [openaiModels,   setOpenaiModels]   = useState('')
  const [anthropicKey,   setAnthropicKey]   = useState('')
  const [anthropicModels,setAnthropicModels]= useState('')
  const [googleKey,      setGoogleKey]      = useState('')
  const [googleModels,   setGoogleModels]   = useState('')
  const [sumopodKey,     setSumopodKey]     = useState('')
  const [sumopodHost,    setSumopodHost]    = useState('')
  const [sumopodModels,  setSumopodModels]  = useState('')
  const [ollamaHost,     setOllamaHost]     = useState('')
  const [ollamaModels,   setOllamaModels]   = useState('')
  const [waToken,        setWaToken]        = useState('')
  const [waPhoneId,      setWaPhoneId]      = useState('')

  const [activeTab, setActiveTab] = useState(() => localStorage.getItem('int_active_tab') || 'messaging')
  useEffect(() => { localStorage.setItem('int_active_tab', activeTab) }, [activeTab])

  const TABS = [
    { id: 'messaging', label: 'Messaging', icon: '💬' },
    { id: 'model_ai',  label: 'Model AI',  icon: '🤖' },
    { id: 'cloud_storage', label: 'Cloud Storage', icon: '☁️' },
    { id: 'webhook',   label: 'Webhook & Otomasi', icon: '🔗' },
    { id: 'api_docs',  label: 'API Endpoints', icon: '🔌' },
  ]

  const load = async () => {
    try {
      const s = await intApi.status()
      setStatus(s)
      if (s.openai?.models)  setOpenaiModels(s.openai.models)
      if (s.anthropic?.models) setAnthropicModels(s.anthropic.models)
      if (s.google?.models)  setGoogleModels(s.google.models)
      if (s.sumopod?.host)   setSumopodHost(s.sumopod.host)
      if (s.sumopod?.models) setSumopodModels(s.sumopod.models)
      if (s.ollama?.host)    setOllamaHost(s.ollama.host)
      if (s.ollama?.models)  setOllamaModels(s.ollama.models)
    } catch {} finally { setLoading(false) }
  }

  // On mount: also fetch current models and sync to orchestrator store
  useEffect(() => {
    load()
    api.listModels().then(r => {
      const ms = r.models || []
      useModelsStore.setState({ models: ms })
      syncModelsToOrchestrator(ms)
    }).catch(() => {})
  }, [])

  async function save(provider, fields) {
    setSaving(s => ({ ...s, [provider]: true }))
    try { 
      const r = await intApi.saveKey(provider, fields); 
      if (r.models) {
        useModelsStore.setState({ models: r.models });
        syncModelsToOrchestrator(r.models);
      }
      toast.success(`✓ ${r.message}`); await load() 
    } catch (e) { toast.error(e.message) }
    finally { setSaving(s => ({ ...s, [provider]: false })) }
  }

  async function testConn(provider, fn) {
    setTesting(s => ({ ...s, [provider]: true }))
    try {
      const r = await fn()
      toast.success(`✓ Koneksi ${provider} Berhasil`)
    } catch (e) { toast.error(`✗ ${e.message}`) }
    finally { setTesting(s => ({ ...s, [provider]: false })) }
  }

  if (loading) return (
    <div className="p-6 text-sm text-ink-3 flex items-center gap-2">
      <RefreshCw size={14} className="animate-spin"/>Memuat...
    </div>
  )

  return (
    <div className="p-4 md:p-6 w-full">
      <div className="flex items-start justify-between mb-5 flex-wrap gap-3">
        <div>
          <h1 className="text-lg font-bold text-ink">Integrasi Platform</h1>
          <p className="text-xs text-ink-3 mt-0.5">API key & koneksi layanan eksternal</p>
        </div>
        <div className="flex items-center gap-2">
          <Btn label="Reload Model" onClick={async () => {
            setReloading(true)
            try { 
              const r = await intApi.reloadModels(); 
              if (r.models) {
                useModelsStore.setState({ models: r.models });
                syncModelsToOrchestrator(r.models);
              }
              toast.success(`✓ ${r.message}`);
            }
            catch (e) { toast.error(e.message) } finally { setReloading(false) }
          }} loading={reloading} variant="success" icon={RefreshCw}/>
          <Btn label="Restart Server" onClick={async () => {
            if (!confirm('Restart server?')) return
            setRestarting(true)
            try { await intApi.restart(); await new Promise(r => setTimeout(r, 4000)); toast.success('Restart selesai!') }
            catch (e) { toast.error(e.message) } finally { setRestarting(false) }
          }} loading={restarting} variant="danger" icon={RotateCcw}/>
        </div>
      </div>

      <div className="flex gap-2 overflow-x-auto pb-0 mb-5 border-b border-border scrollbar-hide">
        {TABS.map(t => (
          <button key={t.id} onClick={() => setActiveTab(t.id)}
            className={clsx('flex items-center gap-2 px-4 py-2.5 text-xs font-semibold transition-all whitespace-nowrap border-b-2 outline-none',
              activeTab === t.id ? 'border-accent text-accent' : 'border-transparent text-ink-3 hover:text-ink hover:border-border-2')}>
            <span className="text-base">{t.icon}</span> {t.label}
          </button>
        ))}
      </div>

      <div className="animate-fade space-y-3">
        <div className={clsx("space-y-3", activeTab !== 'messaging' && "hidden")}>
          <TelegramCard status={status} onSave={save} saving={saving.telegram}
            onTest={() => testConn('telegram', intApi.testTelegram)} testing={testing.telegram}/>

          <Card icon="💬" title="WhatsApp Business" subtitle="Meta Business API" configured={status?.whatsapp?.configured}>
            <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-4">
              <MaskedField masked={status?.whatsapp?.token_masked} label="Access Token" value={waToken} onChange={setWaToken} onSave={() => save('whatsapp', { WHATSAPP_ACCESS_TOKEN: waToken })} saving={saving.whatsapp}/>
              <MaskedField masked={status?.whatsapp?.phone_number_id} label="Phone Number ID" value={waPhoneId} onChange={setWaPhoneId} onSave={() => save('whatsapp', { WHATSAPP_PHONE_NUMBER_ID: waPhoneId })} saving={saving.whatsapp} isSecret={false}/>
            </div>
          </Card>
        </div>

        <div className={clsx("space-y-3", activeTab !== 'model_ai' && "hidden")}>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            <Card icon="🧠" title="OpenAI" subtitle="GPT-4o, GPT-4o Mini" configured={status?.openai?.configured}>
              <div className="mt-3 space-y-2.5">
                <MaskedField masked={status?.openai?.key_masked} label="API Key" value={openaiKey} onChange={setOpenaiKey} onSave={() => save('openai', { OPENAI_API_KEY: openaiKey, OPENAI_AVAILABLE_MODELS: openaiModels })} saving={saving.openai}/>
                <div className="flex gap-2 items-end">
                  <div className="flex-1"><TextInput label="Model AI (opsional, pisahkan koma)" value={openaiModels} onChange={setOpenaiModels} placeholder="contoh: o1, o1-mini" mono/></div>
                  {status?.openai?.configured && <Btn label="Simpan" onClick={() => save('openai', { OPENAI_AVAILABLE_MODELS: openaiModels })} loading={saving.openai} variant="default" icon={Save}/>}
                </div>
              </div>
            </Card>
            <Card icon="✨" title="Anthropic Claude" subtitle="Claude 3.5" configured={status?.anthropic?.configured}>
              <div className="mt-3 space-y-2.5">
                <MaskedField masked={status?.anthropic?.key_masked} label="API Key" value={anthropicKey} onChange={setAnthropicKey} onSave={() => save('anthropic', { ANTHROPIC_API_KEY: anthropicKey, ANTHROPIC_AVAILABLE_MODELS: anthropicModels })} saving={saving.anthropic}/>
                <div className="flex gap-2 items-end">
                  <div className="flex-1"><TextInput label="Model AI (opsional, pisahkan koma)" value={anthropicModels} onChange={setAnthropicModels} placeholder="contoh: claude-3-5-sonnet-20241022" mono/></div>
                  {status?.anthropic?.configured && <Btn label="Simpan" onClick={() => save('anthropic', { ANTHROPIC_AVAILABLE_MODELS: anthropicModels })} loading={saving.anthropic} variant="default" icon={Save}/>}
                </div>
              </div>
            </Card>
            <Card icon="💎" title="Google Gemini" subtitle="Gemini 1.5" configured={status?.google?.configured}>
              <div className="mt-3 space-y-2.5">
                <MaskedField masked={status?.google?.key_masked} label="API Key" value={googleKey} onChange={setGoogleKey} onSave={() => save('google', { GOOGLE_API_KEY: googleKey, GOOGLE_AVAILABLE_MODELS: googleModels })} saving={saving.google}/>
                <div className="flex gap-2 items-end">
                  <div className="flex-1"><TextInput label="Model AI (opsional, pisahkan koma)" value={googleModels} onChange={setGoogleModels} placeholder="contoh: gemini-2.0-flash, gemini-1.5-pro" mono/></div>
                  {status?.google?.configured && <Btn label="Simpan" onClick={() => save('google', { GOOGLE_AVAILABLE_MODELS: googleModels })} loading={saving.google} variant="default" icon={Save}/>}
                </div>
              </div>
            </Card>
            <Card icon="🚀" title="Sumopod" subtitle="OpenAI-compatible" configured={status?.sumopod?.configured}>
              <div className="mt-3 space-y-2.5">
                <MaskedField masked={status?.sumopod?.key_masked} label="API Key" value={sumopodKey} onChange={setSumopodKey} onSave={() => save('sumopod', { SUMOPOD_API_KEY: sumopodKey, SUMOPOD_HOST: sumopodHost, SUMOPOD_AVAILABLE_MODELS: sumopodModels })} saving={saving.sumopod}/>
                <TextInput label="API Host" value={sumopodHost} onChange={setSumopodHost} placeholder="https://ai.sumopod.com/v1" mono/>
                <div className="flex gap-2 items-end">
                  <div className="flex-1"><TextInput label="Model AI (opsional, pisahkan koma)" value={sumopodModels} onChange={setSumopodModels} placeholder="contoh: meta-llama/Llama-3-70b" mono/></div>
                  {status?.sumopod?.configured && <Btn label="Simpan" onClick={() => save('sumopod', { SUMOPOD_HOST: sumopodHost, SUMOPOD_AVAILABLE_MODELS: sumopodModels })} loading={saving.sumopod} variant="default" icon={Save}/>}
                </div>
              </div>
            </Card>
            <Card icon="🦙" title="Ollama" subtitle="Lokal" configured={status?.ollama?.configured}>
              <div className="mt-3 space-y-2.5">
                <TextInput label="Host" value={ollamaHost} onChange={setOllamaHost} placeholder="http://localhost:11434" mono/>
                <TextInput label="Model AI (opsional, pisahkan koma)" value={ollamaModels} onChange={setOllamaModels} placeholder="contoh: llama3.1, mistral" mono/>
                <div className="flex gap-2 mt-2">
                  <Btn label="Simpan" onClick={() => save('ollama', { OLLAMA_HOST: ollamaHost, OLLAMA_AVAILABLE_MODELS: ollamaModels })} loading={saving.ollama} variant="primary" icon={Save}/>
                  <Btn label="Test" onClick={() => testConn('ollama', intApi.testOllama)} loading={testing.ollama} variant="success" icon={Send}/>
                </div>
              </div>
            </Card>
          </div>
          <CustomModelSection/>
        </div>

        <div className={clsx("space-y-3", activeTab !== 'cloud_storage' && "hidden")}>
          <GoogleDriveCard status={status} onSave={save} saving={saving.google_drive}/>
        </div>

        <div className={clsx(activeTab !== 'webhook' && "hidden")}>
          <WebhookSection/>
        </div>

        <div className={clsx(activeTab !== 'api_docs' && "hidden")}>
          <div className="bg-bg-3 border border-border shadow-sm rounded-xl p-4">
            <h2 className="text-sm font-semibold text-ink mb-3">🔌 REST API Endpoints</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-1.5 text-[10px] font-mono text-ink-2">
              <div className="p-2 bg-bg-4 rounded-lg border border-border">POST /api/chat/send</div>
              <div className="p-2 bg-bg-4 rounded-lg border border-border">GET /api/models</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
