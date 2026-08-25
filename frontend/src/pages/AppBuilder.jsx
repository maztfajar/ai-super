/**
 * AppBuilder — Halaman perencanaan & pembangunan aplikasi
 * Flow: Describe → Plan → Design → Build → Deploy
 */
import React, { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Layers, Code2, Smartphone, Server, Terminal, Globe,
  ArrowRight, ArrowLeft, CheckCircle2, Loader2, Copy,
  FolderTree, Rocket, Palette, FileCode, Cpu, ChevronRight,
  Sparkles, Send, Plus, Minus
} from 'lucide-react'
import { api } from '../hooks/useApi'
import toast from 'react-hot-toast'

const APP_TYPES = [
  { id: 'web',     label: 'Web App',    icon: Globe,    desc: 'React / Vue / Angular + API',   color: '#4f6ef7' },
  { id: 'mobile',  label: 'Mobile App', icon: Smartphone, desc: 'Flutter / React Native',      color: '#f59e0b' },
  { id: 'api',     label: 'REST API',   icon: Server,   desc: 'FastAPI / Express / Django',     color: '#34d399' },
  { id: 'cli',     label: 'CLI Tool',   icon: Terminal, desc: 'Python / Go / Node CLI',        color: '#818cf8' },
  { id: 'desktop', label: 'Desktop',    icon: Cpu,      desc: 'Electron / Tauri / PyQt',        color: '#f472b6' },
]

const STEPS = [
  { id: 'describe', label: 'Deskripsi',   icon: Sparkles },
  { id: 'plan',     label: 'Rencana',     icon: FolderTree },
  { id: 'design',   label: 'Desain',      icon: Palette },
  { id: 'build',    label: 'Build',       icon: Code2 },
  { id: 'deploy',   label: 'Deploy',      icon: Rocket },
]

