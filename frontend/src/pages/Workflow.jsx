import { useState, useCallback } from 'react'
import { NavLink } from 'react-router-dom'
import toast from 'react-hot-toast'
import {
  Plus, Trash2, Save, ChevronDown, GripVertical,
  Repeat2, ArrowDown, Sparkles, Brain, AlertTriangle, Plug,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
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
  const { t } = useTranslation()
  const isLast = index === total - 1

  return (
    <div className="relative">
      {/* Step card */}
      <div className="bg-bg-2 border-2 border-border rounded-2xl overflow-hidden transition-all hover:border-accent/40 hover:shadow-2xl hover:shadow-accent/5 group">
        {/* Step header */}
        <div className="flex items-center gap-4 px-5 py-4 border-b-2 border-border bg-bg-3/50">
          <div className="flex items-center gap-3">
            <GripVertical size={18} className="text-ink-3 opacity-0 group-hover:opacity-100 transition-opacity cursor-grab" />
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent to-accent-2 flex items-center justify-center flex-shrink-0 shadow-lg shadow-accent/20">
              <span className="text-sm font-bold text-white">{index + 1}</span>
            </div>
            <div>
              <h4 className="text-lg font-bold text-ink uppercase tracking-tight">{t('step_label')} {index + 1}</h4>
              <p className="text-xs text-ink-3 leading-tight font-bold uppercase tracking-widest opacity-50">Pipeline step #{index + 1}</p>
            </div>
          </div>
          <div className="ml-auto flex items-center gap-2">
            {total > 1 && (
              <button
                onClick={() => onDelete(step.id)}
                className="p-2 rounded-xl text-ink-3 hover:bg-danger/10 hover:text-danger transition-all opacity-0 group-hover:opacity-100 shadow-sm"
                title="Hapus langkah ini"
              >
                <Trash2 size={18} />
              </button>
            )}
          </div>
        </div>

        {/* Step body */}
        <div className="p-6 space-y-6">
          {/* Model selector */}
          <div>
            <label className="flex items-center gap-2 text-sm font-bold text-ink-2 mb-2 uppercase tracking-widest opacity-60">
              <Brain size={16} className="text-accent-2" />
              AI Model
            </label>
            <div className="relative">
              {modelsEmpty ? (
                /* Empty state — no models available */
                <div className="w-full bg-bg-4 border-2 border-warn/30 rounded-xl px-4 py-3 text-sm text-warn/80 flex items-center gap-3 shadow-inner">
                  <AlertTriangle size={16} className="flex-shrink-0 text-warn" />
                  <span className="font-semibold">⚠️ Pilih model di menu Integrasi terlebih dahulu</span>
                </div>
              ) : (
                <>
                  <select
                    value={step.modelId}
                    onChange={(e) => onUpdate(step.id, 'modelId', e.target.value)}
                    className="w-full bg-bg-2 border-2 border-border-2 rounded-xl px-4 py-3 text-sm font-bold text-ink outline-none appearance-none cursor-pointer hover:border-accent/40 focus:border-accent transition-all shadow-inner"
                  >
                    <option value="" disabled>Pilih model AI...</option>
                    {availableModels.map((m) => (
                      <option key={m.id} value={m.id}>{m.name} — {m.provider}</option>
                    ))}
                  </select>
                  <ChevronDown size={16} className="absolute right-4 top-1/2 -translate-y-1/2 text-ink-3 pointer-events-none" />
                </>
              )}
            </div>
          </div>

          {/* System Prompt */}
          <div>
            <label className="flex items-center gap-2 text-sm font-bold text-ink-2 mb-2 uppercase tracking-widest opacity-60">
              <Sparkles size={16} className="text-accent-2" />
              System Prompt / Instruksi
            </label>
            <textarea
              value={step.systemPrompt}
              onChange={(e) => onUpdate(step.id, 'systemPrompt', e.target.value)}
              placeholder="Tuliskan instruksi yang jelas untuk AI di langkah ini. Contoh: 'Kamu adalah analis data. Analisa data input dan berikan ringkasan dalam format tabel...'"
              rows={4}
              className="w-full bg-bg-2 border-2 border-border-2 rounded-xl px-4 py-3 text-sm font-bold text-ink placeholder-ink-3 outline-none resize-none hover:border-accent/40 focus:border-accent transition-all leading-relaxed shadow-inner"
            />
          </div>
        </div>
      </div>

      {/* Connector line & arrow (except last step) */}
      {!isLast && (
        <div className="flex flex-col items-center py-2">
          <div className="w-0.5 h-6 bg-gradient-to-b from-accent/60 to-accent/20" />
          <div className="w-10 h-10 rounded-full bg-bg-3 border-2 border-border-2 flex items-center justify-center shadow-lg">
            <ArrowDown size={18} className="text-accent-2" />
          </div>
          <div className="w-0.5 h-6 bg-gradient-to-b from-accent/20 to-accent/10" />
        </div>
      )}
    </div>
  )
}

