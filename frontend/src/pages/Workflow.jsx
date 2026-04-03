import { useState, useEffect } from 'react'
import { api } from '../hooks/useApi'
import toast from 'react-hot-toast'
import { Plus, Trash2, Play, Pause, RefreshCw, Repeat2 } from 'lucide-react'

const TRIGGER_ICON = { manual: '🖱️', schedule: '⏰', webhook: '🪝', message: '📨' }

export default function Workflow() {
  const [workflows, setWorkflows] = useState([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [form, setForm] = useState({ name: '', description: '', trigger_type: 'manual' })

  const load = () => api.listWorkflows().then(setWorkflows).catch(() => []).finally(() => setLoading(false))
  useEffect(() => { load() }, [])

  async function create() {
    if (!form.name.trim()) return
    try {
      await api.createWorkflow(form)
      toast.success('Workflow dibuat!')
      setCreating(false)
      setForm({ name: '', description: '', trigger_type: 'manual' })
      load()
    } catch { toast.error('Gagal membuat workflow') }
  }

  async function run(id, name) {
    try {
      await api.runWorkflow(id)
      toast.success(`Workflow "${name}" dijalankan!`)
      setTimeout(load, 1000)
    } catch { toast.error('Gagal menjalankan') }
  }

  async function toggle(wf) {
    try {
      await api.updateWorkflow(wf.id, { is_active: !wf.is_active })
      load()
    } catch { toast.error('Gagal') }
  }

  async function del(id, name) {
    if (!confirm(`Hapus workflow "${name}"?`)) return
    try { await api.deleteWorkflow(id); toast.success('Dihapus'); load() } catch { toast.error('Gagal') }
  }

  return (
    <div className="p-4 md:p-6 w-full">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-lg font-bold text-ink">Workflow Automation</h1>
          <p className="text-xs text-ink-3 mt-0.5">Otomasi tugas AI — n8n style</p>
        </div>
        <button onClick={() => setCreating(true)} className="flex items-center gap-1.5 px-3 py-1.5 bg-accent hover:bg-accent/80 text-white rounded-lg text-xs font-medium transition-colors">
          <Plus size={13} /> Workflow Baru
        </button>
      </div>

      {/* Create form */}
      {creating && (
        <div className="bg-bg-3 border border-accent/30 rounded-xl p-4 mb-4">
          <h3 className="text-sm font-semibold text-ink mb-3">Buat Workflow Baru</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
            <div>
              <label className="text-xs text-ink-3 mb-1 block">Nama Workflow *</label>
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="Contoh: Auto Reply Telegram"
                className="w-full bg-bg-4 border border-border-2 rounded-lg px-3 py-2 text-sm text-ink outline-none focus:border-accent" />
            </div>
            <div>
              <label className="text-xs text-ink-3 mb-1 block">Tipe Trigger</label>
              <select value={form.trigger_type} onChange={(e) => setForm({ ...form, trigger_type: e.target.value })}
                className="w-full bg-bg-4 border border-border-2 rounded-lg px-3 py-2 text-sm text-ink outline-none">
                <option value="manual">🖱️ Manual</option>
                <option value="schedule">⏰ Jadwal (Cron)</option>
                <option value="webhook">🪝 Webhook</option>
                <option value="message">📨 Pesan Masuk</option>
              </select>
            </div>
          </div>
          <div className="mb-3">
            <label className="text-xs text-ink-3 mb-1 block">Deskripsi (opsional)</label>
            <input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="Deskripsi singkat workflow ini..."
              className="w-full bg-bg-4 border border-border-2 rounded-lg px-3 py-2 text-sm text-ink outline-none focus:border-accent" />
          </div>
          <div className="flex gap-2">
            <button onClick={create} className="px-4 py-2 bg-accent hover:bg-accent/80 text-white rounded-lg text-sm">Buat</button>
            <button onClick={() => setCreating(false)} className="px-4 py-2 border border-border text-ink-2 rounded-lg text-sm hover:bg-bg-4">Batal</button>
          </div>
        </div>
      )}

      {/* Workflow list */}
      {loading && <div className="text-xs text-ink-3 py-4 flex items-center gap-2"><RefreshCw size={12} className="animate-spin" /> Memuat...</div>}

      {!loading && workflows.length === 0 && !creating && (
        <div className="bg-bg-3 border border-border rounded-xl p-8 text-center">
          <Repeat2 size={32} className="text-ink-3 mx-auto mb-3" />
          <h2 className="text-sm font-semibold text-ink mb-2">Belum ada workflow</h2>
          <p className="text-xs text-ink-3 mb-4">Buat workflow pertama untuk mengotomasi tugas AI kamu</p>
          <div className="grid grid-cols-2 gap-2 max-w-lg mx-auto text-left text-xs">
            {[
              { icon: '✈', t: 'Telegram Auto-Reply', d: 'Balas pesan otomatis via AI' },
              { icon: '⏰', t: 'Daily Report', d: 'Generate laporan setiap pagi' },
              { icon: '📄', t: 'Auto Index Docs', d: 'Index dokumen baru ke RAG' },
              { icon: '🌐', t: 'Web Monitor', d: 'Monitor website + alert' },
            ].map((ex) => (
              <div key={ex.t} className="p-2.5 bg-bg-4 rounded-lg border border-border">
                <div className="font-medium text-ink mb-0.5">{ex.icon} {ex.t}</div>
                <div className="text-ink-3">{ex.d}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="space-y-2">
        {workflows.map((wf) => (
          <div key={wf.id} className="flex items-center gap-3 p-4 bg-bg-3 border border-border rounded-xl hover:border-border-2 transition-colors group">
            <div className="text-xl">{TRIGGER_ICON[wf.trigger_type] || '⚙'}</div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-ink">{wf.name}</span>
                <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${wf.is_active ? 'bg-success/10 text-success' : 'bg-ink-3/10 text-ink-3'}`}>
                  {wf.is_active ? '● Aktif' : '○ Pause'}
                </span>
              </div>
              {wf.description && <div className="text-xs text-ink-3 mt-0.5">{wf.description}</div>}
              <div className="text-[10px] text-ink-3 mt-0.5">
                {TRIGGER_ICON[wf.trigger_type]} {wf.trigger_type} · {wf.run_count} runs
                {wf.last_run_at && ` · Last: ${new Date(wf.last_run_at).toLocaleString('id-ID')}`}
              </div>
            </div>
            <div className="flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
              <button onClick={() => run(wf.id, wf.name)} className="p-1.5 rounded-lg bg-success/10 hover:bg-success/20 text-success">
                <Play size={13} />
              </button>
              <button onClick={() => toggle(wf)} className="p-1.5 rounded-lg bg-bg-4 hover:bg-bg-5 text-ink-2">
                <Pause size={13} />
              </button>
              <button onClick={() => del(wf.id, wf.name)} className="p-1.5 rounded-lg hover:bg-danger/10 text-danger">
                <Trash2 size={13} />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