// ── Komponen Step Indicator ────────────────────────────────────────────────
function StepBar({ currentStep }) {
  const idx = STEPS.findIndex(s => s.id === currentStep)
  return (
    <div className="flex items-center gap-1 justify-center py-4">
      {STEPS.map((step, i) => {
        const Icon = step.icon
        const done    = i < idx
        const active  = i === idx
        return (
          <React.Fragment key={step.id}>
            <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-300 ${
              active ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30' :
              done   ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                       'bg-white/5 text-white/30 border border-white/5'
            }`}>
              {done ? <CheckCircle2 size={12} /> : <Icon size={12} />}
              <span className="hidden sm:inline">{step.label}</span>
            </div>
            {i < STEPS.length - 1 && (
              <div className={`w-4 h-px ${i < idx ? 'bg-emerald-500/40' : 'bg-white/10'}`} />
            )}
          </React.Fragment>
        )
      })}
    </div>
  )
}

// ── Step 1: Describe ────────────────────────────────────────────────────────
function StepDescribe({ onNext }) {
  const [description, setDescription] = useState('')
  const [appType, setAppType] = useState('web')
  const textRef = useRef(null)

  const examples = [
    'Aplikasi todo list dengan auth login, kategori task, dan notifikasi deadline',
    'Dashboard analytics penjualan dengan chart real-time dan export Excel',
    'API manajemen inventory toko dengan barcode scanner dan laporan stok',
    'Chatbot customer service dengan knowledge base dari dokumen PDF',
  ]

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold text-white">Deskripsikan Aplikasi Anda</h2>
        <p className="text-white/50 text-sm">Ceritakan apa yang ingin Anda buat. Semakin detail, semakin baik rencana yang dihasilkan.</p>
      </div>

      {/* App Type Selector */}
      <div className="grid grid-cols-5 gap-2">
        {APP_TYPES.map(type => {
          const Icon = type.icon
          return (
            <button
              key={type.id}
              onClick={() => setAppType(type.id)}
              className={`flex flex-col items-center gap-1.5 p-3 rounded-xl border text-center transition-all duration-200 ${
                appType === type.id
                  ? 'border-opacity-50 bg-opacity-10'
                  : 'border-white/5 bg-white/3 hover:bg-white/5'
              }`}
              style={appType === type.id ? {
                borderColor: type.color + '60',
                backgroundColor: type.color + '15',
              } : {}}
            >
              <Icon size={18} style={{ color: appType === type.id ? type.color : '#ffffff44' }} />
              <span className="text-[10px] font-medium" style={{ color: appType === type.id ? type.color : '#ffffff60' }}>
                {type.label}
              </span>
            </button>
          )
        })}
      </div>

      {/* Description Textarea */}
      <div className="relative">
        <textarea
          ref={textRef}
          value={description}
          onChange={e => setDescription(e.target.value)}
          placeholder="Contoh: Buat aplikasi manajemen keuangan pribadi dengan fitur pencatatan pemasukan/pengeluaran, kategorisasi, laporan bulanan, dan target tabungan..."
          className="w-full h-36 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white/80 placeholder-white/20 focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/20 resize-none transition-all"
        />
        <div className="absolute bottom-3 right-3 text-[10px] text-white/20">
          {description.length} karakter
        </div>
      </div>

      {/* Examples */}
      <div>
        <p className="text-xs text-white/30 mb-2">💡 Contoh deskripsi:</p>
        <div className="space-y-1.5">
          {examples.map((ex, i) => (
            <button
              key={i}
              onClick={() => setDescription(ex)}
              className="w-full text-left text-xs text-white/40 hover:text-white/70 bg-white/3 hover:bg-white/8 px-3 py-2 rounded-lg transition-all border border-transparent hover:border-white/10"
            >
              <ChevronRight size={10} className="inline mr-1 opacity-50" />
              {ex}
            </button>
          ))}
        </div>
      </div>

      <button
        onClick={() => onNext({ description, appType })}
        disabled={description.trim().length < 20}
        className="w-full py-3 rounded-xl font-semibold text-sm transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed"
        style={{ background: 'linear-gradient(135deg, #4f6ef7 0%, #7b93ff 100%)', color: 'white' }}
      >
        Generate Rencana <ArrowRight size={16} />
      </button>
    </div>
  )
}

// ── Step 2: Plan ────────────────────────────────────────────────────────────
function StepPlan({ planData, onNext, onBack }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(planData, null, 2))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (!planData) return (
    <div className="flex items-center justify-center h-40 gap-3 text-white/40">
      <Loader2 size={20} className="animate-spin" />
      <span className="text-sm">Membuat rencana aplikasi...</span>
    </div>
  )

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-white">Rencana Aplikasi</h2>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 text-xs text-white/40 hover:text-white/70 bg-white/5 px-3 py-1.5 rounded-lg transition-all"
        >
          {copied ? <CheckCircle2 size={12} className="text-emerald-400" /> : <Copy size={12} />}
          {copied ? 'Disalin' : 'Salin JSON'}
        </button>
      </div>

      {/* Tech Stack */}
      <div className="bg-white/3 border border-white/8 rounded-xl p-4 space-y-2">
        <h3 className="text-xs font-semibold text-white/50 uppercase tracking-widest">Tech Stack</h3>
        <div className="grid grid-cols-2 gap-2">
          {Object.entries(planData.tech_stack || {}).map(([k, v]) => (
            <div key={k} className="bg-white/5 rounded-lg px-3 py-2">
              <div className="text-[10px] text-white/30 uppercase tracking-wider">{k}</div>
              <div className="text-xs text-indigo-300 font-medium mt-0.5">{v}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Folder Structure */}
      <div className="bg-white/3 border border-white/8 rounded-xl p-4 space-y-2">
        <h3 className="text-xs font-semibold text-white/50 uppercase tracking-widest flex items-center gap-1.5">
          <FolderTree size={12} /> Struktur Folder
        </h3>
        <div className="font-mono text-xs space-y-0.5">
          {(planData.folder_structure || []).map((f, i) => (
            <div key={i} className="text-white/40 hover:text-white/70 transition-colors">
              <span className="text-white/15">{'  '.repeat(f.split('/').length - 1)}</span>
              <span className="text-indigo-300/70">📁</span>
              {' '}{f.split('/').pop()}
            </div>
          ))}
        </div>
      </div>

      {/* Development Phases */}
      <div className="bg-white/3 border border-white/8 rounded-xl p-4 space-y-3">
        <h3 className="text-xs font-semibold text-white/50 uppercase tracking-widest">Development Phases</h3>
        {(planData.development_phases || []).map(phase => (
          <div key={phase.phase} className="flex gap-3">
            <div className="w-6 h-6 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">
              {phase.phase}
            </div>
            <div>
              <div className="text-xs font-semibold text-white/70">{phase.name}</div>
              <ul className="mt-1 space-y-0.5">
                {(phase.tasks || []).map((task, i) => (
                  <li key={i} className="text-[11px] text-white/40 flex items-start gap-1.5">
                    <ChevronRight size={10} className="mt-0.5 shrink-0 text-white/20" />
                    {task}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ))}
      </div>

      <div className="flex gap-3">
        <button onClick={onBack} className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm text-white/50 bg-white/5 hover:bg-white/10 transition-all">
          <ArrowLeft size={14} /> Kembali
        </button>
        <button
          onClick={() => onNext(planData)}
          className="flex-1 py-2.5 rounded-xl font-semibold text-sm flex items-center justify-center gap-2 transition-all"
          style={{ background: 'linear-gradient(135deg, #4f6ef7 0%, #7b93ff 100%)', color: 'white' }}
        >
          Lanjut ke Desain <ArrowRight size={14} />
        </button>
      </div>
    </div>
  )
}

// ── Step 3: Design ──────────────────────────────────────────────────────────
function StepDesign({ onNext, onBack }) {
  const [palette, setPalette] = useState('dark-blue')
  const [font, setFont] = useState('inter')
  const [style, setStyle] = useState('modern')

  const PALETTES = [
    { id: 'dark-blue',  label: 'Dark Navy',    colors: ['#0f172a', '#1e293b', '#4f6ef7', '#e2e8f0'] },
    { id: 'dark-green', label: 'Dark Forest',  colors: ['#0a1e0f', '#14532d', '#22c55e', '#f0fdf4'] },
    { id: 'dark-purple',label: 'Dark Violet',  colors: ['#1e1b4b', '#312e81', '#818cf8', '#e0e7ff'] },
    { id: 'light',      label: 'Clean Light',  colors: ['#f8fafc', '#ffffff', '#3b82f6', '#1e293b'] },
    { id: 'neon',       label: 'Neon Cyber',   colors: ['#000000', '#0d0d0d', '#00ff88', '#ff00ff'] },
  ]

  const FONTS = [
    { id: 'inter',    label: 'Inter',     sample: 'Clean & Modern' },
    { id: 'outfit',   label: 'Outfit',    sample: 'Friendly & Bold' },
    { id: 'geist',    label: 'Geist',     sample: 'Dev-focused' },
    { id: 'poppins',  label: 'Poppins',   sample: 'Rounded & Warm' },
  ]

  const STYLES = [
    { id: 'modern',      label: 'Modern Flat' },
    { id: 'glassmorphism', label: 'Glassmorphism' },
    { id: 'brutalist',   label: 'Brutalist' },
    { id: 'minimal',     label: 'Minimal' },
  ]

  return (
    <div className="max-w-2xl mx-auto space-y-5">
      <div className="text-center space-y-1">
        <h2 className="text-xl font-bold text-white">Sistem Desain</h2>
        <p className="text-white/40 text-sm">Pilih estetika yang sesuai dengan aplikasi Anda</p>
      </div>

      {/* Color Palette */}
      <div className="bg-white/3 border border-white/8 rounded-xl p-4 space-y-3">
        <h3 className="text-xs font-semibold text-white/50 uppercase tracking-widest">Color Palette</h3>
        <div className="grid grid-cols-5 gap-2">
          {PALETTES.map(p => (
            <button
              key={p.id}
              onClick={() => setPalette(p.id)}
              className={`rounded-xl p-2 space-y-2 border transition-all ${palette === p.id ? 'border-indigo-500/50' : 'border-white/5'}`}
              style={{ background: p.colors[0] }}
            >
              <div className="flex gap-0.5">
                {p.colors.map((c, i) => (
                  <div key={i} className="flex-1 h-4 rounded-sm first:rounded-l-md last:rounded-r-md" style={{ background: c }} />
                ))}
              </div>
              <p className="text-[10px] text-center" style={{ color: p.colors[3] }}>{p.label}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Typography */}
      <div className="bg-white/3 border border-white/8 rounded-xl p-4 space-y-3">
        <h3 className="text-xs font-semibold text-white/50 uppercase tracking-widest">Typography</h3>
        <div className="grid grid-cols-4 gap-2">
          {FONTS.map(f => (
            <button
              key={f.id}
              onClick={() => setFont(f.id)}
              className={`p-3 rounded-xl border text-center transition-all ${font === f.id ? 'border-indigo-500/50 bg-indigo-500/10' : 'border-white/5 bg-white/3 hover:bg-white/5'}`}
            >
              <div className={`text-sm font-bold text-white/70`} style={{ fontFamily: f.id }}>{f.label}</div>
              <div className="text-[10px] text-white/30 mt-0.5">{f.sample}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Style */}
      <div className="bg-white/3 border border-white/8 rounded-xl p-4 space-y-3">
        <h3 className="text-xs font-semibold text-white/50 uppercase tracking-widest">UI Style</h3>
        <div className="grid grid-cols-4 gap-2">
          {STYLES.map(s => (
            <button
              key={s.id}
              onClick={() => setStyle(s.id)}
              className={`py-2 px-3 rounded-xl border text-xs font-medium transition-all ${style === s.id ? 'border-indigo-500/50 bg-indigo-500/10 text-indigo-300' : 'border-white/5 bg-white/3 text-white/40 hover:bg-white/5'}`}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex gap-3">
        <button onClick={onBack} className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm text-white/50 bg-white/5 hover:bg-white/10 transition-all">
          <ArrowLeft size={14} /> Kembali
        </button>
        <button
          onClick={() => onNext({ palette, font, style })}
          className="flex-1 py-2.5 rounded-xl font-semibold text-sm flex items-center justify-center gap-2 transition-all"
          style={{ background: 'linear-gradient(135deg, #4f6ef7 0%, #7b93ff 100%)', color: 'white' }}
        >
          Mulai Build <Rocket size={14} />
        </button>
      </div>
    </div>
  )
}

// ── Step 4: Build ───────────────────────────────────────────────────────────
function StepBuild({ config, onBack }) {
  const navigate = useNavigate()
  const [status, setStatus] = useState('ready') // ready | building | done | error
  const [logs, setLogs] = useState([])
  const [prompt, setPrompt] = useState('')
  const logsRef = useRef(null)

  const buildPrompt = `Buat ${config?.appType || 'web'} app dengan deskripsi berikut:\n${config?.description}\n\nGunakan design: ${JSON.stringify(config?.design || {})}`

  const startBuild = () => {
    setStatus('building')
    setLogs([{ time: new Date().toLocaleTimeString(), text: '🚀 Memulai build...', type: 'info' }])
    // Redirect ke chat dengan pre-filled prompt
    navigate('/chat', { state: { prefillPrompt: prompt || buildPrompt } })
  }

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      <div className="text-center space-y-1">
        <h2 className="text-xl font-bold text-white">Build Aplikasi</h2>
        <p className="text-white/40 text-sm">AI akan membuat kode berdasarkan rencana yang sudah dibuat</p>
      </div>

      {/* Config Summary */}
      <div className="bg-white/3 border border-white/8 rounded-xl p-4 space-y-2">
        <h3 className="text-xs font-semibold text-white/50 uppercase tracking-widest">Konfigurasi Build</h3>
        <div className="text-sm text-white/60 space-y-1">
          <div><span className="text-white/30">Tipe: </span><span className="text-indigo-300">{config?.appType}</span></div>
          <div><span className="text-white/30">Deskripsi: </span>{config?.description?.slice(0, 100)}...</div>
        </div>
      </div>

      {/* Custom Prompt */}
      <div>
        <label className="text-xs font-semibold text-white/50 uppercase tracking-widest block mb-2">
          Instruksi Tambahan (opsional)
        </label>
        <textarea
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          placeholder="Tambahan: pakai bahasa Indonesia, tambah dark mode, dll..."
          className="w-full h-20 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white/80 placeholder-white/20 focus:outline-none focus:border-indigo-500/50 resize-none transition-all"
        />
      </div>

      <div className="flex gap-3">
        <button onClick={onBack} className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm text-white/50 bg-white/5 hover:bg-white/10 transition-all">
          <ArrowLeft size={14} /> Kembali
        </button>
        <button
          onClick={startBuild}
          className="flex-1 py-2.5 rounded-xl font-bold text-sm flex items-center justify-center gap-2 transition-all hover:scale-[1.02]"
          style={{ background: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)', color: 'white' }}
        >
          <Sparkles size={15} />
          Kirim ke Agent & Build
        </button>
      </div>
    </div>
  )
}

// ── Main AppBuilder Page ────────────────────────────────────────────────────
export default function AppBuilder() {
  const [step, setStep] = useState('describe')
  const [config, setConfig] = useState({})
  const [planData, setPlanData] = useState(null)
  const [isLoading, setIsLoading] = useState(false)

  const handleDescribeNext = async ({ description, appType }) => {
    setConfig(prev => ({ ...prev, description, appType }))
    setStep('plan')
    setIsLoading(true)
    try {
      const res = await api.post('/chat/app_plan', { description, app_type: appType })
      setPlanData(res.data?.plan || {
        tech_stack: { Frontend: 'React + Vite', Backend: 'FastAPI', Database: 'SQLite' },
        folder_structure: ['frontend/src/', 'backend/api/', 'backend/core/', 'docker-compose.yml'],
        development_phases: [
          { phase: 1, name: 'Setup', tasks: ['Init project', 'Setup env'] },
          { phase: 2, name: 'Core Features', tasks: ['Build main features'] },
          { phase: 3, name: 'UI/UX', tasks: ['Design & implement UI'] },
          { phase: 4, name: 'Testing', tasks: ['Write tests', 'Fix bugs'] },
          { phase: 5, name: 'Deploy', tasks: ['Docker', 'Production setup'] },
        ]
      })
    } catch {
      // Fallback plan jika API gagal
      setPlanData({
        tech_stack: { Frontend: 'React + Vite', Backend: 'FastAPI', Database: 'SQLite' },
        folder_structure: ['frontend/src/', 'backend/api/', 'backend/core/', 'docker-compose.yml'],
        development_phases: [
          { phase: 1, name: 'Setup', tasks: ['Init project', 'Setup env'] },
          { phase: 2, name: 'Core Features', tasks: ['Build main features'] },
          { phase: 3, name: 'Deploy', tasks: ['Docker', 'Production setup'] },
        ]
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handlePlanNext = (plan) => {
    setConfig(prev => ({ ...prev, plan }))
    setStep('design')
  }

  const handleDesignNext = (design) => {
    setConfig(prev => ({ ...prev, design }))
    setStep('build')
  }

  return (
    <div className="min-h-screen bg-[var(--bg)] text-white">
      {/* Header */}
      <div className="border-b border-white/5 bg-white/2">
        <div className="max-w-3xl mx-auto px-6 py-4 flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500/30 to-purple-500/30 border border-indigo-500/20 flex items-center justify-center">
            <Layers size={15} className="text-indigo-400" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-white">App Builder</h1>
            <p className="text-xs text-white/40">Plan → Design → Build → Deploy</p>
          </div>
        </div>
      </div>

      {/* Step Indicator */}
      <StepBar currentStep={step} />

      {/* Content */}
      <div className="max-w-3xl mx-auto px-6 pb-12">
        {step === 'describe' && <StepDescribe onNext={handleDescribeNext} />}
        {step === 'plan'     && <StepPlan planData={isLoading ? null : planData} config={config} onNext={handlePlanNext} onBack={() => setStep('describe')} />}
        {step === 'design'   && <StepDesign onNext={handleDesignNext} onBack={() => setStep('plan')} />}
        {step === 'build'    && <StepBuild config={config} onBack={() => setStep('design')} />}
      </div>
    </div>
  )
}
