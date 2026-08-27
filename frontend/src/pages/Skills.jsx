import { useState, useEffect, useRef } from 'react'
import { api } from '../hooks/useApi'
import toast from 'react-hot-toast'
import {
  Zap, Plus, Upload, Download, Search, Trash2, Edit3, X, Save,
  ChevronDown, Tag, BookOpen, BarChart3, Sparkles, FileText,
  CheckCircle2, AlertCircle, RefreshCw, Star, Hash, List,
  ArrowUpRight, MoreVertical
} from 'lucide-react'

// ── Konstanta ─────────────────────────────────────────────────────────────────

const CATEGORIES = [
  { value: 'general',        label: 'General',        color: '#6b7280' },
  { value: 'coding',         label: 'Coding',         color: '#3b82f6' },
  { value: 'system',         label: 'System',         color: '#f59e0b' },
  { value: 'analysis',       label: 'Analysis',       color: '#8b5cf6' },
  { value: 'writing',        label: 'Writing',        color: '#10b981' },
  { value: 'file_operation', label: 'File Operation', color: '#f43f5e' },
]

const CAT_MAP = Object.fromEntries(CATEGORIES.map(c => [c.value, c]))

// ── Helper Components ─────────────────────────────────────────────────────────

function CategoryBadge({ category }) {
  const cat = CAT_MAP[category] || CAT_MAP.general
  return (
    <span style={{
      background: cat.color + '22',
      color: cat.color,
      border: `1px solid ${cat.color}44`,
      borderRadius: 8,
      padding: '2px 10px',
      fontSize: 11,
      fontWeight: 700,
      letterSpacing: '0.04em',
      textTransform: 'uppercase',
    }}>
      {cat.label}
    </span>
  )
}

function StatCard({ icon: Icon, label, value, color = 'var(--accent-2)' }) {
  return (
    <div style={{
      background: 'var(--bg-3)',
      border: '1px solid var(--border-2)',
      borderRadius: 16,
      padding: '20px 24px',
      display: 'flex',
      alignItems: 'center',
      gap: 16,
      flex: 1,
      minWidth: 140,
    }}>
      <div style={{
        width: 44, height: 44, borderRadius: 12,
        background: color + '18',
        border: `1px solid ${color}33`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        color, flexShrink: 0,
      }}>
        <Icon size={20} />
      </div>
      <div>
        <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--ink)', lineHeight: 1.1 }}>{value ?? '—'}</div>
        <div style={{ fontSize: 11, color: 'var(--ink-3)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', marginTop: 2 }}>{label}</div>
      </div>
    </div>
  )
}

// ── Skill Form Modal ──────────────────────────────────────────────────────────

