/**
 * AgentProgress.jsx — ProcessStepsPanel, _Step, _ElapsedBadge, ArtifactsPanel
 * Extracted from Chat.jsx for modularity.
 */
import React, { useState, useEffect } from 'react'
import { copyToClipboard } from '../../utils/clipboard'
import {
  Copy, Check, Download, X,
  ExternalLink, FileCode2, Maximize2,
  Terminal, BookOpen, PenLine, Brain,
  List, Search, Globe, FilePlus, Trash, MoveRight,
  ClipboardList, AlignLeft, CheckCircle2, Hash, AlertCircle, Wrench, RefreshCw, Zap,
} from 'lucide-react'
import clsx from 'clsx'

// ── Language color badges (shared) ────────────────────────────
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

// ── ACTION_META ───────────────────────────────────────────────
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

// ── Status visual per langkah ─────────────────────────────────
const _SS = {
  done:    { dot: '#4ade80', bg: 'rgba(74,222,128,0.10)',    border: 'rgba(74,222,128,0.30)',  text: '#4ade80',  label: 'Selesai'  },
  running: { dot: '#a78bfa', bg: 'rgba(167,139,250,0.10)',   border: 'rgba(167,139,250,0.35)', text: '#a78bfa',  label: 'Berjalan' },
  error:   { dot: '#f87171', bg: 'rgba(248,113,113,0.10)',   border: 'rgba(248,113,113,0.30)', text: '#f87171',  label: 'Error'    },
}

// ── Action → Tabler icon ──────────────────────────────────────
const _ICONS = {
  Thinking: 'brain', Thought: 'brain',
  Planned: 'list-check', Worked: 'tool',
  Explored: 'compass', Ran: 'terminal-2',
  Edited: 'pencil', Modify: 'pencil',
  Analyzed: 'chart-bar', Reading: 'book-open',
  Writing: 'file-pencil', Written: 'file-check',
  Listed: 'list', Searched: 'search',
  Fetched: 'world', Created: 'file-plus',
  Deleted: 'trash', Moved: 'arrow-right',
  Copied: 'copy', Summarized: 'align-left',
  Checked: 'circle-check', Found: 'hash',
  Error: 'alert-circle', Done: 'circle-check',
}

// ── Elapsed time display ──────────────────────────────────────
function _ElapsedBadge({ active }) {
  const [sec, setSec] = React.useState(0)
  const ref = React.useRef(null)
  React.useEffect(() => {
    if (!active) { setSec(0); return }
    const start = Date.now()
    ref.current = setInterval(() => setSec(Math.floor((Date.now() - start) / 1000)), 1000)
    return () => clearInterval(ref.current)
  }, [active])
  if (!active && sec === 0) return null
  const fmt = s => s < 60 ? `${s}s` : `${Math.floor(s/60)}m ${s%60}s`
  return (
    <span style={{
      marginLeft: 'auto', fontSize: 11, fontFamily: 'var(--font-mono, monospace)',
      color: 'var(--color-text-tertiary, #555)', flexShrink: 0,
    }}>
      <i className="ti ti-clock" style={{ marginRight: 3, fontSize: 10 }} />
      {fmt(sec)}
    </span>
  )
}

