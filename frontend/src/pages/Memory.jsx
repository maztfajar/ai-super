import { useState, useEffect } from 'react'
import { api } from '../hooks/useApi'
import { useAuthStore } from '../store'
import toast from 'react-hot-toast'
import {
  Trash2, Plus, Brain, RefreshCw, CheckCircle2, XCircle,
  Database, Zap, Clock, MessageSquare, Info, Shield,
  ChevronDown, ChevronUp,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import clsx from 'clsx'

// ── Komponen kecil ────────────────────────────────────────────
function InfoCard({ icon: Icon, title, value, sub, color = 'text-accent-2', bg = 'bg-accent/10' }) {
  return (
    <div className="bg-bg-3 border border-border-2 rounded-xl p-5 shadow-sm">
      <div className={clsx('w-9 h-9 rounded-lg flex items-center justify-center mb-3', bg)}>
        <Icon size={16} className={color}/>
      </div>
      <div className="text-xl font-bold font-mono text-ink tracking-tight">{value}</div>
      <div className="text-xs font-bold text-ink-3 uppercase tracking-wider mt-1">{title}</div>
      {sub && <div className="text-[11px] text-ink-2 mt-1.5 font-semibold uppercase tracking-tight opacity-70">{sub}</div>}
    </div>
  )
}

function LayerCard({ icon, title, color, bgColor, badge, items, children }) {
  const [open, setOpen] = useState(false)
  return (
    <div className={clsx('rounded-2xl border-2 overflow-hidden shadow-lg', bgColor)}>
      <button onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-4 px-5 py-4 hover:bg-black/5 transition-all">
        <span className="text-2xl flex-shrink-0">{icon}</span>
        <div className="flex-1 text-left">
          <div className={clsx('text-lg font-bold uppercase tracking-tight', color)}>{title}</div>
          {badge && <div className="text-xs opacity-80 font-bold uppercase tracking-widest mt-0.5">{badge}</div>}
        </div>
        {open ? <ChevronUp size={20} className="opacity-60"/> : <ChevronDown size={20} className="opacity-60"/>}
      </button>
      {open && <div className="px-5 pb-5 space-y-3">{children}</div>}
    </div>
  )
}

export default function Memory() {
  const { t } = useTranslation()
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
        <h1 className="text-3xl font-bold text-ink flex items-center gap-3 uppercase tracking-tighter">
          <Brain size={32} className="text-accent-2"/>{t('memory_system_title')}
        </h1>
        <p className="text-lg text-ink-3 mt-1.5 font-semibold uppercase tracking-tight opacity-80">
          {t('memory_system_desc')}
        </p>
      </div>

      {/* ── Penjelasan sistem memory ── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">

        <LayerCard icon="⚡" title={t('short_term_memory')}
          color="text-sky-400" bgColor="bg-sky-400/5 border-sky-400/20"
          badge={t('short_term_desc')}>
          <div className="text-base text-ink-3 space-y-3 font-semibold">
            <div className="flex items-start gap-3">
              <CheckCircle2 size={16} className="text-success mt-0.5 flex-shrink-0"/>
              <span><strong className="text-ink">Aktif otomatis</strong> — setiap percakapan langsung disimpan</span>
            </div>
            <div className="flex items-start gap-3">
              <CheckCircle2 size={16} className="text-success mt-0.5 flex-shrink-0"/>
              <span>AI membawa <strong className="text-ink font-bold">20 pesan terakhir</strong> di setiap sesi</span>
            </div>
            <div className="flex items-start gap-3">
              <CheckCircle2 size={16} className="text-success mt-0.5 flex-shrink-0"/>
              <span>Tersimpan <strong className="text-ink font-bold">7 hari</strong> di Redis, auto-expire setelahnya</span>
            </div>
            <div className="flex items-start gap-3">
              <Info size={16} className="text-sky-400 mt-0.5 flex-shrink-0"/>
              <span>Jika Redis tidak aktif, AI tetap mengambil riwayat dari database</span>
            </div>
          </div>
        </LayerCard>

        <LayerCard icon="📚" title={t('long_term_memory')}
          color="text-success" bgColor="bg-success/5 border-success/20"
          badge={t('long_term_desc')}>
          <div className="text-base text-ink-3 space-y-3 font-semibold">
            <div className="flex items-start gap-3">
              <CheckCircle2 size={16} className="text-success mt-0.5 flex-shrink-0"/>
              <span><strong className="text-ink font-bold">Semua pesan</strong> disimpan permanen ke database</span>
            </div>
            <div className="flex items-start gap-3">
              <CheckCircle2 size={16} className="text-success mt-0.5 flex-shrink-0"/>
              <span>Saat sesi dibuka ulang, AI <strong className="text-ink font-bold">memuat riwayat dari DB</strong> ke Redis</span>
            </div>
            <div className="flex items-start gap-3">
              <CheckCircle2 size={16} className="text-success mt-0.5 flex-shrink-0"/>
              <span>Bisa muat ulang <strong className="text-ink font-bold">hingga 50 pesan</strong> terakhir per sesi</span>
            </div>
            <div className="flex items-start gap-3">
              <Info size={16} className="text-success mt-0.5 flex-shrink-0"/>
              <span>Tidak pernah hilang kecuali sesi dihapus manual atau reset analytics</span>
            </div>
          </div>
        </LayerCard>

        <LayerCard icon="🎯" title={t('behavioral_memory')}
          color="text-warn" bgColor="bg-warn/5 border-warn/20"
          badge={t('behavioral_desc')}>
          <div className="text-base text-ink-3 space-y-3 font-semibold">
            <div className="flex items-start gap-3">
              <CheckCircle2 size={16} className="text-success mt-0.5 flex-shrink-0"/>
              <span>Preferensi yang <strong className="text-ink font-bold">Anda tambahkan manual</strong> di bawah ini</span>
            </div>
            <div className="flex items-start gap-3">
              <CheckCircle2 size={16} className="text-success mt-0.5 flex-shrink-0"/>
              <span>Selalu disertakan di <strong className="text-ink font-bold">setiap percakapan</strong> (semua sesi)</span>
            </div>
            <div className="flex items-start gap-3">
              <CheckCircle2 size={16} className="text-success mt-0.5 flex-shrink-0"/>
              <span>Contoh: gaya bahasa, topik favorit, informasi diri</span>
            </div>
            <div className="flex items-start gap-3">
              <Info size={16} className="text-warn mt-0.5 flex-shrink-0"/>
              <span>Tambahkan preferensi agar AI makin personal untuk Anda</span>
            </div>
          </div>
        </LayerCard>
      </div>

      {/* ── Status realtime ── */}
      <div className="bg-bg-3 border border-border-2 rounded-2xl p-6 shadow-md">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-xl font-bold text-ink flex items-center gap-3 uppercase tracking-tight">
            <Database size={20} className="text-accent-2"/>{t('memory_status')}
          </h2>
          <div className="flex items-center gap-3">
            {selSession && (
              <select value={selSession} onChange={e => setSelSession(e.target.value)}
                className="bg-bg-2 border border-border-2 rounded-xl px-4 py-2 text-sm text-ink outline-none max-w-64 truncate font-bold shadow-sm">
                {sessions.map(s => (
                  <option key={s.id} value={s.id}>{s.title?.slice(0, 40) || 'Chat'}</option>
                ))}
              </select>
            )}
            <button onClick={() => {
              if (sessions.length > 0 && !selSession) setSelSession(sessions[0]?.id)
              else setSelSession(null)
            }}
              className="text-xs text-ink-3 hover:text-accent-2 px-4 py-2 rounded-xl bg-bg-4 border border-border-2 font-bold uppercase tracking-wider transition-all shadow-sm">
              {selSession ? t('hide_session') : t('select_session')}
            </button>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <InfoCard icon={Zap} title={t('redis_messages')}
            value={memInfo?.redis_messages ?? '—'}
            sub="sesi ini (short-term)"
            color="text-sky-400" bg="bg-sky-400/10"/>
          <InfoCard icon={Database} title={t('db_messages')}
            value={memInfo?.db_messages ?? '—'}
            sub="sesi ini (long-term)"
            color="text-success" bg="bg-success/10"/>
          <InfoCard icon={MessageSquare} title={t('context_window_label')}
            value={memInfo?.context_window ?? 20}
            sub="pesan terakhir dibawa ke AI"
            color="text-accent-2" bg="bg-accent/10"/>
          <InfoCard icon={Clock} title={t('redis_ttl_label')}
            value={(memInfo?.redis_ttl_days ?? 7) + ' hari'}
            sub="sebelum auto-expire"
            color="text-warn" bg="bg-warn/10"/>
        </div>

        {!selSession && (
          <div className="mt-5 p-4 bg-bg-4 border border-border/20 rounded-xl text-sm text-ink-3 flex items-center gap-3 font-semibold uppercase tracking-tight">
            <Info size={18} className="text-accent-2 flex-shrink-0"/>
            Klik "Pilih Sesi" di atas untuk melihat status memory sesi tertentu
          </div>
        )}
      </div>

      {/* ── FAQ Memory ── */}
      <LayerCard icon="❓" title={t('common_questions')}
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
              a: 'AI ORCHESTRATOR tetap bekerja. Short-term memory (Redis) akan di-bypass, dan AI mengambil riwayat langsung dari database. Performa sedikit lebih lambat tapi fungsional.',
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
            <div key={i} className="border border-border-2 rounded-2xl overflow-hidden shadow-sm">
              <div className="flex items-start gap-4 p-4 bg-bg-4">
                {item.ok === true && <CheckCircle2 size={18} className="text-success flex-shrink-0 mt-0.5"/>}
                {item.ok === false && <XCircle size={18} className="text-warn flex-shrink-0 mt-0.5"/>}
                {item.ok === null && <Info size={18} className="text-accent-2 flex-shrink-0 mt-0.5"/>}
                <div className="text-base font-bold text-ink uppercase tracking-tight">{item.q}</div>
              </div>
              <div className="px-4 py-4 text-base text-ink-2 leading-relaxed font-semibold opacity-90">{item.a}</div>
            </div>
          ))}
        </div>
      </LayerCard>

      {/* ── Behavioral Memory (tambah manual) ── */}
      <LayerCard icon="🎯" title={`${t('behavioral_memory')} (${memories.length} tersimpan)`}
        color="text-warn" bgColor="bg-warn/5 border-warn/20"
        badge={t('behavioral_memory_desc')}>
        <div className="flex items-center justify-between mb-4">
          <p className="text-base text-ink-3 font-semibold uppercase tracking-tight">Preferensi yang selalu disertakan ke AI di semua percakapan</p>
          <button onClick={load} className="text-ink-3 hover:text-ink p-2 rounded-lg hover:bg-bg-4 transition-all">
            <RefreshCw size={18} className={loading ? 'animate-spin' : ''}/>
          </button>
        </div>

        {/* Input tambah */}
        <div className="flex gap-3 mb-5">
          <input value={newMem} onChange={e => setNewMem(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && add()}
            placeholder={t('add_memory_placeholder')}
            className="flex-1 bg-bg-2 border border-border-2 rounded-xl px-5 py-4 text-base text-ink placeholder-ink-3 outline-none focus:border-accent font-semibold shadow-inner"/>
          <button onClick={add} disabled={!newMem.trim() || adding}
            className="px-6 py-4 bg-accent hover:bg-accent/80 text-white rounded-xl text-base font-bold disabled:opacity-50 flex items-center gap-3 transition-all shadow-lg shadow-accent/20 active:scale-95">
            {adding ? <RefreshCw size={18} className="animate-spin"/> : <Plus size={18}/>}
            {t('add')}
          </button>
        </div>

        {/* Contoh preset */}
        <div className="mb-6">
          <div className="text-sm text-ink-3 mb-3 font-bold uppercase tracking-widest opacity-70">💡 Contoh cepat — klik untuk tambahkan:</div>
          <div className="flex flex-wrap gap-2">
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
                className="text-xs px-4 py-2 bg-bg-4 hover:bg-accent/10 hover:text-accent-2 border-2 border-border/40 hover:border-accent/40 rounded-xl text-ink-3 font-bold uppercase tracking-tight transition-all shadow-sm">
                {preset}
              </button>
            ))}
          </div>
        </div>

        {/* List memory */}
        {loading ? (
          <div className="text-base text-ink-3 font-semibold flex items-center gap-3 py-6">
            <RefreshCw size={20} className="animate-spin"/>{t('loading_behavioral')}
          </div>
        ) : memories.length === 0 ? (
          <div className="text-center py-12 bg-bg-4/50 rounded-2xl border-2 border-dashed border-border/50">
            <Brain size={48} className="mx-auto mb-4 opacity-20"/>
            <p className="text-lg font-bold text-ink-2 uppercase tracking-tight">Belum ada behavioral memory</p>
            <p className="text-sm text-ink-3 font-semibold opacity-70">Tambahkan preferensi agar AI makin personal</p>
          </div>
        ) : (
          <div className="space-y-3">
            {memories.map(m => (
              <div key={m.id} className="flex items-start gap-4 p-5 bg-bg-4 border border-border-2 rounded-2xl group hover:border-accent/30 transition-all shadow-sm">
                <div className="flex-1 min-w-0">
                  <div className="text-base text-ink leading-relaxed font-semibold">{m.content}</div>
                  <div className="flex items-center gap-4 mt-3 flex-wrap">
                    <span className={clsx('text-xs px-3 py-1 rounded-lg border-2 font-bold uppercase tracking-wider', TYPE_COLOR[m.memory_type] || 'bg-bg-5 text-ink-3 border-border')}>
                      {m.memory_type}
                    </span>
                    <span className="text-xs text-ink-3 font-bold uppercase tracking-widest opacity-60">
                      {new Date(m.created_at).toLocaleDateString('id-ID', { dateStyle: 'medium' })}
                    </span>
                  </div>
                </div>
                <button onClick={() => del(m.id)}
                  className="opacity-0 group-hover:opacity-100 p-2.5 rounded-xl hover:bg-danger/10 flex-shrink-0 transition-all shadow-sm">
                  <Trash2 size={18} className="text-danger"/>
                </button>
              </div>
            ))}
          </div>
        )}
      </LayerCard>
    </div>
  )
}
