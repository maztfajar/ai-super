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
import { useTranslation } from 'react-i18next'
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
  updateCustomModel:    (id,d) => api.updateCustomModel(id, d),
  deleteCustomModel:    (id) => api.deleteCustomModel(id),
  testCustomModel:      (id) => api.testCustomModel(id),
  testCustomConnection: (d) => api.testCustomConnection(d),
  // AI Roles
  getSettings:          () => api.getSettings(),
  saveAiRoles:          (d) => api.saveAiRoles(d),
  getResolvedRoles:     () => api.getResolvedRoles(),
  testNativeTools:      (model_id) => api.post('/settings/ai-roles/test-tools', { model_id }),
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
  return <label className="block text-xs text-ink-3 mb-2 uppercase tracking-widest font-bold opacity-60">{children}</label>
}

function SecretInput({ label, value, onChange, placeholder, hint, disabled }) {
  const [show, setShow] = useState(false)
  return (
    <div className="space-y-1.5">
      {label && <Label>{label}</Label>}
      <div className="relative">
        <input type={show ? 'text' : 'password'} value={value} onChange={e => onChange(e.target.value)}
          placeholder={placeholder} disabled={disabled}
          autoComplete="new-password"
          className="w-full bg-bg-2 border border-border rounded-xl px-4 py-3 text-sm font-bold text-ink placeholder-ink-3 outline-none focus:border-accent pr-11 font-mono disabled:opacity-50 shadow-inner transition-all"/>
        <button type="button" onClick={() => setShow(!show)}
          className="absolute right-3.5 top-1/2 -translate-y-1/2 text-ink-3 hover:text-ink transition-all">
          {show ? <EyeOff size={16}/> : <Eye size={16}/>}
        </button>
      </div>
      {hint && <p className="text-[11px] text-ink-3 mt-1.5 font-semibold uppercase tracking-tight opacity-70">{hint}</p>}
    </div>
  )
}

function TextInput({ label, value, onChange, placeholder, hint, mono, disabled }) {
  return (
    <div className="space-y-1.5">
      {label && <Label>{label}</Label>}
      <input type="text" value={value} onChange={e => onChange(e.target.value)}
        placeholder={placeholder} disabled={disabled}
        className={clsx('w-full bg-bg-2 border border-border rounded-xl px-4 py-3 text-sm font-bold text-ink placeholder-ink-3 outline-none focus:border-accent disabled:opacity-50 shadow-inner transition-all', mono && 'font-mono')}/>
      {hint && <p className="text-[11px] text-ink-3 mt-1.5 font-semibold uppercase tracking-tight opacity-70">{hint}</p>}
    </div>
  )
}

function Textarea({ label, value, onChange, placeholder, hint, rows = 3 }) {
  return (
    <div className="space-y-1.5">
      {label && <Label>{label}</Label>}
      <textarea value={value} onChange={e => onChange(e.target.value)}
        placeholder={placeholder} rows={rows}
        className="w-full bg-bg-2 border border-border rounded-xl px-4 py-3 text-sm font-bold text-ink placeholder-ink-3 outline-none focus:border-accent font-mono resize-none shadow-inner transition-all"/>
      {hint && <p className="text-[11px] text-ink-3 mt-1.5 font-semibold uppercase tracking-tight opacity-70">{hint}</p>}
    </div>
  )
}

function StatusBadge({ ok }) {
  const { t } = useTranslation()
  return ok
    ? <span className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-success bg-success/10 border border-success/30 px-3 py-1 rounded-full shadow-sm"><CheckCircle2 size={12}/>{t('active')}</span>
    : <span className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-ink-3 bg-bg-4 border border-border px-3 py-1 rounded-full opacity-60"><XCircle size={12}/>{t('not_setup')}</span>
}

function Btn({ label, onClick, loading, variant = 'default', icon: Icon, small, disabled, full }) {
  return (
    <button onClick={onClick} disabled={loading || disabled}
      className={clsx('flex items-center justify-center gap-2 rounded-xl font-bold uppercase tracking-widest transition-all disabled:opacity-50 active:scale-95 shadow-md',
        full ? 'w-full' : '',
        small ? 'px-3 py-2 text-[10px]' : 'px-5 py-3 text-sm',
        variant === 'primary' && 'bg-accent hover:bg-accent/80 text-white shadow-accent/20',
        variant === 'success' && 'bg-success/10 hover:bg-success/20 border border-success/30 text-success',
        variant === 'danger'  && 'bg-danger/10 hover:bg-danger/20 border border-danger/30 text-danger',
        variant === 'warn'    && 'bg-warn/10 hover:bg-warn/20 border border-warn/30 text-warn',
        variant === 'default' && 'bg-bg-4 hover:bg-bg-5 border border-border text-ink-2 hover:text-ink',
      )}>
      {loading ? <RefreshCw size={small ? 12 : 16} className="animate-spin"/> : Icon && <Icon size={small ? 12 : 16}/>}
      {label}
    </button>
  )
}

function CopyBtn({ text }) {
  const [ok, setOk] = useState(false)
  return (
    <button onClick={() => { copyToClipboard(text); setOk(true); setTimeout(() => setOk(false), 2000) }}
      className="p-2 rounded-lg hover:bg-bg-5 text-ink-3 hover:text-ink transition-all flex-shrink-0">
      {ok ? <Check size={14} className="text-success"/> : <Copy size={14}/>}
    </button>
  )
}

