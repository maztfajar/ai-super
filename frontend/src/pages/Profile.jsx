import { useState, useEffect, useRef } from 'react'
import { api } from '../hooks/useApi'
import { useAuthStore } from '../store'
import toast from 'react-hot-toast'
import {
  User, Save, RefreshCw, Eye, EyeOff, CheckCircle2,
  Upload, Maximize2, Info, LayoutDashboard,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import clsx from 'clsx'

// ── Primitives ────────────────────────────────────────────────
function Label({ children }) {
  return <label className="block text-xs text-ink-3 mb-2 uppercase tracking-widest font-bold opacity-60">{children}</label>
}

function TextInp({ value, onChange, placeholder, disabled, maxLength, label }) {
  return (
    <div>
      {label && <Label>{label}</Label>}
      <input
        type="text" value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder} disabled={disabled} maxLength={maxLength}
        className="w-full bg-bg-2 border border-border rounded-xl px-4 py-3 text-sm font-bold text-ink placeholder-ink-3 outline-none focus:border-accent disabled:opacity-50 transition-all shadow-inner"
      />
    </div>
  )
}

function PassInp({ value, onChange, placeholder, label, onKeyDown }) {
  const [show, setShow] = useState(false)
  return (
    <div>
      {label && <Label>{label}</Label>}
      <div className="relative">
        <input
          type={show ? 'text' : 'password'} value={value}
          onChange={e => onChange(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={placeholder} autoComplete="new-password"
          className="w-full bg-bg-2 border border-border rounded-xl px-4 py-3 pr-10 text-sm text-ink placeholder-ink-3 outline-none focus:border-accent transition-all font-mono shadow-inner font-bold"
        />
        <button type="button" onClick={() => setShow(!show)}
          className="absolute right-3.5 top-1/2 -translate-y-1/2 text-ink-3 hover:text-ink transition-all">
          {show ? <EyeOff size={16}/> : <Eye size={16}/>}
        </button>
      </div>
    </div>
  )
}

// ── Password Strength ─────────────────────────────────────────
function PwStrength({ pw }) {
  if (!pw) return null
  const checks = [
    { ok: pw.length >= 8,           label: 'Min 8' },
    { ok: /[A-Z]/.test(pw),         label: 'Huruf besar' },
    { ok: /[0-9]/.test(pw),         label: 'Angka' },
    { ok: /[^a-zA-Z0-9]/.test(pw),  label: 'Simbol' },
  ]
  const score = checks.filter(c => c.ok).length
  const bar   = ['bg-danger','bg-danger','bg-warn','bg-warn','bg-success']
  const lbl   = ['Lemah','Lemah','Cukup','Kuat','Sangat Kuat']
  return (
    <div className="mt-2 space-y-1.5">
      <div className="flex gap-1 h-1.5">
        {[0,1,2,3].map(i => (
          <div key={i} className={clsx('flex-1 rounded-full', i < score ? bar[score] : 'bg-bg-5')}/>
        ))}
      </div>
      <div className="flex items-center justify-between flex-wrap gap-2">
        <span className={clsx('text-xs font-bold uppercase tracking-widest opacity-80',
          score <= 1 ? 'text-danger' : score <= 2 ? 'text-warn' : 'text-success')}>
          {lbl[score]}
        </span>
        <div className="flex gap-3 flex-wrap">
          {checks.map(c => (
            <span key={c.label} className={clsx('text-[10px] font-bold uppercase tracking-tight', c.ok ? 'text-success' : 'text-ink-3 opacity-50')}>
              {c.ok ? '✓' : '○'} {c.label}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Logo Uploader ─────────────────────────────────────────────
function LogoUploader({ current, onFileSelected }) {
  const ref = useRef()
  const [preview, setPreview] = useState(current || '')
  const [info,    setInfo]    = useState(null)
  const [drag,    setDrag]    = useState(false)
  const [dim,     setDim]     = useState({ w:0, h:0 })

  useEffect(() => { if (current) setPreview(current) }, [current])

  const process = (file) => {
    if (!file) return
    if (!file.type.startsWith('image/')) { toast.error('File harus berupa gambar'); return }
    if (file.size > 2*1024*1024) { toast.error('Maks 2MB'); return }
    const reader = new FileReader()
    reader.onload = ev => {
      const url = ev.target.result
      setPreview(url)
      setInfo({ name: file.name, size: (file.size/1024).toFixed(0)+' KB' })
      const img = new window.Image()
      img.onload = () => setDim({ w: img.naturalWidth, h: img.naturalHeight })
      img.src = url
      onFileSelected(file)
    }
    reader.readAsDataURL(file)
  }

  return (
    <div className="space-y-3">
      <div
        onClick={() => ref.current?.click()}
        onDragOver={e => { e.preventDefault(); setDrag(true) }}
        onDragLeave={() => setDrag(false)}
        onDrop={e => { e.preventDefault(); setDrag(false); process(e.dataTransfer.files?.[0]) }}
        className={clsx('border border-dashed rounded-xl p-4 cursor-pointer transition-all',
          drag ? 'border-accent bg-accent/8' : 'border-border hover:border-accent/50 hover:bg-bg-4')}>
        <input ref={ref} type="file" accept="image/*" className="hidden"
          onChange={e => process(e.target.files?.[0])}/>
        <div className="flex items-center gap-4">
          {/* Preview */}
          <div className="flex flex-col items-center gap-2 flex-shrink-0">
            <div className="w-16 h-16 rounded-xl border border-border bg-bg-5 flex items-center justify-center overflow-hidden">
              {preview ? <img src={preview} className="w-full h-full object-contain" alt="preview"/> : <span className="text-2xl">🧠</span>}
            </div>
            <div className="flex items-center gap-1">
              <div className="w-8 h-8 rounded-lg border border-border bg-bg-5 flex items-center justify-center overflow-hidden">
                {preview ? <img src={preview} className="w-full h-full object-contain" alt="sm"/> : <span className="text-sm">🧠</span>}
              </div>
              <span className="text-[11px] text-ink-3 font-semibold">32px</span>
            </div>
          </div>
          {/* Info */}
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <Upload size={16} className={drag ? 'text-accent-2' : 'text-ink-3'}/>
              <span className="text-sm font-bold text-ink uppercase tracking-tight">{drag ? 'Lepas di sini!' : 'Klik atau drag & drop'}</span>
            </div>
            {info ? (
              <div className="space-y-1 mt-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <CheckCircle2 size={14} className="text-success"/>
                  <span className="text-xs text-success font-bold">{info.name}</span>
                  <span className="text-xs text-ink-3 font-semibold">{info.size}</span>
                  {dim.w > 0 && (
                    <span className={clsx('text-[10px] font-mono px-2 py-0.5 rounded-full font-bold',
                      dim.w >= 64 ? 'bg-success/15 text-success' : 'bg-warn/15 text-warn')}>
                      {dim.w}×{dim.h}
                    </span>
                  )}
                </div>
              </div>
            ) : (
              <span className="text-xs text-ink-3 font-semibold uppercase tracking-widest opacity-60">PNG/JPG/WebP/SVG · maks 2MB</span>
            )}
          </div>
        </div>
      </div>

      <div className="bg-bg-4 border border-border/40 rounded-2xl p-4 shadow-inner">
        <div className="flex items-center gap-2 mb-3">
          <Maximize2 size={16} className="text-accent-2"/>
          <span className="text-sm font-bold text-ink-2 uppercase tracking-widest opacity-80">Panduan Ukuran (Pixel)</span>
        </div>
        <div className="grid grid-cols-4 gap-2 mb-3">
          {[{px:32,label:'Sidebar'},{px:64,label:'Min'},{px:128,label:'⭐ Ideal'},{px:256,label:'Optimal'}].map(s => (
            <div key={s.px} className={clsx('rounded-xl p-2.5 border text-center transition-all',
              s.px === 128 ? 'border-accent/40 bg-accent/10' : 'border-border bg-bg-3')}>
              <div className={clsx('text-sm font-bold font-mono tracking-tighter', s.px===128?'text-accent-2':'text-ink-2')}>{s.px}</div>
              <div className="text-[10px] text-ink-3 font-bold uppercase tracking-tight opacity-60">{s.label}</div>
            </div>
          ))}
        </div>
        <div className="text-xs text-ink-3 space-y-1.5 font-semibold leading-relaxed">
          <div>💡 Tampil <span className="font-mono text-accent-2 font-bold">32px</span> di sidebar — upload min <span className="font-mono text-accent-2 font-bold">128px</span></div>
          <div>💡 Gunakan PNG transparan untuk tampilan terbaik</div>
        </div>
      </div>
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────
export default function Profile() {
  const { t } = useTranslation()
  const { user, setAuth, token } = useAuthStore()
  const [loading, setLoading]  = useState(true)
  const [profile, setProfile]  = useState(null)

  // Akun
  const [newUser,  setNewUser]  = useState('')
  const [newPass,  setNewPass]  = useState('')
  const [confPass, setConfPass] = useState('')
  const [savingP,  setSavingP]  = useState(false)

  // App
  const [appName,  setAppName]  = useState('')
  const [logoFile, setLogoFile] = useState(null)
  const [logoSrc,  setLogoSrc]  = useState('')
  const [savingA,   setSavingA]  = useState(false)
  const [savedOk,   setSavedOk]  = useState(false)
  const [origName,  setOrigName]  = useState('')  // nama asli untuk deteksi perubahan

  const isAdmin = user?.is_admin

  useEffect(() => {
    const load = async () => {
      try {
        const me = await api.me()
        setProfile(me)
        setNewUser(me.username || '')
      } catch(e) {
        toast.error('Gagal memuat profil: ' + (e.message || ''))
      }
      try {
        const ap = await api.getAppProfile()
        if (ap?.app_name) { const n=ap.app_name.replace(/^["']|["']$/g,''); setAppName(n); setOrigName(n) }
        if (ap?.logo_b64) setLogoSrc(ap.logo_b64)
      } catch {}
      setLoading(false)
    }
    load()
  }, [])

  // ── Save profil akun ───────────────────────────────────────
  const handleSaveProfile = async () => {
    if (newPass && newPass !== confPass) { toast.error('Password tidak cocok'); return }
    if (newPass && newPass.length < 6)   { toast.error('Password minimal 6 karakter'); return }

    const usernameChanged = newUser.trim() !== '' && newUser.trim() !== (profile?.username || '')
    const passwordChanged = newPass.trim().length >= 6

    if (!usernameChanged && !passwordChanged) {
      toast('Tidak ada perubahan untuk disimpan', { icon: 'ℹ️' }); return
    }

    setSavingP(true)
    try {
      const payload = {}
      if (usernameChanged) payload.new_username = newUser.trim()
      if (passwordChanged) payload.new_password = newPass.trim()

      const res = await api.updateProfile(payload)

      if (res?.status === 'updated') {
        toast.success('✓ Profil berhasil disimpan!')
        setNewPass('')
        setConfPass('')
        if (res.access_token && res.user) {
          setAuth(res.access_token, res.user)
          setProfile(res.user)
          setNewUser(res.user.username || '')
        }
      } else {
        toast(res?.message || 'Tidak ada perubahan', { icon: 'ℹ️' })
      }
    } catch(e) {
      const msg = e.message || ''
      if (msg.includes('Username sudah')) toast.error('Username sudah dipakai, pilih yang lain')
      else if (msg.includes('401') || msg.includes('Unauthorized')) toast.error('Sesi habis, silakan login ulang')
      else toast.error('Gagal menyimpan: ' + (msg || 'Unknown error'))
    } finally {
      setSavingP(false)
    }
  }

  // ── Save logo & nama app ───────────────────────────────────
  const handleSaveApp = async () => {
    const nameChanged = appName.trim() !== '' && appName.trim() !== origName
    if (!nameChanged && !logoFile) { toast.error('Ubah nama atau pilih logo terlebih dahulu'); return }

    setSavingA(true)
    try {
      const res = await api.updateAppProfile(
        nameChanged ? appName.trim() : undefined,
        logoFile instanceof File ? logoFile : undefined
      )

      if (res?.status === 'no_change') {
        toast('Tidak ada perubahan', { icon: 'ℹ️' })
      } else {
        setSavedOk(true)
        setTimeout(() => setSavedOk(false), 6000)
        setLogoFile(null)
        // Reload dari server
        const fresh = await api.getAppProfile().catch(() => null)
        if (fresh?.logo_b64) setLogoSrc(fresh.logo_b64)
        if (fresh?.app_name) { const n=fresh.app_name.replace(/^["']|["']$/g,''); setAppName(n); setOrigName(n) }
        // Trigger sidebar update
        window.dispatchEvent(new Event('ai-orchestrator:profile-updated'))
        toast.success(logoFile ? 'Logo & nama disimpan!' : 'Nama aplikasi disimpan!')
      }
    } catch(e) {
      toast.error('Gagal simpan: ' + (e.message || ''))
    } finally {
      setSavingA(false)
    }
  }

  const canSave = (newUser.trim() !== (profile?.username || '') && newUser.trim() !== '') || newPass.length >= 6

  if (loading) return (
    <div className="p-6 flex items-center gap-3 text-ink-3 text-sm font-bold uppercase tracking-widest">
      <RefreshCw size={18} className="animate-spin"/>{t('loading') || 'Loading...'}
    </div>
  )

  return (
    <div className="p-4 md:p-6 w-full">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-ink uppercase tracking-tighter">{t('edit_profile_title')}</h1>
        <p className="text-base text-ink-3 mt-1 font-semibold uppercase tracking-tight opacity-70">{t('manage_account_desc')}</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 items-start">

        {/* ── Kartu Akun ── */}
        <div className="bg-bg-3 border border-border rounded-2xl overflow-hidden shadow-lg">
          <div className="flex items-center gap-3 px-5 py-4 border-b-2 border-border">
            <User size={18} className="text-accent-2"/>
            <span className="text-base font-bold text-ink uppercase tracking-tight">{t('account_profile')}</span>
          </div>
          <div className="p-6 space-y-5">

            {/* Avatar + info */}
            <div className="flex items-center gap-5 pb-6 border-b-2 border-border">
              <div className="w-16 h-16 rounded-full bg-gradient-to-br from-accent to-pink flex items-center justify-center text-3xl font-bold text-white flex-shrink-0 select-none shadow-lg">
                {(newUser || user?.username || 'A')[0].toUpperCase()}
              </div>
              <div>
                <div className="text-lg font-bold text-ink tracking-tight">{profile?.username || user?.username}</div>
                <div className="text-sm text-ink-3 font-semibold opacity-80">{profile?.email || ''}</div>
                <div className={clsx('text-[10px] mt-2 px-3 py-1 rounded-full inline-block font-bold uppercase tracking-widest shadow-sm',
                  isAdmin ? 'bg-accent/15 text-accent-2 border border-accent/30' : 'bg-bg-4 text-ink-3 border border-border')}>
                  {isAdmin ? `👑 ${t('admin_label')}` : `👤 ${t('sub_admin_label')}`}
                </div>
              </div>
            </div>

            {/* Form */}
            <TextInp
              label="Username"
              value={newUser}
              onChange={setNewUser}
              placeholder={profile?.username || 'username'}
              maxLength={32}
            />

            <PassInp
              label={t('new_password_label')}
              value={newPass}
              onChange={setNewPass}
              placeholder="password baru..."
              onKeyDown={e => { if (e.key === 'Enter' && canSave && !savingP) handleSaveProfile() }}
            />
            <PwStrength pw={newPass}/>

            {newPass && (
              <PassInp
                label="Konfirmasi Password"
                value={confPass}
                onChange={setConfPass}
                placeholder="ketik ulang..."
                onKeyDown={e => { if (e.key === 'Enter' && canSave && !savingP) handleSaveProfile() }}
              />
            )}
            {confPass && newPass !== confPass && (
              <p className="text-[11px] text-danger font-bold uppercase tracking-widest mt-1">⚠ Password tidak cocok</p>
            )}
            {confPass && newPass === confPass && newPass.length >= 6 && (
              <p className="text-[11px] text-success font-bold uppercase tracking-widest mt-1">✓ Password cocok</p>
            )}

            <button onClick={handleSaveProfile} disabled={savingP || !canSave}
              className="w-full flex items-center justify-center gap-3 py-3.5 bg-accent hover:bg-accent/80 disabled:opacity-40 text-white text-sm font-bold uppercase tracking-widest rounded-xl transition-all shadow-md active:scale-95">
              {savingP ? <RefreshCw size={16} className="animate-spin"/> : <Save size={16}/>}
              {savingP ? t('saving') : t('save_account_changes')}
            </button>

            <div className="bg-bg-4 border border-border/40 rounded-2xl p-4 text-xs text-ink-3 space-y-2 font-semibold shadow-inner">
              <div className="text-ink-2 font-bold uppercase tracking-widest mb-2 opacity-80">💡 {t('security_tips')}:</div>
              <div>• Gunakan password minimal 8 karakter + angka + simbol</div>
              <div>• Aktifkan <span className="text-accent-2 font-bold">2FA & Login</span> untuk perlindungan ekstra</div>
            </div>
          </div>
        </div>

        {/* ── Kartu App ── */}
        <div className="bg-bg-3 border border-border rounded-2xl overflow-hidden shadow-lg">
          <div className="flex items-center gap-3 px-5 py-4 border-b-2 border-border">
            <LayoutDashboard size={18} className="text-success"/>
            <span className="text-base font-bold text-ink uppercase tracking-tight">
              {isAdmin ? t('app_logo_name') : t('app_info')}
            </span>
          </div>
          <div className="p-6">
            {isAdmin ? (
              <div className="space-y-4">
                <TextInp
                  label="Nama Aplikasi"
                  value={appName}
                  onChange={setAppName}
                  placeholder="AI ORCHESTRATOR"
                  maxLength={24}
                />
                <p className="text-[11px] text-ink-3 -mt-3 font-semibold uppercase tracking-tight opacity-60">Tampil di sidebar & header. Maks 24 karakter.</p>

                <div>
                  <Label>Logo Aplikasi</Label>
                  <LogoUploader current={logoSrc} onFileSelected={f => setLogoFile(f)}/>
                </div>

                {savedOk && (
                  <div className="flex items-center gap-3 p-4 bg-success/10 border border-success/30 rounded-2xl text-sm text-success font-bold uppercase tracking-tight shadow-inner">
                    <CheckCircle2 size={16}/>
                    Tersimpan! Tekan <kbd className="mx-1 bg-bg-2 border border-border px-2 py-1 rounded-lg text-[10px] text-ink font-mono font-bold shadow-sm">F5</kbd> untuk refresh sidebar.
                  </div>
                )}

                <button onClick={handleSaveApp} disabled={savingA || (appName.trim() === origName && !logoFile)}
                  className="w-full flex items-center justify-center gap-3 py-3.5 bg-success hover:bg-success/80 disabled:opacity-40 text-white text-sm font-bold uppercase tracking-widest rounded-xl transition-all shadow-md active:scale-95">
                  {savingA ? <RefreshCw size={16} className="animate-spin"/> : <Save size={16}/>}
                  {savingA ? 'Menyimpan...' : 'Simpan Logo & Nama'}
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center gap-4 p-4 bg-bg-4 border border-border rounded-2xl shadow-inner">
                  <div className="w-14 h-14 rounded-xl border border-border bg-bg-5 flex items-center justify-center overflow-hidden flex-shrink-0 shadow-sm">
                    {logoSrc ? <img src={logoSrc} className="w-full h-full object-contain" alt="logo"/> : <span className="text-3xl">🧠</span>}
                  </div>
                  <div>
                    <div className="font-bold text-lg text-ink uppercase tracking-tight">{appName || 'AI ORCHESTRATOR'}</div>
                    <div className="text-xs text-ink-3 font-bold uppercase tracking-widest opacity-60">AI Orchestrator Platform</div>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-4 bg-bg-4 border border-border rounded-2xl text-xs text-ink-3 font-semibold leading-relaxed shadow-sm">
                  <Info size={16} className="text-accent-2 flex-shrink-0 mt-0.5"/>
                  <span className="opacity-80">Logo dan nama aplikasi adalah identitas sistem yang hanya dapat diubah oleh Administrator melalui pengaturan ini.</span>
                </div>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  )
}
