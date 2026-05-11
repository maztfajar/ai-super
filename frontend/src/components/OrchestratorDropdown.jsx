import { useState, useRef, useEffect } from 'react'
import { NavLink } from 'react-router-dom'
import { ChevronDown, Sparkles, Workflow, Brain, Check, AlertTriangle, Plug } from 'lucide-react'
import clsx from 'clsx'
import { AUTO_ORCHESTRATOR } from '../data/mockOrchestratorData'
import { useOrchestratorStore } from '../store'

/**
 * OrchestratorDropdown — Categorized custom dropdown for the top navbar.
 * Shows 3 categories: AUTO, WORKFLOWS, SINGLE MODELS.
 * Default selection: Auto-Orchestrator.
 *
 * SINGLE MODELS reads from Zustand `activeConfiguredModels` (populated by Integrasi page).
 * WORKFLOWS reads from Zustand `savedWorkflows`.
 * If empty → shows a warning with a link to the relevant page.
 */
export default function OrchestratorDropdown({ value, onChange, compact = false }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  // Read from global store
  const activeConfiguredModels = useOrchestratorStore(s => s.activeConfiguredModels)
  const savedWorkflows = useOrchestratorStore(s => s.savedWorkflows)

  // Close on outside click
  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // Close on Escape
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [])

  // Resolve display label
  const getSelectedLabel = () => {
    if (!value || value === AUTO_ORCHESTRATOR.id) return AUTO_ORCHESTRATOR.name
    const wf = savedWorkflows.find(w => w.id === value)
    if (wf) return wf.name
    const model = activeConfiguredModels.find(m => m.id === value)
    if (model) return model.name
    return '✨ Auto-Orchestrator'
  }

  const selected = value || AUTO_ORCHESTRATOR.id

  const handleSelect = (id) => {
    onChange?.(id)
    setOpen(false)
  }

  return (
    <div ref={ref} className="relative" id="orchestrator-dropdown">
      {/* Trigger button */}
      <button
        onClick={() => setOpen(!open)}
        className={clsx(
          'flex items-center gap-2.5 rounded-lg text-sm font-semibold transition-all border shadow-sm',
          'bg-bg-4 border-border-2 text-ink hover:bg-bg-5 hover:border-accent/40',
          open && 'border-accent/60 bg-bg-5 ring-1 ring-accent/20',
          compact ? 'px-3 py-2' : 'px-4 py-2'
        )}
      >
        <span className={clsx('truncate font-bold', compact ? 'max-w-[140px]' : 'max-w-[200px]')}>{getSelectedLabel()}</span>
        <ChevronDown
          size={compact ? 13 : 15}
          className={clsx('text-ink-3 transition-transform duration-200 flex-shrink-0', open && 'rotate-180')}
        />
      </button>

      {/* Dropdown panel */}
      {open && (
        <div className="absolute right-0 top-full mt-1.5 w-72 bg-bg-2 border border-border-2 rounded-xl shadow-2xl shadow-black/20 z-[100] overflow-hidden animate-fade">
          {/* ═══ AUTO ═══ */}
          <div className="px-3 pt-3 pb-2 border-b border-border/20 mb-1">
            <div className="text-xs font-bold tracking-widest uppercase text-ink-3 flex items-center gap-2">
              <Sparkles size={12} className="text-accent-2" />
              Auto
            </div>
          </div>
          <div className="px-2 pb-1">
            <button
              onClick={() => handleSelect(AUTO_ORCHESTRATOR.id)}
              className={clsx(
                'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all text-sm',
                selected === AUTO_ORCHESTRATOR.id
                  ? 'bg-accent/10 text-accent-2 font-semibold shadow-sm'
                  : 'text-ink hover:bg-bg-4 font-medium'
              )}
            >
              <span className="flex-1">✨ Auto-Orchestrator</span>
              {selected === AUTO_ORCHESTRATOR.id && <Check size={14} className="text-accent-2" />}
              <span className="text-[11px] text-ink-3 border border-border rounded px-2 py-0.5 font-semibold uppercase bg-bg-5">Default</span>
            </button>
          </div>

          {/* Separator */}
          <div className="border-t border-border mx-3 my-1" />

          {/* ═══ WORKFLOWS (dynamic from Zustand store) ═══ */}
          <div className="px-3 pt-2 pb-2 border-b border-border/20 mb-1">
            <div className="text-xs font-bold tracking-widest uppercase text-ink-3 flex items-center gap-2">
              <Workflow size={12} className="text-accent-2" />
              Workflows
            </div>
          </div>
          <div className="px-2 pb-1 max-h-36 overflow-y-auto scrollbar-hide">
            {savedWorkflows.length === 0 ? (
              <div className="px-2.5 py-2 text-xs text-ink-3 italic">Belum ada workflow</div>
            ) : (
              savedWorkflows.map((wf) => {
                // Generate dynamic model label based on active models
                let dynamicModel = wf.model
                if (activeConfiguredModels?.length > 0) {
                  const getName = (idx) => activeConfiguredModels[idx]?.name.replace('🧠 ', '') || ''
                  
                  if (wf.id === 'wf-riset-data') {
                    dynamicModel = activeConfiguredModels.length > 1 
                      ? `Kombinasi (${getName(0)} + ${getName(1)})` 
                      : getName(0)
                  } else if (wf.id === 'wf-analisis-laporan') {
                    dynamicModel = getName(0)
                  } else if (wf.id === 'wf-auto-reply') {
                    const idx = activeConfiguredModels.length > 2 ? 2 : 0
                    dynamicModel = getName(idx)
                  }
                } else {
                  dynamicModel = '(Belum ada model AI terhubung)'
                }

                return (
                  <button
                    key={wf.id}
                    onClick={() => handleSelect(wf.id)}
                    className={clsx(
                      'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all text-sm',
                      selected === wf.id
                        ? 'bg-accent/10 text-accent-2 font-semibold shadow-sm'
                        : 'text-ink hover:bg-bg-4 font-medium'
                    )}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="truncate">{wf.name}</div>
                      <div className="text-[11px] text-ink-3 truncate mt-0.5 font-mono font-semibold">{dynamicModel}</div>
                    </div>
                    {selected === wf.id && <Check size={14} className="text-accent-2" />}
                  </button>
                )
              })
            )}
          </div>

          {/* Separator */}
          <div className="border-t border-border mx-3 my-1" />

          {/* ═══ SINGLE MODELS (dynamic from Zustand store) ═══ */}
          <div className="px-3 pt-2 pb-2 border-b border-border/20 mb-1">
            <div className="text-xs font-bold tracking-widest uppercase text-ink-3 flex items-center gap-2">
              <Brain size={12} className="text-accent-2" />
              Single Models
            </div>
          </div>
          <div className="px-2 pb-2 max-h-44 overflow-y-auto scrollbar-hide">
            {activeConfiguredModels.length === 0 ? (
              /* Empty state — no models configured */
              <div className="px-3 py-3 flex flex-col gap-2">
                <div className="flex items-start gap-2.5 text-xs text-warn font-semibold">
                  <AlertTriangle size={14} className="flex-shrink-0 mt-0.5" />
                  <span>Belum ada model terhubung. Buka menu <strong>Integrasi</strong>.</span>
                </div>
                <NavLink
                  to="/integrations"
                  onClick={() => setOpen(false)}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-bold bg-accent/10 text-accent-2 hover:bg-accent/20 transition-all shadow-sm"
                >
                  <Plug size={14} />
                  Buka Integrasi Platform
                </NavLink>
              </div>
            ) : (
              activeConfiguredModels.map((m) => (
                <button
                  key={m.id}
                  onClick={() => handleSelect(m.id)}
                  className={clsx(
                    'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all text-sm group',
                    selected === m.id
                      ? 'bg-accent/10 text-accent-2 font-semibold shadow-sm'
                      : 'text-ink hover:bg-bg-4 font-medium'
                  )}
                >
                  <span className="flex-1 truncate">{m.name}</span>
                  {selected === m.id && <Check size={14} className="text-accent-2" />}
                  <span className="text-[11px] text-ink-3 opacity-0 group-hover:opacity-100 transition-opacity font-semibold uppercase tracking-tight">{m.provider}</span>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}
