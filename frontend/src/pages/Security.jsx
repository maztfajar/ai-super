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
import clsx from 'clsx'

// ── Primitive ─────────────────────────────────────────────────
function Label({ children }) {
  return <label className="block text-[10px] text-ink-3 mb-1.5 uppercase tracking-wider font-medium">{children}</label>
}
function SecretInp({ value, onChange, placeholder, disabled }) {
  const [show, setShow] = useState(false)
  return (
    <div className="relative">
      <input type={show ? 'text' : 'password'} value={value} onChange={e => onChange(e.target.value)}
        placeholder={placeholder} disabled={disabled} autoComplete="new-password"
        className="w-full bg-bg-2 border border-border-2 rounded-lg px-3 py-2 pr-9 text-xs text-ink placeholder-ink-3 outline-none focus:border-accent font-mono disabled:opacity-50"/>
      <button type="button" onClick={() => setShow(!show)} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-ink-3 hover:text-ink">
        {show ? <EyeOff size={13}/> : <Eye size={13}/>}
      </button>
    </div>
  )
}
function Btn({ label, onClick, loading, variant = 'primary', icon: Icon, disabled, full }) {
  return (
    <button onClick={onClick} disabled={loading || disabled}
      className={clsx('flex items-center justify-center gap-1.5 px-3 py-2 text-xs rounded-lg font-medium transition-all disabled:opacity-50',
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
function Card({ title, icon: Icon, iconColor = 'text-accent-2', children, badge, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="bg-bg-3 border border-border rounded-xl overflow-hidden">
      <button onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2.5 px-4 py-3 border-b border-border hover:bg-bg-4/50 transition-colors">
        <Icon size={14} className={iconColor}/>
        <span className="text-sm font-semibold text-ink flex-1 text-left">{title}</span>
        {badge}
        {open ? <ChevronUp size={13} className="text-ink-3"/> : <ChevronDown size={13} className="text-ink-3"/>}
      </button>
      {open && <div className="p-4">{children}</div>}
    </div>
  )
}
function CopyBtn({ text }) {
  const [ok, setOk] = useState(false)
  return (
    <button onClick={() => { copyToClipboard(text); setOk(true); setTimeout(() => setOk(false), 2000) }}
      className="p-1.5 rounded hover:bg-bg-5 text-ink-3 hover:text-ink transition-colors flex-shrink-0">
      {ok ? <Check size={12} className="text-success"/> : <Copy size={12}/>}
    </button>
  )
}
function CodeLine({ cmd }) {
  return (
    <div className="flex items-center gap-2 bg-bg-2 border border-border rounded-lg px-3 py-2 font-mono text-[11px]">
      <span className="text-accent-2 flex-1">{cmd}</span>
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
      <div className="text-[10px] text-ink-3">Kekuatan: <span className={clsx('font-semibold',
        score <= 1 ? 'text-danger' : score <= 3 ? 'text-warn' : 'text-success')}>{label}</span></div>
      <div className="grid grid-cols-2 gap-1">
        {checks.map(c => (
          <div key={c.label} className={clsx('flex items-center gap-1 text-[9px]', c.ok ? 'text-success' : 'text-ink-3')}>
            {c.ok ? <CheckCircle2 size={9}/> : <XCircle size={9}/>}{c.label}
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────
export default function Security() {
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
      <div>
        <h1 className="text-lg font-bold text-ink flex items-center gap-2">
          <Shield size={18} className="text-accent-2"/>Keamanan Akun
        </h1>
        <p className="text-xs text-ink-3 mt-0.5">Kelola password, recovery, dan pantau aktivitas login</p>
      </div>

      {/* ── Security Status ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { icon: Lock, label: 'Brute Force', value: 'Aktif', sub: 'Blokir 5 gagal', ok: true, color: 'text-success', bg: 'bg-success/10' },
          { icon: Clock, label: 'Session JWT', value: '7 Hari', sub: 'Auto-expire', ok: true, color: 'text-accent-2', bg: 'bg-accent/10' },
          { icon: FileKey, label: 'Recovery Token', value: '1 Jam', sub: 'One-time use', ok: true, color: 'text-warn', bg: 'bg-warn/10' },
          { icon: LogIn, label: 'Login Log', value: logs.length + ' entri', sub: 'Tersimpan DB', ok: true, color: 'text-sky-400', bg: 'bg-sky-400/10' },
        ].map(s => (
          <div key={s.label} className="bg-bg-3 border border-border rounded-xl p-3.5">
            <div className={clsx('w-7 h-7 rounded-lg flex items-center justify-center mb-2', s.bg)}>
              <s.icon size={13} className={s.color}/>
            </div>
            <div className="text-sm font-bold text-ink">{s.value}</div>
            <div className="text-[10px] text-ink-2 font-medium">{s.label}</div>
            <div className="text-[9px] text-ink-3">{s.sub}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">

        {/* ── Ganti Password ── */}
        <Card title="Ganti Password" icon={Key} iconColor="text-accent-2">
          <div className="space-y-3">
            <div>
              <Label>Password Saat Ini</Label>
              <SecretInp value={curPass} onChange={setCurPass} placeholder="password lama..."/>
            </div>
            <div>
              <Label>Password Baru</Label>
              <SecretInp value={newPass} onChange={setNewPass} placeholder="password baru..."/>
              <PasswordStrength password={newPass}/>
            </div>
            {newPass && (
              <div>
                <Label>Konfirmasi Password Baru</Label>
                <SecretInp value={confPass} onChange={setConfPass} placeholder="ketik ulang..."/>
                {confPass && newPass !== confPass && (
                  <p className="text-[10px] text-danger mt-1">⚠ Password tidak cocok</p>
                )}
              </div>
            )}
            <Btn label="Ubah Password" onClick={handleChangePass}
              loading={savingPw} icon={Key} full
              disabled={!curPass || !newPass || newPass !== confPass}/>

            {/* Tips password */}
            <div className="bg-bg-4 rounded-xl p-3 text-[10px] text-ink-3 space-y-1">
              <div className="text-ink-2 font-semibold mb-1.5">💡 Tips password kuat:</div>
              <div>• Minimal 12 karakter, campuran huruf besar/kecil, angka, simbol</div>
              <div>• Jangan gunakan nama, tanggal lahir, atau kata umum</div>
              <div>• Gunakan password manager (Bitwarden, 1Password, dll)</div>
              <div>• Ganti password secara berkala setiap 3-6 bulan</div>
            </div>
          </div>
        </Card>

        {/* ── Ide Keamanan Mendatang ── */}
        <Card title="Fitur Keamanan Mendatang" icon={Shield} iconColor="text-warn"
          badge={<span className="text-[9px] bg-warn/15 text-warn px-2 py-0.5 rounded-full font-medium">Roadmap</span>}>
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
              <div key={f.title} className="bg-bg-4 border border-border rounded-xl p-3">
                <div className="flex items-start gap-2.5">
                  <span className="text-xl flex-shrink-0">{f.icon}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs font-semibold text-ink">{f.title}</span>
                      <span className={clsx('text-[9px] px-1.5 py-0.5 rounded-full font-medium',
                        f.status === 'soon' ? 'bg-accent/15 text-accent-2' : 'bg-bg-5 text-ink-3')}>
                        {f.status === 'soon' ? '🚀 Segera' : '🔮 Masa Depan'}
                      </span>
                    </div>
                    <div className="text-[10px] text-ink-3 mt-0.5">{f.desc}</div>
                    <div className="text-[10px] text-ink-2 mt-1 flex items-center gap-1">
                      <Info size={9} className="text-accent-2 flex-shrink-0"/>
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
        <Card title="🔑 Generate Token Recovery" icon={FileKey} iconColor="text-warn"
          badge={<span className="text-[9px] bg-warn/15 text-warn px-2 py-0.5 rounded-full font-medium">Admin Only</span>}
          defaultOpen={false}>
          <div className="space-y-4">

            {/* Info */}
            <div className="flex items-start gap-2.5 p-3 bg-accent/8 border border-accent/20 rounded-xl text-[10px] text-ink-2">
              <Info size={12} className="text-accent-2 flex-shrink-0 mt-0.5"/>
              <div>
                <strong className="text-ink block mb-0.5">Cara pakai Token Recovery:</strong>
                Admin generate token → kirim ke user yang lupa password →
                user paste token di halaman login (tab "Lupa Password?" → Token Recovery).
                Token berlaku <strong>15 menit</strong> dan hanya bisa dipakai <strong>1 kali</strong>.
              </div>
            </div>

            {/* Pilih target user */}
            <div>
              <Label>Generate Token untuk:</Label>
              <select value={genTargetId} onChange={e => setGenTargetId(e.target.value)}
                className="w-full bg-bg-2 border border-border-2 rounded-lg px-3 py-2 text-xs text-ink outline-none focus:border-accent">
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
              <div className="bg-success/8 border-2 border-success/40 rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 size={14} className="text-success"/>
                    <span className="text-sm font-semibold text-success">Token Dibuat!</span>
                    <span className="text-[10px] text-ink-3">untuk: <strong className="text-ink">{recovToken.username}</strong></span>
                  </div>
                  <div className={clsx('text-xs font-mono font-bold px-2 py-1 rounded-lg',
                    countdown > 120 ? 'bg-success/15 text-success' : 'bg-danger/15 text-danger animate-pulse')}>
                    ⏱ {fmtCountdown(countdown)}
                  </div>
                </div>

                <div className="bg-bg-2 border border-border rounded-xl p-3">
                  <div className="text-[10px] text-warn mb-1.5 flex items-center gap-1">
                    <AlertTriangle size={10}/>Token hanya tampil SEKALI — salin sekarang!
                  </div>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 font-mono text-sm text-accent-2 break-all leading-relaxed select-all">
                      {recovToken.token}
                    </code>
                    <CopyBtn text={recovToken.token}/>
                  </div>
                </div>

                <div className="text-[10px] text-ink-3 bg-bg-4 rounded-xl p-2.5 space-y-1">
                  <div>📋 <strong className="text-ink-2">Cara kirim ke user:</strong></div>
                  <div>WhatsApp/Telegram: "Ini token reset password kamu: <code className="font-mono">{recovToken.token}</code>"</div>
                  <div>User buka login → <strong>Lupa Password?</strong> → <strong>Token Recovery</strong> → paste token</div>
                </div>
              </div>
            )}
          </div>
        </Card>
      )}

      {/* ── Login Logs (Admin) ── */}
      {isAdmin && (
        <Card title="Riwayat Login" icon={LogIn} iconColor="text-sky-400" defaultOpen={false}
          badge={
            <button onClick={loadLogs} disabled={loadLog}
              className="text-[10px] text-ink-3 hover:text-ink flex items-center gap-1 mr-2">
              <RefreshCw size={10} className={loadLog ? 'animate-spin' : ''}/>Refresh
            </button>
          }>
          {logs.length === 0 ? (
            <div className="text-center py-6 text-xs text-ink-3">Belum ada log login</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-[10px]">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left px-2 py-2 text-ink-3 font-medium">Waktu</th>
                    <th className="text-left px-2 py-2 text-ink-3 font-medium">Username</th>
                    <th className="text-center px-2 py-2 text-ink-3 font-medium">Status</th>
                    <th className="text-left px-2 py-2 text-ink-3 font-medium">Keterangan</th>
                    <th className="text-left px-2 py-2 text-ink-3 font-medium">IP</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/50">
                  {logs.map(l => (
                    <tr key={l.id} className={clsx('hover:bg-bg-4/50', !l.success && 'bg-danger/3')}>
                      <td className="px-2 py-2 text-ink-3 font-mono whitespace-nowrap">
                        {new Date(l.created_at).toLocaleString('id-ID', { dateStyle: 'short', timeStyle: 'short' })}
                      </td>
                      <td className="px-2 py-2 text-ink-2 font-medium">{l.username}</td>
                      <td className="px-2 py-2 text-center">
                        {l.success
                          ? <span className="inline-flex items-center gap-1 text-success"><CheckCircle2 size={11}/>OK</span>
                          : <span className="inline-flex items-center gap-1 text-danger"><XCircle size={11}/>Gagal</span>
                        }
                      </td>
                      <td className="px-2 py-2 text-ink-3">{l.reason || (l.success ? 'Login berhasil' : '—')}</td>
                      <td className="px-2 py-2 text-ink-3 font-mono">{l.ip || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {/* ── Checklist Keamanan ── */}
      <Card title="Checklist Keamanan" icon={Shield} iconColor="text-success" defaultOpen={false}>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
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
            <label key={item.key} className="flex items-center gap-2.5 p-2.5 bg-bg-4 rounded-xl border border-border cursor-pointer hover:border-border-2 transition-colors group">
              <input type="checkbox" className="accent-accent w-3.5 h-3.5 flex-shrink-0"/>
              <span className="text-[11px] text-ink-2 flex-1">{item.label}</span>
              {item.critical && (
                <span className="text-[9px] bg-danger/15 text-danger px-1.5 py-0.5 rounded font-medium flex-shrink-0">Wajib</span>
              )}
            </label>
          ))}
        </div>
        <p className="text-[10px] text-ink-3 mt-3">
          Centang item yang sudah diselesaikan. Status checklist tidak tersimpan (hanya sebagai pengingat).
        </p>
      </Card>

    </div>
  )
}
