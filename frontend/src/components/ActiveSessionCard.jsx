import { useState, useEffect } from 'react'
import { MessageSquare, Clock, Zap, AlertCircle } from 'lucide-react'
import clsx from 'clsx'
import { useTranslation } from 'react-i18next'

// ── Active AI Session Card (Horizontal) ────────────────────
function ActiveSessionCardNew({ session }) {
  const { t } = useTranslation()
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    const interval = setInterval(() => {
      if (session.last_activity) {
        const diff = Math.floor((Date.now() - new Date(session.last_activity).getTime()) / 1000)
        setElapsed(diff)
      }
    }, 1000)
    return () => clearInterval(interval)
  }, [session])

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`
  }

  // Determine agents based on session title/content (smarter inference)
  const getAgentsInvolved = () => {
    const allAgents = [
      { name: t('agent_reasoning'), icon: '🧠', color: '#8B5CF6', type: 'reasoning' },
      { name: t('agent_coding'), icon: '💻', color: '#3B82F6', type: 'coding' },
      { name: t('agent_research'), icon: '🔍', color: '#10B981', type: 'research' },
      { name: t('agent_writing'), icon: '✍️', color: '#F59E0B', type: 'writing' },
      { name: t('agent_system'), icon: '🖥️', color: '#EF4444', type: 'system' },
      { name: t('agent_creative'), icon: '🎨', color: '#EC4899', type: 'creative' },
    ]
    
    const title = (session.title || '').toLowerCase()
    const model = (session.model_used || '').toLowerCase()
    const text = `${title} ${model}`
    
    // Match keywords to agents
    const matched = new Set()
    if (text.match(/code|sql|python|function|debug|script/)) matched.add('coding')
    if (text.match(/riset|research|cari|search|data/)) matched.add('research')
    if (text.match(/tulis|write|doc|email|konten|artikel/)) matched.add('writing')
    if (text.match(/analisis|logic|strategi|reason/)) matched.add('reasoning')
    if (text.match(/server|deploy|sistem|devops|vps/)) matched.add('system')
    if (text.match(/kreatif|creative|idea|brainstorm|design/)) matched.add('creative')
    
    if (matched.size > 0) {
      return allAgents.filter(a => matched.has(a.type)).slice(0, 3)
    }
    return allAgents.slice(0, 2)
  }

  // Get consistent status for this session
  const getOrchestratorStatus = () => {
    const statuses = [
      { icon: '🔄', label: t('task_breakdown'), color: '#3B82F6' },
      { icon: '💻', label: t('code_generation'), color: '#10B981' },
      { icon: '🧠', label: t('analysis_label'), color: '#8B5CF6' },
      { icon: '📊', label: t('data_processing'), color: '#F59E0B' },
    ]
    // Hash session ID to get consistent status
    const hash = session.session_id.split('').reduce((h, c) => ((h << 5) - h) + c.charCodeAt(0), 0)
    const idx = Math.abs(hash) % statuses.length
    return statuses[idx]
  }

  const orchestratorStatus = getOrchestratorStatus()
  const agents = getAgentsInvolved()

  return (
    <div
      className="relative rounded-xl p-4 mb-3 border transition-all hover:border-accent/50 overflow-hidden"
      style={{
        background: session.is_streaming 
          ? 'linear-gradient(135deg, rgba(16,185,129,0.05), rgba(59,130,246,0.05))'
          : 'rgba(255,255,255,0.02)',
        borderColor: session.is_streaming ? 'rgba(16,185,129,0.3)' : 'rgba(100,100,100,0.2)',
        boxShadow: session.is_streaming ? '0 0 16px rgba(16,185,129,0.1)' : 'none',
      }}
    >
      {/* Pulse animation untuk active sessions */}
      {session.is_streaming && (
        <div className="absolute inset-0 rounded-xl pointer-events-none"
          style={{
            boxShadow: 'inset 0 0 0 1px rgba(16,185,129,0.4)',
            animation: 'pulse 2s ease-in-out infinite',
          }} />
      )}

      <div className="relative z-10 space-y-3">
        {/* Row 1: User Prompt */}
        <div className="flex items-start gap-4 pb-3 border-b border-border/30">
          <MessageSquare size={18} className="text-ink-3 flex-shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <p className="text-base font-semibold text-ink line-clamp-2">
              {session.title || t('new_chat_session')}
            </p>
          </div>
        </div>

        {/* Row 2: Timer & Status */}
        <div className="flex items-center justify-between gap-3 mb-2 flex-wrap">
          {/* Timer */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-bg-4/50">
            <Clock size={14} className="text-accent" />
            <span className="text-xs font-mono font-bold text-ink">
              {formatTime(elapsed)}s {t('elapsed')}
            </span>
          </div>

          {/* Orchestrator Status */}
          <div className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg"
            style={{ background: `${orchestratorStatus.color}15`, border: `1px solid ${orchestratorStatus.color}30` }}>
            <span className="text-base">{orchestratorStatus.icon}</span>
            <span className="text-xs font-bold text-ink-2 uppercase tracking-tight">{orchestratorStatus.label}</span>
          </div>

          {/* Streaming Indicator */}
          {session.is_streaming && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-success/15 border border-success/30">
              <span className="w-2 h-2 rounded-full bg-success animate-pulse" />
              <span className="text-xs font-bold text-success uppercase">{t('processing_label')}</span>
            </div>
          )}
        </div>

        {/* Row 3: Agents Involved */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[10px] font-bold text-ink-3 uppercase tracking-widest mr-1">Agents:</span>
          {agents.map((agent, i) => (
            <div key={i} className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs shadow-sm"
              style={{
                background: `${agent.color}15`,
                border: `1px solid ${agent.color}35`,
              }}>
              <span className="text-xs">{agent.icon}</span>
              <span className="font-semibold text-ink-2">{agent.name}</span>
              <span className="w-2 h-2 rounded-full"
                style={{
                  background: session.is_streaming ? agent.color : '#999',
                  animation: session.is_streaming ? 'pulse 1.5s ease-in-out infinite' : 'none',
                }} />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export { ActiveSessionCardNew }
export default ActiveSessionCardNew