// ── Individual step ───────────────────────────────────────────
function _Step({ step, isActive, isLast, isStreaming, streamingText, onOpenArtifactCard }) {
  const [open, setOpen] = React.useState(isActive)

  React.useEffect(() => {
    if (isActive) setOpen(true)
    if (!isActive && !step.code && !step.result) setOpen(false)
  }, [isActive])

  const status = step.action === 'Error' ? 'error' : isActive ? 'running' : 'done'
  const s = _SS[status]
  const icon = _ICONS[step.action] || 'bolt'
  const spinning = status === 'running'

  const getContent = () => {
    if (isActive && step._textOffset != null && streamingText && !step._isLiveThinking) {
      const live = streamingText.substring(step._textOffset)
      if (live.trim()) return live
    }
    return step.liveContent || step.code || step.result
      || `Action: ${step.action}\nDetail: ${step.detail || '—'}`
  }

  const handleCopy = (e) => {
    e.stopPropagation()
    navigator.clipboard?.writeText(getContent()).catch(() => {})
  }

  return (
    <div style={{ display: 'flex', gap: 10 }}>
      {/* Icon + connector line */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flexShrink: 0 }}>
        <div style={{
          width: 32, height: 32, borderRadius: '10px',
          background: s.bg, border: `2px solid ${s.border}`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          transition: 'all 0.3s', boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.1)',
        }}>
          <i
            className={`ti ti-${icon}`}
            style={{
              fontSize: 16, color: s.text,
              animation: spinning ? '_sp-spin 1.2s linear infinite' : 'none',
            }}
          />
        </div>
        {!isLast && (
          <div style={{ width: 2, flex: 1, minHeight: 12, background: 'var(--border)', margin: '4px 0', opacity: 0.5 }} />
        )}
      </div>

      {/* Body */}
      <div style={{ flex: 1, paddingBottom: isLast ? 2 : 6 }}>
        {/* Header row — clickable */}
        <div
          onClick={() => setOpen(o => !o)}
          style={{
            display: 'flex', alignItems: 'center', gap: 10,
            padding: '8px 12px', borderRadius: 12, cursor: 'pointer',
            transition: 'all 0.2s', border: '1px solid transparent',
          }}
          onMouseEnter={e => { e.currentTarget.style.background = 'var(--bg-5)'; e.currentTarget.style.borderColor = 'var(--border)' }}
          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.borderColor = 'transparent' }}
        >
          {/* Status badge */}
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            fontSize: 10, fontWeight: 900,
            padding: '3px 10px', borderRadius: 99, flexShrink: 0,
            background: s.bg, border: `2px solid ${s.border}`, color: s.text,
            animation: spinning ? '_sp-pulse 1.5s ease-in-out infinite' : 'none',
            letterSpacing: '1px', textTransform: 'uppercase',
            boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
          }}>
            <span style={{
              width: 6, height: 6, borderRadius: '50%', background: s.dot,
              animation: spinning ? '_sp-pulse 1.2s ease-in-out infinite' : 'none',
              boxShadow: `0 0 8px ${s.dot}`,
            }} />
            {s.label}
          </span>

          {/* Detail label */}
          <span style={{
            fontSize: 13, fontWeight: 900,
            color: isActive ? 'var(--color-text-primary, #ddd)' : 'var(--color-text-secondary, #aaa)',
            flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            textTransform: 'uppercase', letterSpacing: '0.5px', opacity: isActive ? 1 : 0.7,
          }}>
            {step.detail || step.action}
          </span>

          {/* Language pill */}
          {step.language && (
            <span style={{
              fontSize: 9, fontFamily: 'var(--font-mono, monospace)', fontWeight: 900,
              padding: '2px 8px', borderRadius: 6,
              background: 'var(--bg-4)', border: '2px solid var(--border)',
              color: 'var(--ink-3)', flexShrink: 0, textTransform: 'uppercase', letterSpacing: '0.5px',
            }}>
              {step.language}
            </span>
          )}

          {/* Animated dots when active */}
          {isActive && isStreaming && (
            <span style={{ display: 'flex', gap: 3, flexShrink: 0 }}>
              {[0, 1, 2].map(i => (
                <span key={i} style={{
                  width: 4, height: 4, borderRadius: '50%', background: '#a78bfa',
                  animation: `_sp-pulse 1.2s ease-in-out ${i * 0.2}s infinite`,
                }} />
              ))}
            </span>
          )}

          {/* Chevron */}
          <i
            className="ti ti-chevron-down"
            style={{
              fontSize: 16, color: 'var(--color-text-tertiary, #555)', flexShrink: 0,
              transition: 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)', transform: open ? 'rotate(180deg)' : 'none',
              opacity: open ? 1 : 0.5,
            }}
          />
        </div>

        {/* Expandable detail panel */}
        <div style={{
          overflow: 'hidden', maxHeight: open ? 600 : 0,
          transition: 'max-height 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
        }}>
          <div style={{
            margin: '8px 4px 10px 4px',
            border: '2px solid var(--border)',
            borderRadius: 16,
            background: 'var(--bg-3)',
            overflow: 'hidden',
            boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
          }}>
            {/* Detail header */}
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '8px 16px',
              background: 'var(--bg-4)',
              borderBottom: '2px solid var(--border)',
            }}>
              <span style={{ fontSize: 10, color: s.text, fontWeight: 900, textTransform: 'uppercase', letterSpacing: '1px', display: 'flex', alignItems: 'center', gap: 6 }}>
                <i className={`ti ti-${icon}`} style={{ fontSize: 12 }} />
                {step.action}
              </span>
              <button
                onClick={handleCopy}
                style={{
                  padding: '4px 10px', borderRadius: 8, border: '2px solid var(--border)',
                  background: 'var(--bg-3)', cursor: 'pointer', fontSize: 10, fontWeight: 900,
                  color: 'var(--ink-3)', transition: 'all 0.2s', textTransform: 'uppercase', letterSpacing: '0.5px',
                }}
                onMouseEnter={e => { e.currentTarget.style.background = 'var(--bg-5)'; e.currentTarget.style.borderColor = 'var(--accent-2)' }}
                onMouseLeave={e => { e.currentTarget.style.background = 'var(--bg-3)'; e.currentTarget.style.borderColor = 'var(--border)' }}
              >
                <i className="ti ti-copy" style={{ fontSize: 12, marginRight: 4 }} />
                Copy
              </button>
            </div>

            {/* Code/content area */}
            <pre style={{
              padding: '16px 20px', margin: 0,
              fontSize: 12, fontFamily: 'var(--font-mono, monospace)', lineHeight: 1.7,
              color: 'var(--color-text-secondary, #bbb)', fontWeight: 700,
              overflowX: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-word',
              maxHeight: 350, overflowY: 'auto', background: 'rgba(0,0,0,0.1)',
            }}>
              {getContent()}
              {isActive && step._isLiveThinking && (
                <span style={{
                  display: 'inline-block', width: 8, height: 16,
                  background: '#a78bfa', animation: '_sp-pulse 1s ease-in-out infinite',
                  verticalAlign: 'middle', marginLeft: 4, borderRadius: 2,
                  boxShadow: '0 0 8px rgba(167,139,250,0.5)',
                }} />
              )}
            </pre>

            {/* Open in Artifacts button for Written steps */}
            {step.action === 'Written' && step.code && onOpenArtifactCard && (
              <div style={{
                padding: '8px 16px', borderTop: '2px solid var(--border)',
                background: 'var(--bg-4)', textAlign: 'right',
              }}>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    const ext = (step.language || step.detail?.split('.').pop() || 'txt').toLowerCase()
                    onOpenArtifactCard(
                      step.code + (step.truncated ? '\n\n// [konten dipotong]' : ''),
                      ext, `✍️ ${step.detail?.split('/').pop()}`, false
                    )
                  }}
                  style={{
                    display: 'inline-flex', alignItems: 'center', gap: 8,
                    padding: '6px 16px', borderRadius: 10,
                    background: 'rgba(139,92,246,0.2)', border: '2px solid rgba(139,92,246,0.4)',
                    color: '#a78bfa', fontSize: 11, fontWeight: 900, cursor: 'pointer',
                    textTransform: 'uppercase', letterSpacing: '1px', transition: 'all 0.2s',
                    boxShadow: '0 4px 8px rgba(139,92,246,0.2)',
                  }}
                  onMouseEnter={e => { e.currentTarget.style.background = 'rgba(139,92,246,0.3)'; e.currentTarget.style.transform = 'translateY(-1px)' }}
                  onMouseLeave={e => { e.currentTarget.style.background = 'rgba(139,92,246,0.2)'; e.currentTarget.style.transform = 'translateY(0)' }}
                >
                  <i className="ti ti-external-link" style={{ fontSize: 13 }} />
                  Buka di Artifacts
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// ── ProcessStepsPanel ─────────────────────────────────────────
const ProcessStepsPanel = React.memo(function ProcessStepsPanel({
  steps, isStreaming, onStop, streamingText, onOpenArtifactCard, defaultOpen = true
}) {
  const [open, setOpen] = React.useState(defaultOpen)
  const [staleSeconds, setStaleSeconds] = React.useState(0)
  const staleCountRef = React.useRef(steps.length)

  React.useEffect(() => {
    if (!isStreaming) { setStaleSeconds(0); return }
    if (steps.length !== staleCountRef.current) {
      staleCountRef.current = steps.length
      setStaleSeconds(0)
      return
    }
    const t = setInterval(() => setStaleSeconds(s => s + 1), 1000)
    return () => clearInterval(t)
  }, [steps.length, isStreaming])

  if (!steps || steps.length === 0) return null

  const latest = steps[steps.length - 1]
  const doneCount = isStreaming ? steps.length - 1 : steps.length
  const hasError = steps.some(s => s.action === 'Error')

  const headerLabel = isStreaming
    ? `⚡ ${latest?.action}${latest?.detail ? ` · ${latest.detail}` : '...'}`
    : `✓ Eksekusi selesai (${steps.length} langkah)`

  return (
    <>
      <style>{`
        @keyframes _sp-spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes _sp-pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.45; } }
      `}</style>

      <div style={{ marginBottom: 20, marginTop: 4 }} className="animate-fade">
        <div
          style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: open ? 16 : 0, cursor: 'pointer' }}
          onClick={() => setOpen(o => !o)}
        >
          <i
            className="ti ti-chevron-down"
            style={{
              fontSize: 18, color: 'var(--color-text-tertiary, #777)',
              transition: 'transform 0.3s', transform: open ? 'none' : 'rotate(-90deg)',
            }}
          />
          <i
            className={`ti ti-${hasError ? 'alert-circle' : isStreaming ? 'loader-2' : 'circle-check'}`}
            style={{
              fontSize: 16,
              color: hasError ? '#f87171' : isStreaming ? '#a78bfa' : '#4ade80',
              animation: isStreaming ? '_sp-spin 1.2s linear infinite' : 'none',
              filter: isStreaming ? 'drop-shadow(0 0 8px rgba(167,139,250,0.5))' : 'none',
            }}
          />
          <span style={{ fontSize: 14, fontWeight: 900, color: 'var(--color-text-secondary, #ccc)', flex: 1, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            {headerLabel}
          </span>
          <span className="text-[10px] px-3 py-1 rounded-full bg-bg-3 border border-border text-ink-3 font-bold uppercase tracking-widest shadow-sm">
            {doneCount} / {steps.length} langkah
          </span>
          <_ElapsedBadge active={isStreaming} />
          {isStreaming && (
            <i className="ti ti-loader-2" style={{ fontSize: 16, color: '#a78bfa', animation: '_sp-spin 1s linear infinite', marginLeft: 4 }} />
          )}
        </div>

        {open && (
          <div className="ml-2 pl-6 border-l-2 border-border/50">
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {steps.map((step, i) => (
                <_Step
                  key={i}
                  step={step}
                  idx={i}
                  isActive={i === steps.length - 1 && isStreaming}
                  isLast={i === steps.length - 1}
                  isStreaming={isStreaming}
                  streamingText={streamingText}
                  onOpenArtifactCard={onOpenArtifactCard}
                />
              ))}
            </div>

            {isStreaming && (staleSeconds >= 8 || onStop) && (
              <div style={{ marginTop: 20, marginLeft: 10, display: 'flex', alignItems: 'center', gap: 16 }}>
                {staleSeconds >= 8 && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: '#fbbf24', fontWeight: 900, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    <i className="ti ti-loader-2" style={{ animation: '_sp-spin 1s linear infinite', fontSize: 14 }} />
                    Menunggu pemrosesan tool... ({staleSeconds}s)
                  </div>
                )}
                {onStop && (
                  <button
                    data-allow-propagation="true"
                    onClick={(e) => { e.stopPropagation(); onStop() }}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 8,
                      padding: '6px 16px', borderRadius: 10,
                      background: 'rgba(248,113,113,0.15)', border: '2px solid rgba(248,113,113,0.40)',
                      color: '#f87171', fontSize: 11, fontWeight: 900,
                      cursor: 'pointer', letterSpacing: '1px', textTransform: 'uppercase',
                      transition: 'all 0.2s', boxShadow: '0 4px 8px rgba(248,113,113,0.2)',
                    }}
                    onMouseEnter={e => { e.currentTarget.style.background = 'rgba(248,113,113,0.25)'; e.currentTarget.style.transform = 'translateY(-1px)' }}
                    onMouseLeave={e => { e.currentTarget.style.background = 'rgba(248,113,113,0.15)'; e.currentTarget.style.transform = 'translateY(0)' }}
                  >
                    <i className="ti ti-square-filled" style={{ fontSize: 10 }} />
                    HENTIKAN EKSEKUSI
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </>
  )
})

// ── ArtifactsPanel ────────────────────────────────────────────
function ArtifactsPanel({ code, language, title, isPreviewUrl, onClose }) {
  const isAppPreview = isPreviewUrl || language === 'preview'
  const isHtml = ['html', 'htm', 'svg'].includes((language || '').toLowerCase())

  const [activeTab, setActiveTab] = useState(isAppPreview || isHtml ? 'preview' : 'code')
  const [copied, setCopied] = useState(false)
  const [localCode, setLocalCode] = useState(code)
  const [iframeKey, setIframeKey] = useState(0)
  const [appOnline, setAppOnline] = useState(true)

  useEffect(() => { setLocalCode(code) }, [code])

  const filename  = `artifact.${language || 'txt'}`
  const iframeSrc = isAppPreview
    ? localCode
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
    <div className="flex flex-col border-l-2 border-border bg-bg-2 animate-slide-in-right shadow-2xl" style={{ width: '48%', flexShrink: 0 }}>
      {/* Header */}
      <div className="h-14 border-b-2 border-border flex items-center px-4 gap-3 flex-shrink-0 bg-bg-3">
        {isAppPreview
          ? <span className="text-xl flex-shrink-0">🚀</span>
          : <FileCode2 size={20} className="text-accent-2 flex-shrink-0" />}
        <span className="text-sm font-bold text-ink truncate flex-1 uppercase tracking-tight">{title || filename}</span>

        {isAppPreview && (
          <span className="flex items-center gap-2 px-3 py-1 rounded-full bg-success/15 border border-success/30 text-success text-[10px] font-bold uppercase tracking-widest flex-shrink-0 shadow-sm">
            <span className="w-2 h-2 rounded-full bg-success animate-pulse shadow-lg" />
            Running
          </span>
        )}

        {!isAppPreview && (
          <>
            <span className={clsx('text-[10px] font-mono font-bold px-2 py-0.5 rounded border flex-shrink-0 uppercase tracking-widest shadow-sm', langColor)}>
              {language || 'txt'}
            </span>
            <span className="text-[10px] text-ink-3 font-bold uppercase tracking-widest flex-shrink-0 opacity-60">{lines} baris</span>
          </>
        )}

        <div className="flex items-center gap-1 flex-shrink-0">
          {isAppPreview && (
            <button onClick={() => setIframeKey(k => k + 1)} className="p-2 rounded-xl hover:bg-bg-4 transition-all text-ink-3 hover:text-ink shadow-sm border border-transparent hover:border-border" title="Reload aplikasi">
              <RefreshCw size={18} />
            </button>
          )}
          {isAppPreview && (
            <button onClick={() => window.open(localCode, '_blank')} className="p-2 rounded-xl hover:bg-bg-4 transition-all text-ink-3 hover:text-ink shadow-sm border border-transparent hover:border-border" title="Buka di tab baru">
              <ExternalLink size={18} />
            </button>
          )}
          <button onClick={handleCopy} className="p-2 rounded-xl hover:bg-bg-4 transition-all text-ink-3 hover:text-ink shadow-sm border border-transparent hover:border-border" title={isAppPreview ? 'Copy URL' : 'Copy semua'}>
            {copied ? <Check size={18} className="text-success" /> : <Copy size={18} />}
          </button>
          {!isAppPreview && (
            <button onClick={handleDownload} className="p-2 rounded-xl hover:bg-bg-4 transition-all text-ink-3 hover:text-ink shadow-sm border border-transparent hover:border-border" title={`Download ${filename}`}>
              <Download size={18} />
            </button>
          )}
          <button onClick={onClose} className="p-2 rounded-xl hover:bg-danger/10 hover:text-danger transition-all text-ink-3 shadow-sm border border-transparent hover:border-danger/30" title="Tutup panel">
            <X size={18} />
          </button>
        </div>
      </div>

      {/* URL bar for app previews */}
      {isAppPreview && (
        <div className="flex items-center gap-3 px-4 py-2 border-b-2 border-border bg-bg-3 flex-shrink-0 shadow-inner">
          <span className="text-[10px] text-ink-3 flex-shrink-0 font-bold uppercase tracking-widest opacity-60">URL:</span>
          <span className="flex-1 text-[11px] font-mono text-accent-2 truncate font-bold">{localCode}</span>
          <button onClick={() => window.open(localCode, '_blank')} className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-accent/10 hover:bg-accent/20 border border-accent/20 text-accent-2 text-[10px] font-bold uppercase tracking-widest transition-all flex-shrink-0 shadow-sm active:scale-95">
            <ExternalLink size={12} /> Buka
          </button>
        </div>
      )}

      {/* Tabs */}
      {isHtml && !isAppPreview && (
        <div className="flex border-b-2 border-border flex-shrink-0 bg-bg-3 p-1">
          {['preview', 'code'].map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={clsx(
                'flex-1 py-2 text-xs font-bold uppercase tracking-widest transition-all rounded-xl',
                activeTab === tab
                  ? 'text-accent-2 bg-accent/10 shadow-inner'
                  : 'text-ink-3 hover:text-ink hover:bg-bg-4'
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
        <div className="flex-1 overflow-auto flex flex-col bg-bg-4">
          <textarea
            value={localCode}
            onChange={(e) => setLocalCode(e.target.value)}
            className="flex-1 w-full p-6 font-mono text-[13px] leading-relaxed text-ink-2 bg-transparent border-none resize-none focus:outline-none focus:ring-0 font-semibold shadow-inner"
            spellCheck="false"
            style={{ minHeight: '100%' }}
          />
        </div>
      )}
    </div>
  )
}

export { ProcessStepsPanel, ArtifactsPanel, ACTION_META, DEFAULT_META }
export default ProcessStepsPanel