function SkillModal({ skill, onClose, onSaved }) {
  const isEdit = !!skill?.id
  const [form, setForm] = useState({
    name: skill?.name || '',
    description: skill?.description || '',
    category: skill?.category || 'general',
    tags: (skill?.tags || []).join(', '),
    trigger_keywords: (skill?.trigger_keywords || []).join(', '),
    steps: (skill?.steps || []).join('\n'),
    examples: (skill?.examples || []).join('\n'),
    content: skill?.content || '',
  })
  const [saving, setSaving] = useState(false)
  const [activeTab, setActiveTab] = useState('basic')

  const handleSave = async () => {
    if (!form.name.trim()) { toast.error('Nama skill wajib diisi'); return }
    setSaving(true)
    try {
      const payload = {
        name: form.name.trim(),
        description: form.description.trim(),
        category: form.category,
        tags: form.tags.split(',').map(t => t.trim()).filter(Boolean),
        trigger_keywords: form.trigger_keywords.split(',').map(t => t.trim()).filter(Boolean),
        steps: form.steps.split('\n').map(s => s.trim()).filter(Boolean),
        examples: form.examples.split('\n').map(s => s.trim()).filter(Boolean),
        content: form.content.trim(),
      }
      if (isEdit) {
        await api.updateSkill(skill.id, payload)
        toast.success('Skill diupdate')
      } else {
        await api.createSkill(payload)
        toast.success('Skill berhasil dibuat!')
      }
      onSaved()
      onClose()
    } catch (e) {
      toast.error(e.message || 'Gagal menyimpan skill')
    } finally {
      setSaving(false)
    }
  }

  const tabs = [
    { id: 'basic', label: 'Dasar', icon: BookOpen },
    { id: 'steps', label: 'Langkah-langkah', icon: List },
    { id: 'advanced', label: 'Lanjutan', icon: Sparkles },
  ]

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 9999,
      background: 'rgba(0,0,0,0.7)',
      backdropFilter: 'blur(6px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '20px',
    }} onClick={onClose}>
      <div style={{
        background: 'var(--bg-2)',
        border: '1px solid var(--border-2)',
        borderRadius: 24,
        width: '100%', maxWidth: 680,
        maxHeight: '90vh',
        overflow: 'hidden',
        display: 'flex', flexDirection: 'column',
        boxShadow: '0 30px 80px rgba(0,0,0,0.5)',
      }} onClick={e => e.stopPropagation()}>

        {/* Header */}
        <div style={{
          padding: '24px 28px 0',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{
              width: 40, height: 40, borderRadius: 12,
              background: 'linear-gradient(135deg, var(--accent), var(--accent-2))',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Zap size={18} color="white" />
            </div>
            <div>
              <div style={{ fontWeight: 800, fontSize: 18, color: 'var(--ink)' }}>
                {isEdit ? 'Edit Skill' : 'Tambah Skill Baru'}
              </div>
              <div style={{ fontSize: 12, color: 'var(--ink-3)', marginTop: 1 }}>
                {isEdit ? `ID: ${skill.id}` : 'Definisikan kemampuan baru untuk AI'}
              </div>
            </div>
          </div>
          <button onClick={onClose} style={{
            width: 36, height: 36, borderRadius: 10, border: '1px solid var(--border-2)',
            background: 'var(--bg-3)', color: 'var(--ink-2)', cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}><X size={16} /></button>
        </div>

        {/* Tabs */}
        <div style={{ padding: '16px 28px 0', display: 'flex', gap: 4, flexShrink: 0 }}>
          {tabs.map(tab => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)} style={{
              display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px',
              borderRadius: 10, border: 'none', cursor: 'pointer', fontSize: 12.5, fontWeight: 700,
              background: activeTab === tab.id ? 'var(--accent)/12' : 'transparent',
              backgroundColor: activeTab === tab.id ? 'rgba(var(--accent-rgb,100,200,255),0.12)' : 'transparent',
              color: activeTab === tab.id ? 'var(--accent-2)' : 'var(--ink-3)',
              borderBottom: activeTab === tab.id ? '2px solid var(--accent-2)' : '2px solid transparent',
              transition: 'all 0.2s',
            }}>
              <tab.icon size={14} />{tab.label}
            </button>
          ))}
        </div>

        {/* Form Body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px 28px' }}>
          {activeTab === 'basic' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div>
                <label style={labelStyle}>Nama Skill *</label>
                <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  placeholder="cth: Deploy Aplikasi Node.js ke VPS"
                  style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Deskripsi</label>
                <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                  placeholder="Jelaskan apa yang dilakukan skill ini secara singkat..."
                  rows={3} style={{ ...inputStyle, resize: 'vertical', lineHeight: 1.5 }} />
              </div>
              <div>
                <label style={labelStyle}>Kategori</label>
                <select value={form.category} onChange={e => setForm(f => ({ ...f, category: e.target.value }))}
                  style={inputStyle}>
                  {CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
                </select>
              </div>
              <div>
                <label style={labelStyle}>Tags <span style={{ color: 'var(--ink-3)', fontWeight: 400 }}>(pisahkan dengan koma)</span></label>
                <input value={form.tags} onChange={e => setForm(f => ({ ...f, tags: e.target.value }))}
                  placeholder="deploy, nodejs, vps, nginx"
                  style={inputStyle} />
              </div>
              <div>
                <label style={labelStyle}>Trigger Keywords <span style={{ color: 'var(--ink-3)', fontWeight: 400 }}>(pisahkan dengan koma)</span></label>
                <input value={form.trigger_keywords} onChange={e => setForm(f => ({ ...f, trigger_keywords: e.target.value }))}
                  placeholder="deploy, setup server, install nginx"
                  style={inputStyle} />
                <div style={{ fontSize: 11, color: 'var(--ink-3)', marginTop: 4 }}>
                  Kata kunci yang akan memicu AI untuk menggunakan skill ini
                </div>
              </div>
            </div>
          )}

          {activeTab === 'steps' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div>
                <label style={labelStyle}>Langkah-langkah Prosedural</label>
                <textarea value={form.steps} onChange={e => setForm(f => ({ ...f, steps: e.target.value }))}
                  placeholder={"Tuliskan setiap langkah di baris baru:\nCek koneksi SSH ke server\nInstall dependencies dengan npm install\nBuild aplikasi dengan npm run build\n..."}
                  rows={10} style={{ ...inputStyle, resize: 'vertical', fontFamily: 'monospace', fontSize: 13, lineHeight: 1.6 }} />
                <div style={{ fontSize: 11, color: 'var(--ink-3)', marginTop: 4 }}>
                  Satu langkah per baris. Akan dikonversi ke daftar bernomor.
                </div>
              </div>
              <div>
                <label style={labelStyle}>Contoh Penggunaan</label>
                <textarea value={form.examples} onChange={e => setForm(f => ({ ...f, examples: e.target.value }))}
                  placeholder={"Satu contoh per baris:\n\"Deploy aplikasi express.js ke VPS Ubuntu\"\n\"Setup nginx sebagai reverse proxy\""}
                  rows={5} style={{ ...inputStyle, resize: 'vertical', lineHeight: 1.6 }} />
              </div>
            </div>
          )}

          {activeTab === 'advanced' && (
            <div>
              <label style={labelStyle}>Catatan Tambahan (Markdown)</label>
              <textarea value={form.content} onChange={e => setForm(f => ({ ...f, content: e.target.value }))}
                placeholder="Tambahkan catatan, peringatan, atau konteks tambahan dalam format Markdown..."
                rows={12} style={{ ...inputStyle, resize: 'vertical', fontFamily: 'monospace', fontSize: 13, lineHeight: 1.6 }} />
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{
          padding: '16px 28px 24px',
          borderTop: '1px solid var(--border-2)',
          display: 'flex', justifyContent: 'flex-end', gap: 10, flexShrink: 0,
          background: 'var(--bg-2)',
        }}>
          <button onClick={onClose} style={{
            padding: '10px 24px', borderRadius: 12, border: '1px solid var(--border-2)',
            background: 'transparent', color: 'var(--ink-2)', cursor: 'pointer', fontWeight: 600, fontSize: 13,
          }}>Batal</button>
          <button onClick={handleSave} disabled={saving} style={{
            padding: '10px 28px', borderRadius: 12, border: 'none',
            background: 'linear-gradient(135deg, var(--accent), var(--accent-2))',
            color: 'white', cursor: 'pointer', fontWeight: 700, fontSize: 13,
            display: 'flex', alignItems: 'center', gap: 8,
            opacity: saving ? 0.7 : 1,
          }}>
            {saving ? <><RefreshCw size={14} style={{ animation: 'spin 1s linear infinite' }} />Menyimpan...</> : <><Save size={14} />Simpan Skill</>}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Skill Card ────────────────────────────────────────────────────────────────

function SkillCard({ skill, onEdit, onDelete }) {
  const [showMenu, setShowMenu] = useState(false)
  const menuRef = useRef()

  useEffect(() => {
    const close = (e) => { if (menuRef.current && !menuRef.current.contains(e.target)) setShowMenu(false) }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  return (
    <div style={{
      background: 'var(--bg-2)',
      border: '1px solid var(--border-2)',
      borderRadius: 18,
      padding: '20px',
      display: 'flex',
      flexDirection: 'column',
      gap: 12,
      transition: 'all 0.2s',
      cursor: 'pointer',
      position: 'relative',
    }}
      onMouseEnter={e => {
        e.currentTarget.style.borderColor = 'var(--accent-2)'
        e.currentTarget.style.boxShadow = '0 8px 30px rgba(100,200,255,0.08)'
        e.currentTarget.style.transform = 'translateY(-2px)'
      }}
      onMouseLeave={e => {
        e.currentTarget.style.borderColor = 'var(--border-2)'
        e.currentTarget.style.boxShadow = 'none'
        e.currentTarget.style.transform = 'none'
      }}
    >
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <span style={{ fontWeight: 800, fontSize: 15, color: 'var(--ink)', lineHeight: 1.3 }}>{skill.name}</span>
            <CategoryBadge category={skill.category} />
          </div>
          {skill.description && (
            <div style={{ fontSize: 12.5, color: 'var(--ink-3)', marginTop: 4, lineHeight: 1.5, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
              {skill.description}
            </div>
          )}
        </div>
        {/* Menu */}
        <div ref={menuRef} style={{ position: 'relative', flexShrink: 0 }}>
          <button onClick={e => { e.stopPropagation(); setShowMenu(v => !v) }} style={{
            width: 30, height: 30, borderRadius: 8, border: '1px solid var(--border-2)',
            background: 'var(--bg-3)', color: 'var(--ink-2)', cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}><MoreVertical size={14} /></button>
          {showMenu && (
            <div style={{
              position: 'absolute', right: 0, top: 34, zIndex: 100,
              background: 'var(--bg-3)', border: '1px solid var(--border-2)',
              borderRadius: 12, boxShadow: '0 8px 24px rgba(0,0,0,0.3)',
              minWidth: 130, overflow: 'hidden',
            }}>
              <button onClick={() => { setShowMenu(false); onEdit(skill) }} style={menuItemStyle}>
                <Edit3 size={13} />Edit
              </button>
              <button onClick={() => { setShowMenu(false); onDelete(skill) }} style={{ ...menuItemStyle, color: 'var(--danger)' }}>
                <Trash2 size={13} />Hapus
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Tags */}
      {skill.tags?.length > 0 && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
          {skill.tags.slice(0, 5).map(tag => (
            <span key={tag} style={{
              background: 'var(--bg-4)', color: 'var(--ink-2)',
              borderRadius: 6, padding: '2px 8px', fontSize: 10.5, fontWeight: 600,
              display: 'flex', alignItems: 'center', gap: 3,
            }}>
              <Hash size={9} />{tag}
            </span>
          ))}
          {skill.tags.length > 5 && <span style={{ fontSize: 10.5, color: 'var(--ink-3)', padding: '2px 4px' }}>+{skill.tags.length - 5}</span>}
        </div>
      )}

      {/* Steps count + stats */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, fontSize: 11.5, color: 'var(--ink-3)', marginTop: 'auto', paddingTop: 4, borderTop: '1px solid var(--border-2)' }}>
        {skill.steps?.length > 0 && (
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <List size={12} />{skill.steps.length} langkah
          </span>
        )}
        {skill.use_count > 0 && (
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <Star size={12} />dipakai {skill.use_count}×
          </span>
        )}
        <span style={{ display: 'flex', alignItems: 'center', gap: 4, marginLeft: 'auto' }}>
          ID: <code style={{ fontFamily: 'monospace', background: 'var(--bg-4)', padding: '1px 5px', borderRadius: 4 }}>{skill.id}</code>
        </span>
      </div>
    </div>
  )
}

