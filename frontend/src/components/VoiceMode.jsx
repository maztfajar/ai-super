/**
 * VoiceMode — Gemini-style voice conversation overlay
 * Flow: listening → (VAD silence) → processing → speaking → listening (loop)
 */
import React, { useState, useEffect, useRef, useCallback } from 'react'
import { api } from '../hooks/useApi'

// ── State constants ──────────────────────────────────────────
const S = { IDLE: 'idle', LISTENING: 'listening', PROCESSING: 'processing', SPEAKING: 'speaking', ERROR: 'error' }

// ── Silence detection config ─────────────────────────────────
const SILENCE_THRESHOLD = 12      // 0–255 frequency amplitude
const SILENCE_HOLD_MS   = 1600   // stop after 1.6s of silence
const MIN_RECORD_MS     = 800    // don't stop before 0.8s

// ── Helper: split long AI text into sentence chunks for TTS ──
function splitSentences(text, maxLen = 300) {
  // Strip markdown before TTS
  const clean = text
    .replace(/```[\s\S]*?```/g, '')
    .replace(/`[^`]+`/g, '')
    .replace(/[*_~>#]/g, '')
    .replace(/\n+/g, ' ')
    .trim()
  if (clean.length <= maxLen) return [clean]
  const parts = []
  let buf = ''
  for (const sentence of clean.split(/(?<=[.?!:])\s+/)) {
    if ((buf + sentence).length > maxLen && buf) {
      parts.push(buf.trim())
      buf = ''
    }
    buf += sentence + ' '
  }
  if (buf.trim()) parts.push(buf.trim())
  return parts.length ? parts : [clean.substring(0, maxLen)]
}

// ── CSS injected once ────────────────────────────────────────
const STYLES = `
  @keyframes vm-pulse   { 0%,100%{transform:scale(1);opacity:.9} 50%{transform:scale(1.12);opacity:1} }
  @keyframes vm-wave    { 0%{transform:scale(1);opacity:.6} 100%{transform:scale(2.2);opacity:0} }
  @keyframes vm-spin    { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }
  @keyframes vm-fade-in { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:translateY(0)} }
  @keyframes vm-bar     { 0%,100%{transform:scaleY(.3)} 50%{transform:scaleY(1)} }

  .vm-overlay {
    position:fixed;inset:0;z-index:9999;
    background:rgba(0,0,0,.85);
    backdrop-filter:blur(20px);
    display:flex;align-items:center;justify-content:center;
    animation:vm-fade-in .25s ease;
  }
  .vm-card {
    width:min(420px,92vw);
    background:linear-gradient(145deg,rgba(20,20,30,.98),rgba(10,10,20,.98));
    border:1px solid rgba(255,255,255,.1);
    border-radius:32px;
    padding:40px 32px 32px;
    display:flex;flex-direction:column;align-items:center;gap:28px;
    box-shadow:0 40px 80px rgba(0,0,0,.6), inset 0 1px 0 rgba(255,255,255,.06);
    position:relative;
  }

  /* Orb */
  .vm-orb-wrap { position:relative;width:140px;height:140px;display:flex;align-items:center;justify-content:center; }
  .vm-ring {
    position:absolute;border-radius:50%;border:2px solid;
    animation:vm-wave 2.5s ease-out infinite;
  }
  .vm-orb {
    width:90px;height:90px;border-radius:50%;
    display:flex;align-items:center;justify-content:center;
    position:relative;z-index:2;
    transition:all .4s ease;
    cursor:pointer;
  }
  .vm-orb.idle    { background:linear-gradient(135deg,#1a1a2e,#16213e);border:2px solid rgba(100,100,200,.3); animation:vm-pulse 3s ease-in-out infinite; }
  .vm-orb.listening { background:linear-gradient(135deg,#0d4f3c,#0a3d2e);border:2px solid rgba(52,211,153,.5);box-shadow:0 0 30px rgba(52,211,153,.3); animation:vm-pulse 1.2s ease-in-out infinite; }
  .vm-orb.processing { background:linear-gradient(135deg,#1e1b4b,#312e81);border:2px solid rgba(139,92,246,.5);box-shadow:0 0 30px rgba(139,92,246,.3); animation:vm-spin 2s linear infinite; }
  .vm-orb.speaking { background:linear-gradient(135deg,#1e3a5f,#1a3a5f);border:2px solid rgba(96,165,250,.5);box-shadow:0 0 40px rgba(96,165,250,.4); animation:vm-pulse .9s ease-in-out infinite; }
  .vm-orb.error   { background:linear-gradient(135deg,#4a1212,#3b0f0f);border:2px solid rgba(248,113,113,.5); }

  /* Equalizer bars (speaking state) */
  .vm-bars { display:flex;align-items:center;gap:3px;height:28px; }
  .vm-bar { width:4px;border-radius:2px;background:rgba(96,165,250,.9); }
  .vm-bar:nth-child(1){animation:vm-bar .7s ease-in-out infinite .0s}
  .vm-bar:nth-child(2){animation:vm-bar .7s ease-in-out infinite .1s}
  .vm-bar:nth-child(3){animation:vm-bar .7s ease-in-out infinite .05s}
  .vm-bar:nth-child(4){animation:vm-bar .7s ease-in-out infinite .15s}
  .vm-bar:nth-child(5){animation:vm-bar .7s ease-in-out infinite .08s}

  /* Transcript boxes */
  .vm-transcript { width:100%;min-height:36px;text-align:center;animation:vm-fade-in .3s ease; }
  .vm-user-text  { font-size:15px;color:rgba(255,255,255,.75);font-weight:500;line-height:1.5; }
  .vm-ai-text    { font-size:14px;color:rgba(200,220,255,.65);font-weight:400;line-height:1.6;margin-top:6px;max-height:90px;overflow:hidden; }

  /* Lang selector */
  .vm-lang { display:flex;gap:8px; }
  .vm-lang-btn {
    padding:5px 14px;border-radius:20px;border:1.5px solid rgba(255,255,255,.15);
    background:transparent;color:rgba(255,255,255,.5);font-size:12px;font-weight:700;
    cursor:pointer;transition:all .2s;letter-spacing:.5px;text-transform:uppercase;
  }
  .vm-lang-btn.active { border-color:rgba(139,92,246,.7);background:rgba(139,92,246,.15);color:#c4b5fd; }

  /* Status label */
  .vm-status {
    font-size:13px;font-weight:600;letter-spacing:.5px;text-transform:uppercase;
    color:rgba(255,255,255,.45);text-align:center;min-height:20px;
  }
  .vm-status.listening { color:rgba(52,211,153,.8); }
  .vm-status.processing { color:rgba(139,92,246,.8); }
  .vm-status.speaking { color:rgba(96,165,250,.8); }
  .vm-status.error { color:rgba(248,113,113,.8); }

  /* Close button */
  .vm-close {
    width:48px;height:48px;border-radius:50%;border:1.5px solid rgba(255,255,255,.15);
    background:rgba(255,255,255,.06);color:rgba(255,255,255,.5);
    display:flex;align-items:center;justify-content:center;cursor:pointer;
    font-size:20px;transition:all .2s;
  }
  .vm-close:hover { background:rgba(248,113,113,.2);border-color:rgba(248,113,113,.5);color:#f87171; }
`

let stylesInjected = false

export default function VoiceMode({ isOpen, onClose, sessionId, selectedModel }) {
  const [voiceState, setVoiceState]     = useState(S.IDLE)
  const [userText, setUserText]         = useState('')
  const [aiText, setAiText]             = useState('')
  const [lang, setLang]                 = useState('id')
  const [statusMsg, setStatusMsg]       = useState('Tekan orb untuk mulai')
  const [level, setLevel]               = useState(0)

  // Refs (for use inside callbacks without stale closure issues)
  const stateRef        = useRef(S.IDLE)
  const activeRef       = useRef(false)      // is voice mode loop running?
  const streamRef       = useRef(null)       // MediaStream
  const recorderRef     = useRef(null)       // MediaRecorder
  const chunksRef       = useRef([])
  const audioCtxRef     = useRef(null)
  const analyserRef     = useRef(null)
  const silenceTimerRef = useRef(null)
  const recStartRef     = useRef(0)
  const rafRef          = useRef(null)
  const currentAudioRef = useRef(null)       // currently playing Audio element
  const loopRef         = useRef(null)       // pending setTimeout for loop
  const langRef         = useRef('id')

  // Keep langRef in sync
  useEffect(() => { langRef.current = lang }, [lang])

  // Inject styles once
  useEffect(() => {
    if (stylesInjected) return
    const el = document.createElement('style')
    el.textContent = STYLES
    document.head.appendChild(el)
    stylesInjected = true
  }, [])

  // ── Set state (both React state + ref) ──────────────────────
  const setState = useCallback((s, msg) => {
    stateRef.current = s
    setVoiceState(s)
    const labels = {
      [S.IDLE]:       'Tekan orb untuk mulai',
      [S.LISTENING]:  'Mendengarkan...',
      [S.PROCESSING]: 'Memproses...',
      [S.SPEAKING]:   'AI sedang berbicara...',
      [S.ERROR]:      'Terjadi kesalahan',
    }
    setStatusMsg(msg || labels[s] || s)
  }, [])

  // ── Cleanup everything ───────────────────────────────────────
  const cleanup = useCallback(() => {
    activeRef.current = false
    clearTimeout(loopRef.current)
    clearTimeout(silenceTimerRef.current)
    cancelAnimationFrame(rafRef.current)

    if (currentAudioRef.current) {
      currentAudioRef.current.pause()
      currentAudioRef.current = null
    }
    if (recorderRef.current && recorderRef.current.state !== 'inactive') {
      try { recorderRef.current.stop() } catch {}
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop())
      streamRef.current = null
    }
    if (audioCtxRef.current && audioCtxRef.current.state !== 'closed') {
      audioCtxRef.current.close().catch(() => {})
      audioCtxRef.current = null
    }
    recorderRef.current = null
    chunksRef.current   = []
  }, [])

  // ── Visual audio level meter ─────────────────────────────────
  const startLevelMeter = useCallback(() => {
    const analyser = analyserRef.current
    if (!analyser) return
    const data = new Uint8Array(analyser.frequencyBinCount)
    const tick = () => {
      if (!activeRef.current) return
      analyser.getByteFrequencyData(data)
      const avg = data.reduce((a, b) => a + b, 0) / data.length
      setLevel(Math.min(1, avg / 60))
      rafRef.current = requestAnimationFrame(tick)
    }
    tick()
  }, [])

  // ── SPEAK: TTS → play audio ──────────────────────────────────
  const speak = useCallback(async (text) => {
    if (!text?.trim() || !activeRef.current) return

    setState(S.SPEAKING)
    const chunks = splitSentences(text)

    for (const chunk of chunks) {
      if (!activeRef.current) break
      if (!chunk.trim()) continue

      try {
        const params = new URLSearchParams({ text: chunk, lang: langRef.current })
        const token = (() => {
          try { return JSON.parse(localStorage.getItem('ai-orchestrator-auth') || '{}')?.state?.token } catch { return null }
        })()
        if (token) params.append('token', token)

        const res = await fetch(`/api/media/tts?${params}`)
        if (!res.ok) throw new Error(`TTS ${res.status}`)

        const blob = await res.blob()
        const url  = URL.createObjectURL(blob)

        await new Promise((resolve) => {
          if (!activeRef.current) { resolve(); return }
          const audio = new Audio(url)
          currentAudioRef.current = audio
          audio.onended = () => { URL.revokeObjectURL(url); resolve() }
          audio.onerror = () => { URL.revokeObjectURL(url); resolve() }
          audio.play().catch(() => resolve())
        })
        currentAudioRef.current = null
      } catch (err) {
        console.warn('[VoiceMode] TTS chunk failed:', err)
      }
    }
  }, [setState])

  // ── TRANSCRIBE audio blob ────────────────────────────────────
  const transcribe = useCallback(async (blob) => {
    setState(S.PROCESSING, 'Mentranskripsi suara...')
    try {
      const result = await api.transcribeAudio(blob, 'voice.webm')
      return result?.text?.trim() || ''
    } catch (err) {
      console.error('[VoiceMode] Transcribe failed:', err)
      return ''
    }
  }, [setState])

  // ── SEND text to AI, collect full response ───────────────────
  const sendToAI = useCallback((text, sid) => {
    return new Promise((resolve) => {
      let fullText = ''
      setState(S.PROCESSING, 'AI sedang berpikir...')

      api.chatStream(
        {
          session_id: sid,
          message:    text,
          model:      selectedModel || undefined,
          use_rag:    false,
          channel:    'web',
          agent_mode: false,
          voice_mode: true,
        },
        (chunk) => {
          fullText += chunk
          setAiText(fullText.slice(-200))
        },
        () => resolve(fullText),
        null, null,
        (status) => setStatusMsg(status),
        null, null, null, null
      )
    })
  }, [setState, selectedModel])

  // ── One conversation turn ────────────────────────────────────
  const doTurn = useCallback(async (sid) => {
    if (!activeRef.current) return

    // 1. Start recording
    setState(S.LISTENING)
    setUserText('')
    setAiText('')
    chunksRef.current = []

    let micStream
    try {
      micStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false })
    } catch {
      setState(S.ERROR, 'Akses mikrofon ditolak')
      activeRef.current = false
      return
    }

    streamRef.current = micStream

    // AudioContext for VAD
    const ctx      = new AudioContext()
    audioCtxRef.current = ctx
    const source   = ctx.createMediaStreamSource(micStream)
    const analyser = ctx.createAnalyser()
    analyser.fftSize = 512
    analyserRef.current = analyser
    source.connect(analyser)
    startLevelMeter()

    const data = new Uint8Array(analyser.frequencyBinCount)
    let silenceMs = 0
    recStartRef.current = Date.now()

    // MediaRecorder
    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : 'audio/webm'

    const recorder = new MediaRecorder(micStream, { mimeType })
    recorderRef.current = recorder
    recorder.ondataavailable = e => { if (e.data.size > 0) chunksRef.current.push(e.data) }
    recorder.start(100)

    // VAD polling
    await new Promise(resolve => {
      const vadInterval = setInterval(() => {
        if (!activeRef.current || stateRef.current !== S.LISTENING) {
          clearInterval(vadInterval)
          resolve()
          return
        }
        analyser.getByteFrequencyData(data)
        const avg = data.reduce((a, b) => a + b, 0) / data.length
        const elapsed = Date.now() - recStartRef.current

        if (elapsed > MIN_RECORD_MS) {
          if (avg < SILENCE_THRESHOLD) {
            silenceMs += 100
            if (silenceMs >= SILENCE_HOLD_MS) {
              clearInterval(vadInterval)
              resolve()
            }
          } else {
            silenceMs = 0
          }
        }
      }, 100)
    })

    // Stop recording
    if (recorder.state !== 'inactive') {
      recorder.stop()
      await new Promise(r => { recorder.onstop = r })
    }
    micStream.getTracks().forEach(t => t.stop())
    streamRef.current = null
    ctx.close().catch(() => {})
    audioCtxRef.current = null
    cancelAnimationFrame(rafRef.current)
    setLevel(0)

    if (!activeRef.current) return

    const audioBlob = new Blob(chunksRef.current, { type: mimeType })
    chunksRef.current = []

    // 2. Transcribe
    const userSaid = await transcribe(audioBlob)
    if (!activeRef.current) return

    if (!userSaid) {
      setState(S.LISTENING, 'Tidak terdeteksi, coba lagi...')
      loopRef.current = setTimeout(() => doTurn(sid), 800)
      return
    }

    setUserText(userSaid)

    // 3. AI responds
    const aiResponse = await sendToAI(userSaid, sid)
    if (!activeRef.current) return

    if (!aiResponse?.trim()) {
      loopRef.current = setTimeout(() => doTurn(sid), 400)
      return
    }

    // 4. Speak
    await speak(aiResponse)
    if (!activeRef.current) return

    // 5. Loop
    loopRef.current = setTimeout(() => doTurn(sid), 400)
  }, [setState, transcribe, sendToAI, speak, startLevelMeter])

  // ── Start / Stop voice mode ──────────────────────────────────
  const startVoice = useCallback(async () => {
    if (activeRef.current) return
    activeRef.current = true

    let sid = sessionId
    if (!sid) {
      try {
        const s = await api.createSession('Voice Chat')
        sid = s.id
      } catch {
        setState(S.ERROR, 'Gagal membuat sesi')
        activeRef.current = false
        return
      }
    }
    doTurn(sid)
  }, [sessionId, doTurn, setState])

  const stopVoice = useCallback(() => {
    cleanup()
    setState(S.IDLE, 'Tekan orb untuk mulai')
    setUserText('')
    setAiText('')
    setLevel(0)
  }, [cleanup, setState])

  const handleClose = useCallback(() => {
    cleanup()
    onClose()
  }, [cleanup, onClose])

  // Cleanup on unmount
  useEffect(() => () => cleanup(), [cleanup])

  // Stop when closed externally
  useEffect(() => {
    if (!isOpen) { cleanup(); setState(S.IDLE) }
  }, [isOpen, cleanup, setState])

  if (!isOpen) return null

  const isActive = voiceState !== S.IDLE && voiceState !== S.ERROR
  const ringColor = {
    [S.LISTENING]:  'rgba(52,211,153,',
    [S.PROCESSING]: 'rgba(139,92,246,',
    [S.SPEAKING]:   'rgba(96,165,250,',
  }[voiceState] || 'rgba(120,120,200,'

  const OrbIcon = voiceState === S.SPEAKING ? (
    <div className="vm-bars">
      {[1,2,3,4,5].map(i => <div key={i} className="vm-bar" style={{ height: `${12 + Math.random() * 16}px` }} />)}
    </div>
  ) : voiceState === S.PROCESSING ? (
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="rgba(139,92,246,.9)" strokeWidth="2.5" strokeLinecap="round">
      <path d="M12 2a10 10 0 0 1 10 10"/><circle cx="12" cy="12" r="4"/>
    </svg>
  ) : voiceState === S.LISTENING ? (
    <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="rgba(52,211,153,.9)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
      <path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v4M8 23h8"/>
    </svg>
  ) : (
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="rgba(160,160,220,.7)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
      <path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v4M8 23h8"/>
    </svg>
  )

  return (
    <div className="vm-overlay" onClick={(e) => e.target === e.currentTarget && handleClose()}>
      <style>{STYLES}</style>
      <div className="vm-card">

        {/* Close button top-right */}
        <button className="vm-close" style={{ position:'absolute',top:16,right:16,width:36,height:36,fontSize:16 }} onClick={handleClose} title="Tutup">✕</button>

        {/* Title */}
        <div style={{ textAlign:'center' }}>
          <div style={{ fontSize:13,fontWeight:700,letterSpacing:2,textTransform:'uppercase',color:'rgba(255,255,255,.3)' }}>
            Voice Mode
          </div>
        </div>

        {/* Orb + rings */}
        <div className="vm-orb-wrap">
          {/* Animated rings (only when active) */}
          {isActive && [0,1,2].map(i => (
            <div key={i} className="vm-ring" style={{
              width: 90 + i * 28,
              height: 90 + i * 28,
              borderColor: `${ringColor}${0.25 - i * 0.07})`,
              animationDelay: `${i * 0.7}s`,
              animationDuration: `${2.2 + i * 0.4}s`,
            }} />
          ))}

          {/* Level indicator ring */}
          {voiceState === S.LISTENING && level > 0.05 && (
            <div style={{
              position:'absolute',
              width: 90 + level * 50,
              height: 90 + level * 50,
              borderRadius:'50%',
              border:'1.5px solid rgba(52,211,153,.4)',
              transition:'all .08s ease',
            }} />
          )}

          {/* Main orb */}
          <div
            className={`vm-orb ${voiceState}`}
            onClick={isActive ? stopVoice : startVoice}
            title={isActive ? 'Hentikan' : 'Mulai berbicara'}
          >
            {OrbIcon}
          </div>
        </div>

        {/* Status text */}
        <div className={`vm-status ${voiceState}`}>{statusMsg}</div>

        {/* Transcript area */}
        <div className="vm-transcript">
          {userText && <div className="vm-user-text">"{userText}"</div>}
          {aiText && <div className="vm-ai-text">{aiText}</div>}
          {!userText && !aiText && voiceState === S.IDLE && (
            <div style={{ fontSize:13, color:'rgba(255,255,255,.25)', textAlign:'center', lineHeight:1.6 }}>
              Klik orb di atas untuk memulai percakapan suara.<br/>
              Bicara setelah ikon menjadi hijau.
            </div>
          )}
        </div>

        {/* Language selector */}
        <div className="vm-lang">
          {[['id','🇮🇩 ID'],['en','🇬🇧 EN']].map(([code, label]) => (
            <button
              key={code}
              className={`vm-lang-btn ${lang === code ? 'active' : ''}`}
              onClick={() => setLang(code)}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Bottom controls */}
        <div style={{ display:'flex',gap:16,alignItems:'center' }}>
          {isActive ? (
            <button
              onClick={stopVoice}
              style={{
                padding:'10px 28px',borderRadius:24,border:'1.5px solid rgba(248,113,113,.5)',
                background:'rgba(248,113,113,.15)',color:'#f87171',
                fontSize:13,fontWeight:700,cursor:'pointer',letterSpacing:.5,transition:'all .2s'
              }}
            >
              ⏹ Hentikan
            </button>
          ) : (
            <button
              onClick={startVoice}
              style={{
                padding:'10px 28px',borderRadius:24,border:'1.5px solid rgba(139,92,246,.5)',
                background:'rgba(139,92,246,.2)',color:'#c4b5fd',
                fontSize:13,fontWeight:700,cursor:'pointer',letterSpacing:.5,transition:'all .2s'
              }}
            >
              🎙 Mulai Berbicara
            </button>
          )}
        </div>

      </div>
    </div>
  )
}
