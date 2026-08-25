/**
 * MessageList.jsx — Message rendering: Bubble, CodeBlock, ArtifactCard, SuccessCard, SaveFileDialog
 * Extracted from Chat.jsx for modularity.
 */
import React, { useState, useEffect, useCallback, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { copyToClipboard } from '../../utils/clipboard'
import {
  Copy, Check, Download, Bot, User, Square, Zap, CloudUpload,
  ChevronDown, ChevronUp, ChevronRight,
  ExternalLink, FileCode2, Maximize2,
  Terminal, BookOpen, PenLine, Brain, Volume2,
  Plus, X, Loader2, Globe, Sparkles, FileText,
} from 'lucide-react'
import clsx from 'clsx'
import { api } from '../../hooks/useApi'
import toast from 'react-hot-toast'

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

// ── CodeBlock ──────────────────────────────────────────────────
function CodeBlock({ language, code, onOpenArtifact }) {
  const [copied, setCopied] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)
  const lines = code.split('\n').length
  const isLong = lines > 25
  const langColor = LANG_COLORS[language?.toLowerCase()] || 'text-ink-3 bg-bg-5 border-border'

  const handleCopy = () => {
    copyToClipboard(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="code-block-wrapper relative my-3 rounded-xl overflow-hidden border border-border bg-bg-3 shadow-sm">
      <div
        className="flex items-center justify-between px-3 py-1.5 bg-bg-4 cursor-pointer hover:bg-bg-5 transition-all"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2">
          {isExpanded ? <ChevronDown size={14} className="text-ink-3" /> : <ChevronRight size={14} className="text-ink-3" />}
          <span className={clsx('text-[10px] font-mono font-bold uppercase tracking-widest px-1.5 py-0.5 rounded border', langColor)}>
            {language || 'code'}
          </span>
          {!isExpanded && (
            <span className="text-[10px] text-ink-3 opacity-60">{lines} baris — klik untuk lihat</span>
          )}
        </div>
        <div className="flex items-center gap-1.5" onClick={e => e.stopPropagation()}>
          {isLong && onOpenArtifact && (
            <button
              onClick={() => onOpenArtifact(code, language || 'txt')}
              className="flex items-center gap-1.5 px-2 py-0.5 rounded-lg text-[10px] font-bold uppercase tracking-widest transition-all border border-transparent hover:border-accent/20 bg-bg-3 shadow-sm"
              style={{ color: 'var(--accent-2)' }}
              title="Buka di Artifacts Panel"
            >
              <ExternalLink size={11} />
              <span>Artifacts</span>
            </button>
          )}
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 px-2 py-0.5 rounded-lg text-[10px] font-bold uppercase tracking-widest transition-all border border-transparent hover:border-border bg-bg-3 shadow-sm"
            style={{ color: copied ? 'var(--success)' : 'var(--ink-3)' }}
            title="Copy kode"
          >
            {copied ? <Check size={11} /> : <Copy size={11} />}
            <span>{copied ? 'Copied!' : 'Copy'}</span>
          </button>
        </div>
      </div>
      {isExpanded && (
        <pre className="p-4 text-[12.5px] overflow-x-auto leading-relaxed font-mono text-ink-2 bg-transparent m-0 border-none">
          <code className="text-inherit bg-transparent p-0 font-semibold">{code}</code>
        </pre>
      )}
    </div>
  )
}

// ── Parse helpers ─────────────────────────────────────────────
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

function stripSaveMarkers(content) {
  if (!content) return content
  return content.replace(/%%SAVE_FILE%%[\s\S]*?%%END_SAVE%%/g, '').trim()
}

function stripInternalTags(content) {
  if (!content) return content
  return content
    .replace(/<function_calls>[\s\S]*?<\/function_calls>/g, '')
    .replace(/<invoke[\s\S]*?<\/invoke>/g, '')
    .replace(/<parameter[\s\S]*?<\/parameter>/g, '')
    .replace(/<[a-z_]+\s+name="[^"]*"\s*\/>/g, '')
    .replace(/<(?:thinking|think|thought|thought_process)>[\s\S]*?<\/(?:thinking|think|thought|thought_process)>/g, '')
    .replace(/<(?:plan|task|action)>[\s\S]*?<\/(?:plan|task|action)>/g, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

export function parseArtifacts(content) {
  if (!content) return { artifacts: [], cleanContent: content }
  const artifacts = []
  let cleanContent = content
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
      if (line.toLowerCase().startsWith('title:')) { title = line.substring('title:'.length).trim(); codeStartIdx = i + 1 }
      else if (line.toLowerCase().startsWith('language:') || line.toLowerCase().startsWith('lang:')) { language = line.substring(line.indexOf(':') + 1).trim().toLowerCase(); codeStartIdx = i + 1 }
      else if (line.toLowerCase().startsWith('type:')) { const t = line.substring('type:'.length).trim().toLowerCase(); if (['html', 'svg'].includes(t)) language = t; codeStartIdx = i + 1 }
      else break
    }
    const code = lines.slice(codeStartIdx).join('\n').trim()
    if (code) { artifacts.push({ id: `art-${Date.now()}-${markerIndex}`, title, language, code }); markerIndex++ }
  }
  const previewRegex = /%%APP_PREVIEW%%\s*(https?:\/\/[^\s]+)\s*%%END_PREVIEW%%/g
  let previewMatch
  while ((previewMatch = previewRegex.exec(content)) !== null) {
    const url = previewMatch[1].trim()
    artifacts.push({ id: `preview-${Date.now()}-${markerIndex}`, title: 'App Preview', language: 'preview', code: url, isPreviewUrl: true })
    markerIndex++
  }
  cleanContent = cleanContent
    .replace(/%%ARTIFACT%%[\s\S]*?%%END_ARTIFACT%%/g, '')
    .replace(/%%APP_PREVIEW%%[\s\S]*?%%END_PREVIEW%%/g, '')
    .replace(/%%SUCCESS_CARD%%[\s\S]*?%%END_SUCCESS_CARD%%/g, '')
    .replace(/%%SAVE_FILE%%[\s\S]*?%%END_SAVE%%/g, '')
    .replace(/%%[A-Z_]+%%[\s\S]*?%%END_[A-Z_]+%%/g, '')
    .replace(/%%[A-Z_]+%%/g, '')
    .trim()
  if (artifacts.length === 0) {
    const codeBlockRegex = /```(\w+)?\n([\s\S]*?)```/g
    let codeMatch, autoIndex = 0
    while ((codeMatch = codeBlockRegex.exec(content)) !== null) {
      const lang = codeMatch[1] || 'txt'
      const code = codeMatch[2].trim()
      if (code.split('\n').length >= 15) {
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
  }
  return { artifacts, cleanContent }
}

function parseSuccessCards(content) {
  if (!content) return { cards: [], cleanContent: content }
  const cards = []
  let cleanContent = content
  const regex = /%%SUCCESS_CARD%%([\s\S]*?)%%END_SUCCESS_CARD%%/g
  let match
  while ((match = regex.exec(content)) !== null) {
    const block = match[1].trim()
    const card = { title: '', url: '', details: [], note: '' }
    for (const line of block.split('\n')) {
      const l = line.trim()
      if (l.toLowerCase().startsWith('title:')) card.title = l.substring(6).trim()
      else if (l.toLowerCase().startsWith('url:')) card.url = l.substring(4).trim()
      else if (l.toLowerCase().startsWith('note:')) card.note = l.substring(5).trim()
      else if (l.toLowerCase().startsWith('detail:')) card.details.push(l.substring(7).trim())
    }
    cards.push(card)
    cleanContent = cleanContent.replace(match[0], '')
  }
  return { cards, cleanContent: cleanContent.trim() }
}

// ── SuccessCard ───────────────────────────────────────────────
function SuccessCard({ card }) {
  const [copied, setCopied] = useState(false)
  const handleCopyUrl = () => {
    if (!card.url) return
    copyToClipboard(card.url)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  const getDetailMeta = (detail) => {
    const d = detail.toLowerCase()
    if (d.includes('http') || d.includes('url') || d.includes('localhost') || d.includes('port')) return { icon: '🌐', label: 'URL APLIKASI' }
    if (d.includes('server') || d.includes('script') || d.includes('.py') || d.includes('.js')) return { icon: '🖥️', label: 'SERVER' }
    if (d.includes('log') || d.includes('.log') || d.includes('file')) return { icon: '📄', label: 'LOG FILE' }
    return { icon: '⚙️', label: 'DETAIL' }
  }

  return (
    <div style={{
      margin: '12px 0', borderRadius: 16,
      background: 'linear-gradient(135deg, rgba(74,222,128,0.06) 0%, rgba(34,197,94,0.03) 100%)',
      border: '1.5px solid rgba(74,222,128,0.25)',
      overflow: 'hidden', boxShadow: '0 4px 20px rgba(74,222,128,0.08)',
    }}>
      <div style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 10, borderBottom: '1px solid rgba(74,222,128,0.15)', background: 'rgba(74,222,128,0.08)' }}>
        <span style={{ fontSize: 16 }}>✅</span>
        <span style={{ fontWeight: 800, fontSize: 15, color: '#4ade80' }}>{card.title || 'Berhasil!'}</span>
      </div>
      {card.url && (
        <div style={{ margin: '10px 12px 4px', borderRadius: 10, background: 'rgba(56,189,248,0.08)', border: '1px solid rgba(56,189,248,0.2)', padding: '8px 12px', display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ width: 32, height: 32, borderRadius: 8, background: 'rgba(56,189,248,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16, flexShrink: 0 }}>🌐</span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 9, fontWeight: 800, color: 'rgba(56,189,248,0.7)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 2 }}>URL APLIKASI</div>
            <a href={card.url} target="_blank" rel="noopener noreferrer" style={{ fontSize: 13, fontWeight: 700, color: '#38bdf8', fontFamily: 'monospace', wordBreak: 'break-all', textDecoration: 'none' }}>{card.url}</a>
          </div>
          <button onClick={handleCopyUrl} style={{ padding: '4px 10px', borderRadius: 7, border: '1px solid rgba(56,189,248,0.3)', background: 'rgba(56,189,248,0.1)', cursor: 'pointer', fontSize: 11, fontWeight: 700, color: copied ? '#4ade80' : '#38bdf8', transition: 'all 0.2s', flexShrink: 0 }}>{copied ? '✓ Copied' : 'Copy'}</button>
        </div>
      )}
      {card.details.length > 0 && (
        <div style={{ padding: '4px 12px 8px', display: 'flex', flexDirection: 'column', gap: 6 }}>
          {card.details.map((detail, i) => {
            const meta = getDetailMeta(detail)
            const colonIdx = detail.indexOf(':')
            const label = colonIdx > 0 ? detail.substring(0, colonIdx).trim() : meta.label
            const value = colonIdx > 0 ? detail.substring(colonIdx + 1).trim() : detail
            return (
              <div key={i} style={{ borderRadius: 10, background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)', padding: '8px 12px', display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ width: 32, height: 32, borderRadius: 8, background: 'rgba(255,255,255,0.05)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 15, flexShrink: 0 }}>{meta.icon}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 9, fontWeight: 800, color: 'var(--ink-3)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 2 }}>{label.toUpperCase()}</div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink)', fontFamily: 'monospace', wordBreak: 'break-all' }}>{value}</div>
                </div>
              </div>
            )
          })}
        </div>
      )}
      {card.note && (
        <div style={{ margin: '0 12px 12px', borderRadius: 10, background: 'rgba(167,139,250,0.06)', border: '1px solid rgba(167,139,250,0.15)', padding: '8px 12px', display: 'flex', alignItems: 'flex-start', gap: 8 }}>
          <span style={{ fontSize: 14, flexShrink: 0, marginTop: 1 }}>ℹ️</span>
          <span style={{ fontSize: 13, color: 'var(--ink-2)', lineHeight: 1.5 }}>{card.note}</span>
        </div>
      )}
    </div>
  )
}

