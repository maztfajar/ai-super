import { useState, useEffect } from 'react'
import { MessageSquare, Clock, Zap, AlertCircle } from 'lucide-react'
import clsx from 'clsx'

// ── Active AI Session Card (Horizontal) ────────────────────
function ActiveSessionCardNew({ session }) {
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
      { name: 'Reasoning', icon: '🧠', color: '#8B5CF6', type: 'reasoning' },
      { name: 'Coding', icon: '💻', color: '#3B82F6', type: 'coding' },
      { name: 'Research', icon: '🔍', color: '#10B981', type: 'research' },
      { name: 'Writing', icon: '✍️', color: '#F59E0B', type: 'writing' },
      { name: 'System', icon: '🖥️', color: '#EF4444', type: 'system' },
      { name: 'Creative', icon: '🎨', color: '#EC4899', type: 'creative' },
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
      { icon: '🔄', label: 'Task Breakdown', color: '#3B82F6' },
      { icon: '💻', label: 'Code Generation', color: '#10B981' },
      { icon: '🧠', label: 'Analysis', color: '#8B5CF6' },
      { icon: '📊', label: 'Data Processing', color: '#F59E0B' },
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
        <div className="flex items-start gap-3 pb-2 border-b border-border/30">
          <MessageSquare size={16} className="text-ink-3 flex-shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <p className="text-sm text-ink line-clamp-2">
              {session.title || 'New Chat Session'}
            </p>
          </div>
        </div>

        {/* Row 2: Timer & Status */}
        <div className="flex items-center justify-between gap-3 mb-2 flex-wrap">
          {/* Timer */}
          <div className="flex items-center gap-2 px-2.5 py-1 rounded-lg bg-bg-4/50">
            <Clock size={13} className="text-accent" />
            <span className="text-[11px] font-mono font-bold text-ink">
              {formatTime(elapsed)}s elapsed
            </span>
          </div>

          {/* Orchestrator Status */}
          <div className="flex items-center gap-2 px-2.5 py-1 rounded-lg"
            style={{ background: `${orchestratorStatus.color}15`, border: `1px solid ${orchestratorStatus.color}30` }}>
            <span className="text-[13px]">{orchestratorStatus.icon}</span>
            <span className="text-[10px] font-semibold text-ink-2">{orchestratorStatus.label}</span>
          </div>

          {/* Streaming Indicator */}
          {session.is_streaming && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-success/15 border border-success/30">
              <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
              <span className="text-[10px] font-bold text-success">Processing</span>
            </div>
          )}
        </div>

        {/* Row 3: Agents Involved */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[9px] font-bold text-ink-3 uppercase tracking-widest">Agents:</span>
          {agents.map((agent, i) => (
            <div key={i} className="flex items-center gap-1.5 px-2 py-1 rounded-full text-[10px]"
              style={{
                background: `${agent.color}15`,
                border: `1px solid ${agent.color}35`,
              }}>
              <span className="text-[11px]">{agent.icon}</span>
              <span className="font-semibold text-ink-2">{agent.name}</span>
              <span className="w-1.5 h-1.5 rounded-full"
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