// ── Main Workflow Editor Page ─────────────────────────────────────
export default function Workflow() {
  const { t } = useTranslation()
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
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-accent to-accent-2 flex items-center justify-center shadow-2xl shadow-accent/25">
            <Repeat2 size={28} className="text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-ink uppercase tracking-tighter">{t('workflow_editor_title')}</h1>
            <p className="text-base text-ink-3 mt-1 font-semibold uppercase tracking-tight opacity-70">{t('workflow_editor_desc')}</p>
          </div>
        </div>
      </div>

      {/* ═══ Empty models warning banner ═══ */}
      {modelsEmpty && (
        <div className="mb-8 bg-warn/10 border-2 border-warn/20 rounded-2xl p-6 flex items-start gap-5 shadow-inner">
          <AlertTriangle size={32} className="text-warn flex-shrink-0 mt-1" />
          <div className="flex-1">
            <h3 className="text-lg font-bold text-warn mb-1 uppercase tracking-tight">{t('no_active_models')}</h3>
            <p className="text-sm text-ink-3 mb-4 font-semibold opacity-80 leading-relaxed">
              {t('no_active_models_desc')}
            </p>
            <NavLink
              to="/integrations"
              className="inline-flex items-center gap-3 px-6 py-3 rounded-xl text-sm font-bold uppercase tracking-widest bg-accent text-white hover:bg-accent/80 transition-all shadow-lg active:scale-95"
            >
              <Plug size={16} />
              {t('open_integrations')}
            </NavLink>
          </div>
        </div>
      )}

      {/* ═══ Header Section — Name & Description ═══ */}
      <div className="bg-bg-3 border-2 border-border rounded-2xl p-6 mb-8 shadow-lg">
        <div className="grid grid-cols-1 gap-6">
          {/* Workflow Name */}
          <div>
            <label htmlFor="workflow-name" className="text-xs font-bold text-ink-3 mb-2 block uppercase tracking-widest opacity-60">
              {t('workflow_name')} <span className="text-danger">*</span>
            </label>
            <input
              id="workflow-name"
              type="text"
              value={workflowName}
              onChange={(e) => setWorkflowName(e.target.value)}
              placeholder="Masukkan nama workflow..."
              className="w-full bg-bg-2 border-2 border-border-2 rounded-xl px-4 py-3 text-sm font-bold text-ink placeholder-ink-3 outline-none hover:border-accent/40 focus:border-accent transition-all shadow-inner"
            />
          </div>

          {/* Description / Trigger */}
          <div>
            <label htmlFor="workflow-description" className="text-xs font-bold text-ink-3 mb-2 block uppercase tracking-widest opacity-60">
              {t('workflow_description')}
            </label>
            <textarea
              id="workflow-description"
              value={workflowDescription}
              onChange={(e) => setWorkflowDescription(e.target.value)}
              placeholder="Jelaskan kapan Auto-Orchestrator harus memicu workflow ini..."
              rows={3}
              className="w-full bg-bg-2 border-2 border-border-2 rounded-xl px-4 py-3 text-sm font-bold text-ink placeholder-ink-3 outline-none resize-none hover:border-accent/40 focus:border-accent transition-all leading-relaxed shadow-inner"
            />
          </div>
        </div>
      </div>

      {/* ═══ Pipeline Section Header ═══ */}
      <div className="flex items-center gap-4 mb-6">
        <div className="flex items-center gap-3">
          <div className="w-2.5 h-2.5 rounded-full bg-accent animate-pulse" />
          <h2 className="text-lg font-bold text-ink uppercase tracking-tight">{t('pipeline_steps')}</h2>
        </div>
        <div className="flex-1 h-[2px] bg-border" />
        <span className="text-[10px] text-ink-3 font-bold bg-bg-3 border-2 border-border rounded-full px-4 py-1.5 uppercase tracking-widest shadow-sm">
          {steps.length} {t('step_label')}
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
      <div className="flex items-center justify-between gap-4 mt-8">
        {/* Add step */}
        <button
          onClick={addStep}
          disabled={modelsEmpty}
          className={clsx(
            'flex items-center gap-3 px-6 py-4 rounded-2xl border-2 border-dashed text-sm font-bold uppercase tracking-widest transition-all shadow-md active:scale-95',
            modelsEmpty
              ? 'border-border text-ink-3 opacity-40 cursor-not-allowed'
              : 'border-border-2 text-ink-2 hover:text-accent-2 hover:border-accent/60 hover:bg-accent/8 hover:shadow-xl'
          )}
          title={modelsEmpty ? 'Tambahkan model AI di Integrasi terlebih dahulu' : 'Tambah langkah baru'}
        >
          <Plus size={20} />
          {t('add_step_label')}
        </button>

        {/* Save workflow */}
        <button
          onClick={handleSave}
          disabled={saving}
          className={clsx(
            'flex items-center gap-3 px-10 py-4 rounded-2xl text-white text-sm font-bold uppercase tracking-widest transition-all shadow-2xl active:scale-95',
            saving
              ? 'bg-accent/60 cursor-not-allowed'
              : 'bg-accent hover:bg-accent/85 shadow-accent/25'
          )}
        >
          <Save size={20} className={clsx(saving && 'animate-spin')} />
          {saving ? t('saving') : t('save_workflow')}
        </button>
      </div>

      {/* ═══ Helper Info ═══ */}
      <div className="mt-12 bg-bg-3 border-2 border-border rounded-2xl p-6 shadow-inner">
        <h3 className="text-sm font-bold text-ink mb-4 flex items-center gap-3 uppercase tracking-widest opacity-80">
          <Sparkles size={18} className="text-accent-2" />
          {t('how_pipeline_works')}
        </h3>
        <ul className="text-sm text-ink-3 space-y-3 font-semibold leading-relaxed">
          <li className="flex items-start gap-3">
            <span className="text-accent-2 mt-1 text-lg leading-none">•</span>
            <span>Setiap <strong className="text-ink-2 font-bold uppercase tracking-tight">Langkah</strong> dalam pipeline dieksekusi secara berurutan oleh agent yang ditunjuk.</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="text-accent-2 mt-1 text-lg leading-none">•</span>
            <span>Output dari Langkah n menjadi input untuk Langkah n+1, menciptakan rantai pemikiran (Chain of Thought).</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="text-accent-2 mt-1 text-lg leading-none">•</span>
            <span>Gunakan <strong className="text-ink-2 font-bold uppercase tracking-tight">model AI</strong> yang berbeda untuk tugas spesifik (misal: R1 untuk penalaran, GPT-4o untuk ringkasan).</span>
          </li>
          <li className="flex items-start gap-3">
            <span className="text-accent-2 mt-1 text-lg leading-none">•</span>
            <span>Sistem akan mendeteksi intent pengguna dan memicu workflow ini secara otomatis jika deskripsi trigger relevan.</span>
          </li>
        </ul>
      </div>
    </div>
  )
}