// ── ArtifactCard ──────────────────────────────────────────────
const ARTIFACT_TYPE_META = {
  html: { icon: Globe, label: 'Web Page', color: 'text-orange-400', bg: 'bg-orange-400/10', border: 'border-orange-400/20' },
  htm: { icon: Globe, label: 'Web Page', color: 'text-orange-400', bg: 'bg-orange-400/10', border: 'border-orange-400/20' },
  svg: { icon: Globe, label: 'SVG Graphic', color: 'text-pink-400', bg: 'bg-pink-400/10', border: 'border-pink-400/20' },
  jsx: { icon: FileCode2, label: 'React Component', color: 'text-cyan-400', bg: 'bg-cyan-400/10', border: 'border-cyan-400/20' },
  tsx: { icon: FileCode2, label: 'React Component', color: 'text-cyan-400', bg: 'bg-cyan-400/10', border: 'border-cyan-400/20' },
  javascript: { icon: FileCode2, label: 'JavaScript', color: 'text-yellow-400', bg: 'bg-yellow-400/10', border: 'border-yellow-400/20' },
  typescript: { icon: FileCode2, label: 'TypeScript', color: 'text-blue-400', bg: 'bg-blue-400/10', border: 'border-blue-400/20' },
  python: { icon: FileCode2, label: 'Python Script', color: 'text-blue-300', bg: 'bg-blue-300/10', border: 'border-blue-300/20' },
  css: { icon: FileCode2, label: 'Stylesheet', color: 'text-pink-400', bg: 'bg-pink-400/10', border: 'border-pink-400/20' },
  sql: { icon: FileCode2, label: 'SQL Query', color: 'text-emerald-400', bg: 'bg-emerald-400/10', border: 'border-emerald-400/20' },
  json: { icon: FileCode2, label: 'JSON Data', color: 'text-amber-400', bg: 'bg-amber-400/10', border: 'border-amber-400/20' },
  bash: { icon: Terminal, label: 'Shell Script', color: 'text-green-400', bg: 'bg-green-400/10', border: 'border-green-400/20' },
  sh: { icon: Terminal, label: 'Shell Script', color: 'text-green-400', bg: 'bg-green-400/10', border: 'border-green-400/20' },
  markdown: { icon: BookOpen, label: 'Document', color: 'text-violet-400', bg: 'bg-violet-400/10', border: 'border-violet-400/20' },
  md: { icon: BookOpen, label: 'Document', color: 'text-violet-400', bg: 'bg-violet-400/10', border: 'border-violet-400/20' },
}
const DEFAULT_ARTIFACT_META = { icon: FileCode2, label: 'Code', color: 'text-accent-2', bg: 'bg-accent/10', border: 'border-accent/20' }

