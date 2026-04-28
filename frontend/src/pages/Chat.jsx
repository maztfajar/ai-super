import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import { api } from '../hooks/useApi'
import { copyToClipboard } from "../utils/clipboard"
import { useAuthStore, useChatStore, useModelsStore, useOrchestratorStore } from '../store'
import ChannelSelector from '../components/ChannelSelector'
import ProjectLocationPopup from '../components/ProjectLocationPopup'
import toast from 'react-hot-toast'
import { useChatFileHandler } from '../hooks/useChatFileHandler'
import { extractFileContent } from '../utils/fileExtractor'
import {
  Plus, Trash2, Send, Paperclip, Copy, Check, Download,
  Bot, User, Loader2, Square, Sparkles, Zap, FileText, CloudUpload, Menu, X,
  ImagePlus, Mic, MicOff, Camera, Volume2, Brain, ChevronDown, ChevronUp, ChevronRight,
  ExternalLink, FileCode2, Maximize2, Minimize2, PanelRightClose, PanelRightOpen,
  Terminal, BookOpen, PenLine, List, Search, Globe, FilePlus, Trash, MoveRight,
  ClipboardList, AlignLeft, CheckCircle2, Hash, AlertCircle, Wrench, RefreshCw
} from 'lucide-react'
import clsx from 'clsx'


// ── Language color badges ─────────────────────────────────────
const LANG_COLORS = {
  javascript: 'text-yellow-400 bg-yellow-400/10 border-yellow-400/20',
  typescript: 'text-blue-400 bg-blue-400/10 border-blue-400/20',
  python: 'text-blue-300 bg-blue-300/10 border-blue-300/20',
  html: 'text-orange-400 bg-orange-400/10 border-orange-400/20',
  css: 'text-pink-400 bg-pink-400/10 border-pink-400/20',
  sql: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20',
  bash: 'text-green-400 bg-green-400/10 border-green-400/20',
  sh: 'text-green-400 bg-green-400/10 border-green-400/20',
  json: 'text-amber-400 bg-amber-400/10 border-amber-400/20',
  jsx: 'text-cyan-400 bg-cyan-400/10 border-cyan-400/20',
  tsx: 'text-cyan-400 bg-cyan-400/10 border-cyan-400/20',
}

// ── CodeBlock: replaces default ReactMarkdown pre/code renders ─
function CodeBlock({ language, code, onOpenArtifact }) {
  const [copied, setCopied] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false) // Custom state to hide/show code
  const lines = code.split('\n').length
  const isLong = lines > 25
  const langColor = LANG_COLORS[language?.toLowerCase()] || 'text-ink-3 bg-bg-5 border-border'

  const handleCopy = () => {
    copyToClipboard(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="code-block-wrapper relative my-2 rounded-xl overflow-hidden border border-border-2 bg-bg-3">
      {/* Header bar */}
      <div 
        className="flex items-center justify-between px-3 py-1.5 border-b border-border-2 bg-bg-4 cursor-pointer hover:bg-bg-5 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2">
          {isExpanded ? <ChevronDown size={14} className="text-ink-3" /> : <ChevronRight size={14} className="text-ink-3" />}
          <span className={clsx('text-[10px] font-mono font-bold uppercase tracking-widest px-1.5 py-0.5 rounded border', langColor)}>
            {language || 'code'}
          </span>
          {!isExpanded && (
            <span className="text-[10px] text-ink-3">({lines} baris)</span>
          )}
        </div>
        <div className="flex items-center gap-1" onClick={e => e.stopPropagation()}>
          {isLong && onOpenArtifact && (
            <button
              onClick={() => onOpenArtifact(code, language || 'txt')}
              className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] transition-all border border-transparent hover:border-accent/20"
              style={{ color: 'var(--accent-2)' }}
              title="Buka di Artifacts Panel"
            >
              <ExternalLink size={9} />
              <span>Artifacts</span>
            </button>
          )}
          <button
            onClick={handleCopy}
            className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] transition-all border border-transparent hover:border-border-2"
            style={{ color: copied ? 'var(--success)' : '#6e7681' }}
            title="Copy kode"
          >
            {copied ? <Check size={9} /> : <Copy size={9} />}
            <span>{copied ? 'Copied!' : 'Copy'}</span>
          </button>
        </div>
      </div>
      {/* Code content — automatically adapts to light/dark themes via CSS vars */}
      {isExpanded && (
        <pre className="p-4 text-[12.5px] overflow-x-auto leading-relaxed font-mono text-ink-2 bg-transparent m-0 border-none">
          <code className="text-inherit bg-transparent p-0">{code}</code>
        </pre>
      )}
    </div>
  )
}

// ── ProcessStepsPanel: Live structured thinking toggle ────────
const ACTION_META = {
  Thinking:   { icon: Brain,         color: 'text-purple-400',  bg: 'bg-purple-400/10' },
  Thought:    { icon: Brain,         color: 'text-purple-400',  bg: 'bg-purple-400/10' },
  Planned:    { icon: ClipboardList, color: 'text-blue-400',    bg: 'bg-blue-400/10'   },
  Worked:     { icon: Wrench,        color: 'text-emerald-400', bg: 'bg-emerald-400/10'},
  Explored:   { icon: RefreshCw,     color: 'text-cyan-400',    bg: 'bg-cyan-400/10'   },
  Ran:        { icon: Terminal,      color: 'text-green-400',   bg: 'bg-green-400/10'  },
  Edited:     { icon: PenLine,       color: 'text-yellow-400',  bg: 'bg-yellow-400/10' },
  Modify:     { icon: PenLine,       color: 'text-yellow-400',  bg: 'bg-yellow-400/10' },
  Analyzed:   { icon: Brain,         color: 'text-indigo-400',  bg: 'bg-indigo-400/10' },
  Reading:    { icon: BookOpen,      color: 'text-sky-400',     bg: 'bg-sky-400/10'    },
  Writing:    { icon: PenLine,       color: 'text-amber-400',   bg: 'bg-amber-400/10'  },
  Written:    { icon: FileCode2,     color: 'text-emerald-300', bg: 'bg-emerald-300/10'},
  Listed:     { icon: List,          color: 'text-teal-400',    bg: 'bg-teal-400/10'   },
  Searched:   { icon: Search,        color: 'text-violet-400',  bg: 'bg-violet-400/10' },
  Fetched:    { icon: Globe,         color: 'text-blue-300',    bg: 'bg-blue-300/10'   },
  Created:    { icon: FilePlus,      color: 'text-emerald-400', bg: 'bg-emerald-400/10'},
  Deleted:    { icon: Trash,         color: 'text-red-400',     bg: 'bg-red-400/10'    },
  Moved:      { icon: MoveRight,     color: 'text-orange-400',  bg: 'bg-orange-400/10' },
  Copied:     { icon: Copy,          color: 'text-orange-300',  bg: 'bg-orange-300/10' },
  Summarized: { icon: AlignLeft,     color: 'text-pink-400',    bg: 'bg-pink-400/10'   },
  Checked:    { icon: CheckCircle2,  color: 'text-emerald-300', bg: 'bg-emerald-300/10'},
  Found:      { icon: Hash,          color: 'text-cyan-300',    bg: 'bg-cyan-300/10'   },
  Error:      { icon: AlertCircle,   color: 'text-red-400',     bg: 'bg-red-400/10'    },
  Done:       { icon: CheckCircle2,  color: 'text-emerald-400', bg: 'bg-emerald-400/10'},
}
const DEFAULT_META = { icon: Zap, color: 'text-ink-3', bg: 'bg-bg-5' }

