import { useState, useEffect } from 'react'
import { api } from '../hooks/useApi'
import { copyToClipboard } from "../utils/clipboard"
import { useAuthStore } from '../store'
import toast from 'react-hot-toast'
import {
  Shield, Key, RefreshCw, Eye, EyeOff, CheckCircle2,
  XCircle, AlertTriangle, Copy, Check, Lock, Unlock,
  Clock, User, Terminal, ChevronDown, ChevronUp,
  FileKey, RotateCcw, Info, LogIn,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import clsx from 'clsx'

// ── Primitive ─────────────────────────────────────────────────
function Label({ children }) {
  return <label className="block text-xs text-ink-3 mb-2 uppercase tracking-widest font-bold opacity-60">{children}</label>
}
function SecretInp({ value, onChange, placeholder, disabled }) {
  const [show, setShow] = useState(false)
  return (
    <div className="relative">
      <input type={show ? 'text' : 'password'} value={value} onChange={e => onChange(e.target.value)}
        placeholder={placeholder} disabled={disabled} autoComplete="new-password"
        className="w-full bg-bg-2 border-2 border-border-2 rounded-xl px-4 py-3 pr-10 text-sm text-ink placeholder-ink-3 outline-none focus:border-accent font-mono disabled:opacity-50 shadow-inner"/>
      <button type="button" onClick={() => setShow(!show)} className="absolute right-3.5 top-1/2 -translate-y-1/2 text-ink-3 hover:text-ink transition-all">
        {show ? <EyeOff size={16}/> : <Eye size={16}/>}
      </button>
    </div>
  )
}
function Btn({ label, onClick, loading, variant = 'primary', icon: Icon, disabled, full }) {
  return (
    <button onClick={onClick} disabled={loading || disabled}
      className={clsx('flex items-center justify-center gap-2 px-5 py-3 text-sm rounded-xl font-bold uppercase tracking-widest transition-all disabled:opacity-50 active:scale-95 shadow-md',
        full && 'w-full',
        variant === 'primary' && 'bg-accent hover:bg-accent/80 text-white',
        variant === 'success' && 'bg-success/10 hover:bg-success/20 border-2 border-success/30 text-success',
        variant === 'warn'    && 'bg-warn/10 hover:bg-warn/20 border-2 border-warn/30 text-warn',
        variant === 'danger'  && 'bg-danger/10 hover:bg-danger/20 border-2 border-danger/30 text-danger',
        variant === 'default' && 'bg-bg-4 hover:bg-bg-5 border-2 border-border text-ink-2 hover:text-ink',
      )}>
      {loading ? <RefreshCw size={14} className="animate-spin"/> : Icon && <Icon size={14}/>}
      {label}
    </button>
  )
}
function Card({ title, icon: Icon, iconColor = 'text-accent-2', children, badge, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="bg-bg-3 border-2 border-border rounded-2xl overflow-hidden shadow-lg">
      <button onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-5 py-4 border-b-2 border-border hover:bg-bg-4/50 transition-all">
        <Icon size={18} className={iconColor}/>
        <span className="text-base font-bold text-ink uppercase tracking-tight flex-1 text-left">{title}</span>
        {badge}
        {open ? <ChevronUp size={16} className="text-ink-3"/> : <ChevronDown size={16} className="text-ink-3"/>}
      </button>
      {open && <div className="p-6">{children}</div>}
    </div>
  )
}
function CopyBtn({ text }) {
  const [ok, setOk] = useState(false)
  return (
    <button onClick={() => { copyToClipboard(text); setOk(true); setTimeout(() => setOk(false), 2000) }}
      className="p-2 rounded-lg hover:bg-bg-5 text-ink-3 hover:text-ink transition-all flex-shrink-0">
      {ok ? <Check size={16} className="text-success"/> : <Copy size={16}/>}
    </button>
  )
}
function CodeLine({ cmd }) {
  return (
    <div className="flex items-center gap-3 bg-bg-2 border-2 border-border rounded-xl px-4 py-3 font-mono text-xs shadow-inner">
      <span className="text-accent-2 flex-1 font-bold">{cmd}</span>
      <CopyBtn text={cmd}/>
    </div>
  )
}

// ── Password Strength ─────────────────────────────────────────
function PasswordStrength({ password }) {
  const checks = [
    { label: 'Minimal 8 karakter',        ok: password.length >= 8 },
    { label: 'Ada huruf besar',            ok: /[A-Z]/.test(password) },
    { label: 'Ada huruf kecil',            ok: /[a-z]/.test(password) },
    { label: 'Ada angka',                  ok: /[0-9]/.test(password) },
    { label: 'Ada simbol (!@#$%...)',      ok: /[^a-zA-Z0-9]/.test(password) },
  ]
  const score = checks.filter(c => c.ok).length
  const label = ['Sangat Lemah', 'Lemah', 'Cukup', 'Kuat', 'Sangat Kuat', 'Sempurna'][score]
  const color = ['bg-danger', 'bg-danger', 'bg-warn', 'bg-warn', 'bg-success', 'bg-success'][score]

  if (!password) return null
  return (
    <div className="mt-2 space-y-1.5">
      <div className="flex gap-1 h-1">
        {[0,1,2,3,4].map(i => (
          <div key={i} className={clsx('flex-1 rounded-full transition-all', i < score ? color : 'bg-bg-5')}/>
        ))}
      </div>
      <div className="text-[10px] text-ink-3 font-bold uppercase tracking-widest opacity-60">Kekuatan: <span className={clsx('font-bold',
        score <= 1 ? 'text-danger' : score <= 3 ? 'text-warn' : 'text-success')}>{label}</span></div>
      <div className="grid grid-cols-2 gap-2">
        {checks.map(c => (
          <div key={c.label} className={clsx('flex items-center gap-2 text-[10px] font-bold uppercase tracking-tight', c.ok ? 'text-success' : 'text-ink-3 opacity-50')}>
            {c.ok ? <CheckCircle2 size={11}/> : <XCircle size={11}/>}{c.label}
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────
export default function Security() {
  const { t } = useTranslation()
  const { user } = useAuthStore()
  const isAdmin  = user?.is_admin

  // Change password
  const [curPass,  setCurPass]  = useState('')
  const [newPass,  setNewPass]  = useState('')
  const [confPass, setConfPass] = useState('')
  const [savingPw, setSavingPw] = useState(false)

  // Recovery token (admin)
  const [recovToken,  setRecovToken]  = useState('')
  const [genLoading,  setGenLoading]  = useState(false)

  // Use recovery token
  const [useToken,    setUseToken]    = useState('')
  const [useNewPass,  setUseNewPass]  = useState('')
  const [useLoading,  setUseLoading]  = useState(false)
  const [useSuccess,  setUseSuccess]  = useState(false)

  // Login logs
  const [logs,    setLogs]    = useState([])
  const [loadLog, setLoadLog] = useState(false)

  useEffect(() => {
    if (isAdmin) {
      loadLogs()
      api.listUsers().then(setUsers).catch(() => {})
    }
  }, [isAdmin])

  // Countdown timer untuk token
  useEffect(() => {
    if (countdown <= 0) return
    const t = setTimeout(() => setCountdown(c => c - 1), 1000)
    return () => clearTimeout(t)
  }, [countdown])

  const loadLogs = async () => {
    setLoadLog(true)
    try { setLogs(await api.loginLogs()) } catch {}
    finally { setLoadLog(false) }
  }

  // Change password
  const handleChangePass = async () => {
    if (!curPass.trim())          { toast.error('Isi password lama'); return }
    if (newPass.length < 6)       { toast.error('Password baru minimal 6 karakter'); return }
    if (newPass !== confPass)      { toast.error('Konfirmasi password tidak cocok'); return }
    if (newPass === curPass)       { toast.error('Password baru harus berbeda'); return }
    setSavingPw(true)
    try {
      await api.changePassword(curPass, newPass)
      toast.success('Password berhasil diubah!')
      setCurPass(''); setNewPass(''); setConfPass('')
    } catch(e) { toast.error(e.message || 'Gagal mengubah password') }
    finally { setSavingPw(false) }
  }

  // Generate recovery token - langsung via JWT auth (tidak perlu SECRET_KEY)
  const handleGenToken = async () => {
    setGenLoading(true)
    try {
      const r = await api.generateRecoveryToken()
      setRecovToken(r.token)
      toast.success('Token recovery dibuat! Berlaku 15 menit, sekali pakai.')
    } catch(e) { toast.error(e.message) }
    finally { setGenLoading(false) }
  }

  // Use recovery token
  const handleUseToken = async () => {
    if (!useToken.trim())       { toast.error('Isi token recovery'); return }
    if (useNewPass.length < 6)  { toast.error('Password minimal 6 karakter'); return }
    setUseLoading(true)
    try {
      await api.useRecoveryToken(useToken, useNewPass)
      setUseSuccess(true)
      toast.success('Password berhasil direset! Silakan login.')
      setUseToken(''); setUseNewPass('')
    } catch(e) { toast.error(e.message) }
    finally { setUseLoading(false) }
  }

  return (
    <div className="p-4 md:p-6 w-full space-y-4">
      {/* Header */}
      <div className="mb-2">
        <h1 className="text-3xl font-bold text-ink uppercase tracking-tighter flex items-center gap-3">
          <Shield size={28} className="text-accent-2"/>{t('account_security')}
        </h1>
        <p className="text-base text-ink-3 mt-1 font-semibold uppercase tracking-tight opacity-70">{t('security_desc')}</p>
      </div>

      {/* ── Security Status ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { icon: Lock, label: 'Brute Force', value: 'Aktif', sub: 'Blokir 5 gagal', ok: true, color: 'text-success', bg: 'bg-success/10' },
          { icon: Clock, label: 'Session JWT', value: '7 Hari', sub: 'Auto-expire', ok: true, color: 'text-accent-2', bg: 'bg-accent/10' },
          { icon: FileKey, label: 'Recovery Token', value: '1 Jam', sub: 'One-time use', ok: true, color: 'text-warn', bg: 'bg-warn/10' },
          { icon: LogIn, label: 'Login Log', value: logs.length + ' entri', sub: 'Tersimpan DB', ok: true, color: 'text-sky-400', bg: 'bg-sky-400/10' },
        ].map(s => (
          <div key={s.label} className="bg-bg-3 border-2 border-border rounded-2xl p-5 shadow-lg">
            <div className={clsx('w-9 h-9 rounded-xl flex items-center justify-center mb-3', s.bg)}>
              <s.icon size={16} className={s.color}/>
            </div>
            <div className="text-xl font-bold text-ink uppercase tracking-tighter font-mono">{s.value}</div>
            <div className="text-xs text-ink-2 font-bold uppercase tracking-widest mt-1.5 opacity-80">{s.label}</div>
            <div className="text-[10px] text-ink-3 font-semibold uppercase tracking-widest opacity-60 mt-1">{s.sub}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">

        {/* ── Ganti Password ── */}
        <Card title={t('change_password')} icon={Key} iconColor="text-accent-2">
          <div className="space-y-3">
            <div>
              <Label>{t('current_password')}</Label>
              <SecretInp value={curPass} onChange={setCurPass} placeholder={t('current_password') + '...'}/>
            </div>
            <div>
              <Label>{t('new_password')}</Label>
              <SecretInp value={newPass} onChange={setNewPass} placeholder={t('new_password') + '...'}/>
              <PasswordStrength password={newPass}/>
            </div>
            {newPass && (
              <div>
                <Label>Konfirmasi Password Baru</Label>
                <SecretInp value={confPass} onChange={setConfPass} placeholder="ketik ulang..."/>
                {confPass && newPass !== confPass && (
                  <p className="text-[11px] text-danger mt-2 font-bold uppercase tracking-widest">⚠ Password tidak cocok</p>
                )}
              </div>
            )}
            <Btn label={t('change_password')} onClick={handleChangePass}
              loading={savingPw} icon={Key} full
              disabled={!curPass || !newPass || newPass !== confPass}/>

            {/* Tips password */}
            <div className="bg-bg-4 border-2 border-border/40 rounded-2xl p-4 text-xs text-ink-3 space-y-2 font-semibold shadow-inner">
              <div className="text-ink-2 font-bold uppercase tracking-widest mb-2 opacity-80">💡 Tips password kuat:</div>
              <div className="flex items-start gap-2">• <span>Minimal 12 karakter, campuran huruf besar/kecil, angka, simbol</span></div>
              <div className="flex items-start gap-2">• <span>Jangan gunakan nama, tanggal lahir, atau kata umum</span></div>
              <div className="flex items-start gap-2">• <span>Gunakan password manager (Bitwarden, 1Password, dll)</span></div>
              <div className="flex items-start gap-2">• <span>Ganti password secara berkala setiap 3-6 bulan</span></div>
            </div>
          </div>
        </Card>

        {/* ── Ide Keamanan Mendatang ── */}
        <Card title={t('upcoming_security')} icon={Shield} iconColor="text-warn"
          badge={<span className="text-[10px] bg-warn/15 text-warn px-3 py-1 rounded-full font-bold uppercase tracking-widest border border-warn/30 shadow-sm">Roadmap</span>}>
          <div className="space-y-2.5">
            {[
              {
                icon: '📱', title: 'Two-Factor Auth (2FA)',
                desc: 'Kode OTP via Telegram Bot atau Google Authenticator (TOTP)',
                how: 'Saat login, user kirim kode 6 digit dari aplikasi authenticator',
                status: 'soon',
              },
              {
                icon: '📧', title: 'Reset Password via Email',
                desc: 'Link reset dikirim ke email yang terdaftar via SMTP/SendGrid',
                how: 'Isi email → dapat link → klik → set password baru',
                status: 'soon',
              },
              {
                icon: '🔑', title: 'Passkey / WebAuthn',
                desc: 'Login tanpa password menggunakan fingerprint atau face ID',
                how: 'Daftar passkey di browser → login hanya dengan biometrik',
                status: 'future',
              },
              {
                icon: '🛡️', title: 'IP Allowlist',
                desc: 'Batasi akses hanya dari IP atau range IP tertentu',
                how: 'Set daftar IP di .env — request dari luar ditolak otomatis',
                status: 'future',
              },
              {
                icon: '🔔', title: 'Notifikasi Login Mencurigakan',
                desc: 'Kirim notifikasi ke Telegram jika ada login dari IP baru',
                how: 'Deteksi IP baru → kirim alert ke bot Telegram admin',
                status: 'soon',
              },
              {
                icon: '⏱️', title: 'Session Management',
                desc: 'Lihat dan logout semua sesi aktif dari perangkat lain',
                how: 'Dashboard sesi aktif + tombol "Logout semua perangkat"',
                status: 'soon',
              },
            ].map(f => (
              <div key={f.title} className="bg-bg-4 border-2 border-border/50 rounded-2xl p-4 hover:border-accent/30 transition-all shadow-sm group">
                <div className="flex items-start gap-4">
                  <span className="text-2xl flex-shrink-0 group-hover:scale-110 transition-transform">{f.icon}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 flex-wrap">
                      <span className="text-base font-bold text-ink uppercase tracking-tight">{f.title}</span>
                      <span className={clsx('text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-widest border shadow-sm',
                        f.status === 'soon' ? 'bg-accent/15 text-accent-2 border-accent/30' : 'bg-bg-5 text-ink-3 border-border/50')}>
                        {f.status === 'soon' ? '🚀 Segera' : '🔮 Masa Depan'}
                      </span>
                    </div>
                    <div className="text-sm text-ink-3 mt-1 font-semibold leading-relaxed">{f.desc}</div>
                    <div className="text-[11px] text-ink-2 mt-2 flex items-center gap-2 font-bold uppercase tracking-tight opacity-70">
                      <Info size={12} className="text-accent-2 flex-shrink-0"/>
                      {f.how}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>

      </div>

      {/* ── Recovery Token (Admin) ── */}
      {isAdmin && (
        <Card title={`🔑 ${t('generate_recovery_token')}`} icon={FileKey} iconColor="text-warn"
          badge={<span className="text-[10px] bg-warn/15 text-warn px-3 py-1 rounded-full font-bold uppercase tracking-widest border border-warn/30 shadow-sm">Admin Only</span>}
          defaultOpen={false}>
          <div className="space-y-4">

            {/* Info */}
            <div className="flex items-start gap-3 p-4 bg-accent/10 border-2 border-accent/20 rounded-2xl text-xs text-ink-2 font-semibold shadow-inner">
              <Info size={16} className="text-accent-2 flex-shrink-0 mt-0.5"/>
              <div className="leading-relaxed">
                <strong className="text-ink block mb-1 font-bold uppercase tracking-tight">Cara pakai Token Recovery:</strong>
                Admin generate token → kirim ke user yang lupa password →
                user paste token di halaman login (tab "Lupa Password?" → Token Recovery).
                Token berlaku <strong className="text-accent-2 font-bold">15 menit</strong> dan hanya bisa dipakai <strong className="text-accent-2 font-bold">1 kali</strong>.
              </div>
            </div>

            {/* Pilih target user */}
            <div>
              <Label>Generate Token untuk:</Label>
              <select value={genTargetId} onChange={e => setGenTargetId(e.target.value)}
                className="w-full bg-bg-2 border-2 border-border-2 rounded-xl px-4 py-3 text-sm font-bold text-ink outline-none focus:border-accent appearance-none cursor-pointer shadow-inner">
                <option value="">Diri sendiri (Admin)</option>
                {users.filter(u => !u.is_admin || u.id !== undefined).map(u => (
                  <option key={u.id} value={u.id}>{u.username} ({u.role})</option>
                ))}
              </select>
            </div>

            {/* Generate button */}
            <Btn label="Generate Token Recovery" onClick={() => handleGenToken(genTargetId)}
              loading={genLoading} variant="warn" icon={FileKey}/>

            {/* Token result */}
            {recovToken && (
              <div className="bg-success/10 border-2 border-success/40 rounded-2xl p-5 space-y-4 shadow-lg">
                <div className="flex items-center justify-between flex-wrap gap-3">
                  <div className="flex items-center gap-3">
                    <CheckCircle2 size={18} className="text-success"/>
                    <span className="text-base font-bold text-success uppercase tracking-tight">Token Dibuat!</span>
                    <span className="text-xs text-ink-3 font-bold uppercase tracking-widest opacity-60">untuk: <strong className="text-ink">{recovToken.username}</strong></span>
                  </div>
                  <div className={clsx('text-sm font-mono font-bold px-3 py-1.5 rounded-xl shadow-inner border border-border/20',
                    countdown > 120 ? 'bg-success/20 text-success' : 'bg-danger/20 text-danger animate-pulse')}>
                    ⏱ {fmtCountdown(countdown)}
                  </div>
                </div>

                <div className="bg-bg-2 border-2 border-border rounded-2xl p-4 shadow-inner">
                  <div className="text-xs text-warn mb-2 flex items-center gap-2 font-bold uppercase tracking-widest opacity-80">
                    <AlertTriangle size={14}/>Token hanya tampil SEKALI — salin sekarang!
                  </div>
                  <div className="flex items-center gap-3">
                    <code className="flex-1 font-mono text-base text-accent-2 break-all leading-relaxed select-all font-bold">
                      {recovToken.token}
                    </code>
                    <CopyBtn text={recovToken.token}/>
                  </div>
                </div>

                <div className="text-xs text-ink-3 bg-bg-4 border border-border/30 rounded-2xl p-4 space-y-2 font-semibold shadow-sm">
                  <div className="flex items-center gap-2">📋 <strong className="text-ink-2 font-bold uppercase tracking-widest">Cara kirim ke user:</strong></div>
                  <div className="opacity-80">WhatsApp/Telegram: "Ini token reset password kamu: <code className="font-mono bg-bg-5 px-1.5 py-0.5 rounded text-accent-2">{recovToken.token}</code>"</div>
                  <div className="opacity-80">User buka login → <strong>Lupa Password?</strong> → <strong>Token Recovery</strong> → paste token</div>
                </div>
              </div>
            )}
          </div>
        </Card>
      )}

      {/* ── Login Logs (Admin) ── */}
      {isAdmin && (
        <Card title={t('login_history')} icon={LogIn} iconColor="text-sky-400" defaultOpen={false}
          badge={
            <button onClick={loadLogs} disabled={loadLog}
              className="text-xs text-ink-3 hover:text-ink flex items-center gap-2 mr-3 font-bold uppercase tracking-widest transition-all p-2 rounded-lg hover:bg-bg-3">
              <RefreshCw size={14} className={loadLog ? 'animate-spin' : ''}/>Refresh
            </button>
          }>
          {logs.length === 0 ? (
            <div className="text-center py-6 text-xs text-ink-3">Belum ada log login</div>
          ) : (
            <div className="overflow-x-auto custom-scrollbar">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b-2 border-border bg-bg-2/50">
                    <th className="text-left px-4 py-3 text-ink-3 font-bold uppercase tracking-widest opacity-60">Waktu</th>
                    <th className="text-left px-4 py-3 text-ink-3 font-bold uppercase tracking-widest opacity-60">Username</th>
                    <th className="text-center px-4 py-3 text-ink-3 font-bold uppercase tracking-widest opacity-60">Status</th>
                    <th className="text-left px-4 py-3 text-ink-3 font-bold uppercase tracking-widest opacity-60">Keterangan</th>
                    <th className="text-left px-4 py-3 text-ink-3 font-bold uppercase tracking-widest opacity-60">IP</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/50">
                  {logs.map(l => (
                    <tr key={l.id} className={clsx('hover:bg-bg-4/50 transition-colors', !l.success && 'bg-danger/5')}>
                      <td className="px-4 py-3 text-ink-3 font-bold font-mono whitespace-nowrap opacity-80">
                        {new Date(l.created_at).toLocaleString('id-ID', { dateStyle: 'short', timeStyle: 'short' })}
                      </td>
                      <td className="px-4 py-3 text-ink-2 font-bold uppercase tracking-tight">{l.username}</td>
                      <td className="px-4 py-3 text-center">
                        {l.success
                          ? <span className="inline-flex items-center gap-2 text-success font-bold uppercase tracking-widest border border-success/30 px-2 py-1 rounded-lg bg-success/10 shadow-sm"><CheckCircle2 size={14}/>OK</span>
                          : <span className="inline-flex items-center gap-2 text-danger font-bold uppercase tracking-widest border border-danger/30 px-2 py-1 rounded-lg bg-danger/10 shadow-sm"><XCircle size={14}/>Gagal</span>
                        }
                      </td>
                      <td className="px-4 py-3 text-ink-3 font-semibold opacity-70">{l.reason || (l.success ? 'Login berhasil' : '—')}</td>
                      <td className="px-4 py-3 text-ink-3 font-bold font-mono opacity-60">{l.ip || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {/* ── Checklist Keamanan ── */}
      <Card title={t('security_checklist')} icon={Shield} iconColor="text-success" defaultOpen={false}>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {[
            { label: 'Ganti SECRET_KEY dari default',              key: 'secret_key',  critical: true },
            { label: 'Ganti password admin dari admin',    key: 'admin_pass',  critical: true },
            { label: 'Gunakan password minimal 12 karakter',       key: 'pass_length', critical: true },
            { label: 'Aktifkan HTTPS via Cloudflare Tunnel',       key: 'https',       critical: true },
            { label: 'Jangan expose port 7860 ke internet',        key: 'port',        critical: false },
            { label: 'Backup file .env secara berkala',            key: 'env_backup',  critical: false },
            { label: 'Catat SECRET_KEY di tempat aman',            key: 'secret_note', critical: false },
            { label: 'Review login log secara berkala',            key: 'log_review',  critical: false },
            { label: 'Batasi pengguna Sub Admin sesuai kebutuhan', key: 'subadmin',    critical: false },
          ].map(item => (
            <label key={item.key} className="flex items-center gap-3 p-4 bg-bg-4 border-2 border-border/50 rounded-2xl cursor-pointer hover:border-accent/30 hover:bg-bg-5 transition-all shadow-sm group">
              <input type="checkbox" className="accent-accent w-5 h-5 flex-shrink-0 rounded-lg"/>
              <span className="text-sm text-ink-2 flex-1 font-bold uppercase tracking-tight opacity-80">{item.label}</span>
              {item.critical && (
                <span className="text-[10px] bg-danger/15 text-danger px-2.5 py-1 rounded-full font-bold uppercase tracking-widest border border-danger/30 shadow-sm">Wajib</span>
              )}
            </label>
          ))}
        </div>
        <p className="text-xs text-ink-3 mt-4 font-semibold uppercase tracking-widest opacity-60">
          Centang item yang sudah diselesaikan. Status checklist tidak tersimpan (hanya sebagai pengingat).
        </p>
      </Card>

    </div>
  )
}
