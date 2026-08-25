/**
 * Chat.jsx — Slim orchestrator (state + wiring only)
 * All UI components extracted to /components/chat/
 *
 * Phase 3 refactor: 3598 → ~850 lines.
 * Components: ChatInput, Bubble, SessionItem, DragOverlay,
 *             ProcessStepsPanel, ArtifactsPanel
 */
import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { api } from '../hooks/useApi'
import { useAuthStore, useChatStore, useModelsStore, useOrchestratorStore } from '../store'
import ProjectLocationPopup from '../components/ProjectLocationPopup'
import FileManagerPopup from '../components/FileManagerPopup'
import { useIntentClassifier } from '../hooks/useIntentClassifier'
import toast from 'react-hot-toast'
import VoiceMode from '../components/VoiceMode'
import { useChatFileHandler } from '../hooks/useChatFileHandler'
import { extractFileContent } from '../utils/fileExtractor'
import AgentLoopVisualizer from '../components/AgentLoopVisualizer'
import { Plus, Loader2, Sparkles, Zap, FileText, CloudUpload } from 'lucide-react'
import clsx from 'clsx'

// ── Modular chat components ──────────────────────────────────
import ChatInput, { DragOverlay } from '../components/chat/ChatInput'
import { Bubble, SessionItem } from '../components/chat/MessageList'
import { ProcessStepsPanel, ArtifactsPanel } from '../components/chat/AgentProgress'

