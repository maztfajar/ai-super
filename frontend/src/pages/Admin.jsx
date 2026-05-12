import { useState, useEffect } from 'react'
import { api } from '../hooks/useApi'
import { copyToClipboard } from "../utils/clipboard"
import { useAuthStore } from '../store'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import {
  Users, Plus, Trash2, RefreshCw, CheckCircle2, XCircle,
  Eye, EyeOff, ShieldAlert, Crown, UserCheck, Pencil, X, Save,
  Key, Copy, Check, Clock, AlertTriangle,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import clsx from 'clsx'

function Label({ children }) {
  return <label className="block text-[13px] text-ink-3 mb-1.5 uppercase tracking-wider font-semibold">{children}</label>
}
function Inp({ value, onChange, placeholder, disabled, mono }) {
  return <input type="text" value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} disabled={disabled}
    className={clsx('w-full bg-bg-2 border border-border-2 rounded-lg px-3 py-2 text-sm text-ink placeholder-ink-3 outline-none focus:border-accent disabled:opacity-50', mono && 'font-mono')}/>
}
function SecretInp({ value, onChange, placeholder }) {
  const [show, setShow] = useState(false)
  return (
    <div className="relative">
      <input type={show ? 'text' : 'password'} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
        className="w-full bg-bg-2 border border-border-2 rounded-lg px-3 py-2 pr-9 text-sm text-ink placeholder-ink-3 outline-none focus:border-accent font-mono"/>
      <button type="button" onClick={() => setShow(!show)} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-ink-3 hover:text-ink">
        {show ? <EyeOff size={13}/> : <Eye size={13}/>}
      </button>
    </div>
  )
}
function RoleBadge({ role }) {
  return role === 'admin' ? (
    <span className="flex items-center gap-1 text-xs font-semibold bg-accent/15 text-accent-2 px-2 py-0.5 rounded-full">
      <Crown size={9}/>Admin
    </span>
  ) : (
    <span className="flex items-center gap-1 text-xs font-medium bg-bg-4 text-ink-3 px-2 py-0.5 rounded-full border border-border">
      <UserCheck size={9}/>Sub Admin
    </span>
  )
}
function StatusDot({ active }) {
  const { t } = useTranslation()
  return active
    ? <span className="flex items-center gap-1 text-xs text-success"><span className="w-1.5 h-1.5 rounded-full bg-success"/>{t('active_label')}</span>
    : <span className="flex items-center gap-1 text-xs text-ink-3"><span className="w-1.5 h-1.5 rounded-full bg-ink-3"/>{t('inactive_label')}</span>
}

// ── Hak Akses per Role ────────────────────────────────────────
const ROLE_ACCESS = {
  admin: {
    label: 'Admin',
    icon: Crown,
    color: 'bg-accent/15 text-accent-2 border-accent/30',
    desc: 'Akses penuh ke semua fitur',
    pages: ['Dashboard', 'Chat', 'Models', 'Knowledge', 'Memory', 'Workflow', 'Integrasi', 'Analytics', 'Logs', 'Playground', 'Pengaturan', 'Profil', 'Admin'],
  },
  subadmin: {
    label: 'Sub Admin',
    icon: UserCheck,
    color: 'bg-bg-4 text-ink-3 border-border',
    desc: 'Akses terbatas: hanya Dashboard, Chat, Analytics',
    pages: ['Dashboard', 'Chat', 'Analytics'],
  },
}

