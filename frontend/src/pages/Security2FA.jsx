import { useState, useEffect, useRef } from 'react'
import { api } from '../hooks/useApi'
import { copyToClipboard } from "../utils/clipboard"
import { useAuthStore } from '../store'
import toast from 'react-hot-toast'
import {
  Shield, Mail, MessageSquare, Key, RefreshCw, CheckCircle2,
  XCircle, Eye, EyeOff, ChevronDown, ChevronUp, AlertTriangle,
  Smartphone, Settings, Wifi, Copy, Check, Info,
} from 'lucide-react'
import clsx from 'clsx'

// ── Primitives ────────────────────────────────────────────────
function Label({ children }) {
  return <label className="block text-[10px] text-ink-3 mb-1.5 uppercase tracking-wider font-medium">{children}</label>
}
function Inp({ value, onChange, placeholder, disabled, mono, type = 'text', maxLength }) {
  return (
    <input type={type} value={value} onChange={e => onChange(e.target.value)}
      placeholder={placeholder} disabled={disabled} maxLength={maxLength}
      autoComplete="new-password"
      className={clsx('w-full bg-bg-2 border border-border-2 rounded-lg px-3 py-2 text-xs text-ink placeholder-ink-3 outline-none focus:border-accent disabled:opacity-50 transition-colors',
        mono && 'font-mono tracking-widest text-center text-sm')}/>
  )
}
function PassInp({ value, onChange, placeholder }) {
  const [show, setShow] = useState(false)
  return (
    <div className="relative">
      <input type={show ? 'text' : 'password'} value={value} onChange={e => onChange(e.target.value)}
        placeholder={placeholder} autoComplete="new-password"
        className="w-full bg-bg-2 border border-border-2 rounded-lg px-3 py-2 pr-9 text-xs text-ink placeholder-ink-3 outline-none focus:border-accent font-mono"/>
      <button type="button" onClick={() => setShow(!show)} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-ink-3 hover:text-ink">
        {show ? <EyeOff size={13}/> : <Eye size={13}/>}
      </button>
    </div>
  )
}
function Btn({ label, onClick, loading, variant = 'primary', icon: Icon, disabled, full }) {
  return (
    <button onClick={onClick} disabled={loading || disabled}
      className={clsx('flex items-center justify-center gap-1.5 px-3 py-2 text-xs rounded-xl font-medium transition-all disabled:opacity-50',
        full && 'w-full',
        variant === 'primary' && 'bg-accent hover:bg-accent/80 text-white',
        variant === 'success' && 'bg-success/10 hover:bg-success/20 border border-success/30 text-success',
        variant === 'warn'    && 'bg-warn/10 hover:bg-warn/20 border border-warn/30 text-warn',
        variant === 'danger'  && 'bg-danger/10 hover:bg-danger/20 border border-danger/30 text-danger',
        variant === 'default' && 'bg-bg-4 hover:bg-bg-5 border border-border text-ink-2 hover:text-ink',
      )}>
      {loading ? <RefreshCw size={12} className="animate-spin"/> : Icon && <Icon size={12}/>}
      {label}
    </button>
  )
}
function StatusBadge({ ok, labelOk = 'Aktif', labelNo = 'Belum Disetup' }) {
  return ok
    ? <span className="flex items-center gap-1 text-[10px] bg-success/10 text-success border border-success/20 px-2 py-0.5 rounded-full font-medium"><CheckCircle2 size={9}/>{labelOk}</span>
    : <span className="flex items-center gap-1 text-[10px] bg-bg-4 text-ink-3 border border-border px-2 py-0.5 rounded-full"><XCircle size={9}/>{labelNo}</span>
}
function OtpInput({ value, onChange, length = 6 }) {
  const refs = useRef([])

  // Buat array 6 slot - selalu length 6, isi dengan digit atau ''
  const slots = Array.from({ length }, (_, i) => value[i] || '')

  const handleChange = (i, raw) => {
    // Ambil hanya angka terakhir yang diketik
    const digit = raw.replace(/[^0-9]/g, '').slice(-1)
    const newSlots = [...slots]
    newSlots[i] = digit
    onChange(newSlots.join(''))
    // Auto-advance ke kotak berikutnya
    if (digit && i < length - 1) {
      setTimeout(() => refs.current[i + 1]?.focus(), 0)
    }
  }

  const handleKeyDown = (i, e) => {
    if (e.key === 'Backspace') {
      if (slots[i]) {
        // Hapus digit saat ini
        const newSlots = [...slots]
        newSlots[i] = ''
        onChange(newSlots.join(''))
      } else if (i > 0) {
        // Kotak kosong - mundur ke sebelumnya
        refs.current[i - 1]?.focus()
        const newSlots = [...slots]
        newSlots[i - 1] = ''
        onChange(newSlots.join(''))
      }
      e.preventDefault()
    } else if (e.key === 'ArrowLeft' && i > 0) {
      refs.current[i - 1]?.focus()
    } else if (e.key === 'ArrowRight' && i < length - 1) {
      refs.current[i + 1]?.focus()
    }
  }

  const handlePaste = (e) => {
    e.preventDefault()
    const pasted = e.clipboardData.getData('text').replace(/[^0-9]/g, '').slice(0, length)
    if (pasted) {
      onChange(pasted.padEnd(length, '').slice(0, length))
      const focusIdx = Math.min(pasted.length, length - 1)
      setTimeout(() => refs.current[focusIdx]?.focus(), 0)
    }
  }

  return (
    <div className="flex gap-2 justify-center my-3">
      {slots.map((digit, i) => (
        <input
          key={i}
          ref={el => refs.current[i] = el}
          type="text"
          inputMode="numeric"
          maxLength={1}
          value={digit}
          onChange={e => handleChange(i, e.target.value)}
          onKeyDown={e => handleKeyDown(i, e)}
          onFocus={e => e.target.select()}
          onPaste={handlePaste}
          className={clsx(
            "w-11 h-14 text-center text-2xl font-bold font-mono rounded-xl outline-none transition-all border-2",
            digit
              ? "bg-accent/10 border-accent text-accent-2"
              : "bg-bg-2 border-border-2 text-ink focus:border-accent focus:bg-bg-3"
          )}
        />
      ))}
    </div>
  )
}
function CopyBtn({ text }) {
  const [ok, setOk] = useState(false)
  return (
    <button onClick={() => { copyToClipboard(text); setOk(true); setTimeout(() => setOk(false), 2000) }}
      className="p-1.5 text-ink-3 hover:text-ink">
      {ok ? <Check size={12} className="text-success"/> : <Copy size={12}/>}
    </button>
  )
}
function Section({ title, icon: Icon, color = 'text-accent-2', badge, defaultOpen = false, children }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="bg-bg-3 border border-border rounded-xl overflow-hidden">
      <button onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2.5 px-4 py-3.5 hover:bg-bg-4/50 transition-colors">
        <Icon size={15} className={color}/>
        <span className="text-sm font-semibold text-ink flex-1 text-left">{title}</span>
        {badge}
        {open ? <ChevronUp size={13} className="text-ink-3"/> : <ChevronDown size={13} className="text-ink-3"/>}
      </button>
      {open && <div className="px-4 pb-5 pt-1 border-t border-border">{children}</div>}
    </div>
  )
}