function ArtifactCard({ artifact, onOpen }) {
  const [copied, setCopied] = useState(false)
  const meta = ARTIFACT_TYPE_META[artifact.language?.toLowerCase()] || DEFAULT_ARTIFACT_META
  const ArtIcon = meta.icon
  const lines = artifact.code.split('\n')
  const previewLines = lines.slice(0, 6).join('\n')
  const isPreviewable = ['html', 'htm', 'svg'].includes((artifact.language || '').toLowerCase())

  const handleCopy = (e) => { e.stopPropagation(); copyToClipboard(artifact.code); setCopied(true); setTimeout(() => setCopied(false), 2000) }
  const handleDownload = (e) => {
    e.stopPropagation()
    const blob = new Blob([artifact.code], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `${artifact.title.replace(/\s+/g, '_').toLowerCase()}.${artifact.language || 'txt'}`; a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="mt-4 border-[0.5px] border-border rounded-2xl overflow-hidden bg-bg-2 hover:border-accent/50 transition-all cursor-pointer shadow-sm group animate-slide-in-up" onClick={() => onOpen(artifact)}>
      <div className="flex items-center gap-3 px-4 py-3 bg-bg-3/50 border-b-[0.5px] border-border">
        <div className={clsx('w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0', meta.bg)}><ArtIcon size={16} className={meta.color} /></div>
        <div className="flex-1 min-w-0">
          <div className="text-[13px] font-semibold text-ink truncate">{artifact.title}</div>
          <div className="flex items-center gap-2 mt-0.5">
            <span className={clsx('text-[10px] font-mono font-semibold uppercase tracking-widest px-1.5 py-0.5 rounded border-[0.5px]', meta.bg, meta.color, meta.border)}>{artifact.language || 'txt'}</span>
            <span className="text-[10px] text-ink-3">{lines.length} lines</span>
            {isPreviewable && <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-success/10 text-success border border-success/20 font-medium">✦ Live Preview</span>}
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button onClick={handleCopy} className="p-1.5 rounded-lg hover:bg-bg-5 transition-colors" title="Copy">{copied ? <Check size={12} className="text-success" /> : <Copy size={12} className="text-ink-3" />}</button>
          <button onClick={handleDownload} className="p-1.5 rounded-lg hover:bg-bg-5 transition-colors" title="Download"><Download size={12} className="text-ink-3" /></button>
        </div>
      </div>
      <div className="artifact-card-preview"><code>{previewLines}</code></div>
      <div className="artifact-card-actions">
        <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-accent/10 hover:bg-accent/20 border border-accent/20 text-accent-2 text-[11px] font-medium transition-all flex-1 justify-center" onClick={(e) => { e.stopPropagation(); onOpen(artifact) }}>
          <Maximize2 size={11} /> Buka & Edit di Panel
        </button>
      </div>
    </div>
  )
}

// ── SaveFileDialog ────────────────────────────────────────────
function SaveFileDialog({ filename, content, onClose }) {
  const [directory, setDirectory] = useState('')
  const [dirs, setDirs] = useState([])
  const [currentPath, setCurrentPath] = useState('')
  const [parentPath, setParentPath] = useState('')
  const [customFilename, setCustomFilename] = useState(filename || 'output.txt')
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(true)
  const [showNewFolder, setShowNewFolder] = useState(false)
  const [newFolderName, setNewFolderName] = useState('')
  const [creatingFolder, setCreatingFolder] = useState(false)

  useEffect(() => { loadDirs('~') }, [])

  async function loadDirs(path) {
    setLoading(true); setShowNewFolder(false); setNewFolderName('')
    try {
      const result = await api.listDirectories(path)
      setDirs(result.directories || []); setCurrentPath(result.path || path); setParentPath(result.parent || ''); setDirectory(result.path || path)
    } catch { toast.error('Gagal memuat direktori') }
    setLoading(false)
  }

  async function handleCreateFolder(e) {
    e.preventDefault(); if (!newFolderName.trim()) return; setCreatingFolder(true)
    try { const result = await api.createDirectory(currentPath, newFolderName.trim()); toast.success(result.message || 'Folder berhasil dibuat'); loadDirs(result.path) }
    catch (e) { toast.error(e.message || 'Gagal membuat folder') }
    setCreatingFolder(false)
  }

  async function handleSave() {
    if (!directory) return toast.error('Pilih direktori tujuan'); setSaving(true)
    try { const result = await api.saveFile(directory, customFilename, content); toast.success(`✅ Tersimpan: ${result.path}`, { duration: 4000 }); onClose() }
    catch (e) { toast.error(e.message || 'Gagal menyimpan file') }
    setSaving(false)
  }

  function handleDownload() {
    const blob = new Blob([content], { type: 'text/plain' }); const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url; a.download = customFilename; a.click(); URL.revokeObjectURL(url)
    toast.success('📥 File di-download ke browser'); onClose()
  }

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fade" onClick={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <div className="bg-bg-2 border border-border rounded-3xl w-[500px] max-w-[90vw] max-h-[80vh] flex flex-col shadow-2xl animate-slide-in-up overflow-hidden">
        <div className="flex items-center justify-between px-6 py-5 border-b-2 border-border bg-bg-3">
          <div className="flex items-center gap-3"><Download size={22} className="text-accent-2" /><span className="text-lg font-bold text-ink uppercase tracking-tight">Simpan File</span></div>
          <button onClick={onClose} className="p-2 rounded-xl hover:bg-danger/10 hover:text-danger transition-all text-ink-3"><X size={20} /></button>
        </div>
        <div className="px-6 py-4 border-b-2 border-border/50 bg-bg-4 shadow-inner">
          <label className="text-[10px] text-ink-3 uppercase tracking-widest font-bold mb-2 block opacity-60">Nama File</label>
          <input value={customFilename} onChange={e => setCustomFilename(e.target.value)} className="w-full px-4 py-3 bg-bg-2 border border-border rounded-xl text-sm text-ink font-mono font-bold focus:outline-none focus:border-accent transition-all shadow-sm" />
        </div>
        <div className="px-6 py-4 flex-1 overflow-hidden flex flex-col bg-bg-2">
          <div className="flex items-center justify-between mb-2">
            <label className="text-[10px] text-ink-3 uppercase tracking-widest font-bold block opacity-60">Direktori Tujuan</label>
            <button onClick={() => setShowNewFolder(!showNewFolder)} className="text-[10px] flex items-center gap-2 font-bold text-accent-2 hover:text-accent-2/80 transition-all uppercase tracking-widest"><Plus size={14} /> Buat Folder</button>
          </div>
          <div className="flex items-center gap-1.5 mb-2">
            <div className="flex-1 px-3 py-1.5 bg-bg-3 border border-border rounded-lg text-xs text-ink font-mono truncate" title={currentPath || '~'}>📁 {currentPath || '~'}</div>
            {parentPath && (<button onClick={() => loadDirs(parentPath)} className="px-2 py-1.5 bg-bg-4 border border-border rounded-lg text-xs text-ink-3 hover:text-ink hover:bg-bg-5 transition-colors flex-shrink-0" title="Naik ke folder induk">⬆️</button>)}
          </div>
          {showNewFolder && (
            <form onSubmit={handleCreateFolder} className="flex gap-2 mb-2 animate-fade">
              <input autoFocus placeholder="Nama folder baru..." value={newFolderName} onChange={e => setNewFolderName(e.target.value)} className="flex-1 px-3 py-1.5 bg-bg-3 border border-border rounded-lg text-xs text-ink focus:outline-none focus:border-accent-2" />
              <button type="submit" disabled={creatingFolder || !newFolderName.trim()} className="px-3 py-1.5 rounded-lg bg-accent-2/10 text-accent-2 border border-accent-2/20 text-xs font-medium hover:bg-accent-2/20 disabled:opacity-50 transition-colors">{creatingFolder ? 'Membuat...' : 'Buat'}</button>
            </form>
          )}
          <div className="flex-1 overflow-y-auto border border-border rounded-lg bg-bg-3 min-h-[140px] max-h-[200px]">
            {loading ? (
              <div className="flex items-center justify-center py-8"><Loader2 size={18} className="animate-spin text-accent-2" /></div>
            ) : dirs.length === 0 ? (
              <div className="text-center text-xs text-ink-3 py-8">Tidak ada subdirektori</div>
            ) : (
              dirs.map((d, i) => (
                <button key={i} onClick={() => loadDirs(d.path)} className="w-full flex items-center gap-2 px-3 py-2 text-left text-xs hover:bg-accent/10 transition-colors border-b border-border/30 last:border-b-0">
                  <span className="text-amber-400">📂</span><span className="text-ink truncate">{d.name}</span>
                </button>
              ))
            )}
          </div>
        </div>
        <div className="flex items-center justify-between px-5 py-4 border-t border-border gap-2">
          <button onClick={handleDownload} className="px-3 py-2 text-xs font-medium rounded-lg bg-bg-4 border border-border text-ink-2 hover:bg-bg-5 hover:text-ink transition-all flex items-center gap-1.5"><Download size={13} /> Download</button>
          <div className="flex gap-2">
            <button onClick={onClose} className="px-4 py-2 text-xs font-medium rounded-lg bg-bg-4 border border-border text-ink-3 hover:text-ink transition-colors">Batal</button>
            <button onClick={handleSave} disabled={saving || !directory} className="px-4 py-2 text-xs font-semibold rounded-lg bg-accent text-white hover:bg-accent/80 transition-colors disabled:opacity-40 flex items-center gap-1.5">
              {saving ? <Loader2 size={13} className="animate-spin" /> : <Check size={13} />} Simpan ke Server
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Bubble (message bubble) ───────────────────────────────────
export const Bubble = React.memo(function Bubble({ msg, isStreaming, onStop, onExport, onSpeak, speakingId, onOpenArtifact, onOpenArtifactCard, onDriveUpload, ProcessStepsPanel }) {
  const [copied, setCopied] = useState(false)
  const [showThinking, setShowThinking] = useState(false)
  const [showSaveDialog, setShowSaveDialog] = useState(false)
  const isUser = msg.role === 'user'

  const saveFileData = !isUser ? parseSaveFileMarker(msg.content) : null

  const splitContent = (content) => {
    let processedContent = stripSaveMarkers(content || '')
    processedContent = stripInternalTags(processedContent)
    try {
      const cleanJson = processedContent.replace(/^```json\s*/i, '').replace(/\s*```$/, '').trim()
      if (cleanJson.startsWith('{') && cleanJson.endsWith('}')) {
        const parsed = JSON.parse(cleanJson)
        if (parsed.response && parsed.model_used) processedContent = parsed.response
      }
    } catch {}
    if (!processedContent) return { mainContent: '', thinkingContent: null, hasThinking: false }
    const thinkStart = processedContent.indexOf('🤔 Proses Berpikir:')
    if (thinkStart === -1) return { mainContent: processedContent, thinkingContent: null, hasThinking: false }
    const beforeThink = processedContent.substring(0, thinkStart).trim()
    const afterThinkStart = thinkStart + '🤔 Proses Berpikir:'.length
    const remaining = processedContent.substring(afterThinkStart)
    const endMarkerIndex = remaining.indexOf('---')
    let thinkingContent = '', mainContentAfterThink = ''
    if (endMarkerIndex !== -1) {
      thinkingContent = remaining.substring(0, endMarkerIndex).trim()
      mainContentAfterThink = remaining.substring(endMarkerIndex + 3).trim()
    } else {
      const lines = remaining.split('\n')
      let thinkLineEnd = lines.length, foundThinkEnd = false
      for (let i = 0; i < lines.length; i++) {
        const trimmed = lines[i].trim()
        const isResponseStart = (trimmed && !trimmed.startsWith('Plan') && !trimmed.startsWith('Tool') && !trimmed.startsWith('Action') && !trimmed.startsWith('Thought') && !trimmed.startsWith('Analysis') && !trimmed.startsWith('Step') && !trimmed.startsWith('-') && !trimmed.startsWith('•') && !trimmed.match(/^[A-Z][a-z]+:/) && (trimmed.startsWith('I\'') || trimmed.startsWith('The ') || trimmed.startsWith('Here') || trimmed.startsWith('Let') || trimmed.startsWith('I will') || trimmed.startsWith('Sure') || /^(Okay|Alright|Got it|Understood|Yes|No|Great|Perfect|Baik|Oke|Tentu|Saya|Ini|Berikut|Sebagai|Data|Hasil)/i.test(trimmed)))
        if (isResponseStart && i > 0) { thinkLineEnd = i; foundThinkEnd = true; break }
      }
      thinkingContent = lines.slice(0, thinkLineEnd).join('\n').trim()
      if (foundThinkEnd) mainContentAfterThink = lines.slice(thinkLineEnd).join('\n').trim()
    }
    let mainContent = beforeThink
    if (mainContentAfterThink) mainContent = (beforeThink ? beforeThink + '\n\n' : '') + mainContentAfterThink
    return { mainContent: mainContent.trim(), thinkingContent, hasThinking: true }
  }

  const { mainContent, thinkingContent: parsedThinking, hasThinking: parsedHasThinking } = splitContent(msg.content || '')
  const thinkingContent = msg.thinking_process || parsedThinking
  const hasThinking = !!msg.thinking_process || parsedHasThinking

  let parsedProcessSteps = null
  if (hasThinking && msg.thinking_process) {
    try { const parsed = JSON.parse(msg.thinking_process); if (Array.isArray(parsed) && parsed.length > 0) parsedProcessSteps = parsed } catch {}
  }

  const { cards: successCards, cleanContent: contentWithoutCards } = !isUser ? parseSuccessCards(mainContent) : { cards: [], cleanContent: mainContent }
  const { artifacts: parsedArtifacts, cleanContent: finalContent } = !isUser ? parseArtifacts(contentWithoutCards) : { artifacts: [], cleanContent: contentWithoutCards }
  const displayContent = finalContent

  const copy = () => { copyToClipboard(msg.content); setCopied(true); setTimeout(() => setCopied(false), 2000) }

  const markdownComponents = {
    code({ node, inline, className, children, ...props }) {
      const match = /language-(\w+)/.exec(className || '')
      const language = match ? match[1] : ''
      const codeText = String(children).replace(/\n$/, '')
      if (inline) return <code className="px-1.5 py-0.5 bg-accent/10 rounded text-accent-2 text-[12px] font-mono border border-accent/20 break-words" {...props}>{children}</code>
      if (!language && codeText.split('\n').length === 1 && codeText.length < 120) return <code className="inline-block px-1.5 py-0.5 mx-1 bg-bg-4 rounded text-ink-2 text-[13px] font-mono border border-border break-words align-middle" {...props}>{codeText}</code>
      return <CodeBlock language={language} code={codeText} onOpenArtifact={onOpenArtifact} />
    },
    a({ node, href, children, ...props }) {
      const isLocalServer = href && (href.includes('localhost') || href.includes('127.0.0.1') || href.includes('0.0.0.0') || /:\d{4,5}/.test(href))
      return (<a href={href} target="_blank" rel="noopener noreferrer" className="text-accent-2 underline underline-offset-2 hover:text-accent transition-colors" title={isLocalServer ? `Buka ${href} di tab baru` : href} {...props}>{children}{isLocalServer && <ExternalLink size={10} className="inline ml-0.5 mb-0.5 opacity-70" />}</a>)
    },
    img({ node, src, alt, ...props }) {
      const [imgState, setImgState] = useState('loading')
      const [retryCount, setRetryCount] = useState(0)
      const imgSrc = retryCount > 0 ? `${src}${src.includes('?') ? '&' : '?'}_r=${retryCount}` : src
      return (
        <div className="my-3 rounded-xl overflow-hidden border border-border bg-bg-3 inline-block max-w-full">
          {imgState === 'loading' && <div className="flex items-center gap-2 px-4 py-3 text-ink-3 text-sm"><span className="inline-block w-4 h-4 border-2 border-accent/30 border-t-accent rounded-full animate-spin" /> Memuat gambar...</div>}
          <img src={imgSrc} alt={alt || 'Generated Image'} className="max-w-full max-h-[500px] object-contain rounded-xl" style={{ display: imgState === 'loaded' ? 'block' : 'none' }} onLoad={() => setImgState('loaded')} onError={() => setImgState('error')} {...props} />
          {imgState === 'error' && (
            <div className="flex flex-col items-center gap-2 px-6 py-4 text-center">
              <span className="text-2xl">🖼️</span><span className="text-sm text-ink-3">Gagal memuat gambar</span>
              <button onClick={() => { setImgState('loading'); setRetryCount(c => c + 1) }} className="px-3 py-1.5 text-xs font-medium rounded-lg bg-accent/10 text-accent-2 border border-accent/20 hover:bg-accent/20 transition-colors">🔄 Coba Lagi</button>
            </div>
          )}
        </div>
      )
    }
  }

  return (
    <div className={clsx('flex gap-2.5 group animate-fade', isUser ? 'flex-row-reverse' : 'flex-row')}>
      <div className={clsx('w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5', isUser ? 'bg-gradient-to-br from-accent to-pink' : 'bg-gradient-to-br from-accent to-accent-2')}>
        {isUser ? <User size={13} className="text-white" /> : <Bot size={13} className="text-white" />}
      </div>
      <div className={clsx('max-w-[98%] lg:max-w-[95%] xl:max-w-[92%] flex flex-col', isUser ? 'items-end' : 'items-start')}>
        <div className={clsx('px-4 py-3 rounded-2xl text-[15px] leading-relaxed relative border-[0.5px]', isUser ? 'bg-accent text-white border-accent shadow-sm' : 'bg-bg-2 border-border text-ink shadow-sm')}>
          {isUser && msg._image_preview && <img src={msg._image_preview} alt="Gambar yang dikirim" className="max-w-[200px] max-h-[150px] rounded-lg mb-2 object-cover border border-white/20" />}
          {isUser ? (
            <div className="flex flex-col gap-2">
              {msg.attachedFiles?.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mb-1">
                  {msg.attachedFiles.map((f) => (<span key={f.id} className="flex items-center gap-1 px-2 py-0.5 rounded-md bg-white/20 text-white text-[10px] border border-white/30 backdrop-blur-sm"><span className="flex-shrink-0">{f.meta?.icon || '📄'}</span><span className="truncate max-w-[100px]">{f.name}</span></span>))}
                </div>
              )}
              <p className="whitespace-pre-wrap leading-relaxed">{msg.original_content || msg.content}</p>
            </div>
          ) : (
            <div className="prose prose-sm max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>{displayContent}</ReactMarkdown>
              {isStreaming && <span className="inline-block w-1.5 h-4 bg-accent-2 animate-pulse2 ml-0.5 align-middle" />}
              {parsedProcessSteps ? (
                <div className="mt-3"><ProcessStepsPanel steps={parsedProcessSteps} isStreaming={isStreaming} onOpenArtifactCard={onOpenArtifactCard} defaultOpen={isStreaming} /></div>
              ) : hasThinking ? (
                <div className="mt-3 border border-border rounded-lg overflow-hidden">
                  <button onClick={() => setShowThinking(!showThinking)} className="w-full flex items-center justify-between px-3 py-2 bg-bg-3 hover:bg-bg-5 transition-colors text-xs text-ink-3">
                    <span className="flex items-center gap-1.5"><Brain size={12} className="text-accent" /> 🤔 Proses Berpikir</span>
                    {showThinking ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </button>
                  {showThinking && (
                    <div className="px-3 py-2 bg-bg-2 text-[11px] text-ink-3 leading-relaxed max-h-48 overflow-y-auto">
                      {thinkingContent.split('\n').map((line, i) => line.trim() && (<div key={i} className="flex gap-2 py-0.5"><span className="text-accent flex-shrink-0">•</span><span className="flex-1">{line.trim()}</span></div>))}
                    </div>
                  )}
                </div>
              ) : null}
              {parsedArtifacts.length > 0 && !isStreaming && parsedArtifacts.map(art => (
                <ArtifactCard key={art.id} artifact={art} onOpen={(artifact) => { if (onOpenArtifactCard) onOpenArtifactCard(artifact.code, artifact.language, artifact.title, artifact.isPreviewUrl); else if (onOpenArtifact) onOpenArtifact(artifact.code, artifact.language) }} />
              ))}
              {successCards && successCards.length > 0 && successCards.map((card, i) => <SuccessCard key={i} card={card} />)}
            </div>
          )}
        </div>
        {saveFileData && !isStreaming && (
          <button onClick={() => setShowSaveDialog(true)} className="mt-2 flex items-center gap-2 px-3 py-2 rounded-lg bg-gradient-to-r from-accent/20 to-accent-2/20 border border-accent/30 text-accent-2 text-xs font-semibold hover:from-accent/30 hover:to-accent-2/30 transition-all group">
            <Download size={14} className="group-hover:animate-bounce" /> 💾 Simpan File: <span className="font-mono text-[11px] text-ink">{saveFileData.filename}</span>
          </button>
        )}
        {showSaveDialog && saveFileData && <SaveFileDialog filename={saveFileData.filename} content={saveFileData.content} onClose={() => setShowSaveDialog(false)} />}
        <div className="flex items-center gap-2 mt-1 px-1">
          <span className="text-[10px] text-ink-3 opacity-0 group-hover:opacity-100 transition-opacity">
            {new Date(msg.created_at || Date.now()).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' })}
          </span>
          {!isUser && msg.model && <span className="text-[10px] font-mono text-ink-3 opacity-0 group-hover:opacity-100 transition-opacity">{msg.model?.split('/').pop()}</span>}
          {isStreaming && onStop && (
            <button onClick={onStop} className="flex items-center gap-1 px-2 py-0.5 rounded-md bg-danger/15 hover:bg-danger/25 border border-danger/30 text-danger text-[10px] font-medium transition-all" title="Hentikan (Esc)">
              <Square size={9} fill="currentColor" /> Stop
            </button>
          )}
          {!isUser && !isStreaming && (
            <div className="flex items-center gap-1 relative">
              {onDriveUpload && <button onClick={() => onDriveUpload(msg)} className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-bg-5 transition-all outline-none" title="Simpan ke Google Drive"><CloudUpload size={11} className="text-accent" /></button>}
              <div className="relative dropdown-container">
                <button onClick={(e) => { const el = e.currentTarget.nextElementSibling; const isHidden = el.style.display === 'none' || el.style.display === ''; document.querySelectorAll('.export-dropdown').forEach(d => d.style.display = 'none'); if (isHidden) el.style.display = 'block' }} className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-bg-5 transition-all outline-none" title="Download Chat (PDF/Word/Excel)">
                  <Download size={11} className="text-accent-2" />
                </button>
                <div className="export-dropdown absolute right-0 bottom-full mb-1 w-36 bg-bg-2 border border-border shadow-md rounded-lg overflow-hidden z-50 text-[11px] animate-fade" style={{ display: 'none' }}>
                  <div className="px-2.5 py-1.5 text-[9px] font-semibold text-ink-3 tracking-wider bg-bg-3 border-b border-border uppercase">Export Format</div>
                  {[{f:'pdf',icon:'📄',label:'PDF Document'},{f:'docx',icon:'📝',label:'Word (DOCX)'},{f:'xlsx',icon:'📊',label:'Excel (XLSX)'},{f:'txt',icon:'📜',label:'Plain Text'}].map(({f,icon,label}) => (
                    <button key={f} onClick={() => { document.querySelectorAll('.export-dropdown').forEach(d => d.style.display = 'none'); onExport(f, msg.id) }} className="w-full text-left px-3 py-2 text-ink hover:bg-bg-4 hover:text-accent transition-colors flex items-center gap-2">
                      <span>{icon}</span> {label}
                    </button>
                  ))}
                </div>
              </div>
              {!isUser && <button onClick={() => onSpeak(msg)} className={clsx("opacity-0 group-hover:opacity-100 p-0.5 rounded transition-all outline-none", speakingId === msg.id ? "bg-accent/20 text-accent opacity-100" : "hover:bg-bg-5 text-ink-3 hover:text-ink")} title="Dengarkan (TTS)"><Volume2 size={11} className={speakingId === msg.id ? "animate-pulse" : ""} /></button>}
              {!isUser && hasThinking && <button onClick={() => setShowThinking(!showThinking)} className={clsx("opacity-0 group-hover:opacity-100 p-0.5 rounded transition-all outline-none", showThinking ? "bg-accent/20 text-accent opacity-100" : "hover:bg-bg-5 text-ink-3 hover:text-ink")} title="Tampilkan Thinking"><Brain size={11} /></button>}
              <button onClick={copy} className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-bg-5 transition-all outline-none" title="Copy ke clipboard">{copied ? <Check size={10} className="text-success" /> : <Copy size={10} className="text-ink-3" />}</button>
            </div>
          )}
        </div>
        {!isUser && msg.rag_sources && (() => {
          try {
            const src = JSON.parse(msg.rag_sources)
            if (src.length > 0) return (<div className="mt-1 flex flex-wrap gap-1">{src.map((s, i) => (<span key={i} className="text-[10px] px-1.5 py-0.5 bg-success/10 text-success border border-success/20 rounded-full">📄 {s}</span>))}</div>)
          } catch {}
          return null
        })()}
      </div>
    </div>
  )
})

// ── SessionItem ───────────────────────────────────────────────
export function SessionItem({ session, active, onClick, onDelete }) {
  return (
    <div onClick={onClick} className={clsx('group flex items-center gap-2 px-2.5 py-2 rounded-lg cursor-pointer mb-0.5 transition-all', active ? 'bg-accent/10 border border-accent/20' : 'hover:bg-bg-4')}>
      <div className="flex-1 min-w-0">
        <div className={clsx('text-xs truncate', active ? 'text-accent-2 font-medium' : 'text-ink-2')}>{session.title || 'New Chat'}</div>
        <div className="text-[10px] text-ink-3 mt-0.5">{session.model_used?.split('/').pop() || 'AI'} · {new Date(session.updated_at || session.created_at).toLocaleDateString('id-ID', { day: 'numeric', month: 'short' })}</div>
      </div>
      <button onClick={(e) => { e.stopPropagation(); onDelete(session.id) }} className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-danger/10 flex-shrink-0">
        <span className="text-danger"><X size={11} /></span>
      </button>
    </div>
  )
}

export default Bubble
