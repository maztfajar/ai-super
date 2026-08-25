/**
 * ChatInput.jsx — Input area: textarea, file attach, voice, send/stop
 * Extracted from Chat.jsx for modularity.
 */
import React, { useRef, useState, useCallback } from 'react'
import {
  Plus, Send, Paperclip, Square, Loader2, X,
  ImagePlus, Mic, MicOff, FilePlus
} from 'lucide-react'
import clsx from 'clsx'
import { api } from '../../hooks/useApi'
import toast from 'react-hot-toast'

// ── FileChip ─────────────────────────────────────────────────
function FileChip({ file, onRemove }) {
  return (
    <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-bg-4 border border-border text-[11px] animate-fade">
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
  )
}

// ── DragOverlay ──────────────────────────────────────────────
export function DragOverlay({ isVisible }) {
  if (!isVisible) return null
  return (
    <div className="absolute inset-0 z-50 flex items-center justify-center bg-bg-2/80 backdrop-blur-sm border border-dashed border-accent m-4 rounded-2xl animate-fade">
      <div className="flex flex-col items-center p-6 bg-bg-3 border border-accent/20 rounded-xl shadow-2xl">
        <div className="text-4xl mb-2 animate-bounce">📂</div>
        <p className="text-sm font-semibold text-ink">Lepaskan file di sini</p>
        <p className="text-xs text-ink-3 mt-1 text-center">
          PDF, DOCX, XLSX, CSV, TXT, Gambar
        </p>
      </div>
    </div>
  )
}