// ── Styles ────────────────────────────────────────────────────────────────────

const inputStyle = {
  width: '100%', padding: '10px 14px', borderRadius: 10, outline: 'none',
  border: '1px solid var(--border-2)', background: 'var(--bg-3)',
  color: 'var(--ink)', fontSize: 13.5, boxSizing: 'border-box',
  transition: 'border-color 0.2s',
}

const labelStyle = {
  display: 'block', fontSize: 12, fontWeight: 700, color: 'var(--ink-2)',
  textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6,
}

const menuItemStyle = {
  display: 'flex', alignItems: 'center', gap: 8,
  width: '100%', padding: '10px 14px', border: 'none',
  background: 'transparent', color: 'var(--ink)', cursor: 'pointer',
  fontSize: 12.5, fontWeight: 600, textAlign: 'left',
  transition: 'background 0.15s',
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function Skills() {
  const [skills, setSkills] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filterCat, setFilterCat] = useState('')
  const [modal, setModal] = useState(null) // null | { mode: 'create' | 'edit', skill? }
  const [importing, setImporting] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState(null)
  const importJsonRef = useRef()
  const importMdRef = useRef()

  const load = async () => {
    setLoading(true)
    try {
      const [r, s] = await Promise.all([
        api.listSkills({ search, category: filterCat }),
        api.skillStats().catch(() => null),
      ])
      setSkills(r.skills || [])
      setStats(s)
    } catch (e) {
      toast.error('Gagal memuat skill')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [search, filterCat])

  const handleDelete = async (skill) => {
    try {
      await api.deleteSkill(skill.id)
      toast.success(`Skill "${skill.name}" dihapus`)
      setDeleteConfirm(null)
      load()
    } catch (e) {
      toast.error(e.message)
    }
  }

  const handleImportJson = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setImporting(true)
    try {
      const r = await api.importSkillsJson(file)
      toast.success(`${r.imported} skill diimport dari JSON`)
      load()
    } catch (e) {
      toast.error(e.message)
    } finally {
      setImporting(false)
      e.target.value = ''
    }
  }

  const handleImportMd = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setImporting(true)
    try {
      const r = await api.importSkillsMarkdown(file)
      toast.success(`${r.imported} skill diimport dari Markdown`)
      load()
    } catch (e) {
      toast.error(e.message)
    } finally {
      setImporting(false)
      e.target.value = ''
    }
  }

  const handleExport = async (fmt) => {
    setExporting(true)
    try {
      if (fmt === 'json') await api.exportSkillsJson()
      else await api.exportSkillsMarkdown()
      toast.success(`Skill diekspor sebagai ${fmt.toUpperCase()}`)
    } catch (e) {
      toast.error(e.message)
    } finally {
      setExporting(false)
    }
  }

  return (
    <div style={{
      minHeight: '100%',
      background: 'var(--bg)',
      padding: '32px 36px',
      fontFamily: 'Inter, system-ui, sans-serif',
    }}>
      {/* Hidden file inputs */}
      <input ref={importJsonRef} type="file" accept=".json" style={{ display: 'none' }} onChange={handleImportJson} />
      <input ref={importMdRef} type="file" accept=".md,.markdown" style={{ display: 'none' }} onChange={handleImportMd} />

      {/* Page Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 28, flexWrap: 'wrap', gap: 16 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 6 }}>
            <div style={{
              width: 44, height: 44, borderRadius: 14,
              background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              boxShadow: '0 8px 20px rgba(99,102,241,0.3)',
            }}>
              <Zap size={22} color="white" />
            </div>
            <div>
              <h1 style={{ margin: 0, fontSize: 24, fontWeight: 900, color: 'var(--ink)', letterSpacing: '-0.02em' }}>
                Skill Registry
              </h1>
              <div style={{ fontSize: 13, color: 'var(--ink-3)', marginTop: 2 }}>
                Kemampuan prosedural yang dipelajari AI dari tugas yang diselesaikan
              </div>
            </div>
          </div>
        </div>

        {/* Action buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          {/* Import */}
          <div style={{ position: 'relative' }}>
            <ImportDropdown
              onJson={() => importJsonRef.current?.click()}
              onMarkdown={() => importMdRef.current?.click()}
              loading={importing}
            />
          </div>

          {/* Export */}
          <div style={{ position: 'relative' }}>
            <ExportDropdown onExport={handleExport} loading={exporting} />
          </div>

          {/* Tambah */}
          <button onClick={() => setModal({ mode: 'create' })} style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '10px 20px', borderRadius: 12, border: 'none', cursor: 'pointer',
            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
            color: 'white', fontWeight: 700, fontSize: 13,
            boxShadow: '0 4px 16px rgba(99,102,241,0.3)',
            transition: 'all 0.2s',
          }}>
            <Plus size={16} />Tambah Skill
          </button>
        </div>
      </div>

      {/* Stats row */}
      {stats && (
        <div style={{ display: 'flex', gap: 12, marginBottom: 24, flexWrap: 'wrap' }}>
          <StatCard icon={Zap} label="Total Skill" value={stats.total_skills} color="#6366f1" />
          <StatCard icon={Star} label="Total Pemakaian" value={stats.total_uses} color="#f59e0b" />
          <StatCard icon={BarChart3} label="Kategori Aktif" value={Object.keys(stats.by_category || {}).length} color="#10b981" />
          {stats.top_used?.[0] && (
            <div style={{
              background: 'var(--bg-3)', border: '1px solid var(--border-2)', borderRadius: 16,
              padding: '16px 20px', flex: 1, minWidth: 180,
            }}>
              <div style={{ fontSize: 11, color: 'var(--ink-3)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 6 }}>
                🏆 Paling Sering Dipakai
              </div>
              <div style={{ fontWeight: 800, fontSize: 14, color: 'var(--ink)' }}>{stats.top_used[0].name}</div>
              <div style={{ fontSize: 12, color: 'var(--ink-3)' }}>{stats.top_used[0].use_count}× digunakan</div>
            </div>
          )}
        </div>
      )}

      {/* Search + Filter bar */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: 200 }}>
          <Search size={15} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--ink-3)', pointerEvents: 'none' }} />
          <input value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Cari nama, deskripsi, atau tag..."
            style={{ ...inputStyle, paddingLeft: 36 }} />
        </div>
        <select value={filterCat} onChange={e => setFilterCat(e.target.value)} style={{ ...inputStyle, width: 'auto', minWidth: 160 }}>
          <option value="">Semua Kategori</option>
          {CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
        </select>
      </div>

      {/* Skills grid */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '80px 0', color: 'var(--ink-3)' }}>
          <RefreshCw size={28} style={{ animation: 'spin 1s linear infinite', marginBottom: 12 }} />
          <div style={{ fontSize: 14, fontWeight: 600 }}>Memuat skill...</div>
        </div>
      ) : skills.length === 0 ? (
        <div style={{
          textAlign: 'center', padding: '80px 0',
          background: 'var(--bg-2)', borderRadius: 20, border: '1px dashed var(--border-2)',
        }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>⚡</div>
          <div style={{ fontSize: 18, fontWeight: 800, color: 'var(--ink)', marginBottom: 8 }}>
            {search || filterCat ? 'Tidak ada skill ditemukan' : 'Belum ada skill'}
          </div>
          <div style={{ fontSize: 13, color: 'var(--ink-3)', marginBottom: 20, maxWidth: 380, margin: '0 auto 20px' }}>
            {search || filterCat
              ? 'Coba ubah kata pencarian atau filter kategori'
              : 'Tambahkan skill pertama AI Anda atau import dari file JSON/Markdown'}
          </div>
          {!search && !filterCat && (
            <button onClick={() => setModal({ mode: 'create' })} style={{
              padding: '10px 24px', borderRadius: 12, border: 'none', cursor: 'pointer',
              background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
              color: 'white', fontWeight: 700, fontSize: 13,
            }}>
              <Plus size={14} style={{ marginRight: 6, verticalAlign: 'middle' }} />Tambah Skill Pertama
            </button>
          )}
        </div>
      ) : (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
          gap: 14,
        }}>
          {skills.map(skill => (
            <SkillCard
              key={skill.id}
              skill={skill}
              onEdit={s => setModal({ mode: 'edit', skill: s })}
              onDelete={s => setDeleteConfirm(s)}
            />
          ))}
        </div>
      )}

      {/* Modals */}
      {modal && (
        <SkillModal
          skill={modal.skill}
          onClose={() => setModal(null)}
          onSaved={load}
        />
      )}

      {/* Delete confirm */}
      {deleteConfirm && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 9999, background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{
            background: 'var(--bg-2)', border: '1px solid var(--border-2)', borderRadius: 20,
            padding: '32px', maxWidth: 400, width: '90%',
            boxShadow: '0 20px 60px rgba(0,0,0,0.4)',
          }}>
            <div style={{ textAlign: 'center', marginBottom: 20 }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>🗑️</div>
              <div style={{ fontWeight: 800, fontSize: 17, color: 'var(--ink)', marginBottom: 8 }}>Hapus Skill?</div>
              <div style={{ fontSize: 13, color: 'var(--ink-3)' }}>
                Skill <strong>"{deleteConfirm.name}"</strong> akan dihapus permanen dari registry.
              </div>
            </div>
            <div style={{ display: 'flex', gap: 10 }}>
              <button onClick={() => setDeleteConfirm(null)} style={{
                flex: 1, padding: '10px', borderRadius: 12, border: '1px solid var(--border-2)',
                background: 'var(--bg-3)', color: 'var(--ink)', cursor: 'pointer', fontWeight: 600,
              }}>Batal</button>
              <button onClick={() => handleDelete(deleteConfirm)} style={{
                flex: 1, padding: '10px', borderRadius: 12, border: 'none',
                background: 'var(--danger)', color: 'white', cursor: 'pointer', fontWeight: 700,
              }}>Hapus</button>
            </div>
          </div>
        </div>
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}

