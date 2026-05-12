import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store'
import { api } from '../hooks/useApi'
import toast from 'react-hot-toast'
import {
  Eye, EyeOff, LogIn, Unlock, RefreshCw,
  Mail, MessageSquare, Smartphone, Key, ChevronRight,
  CheckCircle2, ArrowLeft, Send, AlertTriangle,
} from 'lucide-react'
import clsx from 'clsx'

const cleanUsername = (s) => (s || '').trim().replace(/^@+/, '')

// ── OTP Input 6 kotak ─────────────────────────────────────────
function OtpBoxes({ value, onChange, onEnter }) {
  const refs = useRef([])
  const LENGTH = 6
  const slots = Array.from({ length: LENGTH }, (_, i) => value[i] || '')

  const handleChange = (i, raw) => {
    const digit = raw.replace(/[^0-9]/g, '').slice(-1)
    const ns = [...slots]; ns[i] = digit
    const newVal = ns.join('')
    onChange(newVal)
    if (digit && i < LENGTH - 1) setTimeout(() => refs.current[i+1]?.focus(), 0)
    // Auto-submit jika sudah 6 digit
    if (digit && i === LENGTH - 1 && onEnter) {
      const complete = ns.every(s => s !== '')
      if (complete) setTimeout(() => onEnter(), 100)
    }
  }
  const handleKeyDown = (i, e) => {
    if (e.key === 'Enter' && onEnter) {
      const complete = slots.every(s => s !== '')
      if (complete) onEnter()
      return
    }
    if (e.key === 'Backspace') {
      const ns = [...slots]
      if (ns[i]) { ns[i] = ''; onChange(ns.join('')) }
      else if (i > 0) { refs.current[i-1]?.focus(); ns[i-1] = ''; onChange(ns.join('')) }
      e.preventDefault()
    } else if (e.key === 'ArrowLeft' && i > 0) refs.current[i-1]?.focus()
    else if (e.key === 'ArrowRight' && i < LENGTH-1) refs.current[i+1]?.focus()
  }
  const handlePaste = (e) => {
    e.preventDefault()
    const p = e.clipboardData.getData('text').replace(/[^0-9]/g, '').slice(0, LENGTH)
    if (p) {
      const newVal = p.padEnd(LENGTH, '').slice(0, LENGTH)
      onChange(newVal)
      const focusIdx = Math.min(p.length, LENGTH - 1)
      setTimeout(() => {
        refs.current[focusIdx]?.focus()
        // Auto-submit jika paste 6 digit langsung
        if (p.length === LENGTH && onEnter) onEnter()
      }, 100)
    }
  }

  return (
    <div className="flex gap-2 justify-center my-2">
      {slots.map((d, i) => (
        <input key={i} ref={el => refs.current[i] = el}
          type="text" inputMode="numeric" maxLength={1} value={d}
          onChange={e => handleChange(i, e.target.value)}
          onKeyDown={e => handleKeyDown(i, e)}
          onFocus={e => e.target.select()}
          onPaste={handlePaste}
          className={clsx(
            "w-11 text-center text-xl font-semibold font-mono rounded-xl outline-none transition-all border-2",
            d ? "bg-accent/10 border-accent text-accent-2" : "bg-bg-3 border-transparent text-ink focus:border-accent"
          )}
          style={{ height: "3rem" }}
        />
      ))}
    </div>
  )
}

