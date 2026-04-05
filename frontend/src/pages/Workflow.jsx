import { useState, useCallback } from 'react'
import { NavLink } from 'react-router-dom'
import toast from 'react-hot-toast'
import {
  Plus, Trash2, Save, ChevronDown, GripVertical,
  Repeat2, ArrowDown, Sparkles, Brain, AlertTriangle, Plug,
} from 'lucide-react'
import clsx from 'clsx'
import { useOrchestratorStore } from '../store'

// ── Unique ID generator ───────────────────────────────────────────
let _stepId = 0
const nextId = () => `step-${++_stepId}-${Date.now()}`

// ── Default empty step ────────────────────────────────────────────
const createEmptyStep = (order, models) => ({
  id: nextId(),
  order,
  modelId: models[0]?.id || '',
  systemPrompt: '',
})

// ── Step Card Component ───────────────────────────────────────────
function StepCard({ step, index, total, onUpdate, onDelete, availableModels, modelsEmpty }) {
  const isLast = index === total - 1

  return (
    <div className="relative">
      {/* Step card */}
      <div className="bg-bg-2 border border-border rounded-xl overflow-hidden transition-all hover:border-border-2 hover:shadow-lg hover:shadow-accent/5 group">
        {/* Step header */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-border bg-bg-3/50">
          <div className="flex items-center gap-2">
            <GripVertical size={14} className="text-ink-3 opacity-0 group-hover:opacity-100 transition-opacity cursor-grab" />
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-accent to-accent-2 flex items-center justify-center flex-shrink-0 shadow-md shadow-accent/20">
              <span className="text-[11px] font-bold text-white">{index + 1}</span>
            </div>
            <div>
              <h4 className="text-sm font-semibold text-ink">Langkah {index + 1}</h4>
              <p className="text-[10px] text-ink-3 leading-tight">Pipeline step #{index + 1}</p>
            </div>
          </div>
          <div className="ml-auto flex items-center gap-2">
            {total > 1 && (
              <button
                onClick={() => onDelete(step.id)}
                className="p-1.5 rounded-lg text-ink-3 hover:bg-danger/10 hover:text-danger transition-all opacity-0 group-hover:opacity-100"
                title="Hapus langkah ini"
              >
                <Trash2 size={14} />
              </button>
            )}
          </div>
        </div>

        {/* Step body */}
        <div className="p-4 space-y-4">
          {/* Model selector */}
          <div>
            <label className="flex items-center gap-1.5 text-xs font-medium text-ink-2 mb-1.5">
              <Brain size={12} className="text-accent-2" />
              AI Model
            </label>
            <div className="relative">
              {modelsEmpty ? (
                /* Empty state — no models available */
                <div className="w-full bg-bg-4 border border-warn/30 rounded-lg px-3 py-2.5 text-sm text-warn/80 flex items-center gap-2">
                  <AlertTriangle size={14} className="flex-shrink-0 text-warn" />
                  <span>⚠️ Pilih model di menu Integrasi terlebih dahulu</span>
                </div>
              ) : (
                <>
                  <select
                    value={step.modelId}
                    onChange={(e) => onUpdate(step.id, 'modelId', e.target.value)}
                    className="w-full bg-bg-4 border border-border-2 rounded-lg px-3 py-2.5 text-sm text-ink outline-none appearance-none cursor-pointer hover:border-accent/40 focus:border-accent focus:ring-1 focus:ring-accent/20 transition-all"
                  >
                    <option value="" disabled>Pilih model AI...</option>
                    {availableModels.map((m) => (
                      <option key={m.id} value={m.id}>{m.name} — {m.provider}</option>
                    ))}
                  </select>
                  <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-3 pointer-events-none" />
                </>
              )}
            </div>
          </div>

          {/* System Prompt */}
          <div>
            <label className="flex items-center gap-1.5 text-xs font-medium text-ink-2 mb-1.5">
              <Sparkles size={12} className="text-accent-2" />
              System Prompt / Instruksi
            </label>
            <textarea
              value={step.systemPrompt}
              onChange={(e) => onUpdate(step.id, 'systemPrompt', e.target.value)}
              placeholder="Tuliskan instruksi yang jelas untuk AI di langkah ini. Contoh: 'Kamu adalah analis data. Analisa data input dan berikan ringkasan dalam format tabel...'"
              rows={4}
              className="w-full bg-bg-4 border border-border-2 rounded-lg px-3 py-2.5 text-sm text-ink placeholder-ink-3 outline-none resize-none hover:border-accent/40 focus:border-accent focus:ring-1 focus:ring-accent/20 transition-all leading-relaxed"
            />
          </div>
        </div>
      </div>

      {/* Connector line & arrow (except last step) */}
      {!isLast && (
        <div className="flex flex-col items-center py-1">
          <div className="w-px h-5 bg-gradient-to-b from-accent/40 to-accent/20" />
          <div className="w-7 h-7 rounded-full bg-bg-3 border border-border-2 flex items-center justify-center shadow-sm">
            <ArrowDown size={13} className="text-accent-2" />
          </div>
          <div className="w-px h-5 bg-gradient-to-b from-accent/20 to-accent/10" />
        </div>
      )}
    </div>
  )
}

// ── Main Workflow Editor Page ─────────────────────────────────────
export default function Workflow() {
  // Read configured models from store — NO fallback to mock data
  const activeConfiguredModels = useOrchestratorStore(s => s.activeConfiguredModels)
  const addWorkflow = useOrchestratorStore(s => s.addWorkflow)
  const modelsEmpty = activeConfiguredModels.length === 0

  const [workflowName, setWorkflowName] = useState('')
  const [workflowDescription, setWorkflowDescription] = useState('')
  const [steps, setSteps] = useState([createEmptyStep(1, activeConfiguredModels)])
  const [saving, setSaving] = useState(false)

  const addStep = useCallback(() => {
    setSteps(prev => [...prev, createEmptyStep(prev.length + 1, activeConfiguredModels)])
  }, [activeConfiguredModels])

  const removeStep = useCallback((stepId) => {
    setSteps(prev => {
      const filtered = prev.filter(s => s.id !== stepId)
      return filtered.map((s, i) => ({ ...s, order: i + 1 }))
    })
  }, [])

  const updateStep = useCallback((stepId, field, value) => {
    setSteps(prev => prev.map(s =>
      s.id === stepId ? { ...s, [field]: value } : s
    ))
  }, [])

  const handleSave = async () => {
    if (!workflowName.trim()) {
      toast.error('Nama workflow tidak boleh kosong')
      return
    }
    if (!modelsEmpty && steps.some(s => !s.modelId)) {
      toast.error('Semua langkah harus memiliki model AI')
      return
    }

    setSaving(true)
    // Simulate API call
    await new Promise(r => setTimeout(r, 1200))
    setSaving(false)

    const payload = {
      id: `wf-${Date.now()}`,
      name: `⚙️ ${workflowName}`,
      description: workflowDescription,
      steps: steps.map(s => ({
        order: s.order,
        model_id: s.modelId,
        system_prompt: s.systemPrompt,
      })),
    }

    // Add to global state
    addWorkflow({ id: payload.id, name: payload.name, description: payload.description })

    console.log('Workflow saved:', payload)
    toast.success('Workflow berhasil disimpan!')
  }

  return (
    <div className="p-4 md:p-6 w-full max-w-4xl mx-auto">
      {/* ═══ Page Header ═══ */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent to-accent-2 flex items-center justify-center shadow-lg shadow-accent/25">
            <Repeat2 size={20} className="text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-ink">Workflow Editor</h1>
            <p className="text-xs text-ink-3 mt-0.5">Bangun pipeline multi-agent step-by-step</p>
          </div>
        </div>
      </div>

      {/* ═══ Empty models warning banner ═══ */}
      {modelsEmpty && (
        <div className="mb-6 bg-warn/10 border border-warn/20 rounded-xl p-4 flex items-start gap-3">
          <AlertTriangle size={18} className="text-warn flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="text-sm font-semibold text-warn mb-1">Belum Ada Model AI Terkonfigurasi</h3>
            <p className="text-xs text-ink-3 mb-2.5">
              Anda harus menambahkan setidaknya satu model AI di halaman Integrasi sebelum bisa membuat workflow pipeline.
            </p>
            <NavLink
              to="/integrations"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-accent/10 text-accent-2 hover:bg-accent/20 transition-colors"
            >
              <Plug size={12} />
              Buka Integrasi Platform
            </NavLink>
          </div>
        </div>
      )}

      {/* ═══ Header Section — Name & Description ═══ */}
      <div className="bg-bg-2 border border-border rounded-xl p-5 mb-6">
        <div className="grid grid-cols-1 gap-4">
          {/* Workflow Name */}
          <div>
            <label htmlFor="workflow-name" className="text-xs font-medium text-ink-2 mb-1.5 block">
              Nama Workflow <span className="text-danger">*</span>
            </label>
            <input
              id="workflow-name"
              type="text"
              value={workflowName}
              onChange={(e) => setWorkflowName(e.target.value)}
              placeholder="Masukkan nama workflow..."
              className="w-full bg-bg-4 border border-border-2 rounded-lg px-3.5 py-2.5 text-sm text-ink placeholder-ink-3 outline-none hover:border-accent/40 focus:border-accent focus:ring-2 focus:ring-accent/20 transition-all"
            />
          </div>

          {/* Description / Trigger */}
          <div>
            <label htmlFor="workflow-description" className="text-xs font-medium text-ink-2 mb-1.5 block">
              Deskripsi / Trigger
            </label>
            <textarea
              id="workflow-description"
              value={workflowDescription}
              onChange={(e) => setWorkflowDescription(e.target.value)}
              placeholder="Jelaskan kapan Auto-Orchestrator harus memicu workflow ini..."
              rows={3}
              className="w-full bg-bg-4 border border-border-2 rounded-lg px-3.5 py-2.5 text-sm text-ink placeholder-ink-3 outline-none resize-none hover:border-accent/40 focus:border-accent focus:ring-2 focus:ring-accent/20 transition-all leading-relaxed"
            />
          </div>
        </div>
      </div>

      {/* ═══ Pipeline Section Header ═══ */}
      <div className="flex items-center gap-2 mb-4">
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse2" />
          <h2 className="text-sm font-semibold text-ink">Pipeline Steps</h2>
        </div>
        <div className="flex-1 h-px bg-border" />
        <span className="text-[10px] text-ink-3 font-medium bg-bg-3 border border-border rounded-full px-2.5 py-0.5">
          {steps.length} {steps.length === 1 ? 'langkah' : 'langkah'}
        </span>
      </div>

      {/* ═══ Pipeline Steps ═══ */}
      <div className="mb-6">
        {steps.map((step, idx) => (
          <StepCard
            key={step.id}
            step={step}
            index={idx}
            total={steps.length}
            onUpdate={updateStep}
            onDelete={removeStep}
            availableModels={activeConfiguredModels}
            modelsEmpty={modelsEmpty}
          />
        ))}
      </div>

      {/* ═══ Action Buttons ═══ */}
      <div className="flex items-center justify-between gap-3">
        {/* Add step */}
        <button
          onClick={addStep}
          disabled={modelsEmpty}
          className={clsx(
            'flex items-center gap-2 px-4 py-2.5 rounded-lg border border-dashed text-sm font-medium transition-all',
            modelsEmpty
              ? 'border-border text-ink-3 opacity-50 cursor-not-allowed'
              : 'border-border-2 text-ink-2 hover:text-accent-2 hover:border-accent/40 hover:bg-accent/5'
          )}
          title={modelsEmpty ? 'Tambahkan model AI di Integrasi terlebih dahulu' : 'Tambah langkah baru'}
        >
          <Plus size={15} />
          Tambah Langkah
        </button>

        {/* Save workflow */}
        <button
          onClick={handleSave}
          disabled={saving}
          className={clsx(
            'flex items-center gap-2 px-6 py-2.5 rounded-lg text-white text-sm font-semibold transition-all shadow-lg shadow-accent/25',
            saving
              ? 'bg-accent/60 cursor-not-allowed'
              : 'bg-accent hover:bg-accent/85 active:scale-[0.98]'
          )}
        >
          <Save size={15} className={clsx(saving && 'animate-spin')} />
          {saving ? 'Menyimpan...' : 'Simpan Workflow'}
        </button>
      </div>

      {/* ═══ Helper Info ═══ */}
      <div className="mt-8 bg-bg-3 border border-border rounded-xl p-4">
        <h3 className="text-xs font-semibold text-ink mb-2 flex items-center gap-1.5">
          <Sparkles size={12} className="text-accent-2" />
          Bagaimana Pipeline Bekerja?
        </h3>
        <ul className="text-xs text-ink-3 space-y-1.5">
          <li className="flex items-start gap-2">
            <span className="text-accent-2 mt-0.5">•</span>
            <span>Setiap <strong className="text-ink-2">Langkah</strong> dalam pipeline dieksekusi secara berurutan.</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-accent-2 mt-0.5">•</span>
            <span>Output dari Langkah 1 menjadi input untuk Langkah 2, dan seterusnya.</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-accent-2 mt-0.5">•</span>
            <span>Pilih <strong className="text-ink-2">model AI</strong> yang tepat dan tulis <strong className="text-ink-2">system prompt</strong> yang jelas untuk setiap langkah.</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-accent-2 mt-0.5">•</span>
            <span><strong className="text-ink-2">Auto-Orchestrator</strong> akan memicu workflow ini berdasarkan deskripsi trigger yang kamu tulis.</span>
          </li>
        </ul>
      </div>
    </div>
  )
}