// ── Import Dropdown ───────────────────────────────────────────────────────────

function ImportDropdown({ onJson, onMarkdown, loading }) {
  const [open, setOpen] = useState(false)
  const ref = useRef()
  useEffect(() => {
    const close = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])
  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button onClick={() => setOpen(v => !v)} disabled={loading} style={{
        display: 'flex', alignItems: 'center', gap: 7, padding: '10px 16px',
        borderRadius: 12, border: '1px solid var(--border-2)', background: 'var(--bg-3)',
        color: 'var(--ink)', cursor: 'pointer', fontWeight: 600, fontSize: 13,
      }}>
        <Upload size={14} />{loading ? 'Importing...' : 'Import'}<ChevronDown size={13} />
      </button>
      {open && (
        <div style={{
          position: 'absolute', top: 42, left: 0, zIndex: 100,
          background: 'var(--bg-3)', border: '1px solid var(--border-2)',
          borderRadius: 12, boxShadow: '0 8px 24px rgba(0,0,0,0.3)',
          minWidth: 160, overflow: 'hidden',
        }}>
          <button onClick={() => { setOpen(false); onJson() }} style={{ ...menuItemStyle, fontSize: 13 }}>
            <FileText size={13} />Import JSON
          </button>
          <button onClick={() => { setOpen(false); onMarkdown() }} style={{ ...menuItemStyle, fontSize: 13 }}>
            <BookOpen size={13} />Import Markdown
          </button>
        </div>
      )}
    </div>
  )
}