// ── Main Chat Page ────────────────────────────────────────────
export default function Chat() {
  const { classifyAndHandle, confirmAndProceed, closeFileManager, fileManagerState } = useIntentClassifier()
  const handleFileManagerConfirm = async (selectedPath) => { await confirmAndProceed(selectedPath, sendMessage) }

  const { t } = useTranslation()
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
    agentLoopEvents, agentLoopActive, agentLoopResult,
    setAgentLoopActive, addAgentLoopEvent, setAgentLoopResult, clearAgentLoop
  } = useChatStore()

  const input = useChatStore(s => s.draftInput)
  const setInput = useChatStore(s => s.setDraftInput)
  const [useRAG, setUseRAG] = useState(false)
  const [agentMode, setAgentMode] = useState(false)
  const [loadingMsgs, setLoadingMsgs] = useState(false)
  const [speakingId, setSpeakingId] = useState(null)
  const audioRef = useRef(null)

  // Derived: Filter sessions by selected channel
  const channelType = connectedChannels.find(c => c.id === selectedChannel)?.type || 'web'
  const filteredSessions = sessions.filter(s => {
    const sType = s.platform || 'web'
    if (channelType === 'web') return !sType || sType === 'web'
    return sType === channelType
  })

  // ── TTS ────────────────────────────────────────────────────
  const handleSpeak = useCallback((msg) => {
    if (speakingId === msg.id) {
      if (audioRef.current) { audioRef.current.pause(); audioRef.current = null }
      setSpeakingId(null); return
    }
    if (audioRef.current) audioRef.current.pause()
    setSpeakingId(msg.id)
    const url = api.getTTSUrl(msg.content)
    const audio = new Audio(url)
    audioRef.current = audio
    audio.play().catch(() => { toast.error("Gagal memutar suara"); setSpeakingId(null) })
    audio.onended = () => setSpeakingId(null)
  }, [speakingId])

  const [pendingConfirmation, setPendingConfirmation] = useState(null)
  const [implPlan, setImplPlan] = useState(null)
  const [artifact, setArtifact] = useState({ open: false, code: '', language: '', title: '' })

  // Auto-hide process panel
  const [showLastSteps, setShowLastSteps] = useState(false)
  const [fadingOut, setFadingOut] = useState(false)
  const hideStepsTimerRef = useRef(null)

  const openArtifact = useCallback((code, language) => { setArtifact({ open: true, code, language, title: '' }) }, [])
  const openArtifactCard = useCallback((code, language, title, isPreviewUrl = false) => { setArtifact({ open: true, code, language, title: title || '', isPreviewUrl }) }, [])
  const closeArtifact = useCallback(() => { setArtifact(a => ({ ...a, open: false })) }, [])

  // Project Location Popup
  const [projectLocationPopup, setProjectLocationPopup] = useState({ open: false, sessionId: null })
  const openProjectLocationPopup = useCallback((sessionId) => { setProjectLocationPopup({ open: true, sessionId }) }, [])
  const closeProjectLocationPopup = useCallback(() => { setProjectLocationPopup({ open: false, sessionId: null }) }, [])

  const [pendingResend, setPendingResend] = useState(null)
  const [pendingImage, setPendingImage] = useState(null)
  const [voiceModeOpen, setVoiceModeOpen] = useState(false)

  // Drag and drop
  const { attachedFiles, isDragOver, fileError, addFiles, removeFile, clearFiles, dragHandlers } = useChatFileHandler()

  // Refs
  const deletingIdsRef = useRef(new Set())
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  const scrollBottom = useCallback(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [])
  useEffect(() => { scrollBottom() }, [messages, streamingText])

  // ── SESSION BOOT LOGIC ─────────────────────────────────────
  const [sessionsLoaded, setSessionsLoaded] = useState(false)
  const initDoneRef = useRef(false)

  useEffect(() => {
    if (initDoneRef.current) return
    initDoneRef.current = true
    useChatStore.getState().clearMessages()
    useChatStore.getState().setCurrentSession(null)

    api.listSessions().then(async (serverSessions) => {
      const safe = serverSessions.filter(x => !deletingIdsRef.current.has(x.id))
      setSessions(safe)
      setSessionsLoaded(true)
      const currentUrlId = window.location.pathname.split('/chat/')[1]?.split('/')[0]
      if (currentUrlId) {
        const found = safe.find(x => x.id === currentUrlId) || { id: currentUrlId }
        useChatStore.getState().setCurrentSession(found)
        try {
          const msgs = await api.getMessages(currentUrlId)
          const latestUrlId = window.location.pathname.split('/chat/')[1]?.split('/')[0]
          if (latestUrlId === currentUrlId) {
            if (!found.title && msgs.length > 0) found.title = msgs[0].content.substring(0, 50)
            useChatStore.getState().setMessages(msgs || [])
          }
        } catch {
          useChatStore.getState().setCurrentSession(null)
          useChatStore.getState().clearMessages()
          navigate('/chat', { replace: true })
        }
      } else {
        if (safe.length > 0) navigate(`/chat/${safe[0].id}`, { replace: true })
        else { useChatStore.getState().setCurrentSession(null); useChatStore.getState().clearMessages() }
      }
    }).catch(() => { setSessionsLoaded(true) })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!sessionsLoaded) return
    api.listSessions().then(s => { setSessions(s.filter(x => !deletingIdsRef.current.has(x.id))) }).catch(() => {})
  }, [sessionsLoaded])

  useEffect(() => {
    if (!sessionsLoaded) return
    if (!urlSessionId) { if (currentSession?.id) { setCurrentSession(null); clearMessages() } return }
    if (currentSession?.id !== urlSessionId) {
      const found = sessions.find(s => s.id === urlSessionId)
      loadSession(found || { id: urlSessionId })
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [urlSessionId, sessionsLoaded])

  async function loadSession(session) {
    if (useChatStore.getState().streaming) {
      const abortFn = useChatStore.getState().abortRequest
      if (typeof abortFn === 'function') try { abortFn() } catch {}
      setStreaming(false); clearStreaming(); useChatStore.getState().setAbortRequest(null)
    }
    setCurrentSession(session); clearMessages(); setLoadingMsgs(true)
    try {
      const msgs = await api.getMessages(session.id)
      const latestUrlId = window.location.pathname.split('/chat/')[1]?.split('/')[0]
      if (latestUrlId === session.id) setMessages(msgs || [])
    } catch { toast.error('Gagal memuat pesan') }
    finally { setLoadingMsgs(false) }
  }

  // ── Real-time sync polling ─────────────────────────────────
  useEffect(() => {
    if (!currentSession?.id) return
    const POLL_INTERVAL = 5000
    const pollNewMessages = async () => {
      if (document.visibilityState === 'hidden') return
      if (useChatStore.getState().streaming) return
      const currentMsgs = useChatStore.getState().messages
      if (currentMsgs.length === 0) return
      const lastMsg = currentMsgs[currentMsgs.length - 1]
      const afterTs = lastMsg?.created_at || ''
      if (!afterTs) return
      try {
        const newMsgs = await api.getNewMessages(currentSession.id, afterTs)
        if (newMsgs && newMsgs.length > 0) {
          const existingIds = new Set(currentMsgs.map(m => m.id))
          const existingContents = new Set(currentMsgs.map(m => m.content))
          const uniqueNew = newMsgs.filter(m => !existingIds.has(m.id) && !existingContents.has(m.content))
          if (uniqueNew.length > 0) {
            useChatStore.getState().setMessages([...currentMsgs, ...uniqueNew])
            api.listSessions().then(s => { setSessions(s.filter(x => !deletingIdsRef.current.has(x.id))) }).catch(() => {})
          }
        }
      } catch {}
    }
    const onVisibilityChange = () => { if (document.visibilityState === 'visible') pollNewMessages() }
    document.addEventListener('visibilitychange', onVisibilityChange)
    const interval = setInterval(pollNewMessages, POLL_INTERVAL)
    return () => { clearInterval(interval); document.removeEventListener('visibilitychange', onVisibilityChange) }
  }, [currentSession?.id])

  const isCurrentSessionEmpty = currentSession && messages.length === 0

  async function newSession() {
    if (isCurrentSessionEmpty) { toast('Sesi ini masih kosong. Mulai chat dulu!', { icon: '💬', duration: 2000 }); return }
    try {
      const s = await api.createSession('New Chat')
      const updated = await api.listSessions()
      setSessions(updated); setCurrentSession(s); setMessages([]); navigate(`/chat/${s.id}`)
    } catch { toast.error('Gagal membuat sesi baru') }
  }

  useEffect(() => {
    if (!currentSession?.id) return
    if (currentSession.platform && currentSession.platform !== channelType) {
      if (filteredSessions.length > 0) navigate(`/chat/${filteredSessions[0].id}`)
    }
  }, [channelType])

  async function deleteSession(id) {
    deletingIdsRef.current.add(id)
    const prevSessions = useChatStore.getState().sessions
    const filtered = prevSessions.filter(s => s.id !== id)
    setSessions(filtered)
    const wasActive = currentSession?.id === id
    if (wasActive) { setCurrentSession(null); clearMessages(); navigate('/chat') }
    try {
      await api.deleteSession(id)
      const updated = await api.listSessions()
      setSessions(updated.filter(s => !deletingIdsRef.current.has(s.id)))
      toast.success('Chat dihapus', { duration: 1500 })
    } catch (err) {
      deletingIdsRef.current.delete(id)
      setSessions(prevSessions)
      if (wasActive) setCurrentSession(prevSessions.find(s => s.id === id) || null)
      const status = err?.status || err?.response?.status
      if (status === 404) { deletingIdsRef.current.add(id); setSessions(filtered); if (wasActive) { setCurrentSession(null); setMessages([]) }; return }
      toast.error('Gagal menghapus chat')
    } finally { setTimeout(() => deletingIdsRef.current.delete(id), 10000) }
  }

  // ── STOP streaming ─────────────────────────────────────────
  function stopStreaming() {
    const abortFn = useChatStore.getState().abortRequest
    if (abortFn && typeof abortFn === 'function') { abortFn(); useChatStore.getState().setAbortRequest(null) }
    const partial = useChatStore.getState().streamingText
    if (partial.trim()) {
      addMessage({ id: Date.now() + 1, role: 'assistant', content: partial + '\n\n*[Dihentikan oleh pengguna]*', model: selectedOrchestrator, created_at: new Date().toISOString() })
    }
    clearStreaming(); setStatusText(''); useChatStore.getState().finalizeProcessSteps()
    setShowLastSteps(true)
    if (hideStepsTimerRef.current) clearTimeout(hideStepsTimerRef.current)
    hideStepsTimerRef.current = setTimeout(() => { setFadingOut(true); setTimeout(() => { setShowLastSteps(false); setFadingOut(false) }, 400) }, 3600)
    toast('⏹ Respons dihentikan', { icon: '⏹', duration: 1500 })
  }

  // ── SEND message ───────────────────────────────────────────
  async function sendMessage(overrideText) {
    const text = typeof overrideText === 'string' ? overrideText : input.trim()
    let imageToSend = pendingImage
    if (!text && !imageToSend && attachedFiles.length === 0) return

    if (typeof overrideText !== 'string' && text) {
      if (agentMode) { const shouldProceed = await classifyAndHandle(text); if (!shouldProceed) return }
    }

    let activeSession = currentSession
    if (!activeSession) {
      try {
        activeSession = await api.createSession('New Chat')
        const updated = await api.listSessions()
        setSessions(updated); setCurrentSession(activeSession); setMessages([]); navigate(`/chat/${activeSession.id}`, { replace: true })
      } catch { toast.error('Gagal membuat sesi baru'); return }
    }

    // Interrupt streaming if user sends while AI is responding
    if (streaming) {
      const abortFn = useChatStore.getState().abortRequest
      if (abortFn && typeof abortFn === 'function') { abortFn(); useChatStore.getState().setAbortRequest(null) }
      const partial = useChatStore.getState().streamingText
      if (partial.trim()) addMessage({ id: Date.now() - 1, role: 'assistant', content: partial, model: useChatStore.getState().actualModel || selectedOrchestrator, created_at: new Date().toISOString() })
      clearStreaming(); useChatStore.getState().setStatusText(''); useChatStore.getState().finalizeProcessSteps()
      await new Promise(r => setTimeout(r, 80))
    }

    clearActiveRouting(); clearDrivePrompt()

    // Process attached files
    const currentFiles = [...attachedFiles]; clearFiles()
    let combinedText = text
    if (currentFiles.length > 0) {
      toast.loading("Mengekstrak file...", { id: "extract-file" })
      for (const file of currentFiles) {
        try {
          const extracted = await extractFileContent(file)
          if (extracted.type === 'image' && !imageToSend) imageToSend = { base64: extracted.base64, mime_type: extracted.mime_type, preview: extracted.dataUrl, filename: extracted.name }
          else if (extracted.type === 'text') combinedText += `\n\n[FILE: ${extracted.name}]\n${extracted.text}\n[/FILE]`
          else if (extracted.type === 'error') combinedText += `\n\n[ERROR MEMBACA FILE: ${extracted.name}]\n${extracted.text}`
        } catch(err) { combinedText += `\n\n[ERROR MEMBACA FILE: ${file.name}]\n${err.message}` }
      }
      toast.dismiss("extract-file")
    }

    const sessionId = activeSession.id
    setInput(''); setActualModel(null); useChatStore.getState().setActualModel(null)

    const tempUserMsg = {
      id: Date.now(), role: 'user', content: combinedText, original_content: text,
      attachedFiles: currentFiles, model: selectedOrchestrator, created_at: new Date().toISOString(),
      _image_preview: imageToSend?.preview || pendingImage?.preview || null,
    }
    addMessage(tempUserMsg); setPendingImage(null)
    executeChatStream(combinedText, imageToSend, sessionId)
  }

  // ── Stream execution core ──────────────────────────────────
  const executeChatStream = (combinedText, imageToSend, sessionId) => {
    setStreaming(true); useChatStore.getState().setStatusText(''); clearProcessSteps()

    const handleAddProcessStep = (data) => {
      if (data.type === 'loop_step') { useChatStore.getState().addAgentLoopEvent(data); useChatStore.getState().setAgentLoopActive(true); return }
      if (data.type === 'loop_done') { useChatStore.getState().setAgentLoopResult(data); useChatStore.getState().setAgentLoopActive(false); return }
      const currentOffset = useChatStore.getState().streamingText.length
      const steps = useChatStore.getState().processSteps
      if (data.action === 'thinking_delta' && data.delta) {
        const lastStep = steps[steps.length - 1]
        if (lastStep && lastStep.action === 'Thinking' && lastStep._isLiveThinking) {
          useChatStore.getState().updateLastProcessStep({ liveContent: (lastStep.liveContent || '') + data.delta })
        } else {
          useChatStore.getState().addProcessStep({ action: 'Thinking', detail: 'Reasoning...', ts: Date.now(), _textOffset: currentOffset, liveContent: data.delta, _isLiveThinking: true })
        }
        return
      }
      if (data.action === 'thinking_done') {
        const lastStep = steps[steps.length - 1]
        if (lastStep && lastStep.action === 'Thinking' && lastStep._isLiveThinking) {
          useChatStore.getState().updateLastProcessStep({ detail: data.detail || 'Reasoning complete', result: data.result || lastStep.liveContent || '', _isLiveThinking: false })
        } else {
          useChatStore.getState().addProcessStep({ action: 'Thinking', detail: data.detail || 'Reasoning', ts: data.ts || Date.now(), _textOffset: currentOffset, liveContent: data.result || null, result: data.result || null })
        }
        return
      }
      if (steps.length > 0) {
        const lastStep = steps[steps.length - 1]
        if (lastStep._textOffset != null && lastStep.liveContent == null) {
          const endContent = useChatStore.getState().streamingText.substring(lastStep._textOffset)
          useChatStore.getState().setProcessSteps(steps.map((s, i) => i === steps.length - 1 ? { ...s, liveContent: endContent } : s))
        }
      }
      const { action, detail, count, ts, type, ...rest } = data
      const previewContent = rest.code || rest.result || null
      useChatStore.getState().addProcessStep({ action: action || 'Worked', detail: detail || '', count: count ?? null, ts: ts || Date.now(), _textOffset: currentOffset, liveContent: previewContent, ...rest })
      if (action === 'Written' && rest.code && detail) {
        const lang = (rest.language || detail.split('.').pop() || 'txt').toLowerCase()
        const filename = detail.split('/').pop() || detail
        openArtifactCard(rest.code + (rest.truncated ? '\n\n// [konten dipotong]' : ''), lang, `✍️ ${filename}`, false)
      }
    }

    const handleChunk = (chunk) => { appendStreamingText(chunk) }

    const autoOpenAppPreview = (fullText) => {
      const m = /%%APP_PREVIEW%%\s*(https?:\/\/[^\s]+)\s*%%END_PREVIEW%%/i.exec(fullText)
      if (m) { const url = m[1].trim(); setTimeout(() => { openArtifactCard(url, 'preview', '🚀 App Preview — Jalankan Aplikasi', true); toast.success('🚀 Aplikasi berhasil dibuat!', { duration: 5000 }) }, 400) }
    }

    const onDone = async (done) => {
      const fullText = useChatStore.getState().streamingText
      clearStreaming(); setImplPlan(null); useChatStore.getState().setStatusText('')
      if (done.drive_prompt) setDrivePromptContent(done.drive_prompt.content, done.drive_prompt.title)
      if (done.model_used) setActiveModel(done.model_used)
      if (done.capability_used) setActiveCapability(done.capability_used)
      addMessage({ id: Date.now() + 1, role: 'assistant', content: fullText, model: useChatStore.getState().actualModel || selectedOrchestrator, rag_sources: done.sources?.length ? JSON.stringify(done.sources) : null, thinking_process: done.thinking_process || null, created_at: new Date().toISOString() })
      setTimeout(() => { api.listSessions().then(s => { const safe = s.filter(x => !deletingIdsRef.current.has(x.id)); const cur = useChatStore.getState().sessions; setSessions((cur.length > 0 && safe.length === 0) ? cur : safe) }).catch(() => {}) }, 800)
      useChatStore.getState().finalizeProcessSteps()
      setShowLastSteps(true)
      if (hideStepsTimerRef.current) clearTimeout(hideStepsTimerRef.current)
      hideStepsTimerRef.current = setTimeout(() => { setFadingOut(true); setTimeout(() => { setShowLastSteps(false); setFadingOut(false) }, 400) }, 3600)
      useChatStore.getState().setActualModel(null); useChatStore.getState().setAbortRequest(null)
      autoOpenAppPreview(fullText)
    }

    const onSession = (sessionData) => {
      if (sessionData?.model) useChatStore.getState().setActualModel(sessionData.model)
      if (sessionData?.session_id && (!currentSession || !currentSession.id)) setCurrentSession({ id: sessionData.session_id })
    }

    const onRequireProject = () => {
      clearStreaming(); useChatStore.getState().setStatusText('')
      setPendingResend({ text: combinedText, image: imageToSend })
      openProjectLocationPopup(sessionId)
    }

    if (imageToSend) {
      const abortFn = api.chatStreamMultimodal(
        { session_id: sessionId, message: combinedText, model: selectedOrchestrator, use_rag: useRAG, channel: channelType, agent_mode: agentMode },
        imageToSend, handleChunk, onDone, onSession,
        (status) => useChatStore.getState().setStatusText(status),
        (procData) => handleAddProcessStep(procData), onRequireProject
      )
      useChatStore.getState().setAbortRequest(abortFn)
    } else {
      const abortFn = api.chatStream(
        { session_id: sessionId, message: combinedText, model: selectedOrchestrator, use_rag: useRAG, channel: channelType, agent_mode: agentMode },
        handleChunk, onDone, onSession,
        (pendingData) => { clearStreaming(); useChatStore.getState().setStatusText(''); setPendingConfirmation(pendingData) },
        (status) => useChatStore.getState().setStatusText(status),
        (procData) => handleAddProcessStep(procData),
        (_planData) => {},
        onRequireProject,
        (planData) => { setImplPlan({ text: planData.content, intent: planData.intent, complexity: planData.complexity, ts: Date.now() }) }
      )
      useChatStore.getState().setAbortRequest(abortFn)
    }
  }

  // ── Export ──────────────────────────────────────────────────
  const handleExportChat = async (format, msgId) => {
    if (!currentSession?.id) return toast.error('Sesi aktif tidak ditemukan')
    const loadId = toast.loading(`Mengekspor sesi ke ${format.toUpperCase()}...`)
    try {
      const blob = await api.exportChat(currentSession.id, format, msgId)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a'); a.style.display = 'none'; a.href = url
      a.download = `Export_Chat_${new Date().getTime()}.${format}`
      document.body.appendChild(a); a.click(); window.URL.revokeObjectURL(url); document.body.removeChild(a)
      toast.success('Berhasil mendownload!', { id: loadId })
    } catch (e) { toast.error(e.message, { id: loadId }) }
  }

  // ── Quick actions for welcome ──────────────────────────────
  const quickActions = [
    { icon: Sparkles, label: 'Chat Biasa', desc: 'Tanya jawab dengan AI', color: 'from-accent to-accent-2' },
    { icon: Zap, label: 'Perintah', desc: 'Jalankan otomasi/perintah', color: 'from-amber-500 to-orange-500' },
    { icon: FileText, label: 'Analisa Dokumen', desc: 'Upload & analisa file', color: 'from-emerald-500 to-teal-500' },
  ]

  // ═══════════════════════════════════════════════════════════
  // ── RENDER ─────────────────────────────────────────────────
  // ═══════════════════════════════════════════════════════════
  return (
    <div className="flex w-full h-full relative">

      {/* Chat area */}
      <div
        className={clsx('flex flex-col min-w-0 transition-all duration-300 relative bg-bg', artifact.open ? 'w-1/2 flex-1' : 'w-full flex-1')}
        {...dragHandlers}
      >
        <DragOverlay isVisible={isDragOver} />

        {/* Topbar */}
        <div className="h-12 border-b-[0.5px] border-border flex items-center px-6 gap-3 flex-shrink-0 bg-bg">
          <span className="text-sm font-medium text-ink truncate flex-1">
            {currentSession?.title || t('select_or_create_session')}
          </span>
          <button
            onClick={() => setUseRAG(!useRAG)}
            className={clsx('px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all duration-300 border flex items-center gap-1.5', useRAG ? 'bg-success/15 border-success/50 text-success shadow-[0_0_12px_rgba(74,222,128,0.3)]' : 'bg-bg-4 border-border text-ink-3 hover:bg-bg-5')}
            title="Toggle RAG (Knowledge Base)"
          >
            📚 RAG
            {useRAG && <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse"/>}
          </button>
          <button
            onClick={() => setAgentMode(!agentMode)}
            className={clsx('px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all duration-300 border flex items-center gap-1.5', agentMode ? 'bg-accent/15 border-accent/50 text-accent shadow-[0_0_12px_rgba(168,85,247,0.3)]' : 'bg-bg-4 border-border text-ink-3 hover:bg-bg-5 hover:text-ink-2')}
            title={agentMode ? 'Agent Mode AKTIF' : 'Agent Mode NONAKTIF'}
          >
            🤖 Agent
            <span className={clsx('text-[10px] font-bold px-1 py-0.5 rounded', agentMode ? 'bg-accent/20 text-accent' : 'bg-bg-5 text-ink-4')}>{agentMode ? 'ON' : 'OFF'}</span>
            {agentMode && <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse"/>}
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-6 md:px-10 md:py-8 space-y-6">
          {/* Welcome screen */}
          {!currentSession && (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="relative mb-6">
                <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-accent to-accent-2 flex items-center justify-center shadow-2xl shadow-accent/30"><span className="text-4xl">🧠</span></div>
                <div className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-success border border-bg flex items-center justify-center"><span className="w-2 h-2 rounded-full bg-white animate-pulse2" /></div>
              </div>
              <h2 className="text-xl font-semibold text-ink mb-2">{t('chat_greeting')} <span className="bg-gradient-to-r from-accent to-accent-2 bg-clip-text text-transparent">{appName}</span></h2>
              <p className="text-sm text-ink-3 mb-8 max-w-md leading-relaxed">{t('chat_desc')}</p>
              <div className="flex gap-3 mb-8">
                {quickActions.map(({ icon: Icon, label, desc, color }) => (
                  <button key={label} onClick={newSession} className="flex flex-col items-center gap-2.5 px-5 py-4 bg-bg-2 border border-border rounded-xl hover:border-accent/40 hover:bg-bg-3 transition-all group w-40">
                    <div className={clsx('w-10 h-10 rounded-xl bg-gradient-to-br flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform', color)}><Icon size={18} className="text-white" /></div>
                    <div><div className="text-sm font-semibold text-ink group-hover:text-accent-2 transition-colors">{label}</div><div className="text-[11px] text-ink-3 mt-0.5">{desc}</div></div>
                  </button>
                ))}
              </div>
              <button onClick={newSession} className="flex items-center gap-2 px-5 py-2.5 bg-accent hover:bg-accent/80 text-white rounded-xl text-sm font-medium transition-all shadow-lg shadow-accent/25"><Plus size={15} /> Mulai Chat Baru</button>
              {models.length === 0 && (
                <div className="mt-6 p-3 bg-warn/10 border border-warn/20 rounded-xl text-xs text-warn max-w-sm">
                  ⚠️ Belum ada model aktif. Buka <span className="font-mono">Integrasi</span> untuk menambahkan API key atau install Ollama.
                </div>
              )}
            </div>
          )}

          {loadingMsgs && (<div className="flex items-center gap-2 text-ink-3 text-sm"><Loader2 size={14} className="animate-spin" /> Memuat pesan...</div>)}

          {messages.map((msg) => (
            <Bubble
              key={msg.id} msg={msg} isStreaming={false}
              onExport={handleExportChat} onSpeak={handleSpeak} speakingId={speakingId}
              onOpenArtifact={openArtifact} onOpenArtifactCard={openArtifactCard}
              ProcessStepsPanel={ProcessStepsPanel}
            />
          ))}

          {/* Live Process Steps */}
          {streaming && processSteps.length > 0 && (
            <div><ProcessStepsPanel steps={processSteps} isStreaming={streaming} onStop={stopStreaming} streamingText={streamingText} onOpenArtifactCard={openArtifactCard} /></div>
          )}

          {/* Post-done Process Steps (auto-hide) */}
          {!streaming && showLastSteps && lastProcessSteps && lastProcessSteps.length > 0 &&
            lastProcessSteps.some(s => s.action && s.action !== 'Thinking' && s.action !== 'Thought') && (
            <div className={clsx("relative", fadingOut && "process-panel-fadeout")}>
              <ProcessStepsPanel steps={lastProcessSteps} isStreaming={false} onStop={null} streamingText="" onOpenArtifactCard={openArtifactCard} />
              <div className="flex items-center justify-end px-10 pb-1 gap-2 animate-fade">
                <span className="text-[10px] text-ink-3 opacity-50">Otomatis hilang dalam beberapa detik</span>
                <button onClick={() => setShowLastSteps(false)} className="text-[10px] text-ink-3 hover:text-danger transition-colors underline">Tutup</button>
              </div>
            </div>
          )}

          {/* Agent Loop */}
          {(agentLoopActive || agentLoopEvents.length > 0) && (
            <div className="mb-4 w-full max-w-3xl pr-4"><AgentLoopVisualizer events={agentLoopEvents} isActive={agentLoopActive} isDone={agentLoopResult !== null} result={agentLoopResult} /></div>
          )}

          {/* Streaming Bubble */}
          {streaming && streamingText && (
            <Bubble msg={{ role: 'assistant', content: streamingText, model: actualModel || selectedOrchestrator, created_at: new Date().toISOString() }} isStreaming={true} onStop={stopStreaming} onSpeak={handleSpeak} speakingId={speakingId} onOpenArtifact={openArtifact} onOpenArtifactCard={openArtifactCard} ProcessStepsPanel={ProcessStepsPanel} />
          )}

          {/* Implementation Plan Card */}
          {implPlan && streaming && (
            <div className="flex justify-start mb-4 w-full max-w-3xl pr-4 animate-fade-in-up">
              <div className="flex gap-3 w-full">
                <div className="w-7 h-7 mt-0.5 flex-shrink-0 rounded-lg bg-gradient-to-br from-violet-500/30 to-indigo-500/30 border border-violet-500/40 flex items-center justify-center shadow-lg shadow-violet-500/10"><span className="text-sm">📋</span></div>
                <div className="flex-1 min-w-0 rounded-2xl rounded-tl-sm border border-violet-500/25 bg-gradient-to-br from-bg-2 to-bg-3 shadow-lg overflow-hidden">
                  <div className="flex items-center gap-2 px-4 py-2.5 border-b border-violet-500/20 bg-violet-500/5">
                    <span className="text-[11px] font-semibold text-violet-300 tracking-wide uppercase">Rencana Implementasi</span>
                    <span className="ml-auto flex items-center gap-1.5"><span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse" /><span className="text-[10px] text-violet-400/70">Eksekusi berjalan otomatis</span></span>
                  </div>
                  <div className="px-4 py-3">
                    <div className="text-[12.5px] text-ink-2 leading-relaxed whitespace-pre-wrap font-mono plan-content">
                      {implPlan.text.split('\n').map((line, i) => {
                        if (line.startsWith('## ')) return <div key={i} className="text-[13px] font-bold text-ink mb-1.5 mt-0.5 font-sans">{line.replace('## ', '')}</div>
                        if (line.startsWith('**') && line.endsWith('**')) return <div key={i} className="text-[11px] font-semibold text-ink-2 mb-0.5 font-sans">{line.replace(/\*\*/g, '')}</div>
                        if (/^\d+\./.test(line)) { const num = line.match(/^(\d+)\.\s*/)[1]; const rest = line.replace(/^\d+\.\s*/, ''); return (<div key={i} className="flex gap-2 mb-0.5 items-baseline"><span className="text-[10px] font-bold text-violet-400 tabular-nums w-4 flex-shrink-0">{num}.</span><span className="text-[12px] text-ink-2">{rest}</span></div>) }
                        if (line.startsWith('- ')) { const content = line.replace(/^- /, ''); return (<div key={i} className="flex gap-1.5 mb-0.5 items-baseline"><span className="text-violet-400/60 text-[10px] flex-shrink-0">▸</span><span className="text-[12px] text-ink-3">{content.includes('`') ? content.split('`').map((part, pi) => pi % 2 === 1 ? <code key={pi} className="text-emerald-400 bg-bg-4 px-1 rounded text-[11px]">{part}</code> : <span key={pi}>{part}</span>) : content}</span></div>) }
                        if (line.startsWith('**')) return <div key={i} className="text-[11px] font-semibold text-accent-2 mb-0.5 font-sans mt-1">{line.replace(/\*\*/g, '')}</div>
                        if (!line.trim()) return <div key={i} className="h-1.5" />
                        return <div key={i} className="text-[12px] text-ink-3 mb-0.5">{line}</div>
                      })}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 px-4 py-2 border-t border-border/50 bg-bg-4/50">
                    <div className="flex gap-1">{[0,1,2,3,4].map(i => <div key={i} className="w-1 h-1 rounded-full bg-violet-400/40 animate-pulse" style={{animationDelay: i * 0.15 + 's'}} />)}</div>
                    <span className="text-[10px] text-ink-3">Mengeksekusi rencana di atas...</span>
                    <button onClick={() => setImplPlan(null)} className="ml-auto text-[10px] text-ink-3/50 hover:text-ink-3 transition-colors">sembunyikan</button>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Drive Upload Prompt */}
          {drivePromptContent && !streaming && !pendingConfirmation && (
            <div className="flex justify-start mb-6 w-full max-w-3xl pr-4 animate-fade-in-up">
              <div className="flex gap-4">
                <div className="w-8 h-8 flex-shrink-0 bg-blue-500/20 border border-blue-500/50 rounded-lg flex items-center justify-center"><CloudUpload size={16} className="text-blue-500" /></div>
                <div className="flex-1 min-w-0 bg-bg-2 border border-border rounded-2xl rounded-tl-sm px-4 py-3 shadow-md">
                  <div className="flex items-center justify-between mb-2"><span className="text-sm font-semibold text-ink">Google Drive Upload Ready</span></div>
                  <div className="text-xs text-ink-2 mb-3"><p>Pilih metadata berikut untuk di-upload:</p></div>
                  <div className="bg-bg-3 p-2.5 rounded border border-border font-mono text-[11px] text-ink mb-4 overflow-x-auto whitespace-pre-wrap max-h-32">
                    {drivePromptTitle && <div className="font-semibold border-b border-border pb-1 mb-1">{drivePromptTitle}</div>}
                    {drivePromptContent}
                  </div>
                  <div className="flex gap-3">
                    <button onClick={() => { addMessage({ id: Date.now() + 1, role: 'user', content: `Teruskan metadata ini dan lakukan upload ke gdrive: ${drivePromptTitle || ''}\n\n${drivePromptContent}`, model: selectedOrchestrator, created_at: new Date().toISOString() }); setInput('Tolong upload metadata tadi'); clearDrivePrompt() }} className="flex-1 bg-blue-600 hover:bg-blue-500 text-white font-medium py-2 rounded-lg text-xs shadow-md transition-all">Ya, upload sekarang!</button>
                    <button onClick={() => clearDrivePrompt()} className="flex-1 bg-bg-4 hover:bg-bg-5 text-ink-2 hover:text-ink font-medium py-2 border border-border rounded-lg text-xs transition-all">Batal</button>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} className="h-4" />
        </div>

        {/* Input area */}
        {currentSession && (
          <ChatInput
            input={input}
            setInput={setInput}
            streaming={streaming}
            streamingText={streamingText}
            currentSession={currentSession}
            onSend={sendMessage}
            onStop={stopStreaming}
            attachedFiles={attachedFiles}
            removeFile={removeFile}
            addFiles={addFiles}
            fileError={fileError}
            pendingImage={pendingImage}
            setPendingImage={setPendingImage}
            selectedOrchestrator={selectedOrchestrator}
          />
        )}
      </div>

      {/* Artifacts Panel */}
      {artifact.open && (
        <ArtifactsPanel code={artifact.code} language={artifact.language} title={artifact.title} isPreviewUrl={artifact.isPreviewUrl} onClose={closeArtifact} />
      )}

      {/* Project Location Popup */}
      {projectLocationPopup.open && (
        <ProjectLocationPopup
          isOpen={projectLocationPopup.open}
          sessionId={projectLocationPopup.sessionId}
          onClose={() => { closeProjectLocationPopup(); setPendingResend(null) }}
          onLocationSet={(projectPath) => {
            toast.success(`📁 Lokasi proyek disimpan: ${projectPath}`)
            if (pendingResend) { executeChatStream(pendingResend.text, pendingResend.image, projectLocationPopup.sessionId); setPendingResend(null) }
          }}
        />
      )}

      {/* File Manager Popup */}
      <FileManagerPopup isOpen={fileManagerState.isOpen} mode={fileManagerState.mode} intent={fileManagerState.intent} pendingMessage={fileManagerState.pendingMessage} onConfirm={handleFileManagerConfirm} onClose={closeFileManager} />

      {/* Voice Mode */}
      <VoiceMode isOpen={voiceModeOpen} onClose={() => setVoiceModeOpen(false)} sessionId={currentSession?.id} selectedModel={selectedOrchestrator} />
    </div>
  )
}
