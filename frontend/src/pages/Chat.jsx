import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import { api } from '../hooks/useApi'
import { copyToClipboard } from "../utils/clipboard"
import { useAuthStore, useChatStore, useModelsStore, useOrchestratorStore } from '../store'
import ChannelSelector from '../components/ChannelSelector'
import toast from 'react-hot-toast'
import {
  Plus, Trash2, Send, Paperclip, Copy, Check, Download,
  Bot, User, Loader2, Square, Sparkles, Zap, FileText, CloudUpload, Menu, X,
  ImagePlus, Mic, MicOff, Camera, Volume2, Brain, ChevronDown, ChevronUp
} from 'lucide-react'
import clsx from 'clsx'



// ── Message bubble ────────────────────────────────────────────
function Bubble({ msg, isStreaming, onStop, onExport, onSpeak, speakingId }) {
  const [copied, setCopied] = useState(false)
  const [showThinking, setShowThinking] = useState(false)
  const isUser = msg.role === 'user'

  const copy = () => {
    copyToClipboard(msg.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
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
            <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
          ) : (
            <div className="prose prose-sm max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>{msg.content}</ReactMarkdown>
              {isStreaming && (
                <span className="inline-block w-1.5 h-4 bg-accent-2 animate-pulse2 ml-0.5 align-middle" />
              )}
            </div>
          )}
        </div>

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

              {/* Thinking Toggle - show if thinking_process exists */}
              {!isUser && msg.thinking_process && (
                <button
                  onClick={() => setShowThinking(!showThinking)}
                  className={clsx(
                    "opacity-0 group-hover:opacity-100 p-0.5 rounded transition-all outline-none",
                    showThinking ? "bg-accent/20 text-accent opacity-100" : "hover:bg-bg-5 text-ink-3 hover:text-ink"
                  )}
                  title="Tampilkan Thinking"
                >
                  {showThinking ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
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

        {/* Thinking Process - Expandable Section */}
        {!isUser && msg.thinking_process && showThinking && (
          <div className="mt-2 p-2.5 bg-bg-3 border border-border rounded-lg text-[11px] text-ink-3 leading-relaxed space-y-1">
            <div className="font-semibold text-accent-2 mb-1.5 flex items-center gap-1">
              <Brain size={11} /> Proses Thinking:
            </div>
            <div className="max-h-48 overflow-y-auto space-y-1">
              {msg.thinking_process.split('\n').map((step, i) => step.trim() && (
                <div key={i} className="flex gap-2">
                  <span className="text-ink-3 flex-shrink-0">•</span>
                  <span className="flex-1">{step.trim()}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
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
  const { 
    activeModel, activeCapability, setActiveModel, setActiveCapability, clearActiveRouting,
    drivePromptContent, drivePromptTitle, setDrivePromptContent, clearDrivePrompt 
  } = useOrchestratorStore()

  const {
    sessions, setSessions,
    currentSession, setCurrentSession,
    messages, setMessages, addMessage,
    streaming, setStreaming,
    streamingText, appendStreamingText, clearStreaming,
  } = useChatStore()

  const [input, setInput] = useState('')
  const [useRAG, setUseRAG] = useState(false)
  const [loadingMsgs, setLoadingMsgs] = useState(false)
  const [actualModel, setActualModel] = useState(null)
  const [speakingId, setSpeakingId] = useState(null)
  const audioRef = useRef(null)

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
  const [statusText, setStatusText] = useState('')

  const [sidebarOpen, setSidebarOpen] = useState(false)
  // Multimodal state
  const [pendingImage, setPendingImage] = useState(null)  // { base64, mime_type, preview }
  const [isRecording, setIsRecording] = useState(false)
  const [isTranscribing, setIsTranscribing] = useState(false)
  // Deletion guard: set of session IDs sedang dalam proses hapus
  // Mencegah polling 5 detik mengembalikan sesi yang baru dihapus
  const deletingIdsRef = useRef(new Set())
  const mediaRecorderRef = useRef(null)
  const imagePickerRef = useRef(null)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)
  const abortRef = useRef(null)
  const fileInputRef = useRef(null)
  const scrollBottom = useCallback(() => {

    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => { scrollBottom() }, [messages, streamingText])

  // Load models + sessions
  useEffect(() => {
    api.listSessions().then(setSessions).catch(() => { })
    api.listModels().then(() => {
      // Re-fetch sessions after models loaded (titles may have been updated)
      api.listSessions().then((s) => {
        // Filter out any sessions currently being deleted
        const safe = s.filter(x => !deletingIdsRef.current.has(x.id))
        setSessions(safe)
      }).catch(() => { })
    }).catch(() => { })
  }, [])

  // Load session from URL
  useEffect(() => {
    if (urlSessionId) {
      const s = sessions.find((x) => x.id === urlSessionId)
      if (s && s.id !== currentSession?.id) loadSession(s)
    }
  }, [urlSessionId, sessions])

  async function loadSession(session) {
    setCurrentSession(session)
    setLoadingMsgs(true)
    try {
      const msgs = await api.getMessages(session.id)
      setMessages(msgs)
    } catch { toast.error('Gagal memuat pesan') }
    finally { setLoadingMsgs(false) }
  }

  // ── Real-time sync: poll for new messages every 5s ───────
  // Enables cross-channel sync (Telegram/WhatsApp → Web)
  useEffect(() => {
    if (!currentSession?.id) return
    const POLL_INTERVAL = 5000

    const pollNewMessages = async () => {
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
          const uniqueNew = newMsgs.filter(m => !existingIds.has(m.id))
          if (uniqueNew.length > 0) {
            const merged = [...currentMsgs, ...uniqueNew]
            useChatStore.getState().setMessages(merged)
            // Refresh session list — but filter out sessions being deleted
            api.listSessions().then((s) => {
              const safe = s.filter(x => !deletingIdsRef.current.has(x.id))
              setSessions(safe)
            }).catch(() => {})
          }
        }
      } catch {
        // Silent fail — polling is best-effort
      }
    }

    const interval = setInterval(pollNewMessages, POLL_INTERVAL)
    return () => clearInterval(interval)
  }, [currentSession?.id])

  async function newSession() {
    try {
      const s = await api.createSession('New Chat')
      const updated = await api.listSessions()
      setSessions(updated)
      setCurrentSession(s)
      setMessages([])
      navigate(`/chat/${s.id}`)
    } catch { toast.error('Gagal membuat sesi baru') }
  }

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
      setMessages([])
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
    if (abortRef.current && typeof abortRef.current === 'function') {
      abortRef.current()
      abortRef.current = null
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
    toast('⏹ Respons dihentikan', { icon: '⏹', duration: 1500 })
  }

  // ── SEND message ─────────────────────────────────────────
  async function sendMessage() {
    const text = input.trim()
    const imageToSend = pendingImage
    if (!text && !imageToSend) return
    if (streaming) return
    if (!currentSession) { await newSession(); return }

    clearActiveRouting()
    clearDrivePrompt()

    setInput('')
    setActualModel(null)
    // Reset textarea height
    if (inputRef.current) inputRef.current.style.height = 'auto'

    const tempUserMsg = {
      id: Date.now(),
      role: 'user',
      content: text,
      model: selectedOrchestrator,
      created_at: new Date().toISOString(),
      _image_preview: pendingImage?.preview || null,
    }
    addMessage(tempUserMsg)

    setPendingImage(null)  // clear preview
    setStreaming(true)
    setStatusText('')

    const sessionId = currentSession.id

    // Use different endpoints based on whether image is present
    if (imageToSend) {
      // Use multimodal endpoint for image + text
      abortRef.current = api.chatStreamMultimodal(
        {
          session_id: sessionId,
          message: text,
          model: selectedOrchestrator,
          use_rag: useRAG,
        },
        imageToSend,  // Pass image data (base64 + mime_type)
        (chunk) => appendStreamingText(chunk),
        async (done) => {
          const fullText = useChatStore.getState().streamingText
          clearStreaming()
          setStatusText('')

          if (done.drive_prompt) {
            setDrivePromptContent(done.drive_prompt.content, done.drive_prompt.title)
          }
          if (done.model_used) setActiveModel(done.model_used)
          if (done.capability_used) setActiveCapability(done.capability_used)


        addMessage({
          id: Date.now() + 1,
          role: 'assistant',
          content: fullText,
          model: abortRef.current?.actualModel || selectedOrchestrator,
          rag_sources: done.sources?.length ? JSON.stringify(done.sources) : null,
          thinking_process: done.thinking_process || null,
          created_at: new Date().toISOString(),
        })
        // Refresh session list — tapi hati-hati jangan restore sesi yang dihapus
        api.listSessions().then((s) => {
          const safe = s.filter(x => !deletingIdsRef.current.has(x.id))
          setSessions(safe)
        }).catch(() => {})
      },
      (sessionData) => {
        if (sessionData && sessionData.model) {
          setActualModel(sessionData.model)
          if (abortRef.current) abortRef.current.actualModel = sessionData.model
        }
      },
      (pendingData) => {
        clearStreaming()
        setStatusText('')
        setPendingConfirmation(pendingData)
      },
      (status) => {} // Ignore intermediate status for natural chat
      )
    } else {
      // Use regular endpoint for text-only
      abortRef.current = api.chatStream(
        {
          session_id: sessionId,
          message: text,
          model: selectedOrchestrator,
          use_rag: useRAG,
        },
        (chunk) => appendStreamingText(chunk),
        async (done) => {
          const fullText = useChatStore.getState().streamingText
          clearStreaming()
          setStatusText('')

          if (done.drive_prompt) {
            setDrivePromptContent(done.drive_prompt.content, done.drive_prompt.title)
          }
          if (done.model_used) setActiveModel(done.model_used)
          if (done.capability_used) setActiveCapability(done.capability_used)


          addMessage({
            id: Date.now() + 1,
            role: 'assistant',
            content: fullText,
            model: abortRef.current?.actualModel || selectedOrchestrator,
            rag_sources: done.sources?.length ? JSON.stringify(done.sources) : null,
            thinking_process: done.thinking_process || null,
            created_at: new Date().toISOString(),
          })
          // Refresh session list — tapi hati-hati jangan restore sesi yang dihapus
          api.listSessions().then((s) => {
            const safe = s.filter(x => !deletingIdsRef.current.has(x.id))
            setSessions(safe)
          }).catch(() => {})
        },
        (sessionData) => {
          if (sessionData && sessionData.model) {
            setActualModel(sessionData.model)
            if (abortRef.current) abortRef.current.actualModel = sessionData.model
          }
        },
        (pendingData) => {
          clearStreaming()
          setStatusText('')
          setPendingConfirmation(pendingData)
        },
        (status) => {} // Ignore intermediate status for natural chat
      )
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

    abortRef.current = api.executePending(
      {
        session_id: pendingData.session_id,
        command: pendingData.command,
        model: selectedOrchestrator,
      },
      (chunk) => appendStreamingText(chunk),
      async (done) => {
        const fullText = useChatStore.getState().streamingText
        clearStreaming()
        addMessage({
          id: Date.now() + 1,
          role: 'assistant',
          content: fullText,
          model: abortRef.current?.actualModel || selectedOrchestrator,
          created_at: new Date().toISOString(),
        })
      }
    )
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
            className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg bg-accent hover:bg-accent/80 text-white text-xs font-medium transition-colors"
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
          {sessions.length === 0 && (
            <p className="text-xs text-ink-3 text-center py-6">
              Belum ada sesi.<br />Buat chat pertama!
            </p>
          )}
          {sessions.map((s) => (
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
      <div className="flex-1 flex flex-col min-w-0">

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
            />
          ))}

          {/* Streaming bubble dengan tombol stop */}
          {streaming && streamingText && (
            <Bubble
              msg={{ role: 'assistant', content: streamingText, model: actualModel || selectedOrchestrator, created_at: new Date().toISOString() }}
              isStreaming={true}
              onStop={stopStreaming}
              onSpeak={handleSpeak}
              speakingId={speakingId}
            />
          )}

          {/* Pending Confirmation UI (HIDDEN for vision tasks) */}
          {false && pendingConfirmation && (
            <div className="flex justify-start mb-6 w-full max-w-3xl pr-4 animate-fade-in-up">
              <div className="flex gap-4">
                <div className="w-8 h-8 flex-shrink-0 bg-warn/20 border border-warn/50 rounded-lg flex items-center justify-center">
                  <span className="text-warn text-lg">⚠️</span>
                </div>
                <div className="flex-1 min-w-0 bg-bg-2 border border-warn/30 rounded-2xl rounded-tl-sm px-4 py-3 shadow-lg shadow-black/20">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-bold text-warn">VPS Execution Request</span>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-warn/20 text-warn tracking-widest">{pendingConfirmation.risk} RISK</span>
                  </div>
                  <div className="text-xs text-ink-2 mb-3">
                    <p className="font-semibold text-ink mb-1">Tujuan Perintah:</p>
                    <p>{pendingConfirmation.purpose}</p>
                  </div>
                  <div className="bg-bg-3 p-2.5 rounded border border-border-2 font-mono text-[11px] text-ink mb-4 overflow-x-auto whitespace-pre-wrap">
                    {pendingConfirmation.command}
                  </div>
                  <div className="flex gap-3">
                    <button
                      onClick={() => approveExecution(pendingConfirmation)}
                      className="flex-1 bg-success hover:bg-success/80 text-white font-medium py-2 rounded-lg text-xs shadow-md transition-all"
                    >
                      ✓ Setujui Eksekusi
                    </button>
                    <button
                      onClick={() => setPendingConfirmation(null)}
                      className="flex-1 bg-bg-4 hover:bg-bg-5 text-ink-2 hover:text-ink font-medium py-2 border border-border rounded-lg text-xs transition-all"
                    >
                      ✗ Batalkan
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Thinking indicator - simple & clean */}
          {streaming && !streamingText && (
            <div className="flex gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-accent to-accent-2 flex items-center justify-center flex-shrink-0">
                <Bot size={13} className="text-white" />
              </div>
              <div className="flex flex-col gap-1.5">
                <div className="px-3.5 py-3 bg-bg-4 border border-border rounded-xl rounded-tl-sm flex items-center gap-2">
                  <div className="flex gap-1">
                    {[0, 1, 2].map(i => (
                      <span
                        key={i}
                        className="w-1.5 h-1.5 rounded-full bg-accent-2 animate-pulse2"
                        style={{ animationDelay: `${i * 0.2}s` }}
                      />
                    ))}
                  </div>
                  <span className="text-xs text-ink-3">Thinking...</span>
                </div>
                {/* Stop button */}
                <button
                  onClick={stopStreaming}
                  className="self-start flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-danger/10 hover:bg-danger/20 border border-danger/25 text-danger text-xs font-medium transition-all"
                >
                  <Square size={11} fill="currentColor" /> Hentikan
                </button>
              </div>
            </div>
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

            <div className="flex gap-2 items-end">
              {/* Upload dokumen (paperclip) */}
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                onChange={handleFileUpload}
                accept=".pdf,.docx,.txt,.csv,.md"
              />
              {/* Image picker hidden input */}
              <input
                ref={imagePickerRef}
                type="file"
                className="hidden"
                onChange={handleImagePick}
                accept="image/*"
              />

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
                  onFocus={(e) => {
                    e.currentTarget.parentElement?.classList.remove('ring-2', 'ring-accent', 'bg-accent/5')
                  }}
                  placeholder={
                    streaming
                      ? 'AI sedang merespons... (Esc untuk stop)'
                      : 'Ketik pesan, perintah, atau minta analisa data... (atau drag & drop gambar)'
                  }
                  disabled={streaming}
                  rows={1}
                  className="w-full bg-bg-4 border border-border-2 rounded-xl px-3.5 py-2.5 text-sm text-ink placeholder-ink-3 outline-none focus:border-accent transition-colors resize-none disabled:opacity-60 disabled:cursor-not-allowed"
                />
              </div>

              {/* STOP button — saat streaming */}
              {streaming ? (
                <button
                  onClick={stopStreaming}
                  className="w-9 h-9 flex-shrink-0 flex items-center justify-center rounded-lg bg-danger hover:bg-danger/80 text-white transition-all shadow-lg shadow-danger/20"
                  title="Stop (Esc)"
                >
                  <Square size={16} fill="white" />
                </button>
              ) : (
                /* SEND button — saat tidak streaming */
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


    </div>
  )
}
