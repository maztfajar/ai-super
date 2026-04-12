import { useState, useEffect } from 'react'
import { Zap } from 'lucide-react'
import clsx from 'clsx'
import { api } from '../hooks/useApi'

function AgentRegistry({ viewMode = 'grid' }) {
  const [selectedView, setSelectedView] = useState(viewMode)
  const [agents, setAgents] = useState([])
  const [agentPerformance, setAgentPerformance] = useState({})
  const [activeAgentTypes, setActiveAgentTypes] = useState(new Set())
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchAgents = async () => {
      try {
        const agentsData = await api.monitoringAgents?.()
        if (agentsData?.agents) {
          setAgents(agentsData.agents)
        }
      } catch (err) {
        console.error('Error fetching agents:', err)
      }
    }

    const fetchPerformance = async () => {
      try {
        const perfData = await api.agentPerformance?.()
        const perfMap = {}
        
        perfData?.summaries?.forEach((summary) => {
          const agentType = summary.agent_type || summary.type
          if (!perfMap[agentType]) {
            perfMap[agentType] = {
              tasks: 0,
              success: 0,
              avg_time: 0,
              total_cost: 0,
              count: 0,
            }
          }
          perfMap[agentType].tasks += summary.total_tasks || 0
          perfMap[agentType].success += (summary.success_rate || 0) * (summary.total_tasks || 0)
          perfMap[agentType].avg_time = summary.avg_time_ms || 0
          perfMap[agentType].total_cost += summary.total_cost || 0
          perfMap[agentType].count += 1
        })

        Object.keys(perfMap).forEach(key => {
          if (perfMap[key].count > 0 && perfMap[key].tasks > 0) {
            perfMap[key].success = (perfMap[key].success / perfMap[key].tasks).toFixed(2)
          }
        })

        setAgentPerformance(perfMap)
      } catch (err) {
        console.error('Error fetching agent performance:', err)
      }
    }

    // Fetch active sessions to infer which agents are currently in use
    const fetchActiveSessions = async () => {
      try {
        const res = await fetch('/api/monitoring/active-sessions')
        const data = await res.json()
        const activeTypes = new Set()
        
        data.active_sessions?.forEach(session => {
          const title = (session.title || '').toLowerCase()
          // Map keywords to agent types
          if (title.match(/code|sql|python|function|debug|script/)) activeTypes.add('coding')
          if (title.match(/riset|research|cari|search|data/)) activeTypes.add('research')
          if (title.match(/tulis|write|doc|email|konten/)) activeTypes.add('writing')
          if (title.match(/kreatif|creative|idea|brainstorm|design/)) activeTypes.add('creative')
          if (title.match(/analisis|logic|strategi|reason/)) activeTypes.add('reasoning')
          if (title.match(/server|deploy|sistem|system/)) activeTypes.add('system')
        })
        
        setActiveAgentTypes(activeTypes)
        setLoading(false)
      } catch (err) {
        console.error('Error fetching active sessions:', err)
        setLoading(false)
      }
    }

    fetchAgents()
    fetchPerformance()
    fetchActiveSessions()

    const interval = setInterval(() => {
      fetchPerformance()
      fetchActiveSessions()
    }, 3000)

    return () => clearInterval(interval)
  }, [])

  const getStatusFromPerformance = (agentType) => {
    // If agent is currently being used in an active session, mark as "active"
    if (activeAgentTypes.has(agentType)) {
      return 'active'
    }
    const perf = agentPerformance[agentType]
    if (!perf) return 'idle'
    if (perf.tasks > 10) return 'busy'
    if (perf.tasks > 0) return 'ready'
    return 'idle'
  }

  const statusConfig = {
    active: { label: '🔵 Active', color: '#3B82F6', bg: 'rgba(59,130,246,0.2)', pulse: true },
    ready: { label: '🟢 Ready', color: '#10B981', bg: 'rgba(16,185,129,0.1)' },
    busy: { label: '🔴 Busy', color: '#EF4444', bg: 'rgba(239,68,68,0.1)' },
    idle: { label: '⚪ Idle', color: '#999999', bg: 'rgba(150,150,150,0.1)' },
  }

  if (loading && agents.length === 0) {
    return (
      <div className="text-center py-8 text-ink-3">
        <p className="text-sm">Memuat data agent...</p>
      </div>
    )
  }

  return (
    <div className="space-y-3 w-full">
      <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
        <div className="flex items-center gap-2">
          <Zap size={16} className="text-accent-2" />
          <h2 className="text-base font-black text-ink tracking-tight">
            🤖 Agents
          </h2>
          <span className="text-[9px] font-bold px-2 py-0.5 rounded-full"
            style={{ background: 'rgba(100,102,241,0.15)', color: '#818CF8' }}>
            {agents.length}
          </span>
        </div>

        <div className="flex items-center gap-1 p-0.5 rounded-lg bg-white/5">
          {['grid', 'list'].map(mode => (
            <button
              key={mode}
              onClick={() => setSelectedView(mode)}
              className={clsx(
                'px-2 py-1 rounded text-[9px] font-bold uppercase transition-all',
                selectedView === mode
                  ? 'bg-accent text-white shadow-lg'
                  : 'text-ink-3 hover:text-ink-2'
              )}>
              {mode === 'grid' ? '📊' : '📋'}
            </button>
          ))}
        </div>
      </div>

      {selectedView === 'grid' && (
        <div className="grid grid-cols-2 gap-2">
          {agents.map((agent) => {
            const perf = agentPerformance[agent.type] || {}
            const status = getStatusFromPerformance(agent.type)
            const cfg = statusConfig[status]
            const usage = perf.tasks ? Math.min(100, (perf.tasks / 50) * 100) : 0

            return (
              <div
                key={agent.type}
                className="group relative rounded-lg p-3 border border-border/30 hover:border-accent/50 transition-all cursor-pointer overflow-hidden text-xs"
                style={{
                  background: 'linear-gradient(135deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01))',
                }}
              >
                <div className="absolute inset-0 bg-gradient-to-br from-accent/10 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />

                <div className="relative z-10 space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-1.5 flex-1 min-w-0">
                      <span className="text-lg flex-shrink-0">{agent.icon || '🤖'}</span>
                      <div className="min-w-0">
                        <h3 className="text-[11px] font-bold text-ink truncate">{agent.name}</h3>
                      </div>
                    </div>
                    <span className="text-xs flex-shrink-0">{cfg.label.split(' ')[0]}</span>
                  </div>

                  <div className="flex flex-wrap gap-0.5">
                    {agent.skills?.slice(0, 2).map((skill, i) => (
                      <span key={i} className="text-[7px] px-1 py-0.5 rounded font-semibold"
                        style={{
                          background: 'rgba(100,102,241,0.15)',
                          color: '#818CF8',
                        }}>
                        {typeof skill === 'string' ? skill.substring(0, 8) : skill}
                      </span>
                    ))}
                    {agent.skills?.length > 2 && (
                      <span className="text-[7px] text-ink-3">+{agent.skills.length - 2}</span>
                    )}
                  </div>

                  <div className="space-y-1 text-[8px] text-ink-3">
                    <div>Tasks: {perf.tasks || 0}</div>
                    <div>Success: {(perf.success * 100 || 0).toFixed(0)}%</div>
                  </div>

                  <div className="w-full h-1 rounded-full bg-white/10 overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${usage}%`,
                        background: cfg.color,
                      }}
                    />
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {selectedView === 'list' && (
        <div className="space-y-1 max-h-64 overflow-y-auto">
          {agents.map((agent) => {
            const perf = agentPerformance[agent.type] || {}
            const status = getStatusFromPerformance(agent.type)
            const cfg = statusConfig[status]

            return (
              <div key={agent.type} className="flex items-center justify-between p-2 rounded border border-border/30 hover:border-accent/50 transition-all cursor-pointer text-xs">
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  <span className="text-sm flex-shrink-0">{agent.icon || '🤖'}</span>
                  <div className="min-w-0">
                    <div className="text-[10px] font-bold text-ink truncate">{agent.name}</div>
                    <div className="text-[8px] text-ink-3">{perf.tasks || 0} tasks</div>
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className="text-[9px] px-1.5 py-0.5 rounded-full" style={{ background: cfg.bg, color: cfg.color }}>
                    {cfg.label.split(' ')[0]}
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export { AgentRegistry }
export default AgentRegistry