// ══════════════════════════════════════════════════════════════
// 1. EMAIL RESET
// ══════════════════════════════════════════════════════════════
function EmailResetSection({ isAdmin }) {
  const [smtp,     setSmtp]    = useState(null)
  const [testing,  setTesting] = useState(false)
  const [saving,   setSaving]  = useState(false)

  // SMTP form
  const [host, setHost]   = useState('')
  const [port, setPort]   = useState('587')
  const [user, setUser]   = useState('')
  const [pass, setPass]   = useState('')
  const [from_, setFrom]  = useState('')
  const [appUrl, setAppUrl] = useState('')
  const [tls, setTls]     = useState(true)

  useEffect(() => {
    api.smtpStatus().then(s => {
      setSmtp(s)
      if (s.host)    setHost(s.host)
      if (s.port)    setPort(String(s.port))
      if (s.user)    setUser(s.user)
      if (s.app_url) setAppUrl(s.app_url)
      setTls(s.tls !== false)
    }).catch(() => {})
  }, [])

  const saveSmtp = async () => {
    setSaving(true)
    try {
      const fields = {}
      if (host)   fields.SMTP_HOST = host
      if (port)   fields.SMTP_PORT = port
      if (user)   fields.SMTP_USER = user
      if (pass)   fields.SMTP_PASS = pass
      if (from_)  fields.SMTP_FROM = from_
      if (appUrl) fields.APP_URL   = appUrl
      fields.SMTP_TLS = tls ? 'true' : 'false'
      await api.post('/settings/app', fields)
      toast.success('Konfigurasi SMTP disimpan!')
      const s = await api.smtpStatus(); setSmtp(s)
    } catch(e) { toast.error(e.message) }
    finally { setSaving(false) }
  }

  const testSmtp = async () => {
    setTesting(true)
    try {
      const r = await api.testSmtp()
      r.ok ? toast.success(r.message) : toast.error(r.message)
    } catch(e) { toast.error(e.message) }
    finally { setTesting(false) }
  }

  return (
    <div className="mt-3 space-y-4">
      <div className="flex items-center gap-3">
        <StatusBadge ok={smtp?.configured} labelOk="SMTP Terkonfigurasi"/>
        {smtp?.configured && <span className="text-[10px] text-ink-3 font-mono">{smtp.host}:{smtp.port}</span>}
      </div>

      <div className="bg-bg-4 border border-border rounded-xl p-3 text-[10px] text-ink-3 space-y-1.5">
        <div className="text-ink-2 font-semibold mb-1">ℹ️ Cara kerja reset via email:</div>
        <div>1. User klik "Lupa Password?" di halaman login → masukkan email</div>
        <div>2. AI ORCHESTRATOR kirim link reset ke email terdaftar</div>
        <div>3. User klik link → set password baru (link berlaku 15 menit)</div>
        <div className="text-warn pt-1">⚠ Butuh konfigurasi SMTP di bawah. Cocok untuk Gmail, Outlook, Mailtrap.</div>
      </div>

      {isAdmin && (
        <div className="space-y-3">
          <div className="text-xs font-semibold text-ink border-b border-border pb-2">⚙️ Konfigurasi SMTP</div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <Label>SMTP Host</Label>
              <Inp value={host} onChange={setHost} placeholder="smtp.gmail.com"/>
            </div>
            <div>
              <Label>Port</Label>
              <Inp value={port} onChange={setPort} placeholder="587"/>
            </div>
            <div>
              <Label>Username / Email Pengirim</Label>
              <Inp value={user} onChange={setUser} placeholder="namaanda@gmail.com" mono/>
            </div>
            <div>
              <Label>Password / App Password</Label>
              <PassInp value={pass} onChange={setPass} placeholder="App password Gmail..."/>
            </div>
            <div>
              <Label>From Address (opsional)</Label>
              <Inp value={from_} onChange={setFrom} placeholder="AI ORCHESTRATOR <no-reply@domain.com>" mono/>
            </div>
            <div>
              <Label>App URL (untuk link reset)</Label>
              <Inp value={appUrl} onChange={setAppUrl} placeholder="https://ai-orchestrator.domain.com" mono/>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <div onClick={() => setTls(!tls)}
                className={clsx('w-8 h-4 rounded-full relative transition-colors', tls ? 'bg-accent' : 'bg-bg-5 border border-border')}>
                <div className={clsx('absolute top-0.5 w-3 h-3 rounded-full bg-white shadow transition-transform', tls ? 'translate-x-4' : 'translate-x-0.5')}/>
              </div>
              <span className="text-xs text-ink-2">STARTTLS (port 587) — matikan untuk SSL port 465</span>
            </label>
          </div>

          <div className="flex flex-wrap gap-2">
            <Btn label="Simpan SMTP" onClick={saveSmtp} loading={saving} icon={Settings} variant="primary"/>
            <Btn label="Test Koneksi" onClick={testSmtp} loading={testing} icon={Wifi} variant="success"/>
          </div>

          {/* Panduan Gmail */}
          <details className="group">
            <summary className="text-[10px] text-accent-2 cursor-pointer hover:underline">📧 Panduan setup Gmail →</summary>
            <div className="mt-2 bg-bg-4 rounded-xl p-3 text-[10px] text-ink-3 space-y-1.5">
              <div className="font-semibold text-ink-2 mb-1">Gmail App Password (bukan password biasa):</div>
              <div>1. Buka <span className="text-accent-2">myaccount.google.com</span> → Security</div>
              <div>2. Aktifkan "2-Step Verification" terlebih dahulu</div>
              <div>3. Cari "App passwords" → pilih "Mail" → Generate</div>
              <div>4. Copy 16 karakter yang muncul → paste ke kolom Password di atas</div>
              <div className="pt-1 font-mono text-accent-2">Host: smtp.gmail.com | Port: 587 | TLS: ON</div>
            </div>
          </details>
        </div>
      )}
    </div>
  )
}

