import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../hooks/useApi'
import { Bot, RefreshCw, CheckCircle2, XCircle, Clock } from 'lucide-react'
import clsx from 'clsx'

const PROVIDER_COLOR = {
  openai:    'bg-emerald-500/15 text-emerald-400 border-emerald-500/20',
  anthropic: 'bg-orange-500/15 text-orange-400 border-orange-500/20',
  google:    'bg-blue-500/15 text-blue-400 border-blue-500/20',
  ollama:    'bg-purple-500/15 text-purple-400 border-purple-500/20',
  sumopod:   'bg-pink-500/15 text-pink-400 border-pink-500/20',
  custom:    'bg-cyan-500/15 text-cyan-400 border-cyan-500/20',
}
const PROVIDER_ICON = {
  openai: '🧠', anthropic: '✨', google: '💎',
  ollama: '🦙', sumopod: '🚀', custom: '🔌',
}

export default function Models() {
  const [models, setModels] = useState([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  const load = () => {
    setLoading(true)
    // Load all available models
    api.listModels()
      .then((r) => {
        setModels(r.models || [])
      })
      .catch(() => setModels([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  if (loading) return <div className="p-6 text-sm text-ink-3 flex items-center gap-2"><RefreshCw size={14} className="animate-spin" /> Memuat model...</div>

  return (
    <div className="p-4 md:p-6 w-full">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-lg font-bold text-ink">Model Manager</h1>
          <p className="text-xs text-ink-3 mt-0.5">{models.length} model terdeteksi</p>
        </div>
        <button onClick={load} className="flex items-center gap-1.5 px-3 py-1.5 border border-border-2 rounded-lg text-xs text-ink-2 hover:text-ink hover:bg-bg-4 transition-colors">
          <RefreshCw size={12} /> Refresh
        </button>
      </div>

      {models.length === 0 ? (
        <div className="bg-bg-3 border-2 border-dashed border-border rounded-xl flex flex-col items-center justify-center p-12 text-center hover:border-accent/40 transition-colors cursor-pointer group" onClick={() => navigate('/integrations')}>
          <span className="text-4xl mb-4">🤖</span>
          <h2 className="text-sm font-semibold text-ink mb-2">Belum ada model aktif terdeteksi</h2>
          <p className="text-xs text-ink-3">
            Sistem tidak mendeteksi model AI apapun. Buka menu <span className="font-semibold text-accent-2 group-hover:text-ink transition-colors">Integrasi</span> untuk mengonfigurasi API provider.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {models.map((m) => (
            <div key={m.id} className="bg-bg-3 border border-border rounded-xl p-4 hover:border-border-2 transition-colors">
              <div className="flex items-start gap-3 mb-3">
                <div className="w-10 h-10 rounded-xl bg-bg-4 flex items-center justify-center text-xl flex-shrink-0">
                  {PROVIDER_ICON[m.provider] || '🤖'}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold text-ink truncate">{m.display}</div>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span className={clsx('text-[10px] px-1.5 py-0.5 rounded font-medium', PROVIDER_COLOR[m.provider] || 'bg-bg-4 text-ink-3')}>
                      {m.provider}
                    </span>
                    <span className={clsx('flex items-center gap-0.5 text-[10px]',
                      m.status === 'online' ? 'text-success' : 'text-ink-3')}>
                      {m.status === 'online'
                        ? <><CheckCircle2 size={10} /> Online</>
                        : <><XCircle size={10} /> Offline</>}
                    </span>
                  </div>
                </div>
              </div>

              <div className="text-[10px] font-mono text-ink-3 bg-bg-4 rounded-lg px-2.5 py-1.5 truncate">
                {m.id}
              </div>

              {m.provider === 'ollama' && (
                <div className="mt-2 text-[10px] text-success">✓ Gratis — berjalan di lokal</div>
              )}
            </div>
          ))}

          {/* Add hint card */}
          <div
            className="bg-bg-3 border-2 border-dashed border-border rounded-xl flex flex-col items-center justify-center p-6 text-center hover:border-accent/40 transition-colors cursor-pointer group"
            onClick={() => navigate('/integrations')}
          >
            <span className="text-2xl mb-2">➕</span>
            <span className="text-xs text-ink-3 group-hover:text-ink transition-colors">Tambah model baru</span>
            <span className="text-[10px] text-accent-2 mt-1">Buka halaman Integrasi →</span>
          </div>
        </div>
      )}

      {/* Ollama guide */}
      <div className="mt-6 bg-bg-3 border border-border rounded-xl p-4">
        <h2 className="text-sm font-semibold text-ink mb-3">🦙 Panduan Ollama (Model Lokal Gratis)</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {[
            { step: '1', title: 'Install Ollama', cmd: 'curl -fsSL https://ollama.ai/install.sh | sh' },
            { step: '2', title: 'Pull Model', cmd: 'ollama pull llama3.1\nollama pull mistral\nollama pull codellama' },
            { step: '3', title: 'Set di .env', cmd: 'OLLAMA_HOST=http://localhost:11434\nOLLAMA_DEFAULT_MODEL=llama3.1' },
          ].map(({ step, title, cmd }) => (
            <div key={step} className="bg-bg-4 rounded-lg p-3">
              <div className="text-xs font-bold text-accent-2 mb-1">Step {step}: {title}</div>
              <pre className="text-[10px] font-mono text-ink-3 whitespace-pre-wrap">{cmd}</pre>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