// ── Komponen password input ───────────────────────────────────
function PassInput({ value, onChange, placeholder, label, onKeyDown }) {
  const [show, setShow] = useState(false)
  return (
    <div>
      {label && <label className="block text-xs text-ink-2 mb-1.5">{label}</label>}
      <div className="relative">
        <input
          type={show ? 'text' : 'password'} value={value}
          onChange={e => onChange(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={placeholder} autoComplete="new-password"
          className="w-full bg-bg-3 border border-transparent rounded-xl px-3 py-2.5 pr-10 text-sm text-ink font-mono placeholder-ink-3 outline-none focus:border-accent transition-colors"
        />
        <button type="button" onClick={() => setShow(!show)}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-3 hover:text-ink">
          {show ? <EyeOff size={15}/> : <Eye size={15}/>}
        </button>
      </div>
    </div>
  )
}

// ── Tombol metode recovery ────────────────────────────────────
function MethodBtn({ icon, title, desc, color, bg, onClick, badge }) {
  return (
    <button onClick={onClick}
      className="w-full flex items-center gap-3 p-3.5 bg-bg-3 hover:bg-bg-4 border border-transparent hover:border-transparent rounded-xl transition-all text-left group">
      <div className={clsx('w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 text-lg', bg)}>
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-ink">{title}</span>
          {badge && <span className={clsx('text-[9px] px-1.5 py-0.5 rounded-full font-medium', badge.cls)}>{badge.text}</span>}
        </div>
        <div className="text-[11px] text-ink-3 mt-0.5">{desc}</div>
      </div>
      <ChevronRight size={14} className="text-ink-3 group-hover:text-ink flex-shrink-0"/>
    </button>
  )
}

// ── NewPassForm — komponen terpisah agar tidak re-mount setiap render ──
function NewPassForm({ newPass, setNewPass, confPass, setConfPass, loading, onSubmit, submitLabel }) {
  submitLabel = submitLabel || 'Reset Password'
  const canSubmit = !loading && newPass.length >= 6 && newPass === confPass
  const handleEnter = (e) => { if (e.key === 'Enter' && canSubmit) onSubmit() }
  return (
    <div className="space-y-3">
      <PassInput value={newPass} onChange={setNewPass} placeholder="min 6 karakter" label="Password Baru" onKeyDown={handleEnter}/>
      <PassInput value={confPass} onChange={setConfPass} placeholder="ketik ulang" label="Konfirmasi Password" onKeyDown={handleEnter}/>
      {confPass && newPass !== confPass && (
        <p className="text-[10px] text-danger">⚠ Password tidak cocok</p>
      )}
      {newPass.length >= 6 && newPass === confPass && (
        <p className="text-[10px] text-success">✓ Password cocok — tekan Enter atau klik tombol di bawah</p>
      )}
      <button onClick={onSubmit} disabled={!canSubmit}
        className="w-full bg-success hover:bg-success/80 disabled:opacity-50 text-white font-medium py-2.5 rounded-xl text-sm flex items-center justify-center gap-2 transition-colors">
        {loading ? <RefreshCw size={13} className="animate-spin"/> : <Unlock size={13}/>}
        {loading ? 'Memproses...' : submitLabel}
      </button>
    </div>
  )
}

// ══════════════════════════════════════════════════════════════
// RECOVERY PANEL — semua metode
// ══════════════════════════════════════════════════════════════
function RecoveryPanel({ onBack }) {
  // method: null | 'email' | 'telegram' | 'token' | 'manual'
  const [method, setMethod]     = useState(null)
  const [step,   setStep]       = useState(1)
  const [done,   setDone]       = useState(false)

  // Email
  const [email,     setEmail]   = useState('')
  const [emailSent, setEmailSent] = useState(false)
  const [resetToken, setReset]  = useState('')

  // Telegram
  const [tgUser,  setTgUser]  = useState('')
  const [otpCode, setOtpCode] = useState('')
  const [otpSent, setOtpSent] = useState(false)

  // Token recovery
  const [recToken, setRecToken] = useState('')

  // New password (shared)
  const [newPass,  setNewPass]  = useState('')
  const [confPass, setConfPass] = useState('')
  const [loading,  setLoading]  = useState(false)

  const goBack = () => {
    setMethod(null); setStep(1); setDone(false)
    setEmail(''); setEmailSent(false); setReset('')
    setTgUser(''); setOtpCode(''); setOtpSent(false)
    setRecToken(''); setNewPass(''); setConfPass('')
  }

  // ── Sukses ────────────────────────────────────────────────
  if (done) return (
    <div className="p-6 text-center space-y-5">
      <div className="w-16 h-16 rounded-full bg-success/15 border-2 border-success/30 flex items-center justify-center mx-auto">
        <CheckCircle2 size={28} className="text-success"/>
      </div>
      <div>
        <div className="text-base font-semibold text-ink">Password Berhasil Direset!</div>
        <div className="text-xs text-ink-3 mt-1">Silakan login dengan password baru Anda.</div>
      </div>
      <button onClick={onBack}
        className="w-full bg-accent hover:bg-accent/80 text-white font-medium py-2.5 rounded-xl text-sm flex items-center justify-center gap-2">
        <LogIn size={13}/>Login Sekarang
      </button>
    </div>
  )

  // ── Set password baru (shared) ────────────────────────────
  // NewPassForm dipindah ke luar komponen — lihat di bawah

  // ── Pilih metode ──────────────────────────────────────────
  if (!method) return (
    <div className="p-5 space-y-3">
      <div className="text-center mb-4">
        <div className="text-sm font-semibold text-ink">Pilih Cara Reset Password</div>
        <div className="text-[11px] text-ink-3 mt-1">Pilih metode yang tersedia untuk Anda</div>
      </div>

      <MethodBtn icon="📧" title="Via Email"
        desc="Link reset dikirim ke email terdaftar (15 menit)"
        bg="bg-success/10" color="text-success"
        badge={{ text: 'Butuh SMTP', cls: 'bg-bg-4 text-ink-3' }}
        onClick={() => setMethod('email')}/>

      <MethodBtn icon="📱" title="Via Telegram OTP"
        desc="Kode 6 digit dikirim ke bot Telegram Anda"
        bg="bg-sky-400/10" color="text-sky-400"
        badge={{ text: 'Perlu setup dulu', cls: 'bg-sky-400/15 text-sky-400' }}
        onClick={() => setMethod('telegram')}/>

      <MethodBtn icon="🔑" title="Token Recovery"
        desc="Token dari Admin (menu Keamanan) — 15 menit, sekali pakai"
        bg="bg-warn/10" color="text-warn"
        onClick={() => setMethod('token')}/>

      <MethodBtn icon="💻" title="Reset Manual via Terminal"
        desc="Edit .env atau sqlite3 langsung di server"
        bg="bg-danger/10" color="text-danger"
        badge={{ text: 'Butuh akses server', cls: 'bg-danger/15 text-danger' }}
        onClick={() => setMethod('manual')}/>

      <button onClick={onBack}
        className="w-full text-xs text-ink-3 hover:text-ink py-2 flex items-center justify-center gap-1.5 transition-colors">
        <ArrowLeft size={11}/>Kembali ke Login
      </button>
    </div>
  )

  // ── EMAIL ─────────────────────────────────────────────────
  if (method === 'email') return (
    <div className="p-5 space-y-4">
      <div className="flex items-center gap-2 mb-1">
        <button onClick={goBack} className="text-ink-3 hover:text-ink"><ArrowLeft size={14}/></button>
        <span className="text-sm font-semibold text-ink">📧 Reset via Email</span>
      </div>

      {!emailSent ? (
        <>
          <div className="text-[11px] text-ink-3 bg-bg-4 rounded-xl p-3">
            Masukkan email yang terdaftar. Link reset akan dikirim ke email tersebut.
          </div>
          <div>
            <label className="block text-xs text-ink-2 mb-1.5">Alamat Email</label>
            <input value={email} onChange={e => setEmail(e.target.value)}
              placeholder="email@domain.com" type="email"
              onKeyDown={e => e.key === 'Enter' && email && handleSendEmail()}
              className="w-full bg-bg-3 border border-transparent rounded-xl px-3 py-2.5 text-sm text-ink placeholder-ink-3 outline-none focus:border-accent transition-colors"/>
          </div>
          <button onClick={async () => {
            if (!email.trim()) { toast.error('Isi email'); return }
            setLoading(true)
            try {
              const r = await api.sendEmailReset(email.trim())
              if (r.status === 'smtp_error') {
                toast.error('SMTP belum dikonfigurasi. Hubungi admin.')
                // Jika ada token dari server (SMTP error), tampilkan
                if (r.token) { setReset(r.token); setEmailSent(true) }
              } else {
                setEmailSent(true)
                toast.success('Link reset dikirim! Cek email Anda.')
              }
            } catch(e) { toast.error(e.message) }
            finally { setLoading(false) }
          }} disabled={loading || !email.trim()}
            className="w-full bg-success hover:bg-success/80 disabled:opacity-50 text-white font-medium py-2.5 rounded-xl text-sm flex items-center justify-center gap-2">
            {loading ? <RefreshCw size={13} className="animate-spin"/> : <Send size={13}/>}
            {loading ? 'Mengirim...' : 'Kirim Link Reset'}
          </button>
        </>
      ) : (
        <div className="space-y-3">
          {!resetToken ? (
            <div className="flex items-start gap-2.5 p-3 bg-success/8 border border-success/25 rounded-xl">
              <CheckCircle2 size={14} className="text-success flex-shrink-0 mt-0.5"/>
              <div className="text-[11px] text-ink-2">
                <strong className="text-success block mb-0.5">Email terkirim!</strong>
                Cek inbox atau folder spam <strong>{email}</strong>.
                Link berlaku 15 menit.
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="text-[11px] text-warn bg-warn/8 border border-warn/20 rounded-xl p-3">
                ⚠ SMTP belum dikonfigurasi. Gunakan token di bawah ini:
              </div>
              <div className="bg-bg-2 border border-transparent rounded-xl px-3 py-2 font-mono text-xs text-accent-2 break-all">{resetToken}</div>
            </div>
          )}
          <div className="text-[11px] text-ink-3 text-center">
            Sudah dapat link/token? Masukkan token di bawah:
          </div>
          <div>
            <label className="block text-xs text-ink-2 mb-1.5">Token dari Link Email</label>
            <input value={recToken} onChange={e => setRecToken(e.target.value)}
              placeholder="Token dari link email..."
              className="w-full bg-bg-3 border border-transparent rounded-xl px-3 py-2.5 text-sm font-mono text-ink placeholder-ink-3 outline-none focus:border-accent"/>
          </div>
          <NewPassForm newPass={newPass} setNewPass={setNewPass} confPass={confPass} setConfPass={setConfPass} loading={loading}
            onSubmit={async () => {
              setLoading(true)
              try {
                await api.resetPasswordEmail(recToken.trim(), newPass)
                setDone(true)
              } catch(e) { toast.error(e.message) }
              finally { setLoading(false) }
            }}/>
        </div>
      )}
    </div>
  )

  // ── TELEGRAM OTP ─────────────────────────────────────────
  if (method === 'telegram') return (
    <div className="p-5 space-y-4">
      <div className="flex items-center gap-2 mb-1">
        <button onClick={goBack} className="text-ink-3 hover:text-ink"><ArrowLeft size={14}/></button>
        <span className="text-sm font-semibold text-ink">📱 Reset via Telegram OTP</span>
      </div>

      {!otpSent ? (
        <div className="space-y-3">
          {/* Syarat + panduan */}
          <div className="space-y-2">
            <div className="bg-sky-400/8 border border-sky-400/20 rounded-xl p-3 text-[11px] text-ink-2 space-y-1.5">
              <div className="font-semibold text-sky-400 flex items-center gap-1.5">
                <MessageSquare size={12}/>Cara kerja:
              </div>
              <div>1. Masukkan username akun di bawah</div>
              <div>2. Kode OTP 6 digit dikirim ke bot Telegram Anda</div>
              <div>3. Masukkan kode + set password baru</div>
            </div>
            <div className="bg-warn/8 border border-warn/20 rounded-xl p-3 text-[10px] text-warn">
              <strong className="block mb-0.5">⚠ Syarat:</strong>
              Telegram OTP harus sudah disetup sebelumnya di menu <strong>2FA & Login</strong> saat masih bisa login.
              Jika belum pernah setup, gunakan metode lain (Token Recovery atau Reset Manual).
            </div>
          </div>

          <div>
            <label className="block text-xs text-ink-2 mb-1.5">Username Akun</label>
            <input value={tgUser} onChange={e => setTgUser(e.target.value)}
              placeholder="username (tanpa @)" autoFocus
              onKeyDown={e => e.key === 'Enter' && cleanUsername(tgUser) && (async () => {
                setLoading(true)
                try {
                  await api.sendTelegramReset(cleanUsername(tgUser))
                  setOtpSent(true)
                  toast('Kode OTP dikirim ke Telegram!', { icon: '📱' })
                } catch(e) { toast.error(e.message) }
                finally { setLoading(false) }
              })()}
              className="w-full bg-bg-3 border border-transparent rounded-xl px-3 py-2.5 text-sm text-ink placeholder-ink-3 outline-none focus:border-accent transition-colors"/>
          </div>

          <button onClick={async () => {
            if (!cleanUsername(tgUser)) { toast.error('Isi username'); return }
            setLoading(true)
            try {
              await api.sendTelegramReset(cleanUsername(tgUser))
              setOtpSent(true)
              toast('Kode OTP dikirim ke Telegram!', { icon: '📱' })
            } catch(e) { toast.error(e.message) }
            finally { setLoading(false) }
          }} disabled={loading || !cleanUsername(tgUser)}
            className="w-full bg-sky-500 hover:bg-sky-600 disabled:opacity-50 text-white font-medium py-2.5 rounded-xl text-sm flex items-center justify-center gap-2 transition-colors">
            {loading ? <RefreshCw size={13} className="animate-spin"/> : <MessageSquare size={13}/>}
            {loading ? 'Mengirim...' : 'Kirim Kode OTP ke Telegram'}
          </button>

          {/* Jika belum setup */}
          <div className="border border-warn/30 rounded-xl p-3 text-[10px] text-warn space-y-1">
            <div className="font-semibold">Belum setup Telegram OTP?</div>
            <div>Login dulu dengan cara lain → buka menu <strong>2FA & Login</strong> → setup OTP Telegram</div>
            <div>Atau pilih metode reset lain: Token Recovery atau Reset Manual</div>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center gap-2.5 p-3 bg-success/8 border border-success/25 rounded-xl">
            <CheckCircle2 size={14} className="text-success flex-shrink-0"/>
            <div className="text-[11px] text-ink-2">
              <strong className="text-success block mb-0.5">OTP Terkirim!</strong>
              Cek Telegram Anda — kode 6 digit sudah dikirim ke bot AI ORCHESTRATOR
            </div>
          </div>

          <div>
            <label className="block text-xs text-ink-2 mb-1.5">Kode OTP (6 digit)</label>
            <OtpBoxes value={otpCode} onChange={setOtpCode} onEnter={handleOtpVerify}/>
          </div>

          <NewPassForm newPass={newPass} setNewPass={setNewPass} confPass={confPass} setConfPass={setConfPass} loading={loading}
            submitLabel="Verifikasi & Reset Password"
            onSubmit={async () => {
              const clean = otpCode.replace(/ /g,'')
              if (clean.length !== 6) { toast.error('Masukkan 6 digit kode OTP'); return }
              setLoading(true)
              try {
                await api.telegramResetPass(cleanUsername(tgUser), clean, newPass)
                setDone(true)
              } catch(e) { toast.error(e.message); setOtpCode('') }
              finally { setLoading(false) }
            }}/>

          <button onClick={async () => {
            setOtpSent(false); setOtpCode('')
            // Kirim ulang OTP
            try {
              await api.sendTelegramReset(cleanUsername(tgUser))
              setOtpSent(true)
              toast('OTP baru dikirim!', { icon: '📱' })
            } catch(e) { toast.error(e.message) }
          }}
            className="w-full text-xs text-ink-3 hover:text-ink flex items-center justify-center gap-1.5 py-1">
            <RefreshCw size={10}/>Kirim ulang OTP
          </button>
        </div>
      )}
    </div>
  )

  // ── TOKEN RECOVERY ────────────────────────────────────────
  if (method === 'token') return (
    <div className="p-5 space-y-4">
      <div className="flex items-center gap-2 mb-1">
        <button onClick={goBack} className="text-ink-3 hover:text-ink"><ArrowLeft size={14}/></button>
        <span className="text-sm font-semibold text-ink">🔑 Token Recovery</span>
      </div>

      {/* Panduan langkah */}
      <div className="bg-bg-4 border border-transparent rounded-xl p-3 text-[11px] text-ink-3 space-y-1.5">
        <div className="text-ink-2 font-semibold mb-1">Cara menggunakan:</div>
        <div className="flex gap-2"><span className="text-accent-2 font-semibold flex-shrink-0">1.</span>
          <span>Minta Admin generate token di menu <strong className="text-ink-2">Admin → Recovery Token</strong></span></div>
        <div className="flex gap-2"><span className="text-accent-2 font-semibold flex-shrink-0">2.</span>
          <span>Admin pilih akun Anda saat generate token</span></div>
        <div className="flex gap-2"><span className="text-accent-2 font-semibold flex-shrink-0">3.</span>
          <span>Isi username, paste token, dan set password baru di bawah</span></div>
        <div className="text-warn font-medium pt-0.5">⏱ Token berlaku 15 menit, hanya 1x pakai</div>
      </div>

      {/* Step 1: Username */}
      <div>
        <label className="block text-xs text-ink-2 mb-1.5">
          Username Akun yang Ingin Direset
        </label>
        <input value={tgUser} onChange={e => setTgUser(e.target.value)}
          placeholder="username (tanpa @)"
          autoFocus
          className="w-full bg-bg-3 border border-transparent rounded-xl px-3 py-2.5 text-sm text-ink placeholder-ink-3 outline-none focus:border-accent transition-colors"/>
        <p className="text-[10px] text-ink-3 mt-1">Username harus sesuai dengan akun yang token-nya di-generate oleh Admin</p>
      </div>

      {/* Step 2: Token */}
      <div>
        <label className="block text-xs text-ink-2 mb-1.5">Token Recovery (dari Admin)</label>
        <textarea value={recToken} onChange={e => setRecToken(e.target.value)}
          placeholder="Paste token di sini..."
          rows={2}
          className="w-full bg-bg-3 border border-transparent rounded-xl px-3 py-2.5 text-sm font-mono text-ink placeholder-ink-3 outline-none focus:border-accent transition-colors resize-none"/>
      </div>

      {/* Step 3: Password baru */}
      <NewPassForm newPass={newPass} setNewPass={setNewPass} confPass={confPass} setConfPass={setConfPass} loading={loading}
        onSubmit={async () => {
          if (!cleanUsername(tgUser)) { toast.error('Isi username akun'); return }
          if (!recToken.trim()) { toast.error('Paste token recovery dari Admin'); return }
          setLoading(true)
          try {
            await api.useRecoveryToken(recToken.trim(), newPass, cleanUsername(tgUser))
            setDone(true)
          } catch(e) { toast.error(e.message) }
          finally { setLoading(false) }
        }}
        submitLabel="Reset Password Akun"/>
    </div>
  )

  // ── MANUAL ───────────────────────────────────────────────
  if (method === 'manual') return (
    <div className="p-5 space-y-3">
      <div className="flex items-center gap-2 mb-1">
        <button onClick={goBack} className="text-ink-3 hover:text-ink"><ArrowLeft size={14}/></button>
        <span className="text-sm font-semibold text-ink">💻 Reset Manual via Terminal</span>
      </div>

      {[
        {
          n: 'A', color: 'bg-success/15 text-success border-success/30',
          title: 'Jalankan Skrip Reset (Opsi Pertama)',
          steps: [
            'Buka Terminal Server',
            'Masuk folder aplikasi (cd /path/ke/ai-super)',
            'Jalankan: python reset_admin.py',
            'Login dengan username: admin, password: admin',
          ],
        },
        {
          n: 'B', color: 'bg-warn/15 text-warn border-warn/30',
          title: 'Reset via Python (hash baru)',
          steps: [
            'cd ~/Downloads/ai-orchestrator/backend',
            'source venv/bin/activate',
            'python3 -c "from core.auth import hash_password; print(hash_password(\'PasswordBaru!\'))"',
            'Copy hash → lanjut ke langkah C',
          ],
        },
        {
          n: 'C', color: 'bg-danger/15 text-danger border-danger/30',
          title: 'Update database langsung',
          steps: [
            'sqlite3 data/ai-orchestrator.db',
            "UPDATE users SET hashed_password='[HASH_DARI_B]' WHERE username='admin';",
            '.quit',
          ],
        },
      ].map(item => (
        <div key={item.n} className={clsx('border rounded-xl p-3', item.color)}>
          <div className="text-xs font-semibold mb-2">Opsi {item.n}: {item.title}</div>
          <div className="space-y-1.5">
            {item.steps.map((s, i) => (
              <div key={i} className="flex gap-2">
                <span className="text-[10px] opacity-60 flex-shrink-0 w-4">{i+1}.</span>
                <code className="text-[10px] font-mono bg-bg-2/50 px-1.5 py-0.5 rounded flex-1 break-all">{s}</code>
              </div>
            ))}
          </div>
        </div>
      ))}

      <button onClick={goBack}
        className="w-full text-xs text-ink-3 hover:text-ink py-2 flex items-center justify-center gap-1.5 transition-colors">
        <ArrowLeft size={11}/>Kembali
      </button>
    </div>
  )

  return null
}

// ══════════════════════════════════════════════════════════════
// MAIN LOGIN PAGE
// ══════════════════════════════════════════════════════════════
export default function Login() {
  const [tab,      setTab]      = useState('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPass, setShowPass] = useState(false)
  const [loading,  setLoading]  = useState(false)
  const [attempts, setAttempts] = useState(0)

  // 2FA OTP step (setelah password benar)
  const [otpMode,    setOtpMode]  = useState(null)   // null | 'totp' | 'telegram'
  const [otpCode,    setOtpCode]  = useState('')
  const [otpLoading, setOtpLoad]  = useState(false)

  // App profile untuk logo
  const [appName, setAppName] = useState('AI ORCHESTRATOR')
  const [logoUrl, setLogoUrl] = useState('')

  const { setAuth } = useAuthStore()
  const navigate    = useNavigate()

  // Load app profile untuk logo & nama — useEffect agar hanya dipanggil sekali
  useEffect(() => {
    api.getAppProfile().then(p => {
      if (p.app_name) setAppName(p.app_name)
      if (p.logo_b64) setLogoUrl(p.logo_b64)
    }).catch(() => {})
  }, [])

  const handleLogin = async (e) => {
    e.preventDefault()
    if (!cleanUsername(username) || !password.trim()) { toast.error('Isi username dan password'); return }
    setLoading(true)
    try {
      const res = await api.login(cleanUsername(username), password)

      // Jika 2FA aktif — JANGAN simpan token dulu, minta verifikasi 2FA
      if (res.require_2fa) {
        setOtpMode(res.require_2fa)
        if (res.require_2fa === 'telegram') {
          try {
            await api.sendTelegramOtp(cleanUsername(username))
            toast('Kode OTP dikirim ke Telegram Anda', { icon: '📱' })
          } catch(e) {
            toast.error('Gagal kirim OTP Telegram: ' + e.message)
          }
        } else if (res.require_2fa === 'totp') {
          toast('Masukkan kode dari Google Authenticator', { icon: '🔐' })
        }
        // Simpan token sementara untuk dipakai setelah verify
        window._pendingToken  = res.access_token
        window._pendingUser   = res.user
        return
      }

      // Tidak ada 2FA — langsung login
      setAuth(res.access_token, res.user)
      toast.success('Selamat datang, ' + res.user.username + '!')
      navigate('/dashboard')
    } catch (err) {
      setAttempts(a => a + 1)
      toast.error(err.message || 'Login gagal')
    } finally {
      setLoading(false)
    }
  }

  const handleOtpVerify = async () => {
    const clean = otpCode.replace(/ /g, '')
    if (clean.length !== 6) { toast.error('Masukkan 6 digit kode'); return }
    setOtpLoad(true)
    try {
      let res
      if (otpMode === 'totp')     res = await api.totpVerifyLogin(cleanUsername(username), clean)
      if (otpMode === 'telegram') res = await api.verifyTelegramOtp(cleanUsername(username), clean)
      if (res && res.access_token) {
        setAuth(res.access_token, res.user)
      } else if (window._pendingToken) {
        // Fallback: gunakan token dari login pertama jika verify sukses
        setAuth(window._pendingToken, window._pendingUser)
        delete window._pendingToken
        delete window._pendingUser
      }
      toast.success('Login berhasil!')
      navigate('/dashboard')
    } catch(err) {
      toast.error(err.message || 'Kode salah')
      setOtpCode('')
    } finally { setOtpLoad(false) }
  }

  return (
    <div className="min-h-screen bg-bg flex items-center justify-center p-4">
      <div className="w-full max-w-sm">

        {/* Logo & nama app */}
        <div className="text-center mb-6">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-accent to-accent-2 flex items-center justify-center mx-auto mb-3 shadow-xl shadow-accent/30 overflow-hidden">
            {logoUrl
              ? <img src={logoUrl} alt="logo" className="w-full h-full object-contain"/>
              : <span className="text-3xl">🧠</span>
            }
          </div>
          <h1 className="text-2xl font-semibold text-ink">{appName}</h1>
          <p className="text-ink-3 text-sm mt-1">AI Orchestrator</p>
        </div>

        {/* Card */}
        <div className="bg-bg-2 border border-transparent rounded-2xl overflow-hidden shadow-2xl">

          {/* Tab header */}
          {tab !== 'recovery' ? (
            <div className="flex border-b border-transparent">
              <button onClick={() => { setTab('login'); setOtpMode(null); setOtpCode('') }}
                className={clsx('flex-1 flex items-center justify-center gap-1.5 py-3 text-xs font-medium transition-colors',
                  tab === 'login' ? 'text-accent-2 border-b-2 border-accent bg-accent/5' : 'text-ink-3 hover:text-ink')}>
                <LogIn size={13}/>Masuk
              </button>
              <button onClick={() => setTab('recovery')}
                className="flex-1 flex items-center justify-center gap-1.5 py-3 text-xs font-medium text-ink-3 hover:text-ink transition-colors">
                🔑 Lupa Password?
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2 px-4 py-3 border-b border-transparent">
              <button onClick={() => setTab('login')} className="text-ink-3 hover:text-ink">
                <ArrowLeft size={14}/>
              </button>
              <span className="text-sm font-semibold text-ink">Reset Password</span>
            </div>
          )}

          {/* Login */}
          {tab === 'login' && !otpMode && (
            <div className="p-6">
              <form onSubmit={handleLogin} className="space-y-4">
                <div>
                  <label className="block text-xs text-ink-2 mb-1.5">Username</label>
                  <input value={username} onChange={e => setUsername(e.target.value)}
                    placeholder="admin" autoFocus autoComplete="username"
                    className="w-full bg-bg-3 border border-transparent rounded-xl px-3 py-2.5 text-sm text-ink placeholder-ink-3 outline-none focus:border-accent transition-colors"/>
                </div>
                <div>
                  <label className="block text-xs text-ink-2 mb-1.5">Password</label>
                  <div className="relative">
                    <input type={showPass ? 'text' : 'password'}
                      value={password} onChange={e => setPassword(e.target.value)}
                      placeholder="••••••••" autoComplete="current-password"
                      className="w-full bg-bg-3 border border-transparent rounded-xl px-3 py-2.5 pr-10 text-sm text-ink placeholder-ink-3 outline-none focus:border-accent transition-colors"/>
                    <button type="button" onClick={() => setShowPass(!showPass)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-3 hover:text-ink">
                      {showPass ? <EyeOff size={15}/> : <Eye size={15}/>}
                    </button>
                  </div>
                </div>

                {attempts >= 3 && (
                  <div className="flex items-start gap-2 text-[10px] text-warn bg-warn/8 border border-warn/25 rounded-xl p-2.5">
                    <span className="flex-shrink-0">⚠</span>
                    <span>Terlalu banyak percobaan? Klik <button type="button" onClick={() => setTab('recovery')}
                      className="underline font-semibold">Lupa Password?</button> untuk reset.</span>
                  </div>
                )}

                <button type="submit" disabled={loading}
                  className="w-full bg-accent hover:bg-accent/80 disabled:opacity-50 text-white font-medium py-2.5 rounded-xl text-sm flex items-center justify-center gap-2 transition-colors">
                  {loading ? <><RefreshCw size={13} className="animate-spin"/>Masuk...</> : <><LogIn size={13}/>Masuk</>}
                </button>
              </form>
            </div>
          )}

          {/* 2FA OTP setelah login */}
          {tab === 'login' && otpMode && (
            <div className="p-6 space-y-4">
              <div className="text-center">
                <div className="text-2xl mb-2">{otpMode === 'totp' ? '🔐' : '📱'}</div>
                <div className="text-sm font-semibold text-ink">
                  {otpMode === 'totp' ? 'Kode Authenticator' : 'Kode OTP Telegram'}
                </div>
                <div className="text-[11px] text-ink-3 mt-1">
                  {otpMode === 'totp'
                    ? 'Buka Google Authenticator / Authy → masukkan kode 6 digit'
                    : 'Cek Telegram Anda — kode sudah dikirim ke bot'}
                </div>
              </div>
              <OtpBoxes value={otpCode} onChange={setOtpCode} onEnter={handleOtpVerify}/>
              <button onClick={handleOtpVerify} disabled={otpLoading || otpCode.replace(/ /g,'').length !== 6}
                className="w-full bg-success hover:bg-success/80 disabled:opacity-50 text-white font-medium py-2.5 rounded-xl text-sm flex items-center justify-center gap-2">
                {otpLoading ? <RefreshCw size={13} className="animate-spin"/> : null}
                {otpLoading ? 'Verifikasi...' : '✓ Verifikasi & Masuk'}
              </button>
              <button onClick={() => { setOtpMode(null); setOtpCode('') }}
                className="w-full text-xs text-ink-3 hover:text-ink flex items-center justify-center gap-1">
                <ArrowLeft size={11}/>Kembali
              </button>
            </div>
          )}

          {/* Recovery */}
          {tab === 'recovery' && (
            <RecoveryPanel onBack={() => setTab('login')}/>
          )}
        </div>

      </div>
    </div>
  )
}