const ProcessStepsPanel = React.memo(function ProcessStepsPanel({ steps, isStreaming, onStop, streamingText, onOpenArtifactCard }) {
  const [open, setOpen] = useState(true)
  const [expandedIdx, setExpandedIdx] = useState(null)
  const [staleSeconds, setStaleSeconds] = useState(0)
  const staleCountRef = useRef(steps.length)

  // Fix 4: useCallback dengan dependency array kosong — tidak re-create setiap render
  const toggleStep = useCallback((i, e) => {
    e.stopPropagation()   // Fix 2: cegah event bubble ke parent
    e.preventDefault()    // Fix 2: cegah default behavior
    setExpandedIdx(prev => prev === i ? null : i) // functional update, aman dari stale closure
  }, []) // empty deps — setExpandedIdx dari useState selalu stabil

  useEffect(() => {
    if (!isStreaming) { setStaleSeconds(0); return }
    if (steps.length !== staleCountRef.current) {
      staleCountRef.current = steps.length
      setStaleSeconds(0)
      return
    }
    const timer = setInterval(() => setStaleSeconds(s => s + 1), 1000)
    return () => clearInterval(timer)
  }, [steps.length, isStreaming])

  if (!steps || steps.length === 0) return null

  const latest = steps[steps.length - 1]
  const meta = ACTION_META[latest?.action] || DEFAULT_META
  const LatestIcon = meta.icon

  // Ambil konten yang bisa ditampilkan untuk setiap step
  const getStepContent = (step, stepIdx) => {
    const isLastStep = stepIdx === steps.length - 1
    // Live streaming untuk step terakhir
    if (isLastStep && isStreaming && step._textOffset != null && streamingText) {
      const live = streamingText.substring(step._textOffset)
      if (live.trim()) return { content: live, isLive: true }
    }
    // Field konten dengan prioritas
    const content = step.liveContent || step.code || step.result
    if (content && content.trim()) return { content: content.trim(), isLive: false }
    return null
  }

  return (
    <div
      className="flex gap-2.5 mb-2 animate-fade"
    >
      <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-accent to-accent-2 flex items-center justify-center flex-shrink-0 mt-0.5">
        <Bot size={13} className="text-white" />
      </div>

      <div className="flex-1 max-w-[90%]">
        {/* Header utama */}
        <button
          onClick={(e) => {
            e.stopPropagation()  // Fix 2: cegah bubble ke parent
            e.preventDefault()
            setOpen(o => !o)
          }}
          className="w-full flex items-center justify-between px-3 py-2 bg-bg-4 border border-border rounded-xl rounded-tl-sm hover:bg-bg-5 transition-all"
        >
          <div className="flex items-center gap-2 min-w-0">
            {isStreaming ? (
              <div className="flex gap-0.5 flex-shrink-0">
                {[0,1,2].map(i => (
                  <span key={i} className="w-1.5 h-1.5 rounded-full bg-accent-2 animate-pulse"
                    style={{ animationDelay: `${i * 0.18}s` }} />
                ))}
              </div>
            ) : (
              <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-emerald-400/15 text-emerald-400 border border-emerald-400/20 flex-shrink-0">
                ✓ Selesai
              </span>
            )}
            <div className={clsx('flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium flex-shrink-0', meta.bg, meta.color)}>
              <LatestIcon size={10} />
              <span>{latest?.action}</span>
            </div>
            {latest?.detail && (
              <span className="text-[11px] text-ink-3 truncate">{latest.detail}</span>
            )}
          </div>
          <div className="flex items-center gap-2 flex-shrink-0 ml-2">
            <span className="text-[10px] text-ink-3 tabular-nums">
              {steps.length} step{steps.length !== 1 ? 's' : ''}
            </span>
            {open ? <ChevronUp size={13} className="text-ink-3" /> : <ChevronDown size={13} className="text-ink-3" />}
          </div>
        </button>

        {/* Daftar steps */}
        {open && (
          <div className="mt-1.5 border border-border bg-bg-3 rounded-xl rounded-tl-sm overflow-hidden">
            <div className="max-h-[500px] overflow-y-auto divide-y divide-border/40">
              {steps.map((step, i) => {
                const m = ACTION_META[step.action] || DEFAULT_META
                const Icon = m.icon
                const isLast = i === steps.length - 1
                const isExpanded = expandedIdx === i
                const contentData = getStepContent(step, i)
                // Semua step bisa diklik — yang tidak punya konten rich tampilkan info minimal
                const displayContent = contentData?.content ||
                  `Action: ${step.action}\nDetail: ${step.detail || '—'}\nTimestamp: ${new Date(step.ts || Date.now()).toLocaleTimeString('id-ID')}`

                return (
                  <div key={i}>
                    {/* Step row */}
                    <button
                      className={clsx(
                        'w-full flex items-center gap-2.5 px-3 py-2.5 text-[11px] transition-colors text-left group',
                        isLast && isStreaming ? 'bg-accent/5' : 'hover:bg-bg-4',
                        isExpanded ? 'bg-bg-4' : ''
                      )}
                      onClick={(e) => toggleStep(i, e)}  // Fix 2: kirim event ke toggleStep
                    >
                      <span className="text-[9px] text-ink-3 tabular-nums w-5 text-right flex-shrink-0 font-mono">
                        {i + 1}
                      </span>

                      {isLast && isStreaming && (
                        <span className="w-1.5 h-1.5 rounded-full bg-accent-2 animate-pulse flex-shrink-0" />
                      )}

                      <div className={clsx('flex items-center gap-1 px-1.5 py-0.5 rounded-full flex-shrink-0', m.bg, m.color)}>
                        <Icon size={9} />
                        <span className="font-semibold text-[10px]">{step.action}</span>
                      </div>

                      <span className={clsx(
                        'truncate flex-1 min-w-0 text-[11px]',
                        isLast && isStreaming ? 'text-ink font-medium' : 'text-ink-3'
                      )}>
                        {step.detail || '—'}
                      </span>

                      {step.count != null && (
                        <span className="tabular-nums text-[10px] font-mono px-1.5 py-0.5 rounded bg-bg-5 text-ink-3 border border-border flex-shrink-0">
                          {step.count}
                        </span>
                      )}

                      {/* Selalu tampilkan chevron di setiap step */}
                      <span className={clsx(
                        'flex-shrink-0 transition-transform duration-200 opacity-0 group-hover:opacity-100',
                        isExpanded ? 'opacity-100 rotate-180' : ''
                      )}>
                        <ChevronDown size={11} className="text-ink-3" />
                      </span>
                    </button>

                    {/* Expandable content */}
                    {isExpanded && (
                      <div className="bg-bg-2 border-b border-border/40">
                        <div className="flex items-center justify-between px-3 py-1.5 bg-bg-3 border-b border-border/30">
                          <div className="flex items-center gap-2">
                            <Icon size={9} className={m.color} />
                            <span className="text-[10px] text-ink-3 font-medium">
                              {step.action === 'Thinking' ? '💭 Proses Berpikir' :
                               step.action === 'Analyzed' ? '🔍 Hasil Analisis' :
                               step.action === 'Planned'  ? '📋 Rencana Eksekusi' :
                               step.action === 'Worked'   ? '⚡ Eksekusi Sub-tasks' :
                               step.action === 'Written'  ? `📄 ${step.detail?.split('/').pop()}` :
                               step.action === 'Ran'      ? '💻 Output Terminal' :
                               step.action === 'Reading'  ? `📖 ${step.detail}` :
                               step.action === 'Searched' ? `🔍 Hasil: ${step.detail}` :
                               step.detail || step.action}
                            </span>
                            {step.language && (
                              <span className={clsx(
                                'text-[9px] font-mono font-bold uppercase px-1.5 py-0.5 rounded border',
                                LANG_COLORS[step.language?.toLowerCase()] || 'text-ink-3 bg-bg-5 border-border'
                              )}>
                                {step.language}
                              </span>
                            )}
                            {contentData?.isLive && (
                              <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-accent/10 text-accent-2 border border-accent/20 animate-pulse">
                                ● live
                              </span>
                            )}
                          </div>
                          <button
                            onClick={(e) => {
                              e.stopPropagation()   // Fix 2
                              e.preventDefault()
                              copyToClipboard(displayContent)
                            }}
                            className="p-1 rounded hover:bg-bg-5 transition-colors"
                            title="Copy"
                          >
                            <Copy size={10} className="text-ink-3" />
                          </button>
                        </div>

                        <pre className="text-[11px] leading-relaxed font-mono p-3 whitespace-pre-wrap overflow-x-auto text-ink-2 max-h-72 overflow-y-auto">
                          {displayContent}
                          {contentData?.isLive && (
                            <span className="inline-block w-1 h-3 bg-accent-2 animate-pulse ml-0.5 align-middle" />
                          )}
                        </pre>

                        {/* Tombol buka di Artifacts untuk file Written */}
                        {step.action === 'Written' && step.code && onOpenArtifactCard && (
                          <div className="px-3 py-2 border-t border-border/30 bg-bg-3 flex justify-between items-center">
                            <span className="text-[10px] text-ink-3">{step.detail}</span>
                            <button
                              onClick={(e) => {
                                e.stopPropagation()  // Fix 2
                                e.preventDefault()
                                const ext = (step.language || step.detail?.split('.').pop() || 'txt').toLowerCase()
                                onOpenArtifactCard(step.code, ext, `✍️ ${step.detail?.split('/').pop()}`, false)
                              }}
                              className="flex items-center gap-1 text-[10px] px-2 py-1 rounded-lg bg-accent/10 hover:bg-accent/20 border border-accent/20 text-accent-2 transition-all"
                            >
                              <ExternalLink size={9} /> Buka di Artifacts
                            </button>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>

            {/* Footer */}
            {isStreaming && staleSeconds >= 8 && (
              <div className="px-3 py-2 border-t border-border/40 bg-amber-400/5 flex items-center gap-2">
                <Loader2 size={10} className="animate-spin text-amber-400 flex-shrink-0" />
                <span className="text-[11px] text-amber-400">
                  Masih memproses... ({staleSeconds}s) — AI menunggu hasil tool
                </span>
              </div>
            )}
            {isStreaming && onStop && (
              <div className="px-3 py-2 border-t border-border">
                <button
                  data-allow-propagation="true"
                  onClick={(e) => { e.stopPropagation(); onStop() }}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-danger/10 hover:bg-danger/20 border border-danger/25 text-danger text-[11px] font-medium transition-all"
                >
                  <Square size={10} fill="currentColor" /> Hentikan
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
})

// ── ArtifactsPanel: slideout panel di sebelah kanan ───────────
function ArtifactsPanel({ code, language, title, isPreviewUrl, onClose }) {
  const isAppPreview = isPreviewUrl || language === 'preview'
  const isHtml = ['html', 'htm', 'svg'].includes((language || '').toLowerCase())

  const [activeTab, setActiveTab] = useState(isAppPreview || isHtml ? 'preview' : 'code')
  const [copied, setCopied] = useState(false)
  const [localCode, setLocalCode] = useState(code)
  const [iframeKey, setIframeKey] = useState(0)  // force reload
  const [appOnline, setAppOnline] = useState(true)

  useEffect(() => { setLocalCode(code) }, [code])

  const filename  = `artifact.${language || 'txt'}`
  const iframeSrc = isAppPreview
    ? localCode   // code IS the URL for app previews
    : isHtml
      ? `data:text/html;charset=utf-8,${encodeURIComponent(localCode)}`
      : null

  const handleCopy = () => {
    copyToClipboard(isAppPreview ? localCode : localCode)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleDownload = () => {
    if (isAppPreview) { window.open(localCode, '_blank'); return }
    const blob = new Blob([localCode], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = filename; a.click()
    URL.revokeObjectURL(url)
  }

  const langColor = LANG_COLORS[(language || '').toLowerCase()] || 'text-ink-3 bg-bg-5 border-border'
  const lines     = isAppPreview ? 0 : localCode.split('\n').length

  return (
    <div className="flex flex-col border-l border-border bg-bg-2 animate-slide-in-right" style={{ width: '48%', flexShrink: 0 }}>
      {/* Header */}
      <div className="h-12 border-b border-border flex items-center px-3 gap-2 flex-shrink-0 bg-bg-3">
        {isAppPreview
          ? <span className="text-base flex-shrink-0">🚀</span>
          : <FileCode2 size={14} className="text-accent-2 flex-shrink-0" />}
        <span className="text-xs font-medium text-ink truncate flex-1">{title || filename}</span>

        {/* Running indicator for app previews */}
        {isAppPreview && (
          <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-success/15 border border-success/25 text-success text-[10px] font-semibold flex-shrink-0">
            <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
            Running
          </span>
        )}

        {!isAppPreview && (
          <>
            <span className={clsx('text-[10px] font-mono font-bold px-1.5 py-0.5 rounded border flex-shrink-0', langColor)}>
              {language || 'txt'}
            </span>
            <span className="text-[10px] text-ink-3 flex-shrink-0">{lines} baris</span>
          </>
        )}

        <div className="flex items-center gap-0.5 flex-shrink-0">
          {/* Reload — for app previews */}
          {isAppPreview && (
            <button
              onClick={() => setIframeKey(k => k + 1)}
              className="p-1.5 rounded-lg hover:bg-bg-4 transition-colors"
              title="Reload aplikasi"
            >
              <RefreshCw size={13} className="text-ink-3" />
            </button>
          )}
          {/* Open in new tab — for app previews */}
          {isAppPreview && (
            <button
              onClick={() => window.open(localCode, '_blank')}
              className="p-1.5 rounded-lg hover:bg-bg-4 transition-colors"
              title="Buka di tab baru"
            >
              <ExternalLink size={13} className="text-ink-3" />
            </button>
          )}
          <button
            onClick={handleCopy}
            className="p-1.5 rounded-lg hover:bg-bg-4 transition-colors"
            title={isAppPreview ? 'Copy URL' : 'Copy semua'}
          >
            {copied ? <Check size={13} className="text-success" /> : <Copy size={13} className="text-ink-3" />}
          </button>
          {!isAppPreview && (
            <button
              onClick={handleDownload}
              className="p-1.5 rounded-lg hover:bg-bg-4 transition-colors"
              title={`Download ${filename}`}
            >
              <Download size={13} className="text-ink-3" />
            </button>
          )}
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-danger/10 hover:text-danger transition-colors"
            title="Tutup panel"
          >
            <X size={13} className="text-ink-3" />
          </button>
        </div>
      </div>

      {/* URL bar for app previews */}
      {isAppPreview && (
        <div className="flex items-center gap-2 px-3 py-1.5 border-b border-border bg-bg-3 flex-shrink-0">
          <span className="text-[10px] text-ink-3 flex-shrink-0">URL:</span>
          <span className="flex-1 text-[11px] font-mono text-accent-2 truncate">{localCode}</span>
          <button
            onClick={() => window.open(localCode, '_blank')}
            className="flex items-center gap-1 px-2 py-0.5 rounded-md bg-accent/10 hover:bg-accent/20 border border-accent/20 text-accent-2 text-[10px] font-medium transition-all flex-shrink-0"
          >
            <ExternalLink size={9} /> Buka
          </button>
        </div>
      )}

      {/* Tabs — for HTML/SVG code artifacts */}
      {isHtml && !isAppPreview && (
        <div className="flex border-b border-border flex-shrink-0">
          {['preview', 'code'].map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={clsx(
                'flex-1 py-2 text-xs font-medium capitalize transition-colors',
                activeTab === tab
                  ? 'text-accent-2 border-b-2 border-accent-2 bg-accent/5'
                  : 'text-ink-3 hover:text-ink hover:bg-bg-3'
              )}
            >
              {tab === 'preview' ? '👁 Preview' : '{ } Code'}
            </button>
          ))}
        </div>
      )}

      {/* Content */}
      {(isAppPreview || (isHtml && activeTab === 'preview')) && iframeSrc ? (
        <iframe
          key={iframeKey}
          src={iframeSrc}
          className="flex-1 w-full"
          style={{ background: 'white', border: 'none' }}
          sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-popups-to-escape-sandbox allow-modals"
          title="App Preview"
          onError={() => setAppOnline(false)}
        />
      ) : (
        <div className="flex-1 overflow-auto flex flex-col">
          <textarea
            value={localCode}
            onChange={(e) => setLocalCode(e.target.value)}
            className="flex-1 w-full p-4 font-mono text-[12.5px] leading-relaxed text-ink-2 bg-transparent border-none resize-none focus:outline-none focus:ring-0"
            spellCheck="false"
            style={{ minHeight: '100%' }}
          />
        </div>
      )}
    </div>
  )
}

// ── SaveFileDialog: dialog untuk simpan file ke server ────────
function SaveFileDialog({ filename, content, onClose }) {
  const [directory, setDirectory] = useState('')
  const [dirs, setDirs] = useState([])
  const [currentPath, setCurrentPath] = useState('')
  const [parentPath, setParentPath] = useState('')
  const [customFilename, setCustomFilename] = useState(filename || 'output.txt')
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(true)

  // Load initial directory
  useEffect(() => {
    loadDirs('~')
  }, [])

  async function loadDirs(path) {
    setLoading(true)
    try {
      const result = await api.listDirectories(path)
      setDirs(result.directories || [])
      setCurrentPath(result.path || path)
      setParentPath(result.parent || '')
      setDirectory(result.path || path)
    } catch (e) {
      toast.error('Gagal memuat direktori')
    }
    setLoading(false)
  }

  async function handleSave() {
    if (!directory) return toast.error('Pilih direktori tujuan')
    setSaving(true)
    try {
      const result = await api.saveFile(directory, customFilename, content)
      toast.success(`✅ Tersimpan: ${result.path}`, { duration: 4000 })
      onClose()
    } catch (e) {
      toast.error(e.message || 'Gagal menyimpan file')
    }
    setSaving(false)
  }

  // Also support client-side download as fallback
  function handleDownload() {
    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = customFilename; a.click()
    URL.revokeObjectURL(url)
    toast.success('📥 File di-download ke browser')
    onClose()
  }

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fade"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <div className="bg-bg-2 border border-border rounded-2xl w-[500px] max-w-[90vw] max-h-[80vh] flex flex-col shadow-2xl animate-slide-in-up">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <div className="flex items-center gap-2">
            <Download size={18} className="text-accent-2" />
            <span className="text-sm font-semibold text-ink">Simpan File</span>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-bg-4 transition-colors">
            <X size={16} className="text-ink-3" />
          </button>
        </div>

        {/* Filename */}
        <div className="px-5 py-3 border-b border-border/50">
          <label className="text-[11px] text-ink-3 uppercase tracking-wider font-medium mb-1.5 block">Nama File</label>
          <input
            value={customFilename}
            onChange={e => setCustomFilename(e.target.value)}
            className="w-full px-3 py-2 bg-bg-3 border border-border rounded-lg text-sm text-ink font-mono focus:outline-none focus:border-accent"
          />
        </div>

        {/* Directory Browser */}
        <div className="px-5 py-3 flex-1 overflow-hidden flex flex-col">
          <label className="text-[11px] text-ink-3 uppercase tracking-wider font-medium mb-1.5 block">Direktori Tujuan</label>
          
          {/* Current path */}
          <div className="flex items-center gap-1.5 mb-2">
            <div className="flex-1 px-3 py-1.5 bg-bg-3 border border-border rounded-lg text-xs text-ink font-mono truncate">
              📁 {currentPath || '~'}
            </div>
            {parentPath && (
              <button
                onClick={() => loadDirs(parentPath)}
                className="px-2 py-1.5 bg-bg-4 border border-border rounded-lg text-xs text-ink-3 hover:text-ink hover:bg-bg-5 transition-colors flex-shrink-0"
                title="Naik ke folder induk"
              >
                ⬆️
              </button>
            )}
          </div>

          {/* Directory list */}
          <div className="flex-1 overflow-y-auto border border-border rounded-lg bg-bg-3 min-h-[140px] max-h-[200px]">
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 size={18} className="animate-spin text-accent-2" />
              </div>
            ) : dirs.length === 0 ? (
              <div className="text-center text-xs text-ink-3 py-8">Tidak ada subdirektori</div>
            ) : (
              dirs.map((d, i) => (
                <button
                  key={i}
                  onClick={() => loadDirs(d.path)}
                  className="w-full flex items-center gap-2 px-3 py-2 text-left text-xs hover:bg-accent/10 transition-colors border-b border-border/30 last:border-b-0"
                >
                  <span className="text-amber-400">📂</span>
                  <span className="text-ink truncate">{d.name}</span>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between px-5 py-4 border-t border-border gap-2">
          <button
            onClick={handleDownload}
            className="px-3 py-2 text-xs font-medium rounded-lg bg-bg-4 border border-border text-ink-2 hover:bg-bg-5 hover:text-ink transition-all flex items-center gap-1.5"
          >
            <Download size={13} /> Download
          </button>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="px-4 py-2 text-xs font-medium rounded-lg bg-bg-4 border border-border text-ink-3 hover:text-ink transition-colors"
            >
              Batal
            </button>
            <button
              onClick={handleSave}
              disabled={saving || !directory}
              className="px-4 py-2 text-xs font-semibold rounded-lg bg-accent text-white hover:bg-accent/80 transition-colors disabled:opacity-40 flex items-center gap-1.5"
            >
              {saving ? <Loader2 size={13} className="animate-spin" /> : <Check size={13} />}
              Simpan ke Server
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Parse %%SAVE_FILE%% marker from AI response ───────────────
function parseSaveFileMarker(content) {
  if (!content) return null
  const markerStart = content.indexOf('%%SAVE_FILE%%')
  const markerEnd = content.indexOf('%%END_SAVE%%')
  if (markerStart === -1 || markerEnd === -1) return null

  const block = content.substring(markerStart + '%%SAVE_FILE%%'.length, markerEnd).trim()
  const lines = block.split('\n')
  let filename = 'output.txt'
  let saveContent = ''
  let contentStarted = false

  for (const line of lines) {
    if (!contentStarted && line.trim().toLowerCase().startsWith('filename:')) {
      filename = line.trim().substring('filename:'.length).trim()
    } else if (!contentStarted && line.trim().toLowerCase().startsWith('content:')) {
      contentStarted = true
      const firstLine = line.trim().substring('content:'.length).trim()
      if (firstLine) saveContent += firstLine + '\n'
    } else if (contentStarted) {
      saveContent += line + '\n'
    }
  }

  return { filename, content: saveContent.trimEnd() }
}

// ── Strip %%SAVE_FILE%% markers from display content ──────────
function stripSaveMarkers(content) {
  if (!content) return content
  return content.replace(/%%SAVE_FILE%%[\s\S]*?%%END_SAVE%%/g, '').trim()
}

// ── Parse %%ARTIFACT%% markers OR auto-detect large code blocks ─
function parseArtifacts(content) {
  if (!content) return { artifacts: [], cleanContent: content }
  const artifacts = []
  let cleanContent = content

  // 1. Explicit markers: %%ARTIFACT%% title:... language:... \n code \n %%END_ARTIFACT%%
  const markerRegex = /%%ARTIFACT%%([\s\S]*?)%%END_ARTIFACT%%/g
  let match
  let markerIndex = 0
  while ((match = markerRegex.exec(content)) !== null) {
    const block = match[1].trim()
    const lines = block.split('\n')
    let title = `Artifact ${markerIndex + 1}`
    let language = 'txt'
    let codeStartIdx = 0

    for (let i = 0; i < Math.min(lines.length, 5); i++) {
      const line = lines[i].trim()
      if (line.toLowerCase().startsWith('title:')) {
        title = line.substring('title:'.length).trim()
        codeStartIdx = i + 1
      } else if (line.toLowerCase().startsWith('language:') || line.toLowerCase().startsWith('lang:')) {
        language = line.substring(line.indexOf(':') + 1).trim().toLowerCase()
        codeStartIdx = i + 1
      } else if (line.toLowerCase().startsWith('type:')) {
        // type: code | html | document | svg
        const t = line.substring('type:'.length).trim().toLowerCase()
        if (['html', 'svg'].includes(t)) language = t
        codeStartIdx = i + 1
      } else {
        break
      }
    }

    const code = lines.slice(codeStartIdx).join('\n').trim()
    if (code) {
      artifacts.push({ id: `art-${Date.now()}-${markerIndex}`, title, language, code })
      markerIndex++
    }
  }

  // 1.5. Parse %%APP_PREVIEW%% url %%END_PREVIEW%%
  const previewRegex = /%%APP_PREVIEW%%\s*(https?:\/\/[^\s]+)\s*%%END_PREVIEW%%/g
  let previewMatch
  while ((previewMatch = previewRegex.exec(content)) !== null) {
    const url = previewMatch[1].trim()
    artifacts.push({ id: `preview-${Date.now()}-${markerIndex}`, title: 'App Preview', language: 'preview', code: url, isPreviewUrl: true })
    markerIndex++
  }

  // Remove markers from display
  cleanContent = cleanContent.replace(/%%ARTIFACT%%[\s\S]*?%%END_ARTIFACT%%/g, '')
                             .replace(/%%APP_PREVIEW%%[\s\S]*?%%END_PREVIEW%%/g, '').trim()

  // 2. Auto-detect large fenced code blocks (```lang\n...```) with >15 lines
  if (artifacts.length === 0) {
    const codeBlockRegex = /```(\w+)?\n([\s\S]*?)```/g
    let codeMatch
    let autoIndex = 0
    while ((codeMatch = codeBlockRegex.exec(content)) !== null) {
      const lang = codeMatch[1] || 'txt'
      const code = codeMatch[2].trim()
      const lineCount = code.split('\n').length
      if (lineCount >= 15) {
        // Determine a smart title
        let title = `${lang.toUpperCase()} Code`
        if (['html', 'htm'].includes(lang.toLowerCase())) title = 'Web Page'
        else if (lang.toLowerCase() === 'svg') title = 'SVG Graphic'
        else if (['jsx', 'tsx'].includes(lang.toLowerCase())) title = 'React Component'
        else if (lang.toLowerCase() === 'python') title = 'Python Script'
        else if (lang.toLowerCase() === 'javascript') title = 'JavaScript'
        else if (lang.toLowerCase() === 'css') title = 'Stylesheet'
        else if (lang.toLowerCase() === 'sql') title = 'SQL Query'

        artifacts.push({ id: `auto-${Date.now()}-${autoIndex}`, title, language: lang, code })
        autoIndex++
      }
    }
    // For auto-detected, we keep the code blocks in cleanContent (they render via CodeBlock too)
  }

  return { artifacts, cleanContent }
}

// ── Strip artifact markers from display content ───────────────
function stripArtifactMarkers(content) {
  if (!content) return content
  return content.replace(/%%ARTIFACT%%[\s\S]*?%%END_ARTIFACT%%/g, '').trim()
}

// ── ARTIFACT TYPES — icons & color mapping ────────────────────
const ARTIFACT_TYPE_META = {
  html:       { icon: Globe,     label: 'Web Page',        color: 'text-orange-400', bg: 'bg-orange-400/10', border: 'border-orange-400/20' },
  htm:        { icon: Globe,     label: 'Web Page',        color: 'text-orange-400', bg: 'bg-orange-400/10', border: 'border-orange-400/20' },
  svg:        { icon: Globe,     label: 'SVG Graphic',     color: 'text-pink-400',   bg: 'bg-pink-400/10',   border: 'border-pink-400/20' },
  jsx:        { icon: FileCode2, label: 'React Component', color: 'text-cyan-400',   bg: 'bg-cyan-400/10',   border: 'border-cyan-400/20' },
  tsx:        { icon: FileCode2, label: 'React Component', color: 'text-cyan-400',   bg: 'bg-cyan-400/10',   border: 'border-cyan-400/20' },
  javascript: { icon: FileCode2, label: 'JavaScript',     color: 'text-yellow-400', bg: 'bg-yellow-400/10', border: 'border-yellow-400/20' },
  typescript: { icon: FileCode2, label: 'TypeScript',     color: 'text-blue-400',   bg: 'bg-blue-400/10',   border: 'border-blue-400/20' },
  python:     { icon: FileCode2, label: 'Python Script',  color: 'text-blue-300',   bg: 'bg-blue-300/10',   border: 'border-blue-300/20' },
  css:        { icon: FileCode2, label: 'Stylesheet',     color: 'text-pink-400',   bg: 'bg-pink-400/10',   border: 'border-pink-400/20' },
  sql:        { icon: FileCode2, label: 'SQL Query',      color: 'text-emerald-400',bg: 'bg-emerald-400/10',border: 'border-emerald-400/20' },
  json:       { icon: FileCode2, label: 'JSON Data',      color: 'text-amber-400',  bg: 'bg-amber-400/10',  border: 'border-amber-400/20' },
  bash:       { icon: Terminal,  label: 'Shell Script',   color: 'text-green-400',  bg: 'bg-green-400/10',  border: 'border-green-400/20' },
  sh:         { icon: Terminal,  label: 'Shell Script',   color: 'text-green-400',  bg: 'bg-green-400/10',  border: 'border-green-400/20' },
  markdown:   { icon: BookOpen,  label: 'Document',       color: 'text-violet-400', bg: 'bg-violet-400/10', border: 'border-violet-400/20' },
  md:         { icon: BookOpen,  label: 'Document',       color: 'text-violet-400', bg: 'bg-violet-400/10', border: 'border-violet-400/20' },
}
const DEFAULT_ARTIFACT_META = { icon: FileCode2, label: 'Code', color: 'text-accent-2', bg: 'bg-accent/10', border: 'border-accent/20' }

// ── ArtifactCard: inline card di dalam pesan ──────────────────
function ArtifactCard({ artifact, onOpen }) {
  const [copied, setCopied] = useState(false)
  const meta = ARTIFACT_TYPE_META[artifact.language?.toLowerCase()] || DEFAULT_ARTIFACT_META
  const ArtIcon = meta.icon
  const lines = artifact.code.split('\n')
  const previewLines = lines.slice(0, 6).join('\n')
  const isPreviewable = ['html', 'htm', 'svg'].includes((artifact.language || '').toLowerCase())

  const handleCopy = (e) => {
    e.stopPropagation()
    copyToClipboard(artifact.code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleDownload = (e) => {
    e.stopPropagation()
    const blob = new Blob([artifact.code], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${artifact.title.replace(/\s+/g, '_').toLowerCase()}.${artifact.language || 'txt'}`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div
      className="artifact-card my-3 cursor-pointer animate-slide-in-up hover:animate-artifact-glow"
      onClick={() => onOpen(artifact)}
    >
      {/* Header */}
      <div className="artifact-card-header">
        <div className={clsx('w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0', meta.bg)}>
          <ArtIcon size={14} className={meta.color} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-xs font-semibold text-ink truncate">{artifact.title}</div>
          <div className="flex items-center gap-2 mt-0.5">
            <span className={clsx('text-[9px] font-mono font-bold uppercase tracking-widest px-1.5 py-0.5 rounded border', meta.bg, meta.color, meta.border)}>
              {artifact.language || 'txt'}
            </span>
            <span className="text-[10px] text-ink-3">{lines.length} baris</span>
            {isPreviewable && (
              <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-success/10 text-success border border-success/20 font-medium">
                ✦ Live Preview
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={handleCopy}
            className="p-1.5 rounded-lg hover:bg-bg-5 transition-colors"
            title="Copy"
          >
            {copied ? <Check size={12} className="text-success" /> : <Copy size={12} className="text-ink-3" />}
          </button>
          <button
            onClick={handleDownload}
            className="p-1.5 rounded-lg hover:bg-bg-5 transition-colors"
            title="Download"
          >
            <Download size={12} className="text-ink-3" />
          </button>
        </div>
      </div>

      {/* Preview */}
      <div className="artifact-card-preview">
        <code>{previewLines}</code>
      </div>

      {/* Footer / Open button */}
      <div className="artifact-card-actions">
        <button
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent/10 hover:bg-accent/20 border border-accent/20 text-accent-2 text-[11px] font-medium transition-all flex-1 justify-center"
          onClick={(e) => { e.stopPropagation(); onOpen(artifact) }}
        >
          <Maximize2 size={11} />
          Buka & Edit di Panel
        </button>
      </div>
    </div>
  )
}


// ── Message bubble ────────────────────────────────────────────
function Bubble({ msg, isStreaming, onStop, onExport, onSpeak, speakingId, onOpenArtifact, onOpenArtifactCard }) {
  const [copied, setCopied] = useState(false)
  const [showThinking, setShowThinking] = useState(false) // Default: collapsed
  const [showSaveDialog, setShowSaveDialog] = useState(false)
  const isUser = msg.role === 'user'

  // Detect %%SAVE_FILE%% marker
  const saveFileData = !isUser ? parseSaveFileMarker(msg.content) : null
  // Helper: Split content into main text and thinking process
  const splitContent = (content) => {
    let processedContent = stripSaveMarkers(content || '')
    
    // Auto-unwrap Sumopod API JSON wrapper if present
    try {
      const cleanJson = processedContent.replace(/^```json\s*/i, '').replace(/\s*```$/, '').trim()
      if (cleanJson.startsWith('{') && cleanJson.endsWith('}')) {
        const parsed = JSON.parse(cleanJson)
        if (parsed.response && parsed.model_used) {
          processedContent = parsed.response;
        }
      }
    } catch(e) {
      // Ignore if not valid JSON
    }

    if (!processedContent) return { mainContent: '', thinkingContent: null, hasThinking: false }
    
    // Find the thinking section: starts with 🤔 Proses Berpikir:
    const thinkStart = processedContent.indexOf('🤔 Proses Berpikir:')
    
    if (thinkStart === -1) {
      return { mainContent: processedContent, thinkingContent: null, hasThinking: false }
    }
    
    // Get everything before the thinking section (main content before thinking)
    const beforeThink = processedContent.substring(0, thinkStart).trim()
    
    // Get the thinking section content (after the header)
    let thinkEnd = processedContent.length
    const afterThinkStart = thinkStart + '🤔 Proses Berpikir:'.length
    
    // Find where thinking ends - backend sends `---` to mark the end
    const remaining = processedContent.substring(afterThinkStart)
    const endMarkerIndex = remaining.indexOf('---')
    
    let thinkingContent = ''
    let mainContentAfterThink = ''
    
    if (endMarkerIndex !== -1) {
      thinkingContent = remaining.substring(0, endMarkerIndex).trim()
      mainContentAfterThink = remaining.substring(endMarkerIndex + 3).trim()
    } else {
      // Fallback heuristic if --- is not found (e.g., legacy messages or streaming cutoffs)
      const lines = remaining.split('\n')
      let thinkLineEnd = lines.length
      let foundThinkEnd = false
      
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i]
        const trimmed = line.trim()
        
        // Check if this line marks the end of thinking (actual response)
        const isResponseStart = (
          trimmed &&
          !trimmed.startsWith('Plan') &&
          !trimmed.startsWith('Tool') &&
          !trimmed.startsWith('Action') &&
          !trimmed.startsWith('Thought') &&
          !trimmed.startsWith('Analysis') &&
          !trimmed.startsWith('Step') &&
          !trimmed.startsWith('-') &&
          !trimmed.startsWith('•') &&
          !trimmed.match(/^[A-Z][a-z]+:/) && // Not a label like "Key: value"
          (trimmed.startsWith('I\'') || trimmed.startsWith('The ') || trimmed.startsWith('Here') || 
           trimmed.startsWith('Let') || trimmed.startsWith('I will') || trimmed.startsWith('Sure') ||
           /^(Okay|Alright|Got it|Understood|Yes|No|Great|Perfect|Baik|Oke|Tentu|Saya|Ini|Berikut|Sebagai|Data|Hasil)/i.test(trimmed))
        )
        
        if (isResponseStart && i > 0) {
          thinkLineEnd = i
          foundThinkEnd = true
          break
        }
      }
      
      thinkingContent = lines.slice(0, thinkLineEnd).join('\n').trim()
      if (foundThinkEnd) {
        mainContentAfterThink = lines.slice(thinkLineEnd).join('\n').trim()
      }
    }
    
    let mainContent = beforeThink
    if (mainContentAfterThink) {
      mainContent = (beforeThink ? beforeThink + '\n\n' : '') + mainContentAfterThink
    }
    
    return { mainContent: mainContent.trim(), thinkingContent, hasThinking: true }
  }

  const { mainContent, thinkingContent, hasThinking } = splitContent(msg.content || '')

  // ── Parse artifacts from mainContent (explicit markers + auto-detect large code blocks)
  const { artifacts: parsedArtifacts, cleanContent: artifactCleanContent } = !isUser
    ? parseArtifacts(mainContent)
    : { artifacts: [], cleanContent: mainContent }
  // Use cleanContent for markdown render when explicit %%ARTIFACT%% markers were found
  const hasExplicitArtifacts = parsedArtifacts.length > 0 && (mainContent || '').includes('%%ARTIFACT%%')
  const displayContent = hasExplicitArtifacts ? artifactCleanContent : mainContent

  const copy = () => {
    copyToClipboard(msg.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // Custom ReactMarkdown components — code block dengan copy & artifacts + link handler
  const markdownComponents = {
    code({ node, inline, className, children, ...props }) {
      const match = /language-(\w+)/.exec(className || '')
      const language = match ? match[1] : ''
      const codeText = String(children).replace(/\n$/, '')
      if (inline) {
        return (
          <code
            className="px-1 py-0.5 bg-accent/10 rounded text-accent-2 text-[11px] font-mono border border-accent/20"
            {...props}
          >{children}</code>
        )
      }
      return <CodeBlock language={language} code={codeText} onOpenArtifact={onOpenArtifact} />
    },
    // Custom link renderer: buka di tab baru + styling yang jelas
    a({ node, href, children, ...props }) {
      const isLocalServer = href && (
        href.includes('localhost') ||
        href.includes('127.0.0.1') ||
        href.includes('0.0.0.0') ||
        /:\d{4,5}/.test(href)
      )
      return (
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          className="text-accent-2 underline underline-offset-2 hover:text-accent transition-colors"
          title={isLocalServer ? `Buka ${href} di tab baru` : href}
          {...props}
        >
          {children}
          {isLocalServer && (
            <ExternalLink size={10} className="inline ml-0.5 mb-0.5 opacity-70" />
          )}
        </a>
      )
    }
  }

  return (
    <div className={clsx('flex gap-2.5 group animate-fade', isUser ? 'flex-row-reverse' : 'flex-row')}>
      {/* Avatar */}
      <div className={clsx(
        'w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5',
        isUser
          ? 'bg-gradient-to-br from-accent to-pink'
          : 'bg-gradient-to-br from-accent to-accent-2'
      )}>
        {isUser
          ? <User size={13} className="text-white" />
          : <Bot size={13} className="text-white" />}
      </div>

      <div className={clsx('max-w-[78%] flex flex-col', isUser ? 'items-end' : 'items-start')}>
        <div className={clsx(
          'px-3.5 py-2.5 rounded-xl text-sm relative',
          isUser
            ? 'bg-accent text-white rounded-tr-sm'
            : 'bg-bg-4 border border-border text-ink rounded-tl-sm'
        )}>
          {/* Tampilkan gambar jika ada */}
          {isUser && msg._image_preview && (
            <img
              src={msg._image_preview}
              alt="Gambar yang dikirim"
              className="max-w-[200px] max-h-[150px] rounded-lg mb-2 object-cover border border-white/20"
            />
          )}
          {isUser ? (
            <div className="flex flex-col gap-2">
              {msg.attachedFiles?.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mb-1">
                  {msg.attachedFiles.map((f) => (
                    <span key={f.id} className="flex items-center gap-1 px-2 py-0.5 rounded-md bg-white/20 text-white text-[10px] border border-white/30 backdrop-blur-sm">
                      <span className="flex-shrink-0">{f.meta?.icon || '📄'}</span>
                      <span className="truncate max-w-[100px]">{f.name}</span>
                    </span>
                  ))}
                </div>
              )}
              <p className="whitespace-pre-wrap leading-relaxed">{msg.original_content || msg.content}</p>
            </div>
          ) : (
            <div className="prose prose-sm max-w-none">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeRaw]}
                components={markdownComponents}
              >{displayContent}</ReactMarkdown>
              {isStreaming && (
                <span className="inline-block w-1.5 h-4 bg-accent-2 animate-pulse2 ml-0.5 align-middle" />
              )}
              
              {/* Collapsible Thinking Section */}
              {hasThinking && (
                <div className="mt-3 border border-border-2 rounded-lg overflow-hidden">
                  <button
                    onClick={() => setShowThinking(!showThinking)}
                    className="w-full flex items-center justify-between px-3 py-2 bg-bg-3 hover:bg-bg-5 transition-colors text-xs text-ink-3"
                  >
                    <span className="flex items-center gap-1.5">
                      <Brain size={12} className="text-accent" />
                      🤔 Proses Berpikir
                    </span>
                    {showThinking ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </button>
                  {showThinking && (
                    <div className="px-3 py-2 bg-bg-2 text-[11px] text-ink-3 leading-relaxed max-h-48 overflow-y-auto">
                      {thinkingContent.split('\n').map((line, i) => line.trim() && (
                        <div key={i} className="flex gap-2 py-0.5">
                          <span className="text-accent flex-shrink-0">•</span>
                          <span className="flex-1">{line.trim()}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* ── Inline Artifact Cards ── */}
              {parsedArtifacts.length > 0 && !isStreaming && parsedArtifacts.map(art => (
                <ArtifactCard
                  key={art.id}
                  artifact={art}
                  onOpen={(artifact) => {
                    if (onOpenArtifactCard) {
                      onOpenArtifactCard(artifact.code, artifact.language, artifact.title, artifact.isPreviewUrl)
                    } else if (onOpenArtifact) {
                      onOpenArtifact(artifact.code, artifact.language)
                    }
                  }}
                />
              ))}
            </div>
          )}
        </div>

        {/* Save File Button — appears when AI includes %%SAVE_FILE%% marker */}
        {saveFileData && !isStreaming && (
          <button
            onClick={() => setShowSaveDialog(true)}
            className="mt-2 flex items-center gap-2 px-3 py-2 rounded-lg bg-gradient-to-r from-accent/20 to-accent-2/20 border border-accent/30 text-accent-2 text-xs font-semibold hover:from-accent/30 hover:to-accent-2/30 transition-all group"
          >
            <Download size={14} className="group-hover:animate-bounce" />
            💾 Simpan File: <span className="font-mono text-[11px] text-ink">{saveFileData.filename}</span>
          </button>
        )}

        {/* SaveFileDialog portal */}
        {showSaveDialog && saveFileData && (
          <SaveFileDialog
            filename={saveFileData.filename}
            content={saveFileData.content}
            onClose={() => setShowSaveDialog(false)}
          />
        )}
        {/* Action row */}
        <div className="flex items-center gap-2 mt-1 px-1">
          <span className="text-[10px] text-ink-3 opacity-0 group-hover:opacity-100 transition-opacity">
            {new Date(msg.created_at || Date.now()).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' })}
          </span>
          {!isUser && msg.model && (
            <span className="text-[10px] font-mono text-ink-3 opacity-0 group-hover:opacity-100 transition-opacity">
              {msg.model?.split('/').pop()}
            </span>
          )}
          {/* Stop button — hanya saat streaming */}
          {isStreaming && onStop && (
            <button
              onClick={onStop}
              className="flex items-center gap-1 px-2 py-0.5 rounded-md bg-danger/15 hover:bg-danger/25 border border-danger/30 text-danger text-[10px] font-medium transition-all"
              title="Hentikan (Esc)"
            >
              <Square size={9} fill="currentColor" /> Stop
            </button>
          )}
          {!isUser && !isStreaming && (
            <div className="flex items-center gap-1 relative">
              {/* Drive Upload */}
              <button
                onClick={() => onDriveUpload(msg)}
                className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-bg-5 transition-all outline-none"
                title="Simpan ke Google Drive"
              >
                <CloudUpload size={11} className="text-accent" />
              </button>

              {/* Export Dropdown */}
              <div className="relative dropdown-container">
                <button
                  onClick={(e) => {
                    const el = e.currentTarget.nextElementSibling;
                    const isHidden = el.style.display === 'none' || el.style.display === '';
                    // Close all other dropdowns
                    document.querySelectorAll('.export-dropdown').forEach(d => d.style.display = 'none');
                    if (isHidden) el.style.display = 'block';
                  }}
                  className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-bg-5 transition-all outline-none"
                  title="Download Chat (PDF/Word/Excel)"
                >
                  <Download size={11} className="text-accent-2" />
                </button>
                <div 
                  className="export-dropdown absolute right-0 bottom-full mb-1 w-36 bg-bg-2 border border-border shadow-md rounded-lg overflow-hidden z-50 text-[11px] animate-fade"
                  style={{ display: 'none' }}
                >
                  <div className="px-2.5 py-1.5 text-[9px] font-semibold text-ink-3 tracking-wider bg-bg-3 border-b border-border uppercase">Export Format</div>
                  <button 
                    onClick={() => { document.querySelectorAll('.export-dropdown').forEach(d => d.style.display = 'none'); onExport("pdf", msg.id) }} 
                    className="w-full text-left px-3 py-2 text-ink hover:bg-bg-4 hover:text-accent transition-colors flex items-center gap-2"
                  >
                    <span>📄</span> PDF Document
                  </button>
                  <button 
                    onClick={() => { document.querySelectorAll('.export-dropdown').forEach(d => d.style.display = 'none'); onExport("docx", msg.id) }} 
                    className="w-full text-left px-3 py-2 text-ink hover:bg-bg-4 hover:text-accent transition-colors flex items-center gap-2"
                  >
                    <span>📝</span> Word (DOCX)
                  </button>
                  <button 
                    onClick={() => { document.querySelectorAll('.export-dropdown').forEach(d => d.style.display = 'none'); onExport("xlsx", msg.id) }} 
                    className="w-full text-left px-3 py-2 text-ink hover:bg-bg-4 hover:text-accent transition-colors flex items-center gap-2 border-b border-border/50"
                  >
                    <span>📊</span> Excel (XLSX)
                  </button>
                  <button 
                    onClick={() => { document.querySelectorAll('.export-dropdown').forEach(d => d.style.display = 'none'); onExport("txt", msg.id) }} 
                    className="w-full text-left px-3 py-2 text-ink hover:bg-bg-4 hover:text-accent transition-colors flex items-center gap-2"
                  >
                    <span>📜</span> Plain Text
                  </button>
                </div>
              </div>

              {/* TTS Listen */}
              {!isUser && (
                <button
                  onClick={() => onSpeak(msg)}
                  className={clsx(
                    "opacity-0 group-hover:opacity-100 p-0.5 rounded transition-all outline-none",
                    speakingId === msg.id ? "bg-accent/20 text-accent opacity-100" : "hover:bg-bg-5 text-ink-3 hover:text-ink"
                  )}
                  title="Dengarkan (TTS)"
                >
                  <Volume2 size={11} className={speakingId === msg.id ? "animate-pulse" : ""} />
                </button>
              )}

              {/* Thinking Toggle - show if embedded thinking exists in content */}
              {!isUser && hasThinking && (
                <button
                  onClick={() => setShowThinking(!showThinking)}
                  className={clsx(
                    "opacity-0 group-hover:opacity-100 p-0.5 rounded transition-all outline-none",
                    showThinking ? "bg-accent/20 text-accent opacity-100" : "hover:bg-bg-5 text-ink-3 hover:text-ink"
                  )}
                  title="Tampilkan Thinking"
                >
                  <Brain size={11} />
                </button>
              )}

              {/* Copy */}
              <button
                onClick={copy}
                className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-bg-5 transition-all outline-none"
                title="Copy ke clipboard"
              >
                {copied
                  ? <Check size={10} className="text-success" />
                  : <Copy size={10} className="text-ink-3" />}
              </button>
            </div>
          )}
        </div>

        {/* RAG sources */}
        {!isUser && msg.rag_sources && (() => {
          try {
            const src = JSON.parse(msg.rag_sources)
            if (src.length > 0) return (
              <div className="mt-1 flex flex-wrap gap-1">
                {src.map((s, i) => (
                  <span key={i} className="text-[10px] px-1.5 py-0.5 bg-success/10 text-success border border-success/20 rounded-full">
                    📄 {s}
                  </span>
                ))}
              </div>
            )
          } catch { }
          return null
        })()}

      </div>
    </div>
  )
}

// ── Komponen FileChip ────────────────────────────────────────────────────────
function FileChip({ file, onRemove }) {
  return (
    <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-bg-4 border border-border-2 text-[11px] animate-fade">
      <span className="flex-shrink-0">{file.meta?.icon || '📄'}</span>
      <span className="truncate max-w-[120px] text-ink">{file.name}</span>
      <span className="text-ink-3 text-[9px]">({(file.size / 1024).toFixed(1)} KB)</span>
      <button 
        onClick={() => onRemove(file.id)}
        className="ml-1 p-0.5 rounded-full hover:bg-danger/10 hover:text-danger text-ink-3 transition-colors"
      >
        <X size={10} />
      </button>
    </div>
  );
}

// ── Komponen DragOverlay ─────────────────────────────────────────────────────
function DragOverlay({ isVisible }) {
  if (!isVisible) return null;
  return (
    <div className="absolute inset-0 z-50 flex items-center justify-center bg-bg-2/80 backdrop-blur-sm border-2 border-dashed border-accent m-4 rounded-2xl animate-fade">
      <div className="flex flex-col items-center p-6 bg-bg-3 border border-accent/20 rounded-xl shadow-2xl">
        <div className="text-4xl mb-2 animate-bounce">📂</div>
        <p className="text-sm font-bold text-ink">Lepaskan file di sini</p>
        <p className="text-xs text-ink-3 mt-1 text-center">
          PDF, DOCX, XLSX, CSV, TXT, Gambar
        </p>
      </div>
    </div>
  );
}

// ── Session item ──────────────────────────────────────────────
function SessionItem({ session, active, onClick, onDelete }) {
  return (
    <div
      onClick={onClick}
      className={clsx(
        'group flex items-center gap-2 px-2.5 py-2 rounded-lg cursor-pointer mb-0.5 transition-all',
        active ? 'bg-accent/10 border border-accent/20' : 'hover:bg-bg-4'
      )}
    >
      <div className="flex-1 min-w-0">
        <div className={clsx('text-xs truncate', active ? 'text-accent-2 font-medium' : 'text-ink-2')}>
          {session.title || 'New Chat'}
        </div>
        <div className="text-[10px] text-ink-3 mt-0.5">
          {session.model_used?.split('/').pop() || 'AI'} ·{' '}
          {new Date(session.updated_at || session.created_at).toLocaleDateString('id-ID', { day: 'numeric', month: 'short' })}
        </div>
      </div>
      <button
        onClick={(e) => { e.stopPropagation(); onDelete(session.id) }}
        className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-danger/10 flex-shrink-0"
      >
        <Trash2 size={11} className="text-danger" />
      </button>
    </div>
  )
}

// ── Main Chat Page ────────────────────────────────────────────
export default function Chat() {
  const { id: urlSessionId } = useParams()
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const { models } = useModelsStore()

  // Global state
  const appName = useOrchestratorStore(s => s.appName)
  const selectedOrchestrator = useOrchestratorStore(s => s.selectedOrchestrator)
  const connectedChannels = useOrchestratorStore(s => s.connectedChannels)
  const selectedChannel = useOrchestratorStore(s => s.selectedChannel)
  const { 
    activeModel, activeCapability, setActiveModel, setActiveCapability, clearActiveRouting,
    drivePromptContent, drivePromptTitle, setDrivePromptContent, clearDrivePrompt 
  } = useOrchestratorStore()

  const {
    sessions, setSessions,
    currentSession, setCurrentSession,
    messages, setMessages, addMessage,
    clearMessages,
    streaming, setStreaming,
    streamingText, appendStreamingText, clearStreaming,
    processSteps, setProcessSteps, addProcessStep,
    lastProcessSteps, finalizeProcessSteps, clearProcessSteps,
    statusText, setStatusText,
    actualModel, setActualModel,
    abortRequest, setAbortRequest,
  } = useChatStore()

  const input = useChatStore(s => s.draftInput)
  const setInput = useChatStore(s => s.setDraftInput)
  const [useRAG, setUseRAG] = useState(false)
  const [loadingMsgs, setLoadingMsgs] = useState(false)
  const [speakingId, setSpeakingId] = useState(null)
  const audioRef = useRef(null)

  // Derived: Filter sessions by currently selected channel
  const channelType = connectedChannels.find(c => c.id === selectedChannel)?.type || 'web'
  const filteredSessions = sessions.filter(s => {
    const sType = s.platform || 'web'
    // Relaxed matching: web and null/empty are treated as the same
    if (channelType === 'web') return !sType || sType === 'web'
    return sType === channelType
  })

  // ── TTS Logic ──
  const handleSpeak = useCallback((msg) => {
    if (speakingId === msg.id) {
       if (audioRef.current) {
         audioRef.current.pause()
         audioRef.current = null
       }
       setSpeakingId(null)
       return
    }

    if (audioRef.current) {
      audioRef.current.pause()
    }

    setSpeakingId(msg.id)
    const url = api.getTTSUrl(msg.content)
    const audio = new Audio(url)
    audioRef.current = audio
    audio.play().catch(err => {
      console.error("TTS Play Error", err)
      toast.error("Gagal memutar suara")
      setSpeakingId(null)
    })
    audio.onended = () => setSpeakingId(null)
  }, [speakingId])

  const [pendingConfirmation, setPendingConfirmation] = useState(null)

  const [sidebarOpen, setSidebarOpen] = useState(false)
  // Artifacts Panel state
  const [artifact, setArtifact] = useState({ open: false, code: '', language: '', title: '' })
  
  // Auto-hide process panel setelah streaming selesai
  const [showLastSteps, setShowLastSteps] = useState(false)
  const [fadingOut, setFadingOut] = useState(false)
  const hideStepsTimerRef = useRef(null)

  const openArtifact = useCallback((code, language) => {
    setArtifact({ open: true, code, language, title: '' })
  }, [])
  const openArtifactCard = useCallback((code, language, title, isPreviewUrl = false) => {
    setArtifact({ open: true, code, language, title: title || '', isPreviewUrl })
  }, [])
  const closeArtifact = useCallback(() => {
    setArtifact(a => ({ ...a, open: false }))
  }, [])
  // Project Location Popup state
  const [projectLocationPopup, setProjectLocationPopup] = useState({ open: false, sessionId: null })
  const openProjectLocationPopup = useCallback((sessionId) => {
    setProjectLocationPopup({ open: true, sessionId })
  }, [])
  const closeProjectLocationPopup = useCallback(() => {
    setProjectLocationPopup({ open: false, sessionId: null })
  }, [])
  // Multimodal state
  const [pendingImage, setPendingImage] = useState(null)  // { base64, mime_type, preview }
  const [isRecording, setIsRecording] = useState(false)
  const [isTranscribing, setIsTranscribing] = useState(false)
  
  // Drag and drop attachment handler
  const {
    attachedFiles,
    isDragOver,
    fileError,
    addFiles,
    removeFile,
    clearFiles,
    dragHandlers,
  } = useChatFileHandler()

  // Deletion guard: set of session IDs sedang dalam proses hapus
  // Mencegah polling 5 detik mengembalikan sesi yang baru dihapus
  const deletingIdsRef = useRef(new Set())
  const mediaRecorderRef = useRef(null)
  const imagePickerRef = useRef(null)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)
  const fileInputRef = useRef(null) // Untuk RAG
  const chatContextFileRef = useRef(null) // Untuk lampiran chat context (non-RAG)
  const scrollBottom = useCallback(() => {

    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => { scrollBottom() }, [messages, streamingText])

  // Watchdog dihapus sesuai permintaan: proses jangan berhenti kecuali pengguna menekan tombol berhenti

  // Load models + sessions
  useEffect(() => {
    api.listSessions().then(s => {
      const currentSessions = useChatStore.getState().sessions
      setSessions((currentSessions.length > 0 && s.length === 0) ? currentSessions : s)
    }).catch(() => { })
    api.listModels().then(() => {
      // Re-fetch sessions after models loaded (titles may have been updated)
      api.listSessions().then((s) => {
        // Filter out any sessions currently being deleted
        const safe = s.filter(x => !deletingIdsRef.current.has(x.id))
        const currentSessions = useChatStore.getState().sessions
        setSessions((currentSessions.length > 0 && safe.length === 0) ? currentSessions : safe)
      }).catch(() => { })
    }).catch(() => { })
  }, [])

  // Auto-redirect /chat → /chat/:id
  // Kasus 1: Ada currentSession di store (sudah login sebelumnya di domain ini)
  // Kasus 2: Tidak ada currentSession (fresh login, misal dari tunnel URL) →
  //          redirect ke sesi terbaru dari database agar langsung muncul tanpa perlu
  //          klik sesi secara manual
  useEffect(() => {
    if (!urlSessionId && currentSession?.id) {
      // Sudah ada sesi aktif di store → langsung pakai
      navigate(`/chat/${currentSession.id}`, { replace: true })
    } else if (!urlSessionId && !currentSession?.id && sessions.length > 0) {
      // Tidak ada sesi aktif (fresh login / domain baru) → pakai sesi terbaru dari DB
      navigate(`/chat/${sessions[0].id}`, { replace: true })
    }
  }, [urlSessionId, currentSession?.id, sessions])

  // Load session from URL — robust version
  // Jika messages sudah ada di store untuk sesi yang sama → jangan fetch ulang (navigasi kembali)
  // Jika tidak ada (pindah menu, reload) → langsung fetch dari API pakai urlSessionId
  useEffect(() => {
    if (!urlSessionId) return

    const storeMessages = useChatStore.getState().messages
    const storeSession  = useChatStore.getState().currentSession
    const isStreaming   = useChatStore.getState().streaming

    // 1. Sudah ada messages untuk sesi ini → tidak perlu fetch ulang
    if (storeSession?.id === urlSessionId && storeMessages.length > 0) return
    // 2. Sedang streaming → jangan ganggu
    if (isStreaming) return

    // 3. Coba cari di sessions list kalau sudah ada
    const s = sessions.find((x) => x.id === urlSessionId)
    if (s) {
      loadSession(s)
      return
    }

    // 4. Sessions list belum dimuat, tapi kita punya urlSessionId → fetch langsung dari API
    // Ini yang terjadi saat pindah menu → kembali ke /chat/:id
    ;(async () => {
      setLoadingMsgs(true)
      try {
        const msgs = await api.getMessages(urlSessionId)
        // Jangan override jika streaming sudah aktif saat ini
        if (useChatStore.getState().streaming) return
        // Set currentSession — gunakan data yang sudah ada di store kalau cocok
        const existingSession = useChatStore.getState().currentSession
        if (!existingSession || existingSession.id !== urlSessionId) {
          // Cari dari sessions list yang mungkin sudah ada
          const found = useChatStore.getState().sessions.find(x => x.id === urlSessionId)
          useChatStore.getState().setCurrentSession(
            found || { id: urlSessionId, title: 'Chat', platform: channelType }
          )
        }
        useChatStore.getState().setMessages(msgs || [])
      } catch {
        // Jika gagal fetch, tidak masalah — biarkan kosong
      } finally {
        setLoadingMsgs(false)
      }
    })()
  }, [urlSessionId, sessions])

  async function loadSession(session) {
    // Skip if already displaying this session with messages (e.g. returning from another menu)
    const storeMessages = useChatStore.getState().messages
    const storeSession  = useChatStore.getState().currentSession
    // Guard: jangan ganggu saat streaming aktif
    if (useChatStore.getState().streaming) return
    if (storeSession?.id === session.id && storeMessages.length > 0) {
      // Just make sure currentSession is set correctly, messages already in store
      setCurrentSession(session)
      return
    }
    setCurrentSession(session)
    clearMessages()
    setLoadingMsgs(true)
    try {
      const msgs = await api.getMessages(session.id)
      setMessages(msgs)
    } catch { toast.error('Gagal memuat pesan') }
    finally { setLoadingMsgs(false) }
  }

  // ── Real-time sync: poll for new messages every 5s ───────
  // Enables cross-channel sync (Telegram/WhatsApp → Web)
  // Pauses automatically when tab is not visible (Page Visibility API)
  useEffect(() => {
    if (!currentSession?.id) return
    const POLL_INTERVAL = 5000

    const pollNewMessages = async () => {
      // Jangan poll saat tab tidak aktif — hemat bandwidth & server resource
      if (document.visibilityState === 'hidden') return
      // Don't poll while streaming — we already get our own messages
      if (useChatStore.getState().streaming) return

      const currentMsgs = useChatStore.getState().messages
      if (currentMsgs.length === 0) return

      // Get timestamp of latest known message
      const lastMsg = currentMsgs[currentMsgs.length - 1]
      const afterTs = lastMsg?.created_at || ''
      if (!afterTs) return

      try {
        const newMsgs = await api.getNewMessages(currentSession.id, afterTs)
        if (newMsgs && newMsgs.length > 0) {
          // Merge: only add messages with IDs we don't already have
          const existingIds = new Set(currentMsgs.map(m => m.id))
          const existingContents = new Set(currentMsgs.map(m => m.content))
          const uniqueNew = newMsgs.filter(m => !existingIds.has(m.id) && !existingContents.has(m.content))
          if (uniqueNew.length > 0) {
            const merged = [...currentMsgs, ...uniqueNew]
            useChatStore.getState().setMessages(merged)
            // Refresh session list — but filter out sessions being deleted
            api.listSessions().then((s) => {
              const safe = s.filter(x => !deletingIdsRef.current.has(x.id))
              const currentSessions = useChatStore.getState().sessions
              setSessions((currentSessions.length > 0 && safe.length === 0) ? currentSessions : safe)
            }).catch(() => {})
          }
        }
      } catch {
        // Silent fail — polling is best-effort
      }
    }

    // Poll saat tab kembali aktif setelah lama di background
    const onVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        pollNewMessages()
      }
    }
    document.addEventListener('visibilitychange', onVisibilityChange)

    const interval = setInterval(pollNewMessages, POLL_INTERVAL)
    return () => {
      clearInterval(interval)
      document.removeEventListener('visibilitychange', onVisibilityChange)
    }
  }, [currentSession?.id])

  // Cek apakah sesi aktif masih kosong (belum ada pesan)
  const isCurrentSessionEmpty = currentSession && messages.length === 0

  async function newSession() {
    // Jika sesi aktif masih kosong, jangan buat sesi baru
    if (isCurrentSessionEmpty) {
      toast('Sesi ini masih kosong. Mulai chat dulu!', { icon: '💬', duration: 2000 })
      inputRef.current?.focus()
      return
    }
    try {
      const s = await api.createSession('New Chat')
      const updated = await api.listSessions()
      setSessions(updated)
      setCurrentSession(s)
      setMessages([])
      navigate(`/chat/${s.id}`)
    } catch { toast.error('Gagal membuat sesi baru') }
  }

  // Auto-reset when changing channel
  // Hanya navigate ke sesi pertama di channel baru — JANGAN buat sesi baru otomatis
  // (mencegah loop: channel mismatch → newSession → clearMessages → chat hilang)
  useEffect(() => {
    if (!currentSession?.id) return
    // Hanya lakukan auto-switch jika platform BENAR-BENAR berbeda dan sudah ada di DB
    // (bukan stub minimal yang dibuat path-4)
    if (currentSession.platform && currentSession.platform !== channelType) {
      if (filteredSessions.length > 0) {
        navigate(`/chat/${filteredSessions[0].id}`)
      }
      // Jika tidak ada sesi di channel ini, biarkan saja — jangan buat sesi baru otomatis
    }
  }, [channelType])

  async function deleteSession(id) {
    // 1. Tandai sebagai sedang dihapus (cegah polling mengembalikannya)
    deletingIdsRef.current.add(id)

    // 2. Optimistic removal — hapus dari UI sebelum API response
    const prevSessions = useChatStore.getState().sessions
    const filtered = prevSessions.filter(s => s.id !== id)
    setSessions(filtered)

    // Jika session yang dihapus adalah session aktif, clear dan navigate
    const wasActive = currentSession?.id === id
    if (wasActive) {
      setCurrentSession(null)
      clearMessages()
      navigate('/chat')
    }

    try {
      await api.deleteSession(id)
      // Setelah berhasil, refresh dari server untuk memastikan konsistensi
      const updated = await api.listSessions()
      // Tetap filter: jangan tampilkan yang sedang dihapus
      const safe = updated.filter(s => !deletingIdsRef.current.has(s.id))
      setSessions(safe)
      toast.success('Chat dihapus', { duration: 1500 })
    } catch (err) {
      // Rollback jika gagal
      deletingIdsRef.current.delete(id)
      setSessions(prevSessions) // kembalikan state sebelumnya
      if (wasActive) {
        setCurrentSession(prevSessions.find(s => s.id === id) || null)
      }
      // Pesan error yang lebih informatif
      const status = err?.status || err?.response?.status
      if (status === 404) {
        // Session sudah tidak ada — anggap berhasil dihapus
        deletingIdsRef.current.add(id)
        setSessions(filtered)
        if (wasActive) { setCurrentSession(null); setMessages([]) }
        return
      } else if (status === 401 || status === 403) {
        toast.error('Tidak punya akses untuk menghapus sesi ini')
      } else if (!navigator.onLine) {
        toast.error('Tidak ada koneksi internet. Chat akan dihapus saat online kembali.')
      } else {
        toast.error('Gagal menghapus chat. Silakan coba lagi.')
      }
    } finally {
      // Setelah 10 detik, unlock dari guard agar tidak leak
      setTimeout(() => deletingIdsRef.current.delete(id), 10000)
    }
  }

  // ── STOP streaming ────────────────────────────────────────
  function stopStreaming() {
    const abortFn = useChatStore.getState().abortRequest
    if (abortFn && typeof abortFn === 'function') {
      abortFn()
      useChatStore.getState().setAbortRequest(null)
    }
    const partial = useChatStore.getState().streamingText
    if (partial.trim()) {
      addMessage({
        id: Date.now() + 1,
        role: 'assistant',
        content: partial + '\n\n*[Dihentikan oleh pengguna]*',
        model: selectedOrchestrator,
        created_at: new Date().toISOString(),
      })
    }
    clearStreaming()
    setStatusText('')
    useChatStore.getState().finalizeProcessSteps()  // Keep steps visible after stop
    
    // Auto-hide timer
    setShowLastSteps(true)
    if (hideStepsTimerRef.current) clearTimeout(hideStepsTimerRef.current)
    hideStepsTimerRef.current = setTimeout(() => {
      setFadingOut(true)
      setTimeout(() => {
        setShowLastSteps(false)
        setFadingOut(false)
      }, 400)
    }, 7600)

    toast('⏹ Respons dihentikan', { icon: '⏹', duration: 1500 })
  }

  // ── SEND message ─────────────────────────────────────────
  async function sendMessage() {
    const text = input.trim()
    let imageToSend = pendingImage
    if (!text && !imageToSend && attachedFiles.length === 0) return
    if (!currentSession) { await newSession(); return }

    // If agent is currently streaming, interrupt it first then send new message
    // This allows the user to answer agent questions mid-stream
    if (streaming) {
      const abortFn = useChatStore.getState().abortRequest
      if (abortFn && typeof abortFn === 'function') {
        abortFn()
        useChatStore.getState().setAbortRequest(null)
      }
      const partial = useChatStore.getState().streamingText
      if (partial.trim()) {
        addMessage({
          id: Date.now() - 1,
          role: 'assistant',
          content: partial,
          model: useChatStore.getState().actualModel || selectedOrchestrator,
          created_at: new Date().toISOString(),
        })
      }
      clearStreaming()
      useChatStore.getState().setStatusText('')
      useChatStore.getState().finalizeProcessSteps()
      // Small delay to let state settle before sending new message
      await new Promise(r => setTimeout(r, 80))
    }

    clearActiveRouting()
    clearDrivePrompt()

    // Proses attached files
    const currentFiles = [...attachedFiles]
    clearFiles()
    let combinedText = text

    if (currentFiles.length > 0) {
      toast.loading("Mengekstrak file...", { id: "extract-file" })
      for (const file of currentFiles) {
        try {
          const extracted = await extractFileContent(file)
          if (extracted.type === 'image' && !imageToSend) {
            imageToSend = {
               base64: extracted.base64,
               mime_type: extracted.mime_type,
               preview: extracted.dataUrl,
               filename: extracted.name
            }
          } else if (extracted.type === 'text') {
            combinedText += `\n\n[FILE: ${extracted.name}]\n${extracted.text}\n[/FILE]`
          } else if (extracted.type === 'error') {
            combinedText += `\n\n[ERROR MEMBACA FILE: ${extracted.name}]\n${extracted.text}`
          }
        } catch(err) {
           combinedText += `\n\n[ERROR MEMBACA FILE: ${file.name}]\n${err.message}`
        }
      }
      toast.dismiss("extract-file")
    }

    // Check if user wants to create an application/project
    const isAppCreation = /buat|create|bikin|develop|make|build/i.test(text) && 
                           (/aplik|apliaksi|application|web|website|project|proyek|sistem|system|app/i.test(text) ||
                            /react|vue|angular|node|python|php|javascript|typescript/i.test(text))

    const sessionId = currentSession?.id || `new-${Date.now()}`
    if (isAppCreation) {
      let hasLocation = false
      if (currentSession?.id) {
        try {
          const projectLocation = await api.getProjectLocation(currentSession.id)
          if (projectLocation && projectLocation.project_path) {
            hasLocation = true
          }
        } catch (error) {
          console.log('Project location not set or session not found')
        }
      }
      
      if (!hasLocation) {
        openProjectLocationPopup(currentSession.id)
        return // Return early. The text stays in the input so the user can just press Enter again.
      }
    }

    setInput('')
    setActualModel(null)
    useChatStore.getState().setActualModel(null)
    // Reset textarea height
    if (inputRef.current) inputRef.current.style.height = 'auto'

    const tempUserMsg = {
      id: Date.now(),
      role: 'user',
      content: combinedText,
      original_content: text,
      attachedFiles: currentFiles,
      model: selectedOrchestrator,
      created_at: new Date().toISOString(),
      _image_preview: imageToSend?.preview || pendingImage?.preview || null,
    }
    addMessage(tempUserMsg)

    setPendingImage(null)  // clear preview
    setStreaming(true)
    useChatStore.getState().setStatusText('')
    clearProcessSteps()  // Reset process steps for new task
    // Reset watchdog (dihapus)

    // Helper: add structured process step from onProcess SSE event.
    // If event has code payload (Written action), also auto-opens artifact panel.
    const handleAddProcessStep = (data) => {
      console.log(`Step "${data.action}" hasContent:`, !!(data.code || data.result), 'data:', data)
      const currentOffset = useChatStore.getState().streamingText.length
      const steps = useChatStore.getState().processSteps

      // Finalize liveContent untuk step sebelumnya
      if (steps.length > 0) {
        const lastStep = steps[steps.length - 1]
        if (lastStep._textOffset != null && lastStep.liveContent == null) {
          const endContent = useChatStore.getState().streamingText.substring(lastStep._textOffset)
          const updatedSteps = steps.map((s, i) =>
            i === steps.length - 1 ? { ...s, liveContent: endContent } : s
          )
          useChatStore.getState().setProcessSteps(updatedSteps)
        }
      }

      // Destructure semua field, simpan sisanya di rest
      const { action, detail, count, ts, type, ...rest } = data

      // Tentukan konten yang akan ditampilkan di toggle
      // Prioritas: code (Written) > result (tool output) > liveContent (streaming)
      const previewContent = rest.code || rest.result || null

      useChatStore.getState().addProcessStep({
        action: action || 'Worked',
        detail: detail || '',
        count: count ?? null,
        ts: ts || Date.now(),
        _textOffset: currentOffset,
        liveContent: previewContent,  // langsung isi jika ada konten
        // spread semua field extra: code, language, result, truncated, dll
        ...rest,
      })

      // Auto-open artifact panel untuk Written action
      if (action === 'Written' && rest.code && detail) {
        const lang = (rest.language || detail.split('.').pop() || 'txt').toLowerCase()
        const filename = detail.split('/').pop() || detail
        openArtifactCard(
          rest.code + (rest.truncated ? '\n\n// [konten dipotong]' : ''),
          lang,
          `✍️ ${filename}`,
          false
        )
      }
    }

    // Chunk handler: append text
    const handleChunk = (chunk) => {
      appendStreamingText(chunk)
    }

    // Auto-open artifact panel when APP_PREVIEW detected in completed response
    const autoOpenAppPreview = (fullText) => {
      const m = /%%APP_PREVIEW%%\s*(https?:\/\/[^\s]+)\s*%%END_PREVIEW%%/i.exec(fullText)
      if (m) {
        const url = m[1].trim()
        // Small delay so the message bubble renders first
        setTimeout(() => {
          openArtifactCard(url, 'preview', '🚀 App Preview — Jalankan Aplikasi', true)
          toast.success('🚀 Aplikasi berhasil dibuat! Klik Preview untuk melihat.', { duration: 5000 })
        }, 400)
      }
    }

    // Use different endpoints based on whether image is present
    if (imageToSend) {
      // chatStreamMultimodal(payload, imageData, onChunk, onDone, onSession, onStatus, onProcess)
      const abortFn = api.chatStreamMultimodal(
        {
          session_id: sessionId,
          message: combinedText,
          model: selectedOrchestrator,
          use_rag: useRAG,
          channel: channelType,
        },
        imageToSend,
        (chunk) => handleChunk(chunk),
        async (done) => {
          const fullText = useChatStore.getState().streamingText
          clearStreaming()
          useChatStore.getState().setStatusText('')

          if (done.drive_prompt) {
            setDrivePromptContent(done.drive_prompt.content, done.drive_prompt.title)
          }
          if (done.model_used) setActiveModel(done.model_used)
          if (done.capability_used) setActiveCapability(done.capability_used)

          addMessage({
            id: Date.now() + 1,
            role: 'assistant',
            content: fullText,
            model: useChatStore.getState().actualModel || selectedOrchestrator,
            rag_sources: done.sources?.length ? JSON.stringify(done.sources) : null,
            thinking_process: done.thinking_process || null,
            created_at: new Date().toISOString(),
          })
          // Delay refresh slightly to ensure backend commit is fully visible (SQLite multi-worker safety)
          setTimeout(() => {
            api.listSessions().then((s) => {
              const safe = s.filter(x => !deletingIdsRef.current.has(x.id))
              const currentSessions = useChatStore.getState().sessions
              setSessions((currentSessions.length > 0 && safe.length === 0) ? currentSessions : safe)
            }).catch(() => {})
          }, 800)
          useChatStore.getState().finalizeProcessSteps()  // Keep visible for review
          
          // Auto-hide timer
          setShowLastSteps(true)
          if (hideStepsTimerRef.current) clearTimeout(hideStepsTimerRef.current)
          hideStepsTimerRef.current = setTimeout(() => {
            setFadingOut(true)
            setTimeout(() => {
              setShowLastSteps(false)
              setFadingOut(false)
            }, 400)
          }, 7600)

          useChatStore.getState().setActualModel(null)
          useChatStore.getState().setAbortRequest(null)
          autoOpenAppPreview(fullText)  // Auto-open preview if app was built
          setTimeout(() => { inputRef.current?.focus() }, 50)
        },
        (sessionData) => {
          if (sessionData && sessionData.model) {
            useChatStore.getState().setActualModel(sessionData.model)
          }
          if (sessionData && sessionData.session_id && (!currentSession || !currentSession.id)) {
            setCurrentSession({ id: sessionData.session_id })
          }
        },
        (status) => useChatStore.getState().setStatusText(status),
        (procData) => handleAddProcessStep(procData)
      )
      useChatStore.getState().setAbortRequest(abortFn)
    } else {
      // chatStream(payload, onChunk, onDone, onSession, onPending, onStatus, onProcess)
      const abortFn = api.chatStream(
        {
          session_id: sessionId,
          message: combinedText,
          model: selectedOrchestrator,
          use_rag: useRAG,
          channel: channelType,
        },
        (chunk) => handleChunk(chunk),
        async (done) => {
          const fullText = useChatStore.getState().streamingText
          clearStreaming()
          useChatStore.getState().setStatusText('')

          if (done.drive_prompt) {
            setDrivePromptContent(done.drive_prompt.content, done.drive_prompt.title)
          }
          if (done.model_used) setActiveModel(done.model_used)
          if (done.capability_used) setActiveCapability(done.capability_used)

          addMessage({
            id: Date.now() + 1,
            role: 'assistant',
            content: fullText,
            model: useChatStore.getState().actualModel || selectedOrchestrator,
            rag_sources: done.sources?.length ? JSON.stringify(done.sources) : null,
            thinking_process: done.thinking_process || null,
            created_at: new Date().toISOString(),
          })
          // Delay refresh slightly to ensure backend commit is fully visible (SQLite multi-worker safety)
          setTimeout(() => {
            api.listSessions().then((s) => {
              const safe = s.filter(x => !deletingIdsRef.current.has(x.id))
              const currentSessions = useChatStore.getState().sessions
              setSessions((currentSessions.length > 0 && safe.length === 0) ? currentSessions : safe)
            }).catch(() => {})
          }, 800)
          useChatStore.getState().finalizeProcessSteps()  // Keep visible for review
          
          // Auto-hide timer
          setShowLastSteps(true)
          if (hideStepsTimerRef.current) clearTimeout(hideStepsTimerRef.current)
          hideStepsTimerRef.current = setTimeout(() => {
            setFadingOut(true)
            setTimeout(() => {
              setShowLastSteps(false)
              setFadingOut(false)
            }, 400)
          }, 7600)

          useChatStore.getState().setActualModel(null)
          useChatStore.getState().setAbortRequest(null)
          autoOpenAppPreview(fullText)  // Auto-open preview if app was built
          setTimeout(() => { inputRef.current?.focus() }, 50)
        },
        (sessionData) => {
          if (sessionData && sessionData.model) {
            useChatStore.getState().setActualModel(sessionData.model)
          }
          if (sessionData && sessionData.session_id && (!currentSession || !currentSession.id)) {
            setCurrentSession({ id: sessionData.session_id })
          }
        },
        (pendingData) => {
          clearStreaming()
          useChatStore.getState().setStatusText('')
          setPendingConfirmation(pendingData)
        },
        (status) => useChatStore.getState().setStatusText(status),
        (procData) => handleAddProcessStep(procData)
      )
      useChatStore.getState().setAbortRequest(abortFn)
    }
    
    // Auto-focus input after sending
    setTimeout(() => {
      if (inputRef.current) {
        inputRef.current.focus()
      }
    }, 100)
  }

  function approveExecution(pendingData) {
    setPendingConfirmation(null)
    setStreaming(true)

    const abortFn = api.executePending(
      {
        session_id: pendingData.session_id,
        command: pendingData.command,
        model: selectedOrchestrator,
      },
      (chunk) => handleChunk(chunk),
      async (done) => {
        const fullText = useChatStore.getState().streamingText
        clearStreaming()
        useChatStore.getState().setStatusText('')
        useChatStore.getState().finalizeProcessSteps()  // Keep visible for review
        useChatStore.getState().setActualModel(null)
        useChatStore.getState().setAbortRequest(null)
        addMessage({
          id: Date.now() + 1,
          role: 'assistant',
          content: fullText,
          model: useChatStore.getState().actualModel || selectedOrchestrator,
          created_at: new Date().toISOString(),
        })
      }
    )
    useChatStore.getState().setAbortRequest(abortFn)
  }

  function handleKeyDown(e) {
    if (e.key === 'Escape' && streaming) {
      e.preventDefault()
      stopStreaming()
      return
    }
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  // ── Handle gambar dari picker ─────────────────────────────
  async function handleImagePick(e) {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      toast.loading('Menyiapkan gambar...')
      const result = await api.uploadImage(file)
      toast.dismiss()
      setPendingImage({
        base64: result.base64,
        mime_type: result.mime_type,
        preview: `data:${result.mime_type};base64,${result.base64}`,
        filename: result.filename,
      })
      toast.success('Gambar siap dikirim!')
    } catch (err) {
      toast.dismiss()
      toast.error('Gagal memuat gambar')
    }
    e.target.value = ''
  }

  // ── Handle voice recording ────────────────────────────────
  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mr = new MediaRecorder(stream, { mimeType: 'audio/webm' })
      const chunks = []
      mr.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data) }
      mr.onstop = async () => {
        setIsRecording(false)
        setIsTranscribing(true)
        stream.getTracks().forEach(t => t.stop())
        const blob = new Blob(chunks, { type: 'audio/webm' })
        try {
          const result = await api.transcribeAudio(blob, 'voice.webm')
          if (result.status === 'ok' && result.text) {
            setInput(prev => prev ? prev + ' ' + result.text : result.text)
            toast.success('🎙️ Suara ditranskrip!')
          } else {
            toast('Tidak ada suara yang terdeteksi', { icon: '🎤' })
          }
        } catch {
          toast.error('Gagal mentranskrip suara')
        } finally {
          setIsTranscribing(false)
        }
      }
      mr.start()
      mediaRecorderRef.current = mr
      setIsRecording(true)
      toast('🔴 Merekam... Klik lagi untuk berhenti', { duration: 60000 })
    } catch {
      toast.error('Tidak bisa mengakses mikrofon')
    }
  }

  function stopRecording() {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop()
      toast.dismiss()
    }
  }

  async function handleFileUpload(e) {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      toast.loading('Mengupload file ke Knowledge Base...')
      await api.uploadDoc(file)
      toast.dismiss()
      toast.success(`${file.name} berhasil diupload!`)
    } catch {
      toast.dismiss()
      toast.error('Upload gagal')
    }
    e.target.value = ''
  }



  // ── Handler Export Chat ─────────────────────────────────────
  const handleExportChat = async (format, msgId) => {
    if (!currentSession?.id) return toast.error('Sesi aktif tidak ditemukan')
    const loadId = toast.loading(`Mengekspor sesi ke ${format.toUpperCase()}...`)
    try {
      const blob = await api.exportChat(currentSession.id, format, msgId)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.style.display = 'none'
      a.href = url
      // Backend headers content-disposition already brings filename, but downloading blob requires setting download attr if needed,
      // it's fine just naming it natively here too.
      a.download = `Export_Chat_${new Date().getTime()}.${format}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      toast.success('Berhasil mendownload!', { id: loadId })
    } catch (e) {
      toast.error(e.message, { id: loadId })
    }
  }

  // ── Quick-action cards for the welcome screen ──────────────
  const quickActions = [
    { icon: Sparkles, label: 'Chat Biasa', desc: 'Tanya jawab dengan AI', color: 'from-accent to-accent-2' },
    { icon: Zap, label: 'Perintah', desc: 'Jalankan otomasi/perintah', color: 'from-amber-500 to-orange-500' },
    { icon: FileText, label: 'Analisa Dokumen', desc: 'Upload & analisa file', color: 'from-emerald-500 to-teal-500' },
  ]

  return (
    <div className="flex h-full relative">
      
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div 
          className="absolute inset-0 bg-black/50 z-40 md:hidden animate-fade"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sessions sidebar */}
      <div className={clsx(
        "w-52 md:w-52 flex-shrink-0 border-r border-border bg-bg-2 flex-col transition-all duration-300 z-50 h-full",
        sidebarOpen ? "flex absolute shadow-2xl" : "hidden md:flex relative"
      )}>
        <div className="p-3 border-b border-border flex items-center justify-between">
          <button
            onClick={() => { newSession(); setSidebarOpen(false); }}
            disabled={isCurrentSessionEmpty}
            className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg bg-accent hover:bg-accent/80 text-white text-xs font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            title={isCurrentSessionEmpty ? 'Sesi ini masih kosong, mulai chat dulu!' : 'Buat sesi chat baru'}
          >
            <Plus size={13} /> New Chat
          </button>
          
          <button 
            className="ml-2 md:hidden p-1.5 rounded-lg text-ink-3 hover:bg-bg-4"
            onClick={() => setSidebarOpen(false)}
          >
            <X size={16} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-2">
          {filteredSessions.length === 0 && (
            <p className="text-xs text-ink-3 text-center py-6">
              Belum ada sesi.<br />Buat chat pertama!
            </p>
          )}
          {filteredSessions.map((s) => (
            <SessionItem
              key={s.id}
              session={s}
              active={currentSession?.id === s.id}
              onClick={() => { loadSession(s); navigate(`/chat/${s.id}`); setSidebarOpen(false); }}
              onDelete={deleteSession}
            />
          ))}
        </div>
      </div>

      {/* Chat area */}
      <div 
        className={clsx(
          'flex flex-col min-w-0 transition-all duration-300 relative',
          artifact.open ? 'flex-1' : 'flex-1'
        )}
        {...dragHandlers}
      >
        <DragOverlay isVisible={isDragOver} />

        {/* Topbar */}
        <div className="h-12 border-b border-border flex items-center px-4 gap-3 flex-shrink-0 bg-bg-2">
          {/* Hamburger Menu for Mobile */}
          <button 
            className="md:hidden p-1.5 -ml-1.5 rounded-lg text-ink-3 hover:text-ink hover:bg-bg-4 transition-colors"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu size={18} />
          </button>
          
          <span className="text-sm font-medium text-ink truncate flex-1">
            {currentSession?.title || 'Pilih atau buat sesi chat'}
          </span>

          {/* RAG toggle */}
          <button
            onClick={() => setUseRAG(!useRAG)}
            className={clsx(
              'px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all duration-300 border flex items-center gap-1.5',
              useRAG
                ? 'bg-success/15 border-success/50 text-success shadow-[0_0_12px_rgba(74,222,128,0.3)]'
                : 'bg-bg-4 border-border text-ink-3 hover:bg-bg-5'
            )}
            title="Toggle RAG (Knowledge Base)"
          >
            📚 RAG
            {useRAG && <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse"/>}
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-4 py-5 space-y-4">
          {!currentSession && (
            <div className="flex flex-col items-center justify-center h-full text-center">
              {/* Animated brain icon */}
              <div className="relative mb-6">
                <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-accent to-accent-2 flex items-center justify-center shadow-2xl shadow-accent/30">
                  <span className="text-4xl">🧠</span>
                </div>
                <div className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-success border-2 border-bg flex items-center justify-center">
                  <span className="w-2 h-2 rounded-full bg-white animate-pulse2" />
                </div>
              </div>

              {/* Dynamic greeting using appName from global state */}
              <h2 className="text-xl font-bold text-ink mb-2">
                Halo! Saya <span className="bg-gradient-to-r from-accent to-accent-2 bg-clip-text text-transparent">{appName}</span>
              </h2>
              <p className="text-sm text-ink-3 mb-8 max-w-md leading-relaxed">
                Ketik pesan, berikan perintah, atau jalankan alur kerja otomatis. Saya akan mengatur model AI mana yang paling tepat untuk merespons Anda.
              </p>

              {/* Quick action cards */}
              <div className="flex gap-3 mb-8">
                {quickActions.map(({ icon: Icon, label, desc, color }) => (
                  <button
                    key={label}
                    onClick={newSession}
                    className="flex flex-col items-center gap-2.5 px-5 py-4 bg-bg-2 border border-border rounded-xl hover:border-accent/40 hover:bg-bg-3 transition-all group w-40"
                  >
                    <div className={clsx('w-10 h-10 rounded-xl bg-gradient-to-br flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform', color)}>
                      <Icon size={18} className="text-white" />
                    </div>
                    <div>
                      <div className="text-xs font-semibold text-ink group-hover:text-accent-2 transition-colors">{label}</div>
                      <div className="text-[10px] text-ink-3 mt-0.5">{desc}</div>
                    </div>
                  </button>
                ))}
              </div>

              <button
                onClick={newSession}
                className="flex items-center gap-2 px-5 py-2.5 bg-accent hover:bg-accent/80 text-white rounded-xl text-sm font-medium transition-all shadow-lg shadow-accent/25 hover:shadow-xl hover:shadow-accent/30"
              >
                <Plus size={15} /> Mulai Chat Baru
              </button>

              {models.length === 0 && (
                <div className="mt-6 p-3 bg-warn/10 border border-warn/20 rounded-xl text-xs text-warn max-w-sm">
                  ⚠️ Belum ada model aktif. Buka <span className="font-mono">Integrasi</span> untuk menambahkan API key atau install Ollama.
                </div>
              )}
            </div>
          )}

          {loadingMsgs && (
            <div className="flex items-center gap-2 text-ink-3 text-sm">
              <Loader2 size={14} className="animate-spin" /> Memuat pesan...
            </div>
          )}

          {messages.map((msg) => (
            <Bubble 
              key={msg.id} 
              msg={msg} 
              isStreaming={false} 
              onExport={handleExportChat}
              onSpeak={handleSpeak}
              speakingId={speakingId}
              onOpenArtifact={openArtifact}
              onOpenArtifactCard={openArtifactCard}
            />
          ))}

          {/* ── PROCESS STEPS PANEL — selalu di atas jawaban ── */}
          {/* Live: tampil saat streaming */}
          {streaming && processSteps.length > 0 && (
            <div
              onClickCapture={(e) => {
                if (!e.target.closest('[data-allow-propagation]')) {
                  e.stopPropagation()
                }
              }}
              onMouseDownCapture={(e) => {
                if (!e.target.closest('[data-allow-propagation]')) {
                  e.stopPropagation()
                }
              }}
            >
              <ProcessStepsPanel
                steps={processSteps}
                isStreaming={streaming}
                onStop={stopStreaming}
                streamingText={streamingText}
                onOpenArtifactCard={openArtifactCard}
              />
            </div>
          )}

          {/* After done: tampil singkat lalu hilang otomatis */}
          {!streaming && showLastSteps && lastProcessSteps && lastProcessSteps.length > 0 &&
            lastProcessSteps.some(s => s.action && s.action !== 'Thinking' && s.action !== 'Thought') && (
            <div className={clsx("relative", fadingOut && "process-panel-fadeout")}>
              <ProcessStepsPanel
                steps={lastProcessSteps}
                isStreaming={false}
                onStop={null}
                streamingText=""
                onOpenArtifactCard={openArtifactCard}
              />
              <div className="flex items-center justify-end px-10 pb-1 gap-2 animate-fade">
                <span className="text-[10px] text-ink-3 opacity-50">
                  Otomatis hilang dalam beberapa detik
                </span>
                <button
                  onClick={() => setShowLastSteps(false)}
                  className="text-[10px] text-ink-3 hover:text-danger transition-colors underline"
                >
                  Tutup
                </button>
              </div>
            </div>
          )}

          {/* ── STREAMING BUBBLE — jawaban di bawah thinking ── */}
          {streaming && streamingText && (
            <Bubble
              msg={{ role: 'assistant', content: streamingText, model: actualModel || selectedOrchestrator, created_at: new Date().toISOString() }}
              isStreaming={true}
              onStop={stopStreaming}
              onSpeak={handleSpeak}
              speakingId={speakingId}
              onOpenArtifact={openArtifact}
              onOpenArtifactCard={openArtifactCard}
            />
          )}


          {/* Real-time Routing Badge / Capability Indicator (HIDDEN) */}
          {false && (activeModel || activeCapability) && !streaming && !pendingConfirmation && (
            <div className="flex justify-center my-4 animate-fade">
              <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-bg-2 border border-border-2 rounded-full shadow-sm">
                <Sparkles size={12} className="text-accent-2" />
                <span className="text-[10px] text-ink-3">Dirutekan ke:</span>
                {activeModel && (
                  <span className="text-[10px] font-medium text-ink-2 bg-bg-3 px-2 py-0.5 rounded-full border border-border">
                    {activeModel}
                  </span>
                )}
                {activeCapability && (
                  <span className="text-[10px] font-bold text-accent-2 tracking-widest uppercase bg-accent-2/10 px-2 py-0.5 rounded-full">
                    {activeCapability}
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Drive Upload Prompt UI */}
          {drivePromptContent && !streaming && !pendingConfirmation && (
             <div className="flex justify-start mb-6 w-full max-w-3xl pr-4 animate-fade-in-up">
               <div className="flex gap-4">
                 <div className="w-8 h-8 flex-shrink-0 bg-blue-500/20 border border-blue-500/50 rounded-lg flex items-center justify-center">
                   <CloudUpload size={16} className="text-blue-500" />
                 </div>
                 <div className="flex-1 min-w-0 bg-bg-2 border border-border rounded-2xl rounded-tl-sm px-4 py-3 shadow-md">
                   <div className="flex items-center justify-between mb-2">
                     <span className="text-sm font-bold text-ink">Google Drive Upload Ready</span>
                   </div>
                   <div className="text-xs text-ink-2 mb-3">
                     <p>Pilih metadata berikut untuk di-upload:</p>
                   </div>
                   <div className="bg-bg-3 p-2.5 rounded border border-border-2 font-mono text-[11px] text-ink mb-4 overflow-x-auto whitespace-pre-wrap max-h-32">
                     {drivePromptTitle && <div className="font-bold border-b border-border-2 pb-1 mb-1">{drivePromptTitle}</div>}
                     {drivePromptContent}
                   </div>
                   <div className="flex gap-3">
                     <button
                       onClick={() => {
                          addMessage({
                            id: Date.now() + 1,
                            role: 'user',
                            content: `Teruskan metadata ini dan lakukan upload ke gdrive: ${drivePromptTitle || ''}\n\n${drivePromptContent}`,
                            model: selectedOrchestrator,
                            created_at: new Date().toISOString(),
                          })
                          setInput(`Tolong upload metadata tadi`)
                          clearDrivePrompt()
                       }}
                       className="flex-1 bg-blue-600 hover:bg-blue-500 text-white font-medium py-2 rounded-lg text-xs shadow-md transition-all"
                     >
                       Ya, upload sekarang!
                     </button>
                     <button
                       onClick={() => clearDrivePrompt()}
                       className="flex-1 bg-bg-4 hover:bg-bg-5 text-ink-2 hover:text-ink font-medium py-2 border border-border rounded-lg text-xs transition-all"
                     >
                       Batal
                     </button>
                   </div>
                 </div>
               </div>
             </div>
          )}

          <div ref={messagesEndRef} className="h-4" />
        </div>

        {/* Input area */}
        {currentSession && (
          <div className="p-3 border-t border-border bg-bg-2 flex-shrink-0">

            {/* Streaming status bar */}
            {streaming && (
              <div className="flex items-center justify-between mb-2 px-1">
                <div className="flex items-center gap-1.5 text-xs text-ink-3">
                  <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse2" />
                  AI sedang merespons...
                  <span className="text-ink-3 font-mono">
                    {streamingText.length} karakter
                  </span>
                </div>
                <div className="flex items-center gap-1.5 text-[10px] text-ink-3">
                  <kbd className="px-1.5 py-0.5 bg-bg-4 border border-border rounded font-mono">Esc</kbd>
                  <span>untuk stop</span>
                </div>
              </div>
            )}

            {/* Preview gambar yang akan dikirim */}
            {pendingImage && (
              <div className="flex items-center gap-2 mb-2 px-1 animate-fade">
                <div className="relative">
                  <img
                    src={pendingImage.preview}
                    alt="Preview gambar"
                    className="h-14 w-14 object-cover rounded-lg border border-border-2"
                  />
                  <button
                    onClick={() => setPendingImage(null)}
                    className="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full bg-danger flex items-center justify-center"
                  >
                    <X size={9} className="text-white" />
                  </button>
                </div>
                <span className="text-[11px] text-ink-3">Gambar siap dikirim</span>
              </div>
            )}

            {/* Lampiran file context chat */}
            {attachedFiles.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-2 px-1 animate-fade">
                {attachedFiles.map((f) => (
                  <FileChip key={f.id} file={f} onRemove={removeFile} />
                ))}
              </div>
            )}

            {fileError && (
              <div className="text-[11px] text-danger mb-2 px-1 animate-fade">⚠️ {fileError}</div>
            )}

            <div className="flex gap-2 items-end">
              {/* Upload dokumen (paperclip) */}
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                onChange={handleFileUpload}
                accept=".pdf,.docx,.txt,.csv,.md"
              />
              {/* Lampiran Context Chat */}
              <input
                ref={chatContextFileRef}
                type="file"
                multiple
                className="hidden"
                onChange={(e) => {
                  if (e.target.files) addFiles(e.target.files);
                  e.target.value = '';
                }}
                accept=".pdf,.docx,.doc,.xlsx,.xls,.csv,.txt,.md,.png,.jpg,.jpeg,.webp"
              />
              {/* Image picker hidden input */}
              <input
                ref={imagePickerRef}
                type="file"
                className="hidden"
                onChange={handleImagePick}
                accept="image/*"
              />

              {/* Tombol Lampirkan File ke Chat */}
              <button
                onClick={() => chatContextFileRef.current?.click()}
                disabled={streaming}
                className="w-9 h-9 flex-shrink-0 flex items-center justify-center rounded-lg border border-border-2 bg-bg-4 hover:bg-bg-5 text-ink-2 hover:text-ink transition-colors disabled:opacity-40"
                title="Lampirkan file (PDF, Excel, Word) ke chat"
              >
                <FilePlus size={15} />
              </button>

              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={streaming}
                className="w-9 h-9 flex-shrink-0 flex items-center justify-center rounded-lg border border-border-2 bg-bg-4 hover:bg-bg-5 text-ink-2 hover:text-ink transition-colors disabled:opacity-40"
                title="Upload file ke Knowledge Base"
              >
                <Paperclip size={15} />
              </button>

              {/* Kamera */}
              <button
                onClick={() => imagePickerRef.current?.click()}
                disabled={streaming}
                className={clsx(
                  'w-9 h-9 flex-shrink-0 flex items-center justify-center rounded-lg border transition-colors disabled:opacity-40',
                  pendingImage
                    ? 'border-accent bg-accent/20 text-accent'
                    : 'border-border-2 bg-bg-4 hover:bg-bg-5 text-ink-2 hover:text-accent'
                )}
                title="Kirim gambar ke AI"
              >
                <ImagePlus size={15} />
              </button>

              {/* Mikrofon */}
              <button
                onClick={isRecording ? stopRecording : startRecording}
                disabled={streaming || isTranscribing}
                className={clsx(
                  'w-9 h-9 flex-shrink-0 flex items-center justify-center rounded-lg border transition-colors disabled:opacity-40',
                  isRecording
                    ? 'border-danger bg-danger/20 text-danger animate-pulse'
                    : isTranscribing
                      ? 'border-warn bg-warn/20 text-warn'
                      : 'border-border-2 bg-bg-4 hover:bg-bg-5 text-ink-2 hover:text-accent'
                )}
                title={isRecording ? 'Berhenti merekam' : isTranscribing ? 'Mentranskripsi...' : 'Rekam suara'}
              >
                {isRecording ? <MicOff size={15} /> : isTranscribing ? <Loader2 size={15} className="animate-spin" /> : <Mic size={15} />}
              </button>

              {/* Text input */}
              <div 
                className="flex-1 relative"
                onDragOver={(e) => {
                  e.preventDefault()
                  e.currentTarget.classList.add('ring-2', 'ring-accent', 'bg-accent/5')
                }}
                onDragLeave={(e) => {
                  e.currentTarget.classList.remove('ring-2', 'ring-accent', 'bg-accent/5')
                }}
                onDrop={(e) => {
                  e.preventDefault()
                  e.currentTarget.classList.remove('ring-2', 'ring-accent', 'bg-accent/5')
                  const files = e.dataTransfer.files
                  if (files.length > 0) {
                    const file = files[0]
                    if (file.type.startsWith('image/')) {
                      handleImagePick({ target: { files } })
                    }
                  }
                }}
              >
                <textarea
                  ref={inputRef}
                  value={input}
                  onChange={(e) => {
                    setInput(e.target.value)
                    e.target.style.height = 'auto'
                    e.target.style.height = Math.min(e.target.scrollHeight, 160) + 'px'
                  }}
                  onKeyDown={handleKeyDown}
                  onPaste={(e) => {
                    const items = e.clipboardData?.items;
                    if (items) {
                      const filesToAttach = [];
                      for (let i = 0; i < items.length; i++) {
                        if (items[i].kind === 'file') {
                          const file = items[i].getAsFile();
                          if (file) filesToAttach.push(file);
                        }
                      }
                      if (filesToAttach.length > 0) {
                        e.preventDefault();
                        addFiles(filesToAttach);
                      }
                    }
                  }}
                  onFocus={(e) => {
                    e.currentTarget.parentElement?.classList.remove('ring-2', 'ring-accent', 'bg-accent/5')
                  }}
                  placeholder={
                    streaming
                      ? 'Ketik jawaban atau pesan baru... (Enter untuk kirim & interrupt)'
                      : 'Ketik pesan, perintah, atau minta analisa data... (atau drag & drop gambar)'
                  }
                  rows={1}
                  className="w-full bg-bg-4 border border-border-2 rounded-xl px-3.5 py-2.5 text-sm text-ink placeholder-ink-3 outline-none focus:border-accent transition-colors resize-none"
                />
              </div>

              {/* Action button — Stop (always visible during streaming), Send (when has text) */}
              {streaming && !input.trim() ? (
                // Pure stop button — no input typed
                <button
                  onClick={stopStreaming}
                  className="w-9 h-9 flex-shrink-0 flex items-center justify-center rounded-lg bg-danger hover:bg-danger/80 text-white transition-all shadow-lg shadow-danger/20"
                  title="Stop (Esc)"
                >
                  <Square size={16} fill="white" />
                </button>
              ) : streaming && input.trim() ? (
                // Interrupt + Send button — user typed a reply while streaming
                <button
                  onClick={sendMessage}
                  className="w-9 h-9 flex-shrink-0 flex items-center justify-center rounded-lg bg-accent hover:bg-accent/80 text-white transition-all shadow-lg shadow-accent/20 relative"
                  title="Interrupt & Kirim jawaban"
                >
                  <Send size={15} />
                  <span className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-danger border border-bg-2" />
                </button>
              ) : (
                /* SEND button — normal */
                <button
                  onClick={sendMessage}
                  disabled={!input.trim() || !currentSession}
                  className="w-9 h-9 flex-shrink-0 flex items-center justify-center rounded-lg bg-accent hover:bg-accent/80 disabled:opacity-40 text-white transition-colors"
                  title="Kirim (Enter)"
                >
                  <Send size={15} />
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Artifacts Panel — slideout dari kanan */}
      {artifact.open && (
        <ArtifactsPanel
          code={artifact.code}
          language={artifact.language}
          title={artifact.title}
          isPreviewUrl={artifact.isPreviewUrl}
          onClose={closeArtifact}
        />
      )}
      
      {/* Project Location Popup */}
      {projectLocationPopup.open && (
        <ProjectLocationPopup
          isOpen={projectLocationPopup.open}
          sessionId={projectLocationPopup.sessionId}
          onClose={closeProjectLocationPopup}
          onLocationSet={(projectPath) => {
            // Store project path in session and notify user
            toast.success(`📁 Lokasi proyek disimpan: ${projectPath}`)
          }}
        />
      )}
    </div>
  )
}