// ── Form Tambah / Edit User ───────────────────────────────────
function UserForm({ editUser, onSave, onCancel, saving }) {
  const [username, setUsername] = useState(editUser?.username || '')
  const [email,    setEmail]    = useState(editUser?.email    || '')
  const [password, setPassword] = useState('')
  const [role,     setRole]     = useState(editUser?.role || 'subadmin')

  const handleSave = () => {
    if (!username.trim()) { toast.error('Username wajib diisi'); return }
    if (!editUser && !email.trim()) { toast.error('Email wajib diisi'); return }
    if (!editUser && !password.trim()) { toast.error('Password wajib diisi untuk user baru'); return }
    if (!editUser && password.length < 6) { toast.error('Password minimal 6 karakter'); return }
    onSave({ username: username.trim(), email: email.trim(), password, role })
  }

  return (
    <div className="bg-bg-4 border border-accent/25 rounded-xl p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-ink">{editUser ? '✏️ Edit Pengguna' : '➕ Tambah Pengguna Baru'}</span>
        <button onClick={onCancel} className="text-ink-3 hover:text-ink"><X size={14}/></button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div>
          <Label>Username *</Label>
          <Inp value={username} onChange={setUsername} placeholder="nama_pengguna"/>
        </div>
        <div>
          <Label>Email {editUser ? '(kosongkan = tidak ubah)' : '*'}</Label>
          <Inp value={email} onChange={setEmail} placeholder="email@domain.com" mono/>
        </div>
      </div>

      <div>
        <Label>Password {editUser ? '(kosongkan = tidak ubah)' : '*'}</Label>
        <SecretInp value={password} onChange={setPassword}
          placeholder={editUser ? 'kosongkan jika tidak ingin ganti' : 'min 6 karakter'}/>
      </div>

      {/* Role selector */}
      <div>
        <Label>Hak Akses</Label>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {Object.entries(ROLE_ACCESS).map(([k, v]) => {
            const Icon = v.icon
            return (
              <div key={k} onClick={() => setRole(k)}
                className={clsx('p-3 rounded-xl border-2 cursor-pointer transition-all',
                  role === k ? 'border-accent bg-accent/8' : 'border-border bg-bg-3 hover:border-border-2')}>
                <div className="flex items-center gap-2 mb-1">
                  <Icon size={13} className={role === k ? 'text-accent-2' : 'text-ink-3'}/>
                  <span className="text-sm font-semibold text-ink">{v.label}</span>
                </div>
                <div className="text-xs text-ink-3 mb-2">{v.desc}</div>
                <div className="flex flex-wrap gap-1">
                  {v.pages.map(p => (
                    <span key={p} className={clsx('text-[11px] px-1.5 py-0.5 rounded font-mono',
                      role === k ? 'bg-accent/15 text-accent-2' : 'bg-bg-5 text-ink-3')}>
                      {p}
                    </span>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      <div className="flex gap-2 pt-1">
        <button onClick={handleSave} disabled={saving}
          className="flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg bg-accent hover:bg-accent/80 text-white font-medium disabled:opacity-50">
          {saving ? <RefreshCw size={11} className="animate-spin"/> : <Save size={11}/>}
          {editUser ? t('update_user') : t('create_user')}
        </button>
        <button onClick={onCancel}
          className="px-3 py-2 text-sm rounded-lg bg-bg-4 hover:bg-bg-5 border border-border text-ink-2 hover:text-ink">
          {t('cancel')}
        </button>
      </div>
    </div>
  )
}

// ── Recovery Token Panel ──────────────────────────────────────
function RecoveryTokenPanel() {
  const [users,    setUsers]   = useState([])
  const [selUser,  setSelUser] = useState('')
  const [token,    setToken]   = useState(null)
  const [loading,  setLoad]    = useState(false)
  const [active,   setActive]  = useState([])
  const [copied,   setCopied]  = useState(false)
  const [countdown, setCount]  = useState(0)

  useEffect(() => {
    api.listUsers().then(u => setUsers(u)).catch(() => {})
    loadActive()
  }, [])

  useEffect(() => {
    if (countdown <= 0) return
    const t = setTimeout(() => setCount(c => c - 1), 1000)
    return () => clearTimeout(t)
  }, [countdown])

  const loadActive = async () => {
    try { setActive((await api.listRecoveryTokens()).tokens || []) } catch {}
  }

  const generate = async () => {
    setLoad(true)
    try {
      const r = await api.generateRecoveryToken(selUser || undefined)
      setToken(r)
      setCount(r.expires_in || 900)
      toast.success('Token dibuat! Salin dan kirim ke pengguna.')
      loadActive()
    } catch(e) { toast.error(e.message) }
    finally { setLoad(false) }
  }

  const copyToken = () => {
    if (!token?.token) return
    copyToClipboard(token.token)
    setCopied(true)
    setTimeout(() => setCopied(false), 3000)
    toast.success('Token disalin!')
  }

  const fmt = s => `${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}`

  return (
    <div className="bg-bg-3 border border-border rounded-xl overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-border">
        <Key size={14} className="text-warn"/>
        <span className="text-sm font-semibold text-ink">{t('recovery_token_title')}</span>
      </div>
      <div className="p-4 space-y-4">

        {/* Penjelasan */}
        <div className="flex items-start gap-2.5 p-3 bg-warn/8 border border-warn/20 rounded-xl text-[13px] text-ink-2">
          <AlertTriangle size={13} className="text-warn flex-shrink-0 mt-0.5"/>
          <div>
            <strong className="text-ink block mb-0.5">Cara kerja:</strong>
            Generate token → salin → kirim ke pengguna via WhatsApp/Telegram → 
            pengguna buka halaman login → tab "Lupa Password?" → pilih "Token Recovery" → paste token → set password baru.
            <span className="text-warn font-semibold block mt-1">Token berlaku 15 menit dan hanya bisa dipakai 1 kali.</span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Generate */}
          <div className="space-y-3">
            <div>
              <label className="block text-[12px] text-ink-3 mb-1.5 uppercase tracking-wider font-semibold">
                Generate Token Untuk
              </label>
              <select value={selUser} onChange={e => setSelUser(e.target.value)}
                className="w-full bg-bg-2 border border-border-2 rounded-lg px-3 py-2 text-sm text-ink outline-none focus:border-accent">
                <option value="">Akun saya sendiri (Admin)</option>
                {users.map(u => (
                  <option key={u.id} value={u.id}>{u.username} ({u.role})</option>
                ))}
              </select>
            </div>

            <button onClick={generate} disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-2.5 bg-warn/10 hover:bg-warn/20 border border-warn/30 text-warn text-sm font-semibold rounded-xl disabled:opacity-50 transition-colors">
              {loading ? <RefreshCw size={14} className="animate-spin"/> : <Key size={14}/>}
              {loading ? t('processing') : t('generate_recovery_token')}
            </button>
          </div>

          {/* Hasil token */}
          <div>
            {token ? (
              <div className="space-y-2.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 size={13} className="text-success"/>
                    <span className="text-xs font-semibold text-success">Token Siap!</span>
                  </div>
                  <div className={clsx('text-xs font-mono font-semibold px-2 py-1 rounded-lg',
                    countdown > 120 ? 'bg-success/15 text-success' : 'bg-danger/15 text-danger animate-pulse')}>
                    <Clock size={10} className="inline mr-1"/>
                    {fmt(countdown)}
                  </div>
                </div>

                <div className="relative bg-bg-2 border border-success/30 rounded-xl p-3">
                  <div className="text-xs text-ink-3 mb-1.5 flex items-center gap-1">
                    <AlertTriangle size={9} className="text-warn"/>
                    Hanya tampil sekali — salin sekarang!
                  </div>
                  <code className="text-sm font-mono text-success break-all leading-relaxed block pr-8">
                    {token.token}
                  </code>
                  <button onClick={copyToken}
                    className={clsx('absolute top-3 right-3 p-1.5 rounded-lg transition-all',
                      copied ? 'bg-success/20 text-success' : 'bg-bg-4 hover:bg-bg-5 text-ink-3 hover:text-ink')}>
                    {copied ? <Check size={12}/> : <Copy size={12}/>}
                  </button>
                </div>

                <div className="text-xs text-ink-3 bg-bg-4 rounded-xl p-2.5">
                  <div>👤 Untuk: <strong className="text-ink">{token.username}</strong></div>
                  <div className="mt-1">📋 Kirim token ini ke pengguna via WhatsApp atau Telegram</div>
                  <div className="mt-0.5">🔗 Pengguna: Login → "Lupa Password?" → "Token Recovery"</div>
                </div>
              </div>
            ) : (
              <div className="h-full flex items-center justify-center text-center p-6 border-2 border-dashed border-border rounded-xl">
                <div className="text-ink-3">
                  <Key size={20} className="mx-auto mb-2 opacity-40"/>
                  <div className="text-sm">Token akan muncul di sini setelah di-generate</div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Token aktif */}
        {active.length > 0 && (
          <div className="border-t border-border pt-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[13px] font-semibold text-ink-2">{t('active_tokens')} ({active.length})</span>
              <button onClick={loadActive} className="text-xs text-ink-3 hover:text-ink flex items-center gap-1">
                <RefreshCw size={9}/>Refresh
              </button>
            </div>
            <div className="space-y-1.5">
              {active.map((t, i) => (
                <div key={i} className={clsx('flex items-center gap-3 px-3 py-2 rounded-lg text-xs',
                  t.used ? 'bg-bg-4 opacity-50' : 'bg-success/5 border border-success/20')}>
                  <div className={clsx('w-1.5 h-1.5 rounded-full flex-shrink-0',
                    t.used ? 'bg-ink-3' : t.expires_in < 120 ? 'bg-warn animate-pulse' : 'bg-success')}/>
                  <span className="font-medium text-ink-2 flex-1">{t.username}</span>
                  <span className="text-ink-3">oleh {t.created_by}</span>
                  <span className={clsx('font-mono font-semibold',
                    t.used ? 'text-ink-3' : t.expires_in < 120 ? 'text-warn' : 'text-success')}>
                    {t.used ? 'Terpakai' : fmt(t.expires_in)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}


// ── Main Admin Page ───────────────────────────────────────────
export default function Admin() {
  const { t } = useTranslation()
  const { user } = useAuthStore()
  const navigate = useNavigate()
  const [users,   setUsers]   = useState([])
  const [loading, setLoad]    = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [editUser, setEditUser] = useState(null)
  const [saving,  setSaving]  = useState(false)
  const [deleting, setDeleting] = useState(null)
  const [confirmDelete, setConfirmDelete] = useState(null)

  // Guard: hanya admin
  useEffect(() => {
    if (!user?.is_admin) { navigate('/dashboard'); return }
    loadUsers()
  }, [])

  const loadUsers = async () => {
    setLoad(true)
    try { setUsers(await api.listUsers()) } catch {}
    finally { setLoad(false) }
  }

  const handleCreate = async (data) => {
    setSaving(true)
    try {
      await api.createUser(data)
      toast.success(`Pengguna "${data.username}" berhasil dibuat!`)
      setShowAdd(false)
      await loadUsers()
    } catch(e) { toast.error(e.message || 'Gagal membuat pengguna') }
    finally { setSaving(false) }
  }

  const handleUpdate = async (data) => {
    setSaving(true)
    try {
      const payload = { role: data.role }
      if (data.username !== editUser.username) payload.username = data.username
      if (data.password.trim()) payload.password = data.password
      await api.updateUser(editUser.id, payload)
      toast.success('Pengguna berhasil diperbarui')
      setEditUser(null)
      await loadUsers()
    } catch(e) { toast.error(e.message) }
    finally { setSaving(false) }
  }

  const handleToggleActive = async (u) => {
    try {
      await api.updateUser(u.id, { is_active: !u.is_active })
      toast.success(u.is_active ? `"${u.username}" dinonaktifkan` : `"${u.username}" diaktifkan`)
      await loadUsers()
    } catch(e) { toast.error(e.message) }
  }

  const handleDelete = async (u) => {
    setDeleting(u.id)
    try {
      await api.deleteUser(u.id)
      toast.success(`Pengguna "${u.username}" dihapus`)
      setConfirmDelete(null)
      await loadUsers()
    } catch(e) { toast.error(e.message) }
    finally { setDeleting(null) }
  }

  const currentUserId = user?.id

  return (
    <div className="p-4 md:p-6 w-full space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-semibold text-ink flex items-center gap-2">
            <Users size={18} className="text-accent-2"/>{t('admin_panel_title')}
          </h1>
          <p className="text-sm text-ink-3 mt-0.5">{t('user_management_desc')}</p>
        </div>
        <button onClick={() => { setShowAdd(!showAdd); setEditUser(null) }}
          className="flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg bg-accent hover:bg-accent/80 text-white font-medium transition-colors">
          <Plus size={12}/>{t('add_user')}
        </button>
      </div>

      {/* Hak Akses Info */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {Object.entries(ROLE_ACCESS).map(([k, v]) => {
          const Icon = v.icon
          const count = users.filter(u => (u.role === k) || (k === 'admin' && u.is_admin && !u.role)).length
          return (
            <div key={k} className={clsx('rounded-xl border p-3.5', v.color)}>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Icon size={14}/>
                  <span className="text-sm font-semibold">{v.label}</span>
                </div>
                <span className="text-xl font-semibold font-mono">{count}</span>
              </div>
              <div className="text-xs opacity-80 mb-2">{v.desc}</div>
              <div className="flex flex-wrap gap-1">
                {v.pages.map(p => (
                  <span key={p} className="text-[11px] bg-bg-2/50 px-1.5 py-0.5 rounded font-mono">{p}</span>
                ))}
              </div>
            </div>
          )
        })}
      </div>

      {/* Form tambah/edit */}
      {showAdd && !editUser && (
        <UserForm onSave={handleCreate} onCancel={() => setShowAdd(false)} saving={saving}/>
      )}
      {editUser && (
        <UserForm editUser={editUser} onSave={handleUpdate} onCancel={() => setEditUser(null)} saving={saving}/>
      )}

      {/* Tabel Pengguna */}
      <div className="bg-bg-3 border border-border rounded-xl overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-border">
          <span className="text-base font-semibold text-ink flex items-center gap-2">
            <Users size={14} className="text-ink-3"/>
            {t('user_list')}
            <span className="text-xs bg-bg-4 text-ink-3 px-2 py-0.5 rounded-full font-normal">{users.length} {t('accounts') || 'accounts'}</span>
          </span>
          <button onClick={loadUsers} disabled={loading}
            className="text-sm text-ink-3 hover:text-ink flex items-center gap-1 disabled:opacity-50">
            <RefreshCw size={11} className={loading ? 'animate-spin' : ''}/>{t('refresh_label')}
          </button>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-10 text-xs text-ink-3 gap-2">
            <RefreshCw size={13} className="animate-spin"/>Memuat pengguna...
          </div>
        ) : users.length === 0 ? (
          <div className="py-10 text-center text-xs text-ink-3">Belum ada pengguna</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left px-4 py-2.5 text-xs text-ink-3 uppercase tracking-wider font-semibold">Pengguna</th>
                  <th className="text-left px-3 py-2.5 text-xs text-ink-3 uppercase tracking-wider font-semibold">Email</th>
                  <th className="text-center px-3 py-2.5 text-xs text-ink-3 uppercase tracking-wider font-semibold">{t('access_rights')}</th>
                  <th className="text-center px-3 py-2.5 text-xs text-ink-3 uppercase tracking-wider font-semibold">Status</th>
                  <th className="text-center px-3 py-2.5 text-xs text-ink-3 uppercase tracking-wider font-semibold">{t('joined_label')}</th>
                  <th className="px-3 py-2.5"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {users.map(u => {
                  const isSelf = u.id === currentUserId
                  const role = u.role || (u.is_admin ? 'admin' : 'subadmin')
                  return (
                    <tr key={u.id} className={clsx('hover:bg-bg-4/50 transition-colors', !u.is_active && 'opacity-60')}>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2.5">
                          <div className={clsx('w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold flex-shrink-0',
                            role === 'admin' ? 'bg-accent/20 text-accent-2' : 'bg-bg-5 text-ink-3')}>
                            {u.username[0].toUpperCase()}
                          </div>
                          <div>
                            <div className="font-semibold text-ink flex items-center gap-1.5">
                              {u.username}
                              {isSelf && <span className="text-[11px] bg-success/15 text-success px-1.5 py-0.5 rounded font-semibold">Anda</span>}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-3 py-3 text-ink-3 font-mono text-sm">{u.email}</td>
                      <td className="px-3 py-3 text-center">
                        <RoleBadge role={role}/>
                      </td>
                      <td className="px-3 py-3 text-center">
                        <StatusDot active={u.is_active}/>
                      </td>
                      <td className="px-3 py-3 text-center text-ink-3">
                        {new Date(u.created_at).toLocaleDateString('id-ID', { dateStyle: 'short' })}
                      </td>
                      <td className="px-3 py-3">
                        {!isSelf && (
                          <div className="flex items-center gap-1 justify-end">
                            <button onClick={() => { setEditUser(u); setShowAdd(false) }}
                              className="p-1.5 rounded-lg text-ink-3 hover:text-accent-2 hover:bg-accent/10 transition-colors">
                              <Pencil size={12}/>
                            </button>
                            <button onClick={() => handleToggleActive(u)}
                              className={clsx('p-1.5 rounded-lg transition-colors',
                                u.is_active ? 'text-ink-3 hover:text-warn hover:bg-warn/10' : 'text-ink-3 hover:text-success hover:bg-success/10')}>
                              {u.is_active ? <XCircle size={12}/> : <CheckCircle2 size={12}/>}
                            </button>
                              {confirmDelete === u.id ? (
                                <div className="flex items-center gap-1">
                                  <button onClick={() => handleDelete(u)} disabled={deleting === u.id}
                                    className="px-2 py-1 text-xs bg-danger text-white rounded-lg font-medium disabled:opacity-50">
                                    {deleting === u.id ? '...' : 'Hapus'}
                                  </button>
                                  <button onClick={() => setConfirmDelete(null)}
                                    className="px-2 py-1 text-xs bg-bg-4 border border-border text-ink-2 rounded-lg">
                                    Batal
                                  </button>
                                </div>
                            ) : (
                              <button onClick={() => setConfirmDelete(u.id)}
                                className="p-1.5 rounded-lg text-ink-3 hover:text-danger hover:bg-danger/10 transition-colors">
                                <Trash2 size={12}/>
                              </button>
                            )}
                          </div>
                        )}
                        {isSelf && <span className="text-xs text-ink-3 px-2">—</span>}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── Recovery Token Panel ── */}
      <RecoveryTokenPanel/>

      {/* Info hak akses Sub Admin */}
      <div className="bg-bg-3 border border-border rounded-xl p-4">
        <div className="flex items-center gap-2 mb-3">
          <ShieldAlert size={14} className="text-warn"/>
          <span className="text-sm font-semibold text-ink">{t('access_summary')}</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-2 pr-4 text-ink-3 font-semibold">Menu / Fitur</th>
                <th className="text-center py-2 px-3 text-accent-2 font-semibold">👑 Admin</th>
                <th className="text-center py-2 px-3 text-ink-3 font-semibold">👤 Sub Admin</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/50">
              {[
                ['Dashboard',    true,  true],
                ['Chat',         true,  true],
                ['Analytics',    true,  true],
                ['Models',       true,  false],
                ['Knowledge',    true,  false],
                ['Memory',       true,  false],
                ['Workflow',     true,  false],
                ['Integrasi',    true,  false],
                ['Logs',         true,  false],
                ['Playground',   true,  false],
                ['Pengaturan',   true,  false],
                ['Profil',       true,  true],
                ['Panel Admin',  true,  false],
              ].map(([name, admin, sub]) => (
                <tr key={name} className="hover:bg-bg-4/30">
                  <td className="py-1.5 pr-4 text-ink-2 font-semibold">{name}</td>
                  <td className="py-1.5 px-3 text-center">{admin ? <CheckCircle2 size={12} className="text-success mx-auto"/> : <XCircle size={12} className="text-danger/40 mx-auto"/>}</td>
                  <td className="py-1.5 px-3 text-center">{sub ? <CheckCircle2 size={12} className="text-success mx-auto"/> : <XCircle size={12} className="text-danger/40 mx-auto"/>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