// ══════════════════════════════════════════════════════════════
// 2. TELEGRAM OTP
// ══════════════════════════════════════════════════════════════
function TelegramOtpSection({ totpStatus, onRefresh }) {
  const { user } = useAuthStore()
  const [step,    setStep]    = useState(1)  // 1=info, 2=input_id, 3=verify
  const [chatId,  setChatId]  = useState('')
  const [otp,     setOtp]     = useState('')
  const [loading, setLoading] = useState(false)
  const [done,    setDone]    = useState(totpStatus?.telegram_otp_ready || false)

  const handleSetup = async () => {
    if (!chatId.trim()) { toast.error('Masukkan Telegram Chat ID'); return }
    setLoading(true)
    try {
      await api.setupTelegramOtp(chatId.trim())
      toast.success('Chat ID tersimpan! Cek Telegram untuk kode verifikasi.')
      setStep(3)
    } catch(e) { toast.error(e.message) }
    finally { setLoading(false) }
  }

  const handleVerify = async () => {
    if (otp.length !== 6) { toast.error('Masukkan 6 digit kode OTP'); return }
    setLoading(true)
    try {
      await api.verifyTelegramSetup(otp)
      toast.success('OTP Telegram aktif! Anda bisa login via Telegram OTP.')
      setDone(true); onRefresh()
    } catch(e) { toast.error(e.message); setOtp('') }
    finally { setLoading(false) }
  }

  if (done) return (
    <div className="mt-3 space-y-3">
      <div className="flex items-center gap-2 p-3 bg-success/8 border border-success/25 rounded-xl">
        <CheckCircle2 size={14} className="text-success"/>
        <div>
          <div className="text-xs font-semibold text-success">Telegram OTP Aktif</div>
          <div className="text-[10px] text-ink-3">Saat login, kode OTP akan dikirim ke Telegram Anda</div>
        </div>
      </div>
      <Btn label="Reset Setup Telegram OTP" onClick={() => { setDone(false); setStep(1); setChatId(''); setOtp('') }} variant="danger" icon={XCircle}/>
    </div>
  )

  return (
    <div className="mt-3 space-y-4">
      <div className="bg-bg-4 border border-border rounded-xl p-3 text-[10px] text-ink-3 space-y-1.5">
        <div className="text-ink-2 font-semibold mb-1">ℹ️ Cara kerja Telegram OTP:</div>
        <div>1. Setelah password benar saat login, AI ORCHESTRATOR kirim kode 6 digit ke Telegram</div>
        <div>2. Masukkan kode tersebut untuk melanjutkan login</div>
        <div>3. Kode berlaku 5 menit dan hanya sekali pakai</div>
        <div className="text-accent-2 pt-1">✓ Tidak perlu aplikasi tambahan — cukup Telegram!</div>
      </div>

      {/* Step indicator */}
      <div className="flex items-center gap-2">
        {[1,2,3].map(s => (
          <div key={s} className="flex items-center gap-2">
            <div className={clsx('w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold transition-all',
              step >= s ? 'bg-accent text-white' : 'bg-bg-4 text-ink-3 border border-border')}>
              {step > s ? '✓' : s}
            </div>
            {s < 3 && <div className={clsx('flex-1 h-px w-8', step > s ? 'bg-accent' : 'bg-border')}/>}
          </div>
        ))}
        <div className="text-[10px] text-ink-3 ml-2">
          {step === 1 && 'Mulai Setup'}
          {step === 2 && 'Masukkan Chat ID'}
          {step === 3 && 'Verifikasi Kode'}
        </div>
      </div>

      {step === 1 && (
        <div className="space-y-3">
          <div className="bg-sky-400/8 border border-sky-400/20 rounded-xl p-3 space-y-2">
            <div className="text-xs font-semibold text-sky-400 flex items-center gap-1.5">
              <MessageSquare size={12}/>Langkah 1: Dapatkan Chat ID Telegram
            </div>
            <div className="text-[10px] text-ink-3 space-y-1">
              <div>1. Buka Telegram → cari <span className="font-mono text-accent-2">@userinfobot</span></div>
              <div>2. Kirim pesan apa saja → bot akan balas dengan ID Anda</div>
              <div>3. Atau: buka bot AI ORCHESTRATOR Anda → kirim <span className="font-mono text-accent-2">/start</span> → catat angka ID yang muncul</div>
            </div>
          </div>
          <Btn label="Lanjut →" onClick={() => setStep(2)} variant="primary" icon={MessageSquare}/>
        </div>
      )}

      {step === 2 && (
        <div className="space-y-3">
          <div>
            <Label>Telegram Chat ID (angka)</Label>
            <Inp value={chatId} onChange={setChatId} placeholder="123456789" mono/>
            <p className="text-[10px] text-ink-3 mt-1">Dapatkan dari @userinfobot — berupa angka panjang</p>
          </div>
          <div className="flex gap-2">
            <Btn label="← Kembali" onClick={() => setStep(1)} variant="default"/>
            <Btn label="Kirim Kode Test →" onClick={handleSetup} loading={loading} variant="primary" icon={MessageSquare}
              disabled={!chatId.trim()}/>
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="space-y-3">
          <div className="text-[10px] text-ink-3 bg-bg-4 border border-border rounded-xl p-3">
            Kode OTP telah dikirim ke Telegram Anda. Masukkan kode 6 digit di bawah.
          </div>
          <div>
            <Label>Kode OTP dari Telegram</Label>
            <OtpInput value={otp} onChange={setOtp} onEnter={handleVerify}/>
          </div>
          <div className="flex gap-2">
            <Btn label="← Kirim Ulang" onClick={handleSetup} loading={loading} variant="default"/>
            <Btn label="Verifikasi & Aktifkan" onClick={handleVerify} loading={loading} variant="success"
              icon={CheckCircle2} disabled={otp.length !== 6}/>
          </div>
        </div>
      )}
    </div>
  )
}