// ── Export Dropdown ───────────────────────────────────────────────────────────

function ExportDropdown({ onExport, loading }) {
  const [open, setOpen] = useState(false)
  const ref = useRef()
  useEffect(() => {
    const close = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])
  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button onClick={() => setOpen(v => !v)} disabled={loading} style={{
        display: 'flex', alignItems: 'center', gap: 7, padding: '10px 16px',
        borderRadius: 12, border: '1px solid var(--border-2)', background: 'var(--bg-3)',
        color: 'var(--ink)', cursor: 'pointer', fontWeight: 600, fontSize: 13,
      }}>
        <Download size={14} />{loading ? 'Exporting...' : 'Export'}<ChevronDown size={13} />
      </button>
      {open && (
        <div style={{
          position: 'absolute', top: 42, left: 0, zIndex: 100,
          background: 'var(--bg-3)', border: '1px solid var(--border-2)',
          borderRadius: 12, boxShadow: '0 8px 24px rgba(0,0,0,0.3)',
          minWidth: 160, overflow: 'hidden',
        }}>
          <button onClick={() => { setOpen(false); onExport('json') }} style={{ ...menuItemStyle, fontSize: 13 }}>
            <FileText size={13} />Export JSON
          </button>
          <button onClick={() => { setOpen(false); onExport('markdown') }} style={{ ...menuItemStyle, fontSize: 13 }}>
            <BookOpen size={13} />Export Markdown
          </button>
        </div>
      )}
    </div>
  )
}
