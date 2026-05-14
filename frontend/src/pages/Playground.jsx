import { useState } from 'react'
import { api } from '../hooks/useApi'
import { copyToClipboard } from "../utils/clipboard"
import { useModelsStore } from '../store'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Play, Loader2 } from 'lucide-react'
import { useTranslation } from 'react-i18next'

export default function Playground() {
  const { t } = useTranslation()
  const { models } = useModelsStore()
  const [system, setSystem] = useState(t('default_system_prompt'))
  const [prompt, setPrompt] = useState('')
  const [model, setModel] = useState('')
  const [temp, setTemp] = useState(0.7)
  const [maxTokens, setMaxTokens] = useState(2048)
  const [output, setOutput] = useState('')
  const [streaming, setStreaming] = useState(false)

  async function run() {
    if (!prompt.trim() || streaming) return
    setStreaming(true)
    setOutput('')
    const chosenModel = model || models[0]?.id

    let full = ''
    api.chatStream(
      { message: prompt, model: chosenModel, use_rag: false, temperature: temp, max_tokens: maxTokens },
      (chunk) => { full += chunk; setOutput(full) },
      () => setStreaming(false),
      () => {}
    )
  }

  return (
    <div className="p-4 md:p-6 w-full">
      <div className="mb-5">
        <h1 className="text-lg font-semibold text-ink">{t('playground_title')}</h1>
        <p className="text-xs text-ink-3">{t('playground_desc')}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Input */}
        <div className="space-y-3">
          <div>
            <label className="text-xs text-ink-3 mb-1 block">Model</label>
            <select value={model} onChange={(e) => setModel(e.target.value)}
              className="w-full bg-bg-3 border border-border rounded-lg px-3 py-2 text-sm text-ink outline-none">
              {models.map((m) => <option key={m.id} value={m.id}>{m.display}</option>)}
              {models.length === 0 && <option value="">{t('no_active_models')}</option>}
            </select>
          </div>

          <div>
            <label className="text-xs text-ink-3 mb-1 block">{t('system_prompt')}</label>
            <textarea value={system} onChange={(e) => setSystem(e.target.value)} rows={3}
              className="w-full bg-bg-3 border border-border rounded-lg px-3 py-2 text-sm text-ink outline-none focus:border-accent resize-none font-mono text-xs" />
          </div>

          <div>
            <label className="text-xs text-ink-3 mb-1 block">{t('user_message')} *</label>
            <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={5}
              placeholder={t('user_message_placeholder')}
              className="w-full bg-bg-3 border border-border rounded-lg px-3 py-2 text-sm text-ink placeholder-ink-3 outline-none focus:border-accent resize-none" />
          </div>

          {/* Params */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-ink-3 mb-1 block">{t('temperature_label')}: {temp}</label>
              <input type="range" min="0" max="1" step="0.05" value={temp}
                onChange={(e) => setTemp(parseFloat(e.target.value))}
                className="w-full accent-accent" />
            </div>
            <div>
              <label className="text-xs text-ink-3 mb-1 block">{t('max_tokens_label')}: {maxTokens}</label>
              <input type="range" min="256" max="8192" step="256" value={maxTokens}
                onChange={(e) => setMaxTokens(parseInt(e.target.value))}
                className="w-full accent-accent" />
            </div>
          </div>

          <button onClick={run} disabled={!prompt.trim() || streaming || models.length === 0}
            className="w-full flex items-center justify-center gap-2 py-2.5 bg-accent hover:bg-accent/80 disabled:opacity-40 text-white rounded-xl text-sm font-medium transition-colors">
            {streaming ? <><Loader2 size={15} className="animate-spin" /> {t('generating')}</> : <><Play size={15} /> {t('run_label')}</>}
          </button>
        </div>

        {/* Output */}
        <div className="bg-bg-3 border border-border rounded-xl p-4 min-h-64">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-semibold text-ink">{t('output_label')}</h3>
            {output && (
              <button onClick={() => copyToClipboard(output)}
                className="text-xs text-accent-2 hover:underline">{t('copy_label')}</button>
            )}
          </div>
          {!output && !streaming && (
            <div className="text-xs text-ink-3 flex items-center justify-center h-40">
              {t('output_placeholder')}
            </div>
          )}
          {output && (
            <div className="prose prose-sm max-w-none overflow-y-auto max-h-[500px]">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{output}</ReactMarkdown>
              {streaming && <span className="inline-block w-1.5 h-4 bg-accent-2 animate-pulse2 ml-0.5 align-middle" />}
            </div>
          )}
        </div>
      </div>

      {/* Quick prompts */}
      <div className="mt-4">
        <h3 className="text-xs font-semibold text-ink mb-2">🚀 {t('quick_prompts')}</h3>
        <div className="flex flex-wrap gap-2">
          {[
            'Buat fungsi Python untuk sorting array',
            'Ringkas artikel ini menjadi 3 poin utama',
            'Terjemahkan ke Bahasa Inggris: "Selamat pagi, apa kabar?"',
            'Jelaskan perbedaan REST API dan GraphQL',
            'Buat email profesional untuk meminta maaf',
          ].map((p) => (
            <button key={p} onClick={() => setPrompt(p)}
              className="text-xs px-3 py-1.5 bg-bg-4 hover:bg-bg-5 border border-border rounded-lg text-ink-2 hover:text-ink transition-colors">
              {p}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