// ── Card collapsible ──────────────────────────────────────────
function Card({ icon, title, subtitle, configured, children }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="bg-bg-3 border border-border shadow-lg rounded-2xl overflow-hidden transition-all duration-300">
      <button className="w-full flex items-center gap-4 px-5 py-4 hover:bg-bg-4 transition-all"
        onClick={() => setOpen(!open)}>
        <div className="w-10 h-10 rounded-xl bg-bg-4 border border-border flex items-center justify-center text-xl flex-shrink-0 shadow-inner">{icon}</div>
        <div className="flex-1 min-w-0 text-left">
          <div className="text-lg font-bold text-ink uppercase tracking-tight">{title}</div>
          <div className="text-xs text-ink-3 font-semibold uppercase tracking-widest opacity-60">{subtitle}</div>
        </div>
        <StatusBadge ok={configured}/>
        {open ? <ChevronUp size={18} className="text-ink-3 flex-shrink-0"/> : <ChevronDown size={18} className="text-ink-3 flex-shrink-0"/>}
      </button>
      <div className={clsx("grid transition-all duration-500 ease-in-out", open ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0")}>
        <div className="overflow-hidden">
          <div className="px-6 pb-6 pt-2 border-t-2 border-border/40">{children}</div>
        </div>
      </div>
    </div>
  )
}

// ── MaskedField — tampil masked + tombol Ganti ────────────────
function MaskedField({ masked, label, value, onChange, placeholder, hint, onSave, saving, isSecret = true }) {
  const [editing, setEditing] = useState(false)
  const { t } = useTranslation()

  if (masked && !editing) {
    return (
      <div className="mt-4">
        <Label>{label}</Label>
        <div className="flex items-center gap-3 p-3 bg-bg-4 rounded-xl border border-border shadow-inner">
          <div className="flex-1 min-w-0">
            <div className="font-mono text-sm text-accent-2 truncate font-bold tracking-widest">{masked}</div>
          </div>
          <button onClick={() => setEditing(true)}
            className="text-[10px] uppercase tracking-widest text-ink-3 hover:text-accent-2 border border-border hover:border-accent/40 px-3 py-1.5 rounded-lg transition-all flex-shrink-0 font-bold shadow-sm active:scale-95 bg-bg-3">
            {t('edit')}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="mt-4 space-y-4">
      {masked && editing && (
        <div className="flex items-center justify-between text-[11px] p-3 bg-warn/10 border border-warn/30 rounded-xl font-bold uppercase tracking-tight shadow-inner">
          <span className="text-warn">Mengganti nilai yang tersimpan</span>
          <button onClick={() => { setEditing(false); onChange('') }} className="text-ink-3 hover:text-ink uppercase tracking-widest text-[10px]">✕ Batal</button>
        </div>
      )}
      {isSecret
        ? <SecretInput label={label} value={value} onChange={onChange} placeholder={placeholder} hint={hint}/>
        : <TextInput   label={label} value={value} onChange={onChange} placeholder={placeholder} hint={hint}/>
      }
      <Btn label={t('save')} onClick={() => { onSave(); !masked && setEditing(false) }}
        loading={saving} variant="primary" icon={Save} disabled={!value.trim()}/>
    </div>
  )
}

// ── Telegram Card ─────────────────────────────────────────────
function TelegramCard({ status, onSave, saving, onTest, testing }) {
  const { t } = useTranslation()
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
    <div className="bg-bg-3 border border-border shadow-lg rounded-2xl overflow-hidden transition-all duration-300">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center gap-4 px-5 py-4 hover:bg-bg-4 transition-all">
        <div className="w-10 h-10 rounded-xl bg-bg-4 border border-border flex items-center justify-center text-xl flex-shrink-0 shadow-inner">✈️</div>
        <div className="flex-1 min-w-0 text-left">
          <div className="text-lg font-bold text-ink uppercase tracking-tight">Telegram Bot</div>
          <div className="text-xs text-ink-3 font-semibold uppercase tracking-widest opacity-60">{t('telegram_desc')}</div>
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          <StatusBadge ok={configured}/>
          {polling.running && (
            <span className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-sky-400 bg-sky-400/10 border border-sky-400/30 px-3 py-1 rounded-full shadow-sm">
              <span className="w-2 h-2 rounded-full bg-sky-400 animate-pulse shadow-lg"/>Polling
            </span>
          )}
          {open ? <ChevronUp size={18} className="text-ink-3 flex-shrink-0"/> : <ChevronDown size={18} className="text-ink-3 flex-shrink-0"/>}
        </div>
      </button>

      <div className={clsx("grid transition-all duration-300 ease-in-out", open ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0")}>
        <div className="overflow-hidden">
          <div className="px-6 pb-6 pt-2 border-t-2 border-border/40">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-4">
                {configured && status?.telegram?.token_masked && !showTokenForm ? (
                  <div>
                    <Label>Bot Token</Label>
                    <div className="flex items-center gap-3 p-3 bg-bg-4 rounded-xl border border-border shadow-inner">
                      <div className="flex-1 min-w-0">
                        <div className="font-mono text-sm text-accent-2 truncate font-bold tracking-widest">{status.telegram.token_masked}</div>
                      </div>
                      <button onClick={() => setShowTF(true)}
                        className="text-[10px] uppercase tracking-widest text-ink-3 hover:text-accent-2 border border-border hover:border-accent/40 px-3 py-1.5 rounded-lg transition-all flex-shrink-0 font-bold shadow-sm active:scale-95 bg-bg-3">
                        Ganti
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {showTokenForm && (
                      <div className="flex items-center justify-between text-[11px] p-3 bg-warn/10 border border-warn/30 rounded-xl font-bold uppercase tracking-tight shadow-inner">
                        <span className="text-warn">Mengganti token tersimpan</span>
                        <button onClick={() => { setShowTF(false); setToken('') }} className="text-ink-3 hover:text-ink uppercase tracking-widest text-[10px]">✕ Batal</button>
                      </div>
                    )}
                    <SecretInput label="Bot Token" value={token} onChange={setToken}
                      placeholder="1234567890:ABCDEFxxxx"
                      hint="Dari @BotFather → /newbot atau /token"/>
                    <TextInput label="Webhook URL (opsional)" value={webhook} onChange={setWebhook}
                      placeholder="https://domain-kamu.com/api/integrations/telegram/webhook"
                      hint="Kosongkan untuk mode Polling (cocok localhost)" mono/>
                    <div className="flex gap-3">
                      <Btn label="Simpan" onClick={() => {
                        if (!token.trim()) { toast.error('Isi token terlebih dahulu'); return }
                        onSave('telegram', { TELEGRAM_BOT_TOKEN: token, ...(webhook ? { TELEGRAM_WEBHOOK_URL: webhook } : {}) })
                        setShowTF(false); setToken(''); setWebhook('')
                      }} loading={saving} variant="primary" icon={Save}/>
                      <Btn label="Test" onClick={onTest} loading={testing} variant="default" icon={Send}/>
                    </div>
                  </div>
                )}

                <div className="bg-bg-4 border border-border/40 rounded-2xl p-4 text-xs space-y-2 text-ink-3 font-semibold shadow-inner">
                  <div className="text-ink-2 font-bold mb-2 uppercase tracking-widest opacity-80">📱 {t('setup_guide')}:</div>
                  {[
                    ['Buka Telegram → cari', '@BotFather', ' → kirim /newbot'],
                    ['Ikuti instruksi → copy token'],
                    ['Tempel token di atas → Simpan'],
                    ['Klik Start Bot di kanan →'],
                  ].map((parts, i) => (
                    <div key={i}>{i + 1}. {parts.map((p, j) => (
                      p.startsWith('@') || p.startsWith('/') ? <code key={j} className="font-mono text-accent-2 font-bold">{p}</code> : p
                    ))}</div>
                  ))}
                  <div className="pt-2 font-mono text-accent-2 font-bold text-[11px] uppercase tracking-widest opacity-60">/start /help /clear /model</div>
                </div>
              </div>

              <div className="space-y-4">
                <div className={clsx('rounded-2xl border p-5 shadow-inner transition-all', polling.running ? 'bg-sky-400/5 border-sky-400/30' : 'bg-bg-4 border-border')}>
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      {polling.running ? <Wifi size={18} className="text-sky-400"/> : <WifiOff size={18} className="text-ink-3 opacity-60"/>}
                      <span className="text-sm font-bold text-ink uppercase tracking-tight">
                        {polling.running ? t('bot_active_polling') : t('bot_inactive')}
                      </span>
                    </div>
                    <label className={clsx("flex items-center gap-3", (!configured || pollingLoading) ? "opacity-50 cursor-not-allowed" : "cursor-pointer")}>
                      <span className="text-[10px] font-bold text-ink-3 uppercase tracking-widest">
                        {pollingLoading ? t('processing') : (polling.running ? 'On' : 'Off')}
                      </span>
                      <div onClick={() => {
                        if (!configured || pollingLoading) return;
                        if (polling.running) handleStop(); else handleStart();
                      }}
                        className={clsx('w-10 h-6 rounded-full relative transition-all shadow-inner border', polling.running ? 'bg-success border-success/30' : 'bg-bg-5 border-border')}>
                        <div className={clsx('absolute top-0.5 w-4 h-4 rounded-full bg-white shadow-lg transition-transform', polling.running ? 'translate-x-4.5' : 'translate-x-0.5')}/>
                      </div>
                    </label>
                  </div>

                  {polling.running && botInfo && (
                    <div className="text-xs text-sky-400 font-mono mb-3 font-bold uppercase tracking-tight border-b border-sky-400/20 pb-2">🤖 @{botInfo.username} ({botInfo.name})</div>
                  )}

                  <div className="text-xs text-ink-3 font-semibold leading-relaxed opacity-80">
                    {polling.running
                      ? t('bot_active_desc')
                      : configured
                        ? t('bot_inactive_desc')
                        : t('bot_setup_desc')
                    }
                  </div>
                </div>

                {!configured && (
                  <div className="p-4 bg-accent/8 border border-accent/20 rounded-2xl text-xs text-ink-2 font-semibold shadow-sm leading-relaxed">
                    <strong className="text-ink-2 block mb-2 text-sm font-bold uppercase tracking-widest opacity-80">💡 Tips Konektivitas:</strong>
                    Mode Polling dirancang untuk kemudahan setup tanpa memerlukan konfigurasi domain publik atau sertifikat SSL — sangat ideal untuk pengembangan di lingkungan localhost.
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
  const [editId, setEditId]       = useState(null)

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
      const r = editId 
        ? await intApi.updateCustomModel(editId, form) 
        : await intApi.addCustomModel(form)
      if (r.models) { useModelsStore.setState({ models: r.models }); syncModelsToOrchestrator(r.models) }
      toast.success(editId ? '✅ Provider berhasil diperbarui!' : '✅ Provider berhasil ditambahkan!')
      setShowAdd(false); setEditId(null); setForm(emptyForm); setTestResult(null); await load()
    } catch (e) { toast.error(e.message) }
    finally { setActing(a => ({ ...a, save: false })) }
  }

  const handleEdit = (p) => {
    setForm({ name: p.name, base_url: p.base_url, api_key: p.api_key || '', models: p.models, icon: p.icon || '🔌' })
    setEditId(p.id)
    setShowAdd(true)
    setTestResult(null)
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
    <div className="bg-bg-3 border border-border shadow-lg rounded-2xl overflow-hidden mt-0 transition-all duration-300">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between px-5 py-4 hover:bg-bg-4 transition-all">
        <div className="flex items-center gap-4 text-left">
          <div className="w-10 h-10 rounded-xl bg-bg-4 border border-border flex items-center justify-center text-xl flex-shrink-0 shadow-inner">🔌</div>
          <div>
            <div className="text-lg font-bold text-ink uppercase tracking-tight">Custom Model Provider</div>
            <div className="text-xs text-ink-3 font-semibold uppercase tracking-widest opacity-60">Tambah model API pihak ketiga (format OpenAI)</div>
          </div>
          {providers.length > 0 && <span className="ml-2 text-[10px] bg-accent/15 text-accent-2 px-2 py-1 rounded-full font-bold uppercase tracking-widest shadow-sm border border-accent/20">{providers.length} provider</span>}
        </div>
        {open ? <ChevronUp size={18} className="text-ink-3 flex-shrink-0"/> : <ChevronDown size={18} className="text-ink-3 flex-shrink-0"/>}
      </button>

      <div className={clsx("grid transition-all duration-500 ease-in-out", open ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0")}>
        <div className="overflow-hidden">
          <div className="p-6 space-y-4 border-t-2 border-border/40">
            <div className="flex justify-end mb-2">
              <Btn label="+ Tambah Provider" onClick={() => { setShowAdd(!showAdd); setEditId(null); setForm(emptyForm); setTestResult(null) }} variant="primary" icon={Plus} small/>
            </div>
            {showAdd && (
              <div className="bg-bg-4 border border-accent/25 rounded-2xl p-6 space-y-4 animate-fade shadow-xl">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-lg font-bold text-ink uppercase tracking-tight">{editId ? '✏️ Edit Model AI Provider' : '➕ Tambah Model AI Provider'}</span>
                  <button onClick={() => { setShowAdd(false); setEditId(null); setTestResult(null) }} className="text-ink-3 hover:text-ink text-sm font-bold">✕</button>
                </div>
                <div>
                  <Label>Ikon Provider</Label>
                  <div className="flex gap-2 flex-wrap">
                    {ICON_OPTIONS.map(ic => (
                      <button key={ic} onClick={() => setF('icon', ic)}
                        className={clsx('w-10 h-10 rounded-xl flex items-center justify-center text-xl border transition-all shadow-sm',
                          form.icon === ic ? 'border-accent bg-accent/15 shadow-accent/10' : 'border-border bg-bg-3 hover:border-border')}>
                        {ic}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <TextInput label="Nama Provider *" value={form.name} onChange={v => setF('name', v)} placeholder="Together AI, Groq, dll"/>
                  <TextInput label="Base URL *" value={form.base_url} onChange={v => setF('base_url', v)} placeholder="https://api.together.xyz/v1" mono/>
                </div>
                <SecretInput label="API Key *" value={form.api_key} onChange={v => setF('api_key', v)} placeholder="sk-..."/>
                <TextInput label="Model (pisah koma) *" value={form.models} onChange={v => setF('models', v)} placeholder="llama-3.1-70b,mixtral-8x7b" mono/>
                <div className="flex items-center gap-3">
                  <Btn label="Test Koneksi" onClick={handleTestConnection} loading={acting.testConn} variant="success" icon={Send}/>
                  {testResult && (
                    <div className={clsx('flex-1 text-[11px] px-4 py-3 rounded-xl font-bold uppercase tracking-tight shadow-inner border',
                      testResult.status === 'ok' ? 'bg-success/10 text-success border-success/30' : 'bg-danger/10 text-danger border-danger/30')}>
                      {testResult.message}
                    </div>
                  )}
                </div>
                <div className="flex items-center justify-end gap-3 pt-2">
                  <Btn label="Batal" onClick={() => { setShowAdd(false); setEditId(null); setTestResult(null) }} variant="default" small/>
                  <Btn label={editId ? 'Simpan Perubahan' : 'Simpan Provider'} onClick={handleSave} loading={acting.save} variant="primary" icon={Save}/>
                </div>
              </div>
            )}
            {loading ? (
              <div className="text-xs text-ink-3 flex items-center gap-2 py-2"><RefreshCw size={11} className="animate-spin"/>Memuat...</div>
            ) : providers.length === 0 && !showAdd ? (
              <div className="text-center py-6 text-xs text-ink-3">Belum ada custom provider.</div>
            ) : (
              <div className="space-y-3">
                {providers.map(p => {
                  const st = STATUS_STYLE[p.status] || STATUS_STYLE.untested
                  return (
                    <div key={p.id} className="bg-bg-4 rounded-2xl border border-border p-4 shadow-sm group/item">
                      <div className="flex items-start gap-4">
                        <span className="text-2xl flex-shrink-0 mt-1">{p.icon || '🔌'}</span>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-3 flex-wrap">
                            <span className="text-base font-bold text-ink uppercase tracking-tight">{p.name}</span>
                            <span className={clsx('text-[10px] px-2.5 py-1 rounded-full font-bold uppercase tracking-widest border', st.cls)}>{st.label}</span>
                          </div>
                          <div className="text-xs text-ink-3 mt-1.5 font-semibold opacity-70">Model: {p.models}</div>
                        </div>
                        <div className="flex items-center gap-2 flex-shrink-0">
                          <Btn label="Test" onClick={() => handleTest(p.id)} loading={acting[p.id+'_test']} variant="success" icon={Send} small/>
                          <button onClick={() => handleEdit(p)} className="p-2 rounded-xl text-ink-3 hover:text-accent hover:bg-accent/10 transition-all shadow-sm border border-transparent hover:border-accent/30" title="Edit">
                            <Code size={16} />
                          </button>
                          <button onClick={() => handleDelete(p.id)} disabled={acting[p.id+'_del']} className="p-2 rounded-xl text-ink-3 hover:text-danger hover:bg-danger/10 transition-all shadow-sm border border-transparent hover:border-danger/30" title="Hapus">
                            <Trash2 size={16}/>
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
    <div className="bg-bg-3 border border-border shadow-lg rounded-2xl overflow-hidden mt-0 transition-all duration-300">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between px-5 py-4 hover:bg-bg-4 transition-all">
        <div className="flex items-center gap-4 text-left">
          <div className="w-10 h-10 rounded-xl bg-bg-4 border border-border flex items-center justify-center text-accent-2 flex-shrink-0 shadow-inner"><Webhook size={20}/></div>
          <div>
            <div className="text-lg font-bold text-ink uppercase tracking-tight">Webhook Lanjutan</div>
            <div className="text-xs text-ink-3 font-semibold uppercase tracking-widest opacity-60">Kirim triggger ke Fonnte, n8n, Make, Zapier, dll</div>
          </div>
        </div>
        {open ? <ChevronUp size={18} className="text-ink-3 flex-shrink-0"/> : <ChevronDown size={18} className="text-ink-3 flex-shrink-0"/>}
      </button>

      <div className={clsx("grid transition-all duration-500 ease-in-out", open ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0")}>
        <div className="overflow-hidden">
          <div className="p-6 space-y-4 border-t-2 border-border/40">
            <div className="flex gap-3 justify-end mb-2">
              <Btn label="+ Tambah Webhook" onClick={() => { setShowAdd(!showAdd); setEditId(null); setForm(emptyForm) }} variant="primary" icon={Plus} small/>
            </div>
            {showAdd && (
              <div className="bg-bg-4 border border-accent/25 rounded-2xl p-6 space-y-4 animate-fade shadow-xl">
                <TextInput label="Nama Webhook *" value={form.name} onChange={v => setF('name', v)}/>
                <TextInput label="URL Endpoint *" value={form.url} onChange={v => setF('url', v)} mono/>
                <div className="flex items-center justify-end gap-3 pt-2">
                  <Btn label="Simpan Webhook" onClick={handleSave} loading={acting.save} variant="primary" icon={Save}/>
                </div>
              </div>
            )}
            {loading ? (
              <div className="text-xs text-ink-3"><RefreshCw size={11} className="animate-spin mr-2"/>Memuat...</div>
            ) : hooks.length === 0 ? (
              <div className="text-center py-6 text-xs text-ink-3">Belum ada webhook.</div>
            ) : (
              <div className="space-y-3">
                {hooks.map(h => {
                  const meta = pm(h.provider)
                  return (
                    <div key={h.id} className="bg-bg-4 rounded-2xl border border-border p-4 shadow-sm group/item">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-3 mb-1">
                            <span className="text-xl">{meta.emoji}</span>
                            <div className="text-base font-bold text-ink uppercase tracking-tight">{h.name}</div>
                          </div>
                          <div className="text-xs text-ink-3 font-mono truncate max-w-md font-bold opacity-60 bg-bg-2 px-2 py-1 rounded border border-border/40 inline-block">{h.url}</div>
                        </div>
                        <div className="flex gap-2 flex-shrink-0">
                          <Btn label="Test" onClick={() => handleTest(h.id)} loading={acting[h.id+'_test']} variant="success" icon={Send} small/>
                          <button onClick={() => handleDelete(h.id)} className="p-2 rounded-xl text-ink-3 hover:text-danger transition-all hover:bg-danger/10 shadow-sm" title="Hapus">
                            <Trash2 size={16}/>
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


// ── AiRoleMappingSection ──────────────────────────────────────
const AI_ROLE_DEFINITIONS = [
  { key: 'general',    emoji: '💬', label: 'Chat Umum',        desc: 'Percakapan, FAQ, pertanyaan ringan' },
  { key: 'coding',     emoji: '💻', label: 'Coding',           desc: 'Programming, debugging, code review' },
  { key: 'reasoning',  emoji: '🧠', label: 'Reasoning',        desc: 'Logika kompleks, analisis, matematika' },
  { key: 'writing',    emoji: '✍️', label: 'Penulisan',        desc: 'Konten, dokumentasi, terjemahan' },
  { key: 'research',   emoji: '🔍', label: 'Riset',            desc: 'Pencarian info, fact-checking, web' },
  { key: 'system',     emoji: '🖥️', label: 'Sistem/DevOps',   desc: 'VPS, terminal, server, networking' },
  { key: 'creative',   emoji: '🎨', label: 'Kreatif',          desc: 'Brainstorming, ide, storytelling' },
  { key: 'validation', emoji: '✅', label: 'Validasi/QA',      desc: 'Verifikasi, testing, fact-check' },
  { key: 'vision',     emoji: '👁️', label: 'Vision',          desc: 'Analisis gambar, OCR, deteksi objek' },
  { key: 'multimodal', emoji: '🌐', label: 'Multimodal',       desc: 'Teks + gambar + audio sekaligus' },
  { key: 'audio_gen',  emoji: '🔊', label: 'Audio / TTS',      desc: 'Text-to-speech, suara' },
  { key: 'image_gen',  emoji: '🖼️', label: 'Image Generation', desc: 'Buat gambar dari teks' },
]

const EMPTY_ROLES = Object.fromEntries(AI_ROLE_DEFINITIONS.map(r => [r.key, '']))

function AiRoleMappingSection({ settings, onSave, saving }) {
  const models = useModelsStore(s => s.models)
  const [roles, setRoles] = useState(EMPTY_ROLES)
  const [open, setOpen] = useState(false)
  // resolved: { role → { model_id, display, source: 'auto'|'manual' } }
  const [resolved, setResolved] = useState({})
  const [loadingResolved, setLoadingResolved] = useState(false)
  const [testingModel, setTestingModel] = useState({})

  useEffect(() => {
    if (settings?.ai_core?.role_mappings) {
      setRoles(prev => ({ ...EMPTY_ROLES, ...settings.ai_core.role_mappings }))
    }
  }, [settings])

  // Fetch resolved roles (what orchestrator actually picks) on open
  useEffect(() => {
    if (!open) return
    let cancelled = false
    const fetchResolved = async () => {
      setLoadingResolved(true)
      try {
        // Fetch current models list to keep mapping realtime
        const r = await api.listModels()
        const ms = r.models || []
        useModelsStore.setState({ models: ms })
        syncModelsToOrchestrator(ms)

        const data = await intApi.getResolvedRoles()
        if (!cancelled) setResolved(data.resolved || {})
      } catch {}
      finally { if (!cancelled) setLoadingResolved(false) }
    }
    fetchResolved()
    // Auto-refresh every 30s while panel is open
    const timer = setInterval(fetchResolved, 30000)
    return () => { cancelled = true; clearInterval(timer) }
  }, [open])

  const handleSave = async () => {
    try {
      await onSave(roles)
      toast.success('Pemetaan Role AI disimpan')
      // Refresh resolved after save
      try {
        const data = await intApi.getResolvedRoles()
        setResolved(data.resolved || {})
      } catch {}
    } catch (e) {
      toast.error(e.message)
    }
  }

  const handleTestTools = async (roleKey, modelId) => {
    if (!modelId) {
      toast.error('Belum ada model yang dipilih untuk diuji')
      return
    }
    setTestingModel(prev => ({ ...prev, [roleKey]: true }))
    try {
      const res = await intApi.testNativeTools(modelId)
      if (res.supported) {
        toast.success(res.message || `✅ Model ${modelId} mendukung Native Tools!`)
      } else {
        toast.error(`⚠️ Model ${modelId} tidak mendukung Native Tools:\n${res.message}`, { duration: 6000 })
      }
    } catch (e) {
      toast.error(`Gagal menguji tools: ${e.message}`)
    } finally {
      setTestingModel(prev => ({ ...prev, [roleKey]: false }))
    }
  }

  const configuredCount = Object.values(roles).filter(v => v).length

  return (
    <div className="bg-bg-3 border border-border shadow-lg rounded-2xl overflow-hidden mt-0 transition-all duration-300">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between px-5 py-4 hover:bg-bg-4 transition-all">
        <div className="flex items-center gap-4 text-left">
          <div className="w-10 h-10 rounded-xl bg-bg-4 border border-border flex items-center justify-center text-accent-2 flex-shrink-0 shadow-inner"><Zap size={20}/></div>
          <div>
            <div className="text-lg font-bold text-ink uppercase tracking-tight">AI Roles Mapping</div>
            <div className="text-xs text-ink-3 font-semibold uppercase tracking-widest opacity-60">
              Petakan setiap jenis tugas ke model spesifik — atau biarkan kosong untuk auto-routing
            </div>
          </div>
          {configuredCount > 0 && (
            <span className="ml-1 text-[10px] bg-accent/15 text-accent-2 px-2.5 py-1 rounded-full flex-shrink-0 font-bold uppercase tracking-widest border border-accent/20 shadow-sm">
              {configuredCount}/{AI_ROLE_DEFINITIONS.length} dikonfigurasi
            </span>
          )}
        </div>
        {open ? <ChevronUp size={18} className="text-ink-3 flex-shrink-0"/> : <ChevronDown size={18} className="text-ink-3 flex-shrink-0"/>}
      </button>

      <div className={clsx("grid transition-all duration-500 ease-in-out", open ? "grid-rows-[1fr] opacity-100" : "grid-rows-[0fr] opacity-0")}>
        <div className="overflow-hidden">
          <div className="p-6 space-y-6 border-t-2 border-border/40">

            {/* Info banner */}
            <div className="p-4 bg-accent/8 border border-accent/20 rounded-2xl text-xs text-ink-2 leading-relaxed font-semibold shadow-sm">
              <span className="font-bold text-ink-2 block mb-2 text-sm uppercase tracking-widest opacity-80">🤖 Auto-Routing Cerdas</span>
              Jika slot dikosongkan, AI Orchestrator otomatis memilih model terbaik berdasarkan kemampuan dan performa historis.
              Model yang dipilih sistem ditampilkan sebagai <span className="bg-blue-500/20 text-blue-400 px-2.5 py-1 rounded-lg text-[10px] font-bold uppercase tracking-widest shadow-sm border border-blue-500/30">🤖 Auto</span>.
            </div>

            {/* Role grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {AI_ROLE_DEFINITIONS.map(role => {
                const manualVal  = roles[role.key] || ''
                const res        = resolved[role.key]
                const autoModel  = res?.model_id || ''
                const autoDisplay= res?.display  || autoModel
                const isManual   = !!manualVal
                const activeModel= isManual ? manualVal : autoModel

                return (
                  <div key={role.key} className="bg-bg-4 rounded-xl border border-border p-3 space-y-2">
                    {/* Header row */}
                    <div className="flex items-center gap-2">
                      <span className="text-base">{role.emoji}</span>
                      <div className="min-w-0 flex-1">
                        <div className="text-sm font-semibold text-ink">{role.label}</div>
                        <div className="text-xs text-ink-3 truncate font-medium">{role.desc}</div>
                      </div>
                      {/* Status badge */}
                      {isManual ? (
                        <span className="flex-shrink-0 text-[11px] bg-success/15 text-success px-1.5 py-0.5 rounded-full font-semibold">
                          ✏️ Manual
                        </span>
                      ) : autoModel ? (
                        <span className="flex-shrink-0 text-[11px] bg-blue-500/15 text-blue-400 px-1.5 py-0.5 rounded-full font-semibold">
                          🤖 Auto
                        </span>
                      ) : null}
                    </div>

                    {/* Resolved model display (when not manually set) */}
                    {!isManual && autoDisplay && (
                      <div className="text-xs text-ink-2 bg-bg-2 rounded-lg px-2.5 py-1.5 border border-border/60 truncate font-medium">
                        <span className="text-ink-3 mr-1">Aktif:</span>
                        <span className="font-semibold text-blue-400">{autoDisplay}</span>
                      </div>
                    )}

                    {/* Dropdown */}
                    <div className="relative">
                      <select
                        value={manualVal}
                        onChange={e => setRoles(r => ({ ...r, [role.key]: e.target.value }))}
                        className="w-full bg-bg-2 border border-border rounded-lg px-3 py-1.5 text-xs text-ink outline-none focus:border-accent appearance-none cursor-pointer pr-7 font-medium"
                      >
                        <option value="">
                          {loadingResolved ? '⏳ Memuat...' : autoDisplay ? `🤖 Auto — ${autoDisplay}` : '🤖 Auto (pilih terbaik)'}
                        </option>
                        {models.map(m => (
                          <option key={m.id} value={m.id}>
                            {m.display || m.id} ({m.provider})
                          </option>
                        ))}
                      </select>
                      <div className="absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none text-ink-3">
                        <ChevronDown size={11}/>
                      </div>
                    </div>
                    
                    {/* Test Native Tools Button */}
                    <div className="pt-1">
                      <Btn 
                        label="Test Native Tools" 
                        onClick={() => handleTestTools(role.key, activeModel)} 
                        loading={testingModel[role.key]} 
                        variant="default" 
                        small 
                        full
                        icon={Zap}
                      />
                    </div>
                  </div>
                )
              })}
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-border/50">
              <p className="text-xs text-ink-3 italic font-medium">
                * Auto-routing belajar dari performa historis dan menyesuaikan diri secara otomatis.
              </p>
              <Btn label="Simpan Pemetaan" onClick={handleSave} loading={saving} variant="primary" icon={Save}/>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Google Ecosystem Section (GOG CLI) ───────────────────────
const gog_api = {
  status:       () => api.get('/integrations/google/status'),
  getAuthUrl:   (credentials_json, redirect_uri) => api.post('/integrations/google/auth/url', { credentials_json, redirect_uri }),
  callback:     (code, redirect_uri) => api.post('/integrations/google/auth/callback', { code, redirect_uri }),
  disconnect:   () => api.delete('/integrations/google/disconnect'),
}

function GoogleEcosystemSection() {
  const [open, setOpen] = useState(false)
  const [configured, setConfigured] = useState(false)
  const [hasCredentials, setHasCredentials] = useState(false)
  const [credsJson, setCredsJson] = useState('')
  const [authStep, setAuthStep] = useState('idle') // idle | pasting | authorizing | callback
  const [authCode, setAuthCode] = useState('')
  const [authUrl, setAuthUrl] = useState('')
  const [acting, setActing] = useState(false)
  const [disconnecting, setDisconnecting] = useState(false)

  const redirectUri = `${window.location.origin}/integrations/google/callback`

  const loadStatus = async () => {
    try {
      const r = await gog_api.status()
      setConfigured(r.configured)
      setHasCredentials(r.has_credentials_file)
    } catch {}
  }

  useEffect(() => { loadStatus() }, [])

  const handleGetAuthUrl = async () => {
    if (!credsJson.trim()) { toast.error('Tempel isi credentials.json terlebih dahulu'); return }
    setActing(true)
    try {
      const r = await gog_api.getAuthUrl(credsJson.trim(), redirectUri)
      setAuthUrl(r.auth_url)
      setAuthStep('authorizing')
      window.open(r.auth_url, '_blank')
    } catch (e) {
      toast.error(`Gagal: ${e.message}`)
    } finally { setActing(false) }
  }

  const handleCallback = async () => {
    if (!authCode.trim()) { toast.error('Masukkan authorization code'); return }
    setActing(true)
    try {
      await gog_api.callback(authCode.trim(), redirectUri)
      toast.success('🎉 Google Ecosystem berhasil terhubung!')
      setAuthStep('idle'); setCredsJson(''); setAuthCode(''); setAuthUrl('')
      await loadStatus()
    } catch (e) {
      toast.error(`Gagal: ${e.message}`)
    } finally { setActing(false) }
  }

  const handleDisconnect = async () => {
    if (!confirm('Putuskan koneksi Google? Semua token akan dihapus.')) return
    setDisconnecting(true)
    try {
      await gog_api.disconnect()
      toast('🔌 Terputus dari Google Ecosystem', { icon: '🔌' })
      setConfigured(false); setHasCredentials(false)
    } catch (e) { toast.error(e.message) }
    finally { setDisconnecting(false) }
  }

  const SERVICES = [
    { icon: '📧', name: 'Gmail', desc: 'Baca & kirim email', cmd: 'gog_read_emails / gog_send_email' },
    { icon: '📅', name: 'Google Calendar', desc: 'Buat & lihat jadwal', cmd: 'gog_create_calendar_event / gog_list_calendar_events' },
    { icon: '📊', name: 'Google Sheets', desc: 'Baca & tulis data spreadsheet', cmd: 'gog_read_sheet / gog_append_sheet_row' },
    { icon: '📁', name: 'Google Drive', desc: 'Cari & daftarkan file', cmd: 'gog_list_drive_files' },
  ]

  return (
    <div className="bg-bg-3 border border-border shadow-sm rounded-xl overflow-hidden">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center gap-3 px-4 py-3.5 hover:bg-bg-4 transition-colors">
        <div className="w-8 h-8 rounded-lg flex items-center justify-center text-lg flex-shrink-0" style={{background:'linear-gradient(135deg,#4285f4,#34a853,#fbbc05,#ea4335)'}}>
          <span>G</span>
        </div>
        <div className="flex-1 min-w-0 text-left">
          <div className="text-base font-semibold text-ink">GOG CLI — Google Ecosystem</div>
          <div className="text-xs text-ink-3 font-medium">Gmail · Calendar · Sheets · Drive — dikendalikan oleh AI</div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {configured
            ? <span className="flex items-center gap-1 text-xs font-semibold text-success bg-success/10 border border-success/20 px-2 py-0.5 rounded-full"><CheckCircle2 size={10}/>Terhubung</span>
            : <span className="flex items-center gap-1 text-xs font-semibold text-ink-3 bg-bg-4 border border-border px-2 py-0.5 rounded-full"><XCircle size={10}/>Belum Setup</span>
          }
          {open ? <ChevronUp size={14} className="text-ink-3"/> : <ChevronDown size={14} className="text-ink-3"/>}
        </div>
      </button>

      <div className={clsx('grid transition-all duration-300 ease-in-out', open ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0')}>
        <div className="overflow-hidden">
          <div className="px-4 pb-5 pt-3 border-t border-border space-y-4">

            {/* Services Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              {SERVICES.map(s => (
                <div key={s.name} className={clsx('rounded-xl border p-3 text-center transition-all', configured ? 'bg-success/5 border-success/20' : 'bg-bg-4 border-border opacity-60')}>
                  <div className="text-2xl mb-1">{s.icon}</div>
                  <div className="text-xs font-semibold text-ink">{s.name}</div>
                  <div className="text-[11px] text-ink-3 mt-0.5 font-medium">{s.desc}</div>
                </div>
              ))}
            </div>

            {configured ? (
              <div className="space-y-3">
                <div className="bg-success/5 border border-success/20 rounded-xl p-3.5 flex items-center gap-3">
                  <CheckCircle2 size={18} className="text-success flex-shrink-0"/>
                  <div>
                    <div className="text-sm font-semibold text-ink">Google Ecosystem Aktif</div>
                    <div className="text-xs text-ink-3 mt-0.5 font-medium">AI dapat mengakses Gmail, Calendar, Sheets, dan Drive Anda secara otonom.</div>
                  </div>
                </div>
                <div className="bg-bg-4 rounded-xl p-3 border border-border">
                  <div className="text-xs text-ink-2 font-semibold mb-2">💡 Contoh Perintah</div>
                  <div className="space-y-1.5">
                    {[
                      '"Cek email baru dari bos saya"',
                      '"Jadwalkan meeting besok jam 10 pagi"',
                      '"Tambahkan data ini ke Google Sheets"',
                      '"Carikan file laporan Q1 di Drive saya"',
                    ].map((cmd, i) => (
                      <div key={i} className="text-xs text-ink-3 font-mono flex items-start gap-2 font-medium">
                        <span className="text-accent-2">→</span> {cmd}
                      </div>
                    ))}
                  </div>
                </div>
                <Btn label="Putuskan Koneksi Google" onClick={handleDisconnect} loading={disconnecting} variant="danger" icon={XCircle} full/>
              </div>
            ) : (
              <div className="space-y-4">
                {/* Setup Instructions */}
                <div className="bg-accent/5 border border-accent/20 rounded-xl p-3.5 space-y-2">
                  <div className="text-sm font-semibold text-ink">📋 Cara Setup (3 langkah)</div>
                  {[
                    ['Buka', 'console.cloud.google.com', '→ buat project baru'],
                    ['Aktifkan API: Gmail, Calendar, Sheets, Drive di', 'Library'],
                    ['Buat', 'OAuth 2.0 Client ID', '(tipe: Desktop App) → Download JSON'],
                  ].map((parts, i) => (
                    <div key={i} className="text-xs text-ink-3 flex gap-1.5 font-medium">
                      <span className="text-accent-2 font-semibold flex-shrink-0">{i+1}.</span>
                      <span>{parts.map((p, j) => p.startsWith('console') || p === 'Library' || p === 'OAuth 2.0 Client ID'
                        ? <code key={j} className="font-mono text-accent-2 bg-accent/10 px-1 rounded font-semibold">{p}</code>
                        : p
                      )}</span>
                    </div>
                  ))}
                </div>

                {authStep === 'idle' && (
                  <div className="space-y-2">
                    <Label>Isi credentials.json (tempel seluruh teks JSON)</Label>
                    <textarea
                      value={credsJson}
                      onChange={e => setCredsJson(e.target.value)}
                      rows={6}
                      placeholder={'{ "installed": { "client_id": "...", "client_secret": "...", ... } }'}
                      className="w-full bg-bg-2 border border-border rounded-lg px-3 py-2 text-xs text-ink placeholder-ink-3 outline-none focus:border-accent font-mono resize-none"
                    />
                    <Btn label="Otorisasi dengan Google →" onClick={handleGetAuthUrl} loading={acting} variant="primary" icon={Globe} full/>
                  </div>
                )}

                {authStep === 'authorizing' && (
                  <div className="space-y-3">
                    <div className="bg-warn/8 border border-warn/25 rounded-xl p-3.5 space-y-2">
                      <div className="text-sm font-semibold text-warn">⏳ Langkah 2 dari 2</div>
                      <div className="text-xs text-ink-3 font-medium">
                        Tab Google baru telah dibuka. Setelah Anda memberi izin, Google akan menampilkan <strong className="text-ink">Authorization Code</strong>. Salin kode tersebut dan tempel di bawah.
                      </div>
                      <button onClick={() => window.open(authUrl, '_blank')} className="text-xs text-accent underline font-semibold">Buka ulang halaman Google</button>
                    </div>
                    <div>
                      <Label>Authorization Code</Label>
                      <input
                        type="text"
                        value={authCode}
                        onChange={e => setAuthCode(e.target.value)}
                        placeholder="4/0AX4..."
                        className="w-full bg-bg-2 border border-border rounded-lg px-3 py-2 text-xs text-ink placeholder-ink-3 outline-none focus:border-accent font-mono"
                      />
                    </div>
                    <div className="flex gap-2">
                      <Btn label="Batal" onClick={() => { setAuthStep('idle'); setAuthUrl('') }} variant="default"/>
                      <Btn label="Selesaikan Otorisasi" onClick={handleCallback} loading={acting} variant="success" icon={CheckCircle2} full/>
                    </div>
                  </div>
                )}
              </div>
            )}
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
  const [tavilyKey,      setTavilyKey]      = useState('')

  const [activeTab, setActiveTab] = useState(() => localStorage.getItem('int_active_tab') || 'messaging')
  useEffect(() => { localStorage.setItem('int_active_tab', activeTab) }, [activeTab])

  const TABS = [
    { id: 'messaging', label: 'Messaging', icon: '💬' },
    { id: 'model_ai',  label: 'Model AI',  icon: '🤖' },
    { id: 'google',    label: 'Google',    icon: '🟢' },
    { id: 'webhook',   label: 'Webhook & Otomasi', icon: '🔗' },
    { id: 'search',    label: 'Pencarian AI', icon: '🔍' },
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
          <h1 className="text-xl font-semibold text-ink">Integrasi Platform</h1>
          <p className="text-sm text-ink-3 mt-0.5">API key & koneksi layanan eksternal</p>
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
            className={clsx('flex items-center gap-2 px-4 py-2.5 text-sm font-semibold transition-all whitespace-nowrap border-b-2 outline-none',
              activeTab === t.id ? 'border-accent text-accent' : 'border-transparent text-ink-3 hover:text-ink hover:border-border')}>
            <span className="text-xl">{t.icon}</span> {t.label}
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
                  <div className="flex-1"><TextInput label="Model AI (opsional, pisahkan koma)" value={anthropicModels} onChange={setAnthropicModels} placeholder="contoh: claude-haiku-4-5" mono/></div>
                  {status?.anthropic?.configured && <Btn label="Simpan" onClick={() => save('anthropic', { ANTHROPIC_AVAILABLE_MODELS: anthropicModels })} loading={saving.anthropic} variant="default" icon={Save}/>}
                </div>
              </div>
            </Card>
            <Card icon="💎" title="Google Gemini" subtitle="Gemini 1.5" configured={status?.google?.configured}>
              <div className="mt-3 space-y-2.5">
                <MaskedField masked={status?.google?.key_masked} label="API Key" value={googleKey} onChange={setGoogleKey} onSave={() => save('google', { GOOGLE_API_KEY: googleKey, GOOGLE_AVAILABLE_MODELS: googleModels })} saving={saving.google}/>
                <div className="flex gap-2 items-end">
                  <div className="flex-1"><TextInput label="Model AI (opsional, pisahkan koma)" value={googleModels} onChange={setGoogleModels} placeholder="contoh: gemini-2.5-flash" mono/></div>
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
          <AiRoleMappingSection 
            settings={status} 
            onSave={(roles) => intApi.saveAiRoles(roles)} 
            saving={saving.ai_roles} 
          />
          <CustomModelSection/>
        </div>



        <div className={clsx(activeTab !== 'google' && 'hidden')}>
          <GoogleEcosystemSection/>
        </div>

        <div className={clsx(activeTab !== 'webhook' && 'hidden')}>
          <WebhookSection/>
        </div>

        <div className={clsx(activeTab !== 'search' && "hidden")}>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            <Card icon="🔍" title="Tavily" subtitle="AI Search Engine" configured={status?.tavily?.configured}>
              <div className="mt-3 space-y-2.5">
                <MaskedField masked={status?.tavily?.key_masked} label="API Key" value={tavilyKey} onChange={setTavilyKey} onSave={() => save('tavily', { TAVILY_API_KEY: tavilyKey })} saving={saving.tavily}/>
                <div className="p-3 bg-bg-4 border border-border rounded-xl text-xs text-ink-3 font-medium">
                  <strong className="text-ink block mb-1 text-sm font-semibold">Pencarian Cerdas</strong>
                  Tavily dirancang khusus untuk agen AI. Dengan API Key ini, AI dapat mengakses informasi terkini secara real-time dari internet.
                </div>
              </div>
            </Card>
          </div>
        </div>

        <div className={clsx(activeTab !== 'api_docs' && "hidden")}>
          <div className="bg-bg-3 border border-border shadow-sm rounded-xl p-4">
            <h2 className="text-base font-semibold text-ink mb-3">🔌 REST API Endpoints</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-1.5 text-xs font-mono text-ink-2 font-semibold">
              <div className="p-2 bg-bg-4 rounded-lg border border-border">POST /api/chat/send</div>
              <div className="p-2 bg-bg-4 rounded-lg border border-border">GET /api/models</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
