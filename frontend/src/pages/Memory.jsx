import { useState, useEffect } from 'react'
import { api } from '../hooks/useApi'
import { useAuthStore } from '../store'
import toast from 'react-hot-toast'
import {
  Trash2, Plus, Brain, RefreshCw, CheckCircle2, XCircle,
  Database, Zap, Clock, MessageSquare, Info, Shield,
  ChevronDown, ChevronUp,
} from 'lucide-react'
import clsx from 'clsx'

// ── Komponen kecil ────────────────────────────────────────────
function InfoCard({ icon: Icon, title, value, sub, color = 'text-accent-2', bg = 'bg-accent/10' }) {
  return (
    <div className="bg-bg-3 border border-border rounded-xl p-3.5">
      <div className={clsx('w-7 h-7 rounded-lg flex items-center justify-center mb-2', bg)}>
        <Icon size={13} className={color}/>
      </div>
      <div className="text-lg font-bold font-mono text-ink">{value}</div>
      <div className="text-[10px] text-ink-3">{title}</div>
      {sub && <div className="text-[10px] text-ink-2 mt-0.5">{sub}</div>}
    </div>
  )
}

function LayerCard({ icon, title, color, bgColor, badge, items, children }) {
  const [open, setOpen] = useState(false)
  return (
    <div className={clsx('rounded-xl border overflow-hidden', bgColor)}>
      <button onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-black/5 transition-colors">
        <span className="text-xl flex-shrink-0">{icon}</span>
        <div className="flex-1 text-left">
          <div className={clsx('text-sm font-semibold', color)}>{title}</div>
          {badge && <div className="text-[10px] opacity-70">{badge}</div>}
        </div>
        {open ? <ChevronUp size={14} className="opacity-50"/> : <ChevronDown size={14} className="opacity-50"/>}
      </button>
      {open && <div className="px-4 pb-4 space-y-2">{children}</div>}
    </div>
  )
}