// ══════════════════════════════════════════════════════════════
// 3. TOTP 2FA (Google Authenticator)
// ══════════════════════════════════════════════════════════════
function TotpSection({ status, onRefresh }) {
  const { user } = useAuthStore()
  const [step,     setStep]    = useState(1)  // 1=info, 2=scan, 3=verify
  const [secret,   setSecret]  = useState('')
  const [qrUri,    setQrUri]   = useState('')
  const [code,     setCode]    = useState('')
  const [loading,  setLoading] = useState(false)
  // Disable form
  const [disPass,  setDisPass]  = useState('')
  const [disCode,  setDisCode]  = useState('')
  const [disLoad,  setDisLoad]  = useState(false)

  const startSetup = async () => {
    setLoading(true)
    try {
      const r = await api.totpSetupStart()
      setSecret(r.secret)
      setQrUri(r.qr_uri)
      setStep(2)
    } catch(e) { toast.error(e.message) }
    finally { setLoading(false) }
  }

  const verifySetup = async () => {
    if (code.length !== 6) { toast.error('Masukkan 6 digit kode'); return }
    setLoading(true)
    try {
      await api.totpSetupVerify(code)
      toast.success('🎉 2FA berhasil diaktifkan!')
      setStep(1); setCode(''); onRefresh()
    } catch(e) { toast.error(e.message); setCode('') }
    finally { setLoading(false) }
  }

  const disable2fa = async () => {
    if (!disPass || !disCode) { toast.error('Isi password dan kode 2FA'); return }
    setDisLoad(true)
    try {
      await api.totpDisable(disPass, disCode)
      toast.success('2FA dinonaktifkan')
      setDisPass(''); setDisCode(''); onRefresh()
    } catch(e) { toast.error(e.message) }
    finally { setDisLoad(false) }
  }

  const enabled = status?.totp_enabled

  // QR Code rendered via canvas (pure JS, no library needed)
  const canvasRef = useRef()
  useEffect(() => {
    if (!qrUri || !canvasRef.current) return
    // Gunakan API QR dari goqr.me sebagai fallback (server-side render)
    const canvas = canvasRef.current
    const ctx    = canvas.getContext('2d')
    const img    = new window.Image()
    img.crossOrigin = 'anonymous'
    img.onload  = () => ctx.drawImage(img, 0, 0, 200, 200)
    img.onerror = () => {}
    img.src = 'https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=' + encodeURIComponent(qrUri)
  }, [qrUri])

  return (
    <div className="mt-3 space-y-4">
      <div className="bg-bg-4 border border-border rounded-xl p-3 text-[10px] text-ink-3 space-y-1.5">
        <div className="text-ink-2 font-semibold mb-1">ℹ️ Cara kerja TOTP 2FA:</div>
        <div>1. Scan QR code dengan Google Authenticator / Authy / FreeOTP</div>
        <div>2. Setiap login, masukkan kode 6 digit dari aplikasi (berganti tiap 30 detik)</div>
        <div>3. Tanpa akses ke aplikasi authenticator, tidak bisa login</div>
        <div className="text-success pt-1">✓ Perlindungan terkuat — tidak bisa diakses tanpa HP Anda</div>
      </div>

      {enabled ? (
        <div className="space-y-3">
          <div className="flex items-center gap-2 p-3 bg-success/8 border border-success/25 rounded-xl">
            <CheckCircle2 size={14} className="text-success"/>
            <div>
              <div className="text-xs font-semibold text-success">2FA TOTP Aktif</div>
              <div className="text-[10px] text-ink-3">Login memerlukan kode 6 digit dari aplikasi authenticator</div>
            </div>
          </div>

          <div className="border border-danger/30 rounded-xl overflow-hidden">
            <div className="flex items-center gap-2 px-3 py-2.5 bg-danger/5 border-b border-danger/20">
              <AlertTriangle size={12} className="text-danger"/>
              <span className="text-xs font-semibold text-danger">Nonaktifkan 2FA</span>
            </div>
            <div className="p-3 space-y-2.5">
              <div>
                <Label>Password Akun</Label>
                <PassInp value={disPass} onChange={setDisPass} placeholder="password saat ini..."/>
              </div>
              <div>
                <Label>Kode 2FA dari Authenticator</Label>
                <OtpInput value={disCode} onChange={setDisCode} onEnter={disable2fa}/>
              </div>
              <Btn label="Nonaktifkan 2FA" onClick={disable2fa} loading={disLoad}
                variant="danger" icon={XCircle} full
                disabled={!disPass || disCode.length !== 6}/>
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Step indicator */}
          <div className="flex items-center gap-2">
            {['Info', 'Scan QR', 'Verifikasi'].map((label, i) => (
              <div key={label} className="flex items-center gap-2">
                <div className={clsx('flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-medium transition-all',
                  step > i+1 ? 'bg-success/15 text-success' :
                  step === i+1 ? 'bg-accent/15 text-accent-2' : 'bg-bg-4 text-ink-3')}>
                  {step > i+1 ? '✓' : i+1}. {label}
                </div>
                {i < 2 && <div className={clsx('w-4 h-px', step > i+1 ? 'bg-success' : 'bg-border')}/>}
              </div>
            ))}
          </div>

          {step === 1 && (
            <div className="space-y-3">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                {[
                  { icon: '📱', name: 'Google Authenticator', dl: 'Play Store / App Store', recommended: true },
                  { icon: '🔐', name: 'Authy', dl: 'authy.com', recommended: false },
                  { icon: '🔓', name: 'FreeOTP', dl: 'Open source', recommended: false },
                ].map(app => (
                  <div key={app.name} className={clsx('rounded-xl border p-3 text-center',
                    app.recommended ? 'border-accent/40 bg-accent/5' : 'border-border bg-bg-4')}>
                    <div className="text-2xl mb-1">{app.icon}</div>
                    <div className="text-[11px] font-semibold text-ink">{app.name}</div>
                    <div className="text-[9px] text-ink-3">{app.dl}</div>
                    {app.recommended && <div className="text-[9px] text-accent-2 mt-1 font-medium">⭐ Direkomendasikan</div>}
                  </div>
                ))}
              </div>
              <Btn label="Mulai Setup 2FA →" onClick={startSetup} loading={loading} variant="primary" icon={Smartphone} full/>
            </div>
          )}

          {step === 2 && qrUri && (
            <div className="space-y-4">
              <div className="text-xs text-ink-2">Scan QR code ini dengan aplikasi authenticator:</div>

              <div className="flex flex-col md:flex-row items-start gap-5">
                {/* QR Code */}
                <div className="flex-shrink-0 flex flex-col items-center gap-2">
                  <div className="bg-white p-3 rounded-2xl shadow-lg">
                    <canvas ref={canvasRef} width={200} height={200}
                      className="block"/>
                  </div>
                  <div className="text-[10px] text-ink-3">Scan dengan aplikasi authenticator</div>
                </div>

                {/* Manual entry */}
                <div className="flex-1 space-y-3">
                  <div className="text-[10px] text-ink-3">Atau masukkan kode ini secara manual:</div>
                  <div className="flex items-center gap-2 bg-bg-2 border border-border rounded-xl px-3 py-2">
                    <code className="flex-1 font-mono text-xs text-accent-2 tracking-widest break-all">{secret}</code>
                    <CopyBtn text={secret}/>
                  </div>
                  <div className="bg-bg-4 rounded-xl p-3 text-[10px] text-ink-3 space-y-1">
                    <div className="font-semibold text-ink-2 mb-1">Manual entry di Google Authenticator:</div>
                    <div>1. Ketuk "+" → "Enter a setup key"</div>
                    <div>2. Account: <span className="font-mono text-accent-2">AI ORCHESTRATOR</span></div>
                    <div>3. Key: copy dari kotak di atas</div>
                    <div>4. Type: Time-based</div>
                  </div>
                </div>
              </div>

              <Btn label="Lanjut ke Verifikasi →" onClick={() => setStep(3)} variant="primary" full/>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-3">
              <div className="text-[10px] text-ink-3 bg-bg-4 rounded-xl p-3">
                Buka Google Authenticator → cari AI ORCHESTRATOR → masukkan kode 6 digit yang muncul
              </div>
              <div>
                <Label>Kode 6 Digit dari Authenticator</Label>
                <OtpInput value={code} onChange={setCode} onEnter={verifySetup}/>
              </div>
              <div className="flex gap-2">
                <Btn label="← Kembali" onClick={() => setStep(2)} variant="default"/>
                <Btn label="Aktifkan 2FA" onClick={verifySetup} loading={loading}
                  variant="success" icon={Shield} disabled={code.length !== 6}/>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ══════════════════════════════════════════════════════════════
// MAIN PAGE
// ══════════════════════════════════════════════════════════════
export default function Security2FA() {
  const { user } = useAuthStore()
  const [status, setStatus] = useState(null)

  const loadStatus = async () => {
    try { setStatus(await api.totpStatus()) } catch {}
  }

  useEffect(() => { loadStatus() }, [])

  const methods = [
    { key: 'email',    active: true,                         label: 'Email Reset', color: 'text-success' },
    { key: 'telegram', active: status?.telegram_otp_ready,  label: 'Telegram OTP', color: 'text-sky-400' },
    { key: 'totp',     active: status?.totp_enabled,        label: '2FA TOTP', color: 'text-accent-2' },
  ]

  return (
    <div className="p-4 md:p-6 w-full space-y-4">
      <div>
        <h1 className="text-lg font-bold text-ink flex items-center gap-2">
          <Shield size={18} className="text-accent-2"/>Autentikasi & Keamanan
        </h1>
        <p className="text-xs text-ink-3 mt-0.5">Reset password, OTP Telegram, dan Two-Factor Authentication</p>
      </div>

      {/* Status overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {[
          { icon: Mail, label: '📧 Email Reset', sub: 'Link reset via email', active: true, color: 'text-success', bg: 'bg-success/10' },
          { icon: MessageSquare, label: '📱 Telegram OTP', sub: 'Kode OTP saat login', active: status?.telegram_otp_ready, color: 'text-sky-400', bg: 'bg-sky-400/10' },
          { icon: Smartphone, label: '🔐 2FA TOTP', sub: 'Google Authenticator', active: status?.totp_enabled, color: 'text-accent-2', bg: 'bg-accent/10' },
        ].map(m => (
          <div key={m.label} className={clsx('rounded-xl border p-4 transition-all',
            m.active ? 'border-success/30 bg-success/3' : 'border-border bg-bg-3')}>
            <div className={clsx('w-8 h-8 rounded-xl flex items-center justify-center mb-2.5', m.active ? 'bg-success/15' : m.bg)}>
              <m.icon size={15} className={m.active ? 'text-success' : m.color}/>
            </div>
            <div className="text-xs font-semibold text-ink">{m.label}</div>
            <div className="text-[10px] text-ink-3 mt-0.5">{m.sub}</div>
            <div className="mt-2">
              <StatusBadge ok={m.active} labelOk="Aktif" labelNo="Belum disetup"/>
            </div>
          </div>
        ))}
      </div>

      {/* Rekomendasi */}
      <div className="flex items-start gap-2.5 p-3 bg-accent/8 border border-accent/20 rounded-xl text-[10px] text-ink-2">
        <Info size={12} className="text-accent-2 flex-shrink-0 mt-0.5"/>
        <div>
          <strong className="text-ink block mb-0.5">Rekomendasi Keamanan:</strong>
          Setup minimal 1 metode 2FA. <strong>TOTP</strong> paling aman (tanpa internet untuk generate kode).
          <strong>Telegram OTP</strong> paling mudah. <strong>Email Reset</strong> sebagai fallback jika lupa password.
        </div>
      </div>

      {/* ── Section 1: Email Reset ── */}
      <Section title="📧 Reset Password via Email" icon={Mail} color="text-success"
        badge={<StatusBadge ok={true} labelOk="Tersedia" labelNo="Perlu Setup"/>}
        defaultOpen={false}>
        <EmailResetSection isAdmin={user?.is_admin}/>
      </Section>

      {/* ── Section 2: Telegram OTP ── */}
      <Section title="📱 OTP via Bot Telegram" icon={MessageSquare} color="text-sky-400"
        badge={<StatusBadge ok={status?.telegram_otp_ready}/>}>
        <TelegramOtpSection totpStatus={status} onRefresh={loadStatus}/>
      </Section>

      {/* ── Section 3: TOTP 2FA ── */}
      <Section title="🔐 Two-Factor Auth (TOTP)" icon={Smartphone} color="text-accent-2"
        badge={<StatusBadge ok={status?.totp_enabled} labelOk="2FA Aktif"/>}>
        <TotpSection status={status} onRefresh={loadStatus}/>
      </Section>

    </div>
  )
}