// ── Main ChatInput component ─────────────────────────────────
export default function ChatInput({
  input,
  setInput,
  streaming,
  streamingText,
  currentSession,
  onSend,
  onStop,
  // File / drag
  attachedFiles,
  removeFile,
  addFiles,
  fileError,
  // Image
  pendingImage,
  setPendingImage,
  // Voice
  selectedOrchestrator,
}) {
  const inputRef = useRef(null)
  const fileInputRef = useRef(null)
  const chatContextFileRef = useRef(null)
  const imagePickerRef = useRef(null)
  const mediaRecorderRef = useRef(null)

  const [showMobileAttachMenu, setShowMobileAttachMenu] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [isTranscribing, setIsTranscribing] = useState(false)

  // ── Image picker ───────────────────────────────────────────
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
    } catch {
      toast.dismiss()
      toast.error('Gagal memuat gambar')
    }
    e.target.value = ''
  }

  // ── Voice recording ────────────────────────────────────────
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

  // ── RAG upload ─────────────────────────────────────────────
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

  // ── Keyboard ───────────────────────────────────────────────
  function handleKeyDown(e) {
    if (e.key === 'Escape' && streaming) {
      e.preventDefault()
      onStop()
      return
    }
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onSend()
    }
  }

  // expose inputRef to parent (for auto-focus after send)
  React.useImperativeHandle(
    React.useRef(null), // unused — parent accesses via callback
    () => ({ focus: () => inputRef.current?.focus() }),
  )

  // Auto-focus after streaming ends
  React.useEffect(() => {
    if (!streaming) {
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [streaming])

  const SLASH_COMMANDS = [
    { cmd: '/buat', label: '/buat <nama project>', desc: 'Buat aplikasi baru & pilih lokasi folder penyimpanan', icon: '🚀' },
    { cmd: '/edit', label: '/edit <nama file>', desc: 'Pilih & modifikasi file di server', icon: '✏️' },
    { cmd: '/buka', label: '/buka <nama folder>', desc: 'Buka direktori/file di server', icon: '📂' },
    { cmd: '/rag', label: '/rag <pertanyaan>', desc: 'Cari informasi dalam RAG Knowledge Base', icon: '📚' },
  ]

  const showSlashMenu = input.startsWith('/') && !input.includes(' ') && !streaming
  const filteredSlash = SLASH_COMMANDS.filter(s => s.cmd.toLowerCase().startsWith(input.toLowerCase()))

  return (
    <div className="p-4 border-t-[0.5px] border-border bg-bg flex-shrink-0 relative">

      {/* Slash command suggestions popup */}
      {showSlashMenu && filteredSlash.length > 0 && (
        <div className="absolute bottom-full left-4 right-4 mb-2 bg-bg-2 border border-border rounded-2xl shadow-2xl p-2 z-50 animate-slide-in-up">
          <div className="text-[10px] font-bold text-ink-3 uppercase tracking-widest px-3 py-1.5 border-b border-border/50 flex items-center justify-between">
            <span>Perintah Cepat (Slash Commands)</span>
            <span className="opacity-60">Tab atau klik untuk pilih</span>
          </div>
          <div className="space-y-1 mt-1">
            {filteredSlash.map((s) => (
              <button
                key={s.cmd}
                type="button"
                onClick={() => {
                  setInput(`${s.cmd} `)
                  inputRef.current?.focus()
                }}
                className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-bg-3 text-left transition-all group"
              >
                <span className="text-lg flex-shrink-0">{s.icon}</span>
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-bold text-ink font-mono group-hover:text-accent transition-colors">{s.label}</div>
                  <div className="text-[11px] text-ink-3 truncate">{s.desc}</div>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

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

      {/* Preview gambar */}
      {pendingImage && (
        <div className="flex items-center gap-2 mb-2 px-1 animate-fade">
          <div className="relative">
            <img
              src={pendingImage.preview}
              alt="Preview gambar"
              className="h-14 w-14 object-cover rounded-lg border border-border"
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

      {/* Lampiran */}
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
        {/* Hidden inputs */}
        <input ref={fileInputRef} type="file" className="hidden" onChange={handleFileUpload} accept=".pdf,.docx,.txt,.csv,.md" />
        <input
          ref={chatContextFileRef}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => { if (e.target.files) addFiles(e.target.files); e.target.value = '' }}
          accept=".pdf,.docx,.doc,.xlsx,.xls,.csv,.txt,.md,.png,.jpg,.jpeg,.webp"
        />
        <input ref={imagePickerRef} type="file" className="hidden" onChange={handleImagePick} accept="image/*" />

        {/* Attach toggle + menu */}
        <div className="relative flex items-end gap-2">
          <button
            onClick={() => setShowMobileAttachMenu(!showMobileAttachMenu)}
            className="md:hidden w-11 h-11 active:scale-95 flex-shrink-0 flex items-center justify-center rounded-xl border border-border bg-bg-4 hover:bg-bg-5 text-ink-2 hover:text-ink transition-all disabled:opacity-40"
            disabled={streaming}
          >
            <Plus size={18} className={clsx("transition-transform duration-200", showMobileAttachMenu && "rotate-45")} />
          </button>

          <div className={clsx(
            "flex md:flex-row gap-2 transition-all duration-200",
            "absolute md:relative bottom-[110%] md:bottom-auto left-0 md:left-auto flex-col-reverse bg-bg-3 md:bg-transparent border border-border md:border-none p-2 md:p-0 rounded-2xl shadow-2xl md:shadow-none z-50",
            showMobileAttachMenu
              ? "opacity-100 pointer-events-auto translate-y-0 scale-100"
              : "opacity-0 pointer-events-none translate-y-2 scale-95 md:opacity-100 md:pointer-events-auto md:translate-y-0 md:scale-100"
          )}>
            <button
              onClick={() => { chatContextFileRef.current?.click(); setShowMobileAttachMenu(false) }}
              disabled={streaming}
              className="w-11 h-11 md:w-9 md:h-9 active:scale-95 flex-shrink-0 flex items-center justify-center rounded-xl md:rounded-lg border border-border bg-bg-4 hover:bg-bg-5 text-ink-2 hover:text-ink transition-all disabled:opacity-40"
              title="Lampirkan file (PDF, Excel, Word) ke chat"
            >
              <FilePlus size={16} className="md:w-[15px] md:h-[15px]" />
            </button>

            <button
              onClick={() => { fileInputRef.current?.click(); setShowMobileAttachMenu(false) }}
              disabled={streaming}
              className="w-11 h-11 md:w-9 md:h-9 active:scale-95 flex-shrink-0 flex items-center justify-center rounded-xl md:rounded-lg border border-border bg-bg-4 hover:bg-bg-5 text-ink-2 hover:text-ink transition-all disabled:opacity-40"
              title="Upload file ke Knowledge Base"
            >
              <Paperclip size={16} className="md:w-[15px] md:h-[15px]" />
            </button>

            <button
              onClick={() => { imagePickerRef.current?.click(); setShowMobileAttachMenu(false) }}
              disabled={streaming}
              className={clsx(
                'w-11 h-11 md:w-9 md:h-9 active:scale-95 flex-shrink-0 flex items-center justify-center rounded-xl md:rounded-lg border transition-all disabled:opacity-40',
                pendingImage
                  ? 'border-accent bg-accent/20 text-accent'
                  : 'border-border bg-bg-4 hover:bg-bg-5 text-ink-2 hover:text-accent'
              )}
              title="Kirim gambar ke AI"
            >
              <ImagePlus size={16} className="md:w-[15px] md:h-[15px]" />
            </button>
          </div>
        </div>

        {/* Mikrofon */}
        <button
          onClick={isRecording ? stopRecording : startRecording}
          disabled={streaming || isTranscribing}
          className={clsx(
            'w-11 h-11 md:w-9 md:h-9 active:scale-95 flex-shrink-0 flex items-center justify-center rounded-xl md:rounded-lg border transition-all disabled:opacity-40',
            isRecording
              ? 'border-danger bg-danger/20 text-danger animate-pulse'
              : isTranscribing
                ? 'border-warn bg-warn/20 text-warn'
                : 'border-border bg-bg-4 hover:bg-bg-5 text-ink-2 hover:text-accent'
          )}
          title={isRecording ? 'Berhenti merekam' : isTranscribing ? 'Mentranskripsi...' : 'Rekam suara ke teks'}
        >
          {isRecording ? <MicOff size={16} className="md:w-[15px] md:h-[15px]" /> : isTranscribing ? <Loader2 size={16} className="animate-spin md:w-[15px] md:h-[15px]" /> : <Mic size={16} className="md:w-[15px] md:h-[15px]" />}
        </button>

        {/* Voice Mode */}
        <button
          onClick={() => {/* VoiceMode handled by parent */}}
          disabled={streaming}
          className="w-11 h-11 md:w-9 md:h-9 active:scale-95 flex-shrink-0 flex items-center justify-center rounded-xl md:rounded-lg border border-border bg-bg-4 hover:bg-bg-5 text-ink-2 hover:text-purple-400 transition-all disabled:opacity-40"
          title="Voice Mode — ngobrol dengan AI via suara"
          data-voice-mode-trigger="true"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <ellipse cx="12" cy="12" rx="10" ry="10"/>
            <path d="M12 7a3 3 0 0 0-3 3v4a3 3 0 0 0 6 0v-4a3 3 0 0 0-3-3z"/>
            <path d="M9 20h6"/><path d="M12 17v3"/>
          </svg>
        </button>

        {/* Textarea */}
        <div
          className="flex-1 relative"
          onDragOver={(e) => { e.preventDefault(); e.currentTarget.classList.add('ring-2', 'ring-accent', 'bg-accent/5') }}
          onDragLeave={(e) => { e.currentTarget.classList.remove('ring-2', 'ring-accent', 'bg-accent/5') }}
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
              const items = e.clipboardData?.items
              if (items) {
                const filesToAttach = []
                for (let i = 0; i < items.length; i++) {
                  if (items[i].kind === 'file') {
                    const file = items[i].getAsFile()
                    if (file) filesToAttach.push(file)
                  }
                }
                if (filesToAttach.length > 0) {
                  e.preventDefault()
                  addFiles(filesToAttach)
                }
              }
            }}
            onFocus={(e) => { e.currentTarget.parentElement?.classList.remove('ring-2', 'ring-accent', 'bg-accent/5') }}
            placeholder={
              streaming
                ? 'Ketik jawaban atau pesan baru... (Enter untuk kirim)'
                : 'Ketik pesan, perintah, atau analisa data...'
            }
            rows={1}
            className="w-full bg-bg-2 border-[0.5px] border-border rounded-2xl md:rounded-2xl px-4 md:px-4 py-3 md:py-3 text-[15px] md:text-[15px] text-ink placeholder-ink-3 outline-none focus:border-accent transition-colors resize-none shadow-sm"
          />
        </div>

        {/* Send / Stop button */}
        {streaming && !input.trim() ? (
          <button
            onClick={onStop}
            className="w-11 h-11 md:w-9 md:h-9 active:scale-95 flex-shrink-0 flex items-center justify-center rounded-xl md:rounded-lg bg-danger hover:bg-danger/80 text-white transition-all shadow-lg shadow-danger/20"
            title="Stop (Esc)"
          >
            <Square size={17} className="md:w-[16px] md:h-[16px]" fill="white" />
          </button>
        ) : streaming && input.trim() ? (
          <button
            onClick={onSend}
            className="w-11 h-11 md:w-9 md:h-9 active:scale-95 flex-shrink-0 flex items-center justify-center rounded-xl md:rounded-lg bg-accent hover:bg-accent/80 text-white transition-all shadow-lg shadow-accent/20 relative"
            title="Interrupt & Kirim jawaban"
          >
            <Send size={16} className="md:w-[15px] md:h-[15px] translate-x-[-1px] translate-y-[1px]" />
            <span className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-danger border border-bg-2" />
          </button>
        ) : (
          <button
            onClick={onSend}
            disabled={!input.trim() || !currentSession}
            className="w-11 h-11 md:w-9 md:h-9 active:scale-95 flex-shrink-0 flex items-center justify-center rounded-xl md:rounded-lg bg-accent hover:bg-accent/80 disabled:opacity-40 text-white transition-all"
            title="Kirim (Enter)"
          >
            <Send size={16} className="md:w-[15px] md:h-[15px] translate-x-[-1px] translate-y-[1px]" />
          </button>
        )}
      </div>
    </div>
  )
}