export default function Memory() {
  const { user } = useAuthStore()
  const [memories,  setMemories]  = useState([])
  const [newMem,    setNewMem]    = useState('')
  const [loading,   setLoading]   = useState(true)
  const [sessions,  setSessions]  = useState([])
  const [selSession, setSelSession] = useState(null)
  const [memInfo,   setMemInfo]   = useState(null)
  const [adding,    setAdding]    = useState(false)

  const TYPE_COLOR = {
    behavioral: 'bg-accent/10 text-accent-2 border-accent/20',
    preference: 'bg-success/10 text-success border-success/20',
    fact:       'bg-info/10 text-info border-info/20',
    summary:    'bg-warn/10 text-warn border-warn/20',
  }

  const load = async () => {
    setLoading(true)
    try {
      const [mems, sess] = await Promise.allSettled([
        api.listMemories(),
        api.listSessions(),
      ])
      if (mems.status === 'fulfilled') setMemories(mems.value)
      if (sess.status === 'fulfilled') setSessions(sess.value.slice(0, 10))
    } catch {}
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  // Load memory info saat sesi dipilih
  useEffect(() => {
    if (!selSession) { setMemInfo(null); return }
    api.get('/memory/session-info/' + selSession)
      .then(setMemInfo)
      .catch(() => setMemInfo(null))
  }, [selSession])

  const add = async () => {
    if (!newMem.trim()) return
    setAdding(true)
    try {
      await api.addMemory(newMem)
      setNewMem('')
      toast.success('Memory ditambahkan')
      await load()
    } catch { toast.error('Gagal') }
    finally { setAdding(false) }
  }

  const del = async (id) => {
    try { await api.deleteMemory(id); load() }
    catch { toast.error('Gagal') }
  }

  return (
    <div className="p-4 md:p-6 w-full space-y-5">
      <div>
        <h1 className="text-lg font-bold text-ink flex items-center gap-2">
          <Brain size={18} className="text-accent-2"/>Memory System
        </h1>
        <p className="text-xs text-ink-3 mt-0.5">
          Sistem memori 3 lapis — AI mengingat konteks percakapan secara otomatis
        </p>
      </div>

      {/* ── Penjelasan sistem memory ── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">

        <LayerCard icon="⚡" title="Short-term Memory"
          color="text-sky-400" bgColor="bg-sky-400/5 border-sky-400/20"
          badge="Redis Cache — TTL 7 hari">
          <div className="text-[10px] text-ink-3 space-y-1.5">
            <div className="flex items-start gap-1.5">
              <CheckCircle2 size={10} className="text-success mt-0.5 flex-shrink-0"/>
              <span><strong className="text-ink-2">Aktif otomatis</strong> — setiap percakapan langsung disimpan</span>
            </div>
            <div className="flex items-start gap-1.5">
              <CheckCircle2 size={10} className="text-success mt-0.5 flex-shrink-0"/>
              <span>AI membawa <strong className="text-ink-2">20 pesan terakhir</strong> di setiap sesi</span>
            </div>
            <div className="flex items-start gap-1.5">
              <CheckCircle2 size={10} className="text-success mt-0.5 flex-shrink-0"/>
              <span>Tersimpan <strong className="text-ink-2">7 hari</strong> di Redis, auto-expire setelahnya</span>
            </div>
            <div className="flex items-start gap-1.5">
              <Info size={10} className="text-sky-400 mt-0.5 flex-shrink-0"/>
              <span>Jika Redis tidak aktif, AI tetap mengambil riwayat dari database</span>
            </div>
          </div>
        </LayerCard>

        <LayerCard icon="📚" title="Long-term Memory"
          color="text-success" bgColor="bg-success/5 border-success/20"
          badge="Database SQLite — Permanen">
          <div className="text-[10px] text-ink-3 space-y-1.5">
            <div className="flex items-start gap-1.5">
              <CheckCircle2 size={10} className="text-success mt-0.5 flex-shrink-0"/>
              <span><strong className="text-ink-2">Semua pesan</strong> disimpan permanen ke database</span>
            </div>
            <div className="flex items-start gap-1.5">
              <CheckCircle2 size={10} className="text-success mt-0.5 flex-shrink-0"/>
              <span>Saat sesi dibuka ulang, AI <strong className="text-ink-2">memuat riwayat dari DB</strong> ke Redis</span>
            </div>
            <div className="flex items-start gap-1.5">
              <CheckCircle2 size={10} className="text-success mt-0.5 flex-shrink-0"/>
              <span>Bisa muat ulang <strong className="text-ink-2">hingga 50 pesan</strong> terakhir per sesi</span>
            </div>
            <div className="flex items-start gap-1.5">
              <Info size={10} className="text-success mt-0.5 flex-shrink-0"/>
              <span>Tidak pernah hilang kecuali sesi dihapus manual atau reset analytics</span>
            </div>
          </div>
        </LayerCard>

        <LayerCard icon="🎯" title="Behavioral Memory"
          color="text-warn" bgColor="bg-warn/5 border-warn/20"
          badge="Preferensi User — Permanen">
          <div className="text-[10px] text-ink-3 space-y-1.5">
            <div className="flex items-start gap-1.5">
              <CheckCircle2 size={10} className="text-success mt-0.5 flex-shrink-0"/>
              <span>Preferensi yang <strong className="text-ink-2">Anda tambahkan manual</strong> di bawah ini</span>
            </div>
            <div className="flex items-start gap-1.5">
              <CheckCircle2 size={10} className="text-success mt-0.5 flex-shrink-0"/>
              <span>Selalu disertakan di <strong className="text-ink-2">setiap percakapan</strong> (semua sesi)</span>
            </div>
            <div className="flex items-start gap-1.5">
              <CheckCircle2 size={10} className="text-success mt-0.5 flex-shrink-0"/>
              <span>Contoh: gaya bahasa, topik favorit, informasi diri</span>
            </div>
            <div className="flex items-start gap-1.5">
              <Info size={10} className="text-warn mt-0.5 flex-shrink-0"/>
              <span>Tambahkan preferensi agar AI makin personal untuk Anda</span>
            </div>
          </div>
        </LayerCard>
      </div>

      {/* ── Status realtime ── */}
      <div className="bg-bg-3 border border-border rounded-xl p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-sm font-semibold text-ink flex items-center gap-2">
            <Database size={13} className="text-accent-2"/>Status Memory
          </h2>
          <div className="flex items-center gap-2">
            {selSession && (
              <select value={selSession} onChange={e => setSelSession(e.target.value)}
                className="bg-bg-2 border border-border-2 rounded-lg px-2 py-1 text-[10px] text-ink outline-none max-w-40 truncate">
                {sessions.map(s => (
                  <option key={s.id} value={s.id}>{s.title?.slice(0, 30) || 'Chat'}</option>
                ))}
              </select>
            )}
            <button onClick={() => {
              if (sessions.length > 0 && !selSession) setSelSession(sessions[0]?.id)
              else setSelSession(null)
            }}
              className="text-[10px] text-ink-3 hover:text-accent-2 px-2 py-1 rounded-lg bg-bg-4 border border-border transition-colors">
              {selSession ? 'Sembunyikan' : 'Pilih Sesi'}
            </button>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <InfoCard icon={Zap} title="Pesan di Redis"
            value={memInfo?.redis_messages ?? '—'}
            sub="sesi ini (short-term)"
            color="text-sky-400" bg="bg-sky-400/10"/>
          <InfoCard icon={Database} title="Pesan di Database"
            value={memInfo?.db_messages ?? '—'}
            sub="sesi ini (long-term)"
            color="text-success" bg="bg-success/10"/>
          <InfoCard icon={MessageSquare} title="Context Window"
            value={memInfo?.context_window ?? 20}
            sub="pesan terakhir dibawa ke AI"
            color="text-accent-2" bg="bg-accent/10"/>
          <InfoCard icon={Clock} title="TTL Redis"
            value={(memInfo?.redis_ttl_days ?? 7) + ' hari'}
            sub="sebelum auto-expire"
            color="text-warn" bg="bg-warn/10"/>
        </div>

        {!selSession && (
          <div className="mt-3 p-2.5 bg-bg-4 rounded-xl text-[10px] text-ink-3 flex items-center gap-2">
            <Info size={11} className="text-accent-2 flex-shrink-0"/>
            Klik "Pilih Sesi" di atas untuk melihat status memory sesi tertentu
          </div>
        )}
      </div>

      {/* ── FAQ Memory ── */}
      <LayerCard icon="❓" title="Pertanyaan Umum"
        color="text-accent-2" bgColor="bg-bg-3 border-border">
        <div className="space-y-3">
          {[
            {
              q: 'Apakah AI mengingat percakapan sebelumnya?',
              a: 'Ya. Semua pesan tersimpan di database secara permanen. Saat Anda membuka sesi lama, AI akan memuat kembali hingga 50 pesan terakhir dari database. AI tidak akan lupa selama sesi tidak dihapus.',
              ok: true,
            },
            {
              q: 'Bagaimana jika Redis tidak aktif?',
              a: 'AI SUPER ASSISTANT tetap bekerja. Short-term memory (Redis) akan di-bypass, dan AI mengambil riwayat langsung dari database. Performa sedikit lebih lambat tapi fungsional.',
              ok: true,
            },
            {
              q: 'Berapa lama riwayat chat tersimpan?',
              a: 'Permanen di database, tidak ada batas waktu. Redis cache bertahan 7 hari lalu auto-expire (tapi database tetap ada). Gunakan menu Analytics → Hapus Chat Lama untuk membersihkan.',
              ok: true,
            },
            {
              q: 'Apakah AI membawa semua riwayat ke setiap prompt?',
              a: 'Tidak — hanya 20 pesan terakhir per sesi yang dibawa ke AI (context window). Ini untuk menjaga efisiensi dan biaya token. Pesan lebih lama tetap tersimpan di database.',
              ok: null,
            },
            {
              q: 'Bagaimana cara AI mengingat preferensi saya lintas sesi?',
              a: 'Gunakan Behavioral Memory di bawah — tambahkan preferensi seperti "Saya suka jawaban singkat" atau "Nama saya [nama]". Preferensi ini disertakan di SEMUA percakapan, bukan hanya satu sesi.',
              ok: true,
            },
          ].map((item, i) => (
            <div key={i} className="border border-border rounded-xl overflow-hidden">
              <div className="flex items-start gap-2.5 p-3 bg-bg-4">
                {item.ok === true && <CheckCircle2 size={13} className="text-success flex-shrink-0 mt-0.5"/>}
                {item.ok === false && <XCircle size={13} className="text-warn flex-shrink-0 mt-0.5"/>}
                {item.ok === null && <Info size={13} className="text-accent-2 flex-shrink-0 mt-0.5"/>}
                <div className="text-xs font-semibold text-ink">{item.q}</div>
              </div>
              <div className="px-3 py-2.5 text-[11px] text-ink-2 leading-relaxed">{item.a}</div>
            </div>
          ))}
        </div>
      </LayerCard>

      {/* ── Behavioral Memory (tambah manual) ── */}
      <LayerCard icon="🎯" title={`Behavioral Memory (${memories.length} tersimpan)`}
        color="text-warn" bgColor="bg-warn/5 border-warn/20"
        badge="Preferensi yang selalu disertakan ke AI">
        <div className="flex items-center justify-between mb-3">
          <p className="text-[10px] text-ink-3">Preferensi yang selalu disertakan ke AI di semua percakapan</p>
          <button onClick={load} className="text-ink-3 hover:text-ink">
            <RefreshCw size={12} className={loading ? 'animate-spin' : ''}/>
          </button>
        </div>

        {/* Input tambah */}
        <div className="flex gap-2 mb-4">
          <input value={newMem} onChange={e => setNewMem(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && add()}
            placeholder='Contoh: "Saya lebih suka jawaban dalam Bahasa Indonesia yang singkat"'
            className="flex-1 bg-bg-2 border border-border-2 rounded-xl px-3 py-2 text-xs text-ink placeholder-ink-3 outline-none focus:border-accent"/>
          <button onClick={add} disabled={!newMem.trim() || adding}
            className="px-3 py-2 bg-accent hover:bg-accent/80 text-white rounded-xl text-xs font-medium disabled:opacity-50 flex items-center gap-1.5 transition-colors">
            {adding ? <RefreshCw size={12} className="animate-spin"/> : <Plus size={12}/>}
            Tambah
          </button>
        </div>

        {/* Contoh preset */}
        <div className="mb-4">
          <div className="text-[10px] text-ink-3 mb-2">💡 Contoh cepat — klik untuk tambahkan:</div>
          <div className="flex flex-wrap gap-1.5">
            {[
              'Jawab selalu dalam Bahasa Indonesia',
              'Saya suka jawaban singkat dan langsung ke poin',
              'Gunakan format bullet point jika ada daftar',
              'Saya adalah developer, jelaskan hal teknis dengan detail',
              'Jangan gunakan emoji berlebihan',
              'Selalu sertakan contoh kode jika relevan',
            ].map(preset => (
              <button key={preset}
                onClick={async () => {
                  try { await api.addMemory(preset); toast.success('Ditambahkan!'); load() }
                  catch { toast.error('Gagal') }
                }}
                className="text-[10px] px-2.5 py-1 bg-bg-4 hover:bg-accent/10 hover:text-accent-2 border border-border hover:border-accent/30 rounded-lg text-ink-3 transition-colors">
                {preset}
              </button>
            ))}
          </div>
        </div>

        {/* List memory */}
        {loading ? (
          <div className="text-xs text-ink-3 flex items-center gap-2 py-4">
            <RefreshCw size={12} className="animate-spin"/>Memuat...
          </div>
        ) : memories.length === 0 ? (
          <div className="text-center py-8 text-ink-3">
            <Brain size={28} className="mx-auto mb-2 opacity-30"/>
            <p className="text-sm mb-1">Belum ada behavioral memory</p>
            <p className="text-[11px] opacity-70">Tambahkan preferensi agar AI makin personal</p>
          </div>
        ) : (
          <div className="space-y-2">
            {memories.map(m => (
              <div key={m.id} className="flex items-start gap-2.5 p-3 bg-bg-4 border border-border rounded-xl group hover:border-border-2 transition-colors">
                <div className="flex-1 min-w-0">
                  <div className="text-xs text-ink leading-relaxed">{m.content}</div>
                  <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                    <span className={clsx('text-[9px] px-1.5 py-0.5 rounded border font-medium', TYPE_COLOR[m.memory_type] || 'bg-bg-5 text-ink-3 border-border')}>
                      {m.memory_type}
                    </span>
                    <span className="text-[9px] text-ink-3">
                      {new Date(m.created_at).toLocaleDateString('id-ID', { dateStyle: 'medium' })}
                    </span>
                  </div>
                </div>
                <button onClick={() => del(m.id)}
                  className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-danger/10 flex-shrink-0 transition-all">
                  <Trash2 size={12} className="text-danger"/>
                </button>
              </div>
            ))}
          </div>
        )}
      </LayerCard>
    </div>
  )
}
