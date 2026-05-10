import { useState, useEffect } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer
} from 'recharts'
import { Activity } from 'lucide-react'
import { api } from '../hooks/useApi'

export function LiveModelPerformanceChart({ activeSessions = [] }) {
  const [chartData, setChartData] = useState([])
  const [liveMetrics, setLiveMetrics] = useState({
    mostActive: '—',
    throughput: '0 requests',
  })

  useEffect(() => {
    const fetchPerformanceData = async () => {
      try {
        const modelStats = {}

        // Fetch active sessions (real-time data)
        try {
          const sessionsData = await api.activeSessions?.()
          sessionsData?.active_sessions?.forEach((session) => {
            const model = session.model_used || 'Unknown'
            // Extract model name from full path (e.g., "gpt-5-mini" from "openai/gpt-5-mini")
            const modelKey = model.includes('/') ? model.split('/').pop() : model
            const displayModel = modelKey.substring(0, 12)
            
            if (!modelStats[displayModel]) {
              modelStats[displayModel] = {
                tasks: 0,
                sessions: 0,
                isActive: true,
              }
            }
            
            modelStats[displayModel].tasks += session.msg_count || 1
            modelStats[displayModel].sessions += 1
          })
        } catch (err) {
          console.log('Active sessions fetch error (non-critical):', err)
        }

        // Also fetch performance data for historical context
        try {
          const perfData = await api.agentPerformance?.()
          perfData?.summaries?.forEach((summary) => {
            const model = summary.model || summary.model_name || 'Unknown'
            const modelKey = model.includes('/') ? model.split('/').pop() : model
            const displayModel = modelKey.substring(0, 12)
            
            // Only add if not already in active sessions
            if (!modelStats[displayModel]) {
              modelStats[displayModel] = {
                tasks: summary.total_tasks || 0,
                sessions: 0,
                isActive: false,
              }
            }
          })
        } catch (err) {
          console.log('Performance data fetch error (non-critical):', err)
        }

        const now = new Date()
        const timeStr = now.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
        
        const newPoint = { time: timeStr }
        Object.entries(modelStats).forEach(([model, stats]) => {
          newPoint[model] = stats.tasks + stats.sessions * 2 || 0
        })

        setChartData(prev => {
          const updated = [...prev, newPoint]
          return updated.length > 60 ? updated.slice(1) : updated
        })

        if (Object.keys(modelStats).length > 0) {
          const mostActive = Object.entries(modelStats).sort((a, b) => 
            (b[1].tasks + b[1].sessions * 2) - (a[1].tasks + a[1].sessions * 2)
          )[0]
          const totalSessions = Object.values(modelStats).reduce((sum, s) => sum + s.sessions, 0)
          
          setLiveMetrics({
            mostActive: `${mostActive[0]} ${mostActive[1].isActive ? '🔴' : ''}`,
            throughput: `${totalSessions} active session${totalSessions !== 1 ? 's' : ''}`,
          })
        }
      } catch (err) {
        console.error('Error fetching performance data:', err)
      }
    }

    fetchPerformanceData()
    const interval = setInterval(fetchPerformanceData, 3000)
    return () => clearInterval(interval)
  }, [])

  const getModelColors = () => {
    const colors = {}
    chartData.forEach(point => {
      Object.keys(point).forEach(key => {
        if (key !== 'time' && !colors[key]) {
          const hue = Object.keys(colors).length * 60
          colors[key] = `hsl(${hue}, 70%, 50%)`
        }
      })
    })
    return colors
  }

  const modelColors = getModelColors()

  return (
    <div className="space-y-4 w-full">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <Activity size={16} className="text-accent animate-pulse" />
          <span className="text-[10px] font-black uppercase tracking-widest text-accent/80">🟢 Real-Time Data</span>
        </div>
        
        <div className="flex items-center gap-2 flex-wrap">
          {Object.entries(modelColors).map(([model, color]) => (
            <div key={model} className="flex items-center gap-1.5 px-2 py-1 rounded-full text-[9px] font-semibold"
              style={{ background: `${color}25`, border: `1px solid ${color}60` }}>
              <span className="w-1.5 h-1.5 rounded-full" style={{ background: color }} />
              <span className="text-ink">{model}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-bg-3/30 rounded-lg p-4 border border-border/30 overflow-x-auto">
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
              <defs>
                {Object.entries(modelColors).map(([model, color]) => (
                  <linearGradient key={model} id={`grad${model}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={color} stopOpacity={0.5} />
                    <stop offset="100%" stopColor={color} stopOpacity={0.05} />
                  </linearGradient>
                ))}
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" vertical={false} />
              <XAxis dataKey="time" stroke="rgba(200,200,200,0.4)" height={25} style={{ fontSize: '11px' }} />
              <YAxis stroke="rgba(200,200,200,0.4)" style={{ fontSize: '11px' }} />
              <Tooltip 
                contentStyle={{ background: 'rgba(15,20,50,0.95)', border: '1px solid #555', borderRadius: '8px', padding: '10px' }}
                labelStyle={{ color: '#fff', fontSize: '12px' }}
              />
              {Object.keys(modelColors).map(model => (
                <Area
                  key={model}
                  type="monotone"
                  dataKey={model}
                  stroke={modelColors[model]}
                  fill={`url(#grad${model})`}
                  strokeWidth={2}
                  isAnimationActive={false}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex flex-col items-center justify-center py-12 text-ink-3">
            <Activity size={24} className="opacity-30 mb-2" />
            <p className="text-sm">Menunggu data real-time...</p>
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="bg-accent/10 border border-accent/30 rounded-lg p-3">
          <div className="text-[9px] font-bold text-accent/70 uppercase tracking-widest">Model Paling Aktif</div>
          <div className="text-base font-black text-accent mt-1 truncate">{liveMetrics.mostActive}</div>
        </div>
        <div className="bg-warn/10 border border-warn/30 rounded-lg p-3">
          <div className="text-[9px] font-bold text-warn/70 uppercase tracking-widest">Total Requests</div>
          <div className="text-base font-black text-warn mt-1">{liveMetrics.throughput}</div>
        </div>
      </div>
    </div>
  )
}

export default LiveModelPerformanceChart
