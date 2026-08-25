/**
 * AgentLoopVisualizer — Real-time ReAct Loop Visualizer
 * Menampilkan langkah Think → Act → Observe → Reflect secara live
 */
import React, { useState, useEffect, useRef } from 'react'
import { Brain, Zap, Eye, RefreshCw, CheckCircle2, AlertCircle, ChevronDown, ChevronUp } from 'lucide-react'
import clsx from 'clsx'

// Step configs
const STEP_CONFIG = {
  think:   { icon: Brain,       label: 'Think',   color: '#818cf8', bg: 'rgba(129,140,248,0.08)' },
  act:     { icon: Zap,         label: 'Act',      color: '#f59e0b', bg: 'rgba(245,158,11,0.08)'  },
  observe: { icon: Eye,         label: 'Observe',  color: '#34d399', bg: 'rgba(52,211,153,0.08)'  },
  reflect: { icon: RefreshCw,   label: 'Reflect',  color: '#60a5fa', bg: 'rgba(96,165,250,0.08)'  },
  done:    { icon: CheckCircle2, label: 'Done',     color: '#22c55e', bg: 'rgba(34,197,94,0.08)'   },
  error:   { icon: AlertCircle,  label: 'Error',    color: '#ef4444', bg: 'rgba(239,68,68,0.08)'   },
}

function ConfidenceBar({ confidence }) {
  const pct = Math.round(confidence * 100)
  const color = pct >= 90 ? '#22c55e' : pct >= 70 ? '#f59e0b' : '#ef4444'
  return (
    <div className="flex items-center gap-2 mt-1">
      <div className="flex-1 h-1 rounded-full bg-white/5 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      <span className="text-[10px] font-mono" style={{ color }}>{pct}%</span>
    </div>
  )
}

function StepCard({ event, isActive, index }) {
  const [expanded, setExpanded] = useState(isActive)
  const cfg = STEP_CONFIG[event.step] || STEP_CONFIG.think
  const Icon = cfg.icon

  useEffect(() => { if (isActive) setExpanded(true) }, [isActive])

  return (
    <div
      className={clsx(
        'rounded-xl border transition-all duration-300 overflow-hidden',
        isActive ? 'border-white/10 shadow-lg' : 'border-white/5 opacity-70'
      )}
      style={{ background: cfg.bg }}
    >
      {/* Header */}
      <button
        className="w-full flex items-center gap-2.5 px-3 py-2 text-left"
        onClick={() => setExpanded(v => !v)}
      >
        {/* Step number */}
        <span className="text-[10px] font-mono text-white/30 w-5 shrink-0">#{index + 1}</span>

        {/* Icon */}
        <div
          className={clsx('w-6 h-6 rounded-lg flex items-center justify-center shrink-0', isActive && 'animate-pulse')}
          style={{ backgroundColor: cfg.color + '22' }}
        >
          <Icon size={12} style={{ color: cfg.color }} />
        </div>

        {/* Step name */}
        <span className="text-xs font-semibold" style={{ color: cfg.color }}>
          {cfg.label}
        </span>

        {/* Iteration badge */}
        {event.iteration && (
          <span className="text-[10px] text-white/30 font-mono ml-0.5">
            iter {event.iteration}
          </span>
        )}

        {/* Action badge */}
        {event.action && (
          <span className="ml-auto text-[10px] bg-white/5 px-2 py-0.5 rounded-full text-white/50 font-mono truncate max-w-[120px]">
            {event.action}
          </span>
        )}

        {/* Confidence */}
        {event.confidence > 0 && (
          <span className="text-[10px] font-mono ml-auto" style={{ color: cfg.color }}>
            {Math.round(event.confidence * 100)}%
          </span>
        )}

        <div className="text-white/20 ml-1">
          {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        </div>
      </button>

      {/* Detail */}
      {expanded && event.detail && (
        <div className="px-3 pb-3 pt-0">
          <p className="text-xs text-white/50 leading-relaxed whitespace-pre-wrap break-words">
            {event.detail}
          </p>
          {event.confidence > 0 && <ConfidenceBar confidence={event.confidence} />}
        </div>
      )}
    </div>
  )
}

/**
 * AgentLoopVisualizer
 *
 * Props:
 *   events   - Array of loop_step events dari SSE
 *   isActive - Boolean apakah loop masih berjalan
 *   isDone   - Boolean apakah loop selesai
 *   result   - Object { reason, iterations, confidence } dari loop_done
 */
export default function AgentLoopVisualizer({ events = [], isActive = false, isDone = false, result = null }) {
  const [collapsed, setCollapsed] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    if (!collapsed && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, [events.length, collapsed])

  if (!events.length && !isActive) return null

  const totalIterations = result?.iterations || (events.length > 0 ? events[events.length - 1]?.iteration : 0)
  const stopReason = result?.reason || (isDone ? 'done' : null)

  return (
    <div className="rounded-2xl border border-white/5 overflow-hidden" style={{ background: 'rgba(255,255,255,0.02)' }}>
      {/* Header */}
      <button
        className="w-full flex items-center gap-2 px-4 py-2.5 hover:bg-white/5 transition-all text-left"
        onClick={() => setCollapsed(v => !v)}
      >
        <Brain size={13} className="text-indigo-400 shrink-0" />
        <span className="text-xs font-semibold text-white/70 flex-1">
          Agent Loop
          {totalIterations > 0 && (
            <span className="ml-1.5 text-white/30 font-mono text-[10px]">
              {totalIterations} iterasi
            </span>
          )}
        </span>

        {/* Status pill */}
        {isActive && !isDone && (
          <span className="flex items-center gap-1 text-[10px] bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded-full">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
            Running
          </span>
        )}
        {isDone && (
          <span className="flex items-center gap-1 text-[10px] bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded-full">
            <CheckCircle2 size={10} />
            {stopReason === 'early_stop' ? 'Early Stop' : stopReason === 'max_iter' ? 'Max Iter' : 'Done'}
          </span>
        )}

        <div className="text-white/20">
          {collapsed ? <ChevronDown size={12} /> : <ChevronUp size={12} />}
        </div>
      </button>

      {/* Steps */}
      {!collapsed && (
        <div className="px-3 pb-3 space-y-1.5">
          {events.map((event, i) => (
            <StepCard
              key={i}
              event={event}
              isActive={isActive && i === events.length - 1}
              index={i}
            />
          ))}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  )
}
